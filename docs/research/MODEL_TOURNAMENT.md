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

**G6–G8 (2026-09-01):** model discovery is **stopped** — roles below are frozen;
the *stack* cannot freeze until A/B/D/E are measured (ADR-015/016). Local
unblocked work done: EXP-005 structural verifier (P/R/F1 = 1.00, n=24); EXP-003b
crop strategies (agreement 4/6); EXP-005b model-independent semantic verifier
(P/R/F1 = 1.00, n=34, INTEGRATED); **G8: failure-aware routing INTEGRATED**
(`derive_resolution` 6 qualifiers + `image_difference_fallback`, 10 tests).
EXP-002 / EXP-004 Run 2 / EXP-008 / EXP-C1/C2 stay blocked on the remote GPU box
(`docs/deployment/REMOTE_GPU_SETUP.md`). Scorecards:
`docs/research/G6_CAPABILITY_CLOSURE.md`, `docs/sih/evidence/README.md`.

Current (post-G5A): 4 models REPRODUCED behind the standard `SpecialistAdapter`
contract. **ChangeFormer + RemoteCLIP INTEGRATED**, now reachable through the
unified **`POST /analyze`** (deterministic interpret → route → dispatch →
aggregate). CROMA/DOFA INTEGRATED as `run_joint_representation()` (representation-
level). A `COMPOSED_SEMANTIC_CHANGE_BASELINE` chains ChangeFormer + RemoteCLIP for
capability C (experimental, disclaimed). Nothing is VALIDATED. The
model-selection experiments (EXP-002 VQA/grounding, EXP-004 Run 2 optical-SAR,
EXP-008 adaptation) are **BLOCKED on artifact acquisition from this host** — **G5A
ran the A/B gate and hit the 6th documented weight-download failure** (0-byte
safetensors on a fresh `Qwen/` repo, 8-min bound); frozen sample specs +
`evaluation/scripts/exp002_ab_gate.py` are committed and ready. **Remote reference
gate OPEN (ADR-013).** Ledger: `EVIDENCE_LEDGER.md`. Confidence: `CONFIDENCE_PLAN.md`.

---

## Model hierarchy (authoritative — ADR-011, ADR-012)

Role labels, not a ranking of quality. **No repo is a "ceiling"** — that word is
reserved for a model that has been *reproduced and measured* under our evaluation,
which none has. Until then EarthDial and GeoChat are **references**. No new
repositories were added; the core SatQuery architecture is unchanged.

| Role | Model | Repo | Licence | Evidence state | Where it runs |
|------|-------|------|---------|----------------|---------------|
| **LOCAL A/B PRIMARY** | **RSCoVLM-3B** | github.com/VisionXLab/RSCoVLM | code MIT / data CC-BY-4.0 | DOCUMENTED | RTX 3050 Ti @ 4-bit / CPU |
| **LOCAL A/B FALLBACK** | **TinyRS-2B** | github.com/aybora/TinyRS | Apache-2.0 (code) | DOCUMENTED — weight DL **BLOCKED** from this host | RTX 3050 Ti @ 4-bit / CPU |
| **GENERIC CONTROL** | **Qwen2-VL-2B** | github.com/QwenLM/Qwen2-VL | Apache-2.0 | runnable (generic) | anywhere @ 4-bit / CPU |
| **TEMPORAL** | **ChangeFormer** | github.com/wgcban/ChangeFormer | MIT | **INTEGRATED** — MEASURED IoU 0.83 / F1 0.91 (n=7) | CPU / 4 GB GPU |
| **OPTICAL-SAR PRIMARY** | **CROMA** | github.com/antofuller/CROMA | MIT | **REPRODUCED** — decide vs DOFA in EXP-004 Run 2 | CPU / 4 GB GPU |
| **OPTICAL-SAR CHALLENGER** | **DOFA** | github.com/zhu-xlab/DOFA | MIT | **REPRODUCED** | CPU / 4 GB GPU |
| **GROUNDING REFERENCE** | **GeoGround** | github.com/VisionXLab/GeoGround | not stated | DOCUMENTED | remote (~7B) |
| **AUXILIARY** | **RemoteCLIP** | github.com/ChenDelong1999/RemoteCLIP | Apache-2.0 | **INTEGRATED** — retrieval / zero-shot / embedding; **not VQA** | CPU / 4 GB GPU |
| **PRIMARY HIGH-CAPABILITY REFERENCE** | **EarthDial** | github.com/hiyamdebary/EarthDial | code MIT / weights unconfirmed | **REFERENCE CANDIDATE** — not reproduced | remote (4B; ≈8–9 GB bf16) |
| **SECONDARY / HISTORICAL RS-VLM REFERENCE** | **GeoChat** | github.com/mbzuai-oryx/GeoChat | Apache¹ (no LICENSE file) | secondary reference — **not** on the critical path; local-run inability is **not** a blocker | remote (~7B) |
| **RESEARCH REFERENCE** | **SARLANG-1M** | github.com/jimmyxichen/sarlang-1m | not stated | dataset/benchmark — SAR-language eval + fine-tune data | n/a (data) |

