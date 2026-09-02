# Local Lightweight Model Replacement Tournament

> **Goal:** the compact stack that runs the mandatory SatQuery capabilities
> **entirely on the ASUS Zephyrus G14 / RTX 3050 Ti / 4 GB VRAM (+ CPU fallback)**,
> with the heavy VLMs (EarthDial, GeoChat, GeoGround) demoted to research-only.
> Optimise **capability per GB of VRAM**, not model size. Use existing GitHub
> implementations; do not build a VLM.
>
> Date: **2026-09-01**. Companions: `LIGHTWEIGHT_AUDIT.md` (the prior 5-candidate
> audit), `MODEL_TOURNAMENT.md`, `CAPABILITY_GAP_MATRIX.md`, `EVIDENCE_LEDGER.md`.
> **Every capability claim below is from the current official GitHub/HF README —
> not inferred from a paper title.** Nothing here is promoted to production from
> documentation alone (`DOCUMENTED → REPRODUCED → MEASURED → INTEGRATED → VALIDATED`).

## 4 GB hardware classes

`LOCAL-EASY` · `LOCAL-FITS-4GB` · `LOCAL-BORDERLINE` · `CPU-FALLBACK` ·
`REMOTE-ONLY` · `REJECT`. "Fits" is necessary, not sufficient — quality, latency,
reliability and integration cost all count.

---

## Research audit — the three NEW candidates

### 1. RS-MoE — `github.com/CongcongWen1208/RS-MoE`

| Field | Value (README + HF, 2026-09-01) |
|-------|--------------------------------|
| Paper | "RS-MoE: A Vision-Language Model with Mixture of Experts for RS Image Captioning and VQA" (IEEE TGRS 2025) |
| **Classification** | **GENERAL VLM (claimed)** — captioning + RSVQA; **no grounding** |
| Base model | **Vicuna-13B + LoRA** (README "implementation guide"); a "RS-MoE-1B variant" is **claimed** ("comparable to 13B VLMs") — no artifact |
| Released checkpoint | **None.** No HF IDs, no sizes, no download. |
| Released inference code | **No.** README: *"training-focused… The MoE architecture is not yet implemented in these files."* |
| License (code / weights) | **Not stated.** |
| Python / PyTorch / CUDA | Not documented. |
| Quantisation / GPU memory | Not documented. |
| Repo health | **6 commits, 8 stars**, incomplete implementation. |
| 4 GB class | **REJECT** — nothing to run; the "1B" model is a paper claim, not a release. Base is a 13B VLM. |
| Decision | **REJECT (no artifacts).** Same outcome as the earlier RS-MoE repo (G1.6). Revisit only on a real 1B checkpoint + inference code + license. |

### 2. DynamicVis — `github.com/KyanChen/DynamicVis`

| Field | Value |
|-------|-------|
| Paper | "DynamicVis: An Efficient and General Visual Foundation Model for RS Image Understanding" (arXiv 2503.16426, 2025) |
| **Classification** | **PERCEPTION / ENCODER** (Dynamic Region-Aware **State Space Model / Mamba** backbone). **NOT a VLM.** README: *"Does not support VQA, captioning, or grounding based on released code."* |
| Released tasks | scene classification, tiny object detection, instance + semantic segmentation, **change detection (LEVIR-CD / WHU-CD / OSCD)**, image retrieval |
| Checkpoints | HF `KyanChen/DynamicVis` — base ("b") + large ("l"); param counts / sizes not in README (configs in `configs_DynamicVis/fMoW`). Pretrain weights uploaded 2025-04; fine-tuned weights not clearly released. |
| License | **Apache-2.0** (code). |
| **GPU memory** | **~800–833 MB for a 2048×2048 image, ~97 ms latency** (~3 % of a base ViT) — genuinely efficient. |
| Python / PyTorch / CUDA | 3.10+, 2.0+ (2.4 rec), 11.7+ (12.1 rec). |
| **Windows** | **"Not supported for Mamba."** | 
| **CPU** | **Not supported** (Mamba kernels are CUDA-only). |
| Repo health | 86 stars, active to 2025-03-31, 4 open issues. |
| 4 GB class | `LOCAL-EASY` **on VRAM** — but **REJECT for the product**: Mamba is **Windows- and CPU-incompatible**, which breaks the "runs on the ASUS machine today + CPU fallback" requirement. |
| Decision | **REJECT for product** (portability-disqualified). **Watch-item** for a future Linux/GPU deployment of change detection — but it must beat ChangeFormer *measurably*, and ChangeFormer already runs on CPU. No measurable SatQuery role it doesn't lose on portability. |

