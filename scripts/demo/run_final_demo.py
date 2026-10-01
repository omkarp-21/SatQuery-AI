"""G18 Part 11/12 — the FROZEN SIH demo set, production architecture.

Runs the PRODUCTION default (`RuleBasedPlanner` → policy → bounded adaptive
executor → evidence → verification → trust category) with the real frozen-stack
models. Nothing is hard-coded; CASE B's shorter path emerges from the actual
ChangeFormer output.

  FLAGSHIP  — one mission, two environments:
    CASE A  significant change   -> change -> regions -> grounding -> SAR -> verify
    CASE B  minimal / no change  -> change -> verify -> early stop
  SECONDARY — one fast grounding query ("where is the largest ship?")

Captures (per Part 11): mission · input metadata · plan · tools · observations ·
replans · verification · confidence · evidence · geojson · final result ·
total latency. Written to docs/sih/evidence/demos/final/.

Usage:
  .venvs/satquery/Scripts/python.exe scripts/demo/run_final_demo.py [--only flagship|secondary]
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

from satquery_agents.agent import RuleBasedPlanner  # noqa: E402

from app.services.agent_runner import run_investigation  # noqa: E402
from app.services.analyze import run_analyze  # noqa: E402
from app.services.normalize import normalize  # noqa: E402

_DEMO = _REPO / "data" / "demo"
_INV = _DEMO / "investigation"
_OUT = _REPO / "docs" / "sih" / "evidence" / "demos" / "final"

_FLAGSHIP_MISSION = (
    "Investigate this area. Identify significant changes between the two "
    "observations, locate the affected structures, compare optical and SAR "
    "evidence, and provide a verified summary."
)
_FLAGSHIP_CASES = {
    "caseA_change": [_INV / "t1_optical.tif", _INV / "t2_optical.tif",
                     _INV / "s2_dfc_optical.tif", _INV / "s1_dfc_sar.tif"],
    "caseB_nochange": [_INV / "t1_optical.tif", _INV / "t2_nochange.tif",
                       _INV / "s2_dfc_optical.tif", _INV / "s1_dfc_sar.tif"],
}
_SECONDARY_QUERY = "Where is the largest ship?"
_SECONDARY_IMAGE = _DEMO / "grounding" / "scene.jpg"


def _trim(o, d=0):
    if isinstance(o, dict):
        return {k: ("<omitted large array>" if k in {"mask", "change_mask", "array",
                                                     "representation_vector"} else _trim(v, d + 1))
                for k, v in o.items()}
    if isinstance(o, list):
        if len(o) > 24 and all(isinstance(x, (int, float)) for x in o):
            return f"<{len(o)} numbers omitted>"
        return [_trim(x, d + 1) for x in o]
    return o


def _raster_meta(paths):
    out = []
    try:
        import rasterio
        for p in paths:
            if str(p).lower().endswith((".tif", ".tiff")):
                with rasterio.open(p) as ds:
                    out.append({"file": Path(p).name, "bands": ds.count, "size": [ds.width, ds.height],
                                "dtype": ds.dtypes[0], "crs": str(ds.crs),
                                "transform_is_identity": ds.transform.is_identity})
            else:
                out.append({"file": Path(p).name, "kind": "image"})
    except Exception as exc:  # noqa: BLE001
        out.append({"error": str(exc)})
    return out


def run_flagship_case(name: str, paths: list[Path]) -> dict:
    missing = [p for p in paths if not p.exists()]
    if missing:
        return {"case": name, "status": "BLOCKED", "missing": [str(p) for p in missing]}
    print(f"\n=== FLAGSHIP {name} ===  {[p.name for p in paths]}")
    t0 = time.time()
    res = run_investigation(_FLAGSHIP_MISSION, [str(p) for p in paths], {}, planner=RuleBasedPlanner())
    wall = round(time.time() - t0, 1)
    conf = res.confidence or {}
    tasks = [s.task.value if hasattr(s.task, "value") else s.task
             for s in (res.plan.steps if res.plan else [])]
    print(f"  planner_used : {res.planner_used}   plan: {' -> '.join(tasks)}")
    print(f"  phase        : {res.phase}  early_stopped={res.early_stopped}  tool_calls={res.tool_calls}")
    print(f"  replans      : {[r.reason for r in res.replans]}")
    for o in res.steps:
        print(f"    {o.step_id:>4} {o.tool:<26} {o.status:<10} {o.verdict:<12} {o.summary or ''}")
    print(f"  conclusion   : {(res.conclusion or '')[:260]}")
    print(f"  verification : {(res.verification or {}).get('status')}   confidence: {conf.get('category')}")
    print(f"  wall_s       : {wall}")

    payload = json.loads(res.model_dump_json())
    for o in payload.get("steps", []):
        if isinstance(o.get("payload"), dict):
            o["payload"] = _trim(o["payload"])
    payload["_capture"] = {
        "script": "scripts/demo/run_final_demo.py", "case": name, "wall_s": wall,
        "architecture": "PRODUCTION: RuleBasedPlanner -> 12-check policy -> bounded adaptive executor "
                        "-> evidence -> verification -> trust category",
        "input_metadata": _raster_meta(paths),
        "note": "Same mission for caseA and caseB; only the post-event image differs. CASE B's shorter "
                "path is decided by the real ChangeFormer output, not hard-coded.",
    }
    _OUT.mkdir(parents=True, exist_ok=True)
    out = _OUT / f"flagship_{name}.json"
    out.write_text(json.dumps(payload, indent=1), encoding="utf-8")
    print(f"  wrote {out.relative_to(_REPO)}")
    return {"case": name, "status": "OK", "planner_used": res.planner_used, "plan_tasks": tasks,
            "phase": res.phase, "early_stopped": res.early_stopped, "tool_calls": res.tool_calls,
            "replans": [r.reason for r in res.replans],
            "verification": (res.verification or {}).get("status"),
            "confidence": conf.get("category"), "wall_s": wall}


def run_secondary() -> dict:
    if not _SECONDARY_IMAGE.exists():
        return {"status": "BLOCKED", "missing": str(_SECONDARY_IMAGE)}
    print(f"\n=== SECONDARY ===  {_SECONDARY_QUERY!r}  [{_SECONDARY_IMAGE.name}]")
    t0 = time.time()
    n = normalize(run_analyze(_SECONDARY_QUERY, [str(_SECONDARY_IMAGE)], {}),
                  latency_s=round(time.time() - t0, 2))
    wall = round(time.time() - t0, 1)
    print(f"  task    : {n.interpreted_task} ({n.task_code})   model: {n.model_used}")
    print(f"  answer  : {(n.answer or '')[:200]}")
    print(f"  boxes   : {[b.xyxy_pixel for b in (n.boxes or [])]}")
    print(f"  verify  : {(n.verification or {}).get('status')}   wall_s: {wall}")
    payload = json.loads(n.model_dump_json())
    payload["_capture"] = {"script": "scripts/demo/run_final_demo.py", "query": _SECONDARY_QUERY,
                           "image": _SECONDARY_IMAGE.name, "wall_s": wall,
                           "purpose": "fast judge attention-grabber (~15-30 s): query -> grounding "
                                      "-> box/mask -> geospatial position -> verification"}
    _OUT.mkdir(parents=True, exist_ok=True)
    out = _OUT / "secondary_grounding.json"
    out.write_text(json.dumps(payload, indent=1), encoding="utf-8")
    print(f"  wrote {out.relative_to(_REPO)}")
    return {"status": "OK", "task": n.task_code, "model": n.model_used,
            "boxes": [b.xyxy_pixel for b in (n.boxes or [])], "wall_s": wall}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", choices=["flagship", "secondary"], default=None)
    a = ap.parse_args()
    summary: dict = {}
    if a.only != "secondary":
        summary["flagship"] = [run_flagship_case(n, p) for n, p in _FLAGSHIP_CASES.items()]
    if a.only != "flagship":
        summary["secondary"] = run_secondary()
    print("\n=== SUMMARY ===")
    print(json.dumps(summary, indent=1))
    fl = summary.get("flagship")
    if fl and all(c.get("status") == "OK" for c in fl):
        a_, b_ = fl[0], fl[1]
        ok = (b_["tool_calls"] <= a_["tool_calls"]
              and (b_["early_stopped"] or b_["tool_calls"] < a_["tool_calls"]))
        print(f"\ncaseA tool_calls={a_['tool_calls']} · caseB tool_calls={b_['tool_calls']} "
              f"early_stopped={b_['early_stopped']} -> "
              + ("PASS: CASE B path is shorter and emerged from the observation"
                 if ok else "REVIEW: CASE B did not clearly shorten"))
    (_OUT / "_summary.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
