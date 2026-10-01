"""REMOTE_SAM_RESOLUTION (Track F) — does input resolution prep help RemoteSAM?

RemoteSAM failed (`no_box`) on a 256 px LEVIR tile in G10. This isolates
**resolution** from **domain**: take N in-domain DIOR-RSVG test cases at native
resolution, downscale each to 256 px (short side) to simulate the small-tile
regime, then feed RemoteSAM three ways and score acc@IoU0.5 on the 256-frame:

  A. native256    the 256 px image as-is
  B. upscale2x    256 px -> bicubic 2x (512 px)
  C. pad_canvas   256 px centred on a 512 px zero canvas (context/margin)

RemoteSAM internally resizes everything to 896^2, so this measures whether a
better pre-upscale (B) or a larger canvas with margin (C) recovers grounding that
the raw 256 px input (A) loses. GT boxes are scaled into each frame.

If B or C does not materially beat A, **do not** add preprocessing complexity.

Usage:  python evaluation/scripts/exp_remotesam_resolution.py [--n 12]
"""

from __future__ import annotations

import argparse
import io
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
_PARQUET = REPO / "models/cache/dior_rsvg/data/test-00000-of-00005.parquet"
_CKPT = REPO / "models/cache/remotesam/RemoteSAM/RemoteSAMv1.pth"
_REPO_RS = REPO / "external/research/RemoteSAM"
_VENV = REPO / ".venvs/remotesam/Scripts/python.exe"
_BRIDGE = REPO / "scripts/research/remotesam_infer.py"
_BERT = REPO / ("models/cache/hf_home/hub/models--bert-base-uncased/snapshots/"
                "86b5e0934494bd15c9632b12f734a8a67f723594")
_SMALL = 256
_BIG = 512


def _iou(a, b) -> float:
    ix1, iy1 = max(a[0], b[0]), max(a[1], b[1])
    ix2, iy2 = min(a[2], b[2]), min(a[3], b[3])
    iw, ih = max(0.0, ix2 - ix1), max(0.0, iy2 - iy1)
    inter = iw * ih
    ua = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / ua if ua > 0 else 0.0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=12)
    a = ap.parse_args()
    if not (_PARQUET.exists() and _CKPT.exists() and _VENV.exists()):
        print("ARTIFACT_MISSING"); return 1

    import pyarrow.parquet as pq
    from PIL import Image

    rows = pq.read_table(_PARQUET).to_pylist()
    rows.sort(key=lambda r: (int(r["image_id"]), int(r["question_id"])))
    seen: set[str] = set()
    cases = []
    for r in rows:
        if r["image_id"] in seen:
            continue
        box = json.loads(r["bbox"]) if isinstance(r["bbox"], str) else list(r["bbox"])
        cases.append({"image_id": r["image_id"], "expr": r["question"],
                      "gt": [float(x) for x in box], "bytes": r["image"]["bytes"]})
        seen.add(r["image_id"])
        if len(cases) >= a.n:
            break

    tmp = Path(tempfile.mkdtemp(prefix="rs_res_"))
    jobs = []
    meta: dict[str, dict] = {}
    for c in cases:
        img = Image.open(io.BytesIO(c["bytes"])).convert("RGB")
        W, H = img.size
        s = _SMALL / min(W, H)
        w256, h256 = round(W * s), round(H * s)
        img256 = img.resize((w256, h256), Image.BICUBIC)
        gt256 = [c["gt"][0] * s, c["gt"][1] * s, c["gt"][2] * s, c["gt"][3] * s]

        variants = {
            "A_native256": (img256, gt256),
            "B_upscale2x": (img256.resize((w256 * 2, h256 * 2), Image.BICUBIC),
                            [v * 2 for v in gt256]),
        }
        canvas = Image.new("RGB", (_BIG, _BIG), (0, 0, 0))
        ox, oy = (_BIG - w256) // 2, (_BIG - h256) // 2
        canvas.paste(img256, (ox, oy))
        variants["C_pad_canvas"] = (canvas, [gt256[0] + ox, gt256[1] + oy,
                                             gt256[2] + ox, gt256[3] + oy])

        for vname, (vimg, vgt) in variants.items():
            key = f"{c['image_id']}::{vname}"
            p = tmp / f"{key.replace('::','_')}.png"
            vimg.save(p)
            jobs.append({"image": str(p), "query": c["expr"], "mask_out": str(p) + ".m.png"})
            meta[c["expr"] + "|" + p.stem] = {"key": key, "variant": vname,
                                              "image_id": c["image_id"], "gt": vgt}

    jf = tmp / "jobs.json"
    jf.write_text(json.dumps(jobs))
    outj = tmp / "out.json"
    t0 = time.time()
    cmd = [str(_VENV), str(_BRIDGE), "--checkpoint", str(_CKPT), "--repo", str(_REPO_RS),
           "--jobs-json", str(jf), "--out-json", str(outj), "--device", "cpu",
           "--hf-home", str(REPO / "models/cache/hf_home"), "--bert-dir", str(_BERT)]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=5400, check=False)
    if not outj.exists():
        print(f"BRIDGE_FAILED rc={proc.returncode}\n{proc.stderr[-1200:]}"); return 1
    bridge = json.loads(outj.read_text())

    agg: dict[str, dict] = {v: {"n": 0, "hit": 0, "no_box": 0, "iou_sum": 0.0}
                            for v in ("A_native256", "B_upscale2x", "C_pad_canvas")}
    per = []
    for r in bridge.get("results", []):
        m = meta.get(r["query"] + "|" + Path(r["image"]).stem)
        if not m:
            continue
        v = m["variant"]
        agg[v]["n"] += 1
        box = r.get("bbox_xyxy")
        if box is None:
            agg[v]["no_box"] += 1
            iou = 0.0
        else:
            iou = _iou(box, m["gt"])
            agg[v]["iou_sum"] += iou
            if iou >= 0.5:
                agg[v]["hit"] += 1
        per.append({"image_id": m["image_id"], "variant": v, "expr": r["query"],
                    "iou": round(iou, 3), "pred_box": box, "gt": [round(x, 1) for x in m["gt"]]})

    summary = {v: {"acc@IoU0.5": round(d["hit"] / d["n"], 3) if d["n"] else None,
                   "no_box": d["no_box"], "mean_iou": round(d["iou_sum"] / d["n"], 3) if d["n"] else None,
                   "n": d["n"]} for v, d in agg.items()}
    report = {
        "experiment": "Track F - RemoteSAM input-resolution preparation",
        "date": time.strftime("%Y-%m-%d"),
        "n_cases": len(cases), "small_px": _SMALL, "big_px": _BIG,
        "wall_time_s": round(time.time() - t0, 1),
        "summary": summary,
        "reading": "compare B/C acc@IoU0.5 vs A. If neither materially beats A, "
                   "keep production preprocessing unchanged (no complexity added).",
        "per_case": per,
    }
    outp = REPO / "evaluation" / "reports" / f"exp_rs_resolution_{time.strftime('%Y%m%dT%H%M%S')}.json"
    outp.parent.mkdir(parents=True, exist_ok=True)
    outp.write_text(json.dumps(report, indent=2))
    print(json.dumps(summary, indent=2))
    print(f"wrote {outp}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