### 3. RemoteSAM — `github.com/1e12Leon/RemoteSAM`

| Field | Value |
|-------|-------|
| Paper | "RemoteSAM: Towards Segment Anything for Earth Observation" (arXiv 2505.18022, **ACM MM 2025**) |
| **Classification** | **GROUNDING / SEGMENTATION MODEL** — unifies tasks through **Referring Expression Segmentation**. **NOT a conversational VLM.** |
| Backbone | **Swin-Base (vision) + BERT (text)** — "order-of-magnitude smaller parameter count (billions → millions)" → ≈ **200 M** (Swin-B ≈ 88 M + BERT-base ≈ 110 M). |
| Released tasks | **referring segmentation (text → mask)**, **visual grounding (text → box)**, semantic segmentation, object detection, multi-label + image classification, image captioning, object counting |
| Checkpoint | HF `1e12Leon/RemoteSAM` (released May 2025) + dataset **RemoteSAM-270K** (270 k image-text-mask triplets). Size not stated — but a Swin-B+BERT model is ≈ 0.4–0.8 GB, **in the range that has downloaded successfully before** (ChangeFormer 492 MB, RemoteCLIP 605 MB). |
| Input / Output | **image + sentence** → **mask** (RES) or **box** (grounding); image + classnames → labels |
| License | **Not stated** in the README ("open-sourced"). **Must be confirmed** before any product use. |
| Python / PyTorch / CUDA | **3.8 / 1.13.0 / 11.6**; **`mmcv-full==1.7.1`** ⚠️ |
| Windows / CPU / quant | Not documented. **`mmcv-full==1.7.1` is the risk** — same dependency class that blocked Change-Agent on Windows (needs a compiler + CUDA toolkit; Linux wheels exist for torch 1.13/cu116). |
| Repo health | **247 stars, 15 commits, last update 2025-07** (ACM MM acceptance). |
| 4 GB class | **`LOCAL-FITS-4GB`** on size (~200 M) — **but env-`BLOCKED`**: `mmcv-full 1.7.1` build on this Windows host is the wall. |
| Decision | **KEEP — REPRODUCED + INTEGRATED (G10, ADR-019).** Runs on the ASUS **CPU** via `.venvs/remotesam` — the grounding inference path needs only **`mmcv` (lite) 1.7.1** (no compiled ops; the `mmcv-full` assumption above was wrong). Checkpoint `RemoteSAMv1.pth` **2.57 GB** (not sub-GB) downloaded. Smoke: 3/5 phrases → in-bounds box+mask, prob ≈ 0.97–1.0. `RemoteSamAdapter` + `/analyze` `SINGLE_IMAGE_GROUNDING` route live. **Open:** DIOR-RSVG acc@IoU0.5 (dataset blocked), GPU/4 GB-VRAM check (CPU-only here, ~8 GB RSS → `CPU-FALLBACK`), and an upstream **licence** (NOT STATED). Full record: `EXP-GROUNDING.md`. |

---

## Tournament results

### Tournament A — VQA  *(RS-MoE-1B / RSCoVLM-3B / TinyRS-2B / Qwen2-VL-2B)*

**No new lightweight VQA winner.** RS-MoE-1B **does not exist as a runnable
artifact** (training-only repo, no weights, no licence). The field is unchanged
from `LIGHTWEIGHT_AUDIT.md`:

| Candidate | Class | Params | 4 GB class | State |
|-----------|-------|:------:|-----------|-------|
| **RSCoVLM-3B** | GENERAL VLM (RS multi-task) | 3 B | `LOCAL-BORDERLINE` (4-bit ~3 GB) | **DOCUMENTED** — download BLOCKED |
| **TinyRS-2B** | GENERAL VLM (RS) | 2 B | `LOCAL-FITS-4GB` (4-bit ~1.8 GB) | **DOCUMENTED** — download BLOCKED (6×) |
| **Qwen2-VL-2B** | GENERAL VLM (generic) | 2 B | `LOCAL-FITS-4GB` (4-bit) | **DOCUMENTED** — control; download BLOCKED |
| RS-MoE-1B | — (claim) | — | `REJECT` | no artifact |

