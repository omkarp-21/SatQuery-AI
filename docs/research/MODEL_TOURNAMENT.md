# Model Tournament (G1.6)

> Evidence-based selection of the smallest set of high-value components.
> Date: **2026-09-01**. Host: ASUS Zephyrus G14, RTX 3050 Ti **4 GB VRAM**, no
> conda/Docker/WSL. Method: research → repo validation → smallest informative run
> → verdict. **Nothing is adopted into the pipeline yet** (`docs/18`, `docs/28`).
> Companions: `runtime_validation.md`, `model_inventory.md`,
> `CAPABILITY_GAP_MATRIX.md`, `EXPERIMENT_DECISION_TREE.md`,
> `docs/19_EXPERIMENT_REGISTRY.md`.

## Evidence ladder (5 levels — kept separate)

`PAPER-REPORTED` → `DOCUMENTED (in repo)` → `REPRODUCED (we ran the example)` →
`MEASURED (we scored it vs data)` → `INTEGRATED (runs in SatQuery via an adapter)`
→ `VALIDATED (end-to-end in the pipeline with provenance)`.

Current: nothing is INTEGRATED. 4 models are REPRODUCED (RemoteCLIP, ChangeFormer,
CROMA, DOFA); ChangeFormer also has one MEASURED point (n=7).

---

## A. Full candidate inventory (15 repos from the G1.6 brief + carry-overs)

| # | Repo | Intended role | License | Weights released? | Local-feasible (4 GB)? | This session |
|---|------|---------------|---------|-------------------|------------------------|--------------|
| 1 | awesome-rs-vlms | catalogue | MIT | n/a | n/a | reference only |
| 2 | **GeoChat** | single-img VQA/caption/grounding | Apache¹ (no LICENSE file) | yes (`MBZUAI/geochat-7B`) | **no** (7B > 4 GB; deepspeed/bnb fail on Windows) | BLOCKED (G1) |
| 3 | **Change-Agent** | temporal semantic + caption | MIT | yes (`MCI_model.pth`) | **no** (`mmcv==1.3.1` unbuildable) | BLOCKED (G1) |
| 4 | **ChangeChat** | temporal change caption/VQA | absent | **no** ("coming soon"); README now says **≥48 GB VRAM** (L20) for training; `requirements.txt` present | no | **RE-VERIFIED — still REJECT** |
| 5 | **ChangeFormer** | change mask worker | MIT | yes (GH release) | **yes** | RUNNING (G1) — **KEEP** |
| 6 | **RemoteCLIP** | RS embeddings / zero-shot / retrieval | Apache-2.0 | yes (`chendelong/RemoteCLIP`) | **yes** | RUNNING (G1) — **KEEP** |
| 7 | **CROMA** | optical–SAR joint representation | **MIT** | yes (`antofuller/CROMA`) | **yes** | **REPRODUCED (G1.6)** — KEEP FOR TOURNAMENT |
| 8 | **DOFA** | multi-sensor (incl. SAR) representation | **MIT** | yes (`XShadow/DOFA`) | **yes** | **REPRODUCED (G1.6)** — CROMA challenger |
| 9 | **RS-MoE** | lightweight RS VQA + captioning (MoE) | not stated | **no** — no checkpoint, no inference script, training-only (InstructBLIP cfgs) | no | **REJECT for now** (no artifacts) |
| 10 | **TinyRS / TinyRS-R1** | lightweight single-image VLM | Apache-2.0 (code) | yes (`aybora/Qwen2-VL-TinyRS*` on HF) | **borderline yes** (2B, 4-bit ~1.5 GB / CPU) | DOCUMENTED — **primary local VQA candidate** |
| 11 | **GeoGround** | RS visual grounding (HBB/OBB/mask) | not stated | yes (`erenzhou/GeoGround`, LLaVA framework) | **no** (~7B) | DOCUMENTED — remote grounding ceiling |
| 12 | **UniRS** | unified single / dual-temporal / video VLM | code Apache-2.0; **weights CC-BY-NC-SA-4.0 (non-commercial)** | not clearly stated | **no** (VILA-1.5, flash-attn 2.4.2) | DOCUMENTED — remote, licence-restricted |
| 13 | **LRS-VQA** | large-RS-image VQA + token-pruning + **benchmark** | not stated | yes (Qwen2-7B / Vicuna-7B on HF/ModelScope) | **no** (7B, A100-tested) | DOCUMENTED — useful as a **VQA benchmark** |
| 14 | **RSCoVLM** | multi-task RS VLM (VQA + grounding + detect) | **code MIT / data CC-BY-4.0** | yes (HF collection); **3B and 7B** (Qwen2.5-VL) | **borderline yes (3B)** | DOCUMENTED — **strong TinyRS challenger** (best licence) |
| 15 | **SARLANG-1M** | SAR-language **dataset/benchmark** (1M pairs, 7 tasks) | not stated | n/a — **data only**, no model (`YiminJimmy/SARLANG-1M`) | n/a | DOCUMENTED — **SAR-language eval + fine-tune data** |

