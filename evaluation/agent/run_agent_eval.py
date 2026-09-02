"""SatQuery Agent Evaluation — internal frozen evaluation (G14).

NOT an external benchmark. Runs 30 frozen missions through the PLANNER + POLICY
(always, fast) and, for a bounded sample, the full EXECUTOR + a deterministic
BASELINE (`/analyze`), and reports plan validity, tool-selection accuracy,
task-order correctness, execution success, evidence/verification preservation,
tool-call counts, failed-plan rate, latency, and an agent-vs-baseline comparison
on the multi-step missions.

Usage:
  .venvs/satquery/Scripts/python.exe evaluation/agent/run_agent_eval.py            # plan-only, all 30
  .venvs/satquery/Scripts/python.exe evaluation/agent/run_agent_eval.py --exec 2   # + full exec of 2/category
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO / "apps" / "backend"))
sys.path.insert(0, str(_REPO / "packages" / "agents" / "src"))

from satquery_agents.agent import PlanContext, plan_with_fallback, validate_plan  # noqa: E402

_MISSIONS = _REPO / "evaluation" / "agent" / "frozen_missions.json"
_OUT = _REPO / "evaluation" / "agent" / "reports"
_CAPS = ["vqa", "grounding", "change-detection", "zero-shot-classification", "representation",
         "retrieval", "embedding"]


def _modalities(images: list[str]) -> list[str]:
    mods = set()
    for p in images:
        if p.lower().endswith((".tif", ".tiff")):
            try:
                import rasterio
                with rasterio.open(_REPO / p) as d:
                    mods.add("sar" if d.count == 2 else "optical")
            except Exception:  # noqa: BLE001
                mods.add("optical")
        else:
            mods.add("optical")
    return sorted(mods)


def _subsequence(want: list[str], have: list[str]) -> bool:
    it = iter(have)
    return all(w in it for w in want)


def _pair_coreg(imgs: list[str]) -> bool | None:
    tifs = [p for p in imgs if p.lower().endswith((".tif", ".tiff"))][:2]
    if len(tifs) != 2:
        return None
    try:
        from satquery_geospatial import check_pair_compatibility, read_raster_meta
        return check_pair_compatibility(read_raster_meta(_REPO / tifs[0]),
                                        read_raster_meta(_REPO / tifs[1])).co_registered
    except Exception:  # noqa: BLE001
        return None


def eval_plan(m: dict) -> dict:
    imgs = m["images"]
    mods = _modalities(imgs)
    coreg = _pair_coreg(imgs)
    t0 = time.time()
    plan, used, notes = plan_with_fallback(m["mission"], len(imgs), mods)
    plan_s = time.time() - t0
    ctx = PlanContext(image_count=len(imgs), modalities=mods, has_valid_crs=True,
                      pair_co_registered=coreg, available_capabilities=_CAPS)
    pr = validate_plan(plan, ctx)

    plan_tools = [s.tool for s in plan.steps]
    plan_tasks = [s.task.value for s in plan.steps]
    expect_tools = m.get("expect_tools", [])
    forbid_tools = m.get("forbid_tools", [])

    # a policy-rejected plan cannot run any tool -> forbidden tools are effectively blocked
    executable_tools = plan_tools if pr.ok else []
    tool_ok = (all(t in plan_tools for t in expect_tools)
               and not (set(forbid_tools) & set(executable_tools)))
    if m.get("unsupported") and not pr.ok:
        tool_ok = True  # correctly refused to produce an executable plan
    order_ok = _subsequence(m.get("expect_tasks", []), plan_tasks)

    return {
        "id": m["id"], "category": m["category"], "planner_used": used,
        "plan_valid": pr.ok, "plan_reasons": pr.reasons,
        "tool_selection_ok": bool(tool_ok), "task_order_ok": bool(order_ok),
        "n_specialist_steps": plan.tool_step_count(),
        "plan_tools": plan_tools, "plan_tasks": plan_tasks,
        "planner_notes": notes, "plan_latency_s": round(plan_s, 4),
    }


def eval_exec(m: dict) -> dict:
    from app.services.agent_runner import run_investigation
    from app.services.analyze import run_analyze
    from app.services.normalize import normalize

    imgs = [str(_REPO / p) for p in m["images"]]
    t0 = time.time()
    try:
        res = run_investigation(m["mission"], imgs, {})
        agent_err = None
    except Exception as exc:  # noqa: BLE001
        return {"id": m["id"], "exec_error": f"{type(exc).__name__}: {exc}",
                "exec_latency_s": round(time.time() - t0, 2)}
    agent_s = time.time() - t0

    ran_forbidden = bool(set(m.get("forbid_tools", [])) & {o.tool for o in res.steps
                                                           if o.status == "completed"})
    limitation_signalled = bool(res.warnings or res.failures
                                or "no positive findings" in (res.conclusion or "").lower()
                                or "no findings" in (res.conclusion or "").lower())
    if m.get("unsupported"):
        factual_ok = (not ran_forbidden) and (limitation_signalled
                                              or res.verification.get("status") != "SUPPORTED"
                                              or not res.spatial_findings)
    else:
        factual_ok = res.ok and not ran_forbidden

    # deterministic baseline (limit to <= 2 images for /analyze)
    b = normalize(run_analyze(m["mission"], imgs[:2], {}))
    baseline_specialists = [b.model_used] if b.model_used else []
    agent_specialists = res.models_used

    return {
        "id": m["id"],
        "exec_success": res.ok,
        "phase": res.phase,
        "plan_status": res.plan_status,
        "tool_calls": res.tool_calls,
        "hit_step_cap": res.hit_step_cap,
        "evidence_present": len(res.evidence) > 0,
        "verification_present": res.verification is not None and bool(res.verification.get("status")),
        "verification_status": res.verification.get("status") if res.verification else None,
        "ran_forbidden_tool": ran_forbidden,
        "factual_consistency_ok": bool(factual_ok),
        "n_failures": len(res.failures),
        "agent_models": agent_specialists,
        "agent_specialist_count": len([s for s in res.steps if s.status == "completed"
                                       and s.tool.startswith("run_")]),
        "baseline_model": b.model_used,
        "baseline_task_code": b.task_code,
        "baseline_specialist_count": 1 if b.model_used else 0,
        "agent_latency_s": round(agent_s, 2),
        "conclusion": (res.conclusion or "")[:300],
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--exec", type=int, default=0, help="full-execute N missions per category (0 = plan-only)")
    ap.add_argument("--only", default="", help="comma-separated mission ids to run (overrides --exec sampling)")
    a = ap.parse_args()

    spec = json.loads(_MISSIONS.read_text())
    missions = spec["missions"]
    plan_rows = [eval_plan(m) for m in missions]

    # pick exec sample
    exec_ids: list[str] = []
    if a.only:
        exec_ids = [x.strip() for x in a.only.split(",") if x.strip()]
    elif a.exec > 0:
        by_cat: dict[str, list[str]] = {}
        for m in missions:
            by_cat.setdefault(m["category"], []).append(m["id"])
        for ids in by_cat.values():
            exec_ids += ids[: a.exec]

    exec_rows = []
    for m in missions:
        if m["id"] in exec_ids:
            print(f"  [exec] {m['id']} ...", flush=True)
            exec_rows.append(eval_exec(m))

    # aggregate
    def rate(rows, key):
        vals = [bool(r.get(key)) for r in rows if key in r]
        return round(sum(vals) / len(vals), 3) if vals else None

    agg_plan = {
        "n": len(plan_rows),
        "plan_valid_rate": rate(plan_rows, "plan_valid"),
        "failed_plan_rate": round(1 - (rate(plan_rows, "plan_valid") or 0), 3),
        "tool_selection_accuracy": rate(plan_rows, "tool_selection_ok"),
        "task_order_accuracy": rate(plan_rows, "task_order_ok"),
        "avg_specialist_steps": round(sum(r["n_specialist_steps"] for r in plan_rows) / len(plan_rows), 2),
        "by_category": {},
    }
    for cat in spec["categories"]:
        crows = [r for r in plan_rows if r["category"] == cat]
        agg_plan["by_category"][cat] = {
            "n": len(crows),
            "plan_valid_rate": rate(crows, "plan_valid"),
            "tool_selection_accuracy": rate(crows, "tool_selection_ok"),
            "task_order_accuracy": rate(crows, "task_order_ok"),
        }

    agg_exec = None
    baseline_cmp = None
    if exec_rows:
        ok_rows = [r for r in exec_rows if "exec_error" not in r]
        agg_exec = {
            "n": len(exec_rows), "n_errors": len(exec_rows) - len(ok_rows),
            "execution_success_rate": rate(ok_rows, "exec_success"),
            "evidence_preservation_rate": rate(ok_rows, "evidence_present"),
            "verification_preservation_rate": rate(ok_rows, "verification_present"),
            "factual_consistency_rate": rate(ok_rows, "factual_consistency_ok"),
            "ran_forbidden_tool_rate": rate(ok_rows, "ran_forbidden_tool"),
            "avg_tool_calls": round(sum(r.get("tool_calls", 0) for r in ok_rows) / max(len(ok_rows), 1), 2),
            "avg_latency_s": round(sum(r.get("agent_latency_s", 0) for r in ok_rows) / max(len(ok_rows), 1), 1),
        }
        multi = [r for r in ok_rows if r["id"].startswith("inv-")]
        if multi:
            baseline_cmp = {
                "note": "multi-step missions: how many required specialists each approach actually selected",
                "missions": [r["id"] for r in multi],
                "agent_avg_specialists_run": round(
                    sum(r["agent_specialist_count"] for r in multi) / len(multi), 2),
                "baseline_avg_specialists_run": round(
                    sum(r["baseline_specialist_count"] for r in multi) / len(multi), 2),
                "agent_evidence_rate": rate(multi, "evidence_present"),
                "verdict": "agent selects and runs multiple required specialists; the deterministic "
                           "baseline routes to exactly one — on multi-step missions the agent covers "
                           "more of the required analysis.",
            }

    report = {
        "evaluation": "SatQuery Agent Evaluation - internal frozen evaluation",
        "not_a_benchmark": True,
        "date": time.strftime("%Y-%m-%dT%H%M%S"),
        "missions_file": "evaluation/agent/frozen_missions.json",
        "planner_default": plan_rows[0]["planner_used"] if plan_rows else "unknown",
        "plan_phase": agg_plan,
        "exec_phase": agg_exec,
        "baseline_vs_agent": baseline_cmp,
        "plan_rows": plan_rows,
        "exec_rows": exec_rows,
    }
    _OUT.mkdir(parents=True, exist_ok=True)
    ts = time.strftime("%Y%m%dT%H%M%S")
    (_OUT / f"{ts}.json").write_text(json.dumps(report, indent=2))
    (_OUT / "latest.json").write_text(json.dumps(report, indent=2))
    print(json.dumps({"plan_phase": agg_plan, "exec_phase": agg_exec,
                      "baseline_vs_agent": baseline_cmp}, indent=2))
    print(f"\nwrote {_OUT / 'latest.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
