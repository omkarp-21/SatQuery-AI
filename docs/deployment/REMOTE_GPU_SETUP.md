# Remote GPU Research Lab — setup runbook

> **Status: TEMPLATE — NOT YET PROVISIONED (2026-09-01).** Every value marked
> `<PENDING>` is filled in *on the box*, by running the `record` block at the
> bottom and pasting its output here. Nothing in G6 Phases 2/3/4/5/6 can be
> **MEASURED** until this is done — they are BLOCKED only on this provisioning
> step, not on capability or code (harnesses are committed and dry-run-clean).

## Purpose & boundaries

- **One** Linux GPU box, used for: multi-GB artifact acquisition (model weights,
  S1/S2 datasets that fail from the Windows dev host — 6 documented download
  failures, `docs/research/EXP-002.md`), heavy inference (7B references), and the
  research experiments EXP-002 / EXP-004 Run 2 / EXP-008.
- **Git stays the source of truth.** The box gets a *clone*, runs experiments,
  and pushes **results** (report JSON, doc updates) back. Product code is not
  developed there. No long-lived state beyond `models/cache/` and
  `evaluation/datasets/` (both gitignored).
- Tear the box down when the measurement backlog is cleared. Keep the report
  JSONs (commit the doc updates that cite them).

## Sizing

| | Minimum | Preferred |
|--|--------|-----------|
| GPU | 1× NVIDIA, **≥ 16 GB VRAM** (T4-16, A10, L4, RTX 4090, A100-40) | 24 GB (A10G / L4 / 4090 / A100) |
| VRAM headroom | EarthDial-4B bf16 ≈ 9 GB; GeoChat-7B fp16 ≈ 15 GB / 4-bit ≈ 6 GB; RSCoVLM-3B fp16 ≈ 6 GB | run 7B fp16 without offload |
| Disk (free SSD) | **50 GB** (weights ≈ 25 GB + datasets ≈ 15 GB + env ≈ 8 GB) | 100 GB |
| Network | any that sustains > 5 MB/s to HF + Zenodo | 100 Mbit+ |
| CUDA | 11.8 or 12.1 (matches Torch wheels) | 12.1 |
| OS | Ubuntu 22.04 LTS | 22.04 LTS |

Cloud spot/preemptible is fine — the experiments checkpoint their own JSON per
model, so a preemption loses at most one candidate's run.

## One-time setup (paste exactly)

```bash
# 0. system
sudo apt-get update && sudo apt-get install -y git git-lfs build-essential python3.11 python3.11-venv
nvidia-smi                                   # confirm the GPU + driver

# 1. code (git remains source of truth)
git clone <SATQUERY_REMOTE_URL> ~/satquery && cd ~/satquery
git checkout <BRANCH>                        # e.g. docs/lightweight-model-audit or main

# 2. base env (mirrors .venvs/satquery on the dev host)
python3.11 -m venv .venvs/satquery
. .venvs/satquery/bin/activate
pip install -U pip
pip install -e packages/core -e packages/geospatial -e packages/agents \
            -e packages/evidence -e packages/model_adapters --no-deps
pip install fastapi "uvicorn[standard]" pydantic rasterio pyproj shapely scipy \
            numpy pillow structlog httpx pytest

# 3. VLM env (Qwen2-VL / Qwen2.5-VL + 4-bit)
python3.11 -m venv .venvs/rsvlm
. .venvs/rsvlm/bin/activate
pip install -U pip
pip install "torch==2.4.*" --index-url https://download.pytorch.org/whl/cu121
pip install "transformers>=4.49" accelerate qwen-vl-utils bitsandbytes psutil pillow
# GeoChat only: its own env, LLaVA-1.5 stack (see external/research/GeoChat/pyproject.toml)
#   python3.11 -m venv .venvs/geochat && pip install -e external/research/GeoChat  + deepspeed

# 4. sanity
. .venvs/satquery/bin/activate
python -m pytest packages apps/backend/tests -q          # expect: all pass
python evaluation/scripts/exp002_ab_gate.py --resolve    # expect: DATASET_MISSING (until step 5)
```

## Artifact acquisition (the thing the dev host cannot do)