¹ classifier metadata only; verify before redistribution.
Carry-over from G1.5: **TEOChat** (temporal EO VLM, ~7B, non-commercial) — remote
only; **MaRS** (VHR optical–SAR FM, AAAI 2026) — watch-item, release unverified,
VHR ≠ our Sentinel scale.

### B. Reproduced this session (real runs)

| Model | What ran | Result | Params | Latency (CPU) | RSS | Verdict |
|-------|----------|--------|--------|---------------|-----|---------|
| **CROMA** (base) | official `use_croma.py` example (README) — SAR(2×120²)+optical(12×120²) → 6 embedding tensors | all keys present, shapes correct (225 patches, dim 768), `joint_GAP` finite & varies (std 0.047) | 194.4 M | ~340 ms/sample (joint forward) | ~1.1–1.8 GB | **REPRODUCED** |
| **DOFA** (ViT-base) | `dofa_v1.vit_base_patch16` + `DOFA_ViT_base_e100.pth`, `forward_features(x, wave_list)` for S2 (12 ch) and **S1 SAR (2 ch)** | (B,768) global feature, finite, both modalities via one wavelength-conditioned encoder; missing/unexpected keys = MAE heads (expected per README) | 111.3 M | ~130 ms/sample (S2), ~110 ms (S1) | ~1.3 GB | **REPRODUCED** |

Both are **MIT**, run on **CPU**, fit the 4 GB GPU with large headroom, minimal
deps (torch + einops for CROMA; torch + `timm==0.9.2` for DOFA). No source edits.
`.venvs/croma`, `.venvs/dofa`; checkpoints in `models/cache/` (gitignored).

### C. Still blocked / cannot reproduce here

| Model | Failure class | Reason | Decision |
|-------|---------------|--------|----------|
| GeoChat | hardware + dependency | 7B > 4 GB VRAM (even 4-bit ~5–6 GB); `deepspeed==0.9.5` fails to build on Windows; `bitsandbytes==0.41.0` Linux-only | TEST FURTHER on a remote GPU ≥16 GB |
| GeoGround | hardware | ~7B LLaVA class | TEST FURTHER on remote GPU (grounding ceiling) |
| UniRS | hardware + licence | VILA-1.5 + flash-attn; weights **non-commercial** | TEST FURTHER on remote GPU; licence blocks deployment claims |
| LRS-VQA | hardware | 7B, A100-tested | Use as a **benchmark**, not a runtime model |
| RSCoVLM (7B) | hardware | 7B | its **3B** variant is the local candidate instead |
| Change-Agent | dependency | `mmcv==1.3.1` unbuildable (no wheels; needs CUDA toolkit + MSVC) | TEST FURTHER on Linux+conda only if EXP-003 needs it |
| ChangeChat | missing checkpoint | no released weights (2 commits); training needs ≥48 GB | **REJECT for now** |
| RS-MoE | missing checkpoint | no released weights, no inference script | **REJECT for now** |
| TinyRS / RSCoVLM-3B | *not attempted this session* | large `transformers` install + multi-GB weight download; not justified in a research phase | **TEST FURTHER locally** — next session (EXP-002) |

---

## Tournaments

### Tournament A — Single-image VQA  *(mandatory capability A)*

