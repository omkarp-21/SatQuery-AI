"""SatQuery G15 flagship investigation capture.

Runs the real agent (`run_investigation`) with the frozen model stack against the
local investigation fixtures, then writes the full result — plan, tool sequence,
per-step observations, replans, verification, final answer, timings — to
`docs/sih/evidence/demos/g15_investigation_flagship.json`.

Nothing is faked. The plan is produced by the planner from the mission text; there
is no hard-coded workflow for the flagship sentence. If a specialist cannot load
(missing checkpoint / venv) the run records it honestly rather than substituting a
synthetic result.

Usage:
    .venvs/satquery/Scripts/python.exe scripts/demo/run_g15_flagship.py [--phrasing N] [--no-write]
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO / "apps" / "backend"))

from app.services.agent_runner import run_investigation  # noqa: E402

_DEMO = _REPO / "data" / "demo" / "investigation"
_OUT = _REPO / "docs" / "sih" / "evidence" / "demos"

_IMAGES = [
    _DEMO / "t1_optical.tif",
    _DEMO / "t2_optical.tif",
    _DEMO / "s2_dfc_optical.tif",
    _DEMO / "s1_dfc_sar.tif",
]

# Alternate phrasings of the same multi-step mission — the plan must EMERGE from
# planning, not from matching the flagship sentence.
_PHRASINGS = [
    "Investigate this area. Identify significant changes between the two "
    "observations, locate the affected structures, and use SAR evidence to "
    "characterize the changes. Give me an evidence-backed summary.",
    "Something happened here between these two dates. Work out what changed, "
    "where the changed structures are, and bring in the radar image to back it "
    "up. Summarise with evidence.",
    "Run a full change investigation on this site: detect the change, pull out "
    "the changed regions, find the buildings involved, cross-check against the "
    "SAR, and give me a verified summary.",
]


def _trim(obj, _depth=0):
    """Drop bulky arrays from a payload so the capture stays readable."""
    if isinstance(obj, dict):
        return {
            k: ("<omitted large array>" if k in {"mask", "change_mask", "array", "representation_vector"}
                else _trim(v, _depth + 1))
            for k, v in obj.items()
        }
    if isinstance(obj, list):
        if len(obj) > 24 and all(isinstance(x, (int, float)) for x in obj):
            return f"<{len(obj)} numbers omitted>"
        return [_trim(x, _depth + 1) for x in obj]
    return obj


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--phrasing", type=int, default=0, choices=range(len(_PHRASINGS)))
    ap.add_argument("--no-write", action="store_true")
    args = ap.parse_args()

    missing = [p for p in _IMAGES if not p.exists()]
    if missing:
        print("BLOCKED — missing fixtures:")
        for p in missing:
            print(f"  {p}")
        return 1

    mission = _PHRASINGS[args.phrasing]
    print(f"Mission (phrasing {args.phrasing}):\n  {mission}\n")
    t0 = time.time()
    res = run_investigation(mission, [str(p) for p in _IMAGES])
    wall = round(time.time() - t0, 1)

    plan_tasks = [s.task.value if hasattr(s.task, "value") else s.task
                  for s in (res.plan.steps if res.plan else [])]
    print(f"planner_used   : {res.planner_used}")
    print(f"plan_status    : {res.plan_status}")
    print(f"mission_family : {res.mission_family}")
    print(f"plan tasks     : {' -> '.join(plan_tasks)}")
    print(f"phase          : {res.phase}   ok={res.ok}   early_stopped={res.early_stopped}")
    print(f"tool_calls     : {res.tool_calls}")
    print(f"replans        : {[r.reason for r in res.replans]}")
    for o in res.steps:
        print(f"  {o.step_id:>4} {o.tool:<26} -> {o.verdict:<10} {o.summary or ''}")
    print(f"conclusion     : {(res.conclusion or '')[:400]}")
    print(f"verification   : {(res.verification or {}).get('overall')}")
    print(f"models_used    : {res.models_used}")
    print(f"warnings       : {res.warnings}")
    print(f"wall_s         : {wall}")

    if args.no_write:
        return 0

    payload = json.loads(res.model_dump_json())
    for o in payload.get("steps", []):
        if isinstance(o.get("payload"), dict):
            o["payload"] = _trim(o["payload"])
    payload["_capture"] = {
        "script": "scripts/demo/run_g15_flagship.py",
        "phrasing_index": args.phrasing,
        "wall_s": wall,
        "real_models": True,
        "note": "Plan produced by the planner from the mission text; no hard-coded flagship workflow.",
    }
    _OUT.mkdir(parents=True, exist_ok=True)
    out = _OUT / f"g15_investigation_flagship_{args.phrasing}.json"
    out.write_text(json.dumps(payload, indent=1), encoding="utf-8")
    print(f"\nwrote {out.relative_to(_REPO)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
