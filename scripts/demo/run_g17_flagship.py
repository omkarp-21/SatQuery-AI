"""G17 Part 14/15 — flagship investigation with the HYBRID architecture, in two
environments, to show the execution path depends on actual observations.

    mission text -> LLM INTENT -> deterministic PlanSynthesizer -> policy ->
    bounded adaptive execution -> trust layer

CASE A  significant change   -> validate -> change -> regions -> grounding -> SAR -> verify
CASE B  little / no change    -> validate -> change -> verify -> early stop

Same mission text, same planner (HybridPlanner). Only the post-event image differs.
Not hard-coded: the plan is synthesised from the extracted Intent; the execution
path is decided by the real ChangeFormer output.

Writes docs/sih/evidence/demos/g17_hybrid_flagship_{caseA,caseB}.json with:
intent · plan · policy · tool calls · observations · replans · evidence ·
verification · confidence category · final answer · latency. No raw LLM text.

Usage:
  SATQUERY_PLANNER_PERSISTENT=1 .venvs/satquery/Scripts/python.exe scripts/demo/run_g17_flagship.py [--phrasing N]
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

from satquery_agents.agent import HybridPlanner  # noqa: E402

from app.services.agent_runner import run_investigation  # noqa: E402

_DEMO = _REPO / "data" / "demo" / "investigation"
_OUT = _REPO / "docs" / "sih" / "evidence" / "demos"

_PHRASINGS = [
    "Investigate this area. Identify significant changes between the two "
    "observations, locate the affected structures, compare optical and SAR "
    "evidence, and give me a verified summary.",
    "Something changed here between these two dates. Work out what changed, find "
    "the affected buildings, bring in the radar to corroborate, and summarise "
    "with evidence.",
    "Run a full change investigation on this site: detect the change, pull out "
    "the changed regions, ground the buildings involved, cross-check the SAR, "
    "and give me a verified report.",
]

_CASES = {
    "caseA": [_DEMO / "t1_optical.tif", _DEMO / "t2_optical.tif",
              _DEMO / "s2_dfc_optical.tif", _DEMO / "s1_dfc_sar.tif"],
    "caseB": [_DEMO / "t1_optical.tif", _DEMO / "t2_nochange.tif",
              _DEMO / "s2_dfc_optical.tif", _DEMO / "s1_dfc_sar.tif"],
}


def _trim(o, d=0):
    if isinstance(o, dict):
        return {k: ("<omitted large array>" if k in {"mask", "change_mask", "array", "representation_vector"}
                    else _trim(v, d + 1)) for k, v in o.items()}
    if isinstance(o, list):
        if len(o) > 24 and all(isinstance(x, (int, float)) for x in o):
            return f"<{len(o)} numbers omitted>"
        return [_trim(x, d + 1) for x in o]
    return o


def run_case(name: str, paths: list[Path], mission: str) -> dict:
    missing = [p for p in paths if not p.exists()]
    if missing:
        return {"case": name, "status": "BLOCKED", "missing": [str(p) for p in missing]}
    print(f"\n=== {name} ===  {[p.name for p in paths]}")
    t0 = time.time()
    res = run_investigation(mission, [str(p) for p in paths], {}, planner=HybridPlanner())
    wall = round(time.time() - t0, 1)
    it = res.intent or {}
    plan_tasks = [s.task.value if hasattr(s.task, "value") else s.task
                  for s in (res.plan.steps if res.plan else [])]
    conf = res.confidence or {}
    print(f"intent         : {it.get('task_family')} caps={it.get('required_capabilities')} "
          f"src={it.get('source')}")
    print(f"planner_used    : {res.planner_used}   plan_status: {res.plan_status}")
    print(f"plan tasks      : {' -> '.join(plan_tasks)}")
    print(f"phase           : {res.phase}  ok={res.ok}  early_stopped={res.early_stopped}")
    print(f"tool_calls      : {res.tool_calls}   replans: {[r.reason for r in res.replans]}")
    for o in res.steps:
        print(f"  {o.step_id:>4} {o.tool:<26} -> {o.verdict:<12} {o.summary or ''}")
    print(f"conclusion      : {(res.conclusion or '')[:280]}")
    print(f"verification    : {(res.verification or {}).get('status')}")
    print(f"confidence      : {conf.get('category')}  ({len(conf.get('reasons', []))} reasons)")
    print(f"models_used     : {res.models_used}   wall_s: {wall}")

    payload = json.loads(res.model_dump_json())
    for o in payload.get("steps", []):
        if isinstance(o.get("payload"), dict):
            o["payload"] = _trim(o["payload"])
    payload["_capture"] = {
        "script": "scripts/demo/run_g17_flagship.py", "case": name, "wall_s": wall,
        "architecture": "hybrid: LLM intent -> deterministic PlanSynthesizer -> policy -> bounded execution",
        "note": "Same mission + planner for caseA and caseB; only the post-event image differs. "
                "The plan is synthesised from the extracted Intent; the execution path is decided "
                "by the real ChangeFormer output. No raw LLM text is stored.",
    }
    _OUT.mkdir(parents=True, exist_ok=True)
    out = _OUT / f"g17_hybrid_flagship_{name}.json"
    out.write_text(json.dumps(payload, indent=1), encoding="utf-8")
    print(f"wrote {out.relative_to(_REPO)}")
    return {"case": name, "status": "OK", "intent_family": it.get("task_family"),
            "intent_source": it.get("source"), "planner_used": res.planner_used,
            "plan_tasks": plan_tasks, "phase": res.phase, "early_stopped": res.early_stopped,
            "tool_calls": res.tool_calls, "replans": [r.reason for r in res.replans],
            "verification": (res.verification or {}).get("status"),
            "confidence": conf.get("category"), "wall_s": wall}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--phrasing", type=int, default=0, choices=range(len(_PHRASINGS)))
    a = ap.parse_args()
    mission = _PHRASINGS[a.phrasing]
    print(f"Mission (phrasing {a.phrasing}):\n  {mission}")
    summary = [run_case(n, p, mission) for n, p in _CASES.items()]
    print("\n=== ADAPTIVITY SUMMARY ===")
    print(json.dumps(summary, indent=1))
    a_, b_ = summary[0], summary[1]
    if a_.get("status") == "OK" and b_.get("status") == "OK":
        ok = (b_["tool_calls"] <= a_["tool_calls"]
              and (b_["early_stopped"] or b_["tool_calls"] < a_["tool_calls"]))
        print(f"\ncaseA tool_calls={a_['tool_calls']} · caseB tool_calls={b_['tool_calls']} "
              f"early_stopped={b_['early_stopped']}")
        print("PASS: caseB is shorter / stops early — execution responded to the observation"
              if ok else "REVIEW: caseB did not clearly shorten")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
