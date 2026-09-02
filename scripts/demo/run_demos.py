"""SatQuery G13 demo runner — 5 deterministic end-to-end scenarios.

Runs the real `run_analyze` pipeline (validate -> interpret -> route -> specialist
-> evidence -> verify -> resolution) against fixed local fixtures with the frozen
model stack, prints a human summary, and writes the real normalized outputs to
`docs/sih/evidence/demos/`.

Nothing is faked. A demo that cannot run (missing checkpoint/venv) is recorded as
`status: BLOCKED` with the reason — never with a synthetic result.

Usage:
    .venvs/satquery/Scripts/python.exe scripts/demo/run_demos.py [--demo N] [--no-write]
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO / "apps" / "backend"))

from app.services.analyze import run_analyze  # noqa: E402
from app.services.normalize import normalize  # noqa: E402

_DEMO = _REPO / "data" / "demo"
_OUT = _REPO / "docs" / "sih" / "evidence" / "demos"

DEMOS = [
    dict(
        n=1, name="VQA — what is present",
        query="What objects are visible in this satellite image?",
        images=[_DEMO / "vqa" / "scene.jpg"],
        expect_code="SINGLE_IMAGE_VQA", model="TinyRS-2B",
    ),
    dict(
        n=2, name="Grounding — locate the largest object",
        query="Where is the largest building?",
        images=[_DEMO / "grounding" / "scene.jpg"],
        expect_code="SINGLE_IMAGE_GROUNDING", model="RemoteSAM",
    ),
    dict(
        n=3, name="Temporal — what changed",
        query="What changed between these two images?",
        images=[_DEMO / "temporal" / "t1.tif", _DEMO / "temporal" / "t2.tif"],
        expect_code="TEMPORAL", model="ChangeFormer",
    ),
    dict(
        n=4, name="Optical + SAR — compare modalities",
        query="Compare the optical and SAR information for this area.",
        images=[_DEMO / "optical_sar" / "s2_optical.tif", _DEMO / "optical_sar" / "s1_sar.tif"],
        expect_code="MULTIMODAL_REPR", model="CROMA",
    ),
    dict(
        n=5, name="Investigation — what changed, where, and what evidence supports it",
        query="Describe what changed and where, with supporting evidence.",
        images=[_DEMO / "temporal" / "t1.tif", _DEMO / "temporal" / "t2.tif"],
        expect_code="TEMPORAL", model="ChangeFormer + RemoteCLIP (composed baseline)",
    ),
]


def _summary(d: dict, n) -> str:
    lines = [
        f"  task        : {n.interpreted_task}  ({n.task_code})",
        f"  model       : {n.model_used or '-'}",
        f"  ok          : {n.ok}",
        f"  answer      : {(n.answer or '')[:300]}",
        f"  latency_s   : {n.latency_s}",
    ]
    if n.boxes:
        lines.append(f"  boxes       : {[b.xyxy_pixel for b in n.boxes]}")
    if n.regions:
        lines.append(f"  regions     : {len(n.regions)}  ({[r.label for r in n.regions]})")
    if n.changed_fraction is not None:
        lines.append(f"  changed_frac: {n.changed_fraction:.4f}   area_ha: {n.area_ha}")
    if n.representation_dim is not None:
        lines.append(f"  repr_dim    : {n.representation_dim}")
    if n.labels:
        lines.append(f"  top labels  : {n.labels[:3]}")
    lines.append(f"  evidence    : {[e.get('evidence_type') for e in n.evidence]}")
    lines.append(f"  verification: {(n.verification or {}).get('status')}")
    lines.append(f"  resolution  : {(n.resolution or {}).get('qualifier')}")
    lines.append(f"  geo         : available={n.geospatial_available} crs={n.crs or n.geospatial_note}")
    if n.warnings:
        lines.append(f"  warnings    : {n.warnings}")
    if n.failures:
        lines.append(f"  failures    : {n.failures}")
    return "\n".join(lines)


def run_one(d: dict, write: bool) -> dict:
    print(f"\n=== DEMO {d['n']} — {d['name']} ===")
    print(f"  query       : {d['query']}")
    imgs = [str(p) for p in d["images"]]
    missing = [p for p in imgs if not Path(p).exists()]
    if missing:
        rec = {"demo": d["name"], "query": d["query"], "status": "BLOCKED",
               "reason": f"fixture(s) missing: {missing}"}
        print(f"  status      : BLOCKED — fixtures missing: {missing}")
    else:
        t0 = time.time()
        try:
            res = run_analyze(d["query"], imgs, {})
            n = normalize(res, latency_s=round(time.time() - t0, 2))
            print(_summary(d, n))
            rec = {"demo": d["name"], "query": d["query"], "inputs": imgs,
                   "status": "OK" if n.ok else "RETURNED_NOT_OK",
                   "expected_task_code": d["expect_code"], "expected_model": d["model"],
                   "normalized_response": n.model_dump()}
        except Exception as exc:  # noqa: BLE001
            rec = {"demo": d["name"], "query": d["query"], "inputs": imgs,
                   "status": "ERROR", "reason": f"{type(exc).__name__}: {exc}"}
            print(f"  status      : ERROR — {type(exc).__name__}: {exc}")
    if write:
        _OUT.mkdir(parents=True, exist_ok=True)
        slug = d["name"].split(" — ")[0].strip().lower().replace(" ", "_").replace("+", "").replace("__", "_")
        fp = _OUT / f"g13_demo{d['n']}_{slug}.json"
        fp.write_text(json.dumps(rec, indent=2, default=str))
        print(f"  wrote       : {fp.relative_to(_REPO)}")
    return rec


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--demo", type=int, default=0, help="run only demo N (1-5); 0 = all")
    ap.add_argument("--no-write", action="store_true", help="do not write JSON captures")
    a = ap.parse_args()
    todo = DEMOS if a.demo == 0 else [d for d in DEMOS if d["n"] == a.demo]
    recs = [run_one(d, not a.no_write) for d in todo]
    ok = sum(1 for r in recs if r["status"] == "OK")
    print(f"\n{ok}/{len(recs)} demos returned ok. "
          f"(BLOCKED/ERROR are recorded honestly, not faked.)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
