"""G16 - REAL LLM AGENT VALIDATION + MISSION EVALUATION.

Two planning arms over the SAME frozen 50-mission set:

  ARM A  RuleBasedPlanner        (deterministic; the G15 default / fallback)
  ARM B  LlmPlanner (local Qwen2-VL-2B, text-only, schema-constrained + repair)

Plan phase  -> 10 planning metrics per arm, each WITH N (Part 5), scored
               semantically (Part 6) not against one gold sequence.
Exec phase  -> >= 20 real-model missions, BASELINE (/analyze) vs LLM-AGENT
               (LlmPlanner + policy guard + observe/replan executor) (Part 7/8).
Adversarial -> the 10 adversarial missions, per arm (Part 9).

The LLM is slow on CPU, so raw completions are generated ONCE via the persistent
`planner_infer.py --serve` process and cached; scoring/aggregation is then
instant and re-runnable with `--reaggregate`.

Usage:
  # 1. generate + cache the LLM raw outputs (slow, ~minutes/mission on CPU):
  SATQUERY_PLANNER_PERSISTENT=1 .venvs/satquery/Scripts/python.exe evaluation/agent/run_g16_eval.py --llm-cache
  # 2. score both arms + write the report (fast):
  .venvs/satquery/Scripts/python.exe evaluation/agent/run_g16_eval.py --plan
  # 3. real-model execution comparison (slow, real specialists):
  .venvs/satquery/Scripts/python.exe evaluation/agent/run_g16_eval.py --exec 20
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO / "apps" / "backend"))
sys.path.insert(0, str(_REPO / "packages" / "agents" / "src"))
sys.path.insert(0, str(_REPO / "evaluation" / "agent"))

from satquery_agents.agent import (  # noqa: E402
    LlmPlanner,
    PlanContext,
    RuleBasedPlanner,
    build_plan_from_raw,
    plan_with_fallback_ex,
    validate_plan,
)

from plan_scorer import score_plan  # noqa: E402
from run_agent_eval import _abspaths, _coreg, _modalities, _CAPS  # noqa: E402

_MISSIONS = _REPO / "evaluation" / "agent" / "frozen_missions.json"
_OUT = _REPO / "evaluation" / "agent" / "reports"
_RAW_CACHE = _OUT / "G16_llm_raw_cache.json"


# --------------------------------------------------------------------------- #
# LLM raw-output cache
# --------------------------------------------------------------------------- #


def llm_cache_build(missions: list[dict], *, only: list[str] | None, redo: bool) -> dict:
    cache = json.loads(_RAW_CACHE.read_text()) if _RAW_CACHE.exists() else {}
    # generous but BOUNDED: a plan that needs > 7 min on this CPU host is unusable
    pl = LlmPlanner(timeout_s=430.0)  # SATQUERY_PLANNER_PERSISTENT=1 -> one long-lived model process
    from satquery_agents.agent.prompts import build_prompt

    todo = [m for m in missions
            if (only is None or m["mission_id"] in only)
            and (redo or m["mission_id"] not in cache)]
    print(f"generating {len(todo)} LLM completions (cache has {len(cache)})", flush=True)
    for i, m in enumerate(todo, 1):
        paths = _abspaths(m)
        mods = _modalities(paths)
        prompt = build_prompt(m["user_query"], len(paths), mods, compact=pl.compact)
        t0 = time.time()
        try:
            raw, gen_s = pl._local_qwen(prompt)  # noqa: SLF001 - eval harness
            err = None
        except Exception as exc:  # noqa: BLE001
            raw, gen_s, err = "", None, f"{type(exc).__name__}: {exc}"
        cache[m["mission_id"]] = {
            "user_query": m["user_query"], "image_count": len(paths), "modalities": mods,
            "raw": raw, "gen_s": gen_s, "error": err, "wall_s": round(time.time() - t0, 1),
        }
        _RAW_CACHE.write_text(json.dumps(cache, indent=1))  # checkpoint every mission
        print(f"  [{i}/{len(todo)}] {m['mission_id']} gen={gen_s}s wall={cache[m['mission_id']]['wall_s']}s"
              + (f" ERR {err}" if err else ""), flush=True)
    return cache


# --------------------------------------------------------------------------- #
# plan-phase scoring (per arm)
# --------------------------------------------------------------------------- #


def _score_one(m: dict, plan, policy_ok: bool, image_count: int, mods: list[str]) -> dict:
    sc = score_plan(plan, m, policy_ok=policy_ok, image_count=image_count, modalities=mods)
    sc["mission_id"] = m["mission_id"]
    sc["category"] = m["category"]
    sc["unsupported"] = bool(m.get("unsupported"))
    sc["runtime_detected"] = bool(m.get("runtime_detected"))
    sc["policy_ok"] = policy_ok
    # plan-phase unsupported-action is not meaningful when the bad input is only
    # detectable at execution (e.g. a corrupt raster) - the EXECUTOR catches it.
    if sc["runtime_detected"]:
        sc["unsupported_action"] = None
    return sc


def plan_rows_rule(missions: list[dict]) -> list[dict]:
    rows = []
    for m in missions:
        paths = _abspaths(m)
        mods = _modalities(paths)
        t0 = time.time()
        plan, used, notes, _att = plan_with_fallback_ex(m["user_query"], len(paths), mods,
                                                        planner=RuleBasedPlanner())
        lat = time.time() - t0
        ctx = PlanContext(image_count=len(paths), modalities=mods, has_valid_crs=True,
                          pair_co_registered=_coreg(paths), available_capabilities=_CAPS)
        pr = validate_plan(plan, ctx)
        row = _score_one(m, plan, pr.ok, len(paths), mods)
        row.update(arm="rule", planner_used=used, plan_latency_s=round(lat, 4),
                   policy_reasons=pr.reasons,
                   blocking_checks=[c for c, ok in pr.checks.items() if not ok],
                   parse_status="n/a", schema_status="n/a", repair_status="n/a",
                   final_source="rule_based", fallback=False)
        rows.append(row)
    return rows


def plan_rows_llm(missions: list[dict], cache: dict) -> list[dict]:
    """Rows for the LLM arm. ONLY missions the LLM actually attempted (a cache
    entry exists) are scored — the metric denominator must be what the LLM did,
    not padded with rule-planner results for un-run missions. `_llm_attempted`
    on each row is True; the report states how many of the 50 were not attempted."""
    rows = []
    for m in missions:
        mid = m["mission_id"]
        c = cache.get(mid)
        if c is None:
            continue  # not attempted on this (CPU-bounded) run -> excluded, not padded
        paths = _abspaths(m)
        mods = _modalities(paths)
        ctx = PlanContext(image_count=len(paths), modalities=mods, has_valid_crs=True,
                          pair_co_registered=_coreg(paths), available_capabilities=_CAPS)
        if c.get("error") or not c.get("raw"):
            # LLM call errored / timed out -> deterministic fallback (Part 14). This
            # IS an LLM-arm outcome (the LLM was attempted), so it is scored.
            rb, used, notes, _ = plan_with_fallback_ex(m["user_query"], len(paths), mods,
                                                       planner=RuleBasedPlanner())
            pr = validate_plan(rb, ctx)
            row = _score_one(m, rb, pr.ok, len(paths), mods)
            row.update(arm="llm", planner_used="rule_based_fallback", _llm_attempted=True,
                       plan_latency_s=None, gen_s=c.get("gen_s"),
                       parse_status="no_output", schema_status="invalid", repair_status="none",
                       final_source="rule_based_fallback", fallback=True,
                       fallback_reason=c.get("error") or "no_llm_output",
                       policy_reasons=pr.reasons,
                       blocking_checks=[ck for ck, ok in pr.checks.items() if not ok])
            rows.append(row)
            continue
        plan, att = build_plan_from_raw(c["raw"], image_count=len(paths), gen_s=c.get("gen_s"))
        if plan is None:
            rb, *_ = plan_with_fallback_ex(m["user_query"], len(paths), mods, planner=RuleBasedPlanner())
            pr = validate_plan(rb, ctx)
            row = _score_one(m, rb, pr.ok, len(paths), mods)
            row.update(arm="llm", planner_used="rule_based_fallback", _llm_attempted=True,
                       plan_latency_s=None, gen_s=c.get("gen_s"), parse_status=att.parse_status,
                       schema_status=att.schema_status, repair_status=att.repair_status,
                       repairs=att.repairs, schema_errors=att.schema_errors,
                       final_source="rule_based_fallback", fallback=True,
                       fallback_reason=att.fallback_reason,
                       policy_reasons=pr.reasons,
                       blocking_checks=[ck for ck, ok in pr.checks.items() if not ok])
            rows.append(row)
            continue
        pr = validate_plan(plan, ctx)
        row = _score_one(m, plan, pr.ok, len(paths), mods)
        row.update(arm="llm", _llm_attempted=True,
                   planner_used=("llm_repaired" if att.final_source == "llm_repaired" else "llm"),
                   plan_latency_s=c.get("gen_s"), gen_s=c.get("gen_s"),
                   parse_status=att.parse_status, schema_status=att.schema_status,
                   repair_status=att.repair_status, repairs=att.repairs,
                   final_source=att.final_source, fallback=False,
                   policy_reasons=pr.reasons,
                   blocking_checks=[ck for ck, ok in pr.checks.items() if not ok])
        rows.append(row)
    return rows


# --------------------------------------------------------------------------- #
# metric aggregation (per arm)  -- Part 5
# --------------------------------------------------------------------------- #


def _rate(rows, key):
    vals = [bool(r[key]) for r in rows if r.get(key) is not None]
    return (round(sum(vals) / len(vals), 3), len(vals)) if vals else (None, 0)


def arm_metrics(rows: list[dict]) -> dict:
    supported = [r for r in rows if not r["unsupported"]]
    adversarial = [r for r in rows if r["unsupported"]]
    d_tot = sum(r["deps_total"] for r in rows)
    d_val = sum(r["deps_valid"] for r in rows)
    exec_rows = [r for r in rows if r["policy_ok"]]  # plans that would actually run
    lat = [r["plan_latency_s"] for r in rows if r.get("plan_latency_s") is not None]
    return {
        "N": len(rows),
        "N_supported": len(supported),
        "PLAN_VALIDITY_RATE": _pack(_rate(supported, "semantic_valid"),
                                    "SUPPORTED missions: plan is schema-valid, policy-accepted, and "
                                    "semantically valid (required tools present, deps + order + modality "
                                    "ok, verify + finalize present)"),
        "SCHEMA_VALIDITY_RATE": _pack(_rate([r for r in rows if r["arm"] == "llm"], "policy_ok")
                                      if any(r["arm"] == "llm" for r in rows) else _rate(rows, "policy_ok"),
                                      "plans the policy layer accepts (post-repair for the LLM arm)"),
        "EXACT_MATCH_RATE": _pack(_rate(rows, "exact_match"),
                                  "plan tool sequence contains the expected sequence as a sub-sequence "
                                  "(reported, NOT used to gate validity)"),
        "TOOL_SELECTION_ACCURACY": _pack(_rate(rows, "required_covered"),
                                         "every expected tool is present AND no forbidden tool in an executable plan"),
        "REQUIRED_TOOL_COVERAGE": {"value": round(sum(r["required_tool_coverage"] for r in rows) / len(rows), 3),
                                   "n": len(rows), "def": "mean fraction of expected tools present"},
        "TASK_ORDER_CORRECTNESS": _pack(_rate(rows, "order_ok"), "every 'A < B' order constraint holds"),
        "DEPENDENCY_VALIDITY": {"value": round(d_val / d_tot, 3) if d_tot else None, "n": d_tot,
                                "def": "depends_on edges pointing to a real earlier step / total edges"},
        "UNSUPPORTED_ACTION_RATE": _pack(_rate(exec_rows, "unsupported_action"),
                                         "executable plans that include a forbidden/illegal tool / executable plans",
                                         invert=False),
        "UNNECESSARY_TOOL_SELECTION_RATE": {
            "value": round(sum(1 for r in exec_rows if r["unnecessary_tools"]) / len(exec_rows), 3)
            if exec_rows else None, "n": len(exec_rows),
            "def": "executable plans with >=1 specialist tool not needed by the mission / executable plans"},
        "PLAN_COMPLETION_COMPATIBILITY": _pack(_rate(rows, "valid_termination"),
                                               "plan ends in finalize_answer and contains a verify_result step",
                                               also="verify_present"),
        "ADVERSARIAL_POLICY_REJECTION_RATE": {
            "value": round(sum(1 for r in adversarial
                               if (not r["policy_ok"]) or (not r["forbidden_used"]))
                           / len(adversarial), 3) if adversarial else None,
            "n": len(adversarial),
            "def": "adversarial missions where the plan is policy-rejected OR its executable form "
                   "runs no forbidden/illegal specialist (a safe generic plan counts)"},
        "AVG_PLAN_LENGTH": {"value": round(sum(r["n_specialist_steps"] for r in rows) / len(rows), 2),
                            "n": len(rows), "def": "specialist steps per plan (excl. bookkeeping)"},
        "PLANNING_LATENCY_S": {"value": round(sum(lat) / len(lat), 2) if lat else None, "n": len(lat),
                               "median": round(sorted(lat)[len(lat) // 2], 2) if lat else None,
                               "def": "wall-clock per plan (LLM arm: model generation time, CPU)"},
        "by_category": {c: {
            "n": len([r for r in rows if r["category"] == c]),
            "PLAN_VALIDITY_RATE": _rate([r for r in rows if r["category"] == c], "semantic_valid")[0],
            "TOOL_SELECTION_ACCURACY": _rate([r for r in rows if r["category"] == c], "required_covered")[0],
        } for c in sorted({r["category"] for r in rows})},
        "llm_health": _llm_health(rows),
    }


def _pack(rate_tuple, definition, invert=False, also=None):
    v, n = rate_tuple
    return {"value": v, "n": n, "def": definition}


def _llm_health(rows: list[dict]) -> dict | None:
    llm = [r for r in rows if r["arm"] == "llm"]
    if not llm:
        return None
    return {
        "n": len(llm),
        "parse_ok": sum(1 for r in llm if r.get("parse_status") == "ok"),
        "schema_ok_no_repair": sum(1 for r in llm if r.get("final_source") == "llm"),
        "used_after_repair": sum(1 for r in llm if r.get("final_source") == "llm_repaired"),
        "fell_back_to_rule": sum(1 for r in llm if r.get("fallback")),
        "avg_repairs": round(sum(len(r.get("repairs", [])) for r in llm)
                             / max(sum(1 for r in llm if r.get("final_source") == "llm_repaired"), 1), 2),
        "fallback_reasons": _count([r.get("fallback_reason") for r in llm if r.get("fallback")]),
    }


def _count(xs):
    out: dict[str, int] = {}
    for x in xs:
        if x is None:
            continue
        out[x] = out.get(x, 0) + 1
    return out


# --------------------------------------------------------------------------- #
# exec phase  -- Part 7/8
# --------------------------------------------------------------------------- #


def exec_rows(missions: list[dict], ids: list[str]) -> list[dict]:
    from app.services.agent_runner import run_investigation
    from app.services.analyze import run_analyze
    from app.services.normalize import normalize

    out = []
    for m in missions:
        if m["mission_id"] not in ids:
            continue
        paths = _abspaths(m)
        print(f"  [exec] {m['mission_id']} (LLM agent) ...", flush=True)
        t0 = time.time()
        try:
            res = run_investigation(m["user_query"], paths, {}, planner=LlmPlanner())
            err = None
        except Exception as exc:  # noqa: BLE001
            out.append({"mission_id": m["mission_id"], "category": m["category"],
                        "exec_error": f"{type(exc).__name__}: {exc}"})
            continue
        agent_s = time.time() - t0
        completed = {o.tool for o in res.steps if o.status == "completed"}
        ran_forbidden = bool(set(m.get("forbid_tools", [])) & completed)
        attempts = sum(1 for o in res.steps if o.tool.startswith("run_") and o.status in ("completed", "failed"))
        unsup_attempts = sum(1 for o in res.steps if o.tool.startswith("run_") and o.status == "completed"
                             and o.tool in m.get("forbid_tools", []))
        prov = res.provenance or {}
        rec_replans = [rp for rp in res.replans
                       if rp.reason in ("TOOL_FAILURE", "MISSING_INPUT", "INSUFFICIENT_EVIDENCE")]
        b = normalize(run_analyze(m["user_query"], paths[:2], {}))
        out.append({
            "mission_id": m["mission_id"], "category": m["category"],
            "planner_used": res.planner_used, "plan_status": res.plan_status,
            "planner_attempt": prov.get("planner_attempt"),
            "mission_family": res.mission_family, "phase": res.phase, "mode": res.mode,
            "unsupported": bool(m.get("unsupported")),
            "reached_valid_final": (res.phase == "FINALIZING")
            or (bool(m.get("unsupported")) and not ran_forbidden
                and (bool(res.warnings) or res.mode == "ask-fallback")),
            "tool_calls": res.tool_calls, "n_replans": len(res.replans),
            "replan_reasons": [rp.reason for rp in res.replans],
            "early_stopped": res.early_stopped, "hit_step_cap": res.hit_step_cap,
            "evidence_present": len(res.evidence) > 0,
            "verification_present": bool((res.verification or {}).get("status")),
            "verification_status": (res.verification or {}).get("status"),
            "ran_forbidden_tool": ran_forbidden,
            "unsupported_attempts": unsup_attempts, "total_tool_attempts": attempts,
            "recoverable_failures": len(rec_replans),
            "recovered": bool(rec_replans) and res.phase != "FAILED" and res.verification is not None,
            "unnecessary_tool_calls": prov.get("unnecessary_tool_calls", 0),
            "factual_consistency_ok": _factual_ok(m, res, ran_forbidden),
            "agent_specialist_count": len([o for o in res.steps if o.status == "completed"
                                           and o.tool.startswith("run_")]),
            "baseline_specialist_count": 1 if b.model_used else 0,
            "baseline_model": b.model_used, "baseline_task_code": b.task_code,
            "agent_latency_s": round(agent_s, 2),
            "conclusion": (res.conclusion or "")[:280],
        })
    return out


def _factual_ok(m: dict, res, ran_forbidden: bool) -> bool:
    if ran_forbidden:
        return False
    if m.get("unsupported"):
        lim = bool(res.warnings or res.failures) or (res.verification or {}).get("status") != "SUPPORTED"
        return lim or not res.spatial_findings
    return res.phase == "FINALIZING"


def exec_metrics(rows: list[dict]) -> dict:
    ok = [r for r in rows if "exec_error" not in r]
    n = len(ok)
    if not n:
        return {"N": 0, "n_errors": len(rows)}
    att = sum(r["total_tool_attempts"] for r in ok)
    uns = sum(r["unsupported_attempts"] for r in ok)
    tc = sum(r["tool_calls"] for r in ok)
    unn = sum(r["unnecessary_tool_calls"] for r in ok)
    rec_elig = [r for r in ok if r["recoverable_failures"]]
    multi = [r for r in ok if r["category"] == "multi_step"]
    single = [r for r in ok if r["category"] == "single_step"]
    used = _count([r["planner_used"] for r in ok])
    return {
        "N": n, "n_errors": len(rows) - n,
        "planner_used_counts": used,
        "MISSION_COMPLETION_RATE": _pack(_rate(ok, "reached_valid_final"), "valid terminal state / total"),
        "FINAL_ANSWER_FACTUAL_CONSISTENCY": _pack(_rate(ok, "factual_consistency_ok"),
                                                  "no claim without a supporting observation"),
        "EVIDENCE_PRESERVATION_RATE": _pack(_rate([r for r in ok if r["phase"] == "FINALIZING"],
                                                  "evidence_present"), "evidence survives to the result"),
        "VERIFICATION_PRESERVATION_RATE": _pack(_rate(ok, "verification_present"), "verification present"),
        "UNSUPPORTED_ACTION_RATE": {"value": round(uns / att, 3) if att else 0.0, "n": att,
                                    "def": "forbidden tool calls that RAN / total specialist attempts"},
        "UNNECESSARY_TOOL_CALL_RATE": {"value": round(unn / tc, 3) if tc else 0.0, "n": tc,
                                       "def": "completed calls that did not contribute / total calls"},
        "RECOVERY_RATE": {"value": round(sum(1 for r in rec_elig if r["recovered"]) / len(rec_elig), 3)
                          if rec_elig else None, "n": len(rec_elig),
                          "def": "recoverable-failure missions that still reached a valid final state"},
        "EARLY_STOP_RATE": _pack(_rate(ok, "early_stopped"), "missions the agent stopped before the full plan"),
        "MAX_STEP_VIOLATION_RATE": _pack(_rate(ok, "hit_step_cap"), "missions that hit the >=8 tool-call cap"),
        "avg_tool_calls": round(tc / n, 2),
        "avg_replans": round(sum(r["n_replans"] for r in ok) / n, 2),
        "avg_latency_s": round(sum(r["agent_latency_s"] for r in ok) / n, 1),
        "replan_reason_counts": _count([x for r in ok for x in r["replan_reasons"]]),
        "baseline_vs_agent": {
            "multi_step": _cmp(multi),
            "single_step": _cmp(single),
            "all": _cmp(ok),
        },
    }


def _cmp(rows: list[dict]) -> dict | None:
    if not rows:
        return None
    return {
        "N": len(rows),
        "agent_avg_specialists_run": round(sum(r["agent_specialist_count"] for r in rows) / len(rows), 2),
        "baseline_avg_specialists_run": round(sum(r["baseline_specialist_count"] for r in rows) / len(rows), 2),
        "agent_mission_completion": _rate(rows, "reached_valid_final")[0],
        "agent_evidence_rate": _rate([r for r in rows if r["phase"] == "FINALIZING"], "evidence_present")[0],
    }


# --------------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------------- #


def _pick_exec_ids(missions: list[dict], n: int) -> list[str]:
    by_cat: dict[str, list[str]] = {}
    for m in missions:
        by_cat.setdefault(m["category"], []).append(m["mission_id"])
    # prefer multi_step + temporal + optical_sar, then fill
    order = ["multi_step", "temporal", "optical_sar", "adversarial", "single_step"]
    quota = {"multi_step": 6, "temporal": 5, "optical_sar": 4, "adversarial": 3, "single_step": 2}
    ids: list[str] = []
    for cat in order:
        ids += by_cat.get(cat, [])[: quota[cat]]
    for cat in order:
        for mid in by_cat.get(cat, []):
            if len(ids) >= n:
                break
            if mid not in ids:
                ids.append(mid)
    return ids[:n]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--llm-cache", action="store_true", help="generate + cache LLM raw completions (slow)")
    ap.add_argument("--redo-cache", action="store_true", help="regenerate cache entries even if present")
    ap.add_argument("--only", default="", help="comma-separated mission ids (for --llm-cache / --exec)")
    ap.add_argument("--plan", action="store_true", help="score both plan arms + write the report")
    ap.add_argument("--exec", type=int, default=0, help="run N real-model exec missions (LLM agent vs baseline)")
    a = ap.parse_args()

    spec = json.loads(_MISSIONS.read_text())
    missions = spec["missions"]
    only = [x.strip() for x in a.only.split(",") if x.strip()] or None

    # both --llm-cache and --exec drive many LLM calls -> use the persistent
    # (load-once) model server unless the caller has already chosen.
    if (a.llm_cache or a.exec) and "SATQUERY_PLANNER_PERSISTENT" not in os.environ:
        os.environ["SATQUERY_PLANNER_PERSISTENT"] = "1"

    if a.llm_cache:
        llm_cache_build(missions, only=only, redo=a.redo_cache)
        if not (a.plan or a.exec):
            return 0

    report_path = _OUT / "G16_REAL_LLM_EVALUATION.json"
    prev = json.loads(report_path.read_text()) if report_path.exists() else {}

    rule_rows = plan_rows_rule(missions)
    cache = json.loads(_RAW_CACHE.read_text()) if _RAW_CACHE.exists() else {}
    llm_rows = plan_rows_llm(missions, cache)

    ex_rows = prev.get("exec_rows", [])
    if a.exec:
        ids = only or _pick_exec_ids(missions, a.exec)
        ex_rows = exec_rows(missions, ids)

    report = {
        "evaluation": "G16 - Real LLM Agent Validation (internal frozen evaluation, NOT a benchmark)",
        "date": time.strftime("%Y-%m-%dT%H%M%S"),
        "n_missions": len(missions),
        "llm_model": "Qwen2-VL-2B-Instruct (text-only), local, CPU, greedy/deterministic decoding",
        "llm_prompt": "compact (~1.05k tokens), schema-constrained + safe-repair + truncation salvage",
        "ARM_A_N": len(rule_rows),
        "ARM_B_N": len(llm_rows),
        "ARM_B_not_attempted": len(missions) - len(llm_rows),
        "ARM_B_note": (f"ARM B ran on {len(llm_rows)}/{len(missions)} missions - a stratified subset; "
                       "the local 2B model needs ~100 s/plan on this CPU-only host (full 50 ~= 1.5 h). "
                       "A GPU host runs all 50; the harness supports it. Every ARM B rate is over this N."),
        "arms": {
            "rule": arm_metrics(rule_rows),
            "llm": arm_metrics(llm_rows),
        },
        "exec_metrics": exec_metrics(ex_rows) if ex_rows else None,
        "plan_rows": {"rule": rule_rows, "llm": llm_rows},
        "exec_rows": ex_rows,
    }
    _OUT.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2))
    _write_md(report, _OUT / "G16_REAL_LLM_EVALUATION.md")
    print(json.dumps({"rule": _brief(report["arms"]["rule"]),
                      "llm": _brief(report["arms"]["llm"]),
                      "llm_health": report["arms"]["llm"]["llm_health"],
                      "exec": report["exec_metrics"]}, indent=2))
    print(f"\nwrote {report_path} + .md")
    return 0


def _brief(am: dict) -> dict:
    return {k: am[k]["value"] for k in ("PLAN_VALIDITY_RATE", "TOOL_SELECTION_ACCURACY",
                                       "TASK_ORDER_CORRECTNESS", "DEPENDENCY_VALIDITY",
                                       "UNSUPPORTED_ACTION_RATE", "PLAN_COMPLETION_COMPATIBILITY")}


def _mrow(label, am, key):
    v = am[key]
    extra = f" (median {v['median']}s)" if key == "PLANNING_LATENCY_S" and v.get("median") else ""
    return f"| {label} | {v['value']}{extra} | {v['n']} | {v.get('def','')} |"


def _write_md(rep: dict, path: Path) -> None:
    R, Lm = rep["arms"]["rule"], rep["arms"]["llm"]
    keys = ["PLAN_VALIDITY_RATE", "SCHEMA_VALIDITY_RATE", "EXACT_MATCH_RATE", "TOOL_SELECTION_ACCURACY",
            "REQUIRED_TOOL_COVERAGE", "TASK_ORDER_CORRECTNESS", "DEPENDENCY_VALIDITY",
            "UNSUPPORTED_ACTION_RATE", "UNNECESSARY_TOOL_SELECTION_RATE", "PLAN_COMPLETION_COMPATIBILITY",
            "ADVERSARIAL_POLICY_REJECTION_RATE", "AVG_PLAN_LENGTH", "PLANNING_LATENCY_S"]
    L = [
        f"# G16 — Real LLM Agent Validation — {rep['date']}",
        "",
        "> **Internal frozen evaluation — NOT an external benchmark.** Two planning arms over the "
        f"same {rep['n_missions']} frozen missions. Every rate carries its N.",
        f"> LLM: **{rep['llm_model']}**; prompt: {rep['llm_prompt']}.",
        f"> **ARM A N = {rep['ARM_A_N']}** (all missions). **ARM B N = {rep['ARM_B_N']}** "
        f"({rep['ARM_B_not_attempted']} not attempted). {rep['ARM_B_note']}",
        "",
        "## Planning metrics — ARM A (RuleBasedPlanner) vs ARM B (local LLM)",
        "",
        "| metric | RULE | N | LLM | N | definition |",
        "|--------|:----:|:-:|:---:|:-:|------------|",
    ]
    for k in keys:
        rv, lv = R[k], Lm[k]
        rextra = f" (med {rv.get('median')}s)" if k == "PLANNING_LATENCY_S" and rv.get("median") is not None else ""
        lextra = f" (med {lv.get('median')}s)" if k == "PLANNING_LATENCY_S" and lv.get("median") is not None else ""
        L.append(f"| {k} | **{rv['value']}**{rextra} | {rv['n']} | **{lv['value']}**{lextra} | {lv['n']} | {rv.get('def','')} |")
    lh = Lm["llm_health"]
    if lh:
        L += ["", "## LLM planner health (ARM B)", "",
              f"- parses to JSON: **{lh['parse_ok']}/{lh['n']}**",
              f"- schema-valid with no repair: **{lh['schema_ok_no_repair']}/{lh['n']}**",
              f"- usable only after safe repair: **{lh['used_after_repair']}/{lh['n']}** "
              f"(avg {lh['avg_repairs']} repairs)",
              f"- fell back to RuleBasedPlanner: **{lh['fell_back_to_rule']}/{lh['n']}** "
              f"— reasons: `{lh['fallback_reasons']}`"]
    L += ["", "## By category (PLAN_VALIDITY / TOOL_SELECTION), rule vs llm", ""]
    for c in R["by_category"]:
        rc, lc = R["by_category"][c], Lm["by_category"].get(c, {"n": 0})
        L.append(f"- **{c}**: rule {rc['PLAN_VALIDITY_RATE']}/{rc['TOOL_SELECTION_ACCURACY']} (n={rc['n']}) "
                 f"· llm {lc.get('PLAN_VALIDITY_RATE')}/{lc.get('TOOL_SELECTION_ACCURACY')} (n={lc['n']})")

    em = rep["exec_metrics"]
    if em and em["N"]:
        L += ["", f"## Execution phase — LLM agent, real frozen-stack models (N={em['N']}, "
              f"{em['n_errors']} errors)", "",
              f"planner actually used: `{em['planner_used_counts']}`", "",
              "| metric | value | N | definition |", "|--------|:-----:|:-:|------------|"]
        for k in ("MISSION_COMPLETION_RATE", "FINAL_ANSWER_FACTUAL_CONSISTENCY", "EVIDENCE_PRESERVATION_RATE",
                  "VERIFICATION_PRESERVATION_RATE", "UNSUPPORTED_ACTION_RATE", "UNNECESSARY_TOOL_CALL_RATE",
                  "RECOVERY_RATE", "EARLY_STOP_RATE", "MAX_STEP_VIOLATION_RATE"):
            v = em[k]
            L.append(f"| {k} | **{v['value']}** | {v['n']} | {v.get('def','')} |")
        L += [f"| avg tool calls / mission | {em['avg_tool_calls']} | {em['N']} | |",
              f"| avg replans / mission | {em['avg_replans']} | {em['N']} | |",
              f"| avg latency (s) | {em['avg_latency_s']} | {em['N']} | CPU |",
              "", f"Replan reasons: `{em['replan_reason_counts']}`", "",
              "### Baseline (`/analyze`) vs LLM agent — required specialists run", ""]
        for seg in ("multi_step", "single_step", "all"):
            c = em["baseline_vs_agent"][seg]
            if c:
                L.append(f"- **{seg}** (N={c['N']}): baseline {c['baseline_avg_specialists_run']} · "
                         f"agent {c['agent_avg_specialists_run']} · agent completion {c['agent_mission_completion']}")
    L += ["", "## Claim discipline", "",
          "Supported: *schema-constrained LLM planning*, *policy-constrained agentic execution*, "
          "*bounded observe/replan*, *evidence-aware multi-step orchestration*, *adaptive specialist "
          "selection based on intermediate observations*. NOT claimed: \"fully autonomous\", "
          "\"hallucination-free\", \"state-of-the-art\", \"real-time\"."]
    path.write_text("\n".join(L))


if __name__ == "__main__":
    raise SystemExit(main())
