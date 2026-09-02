"""Agent executor / bounded state machine (G14).

Binds the typed tool registry (`satquery_agents.agent`) to the real frozen-stack
specialist slices in this package, runs a PLAN produced by the planner (only after
the deterministic policy layer accepts it), OBSERVES each result, and
conditionally chooses the next action. Bounded: <= MAX_STEPS specialist calls, no
recursion. On planner failure it falls back to the deterministic `run_analyze`.

The LLM never touches model code and never bypasses validation — every tool call
goes through a wrapper here, and every wrapper is a thin call to an existing
slice that already emits evidence + verification + provenance.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import numpy as np
import rasterio
from scipy import ndimage

from satquery_agents.agent import (
    MAX_STEPS,
    AgentInvestigationResult,
    AgentMemory,
    PlanContext,
    RegionRef,
    SpatialFinding,
    StepObservation,
    TaskType,
    TimelineEntry,
    assess_step,
    plan_with_fallback,
    validate_plan,
)
from satquery_core.routing import RoutingRequest, route

from app.services.analyze import run_analyze
from app.services.failure_aware import derive_resolution
from app.services.grounding_slice import run_grounding
from app.services.multimodal_slice import run_joint_from_geotiffs
from app.services.normalize import normalize
from app.services.scene_slice import run_scene
from app.services.semantic_change_baseline import run_composed_semantic_change
from app.services.temporal_slice import run_change_fallback, run_change_slice
from app.services.vqa_slice import run_vqa

_REPO_ROOT = Path(__file__).resolve().parents[4]
_CF_CKPT = _REPO_ROOT / ("models/cache/changeformer/CD_ChangeFormerV6_LEVIR_b16_lr0.0001_adamw"
                         "_train_test_200_linear_ce_multi_train_True_multi_infer_False"
                         "_shuffle_AB_False_embed_dim_256")
_MIN_REGION_PX = 64
_NEGLIGIBLE_CHANGE = 0.01  # changed_fraction below this -> agent skips region/grounding steps
_SCENE_PROMPTS = ["urban area", "farmland", "forest", "water body", "bare land",
                  "industrial area", "residential area", "airport"]


def _now() -> str:
    return time.strftime("%H:%M:%S", time.localtime())


def _band_count(p: str) -> int:
    try:
        with rasterio.open(p) as d:
            return d.count
    except Exception:  # noqa: BLE001
        return 0


# --------------------------------------------------------------------------- #
# tool implementations — each returns (payload dict, evidence list, verification, resolution, model)
# --------------------------------------------------------------------------- #


def _tool_validate(step, mem: AgentMemory, ctx: dict) -> dict:
    from satquery_geospatial import check_pair_compatibility, read_raster_meta, validate_geotiff

    tifs = [p for p in mem.image_paths.values() if p.lower().endswith((".tif", ".tiff"))]
    errors, geo_notes = [], []
    for p in tifs:
        try:
            v = validate_geotiff(p)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{Path(p).name}: unreadable ({type(exc).__name__})")
            continue
        if not v.ok:
            failed = {c.name for c in v.failed()}
            (geo_notes if failed <= {"transform_valid", "bounds", "crs_present"} else errors).append(
                f"{Path(p).name}: {sorted(failed)}"
            )
    pair_ok = None
    optical_tifs = tifs[:2]
    if len(optical_tifs) == 2 and not errors:
        try:
            pr = check_pair_compatibility(read_raster_meta(optical_tifs[0]),
                                          read_raster_meta(optical_tifs[1]))
            pair_ok = pr.co_registered
            if not pr.co_registered:
                errors.append(f"pair not co-registered: {pr.mismatches}")
        except Exception as exc:  # noqa: BLE001
            errors.append(f"pair check error: {type(exc).__name__}")
        mem.pair_co_registered = pair_ok
    # CRS + geo availability
    if tifs and not geo_notes:
        try:
            m = read_raster_meta(tifs[0])
            if m.crs:
                mem.crs = str(m.crs)
                mem.geospatial_available = True
        except Exception:  # noqa: BLE001
            pass
    ok = not errors
    payload = {"ok": ok, "errors": errors, "geo_warnings": geo_notes,
               "pair_co_registered": pair_ok, "n_images": len(mem.image_paths)}
    vr = {"status": "SUPPORTED" if ok else "CONTRADICTED",
          "checks": [{"name": "geospatial_validation", "passed": ok, "detail": "; ".join(errors) or "ok"}],
          "notes": geo_notes}
    return {"payload": payload, "evidence": [], "verification": vr, "model": None}


def _tool_vqa(step, mem: AgentMemory, ctx: dict) -> dict:
    img = mem.image_paths[step.inputs.get("image", "img0")]
    q = step.inputs.get("question") or mem.goal
    r = run_vqa(img, q)
    p = r.model_dump()
    return {"payload": p, "evidence": p.get("evidence", []), "verification": p.get("verification"),
            "model": "TinyRS-2B"}


def _tool_grounding(step, mem: AgentMemory, ctx: dict) -> dict:
    img = mem.image_paths[step.inputs.get("image", "img0")]
    phrase = step.inputs.get("phrase") or "buildings"
    r = run_grounding(img, phrase, artifact_dir=ctx.get("artifact_dir"))
    p = r.model_dump()
    return {"payload": p, "evidence": p.get("evidence", []), "verification": p.get("verification"),
            "model": "RemoteSAM"}


def _tool_scene(step, mem: AgentMemory, ctx: dict) -> dict:
    img = mem.image_paths[step.inputs.get("image", "img0")]
    r = run_scene(img, step.inputs.get("prompts") or _SCENE_PROMPTS)
    p = r.model_dump()
    return {"payload": p, "evidence": p.get("evidence", []), "verification": p.get("verification"),
            "model": "RemoteCLIP"}


def _tool_temporal(step, mem: AgentMemory, ctx: dict) -> dict:
    t1 = mem.image_paths[step.inputs.get("t1", "img0")]
    t2 = mem.image_paths[step.inputs.get("t2", "img1")]
    r = run_change_slice(t1, t2, checkpoint_dir=_CF_CKPT, strict=True, artifact_dir=ctx.get("artifact_dir"))
    model = "ChangeFormer"
    if not r.ok:
        fb = run_change_fallback(t1, t2, artifact_dir=ctx.get("artifact_dir"))
        if fb.ok:
            r, model = fb, "image-difference fallback"
    p = r.model_dump()
    if p.get("mask_path"):
        mem.masks[step.step_id] = p["mask_path"]
    stats = p.get("stats") or {}
    if stats.get("changed_fraction") is not None:
        mem.numeric["changed_fraction"] = float(stats["changed_fraction"])
    return {"payload": p, "evidence": p.get("evidence", []), "verification": p.get("verification"),
            "model": model}


def _tool_semantic(step, mem: AgentMemory, ctx: dict) -> dict:
    t1 = mem.image_paths[step.inputs.get("t1", "img0")]
    t2 = mem.image_paths[step.inputs.get("t2", "img1")]
    r = run_composed_semantic_change(t1, t2, checkpoint_dir=_CF_CKPT, artifact_dir=ctx.get("artifact_dir"))
    p = r.model_dump()
    if p.get("mask_path"):
        mem.masks[step.step_id] = p["mask_path"]
    if p.get("changed_fraction") is not None:
        mem.numeric["changed_fraction"] = float(p["changed_fraction"])
    for rg in p.get("regions", []) or []:
        mem.regions.append(RegionRef(region_id=rg["region_id"], bbox_pixel=list(rg["bbox_pixel"]),
                                     bbox_lonlat=list(rg["bbox_lonlat"]) if rg.get("bbox_lonlat") else None,
                                     area_ha=rg.get("area_ha"), label=rg.get("top_tag"),
                                     source_step=step.step_id))
    return {"payload": p, "evidence": p.get("evidence", []), "verification": p.get("verification"),
            "model": "ChangeFormer + RemoteCLIP"}


def _tool_optical_sar(step, mem: AgentMemory, ctx: dict) -> dict:
    opt = mem.image_paths[step.inputs.get("optical", "img0")]
    sar = mem.image_paths[step.inputs.get("sar", "img1")]
    r = run_joint_from_geotiffs(opt, sar, model="croma")
    p = r.model_dump()
    p["repr_dim"] = (p.get("representation") or {}).get("dim")  # scalar so bounded memory keeps it
    return {"payload": p, "evidence": p.get("evidence", []), "verification": p.get("verification"),
            "model": (p.get("model") or "croma").upper()}


def _tool_extract_regions(step, mem: AgentMemory, ctx: dict) -> dict:
    ref = step.inputs.get("change_result_ref")
    mask_path = mem.masks.get(ref) if ref else None
    if not mask_path:
        mask_path = next(iter(mem.masks.values()), None)
    if not mask_path or not Path(mask_path).exists():
        return {"payload": {"ok": False, "errors": ["no change mask to extract regions from"],
                            "regions": []}, "evidence": [], "verification": None, "model": None}
    from satquery_geospatial import read_raster_meta

    with rasterio.open(mask_path) as ds:
        mask = ds.read(1) > 127
    lab, n = ndimage.label(mask)
    meta = None
    for p in mem.image_paths.values():
        if p.lower().endswith((".tif", ".tiff")):
            try:
                meta = read_raster_meta(p)
                break
            except Exception:  # noqa: BLE001
                pass
    px_area = (meta.res[0] * meta.res[1]) if (meta and getattr(meta, "is_projected", False)) else None
    comps = []
    for i in range(1, n + 1):
        ys, xs = np.where(lab == i)
        if ys.size < _MIN_REGION_PX:
            continue
        comps.append((int(ys.size), int(ys.min()), int(xs.min()), int(ys.max()), int(xs.max())))
    comps.sort(reverse=True)
    regions = []
    for k, (area_px, rmin, cmin, rmax, cmax) in enumerate(comps[:6], 1):
        lonlat = None
        if meta and getattr(meta, "crs_epsg", None):
            try:
                from pyproj import Transformer
                a, b, c, d, e, ff = meta.transform
                xs = [a * cc + b * rr + c for cc in (cmin, cmax + 1) for rr in (rmin, rmax + 1)]
                ys = [d * cc + e * rr + ff for cc in (cmin, cmax + 1) for rr in (rmin, rmax + 1)]
                tr = Transformer.from_crs(f"EPSG:{meta.crs_epsg}", "EPSG:4326", always_xy=True)
                lo0, la0 = tr.transform(min(xs), min(ys))
                lo1, la1 = tr.transform(max(xs), max(ys))
                lonlat = [round(min(lo0, lo1), 6), round(min(la0, la1), 6),
                          round(max(lo0, lo1), 6), round(max(la0, la1), 6)]
            except Exception:  # noqa: BLE001
                lonlat = None
        rr = RegionRef(region_id=k, bbox_pixel=[rmin, cmin, rmax, cmax], bbox_lonlat=lonlat,
                       area_ha=(round(area_px * px_area / 10_000.0, 4) if px_area else None),
                       source_step=step.step_id)
        mem.regions.append(rr)
        regions.append(rr.model_dump())
    payload = {"ok": bool(regions), "errors": [] if regions else ["no region above size threshold"],
               "regions": regions, "n_regions": len(regions)}
    vr = {"status": "SUPPORTED" if regions else "INSUFFICIENT_EVIDENCE",
          "checks": [{"name": "regions_extracted", "passed": bool(regions), "detail": f"{len(regions)} region(s)"}]}
    return {"payload": payload, "evidence": [], "verification": vr, "model": None}


def _tool_cross_check(step, mem: AgentMemory, ctx: dict) -> dict:
    # do grounded boxes fall inside a changed region?
    boxes = []
    for sid, res in mem.results.items():
        b = res.get("bbox_xyxy")
        if b and res.get("validation_status") == "PASS":
            boxes.append((sid, b))
    hits = []
    for sid, (x0, y0, x1, y1) in boxes:
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        inside = any(r.bbox_pixel[1] <= cx <= r.bbox_pixel[3] and r.bbox_pixel[0] <= cy <= r.bbox_pixel[2]
                     for r in mem.regions)
        hits.append({"grounding_step": sid, "centroid_in_changed_region": inside})
    payload = {"ok": True, "boxes_checked": len(boxes), "regions": len(mem.regions),
               "matches": hits,
               "note": ("no grounded box to cross-check" if not boxes else
                        "checked grounded box centroids against changed-region bboxes")}
    vr = {"status": "SUPPORTED" if boxes else "NOT_APPLICABLE",
          "checks": [{"name": "spatial_corroboration", "passed": any(h["centroid_in_changed_region"] for h in hits),
                      "detail": f"{sum(h['centroid_in_changed_region'] for h in hits)}/{len(hits)} inside"}]}
    return {"payload": payload, "evidence": [], "verification": vr, "model": None}


def _tool_verify(step, mem: AgentMemory, ctx: dict) -> dict:
    statuses = [s for s in mem.verification_statuses if s]
    contradicted = "CONTRADICTED" in statuses
    supported = statuses.count("SUPPORTED")
    overall = "CONTRADICTED" if contradicted else ("SUPPORTED" if supported else "INSUFFICIENT_EVIDENCE")
    res = derive_resolution(sub_ok=not contradicted and not mem.failures,
                            verification=None, semantic_verification=None,
                            fallback_used=("image-difference fallback" if "image-difference fallback"
                                           in mem.models_used else None))
    payload = {"ok": not contradicted, "overall_status": overall,
               "step_statuses": statuses, "failures": list(mem.failures)}
    vr = {"status": overall, "checks": [{"name": "aggregate_verification", "passed": not contradicted,
                                         "detail": f"{supported} supported / {len(statuses)} checked"}]}
    return {"payload": payload, "evidence": [], "verification": vr,
            "resolution": res.model_dump(), "model": None}


def _tool_inspect_evidence(step, mem: AgentMemory, ctx: dict) -> dict:
    payload = {"ok": True, "evidence_count": len(mem.evidence),
               "evidence_types": sorted({e.get("evidence_type") for e in mem.evidence if e.get("evidence_type")}),
               "evidence_ids": mem.evidence_ids}
    return {"payload": payload, "evidence": [], "verification": None, "model": None}


def _tool_finalize(step, mem: AgentMemory, ctx: dict) -> dict:
    return {"payload": {"ok": True, "note": "synthesis performed after the loop"},
            "evidence": [], "verification": None, "model": None}


TOOL_IMPL = {
    "validate_geospatial_input": _tool_validate,
    "run_vqa": _tool_vqa,
    "run_grounding": _tool_grounding,
    "run_scene_retrieval": _tool_scene,
    "run_temporal_change": _tool_temporal,
    "run_semantic_temporal_baseline": _tool_semantic,
    "run_optical_sar": _tool_optical_sar,
    "extract_changed_regions": _tool_extract_regions,
    "cross_check_evidence": _tool_cross_check,
    "verify_result": _tool_verify,
    "inspect_evidence": _tool_inspect_evidence,
    "finalize_answer": _tool_finalize,
}

_BOOKKEEPING = {"verify_result", "inspect_evidence", "finalize_answer", "cross_check_evidence"}


# --------------------------------------------------------------------------- #
# the executor
# --------------------------------------------------------------------------- #


def _modalities(image_paths: list[str]) -> list[str]:
    mods = set()
    for p in image_paths:
        if p.lower().endswith((".tif", ".tiff")):
            bc = _band_count(p)
            mods.add("sar" if bc == 2 else "optical")
        else:
            mods.add("optical")
    return sorted(mods)


def run_investigation(
    mission: str,
    image_paths: list[str],
    context: dict[str, Any] | None = None,
    *,
    artifact_dir: str | None = None,
    max_steps: int = MAX_STEPS,
    planner=None,
) -> AgentInvestigationResult:
    ctx = context or {}
    started = time.time()
    paths = [str(p) for p in image_paths]
    mods = _modalities(paths)
    res = AgentInvestigationResult(mission=mission, inputs=paths, max_steps=max_steps)
    tl = res.execution_trace
    tl.append(TimelineEntry(ts=_now(), event="Mission received"))

    # --- PLAN ---
    res.phase = "PLANNING"
    plan, planner_used, notes = plan_with_fallback(mission, len(paths), mods, planner=planner)
    res.plan, res.planner_used = plan, planner_used
    tl.append(TimelineEntry(ts=_now(), event=f"Plan generated ({planner_used}, {len(plan.steps)} steps)"))
    for nt in notes:
        res.warnings.append(f"planner: {nt}")

    # --- POLICY ---
    res.phase = "PLAN_VALIDATION"
    pctx = PlanContext(image_count=len(paths), modalities=mods,
                       has_valid_crs=False, pair_co_registered=None,
                       available_capabilities=_registry_caps())
    pr = validate_plan(plan, pctx)
    res.plan_rejection_reasons = pr.reasons
    if not pr.ok:
        tl.append(TimelineEntry(ts=_now(), event=f"Plan REJECTED: {pr.reasons}"))
        res.plan_status = "rejected"
        return _deterministic_fallback(res, mission, paths, ctx, started, artifact_dir)
    res.plan_status = "valid" if planner_used != "rule_based_fallback" else "fallback"
    tl.append(TimelineEntry(ts=_now(), event="Plan validated"))

    # --- EXECUTE ---
    mem = AgentMemory(goal=mission, image_ids=[f"img{i}" for i in range(len(paths))],
                      image_paths={f"img{i}": p for i, p in enumerate(paths)})
    res.phase = "EXECUTING"
    done: set[str] = set()
    skipped: set[str] = set()
    order = _topo_order(plan)

    for sid in order:
        step = next(s for s in plan.steps if s.step_id == sid)
        obs = StepObservation(step_id=sid, task=step.task, tool=step.tool, status="pending",
                              started_at=_now())

        # dependency / skip propagation
        if any(d in skipped for d in step.depends_on) and step.tool not in ("verify_result",
                                                                            "inspect_evidence",
                                                                            "finalize_answer"):
            obs.status = "skipped"
            obs.replan_note = "an upstream step was skipped"
            res.steps.append(obs)
            skipped.add(sid)
            continue

        # bounded autonomy: cap specialist calls
        is_specialist = step.tool not in _BOOKKEEPING and step.tool != "validate_geospatial_input"
        if is_specialist and res.tool_calls >= max_steps:
            obs.status = "skipped"
            obs.replan_note = f"step cap ({max_steps} specialist calls) reached"
            res.hit_step_cap = True
            res.steps.append(obs)
            skipped.add(sid)
            continue

        # --- run ---
        obs.status = "running"
        res.phase = "OBSERVING"
        t0 = time.time()
        try:
            out = TOOL_IMPL[step.tool](step, mem, {"artifact_dir": artifact_dir})
        except Exception as exc:  # noqa: BLE001 - a specialist crash must not fabricate
            obs.status = "failed"
            obs.failure = f"{type(exc).__name__}: {str(exc)[:200]}"
            obs.finished_at = _now()
            obs.runtime_s = round(time.time() - t0, 2)
            mem.failures.append(f"{sid} ({step.tool}): {obs.failure}")
            res.steps.append(obs)
            tl.append(TimelineEntry(ts=_now(), event=f"{step.tool} FAILED: {obs.failure}"))
            if is_specialist:
                res.tool_calls += 1
            continue

        payload = out["payload"]
        obs.runtime_s = round(time.time() - t0, 2)
        obs.finished_at = _now()
        if is_specialist:
            res.tool_calls += 1

        mem.record_result(sid, payload)
        mem.add_evidence(out.get("evidence") or [])
        v = out.get("verification")
        r = out.get("resolution")
        if v and v.get("status"):
            mem.verification_statuses.append(v["status"])
            obs.verification_status = v["status"]
        if r:
            obs.resolution_qualifier = r.get("qualifier")
        mem.note_model(out.get("model"))
        for w in payload.get("geo_warnings", []) or []:
            if w not in mem.warnings:
                mem.warnings.append(w)

        ok = bool(payload.get("ok", True))
        res.phase = "VERIFYING"
        verdict, why = assess_step(task=step.task, ok=ok, payload=payload, verification=v, resolution=r)
        obs.verdict = verdict
        obs.summary = _step_summary(step.task, payload)
        obs.numeric = {k: float(x) for k, x in mem.numeric.items()}
        obs.status = "completed" if ok else "failed"
        if not ok:
            mem.failures.append(f"{sid} ({step.tool}): {payload.get('errors') or 'ok=false'}")
        res.steps.append(obs)
        tl.append(TimelineEntry(ts=_now(), event=f"{step.tool} -> {verdict} ({why})"))

        # ---- OBSERVE / REPLAN: conditional pruning based on the observation ----
        res.phase = "REPLANNING"
        if step.task == TaskType.TEMPORAL_CHANGE and ok:
            cf = mem.numeric.get("changed_fraction", 1.0)
            if cf < _NEGLIGIBLE_CHANGE:
                for later in plan.steps:
                    if later.task in (TaskType.EXTRACT_CHANGED_REGIONS, TaskType.GROUND_OBJECT,
                                      TaskType.OPTICAL_SAR_ANALYSIS) and later.step_id not in done:
                        skipped.add(later.step_id)
                tl.append(TimelineEntry(
                    ts=_now(),
                    event=f"changed_fraction {cf:.4f} < {_NEGLIGIBLE_CHANGE} -> skipping region/grounding/SAR steps"))
                res.warnings.append("no significant change detected; downstream localisation steps were skipped")
        if step.task == TaskType.GROUND_OBJECT:
            if not payload.get("bbox_xyxy"):
                res.warnings.append("grounding produced no region — not fabricating a location")
        if step.task == TaskType.EXTRACT_CHANGED_REGIONS and not payload.get("regions"):
            for later in plan.steps:
                if later.task == TaskType.GROUND_OBJECT and later.step_id not in done:
                    skipped.add(later.step_id)
            tl.append(TimelineEntry(ts=_now(), event="no changed regions -> skipping region grounding"))

        done.add(sid)
        res.phase = "EXECUTING"

    # --- FINALIZE ---
    res.phase = "FINALIZING"
    _synthesize(res, mem, plan)
    res.timings = {"total_s": round(time.time() - started, 2),
                   **{f"{o.step_id}_{o.tool}": o.runtime_s for o in res.steps if o.runtime_s}}
    res.ok = res.verification is not None and res.verification.get("status") != "CONTRADICTED" and not (
        res.tool_calls == 0 and res.plan_status not in ("valid", "fallback"))
    tl.append(TimelineEntry(ts=_now(), event="Final report generated"))
    res.phase = "FINALIZING" if res.ok else "FAILED"
    return res


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #


def _registry_caps() -> list[str]:
    try:
        import yaml
        p = _REPO_ROOT / "packages" / "model_adapters" / "model_registry.yaml"
        data = yaml.safe_load(p.read_text()) or {}
        return sorted({c for m in (data.get("models") or {}).values() for c in m.get("capabilities", [])})
    except Exception:  # noqa: BLE001
        return []


def _topo_order(plan) -> list[str]:
    graph = {s.step_id: list(s.depends_on) for s in plan.steps}
    seq = [s.step_id for s in plan.steps]  # planner order is already ~topological
    out, seen = [], set()

    def visit(n: str) -> None:
        if n in seen or n not in graph:
            return
        for d in graph[n]:
            visit(d)
        seen.add(n)
        out.append(n)

    for n in seq:
        visit(n)
    return out


def _step_summary(task: TaskType, payload: dict) -> str:
    if task == TaskType.VALIDATE_INPUT:
        return ("validation ok" if payload.get("ok") else f"validation failed: {payload.get('errors')}")
    if task == TaskType.VQA:
        return f"answer: {(payload.get('answer_text') or '')[:200]}"
    if task == TaskType.GROUND_OBJECT:
        return (f"grounded box {payload.get('bbox_xyxy')}" if payload.get("bbox_xyxy")
                else f"no region grounded ({payload.get('validation_status')})")
    if task == TaskType.SCENE_UNDERSTANDING:
        a = payload.get("answer") or {}
        return f"top label: {a.get('top_label')}"
    if task == TaskType.TEMPORAL_CHANGE:
        st = payload.get("stats") or {}
        return f"changed_fraction {st.get('changed_fraction')}, area {st.get('changed_area_ha')} ha"
    if task == TaskType.SEMANTIC_CHANGE:
        return f"{len(payload.get('regions', []))} regions; {(payload.get('description') or '')[:160]}"
    if task == TaskType.OPTICAL_SAR_ANALYSIS:
        rep = payload.get("representation") or {}
        return f"joint representation dim {rep.get('dim')}"
    if task == TaskType.EXTRACT_CHANGED_REGIONS:
        return f"{payload.get('n_regions', 0)} region(s) extracted"
    if task == TaskType.CROSS_CHECK_EVIDENCE:
        return payload.get("note", "")
    if task == TaskType.VERIFY:
        return f"overall {payload.get('overall_status')}"
    if task == TaskType.SUMMARIZE:
        return f"{payload.get('evidence_count', 0)} evidence items"
    return ""


def _synthesize(res: AgentInvestigationResult, mem: AgentMemory, plan) -> None:
    """Evidence-first report — built ONLY from observed facts. No LLM invention."""
    findings: list[str] = []
    spatial: list[SpatialFinding] = []

    cf = mem.numeric.get("changed_fraction")
    if cf is not None:
        area = mem.results.get(next((o.step_id for o in res.steps
                                     if o.task in (TaskType.TEMPORAL_CHANGE, TaskType.SEMANTIC_CHANGE)), ""), {})
        stats = area.get("stats") or {}
        ha = stats.get("changed_area_ha") or area.get("changed_area_ha")
        findings.append(
            f"Change detected: ~{cf * 100:.1f}% of the scene changed"
            + (f" (~{ha} ha)" if ha else "") + "."
            if cf >= _NEGLIGIBLE_CHANGE else
            f"No significant change: changed fraction ~{cf * 100:.2f}% (below the {_NEGLIGIBLE_CHANGE * 100:.0f}% threshold)."
        )
    if mem.regions:
        findings.append(f"{len(mem.regions)} changed region(s) were isolated from the change mask.")
        for r in mem.regions[:6]:
            spatial.append(SpatialFinding(
                label=r.label or "changed region",
                where_pixel=[float(x) for x in r.bbox_pixel],
                where_lonlat=r.bbox_lonlat, area_ha=r.area_ha, source_step=r.source_step))

    for o in res.steps:
        pay = mem.results.get(o.step_id, {})
        if o.task == TaskType.VQA and pay.get("answer_text"):
            findings.append(f"VQA: {pay['answer_text']}")
        if o.task == TaskType.GROUND_OBJECT:
            b = pay.get("bbox_xyxy")
            if b:
                findings.append(f"Grounding located a region at pixel box {[round(x, 1) for x in b]}.")
                spatial.append(SpatialFinding(label="grounded structure", where_pixel=list(b),
                                              source_step=o.step_id))
            else:
                findings.append("Grounding: no matching region could be localised (returned explicitly, not fabricated).")
        if o.task == TaskType.SCENE_UNDERSTANDING:
            a = pay.get("answer") or {}
            if a.get("top_label"):
                findings.append(f"Scene: best zero-shot label is '{a['top_label']}'.")
        if o.task == TaskType.OPTICAL_SAR_ANALYSIS:
            dim = pay.get("repr_dim") or (pay.get("representation") or {}).get("dim")
            if dim and o.status == "completed":
                findings.append(
                    f"Optical+SAR: a joint representation (dim {dim}) was produced — "
                    "representation-level only; no textual fact is inferred from the embedding.")
        if o.task == TaskType.CROSS_CHECK_EVIDENCE:
            m = pay.get("matches") or []
            if m:
                inside = sum(1 for x in m if x["centroid_in_changed_region"])
                findings.append(f"Cross-check: {inside}/{len(m)} grounded region(s) fall inside a changed region.")

    # verification + resolution from the verify step
    vstep = next((o for o in res.steps if o.task == TaskType.VERIFY and o.status == "completed"), None)
    if vstep:
        vp = mem.results.get(vstep.step_id, {})
        res.verification = {"status": vp.get("overall_status", "INSUFFICIENT_EVIDENCE"),
                            "checks": [{"name": "aggregate", "passed": vp.get("ok", False),
                                        "detail": f"step statuses: {vp.get('step_statuses')}"}]}
    else:
        res.verification = {"status": "INSUFFICIENT_EVIDENCE", "checks": []}

    res.resolution = {"qualifier": ("RESULT_STRUCTURAL_FAIL" if res.verification["status"] == "CONTRADICTED"
                                    else "RESULT_OK" if res.verification["status"] == "SUPPORTED"
                                    else "RESULT_UNVERIFIED"),
                      "answer_surfaced": res.verification["status"] != "CONTRADICTED",
                      "note": "deterministic post-execution qualifier — NOT a confidence value"}

    res.key_findings = findings or ["The mission produced no positive findings within the executed plan."]
    res.spatial_findings = spatial
    res.evidence = mem.evidence
    res.warnings = _dedup(res.warnings + mem.warnings)
    res.failures = _dedup(res.failures + mem.failures)
    res.models_used = mem.models_used
    res.provenance = {
        "layer": "agent",
        "mask_source": next(iter(mem.masks.values()), None),
        "planner_used": res.planner_used,
        "plan_status": res.plan_status,
        "plan_steps": [{"step_id": s.step_id, "task": s.task.value, "tool": s.tool,
                        "depends_on": s.depends_on} for s in plan.steps],
        "tool_calls": res.tool_calls,
        "hit_step_cap": res.hit_step_cap,
        "note": "the LLM/rule planner proposes steps; the deterministic policy layer + executor run them. "
                "No confidence value is produced. Evidence and verification are preserved from each specialist.",
    }

    parts = []
    if cf is not None and cf >= _NEGLIGIBLE_CHANGE:
        parts.append(f"~{cf * 100:.1f}% of the scene changed")
    if mem.regions:
        parts.append(f"{len(mem.regions)} changed region(s) isolated")
    grounded = sum(1 for o in res.steps if o.task == TaskType.GROUND_OBJECT
                   and mem.results.get(o.step_id, {}).get("bbox_xyxy"))
    if grounded:
        parts.append(f"{grounded} structure region(s) located")
    if any(o.task == TaskType.OPTICAL_SAR_ANALYSIS and o.status == "completed" for o in res.steps):
        parts.append("optical+SAR representation computed")
    if res.failures:
        parts.append(f"{len(res.failures)} step(s) failed")

    # single-answer missions (VQA / scene): the answer IS the conclusion
    single_ans = next(
        (mem.results.get(o.step_id, {}) for o in res.steps
         if o.task == TaskType.VQA and mem.results.get(o.step_id, {}).get("answer_text")),
        None,
    )
    scene_ans = next(
        ((mem.results.get(o.step_id, {}).get("answer") or {}).get("top_label") for o in res.steps
         if o.task == TaskType.SCENE_UNDERSTANDING),
        None,
    )
    if not parts and single_ans:
        res.conclusion = f"{single_ans['answer_text']}  (Verification: {res.verification['status']}.)"
    elif not parts and scene_ans:
        res.conclusion = f"Scene best matches '{scene_ans}'.  (Verification: {res.verification['status']}.)"
    else:
        res.conclusion = (
            (", ".join(parts) + ". " if parts else "No positive findings within the executed plan. ")
            + f"Verification: {res.verification['status']}."
        )


def _deterministic_fallback(res, mission, paths, ctx, started, artifact_dir):
    """Planner unavailable / plan rejected -> run the deterministic /analyze path once."""
    res.mode = "ask-fallback"
    res.execution_trace.append(TimelineEntry(ts=_now(), event="Falling back to deterministic /analyze"))
    try:
        a = run_analyze(mission, paths, ctx, artifact_dir=artifact_dir)
        n = normalize(a, latency_s=round(time.time() - started, 2))
        res.ok = a.ok
        res.conclusion = n.answer
        res.key_findings = [n.answer] if n.answer else ["deterministic path produced no answer"]
        res.evidence = n.evidence
        res.verification = n.verification or {"status": "INSUFFICIENT_EVIDENCE", "checks": []}
        res.resolution = n.resolution
        res.warnings = _dedup(res.warnings + n.warnings)
        res.failures = _dedup(res.failures + n.failures)
        res.models_used = [n.model_used] if n.model_used else []
        res.provenance = {"layer": "agent->deterministic_fallback", "routing_code": n.task_code,
                          "note": "the agent plan could not be produced/validated; the deterministic "
                          "router handled the mission instead."}
        res.timings = {"total_s": round(time.time() - started, 2)}
        res.phase = "FINALIZING" if a.ok else "FAILED"
    except Exception as exc:  # noqa: BLE001
        res.phase = "FAILED"
        res.failures.append(f"deterministic fallback also failed: {type(exc).__name__}")
        res.conclusion = "The mission could not be completed: neither the agent plan nor the deterministic path succeeded."
    return res


def _dedup(xs: list[str]) -> list[str]:
    out = []
    for x in xs:
        if x not in out:
            out.append(x)
    return out
