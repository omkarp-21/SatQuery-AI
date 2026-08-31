# Research Runtime Validation (G1 + G1.6)

> Goal: determine which candidate research repos can actually run, on this
> hardware, and should become SatQuery specialist workers.
> Date: **2026-09-01** · Method: isolated venv per model, run the smallest
> **official** inference example, record real outcomes. No repo source modified.
> No training, no fine-tuning, no large datasets. Companion:
> `docs/research/model_inventory.md`, `docs/research/MODEL_TOURNAMENT.md`,
> `docs/research/repository_compatibility.md`, `docs/research/environment_strategy.md`.
>
> **G1.6 update:** added **CROMA** and **DOFA** — both **REPRODUCED** on CPU
> (sections below). ChangeChat re-verified: still no weights (README now cites
> ≥48 GB VRAM for training) → REJECT stands.
>
> **G2 update (2026-09-01):** **ChangeFormer is now INTEGRATED** — it runs inside
> the temporal vertical slice via a subprocess adapter (`.venvs/changeformer`),
> product code never imports the repo. CROMA + DOFA feature-extraction exercised in
> the EXP-004 Run 1 harness (`docs/research/EXP-004.md`). New venv `.venvs/satquery`
> (rasterio/pyproj) for the geospatial slice; `.venvs/tinyrs` set up for EXP-002
> (weight download flaky — N=0).

## Validation host

| | |
|---|---|
| OS | Windows 11 (MSYS2 bash). **No** conda, Docker, or WSL. |
| Python | 3.11.0 and 3.9.13 available |
| GPU | NVIDIA RTX 3050 Ti Laptop — **4 GB VRAM**, Ampere (sm_86, so CUDA ≥ 11.x only) |
| RAM / disk | disk ~108 GB free |
| Network | PyPI ✓, HuggingFace ✓, GitHub releases ✓ (≈5–10 MB/s) |

Consequences: a 7B VLM cannot be loaded (4 GB VRAM); Linux-only build deps
(`deepspeed`, `bitsandbytes`, `mmcv==1.3.1` ops) cannot be compiled here; CUDA-10.2
pinned stacks are unusable on Ampere.

## Results summary

| Model | STATUS | Ran official example? | Integration cost | Recommendation |
|-------|--------|-----------------------|------------------|----------------|
| **RemoteCLIP** | **RUNNING** | yes — zero-shot classification, correct | **LOW** | **KEEP** |
| **ChangeFormer** | **RUNNING** | yes — `demo_LEVIR.py`, 7 masks, IoU 0.83 (n=7) | **LOW–MEDIUM** | **KEEP** |
| **CROMA** | **RUNNING** (G1.6) | yes — `use_croma.py`, joint SAR+optical embeddings | **LOW–MEDIUM** | **KEEP FOR TOURNAMENT** (primary optical–SAR) |
| **DOFA** | **RUNNING** (G1.6) | yes — `forward_features` for S1 + S2 | **LOW** | **KEEP FOR TOURNAMENT** (CROMA challenger) |
| **GeoChat** | **BLOCKED** (hardware + deps) | no | HIGH | **TEST FURTHER** (needs ≥16 GB GPU / cloud) |
| **Change-Agent** | **BLOCKED** (deps) | no | HIGH | **TEST FURTHER** (mmcv build; Linux) |
| **ChangeChat** | **BLOCKED** (no artifacts) | no — no released weights (README now: ≥48 GB VRAM to train) | n/a | **REJECT for now** |

**G1.6 new candidates not runtime-tested this session** (research phase, install/
download not justified — see `MODEL_TOURNAMENT.md`): TinyRS, RSCoVLM-3B (local,
TEST FURTHER next session), GeoGround, UniRS, LRS-VQA (remote-GPU), RS-MoE
(REJECT — no weights), SARLANG-1M (dataset, not a model).

---

## RemoteCLIP — `external/research/RemoteCLIP` @ `a6a4787`

**STATUS:** RUNNING

**TASKS:** image–text retrieval, zero-shot scene classification, embedding
extraction (single optical image).

**INPUT:** one RGB image (OpenCLIP preprocess for the backbone) + a list of text
prompts (`open_clip.get_tokenizer`).

