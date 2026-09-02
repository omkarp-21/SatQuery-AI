"""EXP-002 (Track C) — local VQA on an RSVQA-LR yes/no sample.

Runs a Qwen2-VL-family model (TinyRS-2B or Qwen2-VL-2B) against the first 40
yes/no questions of the RSVQA-LR-2k validation parquet
(`dmarsili/RSVQA-LR-2k`, non-gated mirror), on CPU.

Measures: balanced accuracy, per-query latency (p50/p95), load time, CPU RSS,
failure rate + categories.  Internal gate: balanced accuracy >= 0.60 (NOT an
official SIH score).

Usage:
  python exp002_vqa_rsvqa.py --model tinyrs   --weights models/cache/tinyrs/Qwen2-VL-TinyRS
  python exp002_vqa_rsvqa.py --model qwen2vl2b --weights models/cache/qwen2vl2b/Qwen2-VL-2B-Instruct
"""

from __future__ import annotations

import argparse
import io
import json
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
_PARQUET = REPO / "models/cache/rsvqa_lr/data/validation-00000-of-00001.parquet"
_N = 40
_GATE = 0.60


def _rss_mb() -> float:
    try:
        import psutil

        return round(psutil.Process().memory_info().rss / 1e6, 1)
    except Exception:  # noqa: BLE001
        return -1.0


def _load_sample() -> list[dict]:
    import pyarrow.parquet as pq

    rows = pq.read_table(_PARQUET).to_pylist()
    out: list[dict] = []
    for i, r in enumerate(rows):
        a = str(r["answer"]).strip().lower()
        if a not in ("yes", "no"):
            continue
        out.append({"row": i, "question": r["question"], "gold": 1 if a == "yes" else 0,
                    "image_bytes": r["image"]["bytes"]})
        if len(out) >= _N:
            break
    return out


def _norm_yesno(s: str) -> int | None:
    s = s.strip().lower()
    if s.startswith("yes") or s in ("true", "1"):
        return 1
    if s.startswith("no") or s in ("false", "0"):
        return 0
    return None


def _balanced_acc(pairs: list[tuple[int, int]]) -> float:
    tp = sum(1 for g, p in pairs if g == 1 and p == 1)
    tn = sum(1 for g, p in pairs if g == 0 and p == 0)
    pos = sum(1 for g, _ in pairs if g == 1)
    neg = sum(1 for g, _ in pairs if g == 0)
    if not pos or not neg:
        return float("nan")
    return 0.5 * (tp / pos + tn / neg)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True, choices=["tinyrs", "qwen2vl2b", "rscovlm-3b"])
    ap.add_argument("--weights", required=True)
    ap.add_argument("--out-json", default=None)
    ap.add_argument("--arch", default="qwen2_vl", choices=["qwen2_vl", "qwen2_5_vl"])
    a = ap.parse_args()

    import torch
    from PIL import Image
    from transformers import AutoProcessor

    if a.arch == "qwen2_5_vl":
        from transformers import Qwen2_5_VLForConditionalGeneration as Cls
    else:
        from transformers import Qwen2VLForConditionalGeneration as Cls

    rep: dict = {"experiment": "EXP-002 Track C - local VQA on RSVQA-LR yes/no",
                 "model": a.model, "weights": a.weights, "n": _N, "gate": _GATE,
                 "date": time.strftime("%Y-%m-%d"),
                 "env": {"python": sys.version.split()[0], "torch": torch.__version__}}

    if not Path(a.weights, "config.json").exists():
        rep["status"] = "ARTIFACT_MISSING"
        _write(a, rep)
        return 1
    sample = _load_sample()
    if len(sample) < _N:
        rep["status"] = "DATASET_MISSING"
        rep["note"] = f"only {len(sample)} yes/no rows resolved"
        _write(a, rep)
        return 2

    t0 = time.time()
    model = Cls.from_pretrained(a.weights, torch_dtype=torch.float32, low_cpu_mem_usage=True)
    model.eval()
    proc = AutoProcessor.from_pretrained(a.weights)
    rep["load_time_s"] = round(time.time() - t0, 1)
    rep["cpu_rss_mb_after_load"] = _rss_mb()

    pairs: list[tuple[int, int]] = []
    lat: list[float] = []
    fails: dict[str, int] = {}
    preds: list[dict] = []
    for k, ex in enumerate(sample):
        img = Image.open(io.BytesIO(ex["image_bytes"])).convert("RGB")
        msg = [{"role": "user", "content": [
            {"type": "image"},
            {"type": "text", "text": ex["question"].rstrip("?") + "? Answer with only 'yes' or 'no'."}]}]
        text = proc.apply_chat_template(msg, tokenize=False, add_generation_prompt=True)
        t1 = time.time()
        try:
            inputs = proc(text=[text], images=[img], return_tensors="pt")
            with torch.no_grad():
                out = model.generate(**inputs, max_new_tokens=6, do_sample=False)
            raw = proc.batch_decode(out[:, inputs["input_ids"].shape[1]:], skip_special_tokens=True)[0]
        except Exception as exc:  # noqa: BLE001
            raw = ""
            fails[type(exc).__name__] = fails.get(type(exc).__name__, 0) + 1
        dt = time.time() - t1
        lat.append(dt)
        pred = _norm_yesno(raw)
        if pred is None:
            fails["unparseable"] = fails.get("unparseable", 0) + 1
        else:
            pairs.append((ex["gold"], pred))
        preds.append({"row": ex["row"], "q": ex["question"], "gold": ex["gold"],
                      "raw": raw.strip()[:40], "pred": pred, "lat_s": round(dt, 2)})
        if k == 0:
            rep["warm_latency_s"] = round(dt, 1)

    lat_s = sorted(lat)
    bal = _balanced_acc(pairs)
    rep.update(
        n_scored=len(pairs),
        balanced_accuracy=None if bal != bal else round(bal, 4),  # NaN guard
        passes_gate=bool(bal == bal and bal >= _GATE),
        failure_rate=round(1 - len(pairs) / _N, 4),
        failure_categories=fails,
        p50_latency_s=round(lat_s[len(lat_s) // 2], 2),
        p95_latency_s=round(lat_s[min(len(lat_s) - 1, int(0.95 * len(lat_s)))], 2),
        cpu_rss_mb_peak=_rss_mb(),
        status="OK",
        predictions=preds,
    )
    _write(a, rep)
    print(f"{a.model}: balanced_acc={rep['balanced_accuracy']} (>= {_GATE}? {rep['passes_gate']}) "
          f"n_scored={rep['n_scored']} fail_rate={rep['failure_rate']} "
          f"p50={rep['p50_latency_s']}s rss_peak={rep['cpu_rss_mb_peak']}MB")
    return 0


def _write(a, rep: dict) -> None:
    p = Path(a.out_json) if a.out_json else (
        REPO / "evaluation" / "reports" / f"exp002_vqa_{a.model}_{time.strftime('%Y%m%dT%H%M%S')}.json")
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(rep, indent=2))
    print(f"wrote {p}")


if __name__ == "__main__":
    sys.exit(main())