**Best local VQA model (evidence-based): still unresolved.** Primary =
**RSCoVLM-3B**, fallback = **TinyRS-2B**, control = **Qwen2-VL-2B**. All BLOCKED on
artifact acquisition (needs a better-connected machine). No 1B RS-VQA model with a
real release exists in the inspected set.

### Tournament B — Grounding  *(RemoteSAM / RSCoVLM / TinyRS / Qwen2-VL / GeoGround ref)*

**RemoteSAM WON capability B — REPRODUCED + INTEGRATED (G10, ADR-019).**

| Candidate | Class | Grounding output | Params | 4 GB class | State |
|-----------|-------|------------------|:------:|-----------|-------|
| **RemoteSAM** | GROUNDING / SEGMENTATION | **mask + box** from a phrase | ~200 M | **`CPU-FALLBACK` verified** (~8 GB RSS; GPU/4 GB unverified) | **REPRODUCED + INTEGRATED** (not benchmarked) |
| RSCoVLM-3B | GENERAL VLM | box-in-text | 3 B | `LOCAL-BORDERLINE` | DOCUMENTED |
| TinyRS-2B | GENERAL VLM | box-in-text | 2 B | `LOCAL-FITS-4GB` | DOCUMENTED |
| Qwen2-VL-2B | GENERAL VLM | native `<box>` tokens | 2 B | `LOCAL-FITS-4GB` | DOCUMENTED (generic control) |
| GeoGround | GENERAL VLM (grounding) | box / mask | ~7 B | `REMOTE-ONLY` | reference |

**Best local grounding model: RemoteSAM — REPRODUCED + INTEGRATED (G10, ADR-019).**
A dedicated ~200 M specialist that returns a **mask *and* a box** (both directly
mappable as evidence), rather than making a 3 B VQA model emit coordinates in
text. **Grounding is now a specialist, not a VQA side-task.** Runs on the ASUS
CPU (`.venvs/remotesam`, `mmcv` **lite** — no compiled ops on the inference
path). Fallback = RSCoVLM-3B grounding head. Reference = GeoGround (remote).
**Not benchmarked** (DIOR-RSVG blocked); GPU/4 GB fit unverified; **licence NOT
STATED** upstream. `EXP-GROUNDING.md`.

### Tournament C — Efficient perception  *(DynamicVis)*

**DynamicVis has no useful SatQuery product role.** It is an encoder (no A/B),
its only overlap with a mandatory capability is **C (change detection)** which
**ChangeFormer already covers and runs on CPU**, and DynamicVis is **Windows- and
CPU-incompatible** (Mamba/CUDA-only) — disqualifying for the stated target. Its
800 MB / 2048² efficiency is real but buys nothing SatQuery needs today.
**REJECT for product; research watch-item only.**

### Tournament D — Optical-SAR  *(CROMA vs DOFA)*

**Unchanged.** Both REPRODUCED (CPU, MIT, sub-GB). No candidate in this audit
touches D. Decision stays with EXP-004 Run 2 (dataset-blocked). Do not replace.

### Tournament E — Temporal  *(ChangeFormer)*

**Unchanged.** ChangeFormer stays the C-mask baseline (INTEGRATED + MEASURED, IoU
0.83, CPU-capable). No candidate here provides a measured improvement at
acceptable cost (DynamicVis is CUDA-only; RS-MoE has no artifact).

### Adaptation (E)

Route unchanged: **frozen CROMA/DOFA encoder + linear probe → LoRA** on a DFC2020
subset (EXP-008). None of the new candidates changes this — RS-MoE has no encoder
to probe, DynamicVis can't run here, RemoteSAM's Swin-B could in principle be
probed but that is a *new* research thread with no current need.

---

## Model composition (hypothesis → evidence)