**OUTPUT:** L2-normalized image & text embeddings → cosine-similarity logits →
softmax over the candidate prompts (or a ranking for retrieval).

**HARDWARE:** ran on **CPU** (torch 2.13.0+cpu). ViT-B-32 = 151.3 M params.
Process RSS ≈ **1.6 GB** (torch runtime + fp32 weights ≈ 605 MB checkpoint).
Fits the 4 GB GPU trivially; GPU not separately timed (CPU build installed).

**LATENCY:** weights load ≈ 1.5 s. Warm inference (1 image + 3–5 prompts):
**≈ 150 ms / query on CPU** (first call 232 ms, then 145–151 ms).

**QUALITY EVIDENCE:** official example on `assets/airport.jpg` with prompts
{airport, university campus, farmland, harbour, residential area} →
**97.78 % "An airport"** (next: farmland 1.44 %). `load_state_dict:
<All keys matched successfully>` into `open-clip-torch` 3.3.0. This is a
sanity check, not a benchmark (n = 1). Author paper numbers (retrieval R@1 etc.)
not reproduced — would need RET-3/SEG-4/DET-10 (`docs/11`).

**DEPENDENCY RISKS:** very low. `pip install open-clip-torch pillow` only; no
version pins in the repo; checkpoint is standard OpenCLIP format so a *newer*
open_clip (3.3.0) still loads the 2023 weights cleanly. No CUDA, no build steps.

**LICENSE:** Apache-2.0 (`LICENSE` present).

**INTEGRATION COST:** **LOW.** Pure-pip venv, CPU-capable, permissive licence,
5 MB repo, stable I/O. Adapter is a thin wrapper over `create_model_and_transforms`
+ `load_state_dict` + `encode_image` / `encode_text`.

**RECOMMENDATION:** **KEEP.** First specialist to wire (V0). Use for scene
retrieval / zero-shot tagging / an embedding index feeding routing and evidence.

**Repro:** `.venvs/remoteclip` (open-clip-torch 3.3.0, torch 2.13.0+cpu);
checkpoint `models/cache/remoteclip/RemoteCLIP-ViT-B-32.pt`
(`chendelong/RemoteCLIP`, 605 208 421 bytes).

---

## ChangeFormer — `external/research/ChangeFormer` @ `afd1b7e`

**STATUS:** RUNNING

**TASKS:** binary change detection — pixel-level change mask from a co-registered
bi-temporal RGB pair (`ChangeFormerV6`, SegFormer-style siamese).

**INPUT:** two 256×256 (LEVIR) or 512×512 (DSIFN) RGB images, 3-band, folder
layout `A/`, `B/`, `list/<split>.txt` (+ `label/` for scoring). Normalised to
[-0.5, 0.5].

**OUTPUT:** binary change mask (`n_class = 2`), one PNG per pair (0 = no change,
255 = change) written to `--output_folder`.

**HARDWARE:** ran on **CPU** (torch 2.5.1+cpu). 41.0 M params. Process RSS ≈
**1.0–1.1 GB**. Would use < 0.6 GB VRAM on the 4 GB GPU (not separately timed —
CPU build installed).

**LATENCY:** model load ≈ 1.1 s. Inference **≈ 790 ms / 256×256 pair on CPU**
(6-run range 772–846 ms). Full `demo_LEVIR.py` over 7 bundled pairs: **17 s**
end-to-end incl. startup. GPU would be ~1–2 orders faster.

**QUALITY EVIDENCE:** `demo_LEVIR.py` completed **exit 0**, produced 7 masks for
the bundled `samples_LEVIR` test pairs (12–25 % changed pixels each — not
degenerate). Scored against the bundled `samples_LEVIR/label/` (7 have labels):
**change-IoU = 0.832, change-F1 = 0.908** (micro-averaged, n = 7). This is a
*SatQuery reproduction* number on a tiny sample — **not** a benchmark. Author's
own record (checkpoint `log.txt`): `Historical_best_acc = 0.9495` overall pixel
accuracy on LEVIR-CD test (their number). Full LEVIR-CD / DSIFN reproduction
deferred (`docs/11`, dataset not downloaded).

