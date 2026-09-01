"""Research-env bridge for RemoteCLIP (runs INSIDE .venvs/remoteclip).

NOT product code. Zero-shot classification / retrieval scoring for one image over
a list of text prompts, using the official open_clip load path.

args:  --image <path> --prompts "p1;p2;p3" --checkpoint <RemoteCLIP-*.pt>
       [--model-name ViT-B-32] --out-json <json>
out:   {ok, model, model_name, prompts, probs, top_index, top_prompt,
        image_embed_dim, runtime_s}
"""

from __future__ import annotations

import argparse
import json
import time
import traceback


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--image", required=True)
    ap.add_argument("--prompts", required=True, help="';'-separated text prompts")
    ap.add_argument("--checkpoint", required=True)
    ap.add_argument("--model-name", default="ViT-B-32")
    ap.add_argument("--out-json", required=True)
    a = ap.parse_args()
    try:
        import torch
        import open_clip
        from PIL import Image

        t0 = time.time()
        model, _, preprocess = open_clip.create_model_and_transforms(a.model_name)
        tok = open_clip.get_tokenizer(a.model_name)
        model.load_state_dict(torch.load(a.checkpoint, map_location="cpu"))
        model.eval()

        prompts = [p.strip() for p in a.prompts.split(";") if p.strip()]
        img = preprocess(Image.open(a.image).convert("RGB")).unsqueeze(0)
        text = tok(prompts)
        with torch.no_grad():
            imf = model.encode_image(img)
            txf = model.encode_text(text)
            imf = imf / imf.norm(dim=-1, keepdim=True)
            txf = txf / txf.norm(dim=-1, keepdim=True)
            probs = (100.0 * imf @ txf.T).softmax(dim=-1)[0].tolist()

        top = int(max(range(len(probs)), key=lambda i: probs[i]))
        out = {
            "ok": True,
            "model": "remoteclip",
            "model_name": a.model_name,
            "prompts": prompts,
            "probs": [round(p, 5) for p in probs],
            "top_index": top,
            "top_prompt": prompts[top],
            "image_embed_dim": int(imf.shape[1]),
            "runtime_s": round(time.time() - t0, 3),
        }
    except Exception as exc:  # noqa: BLE001
        out = {"ok": False, "error": f"{type(exc).__name__}: {exc}", "trace": traceback.format_exc()}
    with open(a.out_json, "w") as fh:
        json.dump(out, fh)
    return 0 if out.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