**EarthDial verification (2026-09-01, no large artifacts downloaded):**
checkpoints **exist** — HF `akshaydudhane/EarthDial_4B_{RGB,MS,Methane_UHI}`,
Safetensors / BF16 / `internvl_chat` / "4B params"; HF pages show **"No model
card"**. Licence: repo footer **MIT**, HF pages assert **no licence** → weights
licence **unconfirmed**. Hardware: trained on 8×A100-80GB; **inference VRAM not
documented** (4B bf16 ≈ 8–9 GB — no 4 GB fit; 4-bit ≈ 3–3.5 GB, unverified).
Env: Python 3.9, InternVL2 + Phi-3-Mini, `flash-attn==2.3.6` (training); torch /
CUDA / `transformers` **not pinned**. Inference path: README points to a "demo
section" — **exact entrypoint not confirmed, not run**. Repo health: 45 commits,
140 stars, CVPR 2025. → **REFERENCE CANDIDATE until reproduced.**

---

## A. Full candidate inventory (15 repos from the G1.6 brief + carry-overs)

| # | Repo | Intended role | License | Weights released? | Local-feasible (4 GB)? | This session |
|---|------|---------------|---------|-------------------|------------------------|--------------|
| 1 | awesome-rs-vlms | catalogue | MIT | n/a | n/a | reference only |
| 2 | **GeoChat** | **secondary / historical** RS-VLM reference (VQA/caption/grounding) | Apache¹ (no LICENSE file) | yes (`MBZUAI/geochat-7B`) | **no** (7B > 4 GB; deepspeed/bnb fail on Windows) | BLOCKED (G1) — **not a project blocker** |
| 2b | **EarthDial** | **primary high-capability reference** (RS multi-task VLM, +SAR +temporal +grounding) | code **MIT** / weights unconfirmed | yes (`akshaydudhane/EarthDial_4B_{RGB,MS,Methane_UHI}`, InternVL2+Phi-3, 4B, BF16) | **no** (4B ≈ 8–9 GB bf16; 4-bit ~3–3.5 GB unverified) | **REFERENCE CANDIDATE** (verified checkpoints exist; not reproduced) |
| 3 | **Change-Agent** | temporal semantic + caption | MIT | yes (`MCI_model.pth`) | **no** (`mmcv==1.3.1` unbuildable) | BLOCKED (G1) |
| 4 | **ChangeChat** | temporal change caption/VQA | absent | **no** ("coming soon"); README now says **≥48 GB VRAM** (L20) for training; `requirements.txt` present | no | **RE-VERIFIED — still REJECT** |
| 5 | **ChangeFormer** | change mask worker | MIT | yes (GH release) | **yes** | RUNNING (G1) — **KEEP** |
| 6 | **RemoteCLIP** | RS embeddings / zero-shot / retrieval | Apache-2.0 | yes (`chendelong/RemoteCLIP`) | **yes** | RUNNING (G1) — **KEEP** |
| 7 | **CROMA** | optical–SAR joint representation | **MIT** | yes (`antofuller/CROMA`) | **yes** | **REPRODUCED (G1.6)** — KEEP FOR TOURNAMENT |
| 8 | **DOFA** | multi-sensor (incl. SAR) representation | **MIT** | yes (`XShadow/DOFA`) | **yes** | **REPRODUCED (G1.6)** — CROMA challenger |
| 9 | **RS-MoE** | lightweight RS VQA + captioning (MoE) | not stated | **no** — no checkpoint, no inference script, training-only (InstructBLIP cfgs) | no | **REJECT for now** (no artifacts) |
| 10 | **TinyRS / TinyRS-R1** | lightweight single-image VLM | Apache-2.0 (code) | yes (`aybora/Qwen2-VL-TinyRS*` on HF) | **borderline yes** (2B, 4-bit ~1.5 GB / CPU) | DOCUMENTED — **primary local VQA candidate** |
| 11 | **GeoGround** | RS visual grounding (HBB/OBB/mask) | not stated | yes (`erenzhou/GeoGround`, LLaVA framework) | **no** (~7B) | DOCUMENTED — **GROUNDING REFERENCE** (remote) |
| 12 | **UniRS** | unified single / dual-temporal / video VLM | code Apache-2.0; **weights CC-BY-NC-SA-4.0 (non-commercial)** | not clearly stated | **no** (VILA-1.5, flash-attn 2.4.2) | DOCUMENTED — remote, licence-restricted |
| 13 | **LRS-VQA** | large-RS-image VQA + token-pruning + **benchmark** | not stated | yes (Qwen2-7B / Vicuna-7B on HF/ModelScope) | **no** (7B, A100-tested) | DOCUMENTED — useful as a **VQA benchmark** |
| 14 | **RSCoVLM** | multi-task RS VLM (VQA + grounding + detect) | **code MIT / data CC-BY-4.0** | yes (HF collection); **3B and 7B** (Qwen2.5-VL) | **borderline yes (3B)** | DOCUMENTED — **strong TinyRS challenger** (best licence) |
| 15 | **SARLANG-1M** | SAR-language **dataset/benchmark** (1M pairs, 7 tasks) | not stated | n/a — **data only**, no model (`YiminJimmy/SARLANG-1M`) | n/a | DOCUMENTED — **SAR-language eval + fine-tune data** |
| 16 | **RemoteSAM** (`1e12Leon/RemoteSAM`) | GROUNDING/SEGMENTATION specialist — referring seg + visual grounding (mask+box); NOT a VLM | not stated | yes (Swin-B+BERT ~200 M, ACM MM 2025) | ✅ size; env-BLOCKED (`mmcv-full==1.7.1`) | **TEST FURTHER — lead capability-B candidate** (`LOCAL_LIGHTWEIGHT_MODEL_TOURNAMENT.md`) |
| 17 | **DynamicVis** (`KyanChen/DynamicVis`) | PERCEPTION/ENCODER (Mamba SSM); NOT a VLM | Apache-2.0 | yes (b/l) | VRAM easy (~800 MB) but **Windows+CPU incompatible** | **REJECT for product** (portability); watch-item |
| 18 | **RS-MoE** (`CongcongWen1208/RS-MoE`) | GENERAL VLM (claim) — caption + VQA | not stated | **no** (training-only; base Vicuna-13B) | ❌ | **REJECT (no artifact)** |

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
| GeoGround | hardware | ~7B LLaVA class | TEST FURTHER on remote GPU (GROUNDING REFERENCE) |
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

