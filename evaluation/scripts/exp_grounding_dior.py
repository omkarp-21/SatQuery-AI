"""EXP-GROUNDING (Track A) — RemoteSAM on a frozen DIOR-RSVG sample.

Resolves 25 referring expressions from the non-gated DIOR-RSVG test parquet
(`pzhang1990/DIOR-RSVG`) deterministically, extracts each image, runs RemoteSAM
via `scripts/research/remotesam_infer.py` (`.venvs/remotesam`), and scores
**acc@IoU0.5** against the ground-truth boxes.

Selection (frozen): rows sorted by (int(image_id), int(question_id)); one
expression per distinct image_id; first 25. Resolved ids are written back into
`evaluation/datasets/dior_rsvg_sample.json`.

Usage:  python evaluation/scripts/exp_grounding_dior.py
"""

from __future__ import annotations

import io
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
_PARQUET = REPO / "models/cache/dior_rsvg/data/test-00000-of-00005.parquet"
_SPEC = REPO / "evaluation/datasets/dior_rsvg_sample.json"
_CKPT = REPO / "models/cache/remotesam/RemoteSAM/RemoteSAMv1.pth"
_REPO_RS = REPO / "external/research/RemoteSAM"
_VENV = REPO / ".venvs/remotesam/Scripts/python.exe"
_BRIDGE = REPO / "scripts/research/remotesam_infer.py"
_BERT = REPO / ("models/cache/hf_home/hub/models--bert-base-uncased/snapshots/"
                "86b5e0934494bd15c9632b12f734a8a67f723594")
_N = 25
_GATE = 0.30


def _iou(a, b) -> float:
    ix1, iy1 = max(a[0], b[0]), max(a[1], b[1])
    ix2, iy2 = min(a[2], b[2]), min(a[3], b[3])
    iw, ih = max(0.0, ix2 - ix1), max(0.0, iy2 - iy1)
    inter = iw * ih
    ua = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / ua if ua > 0 else 0.0


def _resolve() -> list[dict]:
    import pyarrow.parquet as pq

    rows = pq.read_table(_PARQUET).to_pylist()
    rows.sort(key=lambda r: (int(r["image_id"]), int(r["question_id"])))
    seen: set[str] = set()
    out: list[dict] = []
    for r in rows:
        if r["image_id"] in seen:
            continue
        box = json.loads(r["bbox"]) if isinstance(r["bbox"], str) else list(r["bbox"])
        out.append({"image_id": str(r["image_id"]), "question_id": str(r["question_id"]),
                    "expression": r["question"], "gt_box": [float(x) for x in box],
                    "image_bytes": r["image"]["bytes"]})
        seen.add(str(r["image_id"]))
        if len(out) >= _N:
            break
    return out


def main() -> int:
    if not _PARQUET.exists():
        print("DATASET_MISSING: DIOR-RSVG parquet"); return 2
    if not (_CKPT.exists() and _VENV.exists()):
        print("ARTIFACT_MISSING: RemoteSAM checkpoint / venv"); return 1

    items = _resolve()
    tmp = Path(tempfile.mkdtemp(prefix="dior_rsvg_"))
    jobs = []
    for it in items:
        ip = tmp / f"{it['image_id']}.jpg"
        ip.write_bytes(it["image_bytes"])
        jobs.append({"image": str(ip), "query": it["expression"],
                     "mask_out": str(tmp / f"m_{it['image_id']}.png")})
    jf = tmp / "jobs.json"
    jf.write_text(json.dumps(jobs))
    out_json = tmp / "out.json"

    t0 = time.time()
    cmd = [str(_VENV), str(_BRIDGE), "--checkpoint", str(_CKPT), "--repo", str(_REPO_RS),
           "--jobs-json", str(jf), "--out-json", str(out_json), "--device", "cpu",
           "--hf-home", str(REPO / "models/cache/hf_home"), "--bert-dir", str(_BERT)]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=3600, check=False)
    wall = round(time.time() - t0, 1)
    if not out_json.exists():
        print(f"BRIDGE_FAILED rc={proc.returncode}\n{proc.stderr[-1500:]}"); return 1
    bridge = json.loads(out_json.read_text())
    res = {r["query"] + "|" + Path(r["image"]).stem: r for r in bridge.get("results", [])}

    correct = incorrect = nobox = errors = 0
    per: list[dict] = []
    ious: list[float] = []
    for it in items:
        key = it["expression"] + "|" + it["image_id"]
        r = res.get(key, {})
        box = r.get("bbox_xyxy")
        st = r.get("status")
        if st == "error":
            errors += 1
            iou = 0.0
        elif box is None:
            nobox += 1
            iou = 0.0
        else:
            iou = _iou(box, it["gt_box"])
            ious.append(iou)
            if iou >= 0.5:
                correct += 1
            else:
                incorrect += 1
        per.append({"image_id": it["image_id"], "question_id": it["question_id"],
                    "expression": it["expression"], "gt_box": it["gt_box"],
                    "pred_box": box, "iou": round(iou, 3), "status": st,
                    "latency_s": r.get("latency_s")})

    acc = round(correct / _N, 4)
    report = {
        "experiment": "EXP-GROUNDING Track A - RemoteSAM on DIOR-RSVG (n=25, frozen)",
        "date": time.strftime("%Y-%m-%d"),
        "dataset": "pzhang1990/DIOR-RSVG test-00000-of-00005.parquet (non-gated mirror)",
        "n": _N, "metric": "acc@IoU0.5", "gate": _GATE,
        "acc_at_iou50": acc, "passes_gate": bool(acc >= _GATE),
        "correct": correct, "incorrect": incorrect, "no_box": nobox, "errors": errors,
        "mean_iou_over_boxed": round(sum(ious) / len(ious), 3) if ious else None,
        "wall_time_s": wall,
        "load_time_s": bridge.get("load_time_s"),
        "cpu_rss_mb_after_load": bridge.get("cpu_rss_mb_after_load"),
        "cpu_rss_mb_peak": bridge.get("cpu_rss_mb_peak"),
        "warm_latency_s": bridge.get("warm_latency_s"),
        "gpu_peak_mb": bridge.get("gpu_peak_mb"),  # None on CPU - NOT VRAM
        "per_case": per,
    }
    outp = REPO / "evaluation" / "reports" / f"exp_grounding_dior_{time.strftime('%Y%m%dT%H%M%S')}.json"
    outp.parent.mkdir(parents=True, exist_ok=True)
    outp.write_text(json.dumps(report, indent=2))

    # freeze the resolved ids
    spec = json.loads(_SPEC.read_text())
    spec["resolved_ids"] = [f"{it['image_id']}#{it['question_id']}" for it in items]
    spec["resolved_note"] = ("resolved 2026-09-02 from pzhang1990/DIOR-RSVG "
                             "test-00000-of-00005.parquet (non-gated); id = <image_id>#<question_id>")
    _SPEC.write_text(json.dumps(spec, indent=2))

    print(json.dumps({k: v for k, v in report.items() if k != "per_case"}, indent=2))
    print(f"wrote {outp}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
