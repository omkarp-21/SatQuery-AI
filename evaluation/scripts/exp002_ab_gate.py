"""EXP-002 / G5A — A/B reproduction gate harness.

Runs the *same* fixed samples across the local single-image candidates and records
every metric the G5A brief asks for. It does not select the winner and it does not
touch product code — it only measures.

Candidates (role-frozen, ADR-011/012):
    rscovlm-3b   LOCAL A/B PRIMARY    (Qwen2.5-VL-3B; HF Qingyun/rscovlm)
    tinyrs-2b    LOCAL A/B FALLBACK   (Qwen2-VL-2B;  HF aybora/Qwen2-VL-TinyRS)
    qwen2vl-2b   GENERIC CONTROL      (Qwen2-VL-2B;  HF Qwen/Qwen2-VL-2B-Instruct)

Tasks:
    VQA        RSVQA-LR sample  -> balanced accuracy   (threshold 0.60)
    grounding  DIOR-RSVG sample -> acc@IoU0.5           (threshold 0.30)

Thresholds are INTERNAL USABILITY THRESHOLDS, not official SIH scoring criteria.

Usage:
    python exp002_ab_gate.py --model qwen2vl-2b --quant 4bit
    python exp002_ab_gate.py --model rscovlm-3b --resolve   # just materialise sample IDs

Exit status is written into the report JSON as ``status``:
    ARTIFACT_MISSING  weights not on disk
    DATASET_MISSING   RSVQA-LR / DIOR-RSVG not on disk
    OK                ran; see pass/fail per task
"""

from __future__ import annotations

import argparse
import json
import platform
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[2]
DATASETS = REPO / "evaluation" / "datasets"
REPORTS = REPO / "evaluation" / "reports"
CACHE = REPO / "models" / "cache"

MODELS: dict[str, dict[str, str]] = {
    "rscovlm-3b": {
        "hf": "Qingyun/rscovlm",  # collection; concrete repo id set once known
        "local": str(CACHE / "rscovlm" / "RSCoVLM-3B"),
        "arch": "qwen2_5_vl",
        "role": "LOCAL A/B PRIMARY",
    },
    "tinyrs-2b": {
        "hf": "aybora/Qwen2-VL-TinyRS",
        "local": str(CACHE / "tinyrs" / "Qwen2-VL-TinyRS"),
        "arch": "qwen2_vl",
        "role": "LOCAL A/B FALLBACK",
    },
    "qwen2vl-2b": {
        "hf": "Qwen/Qwen2-VL-2B-Instruct",
        "local": str(CACHE / "qwen2vl2b" / "Qwen2-VL-2B-Instruct"),
        "arch": "qwen2_vl",
        "role": "GENERIC CONTROL",
    },
}

VQA_THRESHOLD = 0.60
GND_THRESHOLD = 0.30
LATENCY_BUDGET_S = 45.0


@dataclass
class TaskResult:
    n: int = 0
    n_scored: int = 0
    score: float | None = None
    metric: str = ""
    threshold: float = 0.0
    passed: bool | None = None
    failure_rate: float | None = None
    failure_categories: dict[str, int] = field(default_factory=dict)
    per_query_latency_s: list[float] = field(default_factory=list)
    predictions_path: str | None = None


@dataclass
class Report:
    experiment: str = "EXP-002 / G5A A/B gate"
    frozen_samples: str = "2026-09-01"
    model_key: str = ""
    role: str = ""
    checkpoint: str = ""
    checkpoint_sha256: str | None = None
    quantization: str = "none"
    parameters: str | None = None
    gpu_memory_mb: float | None = None
    cpu_memory_mb: float | None = None
    load_time_s: float | None = None
    warm_latency_s: float | None = None
    vqa: dict[str, Any] = field(default_factory=dict)
    grounding: dict[str, Any] = field(default_factory=dict)
    environment: dict[str, str] = field(default_factory=dict)
    status: str = "OK"
    notes: list[str] = field(default_factory=list)
    timestamp: str = ""


