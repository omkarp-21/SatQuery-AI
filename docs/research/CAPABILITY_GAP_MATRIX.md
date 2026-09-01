# Capability Gap Matrix (G1.5)

> Maps every **mandatory** SIH PS 26167 capability to: the model/tool we have now,
> its evidence status, what is still missing, a candidate solution, a validation
> plan, and the risk. Plus candidate scouting for the three biggest gaps, the
> minimum infrastructure decision, and the single highest-value next experiment.
> Date: **2026-09-01** (refreshed after **G4** — unified `/analyze`, composed
> semantic-change baseline, EXP-007 15/15; EXP-002/004-Run2/008 **BLOCKED** on
> data acquisition → **remote GPU box justified**). Experiment write-ups:
> `EXP-002.md`, `EXP-004.md`, `EXP-007.md`, `EXP-008.md`, `CONFIDENCE_PLAN.md`.
> Companions: `runtime_validation.md`, `model_inventory.md`,
> `docs/19_EXPERIMENT_REGISTRY.md`, `chatgpt.context.md` §4.
>
> **Nothing here adds a model to the final stack.** Candidates are for evaluation
> only (`docs/18` model-selection; `chatgpt.context.md` §28).

## Evidence-status vocabulary (used throughout)

| Level | Meaning |
|-------|---------|
| **DOCUMENTED** | The repo/paper claims the capability. We have not run it. (≈ number #1) |
| **REPRODUCED** | We ran the official example and it produced a sane result on ≥1 input. (start of #2) |
| **MEASURED** | We scored it against reference data with a recorded metric/dataset/split/hardware. (#2 or #3) |
| **INTEGRATED** | It runs *inside* the SatQuery pipeline through an adapter, with provenance. (#3) |

Current tally: RemoteCLIP = REPRODUCED (+ one MEASURED latency); ChangeFormer =
MEASURED (IoU 0.83 / n=7); everything else = DOCUMENTED or DESIGNED-only.
**INTEGRATED count = 0.**

---

## The matrix

### A. Single-image VQA  *(mandatory)*

| | |
|---|---|
| **Current model/tool** | *(role labels — ADR-011/012)* **LOCAL A/B PRIMARY = RSCoVLM-3B**; **FALLBACK = TinyRS-2B**; **GENERIC CONTROL = Qwen2-VL-2B**. High-capability references: **EarthDial** (primary, REFERENCE CANDIDATE) + **GeoChat** (secondary / historical). |
| **Evidence status** | **DOCUMENTED only.** No single-image VLM reproduced. RSCoVLM-3B / TinyRS-2B not yet run (TinyRS weight DL **BLOCKED** from this host, 5 attempts). GeoChat GPU-blocked (7B; `deepspeed`/`bitsandbytes` unbuildable on Windows) — **not a project blocker**. EarthDial = REFERENCE CANDIDATE (checkpoints verified to exist; 4B, not reproduced). |
| **Missing capability** | A VQA model **reproduced** on available hardware and MEASURED against the EXP-002 threshold. |
| **Candidate solution** | **RSCoVLM-3B** (`VisionXLab/RSCoVLM`, code MIT / data CC-BY-4.0, HF `Qingyun/rscovlm`, RS multi-task) at 4-bit on the RTX 3050 Ti; **TinyRS-2B** (`aybora/TinyRS`, Apache-2.0) as fallback; **Qwen2-VL-2B** (`Qwen/Qwen2-VL-2B-Instruct`, Apache-2.0) as the generic control. **EarthDial** (`akshaydudhane/EarthDial_4B_*`, InternVL2+Phi-3, code MIT) + **GeoChat** reproduced on a cloud GPU ≥16 GB for the reference comparison. |
| **Validation plan** | `.venvs/rscovlm` (transformers matching Qwen2.5-VL + `qwen-vl-utils`; **no** deepspeed/flash-attn for inference). Run RSCoVLM-3B on a small RSVQA-LR + DIOR-RSVG sample → REPRODUCED → MEASURE balanced acc / acc@IoU0.5 / latency vs the EXP-002 threshold. Repeat for TinyRS-2B + Qwen2-VL-2B. Compare vs EarthDial + GeoChat on a remote box afterwards. |
| **Risk** | All quality figures are the authors' (#1). RSCoVLM-3B / TinyRS-2B 4-bit on 4 GB is tight; CPU inference is slow (~seconds/answer). EarthDial weights licence **unconfirmed**; EarthDial inference path not verified. RSVQA / DIOR-RSVG overlap with each model's instruction data must be checked (leakage). |

### B. Additional single-image task — captioning OR text-guided grounding  *(mandatory: at least one)*

| | |
|---|---|
| **Current model/tool** | RemoteCLIP (zero-shot scene tagging / retrieval) — **REPRODUCED**. GeoChat (region grounding) — DOCUMENTED, blocked. |
| **Evidence status** | **PARTIAL.** Scene-level description via RemoteCLIP retrieval works today; true **text-guided region grounding** and **generative captioning** are DOCUMENTED only. RemoteCLIP retrieval is arguably not "captioning/grounding" as the PS defines them. |
| **Missing capability** | A running model that does grounding (box from a phrase) or generative captioning. |
| **Candidate solution** | **RSCoVLM-3B** (grounding is a first-class task + a detection-only checkpoint) as LOCAL A/B PRIMARY; **TinyRS-2B** fallback; **Qwen2-VL-2B** native `<\|box\|>` grounding as the GENERIC CONTROL. **GeoGround** (`VisionXLab/GeoGround`, ~7B) = **GROUNDING REFERENCE** (remote). **EarthDial** grounding = high-capability reference. Interim stopgap: RemoteCLIP retrieval + a templated description (explicitly labelled non-generative). |
| **Validation plan** | With RSCoVLM-3B running (see A), test grounding on a DIOR-RSVG sample → MEASURE acc@IoU0.5 (reproduction), same sample for TinyRS-2B + Qwen2-VL-2B. Pick captioning-vs-grounding based on which scores better and integrates cheaper. GeoGround / EarthDial on a remote box as the reference. |
| **Risk** | Box coordinate/format conventions differ per model; small-model grounding accuracy may be weak; a templated stopgap must never be presented as model captioning. |

### C. Bi-temporal semantic change — change understanding + description and/or change-VQA (optional: change map)  *(mandatory)*

| | |
|---|---|
| **Current model/tool** | **ChangeFormer** — binary change **mask** only. RUNNING + **MEASURED** (IoU 0.832 / F1 0.908, n=7 bundled LEVIR-CD). Change-Agent (semantic + caption) — dependency-blocked. |
| **Evidence status** | **Change map = MEASURED. Semantic labels + natural-language change description / change-VQA = NONE.** |
| **Missing capability** | Semantic change categories and a language description / QA over the change. |
| **Candidate solution** | (1) **TEOChat** (temporal EO VLM — building/damage/semantic change + change-QA; HF weights) — but LLaMA-derived, **non-commercial licence**, ~7B → GPU-blocked. (2) Change-Agent perception model (`MCI_model.pth`, building/road classes) once its env is solved on Linux. (3) **Cheap pipeline that runs now:** ChangeFormer mask → connected-component region crops → caption each region with TinyRS/RemoteCLIP → rule-assemble a change description. Our orchestration, no new heavy model. |
| **Validation plan** | **EXP-003:** compare (a) ChangeFormer + region-caption pipeline vs (b) TEOChat zero-shot (on a GPU box) vs (c) Change-Agent (Linux) on a LEVIR-MCI sample. Metrics: change-mask IoU, change-caption BLEU-4/CIDEr, change-QA accuracy. |
| **Risk** | The cheap pipeline gives shallow, templated descriptions; TEOChat's licence blocks any commercial/deployment claim and needs a GPU; Change-Agent env cost is HIGH. |

### D. Optical–SAR joint analysis — co-registered optical+SAR, complementary info, joint reasoning  *(mandatory)*

| | |
|---|---|
| **Current model/tool** | **CROMA** + **DOFA** — both **REPRODUCED** on CPU (G1.6, `runtime_validation.md`). RemoteCLIP / ChangeFormer / GeoChat remain optical-only. |
| **Evidence status** | **REPRODUCED** (was NONE at G1.5). CROMA produces joint SAR+optical embeddings; DOFA encodes S1 (2ch) and S2 (12ch) via one wavelength-conditioned encoder. **Not yet MEASURED** on a task. |
| **Missing capability** | A **measured** SAR-vs-no-SAR delta on a real task; a downstream head. |
| **Candidate solution** | **CROMA** (native joint radar-optical cross-encoder, MIT, 194 M, `antofuller/CROMA`) — **primary**. **DOFA** (one wavelength-conditioned encoder, MIT, 111 M, `XShadow/DOFA`) — **challenger** (fuse S1⊕S2 downstream). MaRS = watch-item (VHR ≠ Sentinel scale; release unverified). |
| **Validation plan** | **EXP-004 (still the recommended next — see below):** 3 arms — optical-only probe / CROMA `joint_GAP` probe / DOFA S1⊕S2 probe — on a **small** fixed reBEN (BigEarthNet v2) subset, held-out split, same head/budget. Metric: built-up F1 (+ 2–3 classes); report abs + rel SAR delta, where SAR helps, where it hurts. **Local.** |
| **Risk** | Sentinel-1/2 preprocessing (12-band S2, 2-band S1 in dB, channel norm, 120-px tiling for CROMA); probe capacity; SAR handled as backscatter, never RGB. Do **not** claim "SAR improves accuracy" before EXP-004 produces the number. |

### E. Remote-sensing adaptation — ≥1 visual/VL component fine-tuned/adapted on BigEarthNet or another open source  *(mandatory)*

| | |
|---|---|
| **Current model/tool** | NONE integrated — but the **encoders are now reproduced** (CROMA, DOFA), so the probe is directly executable. |
| **Evidence status** | **NONE** (plan ready and unblocked). |
| **Missing capability** | A documented adaptation with a before→after measurement. |
| **Candidate solution** | Linear-probe → LoRA on a **frozen** CROMA (or DOFA) encoder over a **reBEN / BigEarthNet v2** subset (S1+S2, 19-class multilabel, 549 k patches, Zenodo `10891137`; use ~10–50 k). Both encoders reproduced → feasible on the 4 GB laptop. Shares EXP-004's data + split. Method labels kept distinct: linear probe ≠ LoRA ≠ full fine-tune ≠ instruction tuning. |
| **Validation plan** | **EXP-E (new):** frozen encoder + linear probe vs LoRA-adapted, on a fixed reBEN subset split. Report multilabel mAP / micro-F1 **before → after** (SatQuery number #3), with seed / split / hardware / date. |
| **Risk** | Scope creep into full fine-tuning — must stay a bounded linear/LoRA probe (`.claude/rules/scope.md`). reBEN full download is large — **subset only**; record exactly which patches. |

### F. Agentic routing — interpret, inspect, select tools, configure params, execute, combine, confidence, evidence, audit summary  *(mandatory)*

| | |
|---|---|
| **Current model/tool** | Our own `packages/agents` + `agent-orchestration` skill — **DESIGNED, no code.** |
| **Evidence status** | **DESIGNED only.** |
| **Missing capability** | The deterministic planner/router implementation + a labelled routing test set. |
| **Candidate solution** | `packages/agents`: rules over `model_registry.yaml` capabilities; an LLM (API, or a small local model) **only** for intent → typed task, schema-validated. LangGraph optional and only if it simplifies DAG execution. |
| **Validation plan** | **EXP-006:** LLM-only routing vs constrained routing on a hand-labelled set of `query + input bundle → (task, modality, specialist)`. Metrics: routing accuracy, invalid-execution rate, plan reproducibility. |
| **Risk** | Only meaningful once ≥2 real adapters populate the registry (RemoteCLIP + ChangeFormer) — so this trails A/D. |

### G. Geospatial validation — CRS, transform, bounds, GSD, bands, NoData, pair compatibility, registration  *(mandatory)*

| | |
|---|---|
| **Current model/tool** | `.claude/rules/geospatial.md` + `geospatial-engineering` skill + empty `packages/geospatial`. **DESIGNED, no code.** |
| **Evidence status** | **DESIGNED only.** |
| **Missing capability** | The `metadata` + `geospatial` stage implementation (rasterio/pyproj), a co-registration assertion, and a stress-test set. |
| **Candidate solution** | Our own — rasterio, pyproj, shapely (already in `packages/geospatial` deps). No external model. |
| **Validation plan** | **EXP-007:** validation gate ON vs OFF on a stress set of deliberately mismatched pairs (different CRS / offset / GSD / missing NoData) mixed with valid pairs. Metrics: fraction of invalid pairs rejected; downstream change-metric error with vs without the gate. |
| **Risk** | Low — straightforward engineering. It is a **prerequisite** for C and D being trustworthy (misregistration → fake change; wrong CRS → wrong area). Do this early. |

### H. Evidence + confidence + audit — traceable evidence, confidence with a defined source, provenance  *(mandatory)*

| | |
|---|---|
| **Current model/tool** | `packages/evidence` + `evidence-provenance` skill — **DESIGNED, no code.** |
| **Evidence status** | **DESIGNED only.** |
| **Missing capability** | The `EvidenceItem` model, provenance-record persistence, a **defined** confidence method, and a verifier. |
| **Candidate solution** | Our own. Confidence sources (each labelled): RemoteCLIP softmax margin, ChangeFormer per-pixel probability, cross-model / optical↔SAR agreement. Verifier: independent-method cross-check + disagreement flagging. |
| **Validation plan** | **EXP-005:** verifier detection precision/recall on a curated right/wrong answer set; **confidence calibration** — reliability diagram on a labelled subset (state whether the score is a probability, a margin, or a heuristic). |
| **Risk** | Calibration needs labelled data; the confidence method must be honestly labelled, never presented as a calibrated probability unless it is one (`.claude/rules/ai-models.md`, `evidence-provenance` skill). |

---

## Gap summary (most urgent first)

| Gap | Status (post-G2) | Blocking? | Cheapest path to next evidence |
|-----|--------|-----------|--------------------------------|
| **D. Optical–SAR** | **REPRODUCED** + probe machinery validated (EXP-004 Run 1, synthetic); joint-repr contract in `/analyze` | mandatory + differentiation | **EXP-004 Run 2 BLOCKED** — no acquirable real S1+S2 set (DFC 11 GB / So2Sat 7 GB). Needs a remote box. |
| **E. RS adaptation** | NONE — harness ready | mandatory | **EXP-008 BLOCKED** on EXP-004 Run 2. Needs a remote box. |
| **A. Single-image VQA** | DOCUMENTED — **LOCAL A/B PRIMARY = RSCoVLM-3B**, FALLBACK TinyRS-2B, CONTROL Qwen2-VL-2B; references EarthDial (primary) + GeoChat (secondary) | mandatory | **EXP-002** — run RSCoVLM-3B @ 4-bit **local** first; TinyRS weight DL BLOCKED (5 attempts). Remote GPU *useful* for the EarthDial/GeoChat reference, not on the critical path. |
| **B. Extra single-image task** | PARTIAL — RemoteCLIP retrieval **integrated as `/scene`** (explicitly *not* captioning/grounding per PS) | mandatory | grounding via **RSCoVLM-3B** (primary) / TinyRS-2B (fallback) / Qwen2-VL-2B (control) — EXP-002, **local**; **GeoGround = GROUNDING REFERENCE** (remote) |
| **C. Semantic change (language)** | mask **INTEGRATED**; **`COMPOSED_SEMANTIC_CHANGE_BASELINE` built & wired into `/analyze`** (mask→components→crop-tag→rule description) — experimental, disclaimed, tags noisy on tiny crops; **learned** semantic change NONE | mandatory | improve the baseline (better crops / a captioner) + EXP-003 with a real VLM on a remote box — **EarthDial** (native temporal + change) is the PRIMARY HIGH-CAPABILITY REFERENCE to reproduce first |
| **G. Geospatial validation** | **VALIDATED at the structural level (EXP-007: 15/15)** — live in `/analyze`, `/change`, `/scene`; every invalid-pair class rejected before any model runs | mandatory + prerequisite | task-level H5 (does the gate cut downstream error?) needs EXP-004 Run 2 data |
| **H. Evidence/confidence/audit** | `EvidenceItem` + standardized `Provenance` + **deterministic `verify()` implemented & wired into both APIs**; **semantic** verification + confidence method still NONE (by design) | mandatory | add semantic checks + a documented/calibrated confidence source (EXP-005) — **local** |
| **F. Agentic routing** | **deterministic router implemented + called by `POST /analyze`** (spec + 8 tests, observable routing info in every response); LLM planner not built | mandatory | add the LLM intent-parsing step (EXP-006), schema-validated against the registry — **local** |

---

## New candidate scouting

Full record per candidate. **None is adopted** — all are for evaluation only.
Role labels: ADR-011/012. Authoritative hierarchy: `MODEL_TOURNAMENT.md`.

### 0. EarthDial  — PRIMARY HIGH-CAPABILITY REFERENCE (gaps A, B, C, D) — **REFERENCE CANDIDATE, not cloned**

| Field | Value (verified 2026-09-01 — README + HF; **no artifacts downloaded**) |
|-------|-------|
| Repo | github.com/hiyamdebary/EarthDial (CVPR 2025). 45 commits, 140 ★. **Not cloned into `external/research/`** (no new repos this pass). |
| Role | **PRIMARY HIGH-CAPABILITY REFERENCE** — replaces the retired "GeoChat = ceiling" framing. **Not** a "ceiling" until reproduced + measured. **Not required by the core SatQuery architecture.** |
| Architecture / params | `internvl_chat` — InternVL2 vision encoder + **Phi-3-Mini** LLM. HF: **"4B params"**, BF16. |
| Licence | Repo footer **MIT**; HF checkpoint pages state **no licence** → **code MIT, weights UNCONFIRMED.** |
| Checkpoints | **Verified to exist** — HF `akshaydudhane/EarthDial_4B_RGB`, `_MS`, `_Methane_UHI` (Safetensors). Not downloaded. |
| Input | RGB / **SAR** / NIR / multispectral; **single or multi-temporal**; + text query. |
| Output | Natural-language text **interleaved with object locations** (grounding coords). |
| Capabilities (README, DOCUMENTED only) | classification / detection / **captioning** / QA / reasoning / **grounding** / **change detection**. **Not verified by us — not inferred as fact.** |
| Environment | Python 3.9; InternVL2 stack; `flash-attn==2.3.6` (training). torch / CUDA / `transformers` **not pinned** in the README. |
| Hardware | Trained on **8× A100-80GB**. **Inference VRAM not documented.** 4B BF16 ≈ **8–9 GB** → no 4 GB fit; 4-bit ≈ 3–3.5 GB (**unverified**). → remote box. |
| Inference path | README points to a "demo section"; **exact entrypoint not confirmed, not run.** |
| Quantisation | **Not mentioned.** |
| Integration cost | **MEDIUM–HIGH** — InternVL runtime; 4B forces a 4-bit path we would have to validate; broadest modality coverage of any candidate (only one that natively claims SAR + temporal + grounding + captioning together). |
| Benchmark evidence | Paper: 44-dataset evaluation; README says "outperforms generic and domain-specific models" — **no numbers in the README** → **#1 DOCUMENTED**, unverified. |
| Verdict | **REFERENCE CANDIDATE** — reproduce on a remote GPU ≥ 16 GB after the local EXP-002 arms are measured; then compare local-vs-reference for A/B and use natively for the C/D-language arms. |

### 1. TinyRS / TinyRS-R1  — lightweight RS-VLM (gaps A, B)

| Field | Value |
|-------|-------|
| Repo | github.com/aybora/TinyRS |
| Paper | "TinyRS-R1: Compact Multimodal Language Model for Remote Sensing", arXiv:2505.12099 (2025); IEEE GRSL 2025 |
| License | **Apache-2.0** (repo). Base model Qwen2-VL-2B (its own licence applies to weights — check). |
| Model size | **2B** params (Qwen2-VL-2B backbone). Variants: PRETRAIN / TinyRS / TinyRS-CoT / TinyRS-R1. |
| Input | RS image + text prompt; variable resolution (≈512–1280 px on the 28-px grid). |
| Output | Text — classification, VQA, visual grounding (boxes in text), open-ended QA; CoT reasoning in R1. |
| Supported modality | Optical (RGB) single image. No SAR, no temporal. |
| Checkpoint availability | **Yes** — HuggingFace: `aybora/Qwen2-VL-TinyRS`, `…-TinyRS-CoT`, `…-TinyRS-R1`, `…-TinyRS-PRETRAIN`. |
| Environment | Python 3.10, PyTorch, `transformers`, `qwen-vl-utils`. Training needs DeepSpeed + flash-attn (**not** needed for plain inference). |
| GPU needs | Training: 4× A100/H100. **Inference: ~2 B → ≈4–5 GB fp16, ≈1.5–2 GB 4-bit** → borderline-fits the 4 GB laptop GPU; CPU works but slow. |
| Integration cost | **MEDIUM** — standard `transformers` generate loop; the main cost is a clean 4-bit/CPU inference path and prompt-format handling. |
| Benchmark evidence | Authors: base TinyRS **83.5 % VQA accuracy** (≈ GeoChat); R1 "matches or surpasses recent 7B RS models" in classification/VQA/grounding/open-QA at ⅓ memory & latency. All **#1 (authors')** — unverified by us. |

### 2. TEOChat  — temporal EO vision-language assistant (gap C)

| Field | Value |
|-------|-------|
| Repo | github.com/ermongroup/TEOChat |
| Paper | "TEOChat: A Large Vision-Language Assistant for Temporal Earth Observation Data", ICLR 2025, arXiv:2410.06234 |
| License | Apache-2.0 (code) **but non-commercial research-preview**: bound by LLaMA model licence + OpenAI-generated-data terms + ShareGPT. **Not usable for a commercial/deployed product claim.** |
| Model size | LLaVA-style, **~7B** (LLaMA-2/Vicuna-7B class) + a video/temporal projector. |
| Input | A **sequence** of EO images (bi-temporal or longer) + text. |
| Output | Text — temporal scene classification, building change & damage assessment, **semantic change detection**, change QA, spatial references. |
| Supported modality | Optical (RGB) temporal. No SAR. |
| Checkpoint availability | **Yes** — weights + data + code released (HF). |
| Environment | LLaVA/`transformers` stack; `pyproject.toml` present. Similar deps to GeoChat. |
| GPU needs | ~7B → **≥16 GB VRAM** for fp16 inference (≈8 GB 4-bit). **GPU-blocked on the dev host**, same as GeoChat. |
| Integration cost | **HIGH** — needs a GPU box; licence restricts deployment claims. |
| Benchmark evidence | Authors: beats GPT-4o and Gemini-1.5-Pro on several temporal tasks; strong zero-shot on a change-detection + change-QA dataset; stronger single-image than a comparable single-EO model. All **#1** — unverified by us. |

### 3. CROMA  — contrastive radar-optical masked autoencoder (gap D — top pick to evaluate)

| Field | Value |
|-------|-------|
| Repo | github.com/antofuller/CROMA |
| Paper | "CROMA: Remote Sensing Representations with Contrastive Radar-Optical Masked Autoencoders", NeurIPS 2023 |
| License | **MIT** |
| Model size | ViT-B and ViT-L variants (`CROMA_base.pt`, `CROMA_large.pt`); exact param counts not stated on the repo (ViT-B ≈ 86 M, ViT-L ≈ 300 M by architecture). |
| Input | **Sentinel-1 SAR (2 ch, VV+VH)** + **Sentinel-2 optical (12 ch)**, 120×120 px default (configurable), channel-wise normalised. |
| Output | Per-patch encodings from the SAR, optical, and **joint** encoders + global-average-pooled feature vectors per pathway. (Representations, not task predictions — needs a downstream head.) |
| Supported modality | Optical + SAR, **jointly** (plus each alone). No language, no temporal. |
| Checkpoint availability | **Yes** — HuggingFace `antofuller/CROMA` (base + large). Preprocessed benchmark data also on HF. |
| Environment | PyTorch + `einops` only. Minimal. |
| GPU needs | Small — ViT-B/L at 120×120 → **well under 4 GB**; CPU feasible for inference. |
| Integration cost | **LOW–MEDIUM** — clean, tiny deps, MIT. Cost is the Sentinel-1/2 preprocessing (bands, dB, norm, 120-px tiling) and a small trained head. |
| Benchmark evidence | Paper reports SOTA-class linear-probe / fine-tune results on BigEarthNet, DFC2020, etc. (2023). **#1** — unverified by us. |

### 4. DOFA  — dynamic one-for-all multi-sensor foundation model (gap D/E alternative)

| Field | Value |
|-------|-------|
| Repo | github.com/zhu-xlab/DOFA (also integrated in **TorchGeo**) |
| Paper | "Neural Plasticity-Inspired Multimodal Foundation Model for Earth Observation" / DOFA (2024); DOFA-CLIP extension arXiv:2503.06312 (2025) |
| License | check repo (TorchGeo integration is Apache/MIT-compatible). |
| Model size | ViT-B / ViT-L; a wavelength-conditioned **hypernetwork** generates the patch-embed per sensor. |
| Input | Any of ~5 sensor types incl. **Sentinel-1 SAR** and **Sentinel-2/optical**, specified by wavelength; flexible band count. |
| Output | Patch/global embeddings (representation model). |
| Supported modality | Optical + SAR + hyperspectral + more, one shared encoder. No language. |
| Checkpoint availability | **Yes** — via TorchGeo `DOFA` weights / HF. |
| Environment | PyTorch; easiest via **TorchGeo** (`pip install torchgeo`). |
| GPU needs | ViT-B/L → fits 4 GB; CPU feasible. |
| Integration cost | **LOW** if used through TorchGeo. |
| Benchmark evidence | Authors: competitive with sensor-specific FMs across GEO-Bench etc. **#1** — unverified. |

### 5. MaRS  — multi-modality VHR optical-SAR foundation model (gap D — research candidate only)

| Field | Value |
|-------|-------|
| Repo / page | Project page `rsidea.whu.edu.cn/mars.htm` (WHU RS-IDEA). GitHub link **not confirmed reachable** from here (2026-09-01, page unreachable — ECONNRESET). |
| Paper | "MaRS: A Multi-modality VHR Remote Sensing Foundation Model with Cross-Granularity Meta-Modality Learning", **AAAI 2026**, 40(14):11685–11693. Authors: Yang, Liu, Yan, Zhou, Fu, Luo, Zhong (WHU). |
| License | **not stated** (page unreachable). |
| Model size | **not stated** here (backbone FM; likely ViT-L/H class given VHR + 16 M pretraining). |
| Input | **Paired VHR SAR + optical**, ~0.35 m GSD. Pretrained on **MaRS-16M** (16,785,168 patch pairs). |
| Output | Modality-invariant representations for downstream tasks (segmentation, detection, classification — "nine multi-modality VHR downstream tasks"). Not a VLM. |
| Supported modality | Optical + SAR (VHR). No language, no temporal. |
| Checkpoint availability | Project page **states** dataset + code are available; **not independently verified** (page unreachable). Treat as **UNVERIFIED** until a working GitHub/HF link is confirmed. |
| Environment | not stated. |
| GPU needs | not stated; VHR FM → expect a **large GPU** for anything beyond linear probing. |
| Integration cost | **UNKNOWN → assume HIGH** (VHR, 0.35 m — our imagery is Sentinel-scale ~10 m; domain mismatch unless we source VHR SAR/optical). |
| Benchmark evidence | Authors: strong backbone across 9 VHR multi-modality downstream tasks; sharper object-boundary activations, more consistent RGB/SAR activation. **#1** — unverified. |

**MaRS note:** promising on paper but (a) VHR 0.35 m ≠ our Sentinel-scale data → likely domain mismatch, (b) release not verified, (c) no language/temporal. **CROMA and DOFA are the practical optical-SAR candidates to evaluate first;** MaRS stays a watch-item.

### Also noted (not carded)

- **Co-LLaVA** (2025) — LLaVA-1.5 + CoCa collaboration for RS-VQA; beats GeoChat/RSGPT on RS-VQA per authors. Still ~7B-class → GPU-blocked; revisit if a small variant appears.
- **GeoGround** (2024) — unified RS visual grounding VLM; candidate for gap B if licence/size fit.
- **SAR-KnowLIP** (2025) — multimodal SAR foundation model; watch-item for SAR-heavy tasks.

---

## Minimum infrastructure decision

| Purpose | Minimum infra | Notes |
|---------|---------------|-------|
| **High-capability reference reproduction** — **EarthDial** (primary, 4B) + **GeoChat** (secondary, 7B), gaps A/B/C (+D-language) | **1× Linux GPU, ≥ 16 GB VRAM** (24 GB ideal — A10G / L4 / RTX 4090 / A100-40). ~40 GB disk for weights + env. CUDA 11.8. | Cloud spot instance for a few hours is enough for reproduction + a batch eval. Same box also covers **GeoGround** (GROUNDING REFERENCE) and **TEOChat**. **Not on the A/B critical path** — the local RSCoVLM-3B / TinyRS-2B / Qwen2-VL-2B arms come first. |
| **Change-Agent reproduction** (*optional*, gap C) | Linux + **conda** + CUDA 11.8 toolkit + GPU ≥ 8 GB + a from-source `mmcv==1.3.1` build (or a port to modern mmcv/mmseg). | Higher effort, lower priority. Defer until after EXP-004 / EXP-003 with cheaper options. |
| **Multimodal candidate validation** (CROMA, DOFA — gap D) | **None new.** Runs on the existing RTX 3050 Ti 4 GB or CPU. | Only needs venvs + a small paired Sentinel-1/2 sample (a few hundred–few thousand reBEN patches, **not** the full 549 k). |
| **RS adaptation probe** (gap E) | **None new** — same 4 GB laptop. | Linear/LoRA head on a reBEN subset (~10–50 k patches). |
| **MaRS validation** | Unknown until release is confirmed; VHR FM → likely a **large GPU** + VHR paired data we do not currently have. | Watch-item, not scheduled. |

**Decision:** provision **one cloud Linux GPU box (≥16 GB, prefer 24 GB)** — it
reproduces the **high-capability references** (EarthDial 4B, GeoChat 7B, GeoGround,
TEOChat) and, with conda, Change-Agent, and gives reliable bandwidth for the
multi-GB weights/datasets that fail from this Windows host. Everything on the A/B
*critical path* (RSCoVLM-3B / TinyRS-2B / Qwen2-VL-2B @ 4-bit) plus CROMA/DOFA/
ChangeFormer runs on the existing laptop. Do **not** buy/keep the GPU box until the
local EXP-002 arms + EXP-004 + EXP-E have produced their evidence. **GeoChat's
inability to run locally is not a project blocker.**

---

## Single highest-value next experiment

> **EXP-004 — CROMA joint optical–SAR vs optical-only for built-up classification,
> on a small reBEN (BigEarthNet v2) subset, with a linear-probe head.**

Why this one (it moves **four** mandatory gaps at once, on hardware we already have):

1. **Closes gap D** (optical–SAR joint analysis) — currently **zero** evidence, mandatory, and a core differentiation claim.
2. **Produces gap E** (RS adaptation) — the linear/LoRA probe on **BigEarthNet v2** is exactly the PS-mandated adaptation, with a before→after number.
3. **First real SatQuery number #3** — an *integrated* measurement (encoder → head → metric), not a paper figure.
4. **No infrastructure spend, no waiting** — CROMA (MIT, torch+einops) + a reBEN subset run on the 4 GB laptop; contrast with EXP-001 (blocked on a GPU box) and EXP-006 (blocked on adapters).
5. Directly feeds the SIH story: "optical + SAR evidence measurably improves reliability for suitable queries" (hypothesis **H3**).

**Shape:** register as EXP-004 in `docs/19` (already slotted). Baseline = optical-only
(RemoteCLIP or CROMA-optical head). Candidate = CROMA joint head. Dataset = a fixed,
recorded reBEN subset (S1+S2), held-out split, leakage-checked. Metric = built-up
(and 2–3 other classes) F1 / mAP, + explicit "where SAR hurt". Record seed /
hardware / date. Decision: KEEP / REJECT / INVESTIGATE CROMA for the SAR path.

**Do not start implementation until this matrix is reviewed** (per the G1.5 brief).
