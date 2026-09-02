"""Research-env bridge for CROMA (runs INSIDE .venvs/croma).

NOT product code. Encodes one co-registered Sentinel-1 (2ch) + Sentinel-2 (12ch)
patch and returns the GAP feature vectors.

args:  --s1-npy <path (2,H,W) float or uint8> --s2-npy <path (12,H,W)>
       --checkpoint <CROMA_base.pt> [--size base] [--resolution 120]
       [--random 0]  --out-json <json>
out:   {ok, model, size, joint_gap, optical_gap, sar_gap, dim, n_patches, runtime_s}
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import traceback

REPO = os.path.join(os.path.dirname(__file__), "..", "..", "external", "research", "CROMA")


def _norm(x):
    import torch

    x = x.float()
    out = []
    for c in range(x.shape[1]):
        mn = x[:, c].mean() - 2 * x[:, c].std()
        mx = x[:, c].mean() + 2 * x[:, c].std()
        v = torch.clip((x[:, c] - mn) / (mx - mn + 1e-8), 0, 1)
        out.append(v.unsqueeze(1))
    return torch.cat(out, dim=1)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--s1-npy")
    ap.add_argument("--s2-npy")
    ap.add_argument("--checkpoint", required=True)
    ap.add_argument("--size", default="base")
    ap.add_argument("--resolution", type=int, default=120)
    ap.add_argument("--random", type=int, default=0)
    ap.add_argument("--lora-weights", default=None,
                    help="OPTIONAL EXP-008 LoRA delta (torch.save dict). Absent = frozen CROMA.")
    ap.add_argument("--out-json", required=True)
    a = ap.parse_args()
    try:
        sys.path.insert(0, os.path.abspath(REPO))
        import numpy as np
        import torch
        from use_croma import PretrainedCROMA

        t0 = time.time()
        R = a.resolution
        if a.random:
            s1 = torch.randn(1, 2, R, R)
            s2 = torch.randn(1, 12, R, R)
        else:
            s1 = torch.tensor(np.load(a.s1_npy)).unsqueeze(0)
            s2 = torch.tensor(np.load(a.s2_npy)).unsqueeze(0)
        s1 = _norm(s1)
        s2 = _norm(s2)

        model = PretrainedCROMA(pretrained_path=a.checkpoint, size=a.size,
                                modality="both", image_resolution=R).eval()
        encoder_mode = "frozen"
        if a.lora_weights:
            # EXP-008 LoRA delta: {name: (A, B, scaling)} applied to matching
            # Linear weights. Applied as a merged weight delta so inference code
            # is unchanged. If nothing matches, fail loudly (never silently frozen).
            delta = torch.load(a.lora_weights, map_location="cpu")
            applied = 0
            sd = model.state_dict()
            for name, mod in model.named_modules():
                key = f"{name}.weight"
                if name in delta and key in sd and hasattr(mod, "weight"):
                    A, B, scaling = delta[name]
                    with torch.no_grad():
                        mod.weight.add_((B @ A) * float(scaling))
                    applied += 1
            if applied == 0:
                raise RuntimeError(f"--lora-weights supplied but 0 layers matched in {a.lora_weights}")
            encoder_mode = f"lora_adapted ({applied} layers)"
        with torch.no_grad():
            out = model(SAR_images=s1, optical_images=s2)
        payload = {
            "ok": True,
            "model": "croma",
            "size": a.size,
            "encoder_mode": encoder_mode,
            "joint_gap": [round(v, 6) for v in out["joint_GAP"][0].tolist()],
            "optical_gap": [round(v, 6) for v in out["optical_GAP"][0].tolist()],
            "sar_gap": [round(v, 6) for v in out["SAR_GAP"][0].tolist()],
            "dim": int(out["joint_GAP"].shape[1]),
            "n_patches": int(out["joint_encodings"].shape[1]),
            "runtime_s": round(time.time() - t0, 3),
        }
    except Exception as exc:  # noqa: BLE001
        payload = {"ok": False, "error": f"{type(exc).__name__}: {exc}", "trace": traceback.format_exc()}
    with open(a.out_json, "w") as fh:
        json.dump(payload, fh)
    return 0 if payload.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