**DEPENDENCY RISKS:** MEDIUM. The repo's `requirements.txt` is a linux-64 conda
lockfile (torch 1.10.1 / CUDA 10.2) that **cannot** be used on Ampere or on
Windows. Ran instead on a rebuilt stack: **torch 2.5.1 + numpy 1.23.5** (+
`opencv-python-headless 4.9`, `tifffile`, `scikit-image 0.21`, `scipy 1.10`,
`timm`, `einops`). Constraints found:
- `datasets/CD_dataset.py` uses `np.str` (removed in NumPy ≥ 1.24) → pin
  `numpy < 1.24`.
- `models/basic_model.py` calls `torch.load` without `weights_only=False` →
  breaks on torch ≥ 2.6 (checkpoint holds a numpy scalar) → pin **torch < 2.6**.
- runtime imports not in the lockfile: `cv2`, `tifffile`.
All handled at the **environment** level — **no repo source was modified.**
A dedicated py3.9 + torch 1.13 env would also work and stay closer to the paper.

**LICENSE:** MIT (`LICENSE` present).

**INTEGRATION COST:** **LOW–MEDIUM.** Small model, fast, MIT, no LLM, deterministic
mask output — ideal as the change-mask backend. Cost is entirely the pinned
environment (numpy < 1.24, torch < 2.6); the adapter itself is straightforward
(`CDEvaluator` + `_forward_pass`). Its output is language-free, so it pairs with a
captioner/VLM for semantic change.

**RECOMMENDATION:** **KEEP.** Primary bi-temporal **change-mask** specialist for
V1. Feeds fusion / verification / the geospatial area computation.

**Repro:** `.venvs/changeformer` (torch 2.5.1+cpu, numpy 1.23.5);
checkpoint `models/cache/changeformer/CD_ChangeFormerV6_LEVIR_.../best_ckpt.pt`
(GitHub release v0.1.0, model 41 M params inside a 492 MB training checkpoint);
command run from the repo dir:
`python demo_LEVIR.py --gpu_ids -1 --checkpoint_root <cache> --project_name <dir> --output_folder <scratch>`.

---

## GeoChat — `external/research/GeoChat` @ `4850920`

**STATUS:** BLOCKED (hardware + dependencies)

**TASKS (documented, not verified here):** conversational VQA, region captioning,
visual grounding (rotated boxes), scene classification on single optical RS images.

**INPUT:** one RGB RS image (`image-aspect-ratio pad`, ~504 px) + a text prompt
with task tags (`[grounding]`, `[refer]`, …).

**OUTPUT:** text; grounding boxes encoded in the text.

**HARDWARE:** **insufficient.** `MBZUAI/geochat-7B` is a **LoRA-merged full model**
(≥ 7B params; HF repo ≈ 14 GB fp16). 4 GB VRAM cannot hold it even at 4-bit
(≈ 5–6 GB). CPU inference needs ≈ 16 GB RAM and is minutes/response (no
`flash-attn`).

**LATENCY / QUALITY EVIDENCE:** none — not run.

**DEPENDENCY RISKS:** HIGH, and partly fatal on this host:
- `deepspeed==0.9.5` — `pip install` **fails on Windows**: setup.py aborts with
  `AssertionError: Unable to pre-compile ops without torch installed` (it pre-compiles
  C++/CUDA ops at build time; unsupported here).
- `bitsandbytes==0.41.0` — no Windows wheels (Windows support only in bnb ≥ 0.43);
  needed for the 4-/8-bit loading that might otherwise shrink VRAM.
- `gradio==3.35.2` pins `pydantic < 2` (conflicts with SatQuery's Pydantic v2 — but
  the research env is isolated, so this only matters inside the GeoChat env).

**LICENSE:** **no `LICENSE` file in the repo**; `pyproject.toml` classifier says
Apache-2.0. Treat as Apache-2.0, **unconfirmed** — verify with the authors before
any redistribution.

**INTEGRATION COST:** **HIGH.** Needs a Linux GPU box with ≥ 16 GB VRAM (or ≥ 8 GB
+ bnb ≥ 0.43 4-bit), a ~14 GB weight download, and the LLaVA/DeepSpeed toolchain.

