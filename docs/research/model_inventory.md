# Research Model Inventory

> Status: repo inspection (2026-08-31) **+ G1 runtime validation** **+ G1.5
> candidate scouting** **+ G1.6 model tournament (2026-09-01)**.
> Runtime evidence: **`docs/research/runtime_validation.md`**. Tournament +
> full candidate cards: **`docs/research/MODEL_TOURNAMENT.md`**. Gaps:
> **`docs/research/CAPABILITY_GAP_MATRIX.md`**. Branching: **`EXPERIMENT_DECISION_TREE.md`**.
> Source clones: `external/research/` (gitignored, read-only).
> (File is `model_inventory.md` — earlier briefs call it `MODEL_INVENTORY.md`.)

## Evidence ladder — 5 levels, kept separate

| Level | Meaning |
|-------|---------|
| **PAPER-REPORTED** | The authors' number, their setup. (number #1) |
| **DOCUMENTED** | The repo states the capability; we have not run it. |
| **REPRODUCED** | We ran the official example → sane result on ≥1 input. |
| **MEASURED** | We scored it vs reference data; metric + dataset + split + hardware recorded. (#2 / #3) |
| **INTEGRATED** | Runs inside the SatQuery pipeline via an adapter, with provenance. |
| **VALIDATED** | End-to-end in the pipeline, verified, with provenance. |

> **G7–G9 (2026-09-01):** semantic verifier MEASURED + INTEGRATED (EXP-005b);
> failure-aware routing INTEGRATED (`derive_resolution` + `image_difference_fallback`
> + `LOW_MARGIN` advisory). Stack NOT frozen.
>
> **Local Lightweight Model Tournament (2026-09-01):** inspected 3 new candidates
> from official GitHub/HF. **RemoteSAM** (~200 M grounding/segmentation
> specialist) → **TEST FURTHER, lead capability-B candidate**. **RS-MoE** → REJECT
> (no artifact; "MoE not yet implemented"). **DynamicVis** → REJECT for product
> (Mamba: Windows + CPU incompatible). Product confirmed to have **no mandatory
> 7B/16 GB dependency**. Full record: `LOCAL_LIGHTWEIGHT_MODEL_TOURNAMENT.md`.
>
> **Model hierarchy (ADR-011/012) — role labels, not a quality ranking.** LOCAL
> A/B PRIMARY = **RSCoVLM-3B**; LOCAL A/B FALLBACK = **TinyRS-2B**; GENERIC CONTROL
> = **Qwen2-VL-2B**; TEMPORAL = **ChangeFormer**; OPTICAL-SAR PRIMARY = **CROMA**;
> OPTICAL-SAR CHALLENGER = **DOFA**; GROUNDING REFERENCE = **GeoGround**; AUXILIARY
> = **RemoteCLIP**; PRIMARY HIGH-CAPABILITY REFERENCE = **EarthDial** (REFERENCE
> CANDIDATE — not reproduced); SECONDARY / HISTORICAL RS-VLM REFERENCE = **GeoChat**
> (not on the critical path; local-run inability is **not** a blocker); RESEARCH
> REFERENCE = **SARLANG-1M**. Authoritative table: `MODEL_TOURNAMENT.md`.
> **No repo is a "ceiling" until reproduced + measured.**

| Model | Documented | Reproduced | Measured | Integrated | Overall |
|-------|:---------:|:---------:|:--------:|:----------:|---------|
| RemoteCLIP | ✅ | ✅ (zero-shot airport 97.8 %) | ⚠️ latency only (~150 ms) | ❌ | **RUNNING** — AUXILIARY (retrieval / zero-shot / embedding; **not VQA**) |
| ChangeFormer | ✅ | ✅ (`demo_LEVIR.py`) | ✅ change-IoU 0.832 / F1 0.908 (n=7) | ❌ | **RUNNING** — TEMPORAL (change-mask backend) |
| **CROMA** | ✅ | ✅ (`use_croma.py` — joint SAR+optical embeddings, 194 M, ~340 ms CPU) | ❌ | ❌ | **RUNNING** (G1.6) — OPTICAL-SAR PRIMARY |
| **DOFA** | ✅ | ✅ (`forward_features` S1 2ch + S2 12ch, 111 M, ~120 ms CPU) | ❌ | ❌ | **RUNNING** (G1.6) — OPTICAL-SAR CHALLENGER |
| EarthDial | ✅ (checkpoints verified to exist) | ❌ (4B ≈ 8–9 GB bf16; not run) | ❌ | ❌ | **REFERENCE CANDIDATE** — PRIMARY HIGH-CAPABILITY REFERENCE (remote) |
| GeoChat | ✅ | ❌ (7B > 4 GB VRAM; `deepspeed`/`bnb` unbuildable) | ❌ | ❌ | **SECONDARY / HISTORICAL REFERENCE** — TEST FURTHER on ≥16 GB Linux GPU; **not a blocker** |
| Change-Agent | ✅ | ❌ (`mmcv==1.3.1` unbuildable; `transformers` conflict) | ❌ | ❌ | **BLOCKED** — TEST FURTHER on Linux+conda |
| ChangeChat | ✅ | ❌ (no weights; README now ≥48 GB VRAM to train) | ❌ | ❌ | **REJECT for now** (re-verified G1.6) |

**INTEGRATED count = 0.** No model is in the SatQuery pipeline yet.

## G1.6 candidate pool (15 repos + carry-overs — full cards in `MODEL_TOURNAMENT.md`)

| Candidate | Role | Licence | Weights? | Local (4 GB)? | Verdict |
|-----------|------|---------|----------|---------------|---------|
| CROMA | optical–SAR joint repr. | MIT | yes | ✅ | **REPRODUCED** — primary D |
| DOFA | multi-sensor repr. (incl. SAR) | MIT | yes | ✅ | **REPRODUCED** — D challenger |
| RSCoVLM | multi-task RS VLM (VQA+grounding+detect) | **MIT / CC-BY-4.0** | yes (3B & 7B) | borderline (3B @ 4-bit) | **LOCAL A/B PRIMARY** — **G5A: N=0, artifact BLOCKED**; harness ready |
| TinyRS / R1 | lightweight single-image VLM (VQA, grounding) | Apache-2.0 | yes (`aybora/Qwen2-VL-TinyRS*`) | borderline (2B @ 4-bit) | **LOCAL A/B FALLBACK** — **G5A: N=0**, weight DL failed 5× |
| Qwen2-VL-2B | generic VLM (VQA, native bbox grounding) | Apache-2.0 | yes (`Qwen/Qwen2-VL-2B-Instruct`) | ✅ (4-bit) | **GENERIC CONTROL** — **G5A: N=0**, 6th DL failure (0-byte safetensors) |
| EarthDial | RS multi-task VLM (VQA+grounding+caption, **+SAR +temporal**) | code MIT / weights unconfirmed | yes (`akshaydudhane/EarthDial_4B_{RGB,MS,Methane_UHI}`, InternVL2+Phi-3, 4B) | ❌ (4B ≈ 8–9 GB bf16) | **PRIMARY HIGH-CAPABILITY REFERENCE** — REFERENCE CANDIDATE; **G5A remote reference gate** (run on same frozen samples) |
| GeoGround | RS visual grounding (HBB/OBB/mask) | not stated | yes (`erenzhou/GeoGround`) | ❌ (~7B) | **GROUNDING REFERENCE** (remote) / BACKUP |
| **RemoteSAM** | GROUNDING/SEGMENTATION specialist — referring seg + visual grounding (mask+box) | not stated | yes (`1e12Leon/RemoteSAM`, Swin-B+BERT ~200 M) | ✅ size (`LOCAL-FITS-4GB`); env-BLOCKED (mmcv-full 1.7.1) | **TEST FURTHER — lead capability-B candidate** (`LOCAL_LIGHTWEIGHT_MODEL_TOURNAMENT.md`) |
| **DynamicVis** | PERCEPTION/ENCODER (Mamba SSM) — NOT a VLM; classif/detect/seg/change/retrieval | Apache-2.0 | yes (`KyanChen/DynamicVis` b/l) | VRAM `LOCAL-EASY` (~800 MB/2048px) but **Windows+CPU incompatible** | **REJECT for product** (portability); research watch-item |
| **RS-MoE** (`CongcongWen1208/RS-MoE`) | GENERAL VLM (claim) — captioning + VQA | not stated | **no** — training-only, "MoE not yet implemented", base Vicuna-13B | ❌ | **REJECT (no artifact)** — "RS-MoE-1B" is a paper claim |
| LRS-VQA | large-RS-image VQA + token-pruning + **benchmark** | not stated | yes (7B) | ❌ | **KEEP FOR LATER** — as a VQA benchmark |
| UniRS | unified single/dual-temporal/video VLM | code Apache; **weights CC-BY-NC-SA (non-commercial)** | unclear | ❌ (VILA-1.5) | **BACKUP** — remote, licence-restricted |
| TEOChat | temporal EO VLM (semantic change, change-QA) | non-commercial (LLaMA-derived) | yes | ❌ (~7B) | **TEST FURTHER** — remote C ceiling |
| Change-Agent | temporal semantic + caption | MIT | yes (`MCI_model.pth`) | ❌ (`mmcv`) | **TEST FURTHER** — Linux only |
| RS-MoE | lightweight RS caption + VQA (MoE) | not stated | **no** (training cfgs only) | ? | **REJECT for now** — no artifacts |
| ChangeChat | temporal change caption/VQA | absent | **no** ("coming soon") | ❌ | **REJECT for now** |
| SARLANG-1M | SAR-language **dataset/benchmark** (1M pairs, 7 tasks) | not stated | n/a (data only) | n/a | **KEEP FOR LATER** — SAR-language eval + fine-tune data |
| MaRS | VHR optical–SAR FM (AAAI 2026) | not stated | release unverified | ❌ | **BACKUP / WATCH** — VHR ≠ Sentinel scale |

Each numbered entry below records what the repository itself states or implies.
Where a repo is silent, the field says "not stated" — nothing is invented.

---

## 1. awesome-rs-vlms — `external/research/awesome-rs-vlms`

| Field | Value |
|-------|-------|
| Upstream | github.com/lzw-lzw/awesome-remote-sensing-vision-language-models |
| Commit | `4d620f38e07a4c77a5d4d362fa68a012bc7ab011` (2024-04-27) |
| README | Yes — a curated list of RS vision-language models, datasets, and papers. |
| License | MIT (`LICENSE`) |
| Python / PyTorch / CUDA | N/A — not runnable code. |
| Checkpoints | None. |
| Input / Output | N/A. |
| Inference command | N/A. |
| Role for SatQuery | Literature-review index only. Feeds `research-review`, not integration. |

---

## 2. GeoChat — `external/research/GeoChat`

| Field | Value |
|-------|-------|
| Upstream | github.com/mbzuai-oryx/GeoChat (MBZUAI) |
| Commit | `4850920e005a849bd224d0ce35aa9db031fa5155` (2024-11-28) |
| README | Yes. Grounded LVLM for remote sensing (VQA, region captioning, visual grounding, scene classification). Built on LLaVA-v1.5 / Vicuna-7B. |
| License | **No `LICENSE` file in the repo.** `pyproject.toml` classifier declares "Apache Software License". Treat as **Apache-2.0, unconfirmed** — verify with authors before redistribution. |
| Python | `conda create -n geochat python=3.10` (README). `pyproject.toml` says `requires-python >=3.8`. |
| PyTorch | `torch==2.0.1`, `torchvision==0.15.2` (pinned in `pyproject.toml`). |
| CUDA | Not stated explicitly. `torch==2.0.1` default wheels are cu117/cu118. Optional `flash-attn` needs the CUDA toolkit + `ninja`. GPU expected. |
| Key deps | `transformers==4.31.0`, `peft==0.4.0`, `accelerate==0.21.0`, `deepspeed==0.9.5`, `bitsandbytes==0.41.0`, `gradio==3.35.2`, `timm==0.6.13`, `einops==0.6.1`, `scikit-learn==1.2.2`, `httpx==0.24.0`. |
| Checkpoints | Not downloaded. `docs/MODEL_ZOO.md` + `docs/LoRA.md` list them: GeoChat-7B as a **LoRA delta** over a LLaVA-v1.5-7B / Vicuna-7B base. Base weights must be obtained separately. HF org: `MBZUAI`. |
| Input format | One RGB remote-sensing image (`--image-aspect-ratio pad`; ~504px per paper) + a text prompt. Task-specific prompt conventions for grounding (`[grounding]`), region, scene, VQA. |
| Output format | Text. For grounding: bounding boxes (with rotation angle) encoded in the text response. |
| Inference command | Gradio demo: `python geochat_demo.py --model-path <geochat-7B> --model-base <llava/vicuna-7b>`. Batch eval: `python geochat/eval/batch_geochat_vqa.py --model-path <..> --question-file <..> --image-folder <..> --answers-file <..>` (also `batch_geochat_grounding.py`, `batch_geochat_scene.py`, `batch_geochat_referring.py`). |
| SatQuery role | Single-image optical VQA / grounding / scene specialist. |
| Notes | `bitsandbytes==0.41.0` and `deepspeed==0.9.5` are Linux/CUDA-only — 4-/8-bit loading will not work natively on the Windows dev host. `gradio==3.35.2` pins `pydantic<2`. |
| **Runtime (G1)** | **BLOCKED** (hardware + deps). `MBZUAI/geochat-7B` is a LoRA-*merged* ≥7B model (~14 GB fp16) — exceeds the 4 GB validation GPU even at 4-bit (~5–6 GB). `pip install deepspeed==0.9.5` **fails on Windows** (`AssertionError: Unable to pre-compile ops without torch installed`). `bitsandbytes==0.41.0` has no Windows wheels. Not run; weights not downloaded. Integration cost **HIGH** — needs a Linux GPU ≥16 GB. → **TEST FURTHER** (blocks EXP-001). See `runtime_validation.md`. |

---

## 3. Change-Agent — `external/research/Change-Agent`

| Field | Value |
|-------|-------|
| Upstream | github.com/Chen-Yang-Liu/Change-Agent (IEEE TGRS 2024) |
| Commit | `68cbaa7f388b36e4fc10872f7a2911482d26ae5b` (2025-07-27) |
| README | Yes. Two parts: `Multi_change/` (the MCI model — multi-class change detection + change captioning) and `lagent-main/` (a **vendored copy of the `lagent` agent framework**) that drives tools via an LLM. |
| License | MIT (`LICENSE.txt`). `lagent-main/` carries its own `LICENSE`. |
| Python | `conda create -n Multi_change_env python=3.9` (README). |
| PyTorch | `torch==2.0.1+cu118`, `torchvision==0.15.2+cu118`, `torchaudio==2.0.2+cu118` (`Multi_change/requirement.txt`). |
| CUDA | **11.8** (explicit `+cu118`). |
| Key deps | `Multi_change`: `mmcv==1.3.1`, `mmengine==0.9.1`, `mmsegmentation==0.13.0`, `transformers==4.33.1`, `numpy==1.25.2`, `opencv-python==4.8.0.74`, `openai==1.3.4`, `pandas==2.1.2`. `lagent-main`: `streamlit`, `tiktoken`, `lmdeploy>=0.2.3`, `vllm>=0.3.3`, `transformers>=4.34`. |
| Checkpoints | Not downloaded. `MCI_model.pth` from HF `lcybuaa/Change-Agent`; place in `./models_ckpt/`. May also require a SegFormer backbone. |
| Datasets | LEVIR-MCI (HF `lcybuaa/LEVIR-MCI`) — **not downloaded**. |
| Input format | Bi-temporal RGB image pair (LEVIR-MCI style, 256×256, building/road change). Agent layer additionally takes a natural-language instruction. |
| Output format | Multi-class change masks (building / road) + change-caption text. The agent composes these via tool calls and needs an LLM (OpenAI API key via `openai==1.3.4`). |
| Inference command | `python Multi_change/test.py --data_folder <LEVIR-MCI/images> --checkpoint <MCI_model.pth>`. Interactive: edit the checkpoint in `Multi_change/predict.py` (`Change_Perception.define_args()`), then `python Multi_change/try_chat.py` or `python Multi_change/web_demo.py` (Streamlit). |
| SatQuery role | Bi-temporal change detection + captioning; a reference for agentic tool orchestration. |
| Notes | **Internal dependency conflict**: `Multi_change` pins `transformers==4.33.1`, `lagent` requires `>=4.34`. The OpenMMLab stack (`mmcv==1.3.1` + `mmsegmentation==0.13.0` from the mmcv-1.x era, mixed with `mmengine==0.9.1` from the 2.x era) is inconsistent and `mmcv==1.3.1` has no wheels for torch 2.0 — expect a source build. Largest clone (~467 MB). |
| **Runtime (G1)** | **BLOCKED** (deps). `pip install mmcv==1.3.1` **fails at build** on Windows (`No module named 'pkg_resources'` in the isolated build env; 2021-era setup.py) and would need CUDA toolkit + MSVC for ops even past that — no prebuilt wheels for any current Python/torch. Not run; `MCI_model.pth` + LEVIR-MCI not downloaded. Integration cost **HIGH** — Linux + conda + `mmcv` source build (or port to modern mmcv). → **TEST FURTHER** (compare vs ChangeFormer in EXP-003). See `runtime_validation.md`. |

---

## 4. ChangeChat — `external/research/ChangeChat`

| Field | Value |
|-------|-------|
| Upstream | github.com/hanlinwu/ChangeChat |
| Commit | `9facf50c68efa32f446f0f3aa700c0b76309029e` (2025-06-16) |
| README | Yes (`readme.md`). Instruction-tuned LVLM for bi-temporal change (change captioning, change QA, change grounding). **Code is a GeoChat fork** — `pyproject.toml` is GeoChat's with the name swapped; `geochat_demo.py` and `scripts/` are carried over; homepage URL still points to GeoChat. |
| License | **No `LICENSE` file.** `pyproject.toml` classifier says "Apache Software License". Upstream is GeoChat-derived (also Apache, unconfirmed). Treat as **Apache-2.0, unconfirmed**. |
| Python | `conda create -n changechat python=3.9` (README). |
| PyTorch | Badge: "PyTorch 2.0+". `pyproject.toml` (from GeoChat): `torch==2.0.1`, `torchvision==0.15.2`. |
| CUDA | "CUDA 11.7+" (README). |
| Key deps | README says `pip install -r requirements.txt` but **`requirements.txt` is absent at this commit**. Effective deps = `pyproject.toml` (GeoChat set): `transformers==4.31.0`, `peft==0.4.0`, `deepspeed==0.9.5`, `bitsandbytes==0.41.0`, `gradio==3.35.2`, `timm==0.6.13`. |
| Checkpoints | **"coming soon" — not released.** Repo has empty `hf-models/` and `load/` dirs. Would layer a LoRA over a LLaVA/GeoChat base. |
| Input format | Bi-temporal RS image pair + a natural-language instruction / question. |
| Output format | Text (instruction response); change-grounding responses include boxes in text. |
| Inference command | `python geochat_demo.py --model-path <changechat-weights>` (inherited from GeoChat); `test.ipynb`. |
| SatQuery role | Bi-temporal change conversation specialist. |
| Notes | **Not runnable yet**: no released weights, missing `requirements.txt`. Same Linux/CUDA-only concerns as GeoChat (`bitsandbytes`, `deepspeed`, `gradio<3.36`/`pydantic<2`). Second-largest clone (~347 MB), mostly `GPT-api/` and `images/`. |
| **Runtime (G1)** | **BLOCKED** — nothing to run. No released weights ("coming soon"); no `requirements.txt` at the pinned commit. Integration cost cannot be assessed. → **REJECT for now**; revisit only on a weights + dependency release. See `runtime_validation.md`. |

---

## 5. ChangeFormer — `external/research/ChangeFormer`

| Field | Value |
|-------|-------|
| Upstream | github.com/wgcban/ChangeFormer (IGARSS 2022) |
| Commit | `afd1b7ed640aa265a2c730de958416ae7356a2f9` (2024-01-31) |
| README | Yes. Transformer siamese network for binary change detection. |
| License | MIT (`LICENSE`). |
| Python | **3.8.0** (README, explicit). |
| PyTorch | **1.10.1**, `torchvision 0.11.2` (README + `requirements.txt`). |
| CUDA | **10.2** (`requirements.txt` is a conda explicit spec: `cudatoolkit=10.2.89`, `pytorch=1.10.1=py3.8_cuda10.2_cudnn7.6.5_0`). CPU supported via `--gpu_ids -1`. |
| Key deps | `timm=0.4.12`, `einops=0.3.2`, `numpy=1.21.2`, `matplotlib=3.4.3`, `scipy`, `tqdm` (conda spec, linux-64). |
| Checkpoints | Not downloaded. ChangeFormerV6 pretrained for **LEVIR-CD** and **DSIFN-CD** from GitHub Releases `v0.1.0` (zip). Training also needs SegFormer MiT-b2 backbone `segformer.b2.512x512.ade.160k.pth`. Place under `checkpoints/ChangeFormer_LEVIR/` etc. (`best_ckpt.pt`). |
| Input format | Bi-temporal RGB pair, 3-band, 256×256 (LEVIR-CD) or 512×512 (DSIFN). Folder layout `A/`, `B/`, `list/` (+ `label/` for eval). Samples in `samples_LEVIR/`. |
| Output format | Binary change mask (`n_class=2`), predictions saved as PNG to `--output_folder`. |
| Inference command | `python demo_LEVIR.py --checkpoint_root <root> --checkpoint_name best_ckpt.pt --data_name quick_start_LEVIR --split demo --output_folder samples_LEVIR/predict_CD_ChangeFormerV6`. Also `demo_DSIFN.py`. Eval: `sh scripts/eval_ChangeFormer_LEVIR.sh` → `eval_cd.py`. Train: `sh scripts/run_ChangeFormer_LEVIR.sh` → `main_cd.py`. |
| SatQuery role | Bi-temporal **mask** backend (precise, language-free) feeding fusion/verification. |
| Notes | **CUDA 10.2 + cuDNN 7.6.5 does not support Ampere or newer GPUs** (RTX 30xx/40xx, A100/H100). To run on modern hardware, rebuild the env against a newer PyTorch (1.12+/2.x on cu113+) — the model code is simple enough that this usually works — or run CPU-only for the demo. The `requirements.txt` is a linux-64 conda lockfile and will not resolve on Windows/macOS as-is. |
| **Runtime (G1)** | **RUNNING** (no source edits — env pins only). `.venvs/changeformer`: **torch 2.5.1+cpu** (torch ≥2.6 breaks its `torch.load`), **numpy 1.23.5** (`datasets/CD_dataset.py` uses removed `np.str`), + `opencv-python-headless`, `tifffile`, `scikit-image 0.21`, `scipy 1.10`, `timm`, `einops`. `demo_LEVIR.py --gpu_ids -1` → exit 0, 7 masks. Bundled-label score: **change-IoU 0.832 / F1 0.908 (n=7, reproduction)**. Author record: `Historical_best_acc=0.9495` on LEVIR-CD (their number). 41 M params, ~790 ms/256² pair (CPU), RSS ~1.0 GB. Integration cost **LOW–MEDIUM**. See `runtime_validation.md`. |

---

## 6. RemoteCLIP — `external/research/RemoteCLIP`

| Field | Value |
|-------|-------|
| Upstream | github.com/ChenDelong1999/RemoteCLIP (IEEE TGRS 2024) |
| Commit | `a6a4787507e441f444c20404c90dd18520a8960d` (2024-06-27) |
| README | Yes. CLIP fine-tuned for remote sensing; retrieval, zero-shot classification, embeddings. Weights converted to OpenCLIP format. |
| License | **Apache-2.0** (`LICENSE`). |
| Python | Not pinned. Colab/Jupyter demo; works on modern 3.8–3.11. |
| PyTorch | Not pinned. Provided through `open-clip-torch`; `import torch, open_clip`. |
| CUDA | Not required. Demo calls `.cuda()` but image/text encoding runs on CPU. |
| Key deps | `open-clip-torch`, `huggingface_hub` (for `hf_hub_download`), `torch`, `Pillow`. Retrieval eval adds `clip_benchmark`. |
| Checkpoints | Not downloaded. `RemoteCLIP-RN50.pt`, `RemoteCLIP-ViT-B-32.pt`, `RemoteCLIP-ViT-L-14.pt` from HF `chendelong/RemoteCLIP` via `huggingface_hub.hf_hub_download("chendelong/RemoteCLIP", "RemoteCLIP-{name}.pt", cache_dir="checkpoints")`. |
| Input format | One RGB image (OpenCLIP preprocess for the chosen backbone) + text (class names / captions via `open_clip.get_tokenizer`). |
| Output format | L2-normalized image and text embeddings; cosine similarity → zero-shot logits or retrieval ranking. |
| Inference command | `demo.ipynb` / `RemoteCLIP_colab_demo.ipynb`; or `model, _, preprocess = open_clip.create_model_and_transforms("ViT-L-14"); model.load_state_dict(torch.load("RemoteCLIP-ViT-L-14.pt")); model.encode_image(...) / model.encode_text(...)`. Retrieval eval: `python retrieval.py --model-name ViT-L-14 --retrieval-json-dir <..> --retrieval-images-dir <..>`. |
| SatQuery role | Scene retrieval, zero-shot tagging, and embedding index. |
| Notes | Cleanest integration of the six: pure pip, permissive license, small clone (~5 MB), CPU-capable, no exotic pins. |
| **Runtime (G1)** | **RUNNING.** `.venvs/remoteclip` (open-clip-torch 3.3.0, torch 2.13.0+cpu). Checkpoint `RemoteCLIP-ViT-B-32.pt` (605 MB) loads all-keys-matched. Official example on `assets/airport.jpg` → 97.78 % "An airport". 151 M params, ~150 ms/query (CPU, warm), RSS ~1.6 GB. Integration cost **LOW**. See `runtime_validation.md`. |

---

## 7. EarthDial — **not cloned** (PRIMARY HIGH-CAPABILITY REFERENCE, REFERENCE CANDIDATE)

> Added to the inventory as a **reference** by ADR-012. **The repo is NOT cloned
> into `external/research/`** (no new repositories added this pass) — the fields
> below are from the public README + Hugging Face pages, 2026-09-01, **no large
> artifacts downloaded**. Classification: **REFERENCE CANDIDATE until reproduced.**

| Field | Value (verified 2026-09-01) |
|-------|-----------------------------|
| Upstream | github.com/hiyamdebary/EarthDial (CVPR 2025). 45 commits, 140 stars. |
| README | Yes. Conversational multimodal RS assistant; "image input together with a user query … natural language responses interleaved with corresponding object locations". Claims classification / detection / captioning / QA / reasoning / **grounding** / **change detection**, over RGB / **SAR** / NIR / multispectral, **single and multi-temporal**. Capability list is **DOCUMENTED (README), not verified by us.** |
| License | Repo footer: **MIT**. HF checkpoint pages (`akshaydudhane/EarthDial_4B_*`): **no license stated** ("No model card"). → **code MIT; weights licence UNCONFIRMED.** |
| Architecture / params | `internvl_chat` (InternVL2 vision encoder + **Phi-3-Mini** LLM). HF: **"4B params"**, tensor type **BF16**. |
| Checkpoints | **Verified to exist** — HF `akshaydudhane/EarthDial_4B_RGB`, `_MS`, `_Methane_UHI` (Safetensors). File list / total size not shown on the card page. Download example in README: `snapshot_download(repo_id="akshaydudhane/EarthDial_4B_RGB", …)`. **Not downloaded.** |
| Python / PyTorch / CUDA | README: `python=3.9`; `flash-attn==2.3.6` for **training**. **PyTorch / CUDA / `transformers` versions not pinned** in the visible README. |
| Hardware | README: trained on **8× A100 80 GB**. **Inference VRAM not documented.** 4B BF16 ≈ **8–9 GB** → does **not** fit the 4 GB laptop at bf16; 4-bit ≈ 3–3.5 GB (**undocumented, unverified**). → remote box. |
| Inference command | README: "check demo section for instructions on how to run the earthdial demo". **Exact entrypoint / script not quoted in the README excerpt; not run by us.** |
| Input / Output | Input: image(s) (RGB / SAR / NIR / MS; single or temporal) + text query. Output: natural-language text **interleaved with object locations** (grounding coords). |
| Quantization | **Not mentioned.** |
| SatQuery role | **PRIMARY HIGH-CAPABILITY REFERENCE** — the model to reproduce on a remote GPU for the local-vs-reference A/B comparison and (natively) the C/D-language arms. Replaces the earlier "GeoChat = ceiling" framing. **Not a "ceiling" until reproduced + measured. Not required by the core SatQuery architecture.** |
| Runtime status | **REFERENCE CANDIDATE** — not reproduced. Blocked locally on size (4B) + this host's multi-GB download failures; unblocked by a remote Linux GPU ≥ 16 GB. |

---

## Cross-repo summary

| Repo | License | Python | PyTorch | CUDA | Weights available? | CPU-capable? | G1 runtime |
|------|---------|--------|---------|------|--------------------|--------------|------------|
| awesome-rs-vlms | MIT | – | – | – | – | – | n/a (link list) |
| GeoChat | Apache-2.0¹ | 3.10 | 2.0.1 | 11.7/11.8 | Yes (LoRA + base) | Inference yes²; no 4/8-bit on Windows | **BLOCKED** (7B > 4 GB; deepspeed/bnb) — SECONDARY / HISTORICAL REFERENCE, **not a blocker** |
| EarthDial (not cloned) | code MIT / weights unconfirmed | 3.9 | not pinned | not pinned | Yes (`akshaydudhane/EarthDial_4B_*`, 4B BF16) | Not attempted (4B ≈ 8–9 GB bf16) | **REFERENCE CANDIDATE** — PRIMARY HIGH-CAPABILITY REFERENCE (remote) |
| Change-Agent | MIT | 3.9 | 2.0.1+cu118 | 11.8 | Yes (`MCI_model.pth`) | Model yes; agent needs LLM API | **BLOCKED** (mmcv 1.3.1 build) |
| ChangeChat | Apache-2.0¹ | 3.9 | 2.0.1 | 11.7+ | **No (coming soon)** | n/a yet | **BLOCKED** (no weights) |
| ChangeFormer | MIT | 3.8 | 1.10.1 | **10.2** | Yes (Releases v0.1.0) | Yes (`--gpu_ids -1`) | **RUNNING** (torch<2.6, numpy<1.24) |
| RemoteCLIP | Apache-2.0 | flexible | via open-clip | optional | Yes (HF) | Yes | **RUNNING** |

¹ Declared in package metadata; no `LICENSE` file in the repo — confirm before redistribution.
² Full-precision inference needs enough VRAM for a 7B model (~16 GB) or CPU offload.

See `docs/research/repository_compatibility.md` for the conflict analysis and
`docs/research/environment_strategy.md` for per-model isolation.