# --------------------------------------------------------------------------- #
# dataset resolution
# --------------------------------------------------------------------------- #
def _rsvqa_files_present() -> Path | None:
    for base in (DATASETS / "RSVQA-LR", DATASETS / "rsvqa_lr", CACHE / "RSVQA-LR"):
        if (base / "LR_split_test_questions.json").exists():
            return base
    return None


def _dior_files_present() -> Path | None:
    for base in (DATASETS / "DIOR-RSVG", DATASETS / "dior_rsvg", CACHE / "DIOR-RSVG"):
        if (base / "test.txt").exists() and (base / "Annotations").is_dir():
            return base
    return None


def resolve_samples() -> tuple[list[dict], list[dict]]:
    """Materialise the frozen sample ID lists from the selection policy.

    Returns (vqa_items, grounding_items). Raises FileNotFoundError with a clear
    message if a dataset is not on disk.
    """
    spec_vqa = json.loads((DATASETS / "rsvqa_lr_sample.json").read_text())
    spec_gnd = json.loads((DATASETS / "dior_rsvg_sample.json").read_text())

    rs_base = _rsvqa_files_present()
    if rs_base is None:
        raise FileNotFoundError(
            "RSVQA-LR not found. Place LR_split_test_questions.json + "
            "LR_split_test_answers.json + Images_LR/ under evaluation/datasets/RSVQA-LR/."
        )
    di_base = _dior_files_present()
    if di_base is None:
        raise FileNotFoundError(
            "DIOR-RSVG not found. Place test.txt + Annotations/ + JPEGImages/ "
            "under evaluation/datasets/DIOR-RSVG/."
        )

    # --- RSVQA-LR ---
    q = json.loads((rs_base / "LR_split_test_questions.json").read_text())["questions"]
    a = json.loads((rs_base / "LR_split_test_answers.json").read_text())["answers"]
    ans_by_qid = {row["id"]: row["answer"].strip().lower() for row in a}
    pol = spec_vqa["selection_policy"]
    keep_types = set(pol["question_types_included"])
    vqa_items: list[dict] = []
    for row in sorted(q, key=lambda r: r["id"]):
        if not row.get("active", True):
            continue
        if row["type"] not in keep_types:
            continue
        gold = ans_by_qid.get(row["id"])
        if gold not in ("yes", "no"):
            continue
        vqa_items.append(
            {
                "qid": row["id"],
                "image_id": row["img_id"],
                "image": str(rs_base / "Images_LR" / f"{row['img_id']}.tif"),
                "question": row["question"],
                "gold": 1 if gold == "yes" else 0,
            }
        )
        if len(vqa_items) >= pol["take"]:
            break

    # --- DIOR-RSVG ---
    import xml.etree.ElementTree as ET

    expr_ids = [line.strip() for line in (di_base / "test.txt").read_text().splitlines() if line.strip()]
    polg = spec_gnd["selection_policy"]
    seen_images: set[str] = set()
    gnd_items: list[dict] = []
    for eid in expr_ids:
        xml = di_base / "Annotations" / f"{eid}.xml"
        if not xml.exists():
            continue
        root = ET.parse(xml).getroot()
        fname = root.findtext("filename")
        obj = root.find("object")
        if fname is None or obj is None:
            continue
        if polg["one_expression_per_image"] and fname in seen_images:
            continue
        desc = obj.findtext("description") or obj.findtext("name")
        bb = obj.find("bndbox")
        if not desc or bb is None:
            continue
        box = [int(float(bb.findtext(k))) for k in ("xmin", "ymin", "xmax", "ymax")]
        gnd_items.append(
            {
                "expr_id": eid,
                "image": str(di_base / "JPEGImages" / fname),
                "expression": desc.strip(),
                "gold_box": box,
            }
        )
        seen_images.add(fname)
        if len(gnd_items) >= polg["take"]:
            break

    # write back resolved ids for provenance
    spec_vqa["resolved_ids"] = [it["qid"] for it in vqa_items]
    spec_gnd["resolved_ids"] = [it["expr_id"] for it in gnd_items]
    (DATASETS / "rsvqa_lr_sample.json").write_text(json.dumps(spec_vqa, indent=2))
    (DATASETS / "dior_rsvg_sample.json").write_text(json.dumps(spec_gnd, indent=2))
    return vqa_items, gnd_items


