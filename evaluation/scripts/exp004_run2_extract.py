"""EXP-004 Run 2 — stage 1: extract DFC2020 validation patches to npz.

Reads the raw DFC2020 `ROIs0000_validation` GeoTIFFs (Sentinel-1 SAR 2-band dB,
Sentinel-2 optical 13-band, DFC high-res 10-class label) straight from the
downloaded zips, builds a per-patch tensor set + a dominant-land-cover label, and
freezes a deterministic train/eval split.

NOT product code — an evaluation harness. Runs in `.venvs/satquery` (needs
rasterio). No network. No synthetic data.

out:
  <out_dir>/dfc2020_patches_train.npz   ids, s1 (N,2,S,S) f32, s2 (N,12,S,S) f32, y (N,) int
  <out_dir>/dfc2020_patches_eval.npz
  evaluation/datasets/dfc2020_exp004_split.json   frozen id lists + provenance
"""

from __future__ import annotations

import argparse
import io
import json
import time
import zipfile
from pathlib import Path

import numpy as np
import rasterio

# SEN12MS / DFC2020 Sentinel-2 is 13-band: B1 B2 B3 B4 B5 B6 B7 B8 B8A B9 B10 B11 B12
# CROMA + DOFA expect 12 bands (no B10 cirrus) -> drop 0-based index 10.
S2_KEEP = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 11, 12]

# DFC2020 high-res label codes -> IGBP-simplified land-cover names (8-class scheme;
# 3 Savanna and 8 Snow/Ice do not occur in the validation ROIs).
DFC_CLASSES = {
    1: "Forest",
    2: "Shrubland",
    3: "Savanna",
    4: "Grassland",
    5: "Wetlands",
    6: "Croplands",
    7: "Urban/Built-up",
    8: "Snow/Ice",
    9: "Barren",
    10: "Water",
}

REPO_ROOT = Path(__file__).resolve().parents[2]


def _index(zf: zipfile.ZipFile, tag: str) -> dict[int, str]:
    """patch-id -> archive member name (prefix-agnostic; skips macOS ._ sidecars)."""
    out: dict[int, str] = {}
    for n in zf.namelist():
        base = n.rsplit("/", 1)[-1]
        if base.startswith(f"ROIs0000_validation_{tag}_0_p") and base.endswith(".tif") and not base.startswith("._"):
            out[int(base[:-4].split("_p")[-1])] = n
    return out


def _read_tif_from_zip(zf: zipfile.ZipFile, name: str) -> np.ndarray:
    with zf.open(name) as fh:
        data = fh.read()
    with rasterio.open(io.BytesIO(data)) as ds:
        return ds.read()  # (bands, H, W)


