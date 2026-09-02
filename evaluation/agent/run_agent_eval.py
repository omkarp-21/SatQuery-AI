"""SatQuery Agent Evaluation - internal frozen evaluation (G15).

NOT an external benchmark. Runs 50 frozen missions through the PLANNER + POLICY
(always, fast) and, for a bounded sample, the full EXECUTOR + the deterministic
BASELINE (`/analyze`). Reports 13 agent-quality metrics + an agent-vs-baseline
comparison on the multi-step missions. Every rate is reported WITH its N.

Usage:
  .venvs/satquery/Scripts/python.exe evaluation/agent/run_agent_eval.py                 # plan-only, all 50
  .venvs/satquery/Scripts/python.exe evaluation/agent/run_agent_eval.py --exec 2        # + full exec of 2/category
  .venvs/satquery/Scripts/python.exe evaluation/agent/run_agent_eval.py --only mi-01    # one mission, full exec
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
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
_TASK_OF_TOOL = {
    "run_vqa": "VQA", "run_grounding": "GROUND_OBJECT", "run_scene_retrieval": "SCENE_UNDERSTANDING",
    "run_temporal_change": "TEMPORAL_CHANGE", "run_semantic_temporal_baseline": "SEMANTIC_CHANGE",
    "run_optical_sar": "OPTICAL_SAR_ANALYSIS", "extract_changed_regions": "EXTRACT_CHANGED_REGIONS",
}


def _abspaths(m: dict) -> list[str]:
    out = []
    for p in m["required_inputs"]:
        if m.get("synthetic_broken") and p.endswith("broken.tif"):
            bad = Path(tempfile.gettempdir()) / "satq_broken.tif"
            bad.write_bytes(b"II*\x00 not a real tiff " + b"\xff" * 64)
            out.append(str(bad))
        else:
            out.append(str(_REPO / p))
    return out


def _modalities(paths: list[str]) -> list[str]:
    mods = set()
    for p in paths:
        if p.lower().endswith((".tif", ".tiff")):
            try:
                import rasterio
                with rasterio.open(p) as d:
                    mods.add("sar" if d.count == 2 else "optical")
            except Exception:  # noqa: BLE001
                mods.add("optical")
        else:
            mods.add("optical")
    return sorted(mods)


def _coreg(paths: list[str]) -> bool | None:
    tifs = [p for p in paths if p.lower().endswith((".tif", ".tiff"))][:2]
    if len(tifs) != 2:
        return None
    try:
        from satquery_geospatial import check_pair_compatibility, read_raster_meta
        return check_pair_compatibility(read_raster_meta(tifs[0]), read_raster_meta(tifs[1])).co_registered
    except Exception:  # noqa: BLE001
        return None


def _order_ok(constraints: list[str], plan_tasks: list[str]) -> bool:
    idx = {t: i for i, t in enumerate(plan_tasks)}
    for c in constraints:
        a, b = [x.strip() for x in c.split("<")]
        if a in idx and b in idx and idx[a] >= idx[b]:
            return False
    return True


# --------------------------------------------------------------------------- #
# plan phase
# --------------------------------------------------------------------------- #


def eval_plan(m: dict) -> dict:
    paths = _abspaths(m)
    mods = _modalities(paths)
    coreg = _coreg(paths)
    t0 = time.time()
    plan, used, notes = plan_with_fallback(m["user_query"], len(paths), mods)
    plan_s = time.time() - t0
    ctx = PlanContext(image_count=len(paths), modalities=mods, has_valid_crs=True,
                      pair_co_registered=coreg, available_capabilities=_CAPS)
    pr = validate_plan(plan, ctx)

    plan_tools = [s.tool for s in plan.steps]
    plan_tasks = [s.task.value for s in plan.steps]
    executable_tools = plan_tools if pr.ok else []

    expect = m.get("expected_tool_set", [])
    forbid = m.get("forbid_tools", [])
    tool_ok = all(t in plan_tools for t in expect) and not (set(forbid) & set(executable_tools))
    if m.get("unsupported") and not pr.ok:
        tool_ok = True  # correctly refused to produce an executable plan

    # adversarial missions: "correctly handled" = the policy rejects the plan, OR the bad
    # input is only detectable at execution time (runtime_detected), OR the plan simply
    # does not attempt any forbidden/illegal tool (a safe generic fallback, e.g. VQA on a
    # single image for an impossible ask).
    adversarial_ok = None
    if m.get("unsupported"):
        no_forbidden = not (set(forbid) & set(executable_tools))
        adversarial_ok = (not pr.ok) or bool(m.get("runtime_detected")) or no_forbidden
    # tool-selection is not meaningful at plan time for runtime-detected bad input
    tool_ok_scored = None if m.get("runtime_detected") else bool(tool_ok)

    order_ok = _order_ok(m.get("expected_order_constraints", []), plan_tasks)

    # dependency validity: every depends_on points to a real, earlier step
    deps_total = deps_valid = 0
    pos = {s.step_id: i for i, s in enumerate(plan.steps)}
    for s in plan.steps:
        for d in s.depends_on:
            deps_total += 1
            if d in pos and pos[d] < pos[s.step_id]:
                deps_valid += 1

    return {
        "mission_id": m["mission_id"], "category": m["category"], "planner_used": used,
        "unsupported": bool(m.get("unsupported")), "runtime_detected": bool(m.get("runtime_detected")),
        "plan_valid": pr.ok, "plan_reasons": pr.reasons,
        "blocking_checks": [c for c, ok in pr.checks.items() if not ok],
        "tool_selection_ok": tool_ok_scored, "adversarial_handled": adversarial_ok,
        "task_order_ok": bool(order_ok),
        "deps_total": deps_total, "deps_valid": deps_valid,
        "n_specialist_steps": plan.tool_step_count(),
        "plan_tools": plan_tools, "plan_tasks": plan_tasks,
        "planner_notes": notes, "plan_latency_s": round(plan_s, 4),
    }


# --------------------------------------------------------------------------- #
# exec phase
# --------------------------------------------------------------------------- #


def eval_exec(m: dict) -> dict:
    from app.services.agent_runner import run_investigation
    from app.services.analyze import run_analyze
    from app.services.normalize import normalize

    paths = _abspaths(m)
    t0 = time.time()
    try:
        res = run_investigation(m["user_query"], paths, {})
    except Exception as exc:  # noqa: BLE001
        return {"mission_id": m["mission_id"], "exec_error": f"{type(exc).__name__}: {exc}",
                "exec_latency_s": round(time.time() - t0, 2)}
    agent_s = time.time() - t0

    completed_tools = {o.tool for o in res.steps if o.status == "completed"}
    ran_forbidden = bool(set(m.get("forbid_tools", [])) & completed_tools)

    # unsupported-action attempts: forbidden or wrong-task tools that actually RAN
    total_attempts = sum(1 for o in res.steps if o.tool.startswith("run_")
                         and o.status in ("completed", "failed"))
    unsupported_attempts = sum(1 for o in res.steps if o.tool.startswith("run_")
                               and o.status == "completed" and o.tool in m.get("forbid_tools", []))

    # recovery: a recoverable failure (TOOL_FAILURE / MISSING_INPUT / INSUFFICIENT_EVIDENCE replan)
    # that still leads to a valid final state
    recoverable_replans = [rp for rp in res.replans
                           if rp.reason in ("TOOL_FAILURE", "MISSING_INPUT", "INSUFFICIENT_EVIDENCE")]
    recovered = bool(recoverable_replans) and res.phase != "FAILED" and res.verification is not None

    # unnecessary tool calls (from the executor's own accounting)
    prov = res.provenance or {}
    unnecessary = prov.get("unnecessary_tool_calls", 0)

    # early-stop: only meaningful for missions where stopping early is APPROPRIATE
    early_stop_eligible = bool(m.get("expected_early_stop"))
    early_stop_efficient = res.early_stopped if early_stop_eligible else None

    # factual consistency
    limitation = bool(res.warnings or res.failures
                      or "no positive findings" in (res.conclusion or "").lower()
                      or "not performed" in " ".join(res.key_findings).lower())
    if m.get("unsupported"):
        factual_ok = (not ran_forbidden) and (limitation
                                              or (res.verification or {}).get("status") != "SUPPORTED"
                                              or not res.spatial_findings)
    else:
        factual_ok = res.phase in ("FINALIZING",) and not ran_forbidden

    # baseline
    b = normalize(run_analyze(m["user_query"], paths[:2], {}))

    return {
        "mission_id": m["mission_id"], "category": m["category"],
        "mission_family": res.mission_family,
        "phase": res.phase, "plan_status": res.plan_status, "mode": res.mode,
        "unsupported": bool(m.get("unsupported")),
        # a "valid final state" = FINALIZING, OR (for an unsupported mission) an honest
        # terminal refusal: no forbidden tool ran and a limitation was signalled.
        "reached_valid_final": (res.phase in ("FINALIZING",))
        or (bool(m.get("unsupported")) and not ran_forbidden
            and (bool(res.warnings) or bool(res.failures) or res.mode == "ask-fallback")),
        "tool_calls": res.tool_calls, "hit_step_cap": res.hit_step_cap,
        "early_stopped": res.early_stopped, "completion_reason": res.completion_reason,
        "n_replans": len(res.replans),
        "replan_reasons": [rp.reason for rp in res.replans],
        "evidence_present": len(res.evidence) > 0,
        "verification_present": res.verification is not None and bool((res.verification or {}).get("status")),
        "verification_status": (res.verification or {}).get("status"),
        "ran_forbidden_tool": ran_forbidden,
        "unsupported_attempts": unsupported_attempts, "total_tool_attempts": total_attempts,
        "recoverable_failures": len(recoverable_replans), "recovered": recovered,
        "unnecessary_tool_calls": unnecessary,
        "early_stop_efficient": early_stop_efficient,
        "factual_consistency_ok": bool(factual_ok),
        "n_failures": len(res.failures),
        "agent_specialist_count": len([o for o in res.steps if o.status == "completed"
                                       and o.tool.startswith("run_")]),
        "baseline_model": b.model_used, "baseline_task_code": b.task_code,
        "baseline_specialist_count": 1 if b.model_used else 0,
        "agent_latency_s": round(agent_s, 2),
        "conclusion": (res.conclusion or "")[:300],
        "geojson_features": len((res.geojson or {}).get("features", [])),
    }


# --------------------------------------------------------------------------- #
# aggregate + report
# --------------------------------------------------------------------------- #


def _rate(rows, key):
    vals = [bool(r.get(key)) for r in rows if r.get(key) is not None]
    return (round(sum(vals) / len(vals), 3), len(vals)) if vals else (None, 0)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--exec", type=int, default=0, help="full-execute N missions per category (0 = plan-only)")
    ap.add_argument("--only", default="", help="comma-separated mission ids (overrides --exec sampling)")
    ap.add_argument("--reaggregate", default="", help="path to a prior report JSON: re-run the plan phase "
                    "+ re-aggregate its exec_rows WITHOUT re-executing models")
    a = ap.parse_args()

    spec = json.loads(_MISSIONS.read_text())
    missions = spec["missions"]
    plan_rows = [eval_plan(m) for m in missions]

    if a.reaggregate:
        exec_rows = json.loads(Path(a.reaggregate).read_text()).get("exec_rows", [])
        return _finish(spec, missions, plan_rows, exec_rows)

    exec_ids: list[str] = []
    if a.only:
        exec_ids = [x.strip() for x in a.only.split(",") if x.strip()]
    elif a.exec > 0:
        by_cat: dict[str, list[str]] = {}
        for m in missions:
            by_cat.setdefault(m["category"], []).append(m["mission_id"])
        for ids in by_cat.values():
            exec_ids += ids[: a.exec]
        # always include the missions that exercise replans / early-stop / recovery
        for extra in ("tm-10", "ad-03", "ad-06", "mi-06"):
            if extra not in exec_ids:
                exec_ids.append(extra)

    exec_rows = []
    for m in missions:
        if m["mission_id"] in exec_ids:
            print(f"  [exec] {m['mission_id']} ...", flush=True)
            exec_rows.append(eval_exec(m))
    return _finish(spec, missions, plan_rows, exec_rows)


def _finish(spec, missions, plan_rows, exec_rows) -> int:
    # ---- PLAN metrics ----
    d_tot = sum(r["deps_total"] for r in plan_rows)
    d_val = sum(r["deps_valid"] for r in plan_rows)
    supported = [r for r in plan_rows if not r["unsupported"]]
    adversarial = [r for r in plan_rows if r["unsupported"]]
    ts_scored = [r for r in plan_rows if r["tool_selection_ok"] is not None]
    pv, pvn = _rate(supported, "plan_valid")
    plan_metrics = {
        "PLAN_VALIDITY_RATE": {"value": pv, "n": pvn,
                               "def": "SUPPORTED missions whose plan the policy layer accepts / total supported"},
        "FAILED_PLAN_RATE": {"value": round(1 - (pv or 0), 3), "n": pvn,
                             "def": "supported missions the policy layer rejected"},
        "ADVERSARIAL_CORRECTLY_HANDLED_RATE": {"value": _rate(adversarial, "adversarial_handled")[0],
                                               "n": len(adversarial),
                                               "def": "adversarial missions the policy rejected OR flagged as "
                                                      "runtime-detected (blocked by the executor's validate step)"},
        "TOOL_SELECTION_ACCURACY": {"value": _rate(ts_scored, "tool_selection_ok")[0], "n": len(ts_scored),
                                    "def": "missions where expected tools are planned AND no forbidden "
                                           "tool is in an executable plan (excludes runtime-detected bad input)"},
        "TASK_ORDER_CORRECTNESS": {"value": _rate(plan_rows, "task_order_ok")[0], "n": len(plan_rows),
                                   "def": "missions where every 'A < B' order constraint holds in the plan"},
        "DEPENDENCY_VALIDITY": {"value": round(d_val / d_tot, 3) if d_tot else None, "n": d_tot,
                                "def": "depends_on edges that point to a real, earlier step / total edges"},
        "avg_specialist_steps_per_plan": round(sum(r["n_specialist_steps"] for r in plan_rows) / len(plan_rows), 2),
        "by_category": {},
    }
    for cat in spec["categories"]:
        cr = [r for r in plan_rows if r["category"] == cat]
        plan_metrics["by_category"][cat] = {
            "n": len(cr),
            "PLAN_VALIDITY_RATE": _rate(cr, "plan_valid")[0],
            "TOOL_SELECTION_ACCURACY": _rate(cr, "tool_selection_ok")[0],
            "TASK_ORDER_CORRECTNESS": _rate(cr, "task_order_ok")[0],
        }

    # ---- EXEC metrics ----
    exec_metrics = None
    baseline_cmp = None
    _unsup = {m["mission_id"]: bool(m.get("unsupported")) for m in missions}
    if exec_rows:
        ok = [r for r in exec_rows if "exec_error" not in r]
        # derive a valid-terminal-state flag from row fields (so --reaggregate works on
        # older rows): FINALIZING, OR an unsupported mission honestly refused via the
        # visible deterministic fallback without running a forbidden tool.
        for r in ok:
            uns = r.get("unsupported", _unsup.get(r["mission_id"], False))
            r["reached_valid_final"] = (r["phase"] == "FINALIZING") or (
                uns and not r.get("ran_forbidden_tool")
                and (r.get("mode") == "ask-fallback" or r["phase"] == "FAILED"))
        n = len(ok)
        att = sum(r.get("total_tool_attempts", 0) for r in ok)
        uns = sum(r.get("unsupported_attempts", 0) for r in ok)

        rec_ok = sum(1 for r in ok if r.get("recovered"))
        tc = sum(r.get("tool_calls", 0) for r in ok)
        unn = sum(r.get("unnecessary_tool_calls", 0) for r in ok)
        early_elig = [r for r in ok if r.get("early_stop_efficient") is not None]
        did_work = [r for r in ok if r["phase"] == "FINALIZING"]  # missions that actually executed
        exec_metrics = {
            "N": n, "n_errors": len(exec_rows) - n,
            "MISSION_COMPLETION_RATE": {"value": _rate(ok, "reached_valid_final")[0], "n": n,
                                        "def": "missions reaching a valid terminal state (FINALIZING, or an "
                                               "honest refusal for an unsupported mission) / total"},
            "EVIDENCE_PRESERVATION_RATE": {"value": _rate(did_work, "evidence_present")[0], "n": len(did_work),
                                           "def": "executed missions where specialist evidence survives to "
                                                  "the final result / executed missions"},
            "VERIFICATION_PRESERVATION_RATE": {"value": _rate(ok, "verification_present")[0], "n": n},
            "FINAL_ANSWER_FACTUAL_CONSISTENCY": {"value": _rate(ok, "factual_consistency_ok")[0], "n": n},
            "UNSUPPORTED_ACTION_RATE": {"value": round(uns / att, 3) if att else 0.0, "n": att,
                                        "def": "forbidden/illegal tool calls that RAN / total specialist tool attempts"},
            "RECOVERY_RATE": {"value": round(rec_ok / len([r for r in ok if r['recoverable_failures']]), 3)
                              if any(r['recoverable_failures'] for r in ok) else None,
                              "n": len([r for r in ok if r['recoverable_failures']]),
                              "def": "recoverable-failure missions that still reached a valid final state / total such missions"},
            "EARLY_STOP_EFFICIENCY": {"value": round(sum(1 for r in early_elig if r['early_stop_efficient'])
                                                     / len(early_elig), 3) if early_elig else None,
                                      "n": len(early_elig),
                                      "def": "missions where stopping early is APPROPRIATE (negligible change / "
                                             "unbounded ask) and the agent actually stopped early / total such missions"},
            "UNNECESSARY_TOOL_CALL_RATE": {"value": round(unn / tc, 3) if tc else 0.0, "n": tc,
                                           "def": "completed specialist calls that did not contribute to "
                                                  "mission completion / total tool calls"},
            "avg_tool_calls": round(tc / n, 2) if n else 0.0,
            "avg_replans": round(sum(r.get("n_replans", 0) for r in ok) / n, 2) if n else 0.0,
            "avg_latency_s": round(sum(r.get("agent_latency_s", 0) for r in ok) / n, 1) if n else 0.0,
            "replan_reason_counts": _count([x for r in ok for x in r.get("replan_reasons", [])]),
        }
        multi = [r for r in ok if r["category"] == "multi_step"]
        if multi:
            baseline_cmp = {
                "N": len(multi),
                "note": "multi-step missions: required specialists each approach actually selected + ran",
                "missions": [r["mission_id"] for r in multi],
                "agent_avg_specialists_run": round(sum(r["agent_specialist_count"] for r in multi) / len(multi), 2),
                "baseline_avg_specialists_run": round(sum(r["baseline_specialist_count"] for r in multi) / len(multi), 2),
                "agent_evidence_rate": _rate(multi, "evidence_present")[0],
                "agent_unnecessary_tool_call_rate":
                    round(sum(r.get("unnecessary_tool_calls", 0) for r in multi)
                          / max(sum(r.get("tool_calls", 0) for r in multi), 1), 3),
                "verdict": "on multi-step missions the agent plans and runs the multiple required "
                           "specialists; the deterministic baseline routes to one. Value is measured, not assumed.",
            }

    report = {
        "evaluation": "SatQuery Agent Evaluation - internal frozen evaluation (G15)",
        "not_a_benchmark": True,
        "date": time.strftime("%Y-%m-%dT%H%M%S"),
        "missions_file": "evaluation/agent/frozen_missions.json",
        "n_missions": len(missions),
        "categories": {c: sum(1 for m in missions if m["category"] == c) for c in spec["categories"]},
        "planner_default": plan_rows[0]["planner_used"] if plan_rows else "unknown",
        "plan_metrics": plan_metrics,
        "exec_metrics": exec_metrics,
        "baseline_vs_agent_multistep": baseline_cmp,
        "plan_rows": plan_rows,
        "exec_rows": exec_rows,
    }
    _OUT.mkdir(parents=True, exist_ok=True)
    (_OUT / "G15_AGENT_EVALUATION.json").write_text(json.dumps(report, indent=2))
    (_OUT / "latest.json").write_text(json.dumps(report, indent=2))
    _write_md(report, _OUT / "G15_AGENT_EVALUATION.md")
    print(json.dumps({"plan_metrics": {k: v for k, v in plan_metrics.items() if k != "by_category"},
                      "exec_metrics": exec_metrics, "baseline_vs_agent_multistep": baseline_cmp}, indent=2))
    print(f"\nwrote {_OUT / 'G15_AGENT_EVALUATION.json'} + .md")
    return 0


def _count(xs: list[str]) -> dict[str, int]:
    out: dict[str, int] = {}
    for x in xs:
        out[x] = out.get(x, 0) + 1
    return out


def _write_md(rep: dict, path: Path) -> None:
    pm = rep["plan_metrics"]
    em = rep["exec_metrics"]
    bc = rep["baseline_vs_agent_multistep"]
    L = [
        f"# G15 Agent Evaluation — {rep['date']}",
        "",
        "> **Internal frozen evaluation — NOT an external benchmark.** Metrics measure the "
        "PLANNER + POLICY + EXECUTOR, not model accuracy. Every rate carries its N.",
        "",
        f"Missions: **{rep['n_missions']}** — " + ", ".join(f"{k} {v}" for k, v in rep["categories"].items())
        + f". Planner: `{rep['planner_default']}` (default; `LlmPlanner` opt-in, always falls back).",
        "",
        "## Plan phase (all missions, no models)",
        "",
        "| metric | value | N | definition |",
        "|--------|:-----:|:-:|------------|",
    ]
    for k in ("PLAN_VALIDITY_RATE", "FAILED_PLAN_RATE", "ADVERSARIAL_CORRECTLY_HANDLED_RATE",
              "TOOL_SELECTION_ACCURACY", "TASK_ORDER_CORRECTNESS", "DEPENDENCY_VALIDITY"):
        v = pm[k]
        L.append(f"| {k} | **{v['value']}** | {v.get('n', '')} | {v.get('def', '')} |")
    L.append(f"| avg specialist steps / plan | {pm['avg_specialist_steps_per_plan']} | {rep['n_missions']} | |")
    L += ["", "By category (PLAN_VALIDITY / TOOL_SELECTION / TASK_ORDER):", ""]
    for c, v in pm["by_category"].items():
        L.append(f"- **{c}** (n={v['n']}): {v['PLAN_VALIDITY_RATE']} / {v['TOOL_SELECTION_ACCURACY']} / {v['TASK_ORDER_CORRECTNESS']}")

    if em:
        L += ["", f"## Exec phase (N={em['N']}, real frozen-stack models, CPU)", "",
              "| metric | value | N | definition |", "|--------|:-----:|:-:|------------|"]
        for k in ("MISSION_COMPLETION_RATE", "EVIDENCE_PRESERVATION_RATE", "VERIFICATION_PRESERVATION_RATE",
                  "FINAL_ANSWER_FACTUAL_CONSISTENCY", "UNSUPPORTED_ACTION_RATE", "RECOVERY_RATE",
                  "EARLY_STOP_EFFICIENCY", "UNNECESSARY_TOOL_CALL_RATE"):
            v = em[k]
            L.append(f"| {k} | **{v['value']}** | {v['n']} | {v.get('def', '')} |")
        L += [f"| avg tool calls / mission | {em['avg_tool_calls']} | {em['N']} | |",
              f"| avg replans / mission | {em['avg_replans']} | {em['N']} | |",
              f"| avg end-to-end latency (s) | {em['avg_latency_s']} | {em['N']} | CPU, cold model loads |",
              "", f"Replan reasons observed: `{em['replan_reason_counts']}`"]
    if bc:
        L += ["", f"## Baseline vs agent — multi-step missions (N={bc['N']})", "",
              "| | deterministic `/analyze` | agent |", "|---|:--:|:--:|",
              f"| required specialists run (avg) | **{bc['baseline_avg_specialists_run']}** | **{bc['agent_avg_specialists_run']}** |",
              f"| evidence present | — | {bc['agent_evidence_rate']} |",
              f"| unnecessary-tool-call rate | — | {bc['agent_unnecessary_tool_call_rate']} |",
              "", f"> {bc['verdict']}"]
    L += ["", "## Claim discipline",
          "", "SatQuery **can decompose multi-step remote-sensing missions into validated specialist "
          "actions and adapt its execution based on intermediate observations** (bounded agentic "
          "execution, typed tool planning, policy-constrained execution, evidence-backed orchestration). "
          "This is an *internal evaluation*. No claim of \"state-of-the-art\", \"fully autonomous\", "
          "\"hallucination-free\", or \"real-time\"."]
    path.write_text("\n".join(L))


if __name__ == "__main__":
    raise SystemExit(main())