**RECOMMENDATION:** **TEST FURTHER** — off this laptop. Provision a cloud/Linux GPU
(A10/A100 or ≥ 16 GB), then reproduce `geochat_demo.py` / the `batch_geochat_*`
eval scripts and run **EXP-001** (H1). Until then it is not part of the first
runnable stack.

---

## Change-Agent — `external/research/Change-Agent` @ `68cbaa7`

**STATUS:** BLOCKED (dependencies)

**TASKS (documented, not verified here):** bi-temporal multi-class change
detection (building / road) + change captioning, orchestrated by a vendored
`lagent` agent.

**INPUT:** co-registered bi-temporal RGB pair (LEVIR-MCI style, 256×256) + a
natural-language instruction for the agent layer.

**OUTPUT:** multi-class change masks + change-caption text; the agent composes
these via tool calls (needs an OpenAI-compatible LLM endpoint).

**HARDWARE:** the perception model (`MCI_model.pth`) would fit 4 GB, but the env
could not be built, so nothing was run.

**LATENCY / QUALITY EVIDENCE:** none — not run.

**DEPENDENCY RISKS:** HIGH:
- `mmcv==1.3.1` — **unbuildable here.** `pip install mmcv==1.3.1` fails at build
  setup (`ModuleNotFoundError: No module named 'pkg_resources'` in the isolated
  build env; the 2021-era setup.py is incompatible with modern setuptools) and,
  even past that, would need the CUDA toolkit + MSVC to compile ops. No prebuilt
  wheels exist for any current Python/torch.
- `mmsegmentation==0.13.0` (mmcv-1.x era) mixed with `mmengine==0.9.1` (2.x era) —
  unsupported combination.
- Internal conflict: `Multi_change` pins `transformers==4.33.1`; the vendored
  `lagent` needs `transformers>=4.34` → two sub-environments even within this repo.
- Agent layer requires an OpenAI API key; `MCI_model.pth` + LEVIR-MCI not
  downloaded.

**LICENSE:** MIT (`LICENSE.txt`).

**INTEGRATION COST:** **HIGH.** Needs Linux + conda + a from-source `mmcv` build
(or a port to a modern `mmcv`/`mmseg`), plus splitting perception vs agent envs.

**RECOMMENDATION:** **TEST FURTHER** — on Linux with conda, build the perception
env only, run `Multi_change/test.py` on LEVIR-MCI, and compare against ChangeFormer
in **EXP-003**. The `lagent` agent layer is a *reference*, not something we adopt
(our orchestration is `packages/agents`). Not in the first runnable stack.

---

## ChangeChat — `external/research/ChangeChat` @ `9facf50`

**STATUS:** BLOCKED (no runnable artifacts)

**TASKS (documented):** instruction-tuned bi-temporal change conversation — change
captioning, change VQA, change grounding.

**INPUT / OUTPUT:** bi-temporal RGB pair + instruction → text.

**HARDWARE / LATENCY / QUALITY EVIDENCE:** none — cannot run.

**DEPENDENCY RISKS:** the repo is a GeoChat fork (same `torch==2.0.1` /
`transformers==4.31.0` / `bitsandbytes` / `gradio<3.36` stack, same Windows/VRAM
problems as GeoChat) **and**:
- **No released weights** — README says "coming soon"; `hf-models/` and `load/`
  are empty.
- **No `requirements.txt`** at the pinned commit, though the README references one.

**LICENSE:** no `LICENSE` file; `pyproject.toml` (copied from GeoChat) says
Apache-2.0 — **unconfirmed**.

**INTEGRATION COST:** cannot be assessed — nothing to integrate.

**RECOMMENDATION:** **REJECT for now.** Re-open only if the authors release
weights **and** a dependency spec. Its role (conversational change) is covered in
the interim by ChangeFormer (mask) + a captioner/VLM, or by Change-Agent once its
env is solved.

**G1.6 re-verification (2026-09-01):** fetched the current GitHub README. Still
**no released weights** ("coming soon"); a `requirements.txt` is now referenced;
README now states **"NVIDIA GPU with ≥48 GB VRAM (L20 recommended)", CUDA 11.7+**
for training; repo shows only 2 commits. Verdict unchanged: **REJECT for now.**

---

## CROMA — `external/research/CROMA` (G1.6, cloned 2026-09-01, `--depth 1`)