def _resize(arr: np.ndarray, size: int) -> np.ndarray:
    """Bilinear-ish resize (C,H,W)->(C,size,size) via numpy; avoids a torch dep here."""
    c, h, w = arr.shape
    if (h, w) == (size, size):
        return arr.astype(np.float32)
    ys = np.linspace(0, h - 1, size).round().astype(int)
    xs = np.linspace(0, w - 1, size).round().astype(int)
    return arr[:, ys][:, :, xs].astype(np.float32)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dfc-dir", default=str(REPO_ROOT / "models" / "cache" / "dfc2020"))
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--size", type=int, default=128)
    ap.add_argument("--n-train", type=int, default=400)
    ap.add_argument("--n-eval", type=int, default=200)
    ap.add_argument("--seed", type=int, default=20260902)
    ap.add_argument("--split-out", default=None,
                    help="where to write the split doc (default: evaluation/datasets/dfc2020_exp004_split.json; "
                         "pass a different path for a larger G17 split so the G12 frozen split is untouched)")
    a = ap.parse_args()

    dfc_dir = Path(a.dfc_dir)
    out_dir = Path(a.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    z_s1 = zipfile.ZipFile(dfc_dir / "s1_validation.zip")
    z_s2 = zipfile.ZipFile(dfc_dir / "s2_validation.zip")
    z_dfc = zipfile.ZipFile(dfc_dir / "dfc_validation.zip")
    ix_s1, ix_s2, ix_dfc = _index(z_s1, "s1"), _index(z_s2, "s2"), _index(z_dfc, "dfc")

    common = sorted(set(ix_s1) & set(ix_s2) & set(ix_dfc))
    print(f"{len(common)} patches present in s1 AND s2 AND dfc")

    rng = np.random.default_rng(a.seed)
    order = list(common)
    rng.shuffle(order)
    train_ids = sorted(order[: a.n_train])
    eval_ids = sorted(order[a.n_train : a.n_train + a.n_eval])

    def build(ids: list[int], split: str) -> dict[str, np.ndarray]:
        s1s, s2s, ys, kept = [], [], [], []
        t0 = time.time()
        for i, pid in enumerate(ids):
            s1 = _read_tif_from_zip(z_s1, ix_s1[pid])
            s2 = _read_tif_from_zip(z_s2, ix_s2[pid])
            dfc = _read_tif_from_zip(z_dfc, ix_dfc[pid])
            if s1.shape[0] != 2 or s2.shape[0] != 13:
                print(f"  skip p{pid}: s1 {s1.shape} s2 {s2.shape}")
                continue
            lab = dfc[0].astype(int).ravel()
            lab = lab[(lab >= 1) & (lab <= 10)]
            if lab.size == 0:
                print(f"  skip p{pid}: no valid label pixels")
                continue
            dom = int(np.bincount(lab, minlength=11).argmax())
            s1s.append(_resize(s1, a.size))
            s2s.append(_resize(s2[S2_KEEP], a.size))
            ys.append(dom)
            kept.append(pid)
            if (i + 1) % 100 == 0:
                print(f"  {split} {i + 1}/{len(ids)}  ({time.time() - t0:.0f}s)")
        return {
            "ids": np.array(kept, dtype=int),
            "s1": np.stack(s1s).astype(np.float32),
            "s2": np.stack(s2s).astype(np.float32),
            "y": np.array(ys, dtype=int),
        }

    train = build(train_ids, "train")
    ev = build(eval_ids, "eval")
    np.savez_compressed(out_dir / "dfc2020_patches_train.npz", **train)
    np.savez_compressed(out_dir / "dfc2020_patches_eval.npz", **ev)

    def dist(y: np.ndarray) -> dict[str, int]:
        return {DFC_CLASSES[int(c)]: int((y == c).sum()) for c in sorted(set(y.tolist()))}

    split_doc = {
        "experiment": "EXP-004 Run 2 — DFC2020 optical+SAR downstream probe",
        "dataset_source": "HF dataset 125oii/dfc2020 (non-gated mirror of IEEE GRSS DFC2020)",
        "split_origin": "DFC2020 official ROIs0000_validation (986 patches, 256x256)",
        "acquired": time.strftime("%Y-%m-%d"),
        "files": ["s1_validation.zip", "s2_validation.zip", "dfc_validation.zip"],
        "modalities": {
            "s1": "Sentinel-1 GRD, 2 band (VV, VH), dB",
            "s2": "Sentinel-2 L1C, 13 band -> 12 kept (drop B10 cirrus), TOA reflectance*1e4",
            "label": "DFC2020 high-res 10-class land cover; per-patch DOMINANT class",
        },
        "preprocessing": f"read raw GeoTIFF -> keep bands -> nearest-resize to {a.size}px -> "
        "per-channel (mean+-2sigma) clip-normalise at feature-extraction time",
        "task": "single-label patch classification: dominant DFC land-cover class",
        "metric": "macro-F1 (primary), overall accuracy, per-class F1",
        "seed": a.seed,
        "n_train": int(train["y"].size),
        "n_eval": int(ev["y"].size),
        "train_class_distribution": dist(train["y"]),
        "eval_class_distribution": dist(ev["y"]),
        "train_ids": train["ids"].tolist(),
        "eval_ids": ev["ids"].tolist(),
        "note": "sanity-scale: 600 patches of the 986-patch validation split. A real "
        "number (integrated encoder -> frozen probe -> metric), NOT a full benchmark.",
    }
    sp = (Path(a.split_out) if a.split_out
          else REPO_ROOT / "evaluation" / "datasets" / "dfc2020_exp004_split.json")
    sp.parent.mkdir(parents=True, exist_ok=True)
    sp.write_text(json.dumps(split_doc, indent=2))
    print(f"wrote {sp}")
    print(f"train {train['y'].size}  eval {ev['y'].size}")
    print("train dist:", dist(train["y"]))
    print("eval  dist:", dist(ev["y"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