**Best VQA candidate (evidence-based): none proven yet.** Recommended path
(ADR-011/012): **RSCoVLM-3B = LOCAL A/B PRIMARY**, **TinyRS-2B = LOCAL A/B
FALLBACK**, **Qwen2-VL-2B = GENERIC CONTROL**. High-capability references are
**EarthDial (primary, REFERENCE CANDIDATE)** and **GeoChat (secondary /
historical)** — neither is a "ceiling" until reproduced + measured. **Decision
experiment: EXP-002** — run RSCoVLM-3B + TinyRS-2B + Qwen2-VL-2B on an RSVQA-LR /
DIOR-RSVG sample locally @ 4-bit; a remote GPU box reproduces EarthDial + GeoChat
for the reference comparison **only** once the local arms are measured.

### Tournament B — Secondary single-image task (grounding vs captioning)  *(mandatory capability B)*

| Candidate | Status | Notes |
|-----------|--------|-------|
| **RemoteSAM** | **TEST FURTHER — lead** | dedicated ~200 M referring-seg + visual-grounding specialist (**mask + box**), ACM MM 2025, `LOCAL-FITS-4GB`; env-BLOCKED (`mmcv-full==1.7.1`) + licence unstated. `LOCAL_LIGHTWEIGHT_MODEL_TOURNAMENT.md` |
| RSCoVLM grounding | DOCUMENTED, local | spatial grounding at 3B — fallback |
| TinyRS grounding | DOCUMENTED, local | boxes-in-text at 2B |
| Qwen2-VL-2B | DOCUMENTED | native `<box>` tokens — generic control |
| GeoGround | DOCUMENTED | grounding-specialised (~7B) → **GROUNDING REFERENCE** (remote) |
| RS-MoE captioning | REJECTED | no weights / no inference code (2 repos) |