**STATUS:** RUNNING — **REPRODUCED**

**TASKS:** contrastive radar-optical masked autoencoder → **joint / per-modality
representations** (embeddings) from a co-registered Sentinel-1 + Sentinel-2 patch.
No language, no task head — a backbone for downstream probing / retrieval / change.

**INPUT:** Sentinel-1 SAR **2 channels** (VV, VH) + Sentinel-2 optical **12
channels** (drop the cirrus band), default **120×120 px** (`image_resolution`
configurable, multiple of 8). Channel-wise normalise (mean ± 2σ clip), the repo's
`normalize()`.

**OUTPUT:** dict — `SAR_encodings` (B, 225, 768), `SAR_GAP` (B, 768),
`optical_encodings`, `optical_GAP`, **`joint_encodings` (B, 225, 768)**,
**`joint_GAP` (B, 768)**. 225 = (120/8)². `dim=768` (base).

**HARDWARE:** ran on **CPU** (torch 2.13.0+cpu). **194.4 M params** (s1 enc depth
6 + s2 enc depth 12 + cross enc depth 6). Process RSS ≈ 1.1–1.8 GB. Fits the 4 GB
GPU with ~3.5 GB headroom.

**LATENCY:** model load ≈ 2.6 s. Joint forward (SAR + optical + cross) **≈ 340
ms/sample on CPU** (batch of 8 in ≈ 2.7 s). Expect ~10–30 ms/sample on the 4 GB GPU.