| Candidate | Status | Notes |
|-----------|--------|-------|
| RS-MoE | **REJECTED** | no released weights / inference path — cannot enter |
| GeoChat | BLOCKED locally | 7B; strong documented VQA (RSVQA etc.); remote-GPU reference |
| UniRS | BLOCKED locally | VILA-1.5; non-commercial weights |
| **TinyRS / TinyRS-R1** | DOCUMENTED, local-feasible | Qwen2-VL-2B, Apache-2.0, HF weights; authors' VQA acc ≈ 83.5 % (≈ GeoChat), #1 unverified |
| **RSCoVLM-3B** | DOCUMENTED, local-feasible | Qwen2.5-VL-3B, **MIT/CC-BY-4.0**, HF weights, multi-task (VQA+grounding+detect); newer |
| LRS-VQA | benchmark, not a runtime pick | use its 7 333-QA set to score the others |

**Best VQA candidate (evidence-based): none proven yet. Recommended path —
TinyRS as the primary *local* candidate, RSCoVLM-3B as challenger; GeoChat as the
*remote* quality reference.** Rationale: they are the only released-weight VQA
models that plausibly run on 4 GB; RS-MoE (the hoped-for lightweight winner) has no
artifacts. **Decision experiment: EXP-002** — run TinyRS + RSCoVLM-3B on an RSVQA-LR
sample locally; rent a GPU for GeoChat only if both materially underperform.

### Tournament B — Secondary single-image task (grounding vs captioning)  *(mandatory capability B)*