**Recommendation: choose GROUNDING, and make it a DEDICATED SPECIALIST.**
The Local Lightweight Tournament found **RemoteSAM** — a ~200 M model purpose-built
for referring segmentation + visual grounding that emits a **mask *and* a box**
(both directly mappable as evidence). That is strictly better for capability B
than forcing a 3 B VQA model to emit coordinates in text. **Primary = RemoteSAM**
(reproduce first — weights ≈ sub-GB, the risk is the `mmcv` env), **fallback =
RSCoVLM-3B grounding head**, **reference = GeoGround** (remote). Benchmark:
DIOR-RSVG acc@IoU0.5 on the frozen 25-expression sample.

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
TEOChat / Change-Agent / UniRS are remote high-capability references, compared
only if the cheap pipeline underperforms. **EarthDial** (PRIMARY HIGH-CAPABILITY
REFERENCE) natively covers temporal + change and is the first to reproduce on a
remote box for C. No single model should do everything.

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
| RSCoVLM-3B | paper-only | — | RS multi-task | borderline (4-bit) | untested | not yet | MED | **MIT** | A, B | **LOCAL A/B PRIMARY** (EXP-002) |
| TinyRS-2B | paper-only | — | RS instruction-tuned | borderline (4-bit) | untested | not yet | MED | Apache-2.0 | A, B | **LOCAL A/B FALLBACK** (EXP-002; DL blocked) |
| Qwen2-VL-2B | generic #1 only | — | generic (not RS) | ✅ (4-bit) | untested | not yet | LOW | Apache-2.0 | A, B (control) | **GENERIC CONTROL** |
| EarthDial | paper-only | — | RS multi-task (+SAR +temporal) | ❌ local (4B) | — | not yet | MED–HIGH | code MIT / weights unconfirmed | A, B, C, D | **PRIMARY HIGH-CAPABILITY REFERENCE** (REFERENCE CANDIDATE) |
| GeoChat | documented | — | RS instruction-tuned | ❌ local | — | not yet | HIGH | Apache¹ | A, B | **SECONDARY / HISTORICAL REFERENCE** (not a blocker) |
| GeoGround | documented | — | RS grounding | ❌ local | — | not yet | HIGH | B | **GROUNDING REFERENCE** (remote) |
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

**D. Best single-image VQA candidate** — *No winner (G5A: nothing reproduced —
artifact acquisition BLOCKED, 6th download failure).* **LOCAL A/B PRIMARY =
RSCoVLM-3B**, **FALLBACK = TinyRS-2B**, **GENERIC CONTROL = Qwen2-VL-2B**;
references **EarthDial** (primary) + **GeoChat** (secondary). No "ceiling" until
reproduced + measured. **Remote reference gate OPEN (ADR-013)** — run
`exp002_ab_gate.py` on a Linux GPU box; local + reference on the same frozen
RSVQA-LR / DIOR-RSVG samples.

