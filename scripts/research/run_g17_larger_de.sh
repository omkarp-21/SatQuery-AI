#!/usr/bin/env bash
# G17 Part 19/20 — larger D/E validation on the FULL DFC2020 validation split
# (986 patches, 600 train / 386 eval) + persist the EXP-008 LoRA adapter.
#
# The G12 frozen split (400/200) and its results are NOT touched. This writes to
# `evaluation/reports/exp004_run2_g17larger_*` and
# `models/checkpoints/exp008_croma_lora.pt`.
#
# Long CPU job (~2-4 h). Run AFTER the G17 intent cache to avoid contention.
set -euo pipefail
cd "$(dirname "$0")/../.."

P=models/cache/dfc2020_g17_larger
OUT=evaluation/reports
CKPT_C=models/cache/croma/CROMA_base.pt
CKPT_D=models/cache/dofa/DOFA_ViT_base_e100.pth
mkdir -p "$OUT" models/checkpoints

echo "== [1/4] CROMA features (larger split) =="
.venvs/croma/Scripts/python.exe evaluation/scripts/exp004_run2_features.py \
  --encoder croma --patches-npz "$P/dfc2020_patches_train.npz" --checkpoint "$CKPT_C" \
  --out-npz "$OUT/g17larger_croma_train.npz"
.venvs/croma/Scripts/python.exe evaluation/scripts/exp004_run2_features.py \
  --encoder croma --patches-npz "$P/dfc2020_patches_eval.npz" --checkpoint "$CKPT_C" \
  --out-npz "$OUT/g17larger_croma_eval.npz"

echo "== [2/4] DOFA features (larger split) =="
.venvs/dofa/Scripts/python.exe evaluation/scripts/exp004_run2_features.py \
  --encoder dofa --patches-npz "$P/dfc2020_patches_train.npz" --checkpoint "$CKPT_D" \
  --out-npz "$OUT/g17larger_dofa_train.npz"
.venvs/dofa/Scripts/python.exe evaluation/scripts/exp004_run2_features.py \
  --encoder dofa --patches-npz "$P/dfc2020_patches_eval.npz" --checkpoint "$CKPT_D" \
  --out-npz "$OUT/g17larger_dofa_eval.npz"

echo "== [3/4] probe: CROMA optical-only vs joint vs DOFA fused (bootstrap CIs) =="
.venvs/croma/Scripts/python.exe evaluation/scripts/exp004_run2_probe.py \
  --croma-train "$OUT/g17larger_croma_train.npz" --croma-eval "$OUT/g17larger_croma_eval.npz" \
  --dofa-train "$OUT/g17larger_dofa_train.npz" --dofa-eval "$OUT/g17larger_dofa_eval.npz" \
  --n-boot 2000

echo "== [4/4] EXP-008: frozen CROMA vs LoRA CROMA (+ persist the adapter) =="
.venvs/croma/Scripts/python.exe evaluation/scripts/exp008_adapt.py \
  --encoder croma --checkpoint "$CKPT_C" --patches-dir "$P" \
  --save-adapter models/checkpoints/exp008_croma_lora.pt --adopt-threshold 0.03

echo "== DONE — see evaluation/reports/exp004_run2_*.{json,md} and models/checkpoints/exp008_croma_lora.pt =="
