"""G16 Part 15/16 — flagship investigation with the ACTUAL local LLM planner,
in two environments, to demonstrate that execution genuinely depends on
observations (not a fixed change→ground→SAR script).

CASE A  significant change   -> expect change -> regions -> grounding -> SAR -> verify
CASE B  little / no change    -> expect change -> verify -> stop (early)

Same mission text, same planner. The only difference is the post-event image.

Writes docs/sih/evidence/demos/g16_llm_flagship_{caseA,caseB}.json with:
planner used, generated plan, policy validation, specialist calls, observations,
replans, evidence, verification, final answer, timings. The raw LLM text is NOT
included (audit-only, kept in provenance.planner_attempt as status flags).

Usage:
  SATQUERY_PLANNER_PERSISTENT=1 .venvs/satquery/Scripts/python.exe scripts/demo/run_g16_flagship.py
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO / "apps" / "backend"))
sys.path.insert(0, str(_REPO / "packages" / "agents" / "src"))

from satquery_agents.agent import LlmPlanner  # noqa: E402

from app.services.agent_runner import run_investigation  # noqa: E402

_DEMO = _REPO / "data" / "demo" / "investigation"
_OUT = _REPO / "docs" / "sih" / "evidence" / "demos"

_MISSION = (
    "Investigate this area. Identify significant changes between the two "
    "observations, locate the affected structures, compare optical and SAR "
    "evidence, and give me a verified summary."
)

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


def run_case(name: str, paths: list[Path]) -> dict:
    missing = [p for p in paths if not p.exists()]
    if missing:
        return {"case": name, "status": "BLOCKED", "missing": [str(p) for p in missing]}
    print(f"\n=== {name} ===\n{[p.name for p in paths]}")
    t0 = time.time()
    res = run_investigation(_MISSION, [str(p) for p in paths], {}, planner=LlmPlanner())
    wall = round(time.time() - t0, 1)
    plan_tasks = [s.task.value if hasattr(s.task, "value") else s.task
                  for s in (res.plan.steps if res.plan else [])]
    print(f"planner_used   : {res.planner_used}   plan_status: {res.plan_status}")
    print(f"plan tasks     : {' -> '.join(plan_tasks)}")
    print(f"phase          : {res.phase}  ok={res.ok}  early_stopped={res.early_stopped}")
    print(f"tool_calls     : {res.tool_calls}   replans: {[r.reason for r in res.replans]}")
    for o in res.steps:
        print(f"  {o.step_id:>4} {o.tool:<26} -> {o.verdict:<12} {o.summary or ''}")
    print(f"conclusion     : {(res.conclusion or '')[:300]}")
    print(f"verification   : {(res.verification or {}).get('status')}")
    print(f"models_used    : {res.models_used}   wall_s: {wall}")

    payload = json.loads(res.model_dump_json())
    for o in payload.get("steps", []):
        if isinstance(o.get("payload"), dict):
            o["payload"] = _trim(o["payload"])
    payload["_capture"] = {
        "script": "scripts/demo/run_g16_flagship.py", "case": name, "wall_s": wall,
        "planner": "LlmPlanner (local Qwen2-VL-2B, text-only, CPU)",
        "note": "Same mission + planner for caseA and caseB; only the post-event image differs. "
                "The execution path is decided by observations, not hard-coded.",
    }
    _OUT.mkdir(parents=True, exist_ok=True)
    out = _OUT / f"g16_llm_flagship_{name}.json"
    out.write_text(json.dumps(payload, indent=1), encoding="utf-8")
    print(f"wrote {out.relative_to(_REPO)}")
    return {
        "case": name, "status": "OK", "planner_used": res.planner_used,
        "plan_tasks": plan_tasks, "phase": res.phase, "early_stopped": res.early_stopped,
        "tool_calls": res.tool_calls, "replans": [r.reason for r in res.replans],
        "verification": (res.verification or {}).get("status"), "wall_s": wall,
    }


def main() -> int:
    summary = [run_case(name, paths) for name, paths in _CASES.items()]
    print("\n=== ADAPTIVITY SUMMARY ===")
    print(json.dumps(summary, indent=1))
    a, b = summary[0], summary[1]
    if a.get("status") == "OK" and b.get("status") == "OK":
        print(f"\ncaseA tool_calls={a['tool_calls']}  caseB tool_calls={b['tool_calls']}  "
              f"caseB early_stopped={b['early_stopped']}")
        print("PASS: caseB is shorter / stops early" if (b["tool_calls"] <= a["tool_calls"]
              and (b["early_stopped"] or b["tool_calls"] < a["tool_calls"]))
              else "REVIEW: caseB did not clearly shorten")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
