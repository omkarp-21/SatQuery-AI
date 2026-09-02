"""G17 — HYBRID AGENT evaluation: three planner architectures, 100 frozen missions.

  ARM A  RuleBasedPlanner                       (deterministic; the default)
  ARM B  Pure local LLM planner  (LlmPlanner)   (G16 — carried forward + optional fresh sample)
  ARM C  Hybrid = LLM intent -> deterministic PlanSynthesizer

The LLM is slow on CPU, so both the pure-planner raw output (ARM B, reused from
G16) and the intent JSON (ARM C) are generated ONCE via the persistent model
server and cached; scoring is then instant and re-runnable.

Usage:
  # 1. cache ARM C intent JSON for all 100 (persistent server; ~6 s/mission):
  SATQUERY_PLANNER_PERSISTENT=1 .venvs/satquery/Scripts/python.exe evaluation/agent/run_g17_eval.py --intent-cache
  # 2. score all three arms + write the report:
  .venvs/satquery/Scripts/python.exe evaluation/agent/run_g17_eval.py --plan
  # 3. real-model execution: ARM C hybrid agent vs the deterministic baseline:
  .venvs/satquery/Scripts/python.exe evaluation/agent/run_g17_eval.py --exec 12
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
    LlmIntentExtractor,
    PlanContext,
    PlanSynthesizer,
    RuleBasedPlanner,
    derive_intent_rulebased,
    intent_from_raw,
    validate_plan,
)

from plan_scorer import score_plan  # noqa: E402
from run_agent_eval import _CAPS, _abspaths, _coreg, _modalities  # noqa: E402

_MISSIONS = _REPO / "evaluation" / "agent" / "frozen_missions_100.json"
_OUT = _REPO / "evaluation" / "agent" / "reports"
_INTENT_CACHE = _OUT / "G17_intent_cache.json"
_G16 = _OUT / "G16_REAL_LLM_EVALUATION.json"


# --------------------------------------------------------------------------- #
# ARM C — intent cache
# --------------------------------------------------------------------------- #


def intent_cache_build(missions: list[dict], only: list[str] | None, redo: bool) -> dict:
    os.environ.setdefault("SATQUERY_PLANNER_PERSISTENT", "1")
    cache = json.loads(_INTENT_CACHE.read_text()) if _INTENT_CACHE.exists() else {}
    ext = LlmIntentExtractor(timeout_s=180.0)
    todo = [m for m in missions if (only is None or m["mission_id"] in only)
            and (redo or m["mission_id"] not in cache)]
    print(f"generating {len(todo)} LLM intent objects (cache has {len(cache)})", flush=True)
    for i, m in enumerate(todo, 1):
        paths = _abspaths(m)
        mods = _modalities(paths)
        t0 = time.time()
        try:
            it, att = ext.extract(m["user_query"], len(paths), mods)
            raw, gen_s, err = att.raw_output, att.gen_s, None
        except Exception as exc:  # noqa: BLE001
            raw, gen_s, err = "", None, f"{type(exc).__name__}: {exc}"
        cache[m["mission_id"]] = {"user_query": m["user_query"], "image_count": len(paths),
                                  "modalities": mods, "raw": raw, "gen_s": gen_s, "error": err,
                                  "wall_s": round(time.time() - t0, 1)}
        _INTENT_CACHE.write_text(json.dumps(cache, indent=1))
        print(f"  [{i}/{len(todo)}] {m['mission_id']} gen={gen_s}s"
              + (f" ERR {err}" if err else ""), flush=True)
    return cache


# --------------------------------------------------------------------------- #
# plan-phase scoring
# --------------------------------------------------------------------------- #


def _ctx(paths: list[str], mods: list[str]) -> PlanContext:
    return PlanContext(image_count=len(paths), modalities=mods, has_valid_crs=True,
                       pair_co_registered=_coreg(paths), available_capabilities=_CAPS)


def _score_row(m: dict, plan, policy_ok: bool, n_images: int, mods: list[str]) -> dict:
    sc = score_plan(plan, m, policy_ok=policy_ok, image_count=n_images, modalities=mods)
    sc.update(mission_id=m["mission_id"], category=m["category"],
              unsupported=bool(m.get("unsupported")),
              runtime_detected=bool(m.get("runtime_detected")), policy_ok=policy_ok)
    if sc["runtime_detected"]:
        sc["unsupported_action"] = None
    return sc


def arm_rule(missions: list[dict]) -> list[dict]:
    rows = []
    for m in missions:
        paths = _abspaths(m)
        mods = _modalities(paths)
        t0 = time.time()
        plan = RuleBasedPlanner().plan(m["user_query"], len(paths), mods)
        lat = time.time() - t0
        pr = validate_plan(plan, _ctx(paths, mods))
        r = _score_row(m, plan, pr.ok, len(paths), mods)
        r.update(arm="rule", planner_latency_s=round(lat, 5),
                 intent_schema_ok=None, intent_task_ok=None, intent_source="rule_based")
        rows.append(r)
    return rows


def arm_hybrid(missions: list[dict], cache: dict) -> list[dict]:
    """ARM C. Only missions with an intent-cache entry are scored (N stated)."""
    synth = PlanSynthesizer()
    rows = []
    for m in missions:
        c = cache.get(m["mission_id"])
        if c is None:
            continue
        paths = _abspaths(m)
        mods = _modalities(paths)
        exp_fam = (m.get("expected_intent") or {}).get("task_family")

        from satquery_agents.agent.intent import _intent_plausible
        if c.get("error") or not c.get("raw"):
            it = derive_intent_rulebased(m["user_query"], len(paths), mods)
            it.source = "rule_based_fallback"
            schema_ok, task_ok, isrc, gen_s = False, None, "rule_based_fallback", c.get("gen_s")
        else:
            it, att = intent_from_raw(c["raw"], m["user_query"], gen_s=c.get("gen_s"))
            gen_s = c.get("gen_s")
            if it is not None:
                # INTENT_TASK_ACCURACY is scored on the RAW LLM classification
                task_ok = (it.task_family.value == exp_fam) if exp_fam else None
                schema_ok = att.schema_status == "ok" or att.final_source == "llm_repaired"
                isrc = att.final_source
                if not _intent_plausible(it, len(paths)):
                    it = None  # image-count mismatch -> HybridPlanner falls back
            else:
                task_ok, schema_ok, isrc = None, False, "rule_based_fallback"
            if it is None:
                it = derive_intent_rulebased(m["user_query"], len(paths), mods)
                it.source = "rule_based_fallback"
                isrc = "rule_based_fallback"

        plan = synth.synthesize(it, len(paths), mods, mission=m["user_query"])
        pr = validate_plan(plan, _ctx(paths, mods))
        r = _score_row(m, plan, pr.ok, len(paths), mods)
        r.update(arm="hybrid", planner_latency_s=gen_s,
                 intent_schema_ok=bool(schema_ok), intent_task_ok=task_ok,
                 intent_source=isrc, intent_family=it.task_family.value,
                 expected_family=exp_fam,
                 intent_caps=[cp.value for cp in it.required_capabilities])
        rows.append(r)
    return rows


# --------------------------------------------------------------------------- #
# metrics
# --------------------------------------------------------------------------- #


def _rate(rows, key):
    vals = [bool(r[key]) for r in rows if r.get(key) is not None]
    return {"value": round(sum(vals) / len(vals), 3) if vals else None, "n": len(vals)}


def arm_metrics(rows: list[dict], arm: str) -> dict:
    if not rows:
        return {"arm": arm, "N": 0, "note": "not attempted (no cache) — run --intent-cache first"}
    supported = [r for r in rows if not r["unsupported"]]
    adversarial = [r for r in rows if r["unsupported"]]
    execu = [r for r in rows if r["policy_ok"]]
    d_tot = sum(r["deps_total"] for r in rows)
    d_val = sum(r["deps_valid"] for r in rows)
    lat = [r["planner_latency_s"] for r in rows if r.get("planner_latency_s") is not None]
    m = {
        "arm": arm, "N": len(rows), "N_supported": len(supported),
        "PLAN_VALIDITY_RATE": {**_rate(supported, "semantic_valid"),
                               "def": "SUPPORTED missions: schema-valid + policy-accepted + semantically valid "
                                      "(required tools, deps, order, modality, verify, finalize) / supported"},
        "TOOL_SELECTION_ACCURACY": {**_rate(rows, "required_covered"),
                                    "def": "every expected tool present AND no forbidden tool in an executable plan / all"},
        "REQUIRED_TOOL_COVERAGE": {"value": round(sum(r["required_tool_coverage"] for r in rows) / len(rows), 3),
                                   "n": len(rows), "def": "mean fraction of expected tools present"},
        "TASK_ORDER_CORRECTNESS": {**_rate(rows, "order_ok"), "def": "every 'A < B' order constraint holds / all"},
        "DEPENDENCY_VALIDITY": {"value": round(d_val / d_tot, 3) if d_tot else None, "n": d_tot,
                                "def": "depends_on edges to a real earlier step / total edges"},
        "UNSUPPORTED_ACTION_RATE": {**_rate(execu, "unsupported_action"),
                                    "def": "executable plans with a forbidden/illegal tool / executable plans"},
        "UNNECESSARY_TOOL_SELECTION_RATE": {
            "value": round(sum(1 for r in execu if r["unnecessary_tools"]) / len(execu), 3) if execu else None,
            "n": len(execu),
            "def": "executable plans with >=1 specialist not needed by the mission / executable plans"},
        "ADVERSARIAL_CORRECTLY_HANDLED_RATE": {
            "value": round(sum(1 for r in adversarial if (not r["policy_ok"]) or (not r["forbidden_used"]))
                           / len(adversarial), 3) if adversarial else None,
            "n": len(adversarial),
            "def": "adversarial missions: plan policy-rejected OR executable form runs no forbidden specialist / adversarial"},
        "AVG_PLAN_LENGTH": {"value": round(sum(r["n_specialist_steps"] for r in rows) / len(rows), 2), "n": len(rows),
                            "def": "specialist steps per plan (excl. bookkeeping)"},
        "PLANNER_LATENCY_S": {"value": round(sum(lat) / len(lat), 2) if lat else None,
                              "median": round(sorted(lat)[len(lat) // 2], 2) if lat else None, "n": len(lat),
                              "def": "wall-clock per plan; ARM C = LLM intent generation time (CPU)"},
        "by_category": {},
    }
    if arm == "hybrid":
        m["INTENT_SCHEMA_VALIDITY_RATE"] = {**_rate(rows, "intent_schema_ok"),
                                            "def": "LLM intent JSON parses + validates (post safe-repair) / all"}
        m["INTENT_TASK_ACCURACY"] = {**_rate([r for r in rows if r.get("intent_task_ok") is not None], "intent_task_ok"),
                                     "def": "LLM intent task_family == expected_intent.task_family / scored"}
        m["INTENT_FELL_BACK_TO_RULE"] = sum(1 for r in rows if r.get("intent_source") == "rule_based_fallback")
    for cat in sorted({r["category"] for r in rows}):
        cr = [r for r in rows if r["category"] == cat]
        m["by_category"][cat] = {
            "n": len(cr),
            "PLAN_VALIDITY_RATE": _rate([r for r in cr if not r["unsupported"]], "semantic_valid")["value"],
            "TOOL_SELECTION_ACCURACY": _rate(cr, "required_covered")["value"],
            "INTENT_TASK_ACCURACY": _rate([r for r in cr if r.get("intent_task_ok") is not None],
                                          "intent_task_ok")["value"] if arm == "hybrid" else None,
        }
    return m


# --------------------------------------------------------------------------- #
# exec phase (ARM C vs baseline)
# --------------------------------------------------------------------------- #


def exec_rows(missions: list[dict], ids: list[str]) -> list[dict]:
    os.environ.setdefault("SATQUERY_PLANNER_PERSISTENT", "1")
    from app.services.agent_runner import run_investigation
    from app.services.analyze import run_analyze
    from app.services.normalize import normalize
    from satquery_agents.agent import HybridPlanner

    out = []
    for m in missions:
        if m["mission_id"] not in ids:
            continue
        paths = _abspaths(m)
        print(f"  [exec] {m['mission_id']} (hybrid agent) ...", flush=True)
        t0 = time.time()
        try:
            res = run_investigation(m["user_query"], paths, {}, planner=HybridPlanner())
        except Exception as exc:  # noqa: BLE001
            out.append({"mission_id": m["mission_id"], "category": m["category"],
                        "exec_error": f"{type(exc).__name__}: {exc}"})
            continue
        agent_s = time.time() - t0
        completed = {o.tool for o in res.steps if o.status == "completed"}
        ran_forbidden = bool(set(m.get("forbid_tools", [])) & completed)
        attempts = sum(1 for o in res.steps if o.tool.startswith("run_") and o.status in ("completed", "failed"))
        unsup = sum(1 for o in res.steps if o.tool.startswith("run_") and o.status == "completed"
                    and o.tool in m.get("forbid_tools", []))
        prov = res.provenance or {}
        b = normalize(run_analyze(m["user_query"], paths[:2], {}))
        out.append({
            "mission_id": m["mission_id"], "category": m["category"],
            "planner_used": res.planner_used, "plan_status": res.plan_status,
            "intent": res.intent, "mission_family": res.mission_family,
            "phase": res.phase, "mode": res.mode, "unsupported": bool(m.get("unsupported")),
            "reached_valid_final": (res.phase == "FINALIZING")
            or (bool(m.get("unsupported")) and not ran_forbidden
                and (bool(res.warnings) or res.mode == "ask-fallback")),
            "tool_calls": res.tool_calls, "n_replans": len(res.replans),
            "replan_reasons": [rp.reason for rp in res.replans],
            "early_stopped": res.early_stopped, "hit_step_cap": res.hit_step_cap,
            "evidence_present": len(res.evidence) > 0,
            "verification_present": bool((res.verification or {}).get("status")),
            "verification_status": (res.verification or {}).get("status"),
            "confidence_category": (res.confidence or {}).get("category"),
            "ran_forbidden_tool": ran_forbidden,
            "unsupported_attempts": unsup, "total_tool_attempts": attempts,
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
        return bool(lim or not res.spatial_findings)
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
    multi = [r for r in ok if r["category"] == "multi_step"]
    single = [r for r in ok if r["category"] == "single_step"]
    return {
        "N": n, "n_errors": len(rows) - n,
        "planner_used_counts": _count([r["planner_used"] for r in ok]),
        "MISSION_COMPLETION_RATE": {**_rate(ok, "reached_valid_final"), "def": "valid terminal state / total"},
        "FINAL_ANSWER_FACTUAL_CONSISTENCY": {**_rate(ok, "factual_consistency_ok"),
                                             "def": "no claim without a supporting observation / total"},
        "EVIDENCE_PRESERVATION_RATE": {**_rate([r for r in ok if r["phase"] == "FINALIZING"], "evidence_present"),
                                       "def": "evidence survives to the result / finalized missions"},
        "VERIFICATION_PRESERVATION_RATE": {**_rate(ok, "verification_present"), "def": "verification present / total"},
        "UNSUPPORTED_ACTION_RATE": {"value": round(uns / att, 3) if att else 0.0, "n": att,
                                    "def": "forbidden tool calls that RAN / total specialist attempts"},
        "UNNECESSARY_TOOL_CALL_RATE": {"value": round(unn / tc, 3) if tc else 0.0, "n": tc,
                                       "def": "completed calls that did not contribute / total calls"},
        "EARLY_STOP_RATE": {**_rate(ok, "early_stopped"), "def": "missions stopped before the full plan / total"},
        "MAX_STEP_VIOLATION_RATE": {**_rate(ok, "hit_step_cap"), "def": "missions that hit the >=8 tool cap / total"},
        "REPLAN_RATE": {"value": round(sum(1 for r in ok if r["n_replans"]) / n, 3), "n": n,
                        "def": "missions with >=1 replan / total"},
        "avg_tool_calls": round(tc / n, 2), "avg_replans": round(sum(r["n_replans"] for r in ok) / n, 2),
        "avg_total_mission_latency_s": round(sum(r["agent_latency_s"] for r in ok) / n, 1),
        "replan_reason_counts": _count([x for r in ok for x in r["replan_reasons"]]),
        "confidence_category_counts": _count([r.get("confidence_category") for r in ok]),
        "baseline_vs_hybrid": {
            "multi_step": _cmp(multi), "single_step": _cmp(single), "all": _cmp(ok),
        },
    }


def _cmp(rows):
    if not rows:
        return None
    return {"N": len(rows),
            "hybrid_avg_specialists_run": round(sum(r["agent_specialist_count"] for r in rows) / len(rows), 2),
            "baseline_avg_specialists_run": round(sum(r["baseline_specialist_count"] for r in rows) / len(rows), 2),
            "hybrid_mission_completion": _rate(rows, "reached_valid_final")["value"],
            "hybrid_factual_consistency": _rate(rows, "factual_consistency_ok")["value"]}


def _count(xs):
    out: dict[str, int] = {}
    for x in xs:
        if x is None:
            continue
        out[x] = out.get(x, 0) + 1
    return out


# --------------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------------- #


def _carry_g16_arm_b() -> dict | None:
    if not _G16.exists():
        return None
    g16 = json.loads(_G16.read_text())
    b = g16.get("arms", {}).get("llm")
    if not b:
        return None
    return {"arm": "pure_llm_planner", "source": "G16 (carried forward — NOT re-run in G17)",
            "N": b.get("N"), "N_supported": b.get("N_supported"),
            "PLAN_VALIDITY_RATE": b.get("PLAN_VALIDITY_RATE"),
            "TOOL_SELECTION_ACCURACY": b.get("TOOL_SELECTION_ACCURACY"),
            "SCHEMA_VALIDITY_RATE": b.get("SCHEMA_VALIDITY_RATE"),
            "DEPENDENCY_VALIDITY": b.get("DEPENDENCY_VALIDITY"),
            "UNSUPPORTED_ACTION_RATE": b.get("UNSUPPORTED_ACTION_RATE"),
            "PLANNER_LATENCY_S": b.get("PLANNING_LATENCY_S"),
            "by_category": b.get("by_category"),
            "exec_note": ("G16 exec (N=6): FINAL_ANSWER_FACTUAL_CONSISTENCY 0.33, forbidden-tool-that-RAN "
                          "0.67 - structurally-valid echo plans passed policy and ran; the G16 intent "
                          "cross-check was added to contain it."),
            "failure_mode": "example-echo: the same VALIDATE->run_vqa->VERIFY->FINALIZE plan for every mission"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--intent-cache", action="store_true")
    ap.add_argument("--redo-cache", action="store_true")
    ap.add_argument("--only", default="")
    ap.add_argument("--plan", action="store_true")
    ap.add_argument("--exec", type=int, default=0)
    a = ap.parse_args()

    spec = json.loads(_MISSIONS.read_text())
    missions = spec["missions"]
    only = [x.strip() for x in a.only.split(",") if x.strip()] or None

    if a.intent_cache:
        intent_cache_build(missions, only, a.redo_cache)
        if not (a.plan or a.exec):
            return 0

    report_path = _OUT / "G17_HYBRID_EVALUATION.json"
    prev = json.loads(report_path.read_text()) if report_path.exists() else {}

    rule_rows = arm_rule(missions)
    cache = json.loads(_INTENT_CACHE.read_text()) if _INTENT_CACHE.exists() else {}
    hyb_rows = arm_hybrid(missions, cache)

    ex_rows = prev.get("exec_rows", [])
    if a.exec:
        ids = only or _pick_exec_ids(missions, a.exec)
        ex_rows = exec_rows(missions, ids)

    report = {
        "evaluation": "G17 - Hybrid Agent Evaluation (internal frozen evaluation, NOT a benchmark)",
        "date": time.strftime("%Y-%m-%dT%H%M%S"),
        "n_missions": len(missions),
        "categories": {c: sum(1 for m in missions if m["category"] == c) for c in spec["categories"]},
        "llm_model": "Qwen2-VL-2B-Instruct (text-only), local, CPU, greedy decoding",
        "ARM_C_N": len(hyb_rows), "ARM_C_not_attempted": len(missions) - len(hyb_rows),
        "arms": {
            "A_rule": arm_metrics(rule_rows, "rule"),
            "B_pure_llm": _carry_g16_arm_b(),
            "C_hybrid": arm_metrics(hyb_rows, "hybrid"),
        },
        "exec_metrics": exec_metrics(ex_rows) if ex_rows else None,
        "plan_rows": {"rule": rule_rows, "hybrid": hyb_rows},
        "exec_rows": ex_rows,
    }
    _OUT.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2))
    _write_md(report, _OUT / "G17_HYBRID_EVALUATION.md")
    print(json.dumps({"A_rule": _brief(report["arms"]["A_rule"]),
                      "C_hybrid": _brief(report["arms"]["C_hybrid"]),
                      "C_intent": {k: report["arms"]["C_hybrid"].get(k)
                                   for k in ("INTENT_SCHEMA_VALIDITY_RATE", "INTENT_TASK_ACCURACY",
                                             "INTENT_FELL_BACK_TO_RULE")},
                      "exec": report["exec_metrics"]}, indent=2, default=str))
    print(f"\nwrote {report_path} + .md")
    return 0


def _pick_exec_ids(missions: list[dict], n: int) -> list[str]:
    by_cat: dict[str, list[str]] = {}
    for m in missions:
        by_cat.setdefault(m["category"], []).append(m["mission_id"])
    quota = {"multi_step": 4, "temporal": 3, "optical_sar": 2, "adversarial": 2, "single_step": 1}
    ids: list[str] = []
    for cat in ("multi_step", "temporal", "optical_sar", "adversarial", "single_step"):
        ids += by_cat.get(cat, [])[: quota[cat]]
    for cat in by_cat:
        for mid in by_cat[cat]:
            if len(ids) >= n:
                break
            if mid not in ids:
                ids.append(mid)
    return ids[:n]


def _brief(am: dict | None) -> dict:
    if not am:
        return {}
    return {k: (am[k].get("value") if isinstance(am.get(k), dict) else am.get(k))
            for k in ("PLAN_VALIDITY_RATE", "TOOL_SELECTION_ACCURACY", "TASK_ORDER_CORRECTNESS",
                      "DEPENDENCY_VALIDITY", "UNSUPPORTED_ACTION_RATE", "UNNECESSARY_TOOL_SELECTION_RATE",
                      "PLANNER_LATENCY_S")}


def _mval(x):
    return x.get("value") if isinstance(x, dict) else x


def _write_md(rep: dict, path: Path) -> None:
    A = rep["arms"]["A_rule"]
    B = rep["arms"]["B_pure_llm"] or {}
    C = rep["arms"]["C_hybrid"]
    L = [
        f"# G17 — Hybrid Agent Evaluation — {rep['date']}",
        "",
        "> **Internal frozen evaluation — NOT an external benchmark.** Three planner architectures over "
        f"the same **{rep['n_missions']}** frozen missions (20 / category). Every rate carries its N.",
        "> The **G16 negative result for the pure LLM planner is preserved** below (ARM B, carried "
        "forward — not re-run).",
        "",
        "| architecture | what the planner owns |",
        "|---|---|",
        "| **A — RuleBasedPlanner** | everything (keyword/feature → plan) |",
        "| **B — pure local LLM** | intent **and** execution graph (G16 — rejected for production) |",
        "| **C — hybrid** | LLM: typed **intent only** · deterministic `PlanSynthesizer`: the execution graph |",
        "",
        f"ARM A N = {A['N']}. ARM C N = {rep['ARM_C_N']} ({rep['ARM_C_not_attempted']} not attempted). "
        "LLM: " + rep["llm_model"] + ".",
        "",
        "## Planning metrics",
        "",
        "| metric | A rule | N | B pure-LLM | N | C hybrid | N | definition |",
        "|--------|:------:|:-:|:---------:|:-:|:--------:|:-:|------------|",
    ]
    keys = ["PLAN_VALIDITY_RATE", "TOOL_SELECTION_ACCURACY", "REQUIRED_TOOL_COVERAGE",
            "TASK_ORDER_CORRECTNESS", "DEPENDENCY_VALIDITY", "UNSUPPORTED_ACTION_RATE",
            "UNNECESSARY_TOOL_SELECTION_RATE", "ADVERSARIAL_CORRECTLY_HANDLED_RATE",
            "AVG_PLAN_LENGTH", "PLANNER_LATENCY_S"]
    for k in keys:
        av, an = _mval(A.get(k)), (A.get(k) or {}).get("n", "")
        bv = _mval(B.get(k)) if k in B else "—"
        bn = (B.get(k) or {}).get("n", "") if isinstance(B.get(k), dict) else ""
        cv, cn = _mval(C.get(k)), (C.get(k) or {}).get("n", "")
        dfn = (A.get(k) or {}).get("def", "") if isinstance(A.get(k), dict) else ""
        L.append(f"| {k} | **{av}** | {an} | {bv} | {bn} | **{cv}** | {cn} | {dfn} |")
    L += ["", "## ARM C — LLM intent extraction quality", ""]
    if C.get("N"):
        for k in ("INTENT_SCHEMA_VALIDITY_RATE", "INTENT_TASK_ACCURACY"):
            v = C.get(k, {})
            L.append(f"- **{k}**: {v.get('value')} (N={v.get('n')}) — {v.get('def', '')}")
        L.append(f"- fell back to the deterministic intent: **{C.get('INTENT_FELL_BACK_TO_RULE')}** / {C['N']}")
    else:
        L.append("- _ARM C not attempted — run `--intent-cache` first._")
    L += ["", "### By category — PLAN_VALIDITY / TOOL_SELECTION (rule vs hybrid) · INTENT_TASK_ACC (hybrid)", ""]
    for cat in A.get("by_category", {}):
        ac, cc = A["by_category"][cat], C.get("by_category", {}).get(cat, {})
        L.append(f"- **{cat}** (n={ac['n']}): rule {ac['PLAN_VALIDITY_RATE']}/{ac['TOOL_SELECTION_ACCURACY']} "
                 f"· hybrid {cc.get('PLAN_VALIDITY_RATE')}/{cc.get('TOOL_SELECTION_ACCURACY')} "
                 f"· intent-task {cc.get('INTENT_TASK_ACCURACY')}")
    if B:
        L += ["", "## ARM B — pure local LLM planner (G16, preserved)", "",
              f"- PLAN_VALIDITY {(_mval(B.get('PLAN_VALIDITY_RATE')))} · TOOL_SELECTION "
              f"{_mval(B.get('TOOL_SELECTION_ACCURACY'))} · SCHEMA_VALIDITY "
              f"{_mval(B.get('SCHEMA_VALIDITY_RATE'))} · latency ~"
              f"{_mval(B.get('PLANNER_LATENCY_S'))} s (N={B.get('N')})",
              f"- failure mode: {B.get('failure_mode')}",
              f"- {B.get('exec_note')}",
              f"- source: {B.get('source')}"]
    em = rep["exec_metrics"]
    if em and em.get("N"):
        L += ["", f"## Execution phase — ARM C hybrid agent, real frozen-stack models (N={em['N']}, "
              f"{em['n_errors']} errors)", "",
              f"planner actually used: `{em['planner_used_counts']}` · confidence categories: "
              f"`{em['confidence_category_counts']}`", "",
              "| metric | value | N | definition |", "|--------|:-----:|:-:|------------|"]
        for k in ("MISSION_COMPLETION_RATE", "FINAL_ANSWER_FACTUAL_CONSISTENCY", "EVIDENCE_PRESERVATION_RATE",
                  "VERIFICATION_PRESERVATION_RATE", "UNSUPPORTED_ACTION_RATE", "UNNECESSARY_TOOL_CALL_RATE",
                  "EARLY_STOP_RATE", "MAX_STEP_VIOLATION_RATE", "REPLAN_RATE"):
            v = em[k]
            L.append(f"| {k} | **{_mval(v)}** | {v.get('n')} | {v.get('def', '')} |")
        L += [f"| avg tool calls / mission | {em['avg_tool_calls']} | {em['N']} | |",
              f"| avg total mission latency (s) | {em['avg_total_mission_latency_s']} | {em['N']} | CPU, cold loads |",
              "", f"Replan reasons: `{em['replan_reason_counts']}`", "",
              "### Baseline (`/analyze`) vs hybrid agent — required specialists run", ""]
        for seg in ("multi_step", "single_step", "all"):
            c = em["baseline_vs_hybrid"][seg]
            if c:
                L.append(f"- **{seg}** (N={c['N']}): baseline {c['baseline_avg_specialists_run']} · "
                         f"hybrid {c['hybrid_avg_specialists_run']} · hybrid completion "
                         f"{c['hybrid_mission_completion']} · factual {c['hybrid_factual_consistency']}")
    L += ["", "## Claim discipline", "",
          "Supported: *LLM-assisted intent understanding*, *deterministic plan synthesis*, "
          "*policy-constrained execution*, *bounded observe/replan*, *evidence-derived confidence category*. "
          "NOT claimed: the LLM autonomously controls the system; \"fully autonomous\"; \"calibrated "
          "confidence\"; \"state-of-the-art\"; \"real-time\"."]
    path.write_text("\n".join(L))


if __name__ == "__main__":
    raise SystemExit(main())