# --------------------------------------------------------------------------- #
# model
# --------------------------------------------------------------------------- #
def load_model(model_key: str, quant: str):
    """Load a candidate with transformers. Returns (model, processor, meta)."""
    import torch  # noqa: PLC0415
    from transformers import AutoProcessor  # noqa: PLC0415

    spec = MODELS[model_key]
    path = spec["local"]
    if not Path(path, "config.json").exists():
        raise FileNotFoundError(f"{model_key}: weights not at {path} (config.json missing)")

    kwargs: dict[str, Any] = {"torch_dtype": torch.float16, "device_map": "auto"}
    if quant == "4bit":
        from transformers import BitsAndBytesConfig  # noqa: PLC0415

        kwargs["quantization_config"] = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_compute_dtype=torch.float16,
            bnb_4bit_quant_type="nf4",
        )

    if spec["arch"] == "qwen2_5_vl":
        from transformers import Qwen2_5_VLForConditionalGeneration as Cls  # noqa: PLC0415
    else:
        from transformers import Qwen2VLForConditionalGeneration as Cls  # noqa: PLC0415

    t0 = time.time()
    model = Cls.from_pretrained(path, **kwargs)
    model.eval()
    processor = AutoProcessor.from_pretrained(path)
    load_s = time.time() - t0

    n_params = sum(p.numel() for p in model.parameters())
    return model, processor, {"load_time_s": load_s, "parameters": f"{n_params / 1e9:.2f}B"}


def _gen(model, processor, image_path: str, prompt: str, max_new_tokens: int = 64) -> str:
    import torch  # noqa: PLC0415
    from PIL import Image  # noqa: PLC0415

    img = Image.open(image_path).convert("RGB")
    messages = [{"role": "user", "content": [{"type": "image"}, {"type": "text", "text": prompt}]}]
    text = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = processor(text=[text], images=[img], return_tensors="pt").to(model.device)
    with torch.no_grad():
        out = model.generate(**inputs, max_new_tokens=max_new_tokens, do_sample=False)
    trimmed = out[:, inputs["input_ids"].shape[1] :]
    return processor.batch_decode(trimmed, skip_special_tokens=True)[0].strip()


# --------------------------------------------------------------------------- #
# scoring
# --------------------------------------------------------------------------- #
def _norm_yesno(s: str) -> int | None:
    s = s.strip().lower()
    if s.startswith("yes") or s in ("true", "1"):
        return 1
    if s.startswith("no") or s in ("false", "0"):
        return 0
    return None


def _balanced_accuracy(pairs: list[tuple[int, int]]) -> float:
    # pairs: (gold, pred)
    tp = sum(1 for g, p in pairs if g == 1 and p == 1)
    tn = sum(1 for g, p in pairs if g == 0 and p == 0)
    pos = sum(1 for g, _ in pairs if g == 1)
    neg = sum(1 for g, _ in pairs if g == 0)
    if pos == 0 or neg == 0:
        return float("nan")
    return 0.5 * (tp / pos + tn / neg)


def _parse_box(text: str) -> list[float] | None:
    import re  # noqa: PLC0415

    # Qwen2-VL style: (x1,y1),(x2,y2)   or JSON [x1,y1,x2,y2]
    nums = re.findall(r"-?\d+\.?\d*", text)
    if len(nums) >= 4:
        return [float(x) for x in nums[:4]]
    return None


def _iou(a: list[float], b: list[float]) -> float:
    ix1, iy1 = max(a[0], b[0]), max(a[1], b[1])
    ix2, iy2 = min(a[2], b[2]), min(a[3], b[3])
    iw, ih = max(0.0, ix2 - ix1), max(0.0, iy2 - iy1)
    inter = iw * ih
    ua = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / ua if ua > 0 else 0.0


