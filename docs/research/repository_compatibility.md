# Repository Compatibility Analysis

> Companion to `docs/research/model_inventory.md`. Purpose: show why the six
> research repos **cannot share one environment**, and what conflicts each pair
> creates. Compiled 2026-08-31 from repository inspection only.

## TL;DR

There is **no single Python/PyTorch/CUDA environment** that satisfies all repos.
They must be isolated (one env or container per model). Do **not** merge their
requirements files. Details below.

## Conflict matrix

| Axis | GeoChat | Change-Agent | ChangeChat | ChangeFormer | RemoteCLIP |
|------|---------|--------------|------------|--------------|------------|
| Python | 3.10 | 3.9 | 3.9 | **3.8** | flexible |
| PyTorch | 2.0.1 | 2.0.1 (+cu118) | 2.0.1 | **1.10.1** | via open-clip |
| CUDA | 11.7/11.8 | **11.8** | 11.7+ | **10.2** | optional |
| transformers | ==4.31.0 | ==4.33.1 *(lagent wants ≥4.34)* | ==4.31.0 | not used | not used |
| numpy | <2 (sklearn 1.2.2) | ==1.25.2 | <2 | ==1.21.2 | unpinned |
| gradio | ==3.35.2 *(pydantic<2)* | — | ==3.35.2 | — | — |
| Extra stack | deepspeed, bitsandbytes, peft, flash-attn | **OpenMMLab: mmcv 1.3.1 + mmseg 0.13.0 + mmengine 0.9.1**, lmdeploy, vllm | same as GeoChat | timm 0.4.12 (old) | open-clip-torch, clip_benchmark |

## Pairwise conflicts

### ChangeFormer vs everything else — the hard wall
- **CUDA 10.2 vs 11.8.** ChangeFormer's `requirements.txt` locks
  `pytorch=1.10.1=py3.8_cuda10.2_cudnn7.6.5`. CUDA 10.2 / cuDNN 7.6.5 predates
  Ampere and **will not run on RTX 30xx/40xx, A100, H100**.
- **Python 3.8 vs 3.9/3.10.** GeoChat needs 3.10 features via its deps; ChangeFormer's
  lockfile is 3.8-only.
- **PyTorch 1.10 vs 2.0.** ABI-incompatible C extensions (`timm`, custom ops).
- Cannot co-exist in one env with any other repo. Mitigation: rebuild ChangeFormer
  against torch ≥1.12 on cu113+ (model code is small and portable) **or** run it
  CPU-only. Either way, its own env.

### Change-Agent — conflicts with itself and with GeoChat/ChangeChat
- **Internal:** `Multi_change/requirement.txt` pins `transformers==4.33.1`;
  `lagent-main` requires `transformers>=4.34`. The perception model and the agent
  layer need **different transformers** → two sub-environments even within this repo.
- **OpenMMLab stack:** `mmcv==1.3.1` + `mmsegmentation==0.13.0` are mmcv-1.x-era and
  have **no prebuilt wheels for torch 2.0 / cu118** → source build required. Mixing
  them with `mmengine==0.9.1` (the 2.x runtime) is an unsupported combination.
- **vs GeoChat/ChangeChat:** different `transformers` pin (4.33.1 vs 4.31.0) and the
  heavy MM stack that the others don't want. Separate env.

### GeoChat vs ChangeChat — near-identical, still separate
- Same code lineage, same pins (`torch==2.0.1`, `transformers==4.31.0`,
  `bitsandbytes==0.41.0`, `gradio==3.35.2`). They *could* technically share a base
  image, **but**:
  - ChangeChat has **no released weights** and **no `requirements.txt`** at the
    pinned commit — not runnable yet.
  - Keeping them separate preserves clean provenance per model and lets ChangeChat's
    env change when it actually ships deps.
- Recommendation: one shared base image, two derived envs.

### RemoteCLIP vs everything else — compatible in spirit, isolate anyway
- No hard pins, Apache-2.0, CPU-capable, pure pip. It *could* live alongside others,
  but `open-clip-torch` pulls its own `torch`/`timm` and `clip_benchmark` pulls a
  `clip` package — enough to perturb a carefully pinned GeoChat env. Cheap to keep
  in its own venv.

### Shared secondary conflicts
- **`gradio==3.35.2`** (GeoChat, ChangeChat) forces **`pydantic<2`**. Anything in
  the same env needing `pydantic>=2` (incl. modern FastAPI) breaks. SatQuery's own
  backend uses Pydantic v2 — another reason these never touch the product env.
- **`bitsandbytes==0.41.0`, `deepspeed==0.9.5`, `flash-attn`** — Linux + CUDA only.
  No native Windows wheels. The dev host is Windows 11 → these repos run in Linux
  containers or WSL2, not on the host interpreter.
- **numpy**: 1.21.2 (ChangeFormer) vs 1.25.2 (Change-Agent) vs "<2" (GeoChat via
  scikit-learn 1.2.2). All pre-2.0 but pinned differently; a merged env would have
  to pick one and hope.

## Isolation from the SatQuery product environment

`apps/` and `packages/` use Python 3.11 + Pydantic v2 + FastAPI. **Every** research
repo conflicts with that (Python version, `pydantic<2` via gradio, torch pins).
Product code must never import research code — integration is via
`packages/model_adapters/` calling an isolated env/container (subprocess) or a
minimal vendored inference path. See `.claude/rules/ai-models.md`.

## Decision

Per-model isolation, detailed in `docs/research/environment_strategy.md`:

| Model | Isolation unit | Why |
|-------|----------------|-----|
| GeoChat | Docker image `satquery/research-geochat` (Linux, cu118, py3.10) | bitsandbytes/deepspeed Linux-only; pydantic<2 |
| ChangeChat | Derived from the GeoChat base, own tag | same lineage; deps not finalized upstream |
| Change-Agent (perception) | Docker image `satquery/research-changeagent` (Linux, cu118, py3.9) + mmcv source build | MM stack, transformers 4.33.1 |
| Change-Agent (agent/lagent) | separate venv or image, transformers ≥4.34 | internal conflict with the perception pin |
| ChangeFormer | Docker image `satquery/research-changeformer` — **rebuilt** on torch 1.12+/cu113 (not the cu10.2 lockfile) | CUDA 10.2 unusable on modern GPUs |
| RemoteCLIP | plain venv `.venvs/remoteclip` (py3.11, pip) | no hard pins, CPU-ok, Apache-2.0 |
| awesome-rs-vlms | none | not code |