| Capability | PRIMARY | FALLBACK | REFERENCE (research-only) |
|------------|---------|----------|---------------------------|
| **A — VQA** | RSCoVLM-3B *(DOCUMENTED, blocked)* | TinyRS-2B *(blocked)* | GeoChat-7B / EarthDial-4B |
| **B — grounding** | **RemoteSAM** *(DOCUMENTED, TEST FURTHER)* | RSCoVLM-3B grounding | GeoGround-7B |
| **C — change mask** | **ChangeFormer** *(INTEGRATED + MEASURED)* | image-difference fallback *(INTEGRATED)* | — |
| **C — change language** | composed baseline (ChangeFormer→crop→RemoteCLIP) *(experimental)* | — | EarthDial-4B / TEOChat |
| **D — optical-SAR** | CROMA *(REPRODUCED)* | DOFA *(REPRODUCED)* | — |
| **retrieval / prior** | **RemoteCLIP** *(INTEGRATED)* | — | — |

**No bloat:** one production specialist per capability (+ one fallback + one
reference). This audit adds **exactly one** new candidate to the *evaluation*
queue — RemoteSAM for B — and rejects the other two.

---

## Final decision

1. **Best local VQA model** — *unresolved.* RSCoVLM-3B (primary) / TinyRS-2B
   (fallback) / Qwen2-VL-2B (control); all DOCUMENTED, all download-BLOCKED. **No
   1 B RS-VQA model with a real release exists** in the inspected set (RS-MoE-1B
   is a paper claim).
2. **Best local grounding model** — **RemoteSAM** (≈200 M, mask + box, RS-native,
   ACM MM 2025). TEST FURTHER; reproduction blocked on the `mmcv-full==1.7.1` env
   and an unstated licence. This is the audit's one real gain: **B can be a
   dedicated lightweight specialist, not a 3 B VLM side-task.**
3. **DynamicVis role** — **none for the product.** Encoder-only (no A/B),
   Windows/CPU-incompatible; C is already covered by a CPU-capable model.
   Research watch-item only.
4. **Recommended local A/B stack** — **A:** RSCoVLM-3B @ 4-bit (primary) /
   TinyRS-2B (fallback) / Qwen2-VL-2B (control). **B:** **RemoteSAM** (primary,
   dedicated grounding specialist) / RSCoVLM-3B grounding (fallback). Every arm
   still needs a first REPRODUCTION.
5. **Recommended local C stack** — **ChangeFormer** (mask, INTEGRATED + MEASURED)
   + `image_difference_fallback` (INTEGRATED) + the composed semantic-change
   baseline (experimental). Unchanged.
6. **Recommended local D stack** — **CROMA** primary / **DOFA** challenger, both
   REPRODUCED on CPU; decision deferred to EXP-004 Run 2. Unchanged.
7. **Recommended adaptation route** — frozen CROMA/DOFA + linear probe → LoRA on a
   DFC2020 subset (EXP-008). Unchanged.
8. **Can the product run entirely on 4 GB today?** — **C + D + retrieval: YES,
   proven** (ChangeFormer, CROMA, DOFA, RemoteCLIP all CPU-capable / sub-GB /
   reproduced). **A + B: not yet proven** — plausibly 4 GB-feasible
   (RSCoVLM-3B @ 4-bit ≈ 3 GB; RemoteSAM ≈ <1 GB) but **neither is reproduced**;
   both blocked on artifact/env acquisition, not on capability or compute.
9. **Heavy models removable from the product architecture** — **EarthDial,
   GeoChat, GeoGround** (and TEOChat, LRS-VQA, UniRS). They are already
   `excluded:` in `model_registry.yaml`; this audit **confirms** the product has
   **no** mandatory 7B/16 GB dependency. They stay as **optional research
   references**.
10. **Research-only** — EarthDial-4B, GeoChat-7B, GeoGround-7B, TEOChat, LRS-VQA,
    UniRS, **DynamicVis** (CUDA/Windows), **RS-MoE** (no artifact).
11. **Exact next experiment** — **on a machine that can build `mmcv-full==1.7.1`
    (Linux, or a matching Windows wheel): reproduce RemoteSAM** — load the HF
    checkpoint, run its referring-segmentation + visual-grounding examples on 3–5
    RS images, confirm mask + box output, record VRAM / latency / licence. Then
    MEASURE grounding acc@IoU0.5 on the frozen 25-expression DIOR-RSVG sample
    (`evaluation/datasets/dior_rsvg_sample.json`) — the same sample the VQA
    candidates use — so B has one comparable number. This is smaller and more
    likely to succeed than the 3 B VLM downloads (weights ≈ sub-GB), and it
    resolves B independently of the blocked VQA models.