```bash
# --- model weights -> models/cache/ (gitignored) ---
. .venvs/rsvlm/bin/activate
export HF_HUB_ENABLE_HF_TRANSFER=1
hf download Qingyun/rscovlm            --local-dir models/cache/rscovlm            # RSCoVLM-3B (pick the 3B repo in the collection)
hf download aybora/Qwen2-VL-TinyRS     --local-dir models/cache/tinyrs/Qwen2-VL-TinyRS
hf download Qwen/Qwen2-VL-2B-Instruct  --local-dir models/cache/qwen2vl2b/Qwen2-VL-2B-Instruct
hf download akshaydudhane/EarthDial_4B_RGB --local-dir models/cache/earthdial/EarthDial_4B_RGB
hf download MBZUAI/geochat-7B          --local-dir models/cache/geochat/geochat-7B

# --- eval datasets -> evaluation/datasets/ (gitignored) ---
# RSVQA-LR  (Zenodo 3945396): LR_split_test_questions.json + _answers.json + Images_LR/
#   place under  evaluation/datasets/RSVQA-LR/
# DIOR-RSVG (github.com/ZhanYang-nwpu/RSVG-pytorch): test.txt + Annotations/ + JPEGImages/
#   place under  evaluation/datasets/DIOR-RSVG/
python evaluation/scripts/exp002_ab_gate.py --resolve    # now populates resolved_ids in the sample specs
```

## Run the experiments (each writes evaluation/reports/*.json)

```bash
. .venvs/rsvlm/bin/activate
# Phase 2 — EXP-002 A/B gate (local candidates + references, SAME frozen samples)
for m in rscovlm-3b tinyrs-2b qwen2vl-2b; do
  python evaluation/scripts/exp002_ab_gate.py --model $m --quant 4bit
done
# references — EarthDial via .venvs/rsvlm (InternVL path), GeoChat via .venvs/geochat
#   (add --model earthdial-4b / geochat-7b once their loader branches are wired in the harness)

# Phase 5 — EXP-004 Run 2  (smallest valid S1+S2: see docs/research/EXP-004.md "dataset")
python evaluation/scripts/exp004_run2_probe.py            # 3 arms: optical-only / CROMA joint / DOFA fused

# Phase 6 — EXP-008  (frozen encoder + linear probe, THEN LoRA)
python evaluation/scripts/exp008_adaptation.py --method linear_probe
python evaluation/scripts/exp008_adaptation.py --method lora

# push results
git add docs/ evaluation/scripts/ && git commit -m "eval: G6 remote results" && git push
```

## Record the box (fill this in on first boot)

```bash
{ echo "## Provisioned $(date -u +%FT%TZ)"
  echo "- host: $(hostname)  cloud: <PENDING>"
  echo "- OS: $(. /etc/os-release; echo $PRETTY_NAME)"
  echo "- kernel: $(uname -r)"
  echo "- GPU: $(nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader)"
  echo "- CUDA (driver): $(nvidia-smi | grep -oP 'CUDA Version: \K[0-9.]+')"
  echo "- CUDA (toolkit): $(nvcc --version 2>/dev/null | grep -oP 'release \K[0-9.]+' || echo none)"
  echo "- python: $(python3.11 --version)"
  echo "- torch: $(.venvs/rsvlm/bin/python -c 'import torch;print(torch.__version__, torch.version.cuda)')"
  echo "- disk free: $(df -h --output=avail . | tail -1)"
  echo "- net down: $(curl -s -o /dev/null -w '%{speed_download} B/s' https://huggingface.co)"
} >> docs/deployment/REMOTE_GPU_SETUP.md
```

### Provisioned — `<PENDING>`

| Field | Value |
|-------|-------|
| Cloud / instance type | `<PENDING>` |
| OS | `<PENDING>` |
| GPU / VRAM | `<PENDING>` |
| Driver / CUDA (driver) / CUDA (toolkit) | `<PENDING>` |
| Python | `<PENDING>` |
| Torch / torch.version.cuda | `<PENDING>` |
| Disk free | `<PENDING>` |
| Network down (HF) | `<PENDING>` |
| Setup commands run | as above, verbatim |
| First `make test` result | `<PENDING>` |
