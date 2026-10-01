"""EXP-004 Run 2 — stage 2: frozen-encoder feature extraction.

Runs INSIDE a research venv (`.venvs/croma` for --encoder croma, `.venvs/dofa`
for --encoder dofa). Loads the frozen encoder once, batches every patch from the
stage-1 npz, and writes the GAP / global feature vectors.

NOT product code. No network. No training here — pure forward passes on a frozen
checkpoint.

croma -> {optical_gap (N,768), joint_gap (N,768)}   (arm A vs arm B features)
dofa  -> {s2_feat (N,768), s1_feat (N,768)}          (arm A' vs arm C features: C = s2⊕s1)
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

import numpy as np
import torch

REPO_ROOT = Path(__file__).resolve().parents[2]
S2_WAVES = [0.443, 0.490, 0.560, 0.665, 0.705, 0.740, 0.783, 0.842, 0.865, 0.945, 1.610, 2.190]
S1_WAVES = [5.405, 5.405]


def _norm_per_sample(x: torch.Tensor) -> torch.Tensor:
    """(N,C,H,W) -> per-sample per-channel (mean +- 2 sigma) clip to [0,1]."""
    x = x.float()
    mean = x.mean(dim=(2, 3), keepdim=True)
    std = x.std(dim=(2, 3), keepdim=True)
    lo, hi = mean - 2 * std, mean + 2 * std
    return torch.clip((x - lo) / (hi - lo + 1e-8), 0, 1)


def _resize(x: torch.Tensor, size: int) -> torch.Tensor:
    if x.shape[-1] == size and x.shape[-2] == size:
        return x
    return torch.nn.functional.interpolate(x, size=size, mode="bilinear", align_corners=False)


def run_croma(s1: np.ndarray, s2: np.ndarray, ckpt: str, bs: int) -> dict[str, np.ndarray]:
    sys.path.insert(0, str(REPO_ROOT / "external" / "research" / "CROMA"))
    from use_croma import PretrainedCROMA

    res = 120
    model = PretrainedCROMA(pretrained_path=ckpt, size="base", modality="both", image_resolution=res).eval()
    opt, joint = [], []
    with torch.no_grad():
        for i in range(0, len(s1), bs):
            b1 = _norm_per_sample(_resize(torch.tensor(s1[i : i + bs]), res))
            b2 = _norm_per_sample(_resize(torch.tensor(s2[i : i + bs]), res))
            out = model(SAR_images=b1, optical_images=b2)
            opt.append(out["optical_GAP"].cpu().numpy())
            joint.append(out["joint_GAP"].cpu().numpy())
            print(f"  croma {min(i + bs, len(s1))}/{len(s1)}", flush=True)
    return {"optical_gap": np.concatenate(opt), "joint_gap": np.concatenate(joint)}


def run_dofa(s1: np.ndarray, s2: np.ndarray, ckpt: str, bs: int) -> dict[str, np.ndarray]:
    sys.path.insert(0, str(REPO_ROOT / "external" / "research" / "DOFA"))
    from dofa_v1 import vit_base_patch16

    res = 224
    model = vit_base_patch16()
    model.load_state_dict(torch.load(ckpt, map_location="cpu"), strict=False)
    model.eval()

    def feats(x_np: np.ndarray, waves: list[float]) -> np.ndarray:
        acc = []
        with torch.no_grad():
            for i in range(0, len(x_np), bs):
                xb = _norm_per_sample(_resize(torch.tensor(x_np[i : i + bs]), res))
                f = model.forward_features(xb, wave_list=waves)
                acc.append(np.atleast_2d(f.cpu().numpy()))
                print(f"  dofa {min(i + bs, len(x_np))}/{len(x_np)}", flush=True)
        return np.concatenate(acc)

    return {"s2_feat": feats(s2, S2_WAVES), "s1_feat": feats(s1, S1_WAVES)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--encoder", choices=["croma", "dofa"], required=True)
    ap.add_argument("--patches-npz", required=True)
    ap.add_argument("--checkpoint", required=True)
    ap.add_argument("--out-npz", required=True)
    ap.add_argument("--batch-size", type=int, default=16)
    a = ap.parse_args()

    d = np.load(a.patches_npz)
    s1, s2, y, ids = d["s1"], d["s2"], d["y"], d["ids"]
    t0 = time.time()
    torch.manual_seed(0)
    if a.encoder == "croma":
        out = run_croma(s1, s2, a.checkpoint, a.batch_size)
    else:
        out = run_dofa(s1, s2, a.checkpoint, a.batch_size)
    rt = time.time() - t0
    try:
        import psutil

        rss = psutil.Process(os.getpid()).memory_info().rss / 1e6
    except Exception:
        rss = None
    np.savez_compressed(a.out_npz, y=y, ids=ids, **out)
    meta = {
        "encoder": a.encoder,
        "n": int(len(y)),
        "runtime_s": round(rt, 1),
        "per_patch_s": round(rt / max(len(y), 1), 4),
        "cpu_rss_mb": round(rss, 1) if rss else None,
        "cuda": torch.cuda.is_available(),
        "feat_keys": {k: list(v.shape) for k, v in out.items()},
    }
    Path(a.out_npz).with_suffix(".meta.json").write_text(json.dumps(meta, indent=2))
    print(json.dumps(meta, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