| Candidate | Status | Notes |
|-----------|--------|-------|
| GeoGround | DOCUMENTED | grounding-specialised (HBB/OBB/**mask**), HF weights, ~7B → remote |
| GeoChat grounding | BLOCKED locally | remote |
| RS-MoE captioning | REJECTED | no weights |
| TinyRS grounding | DOCUMENTED, local | boxes-in-text at 2B |
| RSCoVLM grounding | DOCUMENTED, local | spatial grounding at 3B |

**Recommendation: choose GROUNDING** over captioning — stronger evidence
visualisation (a box on the map is inspectable), better demo value, and a clean
benchmark (DIOR-RSVG acc@IoU0.5). Local path: whichever of TinyRS / RSCoVLM-3B
grounds acceptably (measured inside EXP-002). **GeoGround is the remote quality
ceiling / backup.**

### Tournament C — Temporal  *(mandatory capability C)*

| Candidate | Status | Notes |
|-----------|--------|-------|
| **ChangeFormer** | **MEASURED** (IoU 0.83 / F1 0.91, n=7) | binary **mask** only — no semantics, no language |
| Change-Agent | BLOCKED | semantic (building/road) + caption; `mmcv` wall |
| ChangeChat | REJECTED | no weights; ≥48 GB to train |
| UniRS | BLOCKED locally | unified temporal VLM; non-commercial |
| TEOChat (G1.5) | BLOCKED locally | semantic change + change-QA; non-commercial; ~7B |

**Best temporal candidate: KEEP ChangeFormer as the mask worker.** For the
mandatory *language* side (change description / change-VQA), the recommended first
build is a **cheap composed pipeline** — `T1+T2 → ChangeFormer → mask → connected
components → caption each region with the chosen single-image VLM → rule-assemble a
change description` — MEASURED in **EXP-003** on a LEVIR-MCI / LEVIR-CC sample.
TEOChat / Change-Agent / UniRS are remote quality ceilings, compared only if the
cheap pipeline underperforms. No single model should do everything.

### Tournament D — Optical + SAR  *(mandatory capability D — biggest gap, now has evidence)*

| Candidate | Status | Architecture | Params | CPU latency | Licence |
|-----------|--------|--------------|--------|-------------|---------|
| **CROMA** (base) | **REPRODUCED** | explicit **joint radar-optical cross-encoder** (S1 2 ch + S2 12 ch, 120²); contrastive + MAE pretraining on S1/S2 | 194 M | ~340 ms/sample | MIT |
| **DOFA** (ViT-B) | **REPRODUCED** | **one wavelength-conditioned encoder** for any sensor; S1/S2 encoded separately, fuse downstream | 111 M | ~120 ms/sample | MIT |

**Best optical–SAR candidate: CROMA is the primary, DOFA the challenger — decided
by EXP-004, not declared now.** Evidence for the lean:
- CROMA has a **native joint encoder** → directly matches the PS wording "joint
  reasoning over the two observations"; DOFA's fusion is a downstream design choice.
- DOFA is lighter and more flexible (any band count, one model for optical + SAR +
  hyperspectral) → better if we later add sensors, and a fair "does fusion even
  help?" baseline.
- Both reproduced locally, both MIT, both ~sub-GB — no reason to pick before EXP-004.

**Do NOT conclude "SAR improves accuracy" without EXP-004** (same dataset / split /
task / probe / budget; report absolute + relative delta, where SAR helps, where it
hurts).

### Tournament E — Remote-sensing adaptation  *(mandatory capability E)*

| Option | Status | Notes |
|--------|--------|-------|
| RS-MoE adaptation | out | no base weights |
| TinyRS instruction-tuning | later / remote | needs a GPU; a VLM adaptation, higher cost |
| **Linear probe / LoRA on a frozen RS encoder** | **executable now** | CROMA or DOFA features (both reproduced) + a small head on **reBEN / BigEarthNet v2** subset |

**Best adaptation strategy: a bounded probe on frozen CROMA (or DOFA) features over
a reBEN subset — linear probe first, then LoRA — reported as EXP-008.** This is the
smallest credible before→after that satisfies the PS adaptation requirement, runs
locally, and reuses the D-tournament encoders. **Method labels stay distinct:**
linear probe (train only a linear head) ≠ LoRA (low-rank adapters in the backbone)
≠ full fine-tune ≠ instruction tuning.

---

## Model-selection scorecard (qualitative — KEEP / KEEP-LATER / BACKUP / TEST-FURTHER / REJECT)

| Model | Acc. evidence | Reliab. | Generaliz. | HW feasible (4 GB) | Latency | Reproducible | Integration cost | Licence | SIH coverage | **Verdict** |
|-------|---------------|---------|-----------|--------------------|---------|--------------|------------------|---------|--------------|-------------|
| RemoteCLIP | reproduced (zero-shot) | — | RS-tuned CLIP | ✅ | ~150 ms | ✅ | LOW | Apache-2.0 | retrieval / planner aux, not VQA | **KEEP** |
| ChangeFormer | **measured** IoU 0.83 (n=7) | — | LEVIR-trained | ✅ | ~790 ms | ✅ | LOW–MED (env pins) | MIT | C (mask) | **KEEP** |
| CROMA | reproduced (embeddings) | — | S1/S2 pretrain | ✅ | ~340 ms | ✅ | LOW–MED | MIT | D (joint), E (probe) | **KEEP FOR TOURNAMENT** (primary D) |
| DOFA | reproduced (embeddings) | — | multi-sensor | ✅ | ~120 ms | ✅ | LOW | MIT | D (challenger), E | **KEEP FOR TOURNAMENT** |
| TinyRS | paper-only | — | RS instruction-tuned | borderline | untested | not yet | MED | Apache-2.0 | A, B | **TEST FURTHER** (local, EXP-002) |
| RSCoVLM-3B | paper-only | — | RS multi-task | borderline | untested | not yet | MED | **MIT** | A, B | **TEST FURTHER** (local, EXP-002) |
| GeoChat | documented | — | RS instruction-tuned | ❌ local | — | not yet | HIGH | Apache¹ | A, B | **TEST FURTHER** (remote GPU) |
| GeoGround | documented | — | RS grounding | ❌ local | — | not yet | HIGH | B | **TEST FURTHER** (remote) / **BACKUP** |
| LRS-VQA | documented + benchmark | — | large-RS-image VQA | ❌ local | — | not yet | HIGH | A (benchmark) | **KEEP FOR LATER** (as benchmark) |
| TEOChat | documented | — | temporal EO | ❌ local | — | not yet | HIGH | C | **TEST FURTHER** (remote); licence risk |
| UniRS | documented | — | unified temporal | ❌ local | — | not yet | HIGH | C | **BACKUP** (non-commercial) |
| Change-Agent | documented | — | LEVIR-MCI | ❌ local | — | not yet | HIGH | C (semantic) | **TEST FURTHER** (Linux) |
| SARLANG-1M | n/a (data) | — | — | n/a | — | — | — | not stated | SAR-language eval + fine-tune | **KEEP FOR LATER** (dataset) |
| MaRS | paper-only | — | VHR only | ❌ | — | release unverified | UNKNOWN | not stated | D (VHR) | **BACKUP / WATCH** |
| ChangeChat | none | — | — | ❌ | — | ❌ (no weights) | — | absent | — | **REJECT for now** |
| RS-MoE | paper-only | — | RS caption/VQA | ? | — | ❌ (no weights) | — | not stated | A, B | **REJECT for now** |

---

## Final recommendations (report items D–N)

**D. Best single-image VQA candidate** — *No winner yet (nothing reproduced).*
Local: **TinyRS** (primary), **RSCoVLM-3B** (challenger). Remote reference:
GeoChat. Resolve via EXP-002.

**E. Best grounding/caption candidate** — Choose **grounding**. Local: TinyRS /
RSCoVLM grounding head (via EXP-002). Ceiling/backup: **GeoGround** (remote).

**F. Best temporal candidate** — **ChangeFormer** (mask, MEASURED) **+ a composed
caption pipeline** for the language side. Ceilings: TEOChat / Change-Agent (remote).

**G. Best optical–SAR candidate** — **CROMA** (primary, native joint encoder,
REPRODUCED), **DOFA** (challenger, REPRODUCED). Decide in EXP-004.

**H. Best adaptation strategy** — **Linear probe → LoRA on frozen CROMA/DOFA
features over a reBEN (BigEarthNet v2) subset** (EXP-008). Bounded, local,
before→after.

**I. Evidence level per mandatory capability**

| Cap | Level now | Note |
|-----|-----------|------|
| A single-image VQA | **DOCUMENTED** | TinyRS/RSCoVLM releasable locally; none reproduced |
| B extra single-image task | **DOCUMENTED** (grounding) / RemoteCLIP retrieval REPRODUCED (not "captioning/grounding" per PS) | |
| C bi-temporal change | mask **MEASURED** (ChangeFormer n=7); semantic/language **NONE** | |
| D optical–SAR | **REPRODUCED** (CROMA + DOFA embeddings) — up from NONE | not yet MEASURED on a task |
| E RS adaptation | **NONE** (plan ready: EXP-008 on reproduced encoders) | |
| F agentic routing | **DESIGNED** only | needs ≥2 adapters first |
| G geospatial validation | **DESIGNED** only | prerequisite for C & D trust |
| H evidence + confidence + audit | **DESIGNED** only | |

**J. Current unresolved blockers**
1. No VQA model reproduced (A/B) — TinyRS/RSCoVLM local run not yet attempted.
2. No semantic/language change (C) — needs the composed pipeline or a remote VLM.
3. D, E not yet MEASURED — needs EXP-004 / EXP-008 (a small reBEN subset).
4. F/G/H are code we haven't written (blocked on adapters + the geospatial stage).
5. GeoChat / TEOChat / GeoGround / Change-Agent all need a remote Linux GPU.

**K. Is remote GPU justified?** — **Not yet.** Every next high-value experiment
(EXP-004 optical–SAR, EXP-008 adaptation, EXP-002 TinyRS/RSCoVLM-3B local) runs on
the 4 GB laptop. Rent **one** Linux GPU ≥16 GB **only after** EXP-002/004/008, and
**only if** the local VQA candidates materially underperform GeoChat on our RSVQA
subset — then a few hours reproduces GeoChat + TEOChat + GeoGround on the same box.

**L. Recommended minimum V0 stack** (all locally reproduced, no GPU spend):
- **RemoteCLIP** — retrieval / zero-shot tagging / planner-aux embedding index.
- **ChangeFormer** — bi-temporal change mask.
- **CROMA** *(pending EXP-004)* — optical–SAR joint features + the reBEN adaptation head.
- SatQuery-owned: GeoTIFF ingestion, metadata + CRS validation, pair-compatibility,
  constrained planner, registry, adapters, evidence + confidence + provenance.
- VQA (A) and grounding (B) enter V0.5 once EXP-002 picks TinyRS or RSCoVLM-3B.

**M. Top 3 experiments after G1.6**
1. **EXP-004** — CROMA vs DOFA, optical-only vs optical+SAR, reBEN subset, linear
   probe. Closes D, tests H3, first integrated #3 number. *(local)*
2. **EXP-008** — linear-probe → LoRA on frozen CROMA/DOFA over the same reBEN
   subset. Closes E with a before→after. *(local, shares EXP-004 data)*
3. **EXP-002** — TinyRS vs RSCoVLM-3B on an RSVQA-LR sample (VQA + grounding),
   4-bit / CPU. Picks the local single-image model for A/B. *(local)*

**N. Win scorecard** — see `docs/PROJECT_STATUS.md` (updated this session).