# --------------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------------- #
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", choices=list(MODELS), required=False)
    ap.add_argument("--quant", choices=["none", "4bit"], default="4bit")
    ap.add_argument("--resolve", action="store_true", help="only materialise sample IDs")
    args = ap.parse_args()

    REPORTS.mkdir(parents=True, exist_ok=True)
    ts = time.strftime("%Y%m%dT%H%M%S")

    try:
        vqa_items, gnd_items = resolve_samples()
        print(f"resolved: {len(vqa_items)} VQA questions, {len(gnd_items)} grounding expressions")
    except FileNotFoundError as e:
        print(f"DATASET_MISSING: {e}")
        if args.resolve or args.model:
            rep = Report(model_key=args.model or "", status="DATASET_MISSING",
                         notes=[str(e)], timestamp=ts)
            p = REPORTS / f"exp002_{args.model or 'resolve'}_{ts}.json"
            p.write_text(json.dumps(asdict(rep), indent=2))
            print(f"wrote {p}")
        return 2

    if args.resolve:
        return 0
    if not args.model:
        ap.error("--model is required unless --resolve")

    spec = MODELS[args.model]
    rep = Report(model_key=args.model, role=spec["role"], checkpoint=spec["local"],
                 quantization=args.quant, timestamp=ts)
    rep.environment = {
        "python": platform.python_version(),
        "platform": platform.platform(),
    }
    try:
        import torch  # noqa: PLC0415
        import transformers  # noqa: PLC0415

        rep.environment["torch"] = torch.__version__
        rep.environment["transformers"] = transformers.__version__
        rep.environment["cuda_available"] = str(torch.cuda.is_available())
    except ImportError as e:
        rep.status = "ENV_MISSING"
        rep.notes.append(f"import failed: {e}")
        (REPORTS / f"exp002_{args.model}_{ts}.json").write_text(json.dumps(asdict(rep), indent=2))
        print(f"ENV_MISSING: {e}")
        return 3

    try:
        model, processor, meta = load_model(args.model, args.quant)
    except FileNotFoundError as e:
        rep.status = "ARTIFACT_MISSING"
        rep.notes.append(str(e))
        (REPORTS / f"exp002_{args.model}_{ts}.json").write_text(json.dumps(asdict(rep), indent=2))
        print(f"ARTIFACT_MISSING: {e}")
        return 1

    rep.load_time_s = round(meta["load_time_s"], 2)
    rep.parameters = meta["parameters"]

    import psutil  # noqa: PLC0415
    import torch  # noqa: PLC0415

    rep.cpu_memory_mb = round(psutil.Process().memory_info().rss / 1e6, 1)
    if torch.cuda.is_available():
        torch.cuda.reset_peak_memory_stats()

    # warm-up
    if vqa_items:
        t0 = time.time()
        _ = _gen(model, processor, vqa_items[0]["image"], vqa_items[0]["question"])
        rep.warm_latency_s = round(time.time() - t0, 2)

    # --- VQA ---
    vqa = TaskResult(n=len(vqa_items), metric="balanced_accuracy",
                     threshold=VQA_THRESHOLD, failure_categories={})
    preds_v: list[dict] = []
    pairs: list[tuple[int, int]] = []
    for it in vqa_items:
        t0 = time.time()
        try:
            raw = _gen(model, processor, it["image"],
                       it["question"] + " Answer yes or no.", max_new_tokens=8)
        except Exception as ex:  # noqa: BLE001 - harness must not die on one query
            raw, ex_name = "", type(ex).__name__
            vqa.failure_categories[ex_name] = vqa.failure_categories.get(ex_name, 0) + 1
        dt = time.time() - t0
        vqa.per_query_latency_s.append(round(dt, 2))
        pred = _norm_yesno(raw)
        if pred is None:
            vqa.failure_categories["unparseable_answer"] = (
                vqa.failure_categories.get("unparseable_answer", 0) + 1
            )
        else:
            pairs.append((it["gold"], pred))
        preds_v.append({"qid": it["qid"], "gold": it["gold"], "raw": raw, "pred": pred, "latency_s": round(dt, 2)})
    vqa.n_scored = len(pairs)
    vqa.score = None if not pairs else round(_balanced_accuracy(pairs), 4)
    vqa.failure_rate = round(1 - len(pairs) / max(1, len(vqa_items)), 4)
    vqa.passed = (vqa.score is not None) and (vqa.score >= VQA_THRESHOLD)
    pv = REPORTS / f"exp002_{args.model}_{ts}_vqa_preds.json"
    pv.write_text(json.dumps(preds_v, indent=2))
    vqa.predictions_path = str(pv)

    # --- grounding ---
    gnd = TaskResult(n=len(gnd_items), metric="acc@IoU0.5",
                     threshold=GND_THRESHOLD, failure_categories={})
    preds_g: list[dict] = []
    hits = 0
    for it in gnd_items:
        t0 = time.time()
        try:
            raw = _gen(model, processor, it["image"],
                       f"Output the bounding box of: {it['expression']}", max_new_tokens=64)
        except Exception as ex:  # noqa: BLE001
            raw, ex_name = "", type(ex).__name__
            gnd.failure_categories[ex_name] = gnd.failure_categories.get(ex_name, 0) + 1
        dt = time.time() - t0
        gnd.per_query_latency_s.append(round(dt, 2))
        box = _parse_box(raw)
        iou = 0.0
        if box is None:
            gnd.failure_categories["no_box_parsed"] = gnd.failure_categories.get("no_box_parsed", 0) + 1
        else:
            iou = _iou(box, [float(x) for x in it["gold_box"]])
            if iou >= 0.5:
                hits += 1
        preds_g.append({"expr_id": it["expr_id"], "gold_box": it["gold_box"], "raw": raw,
                        "pred_box": box, "iou": round(iou, 3), "latency_s": round(dt, 2)})
    gnd.n_scored = len(gnd_items)
    gnd.score = None if not gnd_items else round(hits / len(gnd_items), 4)
    gnd.failure_rate = round(
        sum(gnd.failure_categories.values()) / max(1, len(gnd_items)), 4
    )
    gnd.passed = (gnd.score is not None) and (gnd.score >= GND_THRESHOLD)
    pg = REPORTS / f"exp002_{args.model}_{ts}_gnd_preds.json"
    pg.write_text(json.dumps(preds_g, indent=2))
    gnd.predictions_path = str(pg)

    if torch.cuda.is_available():
        rep.gpu_memory_mb = round(torch.cuda.max_memory_allocated() / 1e6, 1)

    def _p(xs: list[float], q: float) -> float | None:
        if not xs:
            return None
        s = sorted(xs)
        return round(s[min(len(s) - 1, int(q * len(s)))], 2)

    rep.vqa = {**asdict(vqa), "p50_latency_s": _p(vqa.per_query_latency_s, 0.5),
               "p95_latency_s": _p(vqa.per_query_latency_s, 0.95)}
    rep.grounding = {**asdict(gnd), "p50_latency_s": _p(gnd.per_query_latency_s, 0.5),
                     "p95_latency_s": _p(gnd.per_query_latency_s, 0.95)}
    rep.status = "OK"

    out = REPORTS / f"exp002_{args.model}_{ts}.json"
    out.write_text(json.dumps(asdict(rep), indent=2))
    print(f"\n=== {args.model} ({spec['role']}) — {args.quant} ===")
    print(f"params={rep.parameters} load={rep.load_time_s}s warm={rep.warm_latency_s}s "
          f"gpu={rep.gpu_memory_mb}MB cpu={rep.cpu_memory_mb}MB")
    print(f"VQA  balanced_acc={vqa.score}  (>= {VQA_THRESHOLD}? {vqa.passed})  "
          f"fail_rate={vqa.failure_rate}  p50={rep.vqa['p50_latency_s']}s")
    print(f"GND  acc@IoU0.5={gnd.score}  (>= {GND_THRESHOLD}? {gnd.passed})  "
          f"fail_rate={gnd.failure_rate}  p50={rep.grounding['p50_latency_s']}s")
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