**E. Best grounding/caption candidate** — Choose **grounding, as a dedicated
specialist**. **Primary = RemoteSAM** (~200 M, mask + box, RS-native; repro
BLOCKED on the `mmcv` env). Fallback = RSCoVLM-3B grounding head (via EXP-002).
Control = Qwen2-VL-2B native `<box>`. **GROUNDING REFERENCE: GeoGround** (remote).
See `LOCAL_LIGHTWEIGHT_MODEL_TOURNAMENT.md`.

**F. Best temporal candidate** — **ChangeFormer** (mask, MEASURED) **+ a composed
caption pipeline** for the language side. Ceilings: TEOChat / Change-Agent (remote).

**G. Best optical–SAR candidate** — **CROMA** (primary, native joint encoder,
REPRODUCED), **DOFA** (challenger, REPRODUCED). Decide in EXP-004.

**H. Best adaptation strategy** — **Linear probe → LoRA on frozen CROMA/DOFA
features over a reBEN (BigEarthNet v2) subset** (EXP-008). Bounded, local,
before→after.

**I. Evidence level per mandatory capability**

| Cap | Level now (post-G2) | Note |
|-----|-----------|------|
| A single-image VQA | **DOCUMENTED** | EXP-002 setup done; TinyRS download flaky; none reproduced |
| B extra single-image task | **DOCUMENTED** (grounding); RemoteCLIP retrieval REPRODUCED (≠ PS "captioning/grounding") | |
| C bi-temporal change | mask **INTEGRATED** (G2 slice, e2e, provenance); semantic/language **NONE** | |
| D optical–SAR | **REPRODUCED** + probe machinery **VALIDATED** (EXP-004 Run 1, synthetic) | not yet MEASURED on a real task (Run 2) |
| E RS adaptation | **NONE** (harness ready: EXP-008 on the reproduced encoders) | |
| F agentic routing | **DESIGNED** only | needs the remaining adapters first |
| G geospatial validation | **IMPLEMENTED** (`validate_geotiff` + `check_pair_compatibility`, 13 tests, gate live) | not yet stress-tested (EXP-007) |
| H evidence + confidence + audit | provenance **threaded** through the slice; verifier + confidence method **NONE** | no confidence value is produced anywhere |

**J. Current unresolved blockers**
1. No VQA model reproduced (A/B) — TinyRS/RSCoVLM local run not yet attempted.
2. No semantic/language change (C) — needs the composed pipeline or a remote VLM.
3. D, E not yet MEASURED — needs EXP-004 / EXP-008 (a small reBEN subset).
4. F/G/H are code we haven't written (blocked on adapters + the geospatial stage).
5. GeoChat / TEOChat / GeoGround / Change-Agent all need a remote Linux GPU.

**K. Is remote GPU justified?** — **Yes now — the local A/B path is exhausted.**
G5A ran the A/B gate and hit the **6th** documented weight-download failure
(0-byte safetensors on a fresh `Qwen/` repo, 8-min bound → the blocker is this
host's path to the HF CDN, not any one repo). RSVQA-LR + DIOR-RSVG are the same
multi-GB problem. A remote Linux GPU ≥ 16 GB is needed for: (a) reliable bandwidth
to fetch RSCoVLM-3B / TinyRS-2B / Qwen2-VL-2B weights + the eval datasets,
(b) reproducing the references EarthDial-4B + GeoChat-7B + GeoGround on the same
frozen samples, (c) EXP-004 Run 2 / EXP-008 S1+S2. Run the committed
`evaluation/scripts/exp002_ab_gate.py` there. CROMA/DOFA/ChangeFormer still need
no GPU. **GeoChat's local-run inability is not a project blocker** — it is one of
five models the one box unblocks.

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
3. **EXP-002** — RSCoVLM-3B (primary) vs TinyRS-2B (fallback) vs Qwen2-VL-2B
   (control) on an RSVQA-LR + DIOR-RSVG sample (VQA + grounding), 4-bit / CPU.
   Picks the local single-image model for A/B; **EarthDial** (primary
   high-capability reference) + GeoChat reproduced on a remote box afterwards for
   the local-vs-reference comparison. *(local first)*

**N. Win scorecard** — see `docs/PROJECT_STATUS.md` (updated this session).
