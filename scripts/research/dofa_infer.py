"""Research-env bridge for DOFA (runs INSIDE .venvs/dofa).

NOT product code. Encodes one image tensor with the wavelength-conditioned DOFA
ViT-B and returns the global feature.

args:  --x-npy <path (C,H,W)> --modality s1|s2  --checkpoint <DOFA_ViT_base_e100.pth>
       [--random 0]  --out-json <json>
out:   {ok, model, modality, feature, dim, runtime_s}
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import traceback

REPO = os.path.join(os.path.dirname(__file__), "..", "..", "external", "research", "DOFA")
S2_WAVES = [0.443, 0.490, 0.560, 0.665, 0.705, 0.740, 0.783, 0.842, 0.865, 0.945, 1.610, 2.190]
S1_WAVES = [5.405, 5.405]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--x-npy")
    ap.add_argument("--modality", choices=["s1", "s2"], required=True)
    ap.add_argument("--checkpoint", required=True)
    ap.add_argument("--size", type=int, default=224)
    ap.add_argument("--random", type=int, default=0)
    ap.add_argument("--out-json", required=True)
    a = ap.parse_args()
    try:
        sys.path.insert(0, os.path.abspath(REPO))
        import numpy as np
        import torch
        from dofa_v1 import vit_base_patch16

        t0 = time.time()
        waves = S1_WAVES if a.modality == "s1" else S2_WAVES
        ch = 2 if a.modality == "s1" else 12
        if a.random:
            x = torch.randn(1, ch, a.size, a.size)
        else:
            x = torch.tensor(np.load(a.x_npy)).float().unsqueeze(0)
            x = torch.nn.functional.interpolate(x, size=a.size, mode="bilinear", align_corners=False)

        model = vit_base_patch16()
        model.load_state_dict(torch.load(a.checkpoint, map_location="cpu"), strict=False)
        model.eval()
        with torch.no_grad():
            feat = model.forward_features(x, wave_list=waves)[0]
        payload = {
            "ok": True,
            "model": "dofa",
            "modality": a.modality,
            "feature": [round(v, 6) for v in feat.tolist()],
            "dim": int(feat.shape[0]),
            "runtime_s": round(time.time() - t0, 3),
        }
    except Exception as exc:  # noqa: BLE001
        payload = {"ok": False, "error": f"{type(exc).__name__}: {exc}", "trace": traceback.format_exc()}
    with open(a.out_json, "w") as fh:
        json.dump(payload, fh)
    return 0 if payload.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
