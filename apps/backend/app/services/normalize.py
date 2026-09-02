"""One consistent user-facing response schema for `/analyze` (G13).

`run_analyze()` returns an `AnalyzeResult` whose `result` field is the raw dump of
whichever specialist slice ran (six different shapes). `normalize()` flattens that
into a single `NormalizedResponse` a UI (or a teammate) can consume without
knowing which specialist produced it.

Rules:
- Only populate a field when the task actually produced it. No invented values.
- Never synthesize a confidence number. `score` is passed through verbatim with
  its `score_meaning`.
- Geospatial fields appear only when the input carried a real CRS + transform.
- Caveats (RemoteSAM licence, experimental semantic baseline, representation-only
  optical-SAR, sanity-scale) are surfaced as `warnings`, never dropped.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from app.services.analyze import AnalyzeResult

# task -> the frozen-stack model(s) that serve it (for display when the slice
# doesn't echo a model name back)
_TASK_MODEL = {
    "SINGLE_IMAGE_VQA": "TinyRS-2B (Qwen2-VL-2B base)",
    "SINGLE_IMAGE_GROUNDING": "RemoteSAM",
    "SINGLE_IMAGE_SCENE": "RemoteCLIP",
    "TEMPORAL": "ChangeFormer",
    "MULTIMODAL_REPR": "CROMA",
}
_TASK_CAVEAT = {
    "SINGLE_IMAGE_GROUNDING": "RemoteSAM upstream licence is NOT STATED — treat grounding output as prototype-only.",
    "MULTIMODAL_REPR": "Optical+SAR path is representation-level only (no task head wired); "
    "EXP-004 Run 2 SAR benefit is positive but not significance-tested.",
}


class Box(BaseModel):
    """An axis-aligned box in image pixels (xyxy) plus optional geo bbox."""

    xyxy_pixel: list[float]
    bbox_lonlat: list[float] | None = None
    label: str | None = None
    score: float | None = None


class Region(BaseModel):
    """A connected changed area (semantic-change baseline)."""

    region_id: int
    area_px: int
    area_ha: float | None = None
    bbox_pixel: list[int]
    bbox_lonlat: list[float] | None = None
    label: str | None = None
    label_margin: float | None = None
    low_margin: bool = False


class ExecutionTrace(BaseModel):
    steps: list[str] = Field(
        default_factory=list,
        description="ordered pipeline stages that actually ran, e.g. "
        "['validate', 'interpret', 'route', 'specialist:remotesam', 'evidence', 'verify', 'resolve']",
    )
    routing_code: str | None = None
    routing_rule: str | None = None


class NormalizedResponse(BaseModel):
    # --- request echo ---
    query: str
    interpreted_task: str
    task_code: str
    execution_plan: list[str] = []

    # --- headline ---
    ok: bool
    answer: str | None = None
    model_used: str | None = None
    latency_s: float | None = None

    # --- task-specific payloads (only the relevant ones are filled) ---
    yesno: int | None = None
    labels: list[list[Any]] = Field(default_factory=list, description="[[label, score], ...] for scene ranking")
    boxes: list[Box] = Field(default_factory=list)
    regions: list[Region] = Field(default_factory=list)
    mask_url: str | None = None
    image_dimensions: list[int] | None = None  # [W, H]
    changed_fraction: float | None = None
    area_ha: float | None = None
    centroid_lonlat: list[float] | None = None
    representation_dim: int | None = None

    # --- score (passed through, never fabricated) ---
    score: float | None = None
    score_meaning: str | None = None

    # --- geospatial ---
    crs: str | None = None
    geospatial_available: bool = False
    geospatial_note: str | None = None

    # --- audit surface ---
    evidence: list[dict[str, Any]] = []
    verification: dict[str, Any] | None = None
    resolution: dict[str, Any] | None = None
    provenance: dict[str, Any] | None = None
    execution_trace: ExecutionTrace
    failures: list[str] = []
    warnings: list[str] = []


def _artifact_url(mask_path: str | None) -> str | None:
    if not mask_path:
        return None
    name = mask_path.replace("\\", "/").split("/")[-1]
    return f"/artifact?name={name}"


def _meta_of(payload: dict[str, Any]) -> dict[str, Any] | None:
    for key in ("image_meta", "t1_meta"):
        m = payload.get(key)
        if isinstance(m, dict):
            return m
    return None


def normalize(res: AnalyzeResult, *, latency_s: float | None = None) -> NormalizedResponse:
    """AnalyzeResult -> one flat, UI-ready schema. No field is invented."""
    payload: dict[str, Any] = res.result or {}
    code = res.routing.routing_code
    warnings: list[str] = list(res.validation_errors) + list(getattr(res, "geo_warnings", []) or [])
    failures: list[str] = list(payload.get("failures", []) or [])

    trace_steps = ["validate_input", "interpret_query", "route"]
    if res.routing.selected_specialists:
        trace_steps.append("specialist:" + ",".join(res.routing.selected_specialists))
    if res.evidence:
        trace_steps.append("evidence")
    if res.verification is not None:
        trace_steps.append("verify")
    if res.resolution is not None:
        trace_steps.append("resolve")

    out = NormalizedResponse(
        query=res.query,
        interpreted_task=res.interpretation.intent,
        task_code=code,
        execution_plan=res.routing.execution_order,
        ok=res.ok,
        latency_s=latency_s,
        model_used=_TASK_MODEL.get(code),
        evidence=[e.model_dump() if hasattr(e, "model_dump") else e for e in res.evidence],
        verification=res.verification.model_dump() if res.verification is not None else None,
        resolution=res.resolution.model_dump() if res.resolution is not None else None,
        provenance=res.provenance or None,
        execution_trace=ExecutionTrace(
            steps=trace_steps, routing_code=code, routing_rule=res.routing.routing_rule
        ),
        failures=failures,
        warnings=warnings,
    )

    if code in _TASK_CAVEAT:
        out.warnings.append(_TASK_CAVEAT[code])

    # --- not routed / blocked ---
    if not res.ok and not payload:
        out.answer = None
        out.failures = out.failures or res.errors
        if code == "NO_VQA_SPECIALIST":
            out.warnings.append(res.routing.routing_rule)
        elif code in ("NO_MATCH", "VALIDATION_FAILED"):
            out.warnings.append(res.routing.routing_rule)
        return out

    # --- geospatial (only from a real CRS + transform) ---
    meta = _meta_of(payload)
    if meta and meta.get("crs"):
        out.crs = str(meta.get("crs"))
        out.geospatial_available = True
    else:
        out.geospatial_note = (
            "geospatial coordinates unavailable because CRS/transform is missing"
        )

    # --- per-task mapping ---
    if code == "SINGLE_IMAGE_VQA":
        out.answer = payload.get("answer_text")
        out.yesno = payload.get("yesno")
        out.score = payload.get("score")
        out.score_meaning = payload.get("score_meaning")
        out.latency_s = out.latency_s or payload.get("execution_time_s")

    elif code == "SINGLE_IMAGE_GROUNDING":
        gstatus = payload.get("grounding_status")
        vstatus = payload.get("validation_status")
        out.image_dimensions = payload.get("image_dimensions")
        out.score = payload.get("score")
        out.score_meaning = payload.get("score_meaning")
        out.latency_s = out.latency_s or payload.get("execution_time_s")
        box = payload.get("bbox_xyxy")
        if box and vstatus == "PASS":
            geo = None
            for e in out.evidence:
                sr = (e or {}).get("spatial_region") or {}
                if "bbox_xyxy" in sr and sr.get("bbox_lonlat"):
                    geo = sr["bbox_lonlat"]
            out.boxes = [Box(xyxy_pixel=list(box), bbox_lonlat=geo, score=out.score)]
            out.mask_url = _artifact_url(payload.get("mask_path"))
            out.answer = "1 region grounded for the referring phrase."
        else:
            out.answer = (
                "No region could be grounded for this phrase — returned as an explicit "
                f"insufficient result (status: {gstatus or vstatus})."
            )
            out.warnings.append("no_grounded_region")

    elif code == "SINGLE_IMAGE_SCENE":
        ans = payload.get("answer") or {}
        out.answer = ans.get("top_label")
        out.labels = ans.get("ranking", [])
        out.score = ans.get("score")
        out.score_meaning = ans.get("score_meaning")

    elif code == "TEMPORAL" and res.interpretation.intent == "semantic-change":
        out.answer = payload.get("description")
        out.changed_fraction = payload.get("changed_fraction")
        out.area_ha = payload.get("changed_area_ha")
        out.mask_url = _artifact_url(payload.get("mask_path"))
        # the composed-baseline result carries no raster meta; infer geo-availability
        # from whether the regions got lon/lat boxes.
        if any((r or {}).get("bbox_lonlat") for r in payload.get("regions", []) or []):
            out.geospatial_available = True
            out.geospatial_note = None
        for r in payload.get("regions", []) or []:
            out.regions.append(
                Region(
                    region_id=r["region_id"], area_px=r["area_px"], area_ha=r.get("area_ha"),
                    bbox_pixel=list(r["bbox_pixel"]),
                    bbox_lonlat=list(r["bbox_lonlat"]) if r.get("bbox_lonlat") else None,
                    label=r.get("top_tag"), label_margin=r.get("tag_margin"),
                    low_margin=bool(r.get("low_margin")),
                )
            )
        out.warnings.append(
            "EXPERIMENTAL SEMANTIC BASELINE (ChangeFormer mask + RemoteCLIP tagging) — "
            "not a learned temporal VLM, not validated semantic reasoning."
        )

    elif code == "TEMPORAL":
        stats = payload.get("stats") or {}
        out.changed_fraction = stats.get("changed_fraction")
        out.area_ha = stats.get("changed_area_ha")
        c = stats.get("change_centroid_lonlat")
        out.centroid_lonlat = list(c) if c else None
        bb = stats.get("change_bbox_lonlat")
        if bb:
            out.boxes = [Box(xyxy_pixel=list(stats.get("change_bbox_native") or []), bbox_lonlat=list(bb),
                             label="changed area")]
        out.mask_url = _artifact_url(payload.get("mask_path"))
        prov = payload.get("provenance") or {}
        if prov.get("is_fallback") or (res.resolution and res.resolution.fallback_used):
            out.answer = (
                f"~{(out.changed_fraction or 0) * 100:.1f}% of the scene changed "
                "(image-difference FALLBACK — not ChangeFormer quality)."
            )
            out.warnings.append("SPECIALIST_DEGRADED: image-difference fallback was used, not ChangeFormer.")
        else:
            out.answer = f"~{(out.changed_fraction or 0) * 100:.1f}% of the scene changed between the two dates."

    elif code == "MULTIMODAL_REPR":
        rep = payload.get("representation") or {}
        out.representation_dim = rep.get("dim")
        out.model_used = (payload.get("model") or "croma").upper()
        out.answer = (
            f"Joint optical+SAR representation produced (dim {rep.get('dim')}). "
            "Representation-level only — no task-level answer is generated in this build."
        )

    return out
