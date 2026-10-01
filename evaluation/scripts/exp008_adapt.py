"""EXP-008 — RS adaptation of the EXP-004-winning optical+SAR encoder.

Three arms on the SAME frozen DFC2020 split (`evaluation/datasets/dfc2020_exp004_split.json`),
all with an identical torch linear-classifier head (AdamW, same epochs) so the
only thing that varies is the representation:

  1. optical-only   : FROZEN encoder, optical feature       (baseline)
  2. frozen fused    : FROZEN encoder, joint/fused feature   (= EXP-004 winning arm)
  3. adapted         : LoRA-adapted encoder, joint feature   (parameter-efficient)

Pre-registered decision rule (fixed before the run):
  Adopt the adapted encoder ONLY if it beats **frozen fused** by >= +0.03 macro-F1
  on the held-out split AND adds no deployment blocker (trainable params small,
  checkpoint delta small, still CPU-runnable). Otherwise KEEP THE FROZEN ENCODER
  and record that PEFT gave no meaningful gain. No full fine-tune.

Runs in the winner's venv (`.venvs/croma` or `.venvs/dofa`). No network.
out: evaluation/reports/exp008_<ts>.json + markdown sibling.
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
import torch.nn as nn

REPO_ROOT = Path(__file__).resolve().parents[2]
S2_WAVES = [0.443, 0.490, 0.560, 0.665, 0.705, 0.740, 0.783, 0.842, 0.865, 0.945, 1.610, 2.190]
S1_WAVES = [5.405, 5.405]
DFC_CLASSES = {
    1: "Forest", 2: "Shrubland", 3: "Savanna", 4: "Grassland", 5: "Wetlands",
    6: "Croplands", 7: "Urban/Built-up", 8: "Snow/Ice", 9: "Barren", 10: "Water",
}
SEED = 20260902


def macro_f1(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    classes = sorted(set(y_true.tolist()))
    fs = []
    for c in classes:
        tp = int(np.sum((y_pred == c) & (y_true == c)))
        fp = int(np.sum((y_pred == c) & (y_true != c)))
        fn = int(np.sum((y_pred != c) & (y_true == c)))
        p = tp / (tp + fp) if tp + fp else 0.0
        r = tp / (tp + fn) if tp + fn else 0.0
        fs.append(2 * p * r / (p + r) if p + r else 0.0)
    return float(np.mean(fs))


class LoRALinear(nn.Module):
    """Wrap a frozen nn.Linear with a trainable low-rank residual B@A."""

    def __init__(self, base: nn.Linear, r: int = 8, alpha: int = 16):
        super().__init__()
        self.base = base
        for p in self.base.parameters():
            p.requires_grad_(False)
        self.a = nn.Parameter(torch.zeros(r, base.in_features))
        self.b = nn.Parameter(torch.zeros(base.out_features, r))
        nn.init.kaiming_uniform_(self.a, a=5**0.5)
        self.scaling = alpha / r

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.base(x) + (x @ self.a.T @ self.b.T) * self.scaling


def inject_lora(model: nn.Module, name_contains: tuple[str, ...], r: int, alpha: int) -> int:
    n = 0
    for mod_name, mod in list(model.named_modules()):
        for child_name, child in list(mod.named_children()):
            full = f"{mod_name}.{child_name}"
            if isinstance(child, nn.Linear) and any(t in full for t in name_contains):
                setattr(mod, child_name, LoRALinear(child, r, alpha))
                n += 1
    return n


def _norm_per_sample(x: torch.Tensor) -> torch.Tensor:
    x = x.float()
    m = x.mean(dim=(2, 3), keepdim=True)
    s = x.std(dim=(2, 3), keepdim=True)
    lo, hi = m - 2 * s, m + 2 * s
    return torch.clip((x - lo) / (hi - lo + 1e-8), 0, 1)


def _resize(x: torch.Tensor, size: int) -> torch.Tensor:
    if x.shape[-1] == size and x.shape[-2] == size:
        return x
    return torch.nn.functional.interpolate(x, size=size, mode="bilinear", align_corners=False)


# ---- encoder adapters: return a callable (s1_batch, s2_batch) -> dict of features ----

def build_croma(ckpt: str):
    sys.path.insert(0, str(REPO_ROOT / "external" / "research" / "CROMA"))
    from use_croma import PretrainedCROMA

    res = 120
    model = PretrainedCROMA(pretrained_path=ckpt, size="base", modality="both", image_resolution=res)

    def feat(s1, s2, which):
        b1 = _norm_per_sample(_resize(s1, res))
        b2 = _norm_per_sample(_resize(s2, res))
        out = model(SAR_images=b1, optical_images=b2)
        return out["optical_GAP"] if which == "optical" else out["joint_GAP"]

    return model, feat, ("to_qkv", "to_q", "to_k", "to_v"), 768, 768


def build_dofa(ckpt: str):
    sys.path.insert(0, str(REPO_ROOT / "external" / "research" / "DOFA"))
    from dofa_v1 import vit_base_patch16

    res = 224
    model = vit_base_patch16()
    model.load_state_dict(torch.load(ckpt, map_location="cpu"), strict=False)

    def feat(s1, s2, which):
        f2 = model.forward_features(_norm_per_sample(_resize(s2, res)), wave_list=S2_WAVES)
        if which == "optical":
            return f2
        f1 = model.forward_features(_norm_per_sample(_resize(s1, res)), wave_list=S1_WAVES)
        return torch.cat([f2, f1], dim=1)

    return model, feat, ("attn.qkv", "attn.proj"), 768, 1536


class Head(nn.Module):
    def __init__(self, dim: int, n_cls: int):
        super().__init__()
        self.fc = nn.Linear(dim, n_cls)

    def forward(self, x):
        return self.fc(x)


def _extract_all(feat_fn, which, s1, s2, bs):
    out = []
    with torch.no_grad():
        for i in range(0, len(s1), bs):
            f = feat_fn(torch.tensor(s1[i : i + bs]).float(), torch.tensor(s2[i : i + bs]).float(), which)
            out.append(f.detach())
    return torch.cat(out)


def train_head(feat_fn, model, which, dim, s1tr, s2tr, ytr, s1ev, s2ev, yev, classes,
               *, lora=False, epochs=8, bs=16, lr=1e-3, lora_params=None):
    torch.manual_seed(SEED)
    np.random.seed(SEED)
    cls_index = {c: i for i, c in enumerate(classes)}
    ytr_i = torch.tensor([cls_index[int(v)] for v in ytr])
    yev_i = np.array([cls_index[int(v)] for v in yev])
    head = Head(dim, len(classes))
    params = list(head.parameters()) + (list(lora_params) if lora else [])
    opt = torch.optim.AdamW(params, lr=lr, weight_decay=1e-4)
    lossf = nn.CrossEntropyLoss()
    n = len(ytr)
    model.eval()  # frozen BN/dropout; LoRA params still train
    t0 = time.time()

    # Frozen arms: the encoder never changes -> extract features ONCE, then the
    # head trains on cached tensors (fast). LoRA arm: encoder changes every step
    # -> live forward+backward through the (LoRA-wrapped) encoder each batch.
    ftr_cached = None if lora else _extract_all(feat_fn, which, s1tr, s2tr, bs)

    for ep in range(epochs):
        perm = np.random.permutation(n)
        tot = 0.0
        for i in range(0, n, bs):
            idx = perm[i : i + bs]
            if lora:
                s1b = torch.tensor(s1tr[idx]).float()
                s2b = torch.tensor(s2tr[idx]).float()
                with torch.enable_grad():
                    f = feat_fn(s1b, s2b, which)
            else:
                f = ftr_cached[idx]
            logits = head(f)
            loss = lossf(logits, ytr_i[idx])
            opt.zero_grad()
            loss.backward()
            opt.step()
            tot += float(loss) * len(idx)
        print(f"  [{which}{'+lora' if lora else ''}] epoch {ep+1}/{epochs} loss {tot/n:.4f} ({time.time()-t0:.0f}s)", flush=True)
    train_s = time.time() - t0

    # eval — always a live forward (measures real inference cost)
    head.eval()
    preds = []
    ti = time.time()
    with torch.no_grad():
        for i in range(0, len(yev), bs):
            s1b = torch.tensor(s1ev[i : i + bs]).float()
            s2b = torch.tensor(s2ev[i : i + bs]).float()
            f = feat_fn(s1b, s2b, which)
            preds.append(head(f).argmax(1).cpu().numpy())
    pred_i = np.concatenate(preds)
    infer_s = (time.time() - ti) / max(len(yev), 1)
    inv = {i: c for c, i in cls_index.items()}
    y_pred = np.array([inv[int(p)] for p in pred_i])
    return {
        "macro_f1": round(macro_f1(yev, y_pred), 4),
        "accuracy": round(float(np.mean(pred_i == yev_i)), 4),
        "train_runtime_s": round(train_s, 1),
        "infer_s_per_patch": round(infer_s, 4),
    }, y_pred


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--encoder", choices=["croma", "dofa"], required=True)
    ap.add_argument("--checkpoint", required=True)
    ap.add_argument("--patches-dir", required=True)
    ap.add_argument("--epochs", type=int, default=8)
    ap.add_argument("--lora-r", type=int, default=8)
    ap.add_argument("--lora-alpha", type=int, default=16)
    ap.add_argument("--adopt-threshold", type=float, default=0.03)
    ap.add_argument("--save-adapter", default=None, help="path to torch.save the trained LoRA delta")
    ap.add_argument("--tag", default="", help="output filename tag, e.g. g18_larger")
    ap.add_argument("--split-file", default="evaluation/datasets/dfc2020_exp004_split.json")
    a = ap.parse_args()

    pd = Path(a.patches_dir)
    tr = np.load(pd / "dfc2020_patches_train.npz")
    ev = np.load(pd / "dfc2020_patches_eval.npz")
    s1tr, s2tr, ytr = tr["s1"], tr["s2"], tr["y"]
    s1ev, s2ev, yev = ev["s1"], ev["s2"], ev["y"]
    classes = sorted(set(ytr.tolist()) | set(yev.tolist()))

    builder = {"croma": build_croma, "dofa": build_dofa}[a.encoder]
    model, feat_fn, lora_targets, opt_dim, joint_dim = builder(a.checkpoint)
    for p in model.parameters():
        p.requires_grad_(False)

    proc = None
    try:
        import psutil

        proc = psutil.Process(os.getpid())
    except Exception:
        pass

    # arm 1: optical-only frozen
    r_opt, _ = train_head(feat_fn, model, "optical", opt_dim, s1tr, s2tr, ytr, s1ev, s2ev, yev,
                          classes, lora=False, epochs=a.epochs)
    # arm 2: frozen fused/joint
    r_frozen, p_frozen = train_head(feat_fn, model, "joint", joint_dim, s1tr, s2tr, ytr, s1ev, s2ev, yev,
                                    classes, lora=False, epochs=a.epochs)
    # arm 3: LoRA-adapted, joint
    n_inj = inject_lora(model, lora_targets, a.lora_r, a.lora_alpha)
    lora_params = [p for n, p in model.named_parameters() if p.requires_grad]
    n_trainable = int(sum(p.numel() for p in lora_params))
    r_adapt, p_adapt = train_head(feat_fn, model, "joint", joint_dim, s1tr, s2tr, ytr, s1ev, s2ev, yev,
                                  classes, lora=True, epochs=a.epochs, lora_params=lora_params)

    # persist the LoRA delta (only the trainable A/B tensors) so the adapted
    # encoder can be reloaded for an opt-in production path / a larger-split re-run.
    adapter_path = None
    if a.save_adapter:
        lora_sd = {n: p.detach().cpu() for n, p in model.named_parameters() if p.requires_grad}
        adapter_path = str(Path(a.save_adapter))
        Path(adapter_path).parent.mkdir(parents=True, exist_ok=True)
        torch.save(
            {"lora_r": a.lora_r, "lora_alpha": a.lora_alpha, "targets": list(lora_targets),
             "state_dict": lora_sd},
            adapter_path,
        )
        print(f"saved LoRA adapter -> {adapter_path} ({sum(v.numel() for v in lora_sd.values()):,} params)")

    rss = round(proc.memory_info().rss / 1e6, 1) if proc else None
    ckpt_bytes = int(sum(p.numel() * 4 for p in lora_params))  # fp32 LoRA delta only

    delta_vs_frozen = round(r_adapt["macro_f1"] - r_frozen["macro_f1"], 4)
    delta_vs_optical = round(r_adapt["macro_f1"] - r_opt["macro_f1"], 4)
    frozen_vs_optical = round(r_frozen["macro_f1"] - r_opt["macro_f1"], 4)
    adopt = delta_vs_frozen >= a.adopt_threshold

    payload = {
        "experiment": "EXP-008 — parameter-efficient adaptation of the optical+SAR encoder",
        "date": time.strftime("%Y-%m-%dT%H%M%S"),
        "encoder": a.encoder,
        "dataset": "DFC2020 ROIs0000_validation (non-gated 125oii/dfc2020)",
        "split_file": a.split_file,
        "n_train": int(ytr.size),
        "n_eval": int(yev.size),
        "task": "dominant DFC land-cover class (8 classes)",
        "head": "single torch nn.Linear, AdamW, identical epochs across arms",
        "epochs": a.epochs,
        "lora": {"r": a.lora_r, "alpha": a.lora_alpha, "linear_layers_wrapped": n_inj,
                 "trainable_params": n_trainable, "delta_checkpoint_bytes_fp32": ckpt_bytes,
                 "adapter_path": adapter_path},
        "cuda": torch.cuda.is_available(),
        "cpu_rss_mb_peak": rss,
        "arms": {
            "1_optical_only_frozen": r_opt,
            "2_fused_frozen": r_frozen,
            "3_fused_lora_adapted": r_adapt,
        },
        "deltas_macro_f1": {
            "frozen_fused_minus_optical": frozen_vs_optical,
            "adapted_minus_frozen_fused": delta_vs_frozen,
            "adapted_minus_optical": delta_vs_optical,
        },
        "decision": {
            "rule": f"adopt adapted iff (adapted - frozen_fused) >= {a.adopt_threshold} macro-F1 "
            "AND no deployment blocker",
            "adapted_minus_frozen_fused": delta_vs_frozen,
            "trainable_params": n_trainable,
            "deployment_blocker": False,
            "adopt_adaptation": bool(adopt),
            "outcome": (
                "ADOPT LoRA-adapted encoder" if adopt
                else "KEEP FROZEN encoder — PEFT gave no meaningful gain on this split"
            ),
        },
        "note": f"sanity-scale ({ytr.size}/{yev.size} of 986 validation patches). CPU. "
        f"Seed {SEED}. Real integrated measurement, not a full benchmark. No confidence value.",
    }
    ts = time.strftime("%Y%m%dT%H%M%S")
    stem = f"exp008_{a.tag}_{ts}" if a.tag else f"exp008_{ts}"
    out = REPO_ROOT / "evaluation" / "reports" / f"{stem}.json"
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    _md(payload, out.with_suffix(".md"))
    print(json.dumps(payload["arms"], indent=2))
    print(json.dumps(payload["decision"], indent=2))
    print("wrote", out)
    return 0


def _md(p: dict, path: Path) -> None:
    ar = p["arms"]
    de = p["deltas_macro_f1"]
    dc = p["decision"]
    lines = [
        f"# EXP-008 — RS adaptation ({p['encoder']}) — {p['date']}",
        "",
        f"**Dataset:** {p['dataset']} — {p['n_train']} train / {p['n_eval']} eval "
        f"(`{p['split_file']}`).  ",
        f"**Task:** {p['task']}.  **Head:** {p['head']} ({p['epochs']} epochs).  ",
        f"**LoRA:** r={p['lora']['r']}, alpha={p['lora']['alpha']}, "
        f"{p['lora']['linear_layers_wrapped']} Linear layers wrapped, "
        f"**{p['lora']['trainable_params']:,} trainable params** "
        f"({p['lora']['delta_checkpoint_bytes_fp32'] / 1e6:.2f} MB fp32 delta).  ",
        f"CUDA: {p['cuda']}.  CPU RSS peak: {p['cpu_rss_mb_peak']} MB.  **Sanity-scale.**",
        "",
        "| arm | representation | macro-F1 | accuracy | train s | infer s/patch |",
        "|-----|----------------|:--------:|:--------:|:-------:|:-------------:|",
        f"| 1 | optical-only (frozen) | {ar['1_optical_only_frozen']['macro_f1']} "
        f"| {ar['1_optical_only_frozen']['accuracy']} | {ar['1_optical_only_frozen']['train_runtime_s']} "
        f"| {ar['1_optical_only_frozen']['infer_s_per_patch']} |",
        f"| 2 | fused optical+SAR (frozen) | **{ar['2_fused_frozen']['macro_f1']}** "
        f"| {ar['2_fused_frozen']['accuracy']} | {ar['2_fused_frozen']['train_runtime_s']} "
        f"| {ar['2_fused_frozen']['infer_s_per_patch']} |",
        f"| 3 | fused optical+SAR (LoRA-adapted) | **{ar['3_fused_lora_adapted']['macro_f1']}** "
        f"| {ar['3_fused_lora_adapted']['accuracy']} | {ar['3_fused_lora_adapted']['train_runtime_s']} "
        f"| {ar['3_fused_lora_adapted']['infer_s_per_patch']} |",
        "",
        f"- frozen fused − optical-only: **{de['frozen_fused_minus_optical']:+.4f}**",
        f"- adapted − frozen fused: **{de['adapted_minus_frozen_fused']:+.4f}**  "
        f"(adopt threshold +{p['decision']['rule'].split('>= ')[1].split(' ')[0]})",
        f"- adapted − optical-only: **{de['adapted_minus_optical']:+.4f}**",
        "",
        f"## Decision: {dc['outcome']}",
        "",
        f"> {p['note']}",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
