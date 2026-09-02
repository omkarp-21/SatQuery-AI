"""Qwen2-VL-family single-image VQA bridge — runs INSIDE .venvs/tinyrs.

Used by the TinyRS adapter (and, for the EXP-002 control, Qwen2-VL-2B). Loads a
`Qwen2VLForConditionalGeneration` / `Qwen2_5_VLForConditionalGeneration`
checkpoint on CPU and answers one image + one question per job.

SatQuery product code never imports this. Called by
`packages/model_adapters/tinyrs.py` via subprocess with an explicit arg list.

Usage:
  python qwen2vl_vqa_infer.py --weights <dir> --jobs-json <in.json> \
      --out-json <out.json> [--arch qwen2_vl|qwen2_5_vl] [--max-new-tokens 24]

jobs-json: [{"image": "<path>", "question": "<text>"}]
"""

from __future__ import annotations

import argparse
import json
import sys
import time


def _rss_mb() -> float:
    try:
        import psutil  # noqa: PLC0415

        return round(psutil.Process().memory_info().rss / 1e6, 1)
    except Exception:  # noqa: BLE001
        return -1.0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--weights", required=True)
    ap.add_argument("--jobs-json", required=True)
    ap.add_argument("--out-json", required=True)
    ap.add_argument("--arch", default="qwen2_vl", choices=["qwen2_vl", "qwen2_5_vl"])
    ap.add_argument("--max-new-tokens", type=int, default=24)
    a = ap.parse_args()

    import torch  # noqa: PLC0415
    from PIL import Image  # noqa: PLC0415
    from transformers import AutoProcessor  # noqa: PLC0415

    if a.arch == "qwen2_5_vl":
        from transformers import Qwen2_5_VLForConditionalGeneration as Cls  # noqa: PLC0415
    else:
        from transformers import Qwen2VLForConditionalGeneration as Cls  # noqa: PLC0415

    out: dict = {"model": "qwen2vl", "weights": a.weights, "arch": a.arch,
                 "env": {"python": sys.version.split()[0], "torch": torch.__version__},
                 "results": []}

    t0 = time.time()
    try:
        model = Cls.from_pretrained(a.weights, torch_dtype=torch.float32, low_cpu_mem_usage=True)
        model.eval()
        proc = AutoProcessor.from_pretrained(a.weights)
    except Exception as exc:  # noqa: BLE001
        out["ok"] = False
        out["status"] = "LOAD_FAILED"
        out["error"] = f"{type(exc).__name__}: {exc}"
        _write(a.out_json, out)
        return 1
    out["load_time_s"] = round(time.time() - t0, 1)
    out["cpu_rss_mb_after_load"] = _rss_mb()

    jobs = json.loads(open(a.jobs_json, encoding="utf-8").read())
    for i, job in enumerate(jobs):
        row: dict = {"image": job["image"], "question": job["question"]}
        t1 = time.time()
        try:
            img = Image.open(job["image"]).convert("RGB")
            msg = [{"role": "user", "content": [
                {"type": "image"}, {"type": "text", "text": job["question"]}]}]
            text = proc.apply_chat_template(msg, tokenize=False, add_generation_prompt=True)
            inputs = proc(text=[text], images=[img], return_tensors="pt")
            with torch.no_grad():
                gen = model.generate(**inputs, max_new_tokens=a.max_new_tokens, do_sample=False)
            ans = proc.batch_decode(gen[:, inputs["input_ids"].shape[1]:],
                                    skip_special_tokens=True)[0].strip()
            row["answer"] = ans
            row["status"] = "ok"
        except Exception as exc:  # noqa: BLE001
            row["answer"] = ""
            row["status"] = "error"
            row["error"] = f"{type(exc).__name__}: {exc}"
        row["latency_s"] = round(time.time() - t1, 2)
        out["results"].append(row)
        if i == 0:
            out["warm_latency_s"] = row["latency_s"]

    out["cpu_rss_mb_peak"] = _rss_mb()
    out["ok"] = True
    out["status"] = "ok"
    _write(a.out_json, out)
    return 0


def _write(path: str, obj: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2)
    print(f"wrote {path}")


if __name__ == "__main__":
    sys.exit(main())
