"""Research-env bridge for ChangeFormer (runs INSIDE .venvs/changeformer).

NOT product code. It is allowed to import from external/research/ChangeFormer
because it executes in the isolated research venv, invoked by the SatQuery adapter
via subprocess with an explicit argument list (`.claude/rules/ai-models.md`,
`.claude/rules/security.md`). It never touches the SatQuery packages.

Contract:
    stdin/args:  --a <img> --b <img> --checkpoint-dir <dir> [--net-g ChangeFormerV6]
                 [--embed-dim 256] [--out-mask <png>] --out-json <json>
    stdout:      nothing meaningful (progress only)
    --out-json:  {"ok", "mask_path", "height", "width", "changed_pixels",
                  "total_pixels", "changed_fraction", "model", "checkpoint_name",
                  "runtime_s"}  or  {"ok": false, "error": "..."}
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import tempfile
import traceback

REPO = os.path.join(os.path.dirname(__file__), "..", "..", "external", "research", "ChangeFormer")


def _read_rgb(path: str):
    import numpy as np

    ext = os.path.splitext(path)[1].lower()
    if ext in (".tif", ".tiff"):
        import tifffile

        arr = tifffile.imread(path)
    else:
        from PIL import Image

        arr = np.array(Image.open(path).convert("RGB"))
    arr = np.asarray(arr)
    if arr.ndim == 2:
        arr = np.stack([arr] * 3, axis=-1)
    if arr.shape[0] in (3, 4) and arr.ndim == 3 and arr.shape[-1] not in (3, 4):
        arr = np.transpose(arr, (1, 2, 0))
    return arr[:, :, :3]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--a", required=True)
    ap.add_argument("--b", required=True)
    ap.add_argument("--checkpoint-dir", required=True)
    ap.add_argument("--checkpoint-name", default="best_ckpt.pt")
    ap.add_argument("--net-g", default="ChangeFormerV6")
    ap.add_argument("--embed-dim", type=int, default=256)
    ap.add_argument("--out-mask", default=None)
    ap.add_argument("--out-json", required=True)
    args = ap.parse_args()

    try:
        sys.path.insert(0, os.path.abspath(REPO))
        import numpy as np
        import torch
        import torchvision.transforms.functional as TF
        from argparse import Namespace
        from models.basic_model import CDEvaluator

        t0 = time.time()
        eval_args = Namespace(
            gpu_ids=[],
            project_name="bridge",
            net_G=args.net_g,
            embed_dim=args.embed_dim,
            n_class=2,
            output_folder=tempfile.mkdtemp(),
            checkpoint_dir=os.path.abspath(args.checkpoint_dir),
        )
        model = CDEvaluator(eval_args)
        model.load_checkpoint(args.checkpoint_name)
        model.eval()

        a = _read_rgb(args.a)
        b = _read_rgb(args.b)
        if a.shape != b.shape:
            raise ValueError(f"A/B pixel shapes differ: {a.shape} vs {b.shape}")

        def pre(x):
            t = TF.to_tensor(x.astype("uint8"))
            return TF.normalize(t, [0.5, 0.5, 0.5], [0.5, 0.5, 0.5]).unsqueeze(0)

        batch = {"A": pre(a), "B": pre(b), "name": ["pair"]}
        with torch.no_grad():
            # _forward_pass already returns _visualize_pred(): argmax over classes,
            # scaled to 0/255, shape (1, 1, H, W). Do NOT argmax again.
            pred_vis = model._forward_pass(batch)
        mask = pred_vis[0, 0].cpu().numpy().astype("uint8")  # 0 or 255

        h, w = mask.shape
        changed = int((mask > 127).sum())
        total = int(h * w)

        mask_path = args.out_mask
        if mask_path:
            from PIL import Image

            Image.fromarray(mask).save(mask_path)

        out = {
            "ok": True,
            "mask_path": mask_path,
            "height": h,
            "width": w,
            "changed_pixels": changed,
            "total_pixels": total,
            "changed_fraction": (changed / total) if total else 0.0,
            "model": "ChangeFormerV6",
            "checkpoint_name": args.checkpoint_name,
            "runtime_s": round(time.time() - t0, 3),
        }
    except Exception as exc:  # noqa: BLE001 - bridge reports any failure as JSON
        out = {"ok": False, "error": f"{type(exc).__name__}: {exc}", "trace": traceback.format_exc()}

    with open(args.out_json, "w") as fh:
        json.dump(out, fh)
    return 0 if out.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