**QUALITY EVIDENCE:** official `use_croma.py` example (README) reproduced exactly —
random S1/S2 tensors → all 6 output keys, correct shapes, `joint_GAP` finite and
varies across samples (std 0.047). Checkpoint `CROMA_base.pt` (`antofuller/CROMA`,
777 563 846 bytes) loads as a dict of `s1_encoder / s1_GAP_FFN / s2_encoder /
s2_GAP_FFN / joint_encoder`. **REPRODUCED, not MEASURED** — no real data / metric
yet (that is EXP-004). Paper (#1): SOTA-class linear-probe results on BigEarthNet,
DFC2020 (NeurIPS 2023) — unverified by us.

**DEPENDENCY RISKS:** **very low.** `pip install torch einops` only; no pins in the
repo; `use_croma.py` is device-agnostic (no hardcoded `.cuda()`). numpy needed for
the torch build but not by the example. No CUDA, no build steps, no source edits.

**LICENSE:** **MIT** (`LICENSE` present).

**INTEGRATION COST:** **LOW–MEDIUM.** Tiny deps, MIT, CPU-capable, stable I/O. Cost
is the Sentinel-1/2 preprocessing (12-band S2, 2-band S1 in dB, channel norm,
120-px tiling) and a small trained head for any actual task.

**RECOMMENDATION:** **KEEP FOR TOURNAMENT — primary optical–SAR candidate.** Native
joint radar-optical cross-encoder → matches the PS "joint reasoning" wording.
Decide CROMA vs DOFA in **EXP-004**; do not adopt before a measured SAR delta.

**Repro:** `.venvs/croma` (torch 2.13.0+cpu, einops 0.8.2);
`models/cache/croma/CROMA_base.pt`; script = README example, `modality='both'`,
`size='base'`, CPU.

---

## DOFA — `external/research/DOFA` (G1.6, cloned 2026-09-01, `--depth 1`)

**STATUS:** RUNNING — **REPRODUCED**

**TASKS:** dynamic-one-for-all multi-sensor foundation model → **per-modality
representations** via a single **wavelength-conditioned** encoder. Any band count
if you supply the wavelengths. No language, no task head.

**INPUT:** an image tensor `(B, C, 224, 224)` + a `wave_list` of central
wavelengths. Validated here for **Sentinel-2 (12 ch, µm)** and **Sentinel-1 SAR
(2 ch, C-band ≈ 5.405)**. C can be 2/3/4/6/9/12/13/202/…

**OUTPUT:** `forward_features(x, wave_list)` → global feature **(B, 768)** (ViT-B).
Patch tokens available via the model internals.

**HARDWARE:** ran on **CPU** (torch 2.13.0+cpu, `timm==0.9.2`). **111.3 M params.**
Process RSS ≈ 1.3 GB. Fits the 4 GB GPU with huge headroom.

**LATENCY:** load ≈ 0.9 s. `forward_features` **≈ 130 ms/sample (S2, CPU)**, **≈
110 ms/sample (S1, CPU)** at batch 4.

**QUALITY EVIDENCE:** built `vit_base_patch16`, loaded `DOFA_ViT_base_e100.pth`
(`XShadow/DOFA`, 447 669 164 bytes) with `strict=False` → `missing=4 unexpected=5`
(exactly the MAE `fc_norm/head` vs `mask_token/norm/projector` keys the README
documents). `forward_features` returns finite `(B, 768)` for **both** S1 and S2
through one encoder. **REPRODUCED, not MEASURED.** Paper (#1): competitive with
sensor-specific FMs on GEO-Bench — unverified by us.

**DEPENDENCY RISKS:** **low.** `pip install torch "timm==0.9.2"` (+ `huggingface_hub`
for the download). Heavy repo `requirements.txt` entries (`kornia`, `rasterio`,
`geobench`) are for downstream/demo data only, not the encoder. No source edits.
Note: the README warns to use the **new** `wave_dynamic_layer.py` with the new
weights — the repo clone already has it.

**LICENSE:** **MIT** (`LICENSE` present).

**INTEGRATION COST:** **LOW.** One small file (`dofa_v1.py` + `wave_dynamic_layer.py`),
`timm==0.9.2`, MIT. Fusion of S1+S2 is a downstream design choice (concat / small
head) — not native like CROMA.

**RECOMMENDATION:** **KEEP FOR TOURNAMENT — CROMA challenger.** Lighter, more
flexible (any sensor, one model), and a fair "does native fusion help?" baseline
against CROMA. Decide in **EXP-004**.

**Repro:** `.venvs/dofa` (torch 2.13.0+cpu, `timm==0.9.2`, numpy 1.26.4);
`models/cache/dofa/DOFA_ViT_base_e100.pth`; `forward_features` with S2/S1 wavelength
lists, CPU.

---

## Ranked recommendation — first SatQuery specialist stack (evidence-based, post-G1.6)

1. **RemoteCLIP — KEEP, wire first (V0).** Runs today, zero friction: pure pip,
   CPU-ok, Apache-2.0, official example correct, ~150 ms. Role: scene retrieval /
   zero-shot tagging / planner-aux embedding index. **Not** a VQA model.
2. **ChangeFormer — KEEP, wire second (V1 change path).** Pinned env (numpy < 1.24,
   torch < 2.6), no source edits, MIT, deterministic masks, IoU 0.83 (n = 7).
   Role: bi-temporal change-**mask** backend. Language side = a composed pipeline
   (EXP-003).
3. **CROMA — KEEP FOR TOURNAMENT (primary optical–SAR).** REPRODUCED on CPU, MIT,
   194 M, native joint SAR-optical encoder. Enters the stack **if EXP-004** shows a
   real SAR delta. Also the encoder for the EXP-008 adaptation probe.
4. **DOFA — KEEP FOR TOURNAMENT (CROMA challenger).** REPRODUCED on CPU, MIT, 111 M,
   one wavelength-conditioned encoder for S1 + S2 + more. Head-to-head with CROMA in
   EXP-004.
5. **TinyRS / RSCoVLM-3B — TEST FURTHER (local, next session).** The only
   released-weight VQA candidates that plausibly run on 4 GB. EXP-002 picks one for
   capabilities A + B.
6. **GeoChat / GeoGround / TEOChat — TEST FURTHER on one remote GPU ≥16 GB** — only
   if the local VQA candidates are measured to underperform (EXP-002 gate).
7. **Change-Agent — TEST FURTHER on Linux+conda** (EXP-003 semantic ceiling).
8. **ChangeChat — REJECT for now.** No weights (README now cites ≥48 GB to train).
9. **RS-MoE — REJECT for now.** No released weights, no inference path.

**Minimum V0 stack = RemoteCLIP + ChangeFormer + (pending EXP-004) CROMA.**
VQA/grounding (A/B) join at V0.5 once EXP-002 picks the local single-image model.
No remote GPU until EXP-002/004/008 are done.
