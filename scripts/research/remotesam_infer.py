"""RemoteSAM inference bridge — runs INSIDE .venvs/remotesam.

RemoteSAM (github.com/1e12Leon/RemoteSAM, ACM MM 2025) is a referring-segmentation
/ visual-grounding specialist (Swin-B + BERT). This bridge loads its released
checkpoint and runs `visual_grounding` (text -> box) + `referring_seg`
(text -> mask) for a batch of jobs, writing a single JSON.

It is allowed to import the vendored RemoteSAM source (its own `lib/`, `tasks/`,
`args.py`) because it runs in the isolated env. SatQuery product code never
imports this. Called by `packages/model_adapters/remotesam.py` via subprocess
(same pattern as `changeformer_infer.py` etc.).

Usage:
    python remotesam_infer.py --checkpoint <RemoteSAMv1.pth> --repo <clone dir> \
        --jobs-json <in.json> --out-json <out.json> [--device cpu]

jobs-json: [{"image": "<path>", "query": "<phrase>", "mask_out": "<png path>"}]
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
import time
import types


def _load_remotesam(repo: str):
    """Import tasks/code/model.py as `tasks.code.model` with RuleBasedCaptioning stubbed."""
    repo = os.path.abspath(repo)
    if repo not in sys.path:
        sys.path.insert(0, repo)  # for `import utils`, `import transforms`, `from args import ...`, `from lib import ...`

    # namespace packages so the relative import in model.py resolves
    for pkg in ("tasks", "tasks.code"):
        m = types.ModuleType(pkg)
        m.__path__ = [os.path.join(repo, *pkg.split("."))]
        sys.modules[pkg] = m

    # captioning is not needed for grounding and pulls in pycocotools at import time
    stub = types.ModuleType("tasks.code.RuleBasedCaptioning")
    stub.single_captioning = lambda *a, **k: ""  # type: ignore[attr-defined]
    sys.modules["tasks.code.RuleBasedCaptioning"] = stub

    path = os.path.join(repo, "tasks", "code", "model.py")
    spec = importlib.util.spec_from_file_location("tasks.code.model", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["tasks.code.model"] = mod
    spec.loader.exec_module(mod)
    return mod


def _rss_mb() -> float:
    try:
        import psutil  # noqa: PLC0415

        return round(psutil.Process().memory_info().rss / 1e6, 1)
    except Exception:  # noqa: BLE001
        return -1.0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--checkpoint", required=True)
    ap.add_argument("--repo", required=True)
    ap.add_argument("--jobs-json", required=True)
    ap.add_argument("--out-json", required=True)
    ap.add_argument("--device", default="cpu")
    ap.add_argument("--hf-home", default=None, help="HF_HOME cache dir (offline BERT)")
    ap.add_argument("--bert-dir", default=None,
                    help="local bert-base-uncased dir; passed as --ck_bert to RemoteSAM")
    a = ap.parse_args()

    if a.hf_home:
        os.environ["HF_HOME"] = os.path.abspath(a.hf_home)
        os.environ.setdefault("HF_HUB_OFFLINE", "1")
        os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

    import numpy as np  # noqa: PLC0415
    import torch  # noqa: PLC0415
    from PIL import Image  # noqa: PLC0415

    env = {
        "python": sys.version.split()[0],
        "torch": torch.__version__,
        "numpy": np.__version__,
        "device": a.device,
    }
    out: dict = {"model": "remotesam", "env": env, "checkpoint": a.checkpoint, "results": []}

    t_load = time.time()
    try:
        rs = _load_remotesam(a.repo)
        _argv = sys.argv
        # init_demo_model calls args.get_parser().parse_args() on sys.argv;
        # --ck_bert points RemoteSAM's BertModel at a local dir (offline).
        new_argv = [sys.argv[0]]
        if a.bert_dir:
            new_argv += ["--ck_bert", os.path.abspath(a.bert_dir)]
        sys.argv = new_argv
        try:
            core = rs.init_demo_model(a.checkpoint, a.device)
        finally:
            sys.argv = _argv
        model = rs.RemoteSAM(core, torch.device(a.device), use_EPOC=False)
    except Exception as exc:  # noqa: BLE001
        out["ok"] = False
        out["status"] = "LOAD_FAILED"
        out["error"] = f"{type(exc).__name__}: {exc}"
        _write(a.out_json, out)
        return 1
    out["load_time_s"] = round(time.time() - t_load, 2)
    out["cpu_rss_mb_after_load"] = _rss_mb()
    if a.device == "cuda" and torch.cuda.is_available():
        torch.cuda.reset_peak_memory_stats()

    jobs = json.loads(open(a.jobs_json, encoding="utf-8").read())
    for i, job in enumerate(jobs):
        row: dict = {"image": job["image"], "query": job["query"]}
        try:
            img = Image.open(job["image"]).convert("RGB")
            row["image_dims"] = [img.width, img.height]  # (W, H)
            arr = np.asarray(img)
            t0 = time.time()
            box = model.visual_grounding(image=arr, sentence=job["query"])  # [xmin,ymin,xmax,ymax] or None
            dt_box = time.time() - t0
            mask, prob = model.referring_seg(image=arr, sentence=job["query"], return_prob=True)
            dt_total = time.time() - t0
            row["bbox_xyxy"] = [float(x) for x in box] if box is not None else None
            row["mask_shape"] = list(np.asarray(mask).shape)
            row["mask_fg_fraction"] = float((np.asarray(mask) > 0).mean())
            row["prob_max"] = float(np.asarray(prob).max())
            mp = job.get("mask_out")
            if mp:
                Image.fromarray((np.asarray(mask) > 0).astype("uint8") * 255).save(mp)
                row["mask_path"] = mp
            row["latency_s"] = round(dt_total, 2)
            row["latency_box_only_s"] = round(dt_box, 2)
            row["status"] = "ok" if box is not None else "no_box"
        except Exception as exc:  # noqa: BLE001
            row["status"] = "error"
            row["error"] = f"{type(exc).__name__}: {exc}"
        out["results"].append(row)
        if i == 0:
            out["warm_latency_s"] = row.get("latency_s")

    if a.device == "cuda" and torch.cuda.is_available():
        out["gpu_peak_mb"] = round(torch.cuda.max_memory_allocated() / 1e6, 1)
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
