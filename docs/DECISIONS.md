# Architecture Decision Log

Chronological record of significant technical decisions. Newest first.
Format inspired by ADRs (lightweight).

---

## ADR-017 — G9: `LOW_MARGIN` advisory added to failure-aware routing; remote batches (A/B/D/E) still blocked on human provisioning; stack NOT frozen — the loop stops here until a machine exists

- **Date:** 2026-09-01
- **Status:** Accepted
- **Context:** G9 repeated the G5A–G8 request: provision a remote GPU, run the
  blocked batches, freeze the stack. **Provisioning a cloud GPU machine is not an
  action this session can perform** — it needs a cloud account, billing, and SSH
  keys held by the user. This has been the identical blocker for five gates. All
  local, unblocked work is done (G6 EXP-005 + crop strategy; G7 EXP-005b semantic
  verifier + evidence pack; G8 failure-aware routing). G9's only remaining
  unblocked item was `LOW_MARGIN` (Phase 9), which needs no second model.
- **Built (real, local):** `ChangeRegion.tag_margin` / `.low_margin` (RemoteCLIP
  rank-1 minus rank-2 similarity < 0.05) on the composed semantic-change baseline;
  `derive_resolution(..., low_margin_regions=N)` emits a non-blocking
  `resolution.advisories` entry (`LOW_MARGIN: N region tag(s) ...`). The answer is
  still surfaced — weak tags are flagged, not dropped. 3 new tests
  (`test_failure_aware.py`, `test_semantic_change_baseline.py`). `API_CONTRACT.md`
  + `FAILURE_AWARE_ROUTING.md` updated (step 3 DONE).
- **Still blocked — provisioning only:** EXP-002 (A/B), EXP-004 Run 2 (D),
  EXP-008 (E), EXP-C1/C2 (confidence), the `independent_model` / `optical_sar`
  disagreement qualifiers, and the model freeze (Phase 11 precondition unmet).
- **Decision — stop re-running the remote-execution loop in-session.** Producing
  another "still blocked" gate report adds no evidence. The next move is the
  user's: provision one Linux GPU box per `docs/deployment/REMOTE_GPU_SETUP.md`
  and run the three committed batch scripts. Everything downstream (selection,
  adapter integration, freeze, EXP-C1) is then a single focused session.
- **Consequence (118 → 121 tests; two additive `ChangeRegion` fields + one
  `ResolutionInfo` field, no contract break, no new deps/repos, no confidence
  value):** `semantic_change_baseline.py`, `failure_aware.py`, `analyze.py`;
  `test_failure_aware.py` (+3), `test_semantic_change_baseline.py` (+1);
  `API_CONTRACT.md`, `FAILURE_AWARE_ROUTING.md`, `PROJECT_STATUS.md`,
  `EVIDENCE_LEDGER.md`.

## ADR-016 — G8: failure-aware routing IMPLEMENTED (post-execution qualifier + single-step image-difference fallback); remote experiments still unrunnable in-session; stack NOT frozen

- **Date:** 2026-09-01
- **Status:** Accepted
- **Context:** G8 = provision the remote GPU lab and run the blocked batches
  (A/B, optical-SAR, adaptation), then freeze. Provisioning is a human
  infrastructure action (cloud account + billing + SSH) not performable in this
  session — the same block as G5A/G6/G7. G8 executed the one substantial
  **local, unblocked** phase: **Phase 10 — failure-aware routing.**
- **Built (real, local — the design from ADR-015 / `FAILURE_AWARE_ROUTING.md`):**
  - **`derive_resolution()`** (`apps/backend/app/services/failure_aware.py`) — a
    **pure, deterministic** function of `verify().status` +
    `verify_semantic().status` + the sub-service `ok`/fallback flags. Emits one
    of six qualifiers — `RESULT_OK`, `RESULT_STRUCTURAL_FAIL` (answer withheld),
    `RESULT_SEMANTIC_INCOHERENT` (answer disputed), `RESULT_UNVERIFIED`,
    `SPECIALIST_DEGRADED`, `SPECIALIST_FAILED` — plus `answer_surfaced`. No LLM,
    no loop, no recursion. **Not a confidence value.**
  - Wired into `/analyze` as an **additive** `resolution` field on `AnalyzeResult`
    (also mirrored in `provenance.resolution`). `/analyze`'s top-level `ok` is
    **deliberately unchanged** — callers gate on `resolution.answer_surfaced`;
    flipping `ok` on a failed verifier is a documented follow-up.
  - **`run_change_fallback()`** (`temporal_slice.py`) — the registry-declared
    trivial baseline for change-detection: abs mean-RGB difference + fixed
    threshold (0.15), **same** `validate_geotiff` + `check_pair_compatibility`
    gate, emits an `EvidenceItem` + `verify()` + provenance
    (`model: "image_difference_fallback"`, `is_fallback: true`,
    `score_meaning: "... NOT ChangeFormer quality"`). `/analyze`'s `TEMPORAL`
    branch calls it **once** if `run_change_slice` fails (the pair is already
    co-registered by that point), yielding `SPECIALIST_DEGRADED`.
  - Tests: `apps/backend/tests/test_failure_aware.py` (10) — one per qualifier,
    determinism, "not a confidence", fallback rejects a misregistered pair,
    fallback produces a real mask + verification on the demo pair; plus a
    `resolution` assertion added to `test_analyze_change_path_aggregates_evidence`.
  - `docs/API_CONTRACT.md` documents the `resolution` field + the fallback;
    `FAILURE_AWARE_ROUTING.md` marks steps 1/2/4/5 DONE, step 3 (`LOW_MARGIN`) and
    the `independent_model`/`optical_sar` disagreement qualifiers TODO/BLOCKED.
- **Still blocked (Phases 2–7, 9, 11 — provisioning only):** EXP-002 (A/B),
  EXP-004 Run 2 (D), EXP-008 (E), EXP-C1/C2 (confidence). Harnesses committed and
  dry-run-clean; runbook `docs/deployment/REMOTE_GPU_SETUP.md`.
- **Decision — the model stack is NOT frozen** (Phase 11 precondition "A/B/D/E
  measured" is unmet). G8 exit criteria: **F now fully met** ("deterministic
  routing integrated **and** failure-aware routing integrated"); C, G, H unchanged
  from G7; A, B, D, E blocked.
- **Consequence (108 → 118 tests; one additive `/analyze` field, no contract
  break, no `ok`-semantics change, no new deps, no new repos, no confidence
  value):** new `apps/backend/app/services/failure_aware.py`,
  `apps/backend/tests/test_failure_aware.py`; `run_change_fallback` appended to
  `temporal_slice.py`; `resolution` field wired through `analyze.py`; updated
  `API_CONTRACT.md`, `FAILURE_AWARE_ROUTING.md`, `PROJECT_STATUS.md`,
  `EVIDENCE_LEDGER.md`, `CAPABILITY_GAP_MATRIX.md`, `MODEL_TOURNAMENT.md`,
  `model_inventory.md`, `19_EXPERIMENT_REGISTRY.md`, `docs/sih/evidence/README.md`.

## ADR-015 — G7: model-independent semantic verifier built + measured; SIH evidence pack + failure-aware-routing design; model stack NOT frozen (A/B/D/E still unmeasured)

- **Date:** 2026-09-01
- **Status:** Accepted
- **Context:** G7 = provision the remote GPU lab, run the blocked experiments,
  select + integrate winners, **freeze the model stack**. The provisioning step is
  a human infrastructure action (cloud account + billing + SSH) that this session
  cannot perform; the runbook (`docs/deployment/REMOTE_GPU_SETUP.md`) is ready.
  So G7 executed the phases that are **local and unblocked**.
- **Built + measured (real, local):**
  - **EXP-005b — model-independent semantic verifier.** New
    `verify_semantic(result, evidence, context)`
    (`packages/evidence/src/satquery_evidence/semantic_verifier.py`): deterministic,
    no model call. Six checks — claim↔evidence number, claim↔evidence label,
    temporal-direction on swapped pairs, region-in-bounds / valid lon-lat,
    whole-scene region, region-areas-vs-total. Declares the checks it **cannot**
    do (`independent_model_agreement`, `optical_sar_agreement`,
    `grounding_roundtrip`) in `coverage_unavailable`.
    Curated 34-case corpus (COHERENT 8 / INCOHERENT 10 / BEYOND_SCOPE 6 /
    NOT_ENOUGH 4): **precision / recall / F1 = 1.00** for model-independent
    incoherence detection (TP 10, FP 0, TN 14, FN 0); **BEYOND_SCOPE miss rate
    1.00** (label-correctness errors — need an independent model, as expected).
    `evaluation/scripts/exp005b_semantic_verifier.py` + 9 lock tests.
    Same caveat as EXP-005: curated, proves the checks fire on their target
    classes, **not** a real-world coverage rate.
  - **Integrated** into `COMPOSED_SEMANTIC_CHANGE_BASELINE` as an **additive**
    `semantic_verification` field (`ComposedSemanticChangeResult`) — no `/analyze`
    contract change beyond the optional field. On the demo pair its own output is
    `COHERENT`.
- **Designed / collected (no code):**
  - `docs/research/FAILURE_AWARE_ROUTING.md` — post-execution routing qualifiers
    (`RESULT_STRUCTURAL_FAIL`, `RESULT_SEMANTIC_INCOHERENT`, `RESULT_UNVERIFIED`,
    `SPECIALIST_DEGRADED`, `LOW_MARGIN`) as pure functions of `verify()` +
    `verify_semantic()` + `AdapterResult.status`; single-step registry-driven
    fallback ladder. Implementation deferred to after the model freeze.
  - `docs/sih/evidence/` — SIH evidence pack: 13-topic traceability index, every
    claim tagged TRACEABLE / PARTIAL / BLOCKED, three-numbers rule enforced.
    `docs/sih/evidence/demos/` — **real** captured outputs for DEMO 2 (`/change`),
    DEMO 4 (misregistered pair rejected), DEMO 5 (evidence + structural + semantic
    verification); DEMO 1 (VQA) and DEMO 3 (optical-SAR) written as explicit
    BLOCKED placeholders — **no fabricated demo output**.
  - `model_registry.yaml` — the 4 integrated models gained `paper`,
    `quantization`, `memory`, and a split `benchmark` (authors') vs
    `our_measured_result` (ours) per Phase 11.
- **Decision — the model stack is NOT frozen.** Phase 10's freeze precondition is
  "A/B/D/E have measurements". They do not (EXP-002 / EXP-004 Run 2 / EXP-008 all
  blocked on the remote box). Freezing now would freeze an unmeasured stack. The
  freeze happens in the session that runs the remote experiments.
- **G7 exit criteria: 4/8 met (C, F, G, H) — unchanged from G6 count, but H
  strengthened:** structural verifier VALIDATED (EXP-005) **plus** a
  model-independent semantic verifier MEASURED + INTEGRATED (EXP-005b). A, B, D, E
  remain blocked solely on provisioning.
- **Consequence (108/108 tests, was 97; one additive service field, no contract
  break, no new deps, no new repos, no confidence value):** new
  `packages/evidence/src/satquery_evidence/semantic_verifier.py` (+ `__init__`
  exports), `evaluation/scripts/{exp005b_semantic_verifier,capture_demo_evidence}.py`,
  `packages/evidence/tests/test_semantic_verifier.py` (9),
  `docs/research/FAILURE_AWARE_ROUTING.md`, `docs/sih/evidence/**`;
  `semantic_verification` field + 2 tests on `semantic_change_baseline.py`;
  updated `EXP-002.md` (Phase 3 table), `EXP-005.md` (EXP-005b),
  `CONFIDENCE_PLAN.md`, `model_registry.yaml`, `EVIDENCE_LEDGER.md`,
  `CAPABILITY_GAP_MATRIX.md`, `MODEL_TOURNAMENT.md`, `model_inventory.md`,
  `PROJECT_STATUS.md`, `19_EXPERIMENT_REGISTRY.md`, `REMOTE_GPU_SETUP.md`.

## ADR-014 — G6 capability closure: 4/8 exit criteria met locally; A/B/D/E blocked solely on remote-GPU provisioning; EXP-005 + crop-strategy experiment RAN

- **Date:** 2026-09-01
- **Status:** Accepted
- **Context:** G6 = "stop searching for models, acquire evidence, measure, select,
  integrate, then build the agentic experience." Executed against commit 275cd09.
  No new repos, no architecture change, no frontend, no fabricated metrics, no
  confidence number.
- **What ran locally (real):**
  - **Phase 8 / EXP-005 — structural verifier detection.** Curated 24-case corpus
    (CLEAN 6 / STRUCTURAL 8 / SEMANTIC 6 / INSUFFICIENT 4). `verify()` on it:
    **precision 1.00, recall 1.00, F1 1.00** for structural-defect detection
    (TP 8, FP 0, TN 12, FN 0); **semantic-defect miss rate 1.00** — the
    structural verifier catches none of the structurally-clean-but-wrong cases,
    by design. Semantic-verifier extension points documented (not built).
    `docs/research/EXP-005.md`; `evaluation/scripts/exp005_verifier_detection.py`;
    3 lock tests. Structural verification → **VALIDATED (structural)**, now with a
    number.
  - **Phase 7 / EXP-003b — semantic-change crop strategy.** Added
    `run_composed_semantic_change(..., crop_strategy=)` with `tight` (default,
    unchanged) / `expanded` (75% context pad) / `mask_aware` (context pad +
    non-changed pixels dimmed 0.35×). 3-way run on the demo LEVIR pair (6 regions,
    CPU, ~45 s/strategy): **cross-strategy agreement 4/6 regions**; `expanded` and
    `mask_aware` rescued a `tight` miss on the largest region; `mask_aware`
    collapses toward one label (monoculture risk — logged as a failure mode).
    Provisional default = `expanded`, **not changed in code** (one demo pair is
    insufficient). `docs/research/EXP-003.md`; harness
    `evaluation/scripts/exp003b_semantic_change_crops.py`; 2 tests (1 fast, 1 slow).
  - **Phase 9 / Confidence** — `CONFIDENCE_PLAN.md`: EXP-C1 (temperature/isotonic
    calibration, ECE ≤ 0.05 gate) and EXP-C2 (optical↔SAR disagreement as an
    error detector) fully specified. **No confidence number emitted.**
  - **Phase 5 / EXP-004 Run 2 dataset decision** — smallest valid real S1+S2 set
    chosen: **DFC2020 `ROIs0000_validation` raw GeoTIFF (≈1.5–2 GB), subsample
    400 train / 200 eval by patch id** — official split, per-file, bounded
    acquisition. `EXP-004.md`.
  - **Phase 6 / EXP-008 method lock** — linear probe / LoRA / MLP-head fallback
    defined exactly; a linear probe is never called fine-tuning. `EXP-008.md`.
  - **Phase 1** — `docs/deployment/REMOTE_GPU_SETUP.md`: turnkey runbook (sizing,
    one-time setup, artifact acquisition, experiment commands, a `record` block).
    Box values `<PENDING>` — provisioning needs a cloud account and is not a code
    task.
- **Decision — G6 exit criteria: 4/8 met (C, F, G, H); 4 blocked (A, B, D, E),
  every one solely on artifact/dataset acquisition** (the 6-times-failed multi-GB
  download from this Windows host, now across 2 HF namespaces). No criterion is
  blocked by a capability gap, a design flaw, or a measured model failure.
  `docs/research/G6_CAPABILITY_CLOSURE.md` is the scorecard.
  - **No production A/B model selected, no adapter written, `/analyze` routing
    unchanged** (`NO_VQA_SPECIALIST`) — unchanged from ADR-013, for the same
    reason (no measurement).
  - **The remote GPU box is now the one blocking action** for capability closure.
    Order once it exists: EXP-002 (+ EarthDial/GeoChat references) → integrate the
    winner → EXP-004 Run 2 → EXP-008 → EXP-C1 → then EXP-006 (agentic planning).
- **Consequence (doc + local eval + one additive service param; 97/97 tests, was
  92):** new `evaluation/scripts/{exp005_verifier_detection,exp003b_semantic_change_crops}.py`,
  `docs/deployment/REMOTE_GPU_SETUP.md`, `docs/research/{EXP-003,EXP-005,G6_CAPABILITY_CLOSURE}.md`,
  `packages/evidence/tests/test_exp005_verifier_detection.py`; `crop_strategy`
  param + 2 tests on `semantic_change_baseline.py` (default preserves behaviour);
  updated `EXP-002.md`, `EXP-004.md`, `EXP-008.md`, `CONFIDENCE_PLAN.md`,
  `MODEL_TOURNAMENT.md`, `EVIDENCE_LEDGER.md`, `CAPABILITY_GAP_MATRIX.md`,
  `PROJECT_STATUS.md`, `19_EXPERIMENT_REGISTRY.md`. No new deps, no new repos, no
  confidence value.

## ADR-013 — G5A A/B reproduction gate: local reproduction BLOCKED (6th artifact-acquisition failure) → remote reference gate OPEN; no production A/B model selected

- **Date:** 2026-09-01
- **Status:** Accepted
- **Context:** G5A froze the model hierarchy and ran the final A/B reproduction
  gate — resolve capability **A** (single-image VQA) and **B** (text-guided
  grounding) by *actually reproducing and measuring* RSCoVLM-3B / TinyRS-2B /
  Qwen2-VL-2B on the RTX 3050 Ti, against fixed RSVQA-LR + DIOR-RSVG samples and
  internal usability thresholds (VQA balanced-acc ≥ 0.60; grounding acc@IoU0.5 ≥
  0.30; ≤ 45 s/query). No new repos, no architecture change.
- **What ran:** one bounded weight-download attempt for **Qwen2-VL-2B-Instruct**
  (`Qwen/…` — a *different* HF namespace from the earlier TinyRS attempts),
  `snapshot_download`, `max_workers=2`, 8-minute bound.
- **Result — BLOCKED at three layers:**
  1. **Model weights (6th documented failure).** Config + `merges.txt` landed
     instantly; **both `model-0000?-of-00002.safetensors` shards stuck at 0 bytes**
     (`.incomplete` 0 B) for the entire window. Identical signature to the five
     prior TinyRS attempts (G2.5×2 `ChunkedEncodingError`, G3 DNS, G4 134 MB/4.4 GB,
     Audit 11/12 files) — on a different model from a different org → the blocker
     is this Windows host's network path to the HF CDN, not any one repo. RSCoVLM-3B
     (~6 GB, same infra) not attempted per the bounded-time rule (`docs/21`).
  2. **Evaluation datasets.** RSVQA-LR (Zenodo 3945396) and DIOR-RSVG (DIOR images
     ≈ 20 GB) are the same multi-GB download problem — not on disk.
  3. **Remote GPU.** Not available this session → the reference arm (EarthDial-4B,
     GeoChat-7B on the same frozen samples) could not run.
- **The three numbers stay separate (`docs/18`):** PAPER RESULT is recorded per
  model (attributed); **OUR REPRODUCTION / OUR MEASUREMENT / OUR INTEGRATED RESULT
  are all empty — because no artifact could be acquired, not because a model was
  measured and failed.** `EVIDENCE_LEDGER.md` shows A/B still at **DOCUMENTED**.
- **Decision:**
  - **Remote reference gate is OPEN.** On a Linux box with working bandwidth +
    GPU ≥ 16 GB: run the committed harness `evaluation/scripts/exp002_ab_gate.py`
    for RSCoVLM-3B / TinyRS-2B / Qwen2-VL-2B **and** the reference arm
    EarthDial-4B / GeoChat-7B on the identical frozen samples; record absolute +
    relative deltas; select the production A/B model on the 7 G5A criteria; write
    one adapter.
  - **No production A/B model is selected** and **no adapter is written** — doing
    either without a real run would be fabrication (`.claude/rules/ai-models.md`).
  - **`/analyze` routing is unchanged** — VQA/grounding still returns
    `NO_VQA_SPECIALIST` (never RemoteCLIP). It is wired to the winner only after
    G5A-remote produces one.
  - **Model discovery stops** (per the G5A brief) — the hierarchy is frozen.
- **Consequence (doc + eval-scaffold only; no product code, 92/92 tests
  unchanged):** new `evaluation/datasets/rsvqa_lr_sample.json`,
  `evaluation/datasets/dior_rsvg_sample.json` (frozen deterministic selection
  specs), `evaluation/scripts/exp002_ab_gate.py` (full measurement harness —
  compiles, `--resolve` reports `DATASET_MISSING` cleanly). Updated `EXP-002.md`
  (G5A section + three-numbers table + attempt log), `MODEL_TOURNAMENT.md`,
  `model_inventory.md`, `CAPABILITY_GAP_MATRIX.md`, `EVIDENCE_LEDGER.md`,
  `PROJECT_STATUS.md`, `19_EXPERIMENT_REGISTRY.md`.

## ADR-012 — Model hierarchy: role labels replace "ceiling"; EarthDial = primary high-capability reference (REFERENCE CANDIDATE), GeoChat demoted to secondary/historical

- **Date:** 2026-09-01
- **Status:** Accepted
- **Context:** After ADR-011 the single-image candidate set was revised but the
  docs still carried the conceptual label **"GeoChat = ceiling"**. "Ceiling"
  implies a *measured* upper bound; nothing here is reproduced, so the label
  overclaims. This ADR replaces the ad-hoc labels with an explicit **role
  hierarchy** and swaps the primary high-capability reference. **No new
  repositories. No core-architecture change.**
- **Decision — the model hierarchy (authoritative copy in
  `docs/research/MODEL_TOURNAMENT.md`):**

  | Role | Model | Repo | State |
  |------|-------|------|-------|
  | **LOCAL A/B PRIMARY** | **RSCoVLM-3B** | `VisionXLab/RSCoVLM` | DOCUMENTED — EXP-002 primary, run local @ 4-bit |
  | **LOCAL A/B FALLBACK** | **TinyRS-2B** | `aybora/TinyRS` | DOCUMENTED — weight download BLOCKED from this host |
  | **GENERIC CONTROL** | **Qwen2-VL-2B** | `QwenLM/Qwen2-VL` | runnable — value-of-RS-adaptation baseline |
  | **TEMPORAL** | **ChangeFormer** | `wgcban/ChangeFormer` | INTEGRATED (mask) — MEASURED IoU 0.83 / n=7 |
  | **OPTICAL-SAR PRIMARY** | **CROMA** | `antofuller/CROMA` | REPRODUCED — decide vs DOFA in EXP-004 Run 2 |
  | **OPTICAL-SAR CHALLENGER** | **DOFA** | `zhu-xlab/DOFA` | REPRODUCED |
  | **GROUNDING REFERENCE** | **GeoGround** | `VisionXLab/GeoGround` | DOCUMENTED — ~7B, remote |
  | **AUXILIARY** | **RemoteCLIP** | `ChenDelong1999/RemoteCLIP` | INTEGRATED — retrieval / zero-shot / embedding, **not VQA** |
  | **PRIMARY HIGH-CAPABILITY REFERENCE** | **EarthDial** | `hiyamdebary/EarthDial` | **REFERENCE CANDIDATE** — not reproduced |
  | **SECONDARY / HISTORICAL RS-VLM REFERENCE** | **GeoChat** | `mbzuai-oryx/GeoChat` | **secondary reference** — not on the critical path; local-run inability is **not** a project blocker |
  | **RESEARCH REFERENCE** | **SARLANG-1M** | `jimmyxichen/sarlang-1m` | dataset/benchmark — SAR-language eval + fine-tune data |

- **"Ceiling" retired.** Neither EarthDial nor GeoChat is a "ceiling" until it is
  **reproduced and measured** under our evaluation. Until then both are
  *references*.
- **EarthDial verification (no large artifacts downloaded):**
  - *Checkpoints:* **verified to exist** — HF `akshaydudhane/EarthDial_4B_{RGB,MS,Methane_UHI}`,
    Safetensors, BF16, `internvl_chat` arch, "4B params". HF pages show **"No model
    card"** (sparse).
  - *License:* repo footer = **MIT**; the HF checkpoint pages **assert no license**
    → code MIT, **weights licence unconfirmed** (treat as unconfirmed until stated).
  - *Hardware:* README = trained on "8 A100 GPUs with 80GB"; **inference VRAM not
    documented**. 4B BF16 ≈ 8–9 GB → does **not** fit the 4 GB laptop at bf16;
    4-bit ≈ 3–3.5 GB (undocumented, unverified).
  - *Environment:* Python 3.9, InternVL2 + Phi-3-Mini stack, `flash-attn==2.3.6`
    (training). torch / CUDA / `transformers` versions **not pinned** in the README.
  - *Inference path:* README points to a "demo section"; **exact entrypoint not
    quoted / not run**. `snapshot_download` example given for weights.
  - *Repo health:* 45 commits, 140 stars, CVPR 2025.
  - **Classification: REFERENCE CANDIDATE** until reproduced.
- **GeoChat:** retained as the **secondary / historical** RS-VLM reference. It is
  **not required** for the main SatQuery architecture, and its inability to run on
  the Windows 4 GB host is **explicitly not a project blocker** — the local A/B
  path (RSCoVLM-3B / TinyRS-2B) and EarthDial (remote, when a box exists) cover the
  capability.
- **Consequence:** doc-only. Updated `docs/research/MODEL_TOURNAMENT.md`,
  `docs/research/model_inventory.md`, `docs/research/CAPABILITY_GAP_MATRIX.md`,
  `docs/PROJECT_STATUS.md`, this file. `model_registry.yaml` already carries
  `earthdial_4b` / `geochat` in `excluded:` with statuses — role wording aligned.
  No code, no new deps, no new repos, no confidence value, no fabricated numbers.

## ADR-011 — Lightweight Model Replacement Audit: RSCoVLM-3B is the primary single-image arm; EarthDial-4B replaces TEOChat as the remote SAR/temporal VLM

- **Date:** 2026-09-01
- **Status:** Accepted
- **Context:** Audit — can the heavyweight critical-path RS-VLMs (GeoChat 7B,
  TEOChat 7B) be replaced by lighter, more reproducible models without losing
  mandatory SIH capability (single-image VQA / grounding / captioning, RS
  adaptation, 4 GB feasibility)? Scope-guarded: no architecture change, no new
  repos cloned, only five named candidates inspected (RSCoVLM, SkyEyeGPT,
  EarthDial, Qwen2-VL, ISRO-GeoNLI), compared vs TinyRS + GeoChat. Capabilities
  taken from released artifacts / model cards only — **not** paper titles. No
  bulk checkpoint downloads. Full write-up: `docs/research/LIGHTWEIGHT_AUDIT.md`.
- **Findings (all still #1 DOCUMENTED — no #2 reproduction produced):**
  - **RSCoVLM** (`Qingyun/rscovlm`, VisionXLab) — RS multi-task VLM (VQA +
    grounding + captioning), **MIT** code / CC-BY-4.0 data, released **3B** + 7B
    (card: "3B outperforms 7B"), active repo (~35 commits, arXiv 2511.21272).
    Fits 4 GB **only at 4-bit** (quantisation undocumented). → **primary** arm.
  - **EarthDial** (`akshaydudhane/EarthDial_4B_*`) — InternVL2 + Phi-3-Mini
    **4B**, **MIT code + weights**, natively adds **SAR + bi/multi-temporal +
    grounding + captioning**. Too heavy for 4 GB fp16. → replaces **TEOChat** as
    the first VLM to run on a remote box for the C/D-language arms (also lifts
    TEOChat's non-commercial-licence problem).
  - **Qwen2-VL-2B-Instruct** — Apache-2.0, native bbox grounding, runs anywhere
    at 4-bit. → the **generic control** (value-of-RS-adaptation baseline), not an
    RS answer.
  - **SkyEyeGPT** — ~7B, released weights but **no inference recipe** (README
    "coming soon"), licence unstated. → **BLOCKED**.
  - **ISRO-GeoNLI** — a FastAPI **wrapper** over Qwen3-VL + SAM3, 36 GB+ VRAM, no
    own checkpoint. → **REJECT** (reference architecture only; ≈ what `/analyze`
    already is).
  - **TinyRS-2B** — stays the **fallback** (smaller, surer 4 GB fit); weight
    download **BLOCKED** from this host (5th attempt in the audit: 11/12 files,
    the 4.4 GB shard again did not complete).
- **Decision:** revise the **EXP-002** candidate set — primary **RSCoVLM-3B**,
  fallback **TinyRS-2B**, control **Qwen2-VL-2B**, ceiling **GeoChat** (+
  **EarthDial-4B** on the remote box). Attempt the local **4-bit** RSCoVLM-3B /
  TinyRS-2B path *first* (one bounded download each) before renting a GPU — the
  blocker is download reliability, not compute. Nothing enters
  `model_registry.yaml` `models:` until a #2 reproduction clears the EXP-002
  threshold (VQA bal-acc ≥ 0.60, grounding acc@0.5 ≥ 0.30, CPU ≤ 45 s/query).
- **Consequence:** `docs/research/LIGHTWEIGHT_AUDIT.md` (new); `EXP-002.md`
  candidate set + attempt log updated; `model_registry.yaml` `excluded:` block
  rewritten with measured statuses (`rscovlm`, `earthdial_4b`, `qwen2_vl_2b`,
  `skyeyegpt`, `isro_geonli`; `rscovlm_3b` key renamed `rscovlm`). No code, no
  architecture change, no new repositories, no confidence value, no fabricated
  numbers.

## ADR-010 — G4: unified `POST /analyze`, composed semantic-change baseline; measurement backlog now needs a remote box

- **Date:** 2026-09-01
- **Status:** Accepted
- **Context:** G4 = one unified deterministic analysis layer + real capability
  proof. Experiments run in parallel.
- **Built (deterministic, local, 92 tests, no regressions):**
  - **`POST /analyze`** (`app.services.analyze` + `api/analyze.py`) — query →
    `interpret_query` (keyword→intent, **no LLM**) → input validation (safeguards
    preserved) → `satquery_core.routing.route()` → dispatch to
    `run_scene` / `run_change_slice` / `run_composed_semantic_change` /
    `run_joint_representation` → aggregate evidence + verification + provenance →
    `AnalyzeResult` with **observable routing info** (selected task, specialists,
    routing code + rule, required inputs, execution order, status). VQA →
    `NO_VQA_SPECIALIST` (never RemoteCLIP); bad pair → `VALIDATION_FAILED`.
  - **`COMPOSED_SEMANTIC_CHANGE_BASELINE`** — isolated, exact name, explicit
    "NOT a temporal VLM / NOT learned / NOT validated" disclaimer. ChangeFormer
    mask → `scipy.ndimage` components → per-region T2 crop → RemoteCLIP tagging →
    rule-assembled description. `failures[]` logs per-region failure cases. On the
    demo pair the tags are noisy on tiny crops — a **documented** failure mode,
    which is the point of a baseline.
  - **EXP-007** — `docs/research/EXP-007.md`, 15/15 geospatial safeguard cases
    pass. Safeguards were **not** weakened.
  - **`docs/research/CONFIDENCE_PLAN.md`** — candidate sources + the experiments
    (EXP-005, EXP-C1, EXP-C2) required before any confidence number. **No
    confidence is emitted anywhere.**
- **Blocked (STOP CONDITIONS hit — reported, not concealed):**
  - **EXP-002** — TinyRS weights failed a 4th download (`hf_transfer` + resume, 8
    min → 134 MB; < 1 MB/s, drops). RSCoVLM-3B not attempted (larger, same infra).
  - **EXP-004 Run 2** — no acquirable real S1+S2 set: DFC2020 `.pt` **11 GB**,
    So2Sat **7 GB**, EuroSAT-SAR **922 MB** (SAR-only). Run 1 stays *machinery
    validation only*.
  - **EXP-008** — depends on EXP-004 Run 2.
- **Decision:** **A remote Linux GPU box (≥ 16 GB, reliable bandwidth) is now
  justified** — on *infrastructure* grounds (multi-GB artifact acquisition +
  GPU for the 7B VLMs), not because local models were measured worse. It unblocks
  EXP-002 + EXP-004 Run 2 + EXP-008 + GeoChat/GeoGround together. The
  deterministic `/analyze` layer stands; the LLM planner and `/analyze`'s
  multimodal real-data path remain future work.
- **Consequence:** `apps/backend/app/api/analyze.py`, services `analyze.py` +
  `semantic_change_baseline.py`; new tests `test_analyze_api.py`,
  `test_semantic_change_baseline.py`, `test_exp007_geospatial_stress.py`; new docs
  `EXP-007.md`, `EXP-008.md`, `CONFIDENCE_PLAN.md`; `scipy` added to `.venvs/satquery`.
  No pipeline-architecture change, no rule change, no new repositories, no confidence.

## ADR-009 — G3: coherent system contracts — evidence, verification, router, `/scene`

- **Date:** 2026-09-01
- **Status:** Accepted
- **Context:** G3 = "move from isolated validated components to a real
  vertical-slice application with a clean internal contract", while research
  experiments continue in parallel.
- **Built (all deterministic, CPU-only, 59 tests, no regressions):**
  - **`packages/evidence`** — `EvidenceItem` (**no numeric confidence field, by
    design**), `Provenance.from_adapter()` + `scrub()` (secret-key masking),
    `verify(result, evidence, context) → VerificationResult` with statuses
    `SUPPORTED / CONTRADICTED / INSUFFICIENT_EVIDENCE / NOT_APPLICABLE`. Checks are
    **structural only** (input exists, modality supported, geospatial compat,
    artifact present, output shape/range) — explicitly *not* semantic correctness.
  - **`packages/core/routing`** — `RoutingRequest → RoutingDecision`, 6 ordered
    deterministic rules, capabilities read from `model_registry.yaml`. Rule 5
    (`NO_VQA_SPECIALIST`) is deliberately empty and honest. `docs/research/ROUTING_SPEC.md`.
    **No LLM.**
  - **`POST /scene`** — RemoteCLIP single-image slice (`app.services.scene_slice`),
    wired into `main.py`. Zero-shot ranking + evidence + provenance + verification.
    **Not a VQA endpoint** and the response says so.
  - **`/change` upgraded** — emits `evidence[]` + `verification` + a `standardized`
    provenance block; **all prior fields unchanged** (regression test pins
    changed_fraction 0.2526).
  - **Internal `run_joint_representation()`** — CROMA/DOFA joint-representation
    contract. **No `/fusion` endpoint** — representation-level only until EXP-004
    Run 2 shows a task benefit.
  - **`AdapterResult`** gained `status`, `timing_s`, `model_meta`; registry entries
    gained `fallback`. `docs/API_CONTRACT.md`, `docs/architecture/SPECIALIST_CONTRACT.md`.
- **Alternatives considered:** emit a confidence number from adapter scores
  (rejected — no calibration; `EvidenceItem` has no confidence field on purpose);
  build a `/fusion` endpoint now (rejected — contract not proven useful);
  make `verify()` attempt semantic checks (rejected — dishonest at this stage,
  the `notes` field says so).
- **Consequence:** `packages/evidence` + `packages/core/routing` are now real;
  `apps/backend/app/api/scene.py` + services `scene_slice.py`, `multimodal_slice.py`;
  `temporal_slice.py` extended. New docs: API_CONTRACT, SPECIALIST_CONTRACT,
  ROUTING_SPEC. No pipeline-architecture change, no rule change. Research status
  unchanged: EXP-002 artifact-blocked, EXP-004 Run 2 / EXP-008 pending a dataset.
  Remote GPU still not justified.

## ADR-008 — G2.5: standard SpecialistAdapter interface, 4 adapters, measured-facts registry, `POST /change` API

- **Date:** 2026-09-01
- **Status:** Accepted
- **Context:** G2.5 = "transform validated research components into the beginnings
  of a real SatQuery system." Tracks: adapters (4), registry, first API; plus
  EXP-002 / EXP-004 Run 2 / EXP-008.
- **Built:**
  - **`SpecialistAdapter` interface** (`packages/model_adapters/base.py`) — class
    facts (`name/version/source_repo/license/capabilities/modalities`) + the four
    methods `validate() / execute() / normalize_output() / provenance()` + a `run()`
    template. `_bridge.py` centralizes the subprocess plumbing.
  - **4 adapters** — ChangeFormer, RemoteCLIP, CROMA, DOFA — each `execute()`s a
    `scripts/research/*_infer.py` bridge inside its own `.venvs/<model>`; **no
    research-repo import in product code**. Smokes pass (RemoteCLIP → airport
    0.989; CROMA/DOFA → dim-768; ChangeFormer via the API path).
  - **`model_registry.yaml` v2** — measured facts per model (env, checkpoint size,
    latency, params, licence, `evidence_level`, `status`) + `ADAPTERS` map +
    `routing` table (rule-over-registry; VQA/grounding/semantic-change rows empty
    and honest).
  - **`POST /change`** (`apps/backend/app/api/change.py`, wired into `main.py`) —
    `{t1_path,t2_path}` → validate → co-reg gate → ChangeFormer adapter → mask →
    area/bbox/centroid → provenance → JSON. Path-traversal + 404 + 503 guards.
    `test_change_api.py`. **33/33 tests pass.**
  - **`docs/research/EVIDENCE_LEDGER.md`** — one row per model×claim at its highest
    real level.
- **Not completed (honest):**
  - **EXP-002** — TinyRS weights failed to download 3× (`ChunkedEncodingError`
    ×2, DNS fail ×1, hf_xet inconclusive) over ~50 min. **TEST FURTHER — blocked
    on artifact acquisition**, not capability/compute. RSCoVLM-3B not attempted
    (same HF infra, larger file).
  - **EXP-004 Run 2** — needs a small labelled S1+S2 set; the smallest preprocessed
    real option (`DFC_preprocessed.pt`) is 11 GB. Run 1 (synthetic sanity) stands.
  - **EXP-008** — gated on EXP-004 Run 2 picking an encoder.
- **Decisions:** subprocess-adapter pattern is the standard for every research
  model; the registry stores only measured facts; the co-reg gate is a hard
  precondition (`strict=True` default) in both the slice and the API; **no
  confidence value is emitted anywhere** until a method is chosen and calibrated;
  **remote GPU still not justified** — nothing this session needed it; **no new
  repositories, no agent, no polished frontend.**
- **Consequence:** new `.venvs/{satquery,tinyrs}`; `apps/backend/app/api/change.py`,
  `packages/model_adapters/{base,_bridge,changeformer,remoteclip,croma,dofa}.py`,
  3 new bridge scripts, tests. FastAPI ≥0.115 `include_router` is lazy — routes
  resolve via TestClient though `app.routes` shows `_IncludedRouter`.

## ADR-007 — G2: geospatial + temporal vertical slices; ChangeFormer adapter via subprocess; EXP-004 machinery validated on a synthetic control

- **Date:** 2026-09-01
- **Status:** Accepted
- **Context:** G2 called for controlled capability experiments (EXP-002, EXP-004)
  **and** the first vertical-slice integration, without building the agent, UI, or
  a confidence value.
- **What was built / measured:**
  - **Track C — geospatial slice:** `packages/geospatial/{raster,validation,errors}.py`
    — `validate_geotiff` (format, dims, CRS, transform, bounds, bands, NoData) and
    `check_pair_compatibility` (co-registration gate). 13 tests, synthetic rasters.
  - **Track D — temporal slice (real end-to-end):** `scripts/research/changeformer_infer.py`
    (research-env bridge) + a real `ChangeFormerAdapter` that **subprocesses** into
    `.venvs/changeformer` (product code never imports the research repo) +
    `apps/backend/app/services/temporal_slice.py` (`run_change_slice`). Path:
    T1/T2 GeoTIFF → validate → co-reg check → ChangeFormer → mask → area/bbox/centroid
    → `ChangeSliceResult` + provenance. Demo pair in `data/demo/temporal/`;
    changed_fraction 0.2526 matches G1 `demo_LEVIR.py`; misregistered pairs blocked.
    **No confidence value is produced** — `changed_fraction` is labelled as coverage.
  - **Track B — EXP-004 Run 1:** 3-arm frozen-feature linear probe (optical-only /
    CROMA `joint_GAP` / DOFA S2⊕S1) on a **synthetic** paired S1/S2 set with a
    controlled SAR-only signal (N=240/160, seed 20260901, CPU). SAR-only signal
    recovered by the fusion arms (1.00), at chance for optical-only (~0.49).
    **Explicitly a sanity check, not a benchmark** — no small labelled S1+S2 set is
    free (DFC2020 preprocessed = 11 GB).
  - **Track A — EXP-002:** `.venvs/tinyrs` + transformers 4.49 built; usability
    threshold fixed; TinyRS weight download hit repeated `ChunkedEncodingError` from
    HF — **N=0**.
- **Alternatives considered:** download DFC2020 (11 GB) now for a real EXP-004
  (rejected — over the "no large blind download" line for one session; Run 2 is a
  deliberate, named next step); vendor a ChangeFormer inference path into product
  code instead of subprocessing (rejected — `.claude/rules/ai-models.md` isolation);
  emit a confidence number from `changed_fraction` (rejected — it is coverage, not
  calibrated).
- **Decision:** Keep the subprocess-adapter pattern for all research models. The
  geospatial gate is a hard precondition for any paired analysis (`strict=True`
  default). EXP-004 stays PARTIAL until Run 2 on DFC2020/reBEN. EXP-002 stays
  RUNNING until the download completes and the threshold check runs. **Remote GPU
  still not justified** — nothing this session needed it.
- **Consequence:** new `.venvs/{satquery,tinyrs}`, `data/demo/temporal/`,
  `packages/geospatial/*`, `packages/model_adapters/{errors,changeformer}.py`,
  `scripts/research/changeformer_infer.py`, `apps/backend/app/services/temporal_slice.py`,
  tests. New docs `EXP-002.md`, `EXP-004.md`. No pipeline-architecture or rule change.
  Test-dir `__init__.py` files removed (pytest src-layout); `apps/backend/pyproject.toml`
  `readme` field dropped (hatchling rejected the `../../` path).

## ADR-006 — G1.6 model tournament: CROMA + DOFA reproduced; RS-MoE + ChangeChat rejected; first stack unchanged

- **Date:** 2026-09-01
- **Status:** Accepted
- **Context:** G1.6 validated the full 15-repo candidate pool from the brief
  (`docs/research/MODEL_TOURNAMENT.md`). Ran the smallest official example for each
  local-feasible candidate on the dev host (RTX 3050 Ti 4 GB, no conda/Docker/WSL).
- **Evidence:**
  - **CROMA** — REPRODUCED on CPU. `use_croma.py` official example: joint SAR+optical
    embeddings, correct shapes, finite. 194 M params, MIT, ~340 ms/sample,
    `pip install torch einops`, no source edits.
  - **DOFA** — REPRODUCED on CPU. `vit_base_patch16` + `DOFA_ViT_base_e100.pth`,
    `forward_features` for Sentinel-1 (2 ch) and Sentinel-2 (12 ch) via one
    wavelength-conditioned encoder. 111 M params, MIT, ~120 ms/sample,
    `timm==0.9.2`, no source edits.
  - **ChangeChat** — re-verified: still no released weights ("coming soon"); README
    now cites **≥48 GB VRAM** for training. **REJECT for now** stands.
  - **RS-MoE** — no released checkpoints, no inference script (training cfgs only),
    no license. **REJECT for now** (despite "VERY HIGH" brief priority — artifacts
    don't exist).
  - **TinyRS, RSCoVLM-3B** — DOCUMENTED, released weights, plausibly local (2–3 B,
    4-bit/CPU). Not run this session. **TEST FURTHER (local, EXP-002).**
  - **GeoGround, UniRS, LRS-VQA** — ~7 B, remote-GPU only. LRS-VQA also useful as a
    VQA *benchmark*. UniRS weights are non-commercial.
  - **SARLANG-1M** — a SAR-language dataset/benchmark, not a model. **KEEP FOR
    LATER** as SAR-language eval + fine-tune data.
- **Alternatives considered:** adopt CROMA now (rejected — `docs/18` needs a
  measured SAR delta first); pick CROMA vs DOFA now (rejected — decide in EXP-004);
  rent a GPU to run the 7 B VLMs now (rejected — every next high-value experiment is
  local; the remote-GPU gate in `EXPERIMENT_DECISION_TREE.md` is not yet met).
- **Decision:**
  1. **First stack unchanged:** RemoteCLIP + ChangeFormer, **+ CROMA pending
     EXP-004**. DOFA is CROMA's challenger in EXP-004. No model is adopted yet.
  2. **CROMA is the primary optical–SAR candidate** (native joint encoder → matches
     the PS "joint reasoning" wording); **DOFA the challenger** (lighter, flexible).
  3. VQA/grounding (A/B): **TinyRS + RSCoVLM-3B local bake-off (EXP-002)** before any
     remote GeoChat run.
  4. Repository pool is **closed** — no more hunting (brief rule).
  5. Remote GPU still **not provisioned**; gate = EXP-002 local arm fails the
     usability threshold.
- **Trade-off:** the optical–SAR and adaptation capabilities stay REPRODUCED (not
  MEASURED) until EXP-004/008; the single-image VQA path rests on two untested
  local candidates.
- **Consequence:** new docs `MODEL_TOURNAMENT.md`, `EXPERIMENT_DECISION_TREE.md`;
  updated `runtime_validation.md`, `model_inventory.md`, `CAPABILITY_GAP_MATRIX.md`,
  `docs/19` (EXP-002/003/004 concretized), PROJECT_STATUS. `.venvs/{croma,dofa}` +
  `models/cache/{croma,dofa}` added (gitignored). No pipeline-architecture change,
  no rule change.

## ADR-005 — G1.5 capability-gap closure: candidate shortlist, infra, and next experiment

- **Date:** 2026-09-01
- **Status:** Accepted
- **Context:** G1 left 8 mandatory PS capabilities partly uncovered
  (`docs/research/CAPABILITY_GAP_MATRIX.md`). Biggest: **D (optical–SAR) = NONE**
  and **E (RS adaptation) = NONE**; A (single-image VQA) is DOCUMENTED-only
  (GeoChat GPU-blocked); C has a mask but no semantic/language change; F/G/H are
  designed-only. Candidate scouting (web, 2026-09-01) surfaced current options.
- **Alternatives considered:** provision a GPU box now and reproduce GeoChat/TEOChat
  first (rejected — spends money/time before the free local experiments that close
  more gaps); adopt CROMA/TinyRS into the stack now (rejected — `docs/18` requires
  measurement first).
- **Decision:**
  1. **Candidate shortlist for evaluation only** (not adopted): **CROMA** (gap D,
     MIT, runs local) as the first optical–SAR candidate; **TinyRS** (gaps A/B,
     Apache-2.0, 2B, runs local 4-bit/CPU) as the first local VQA/grounding
     candidate; **TEOChat** (gap C, non-commercial, needs GPU) and **DOFA** (gap D
     alt) as secondary; **MaRS** as a watch-item (VHR ≠ our Sentinel scale;
     release unverified from here).
  2. **BigEarthNet v2 / reBEN** (Zenodo `10891137`, S1+S2, 19-class multilabel) is
     the adaptation source (req. E) — **subset only**.
  3. **Infrastructure:** one **cloud Linux GPU ≥16 GB** (24 ideal) unblocks
     GeoChat + TEOChat + (with conda) Change-Agent. **Do not provision it until
     EXP-004 + EXP-008 (local, free) are done.** CROMA/DOFA/TinyRS/adaptation run
     on the existing RTX 3050 Ti 4 GB.
  4. **Next experiment = EXP-004** — CROMA joint optical–SAR vs optical-only for
     built-up classification on a reBEN subset with a linear-probe head. It moves
     four mandatory gaps at once (D, E via EXP-008, first #3 number, H3) on
     hardware we already have.
- **Trade-off:** the single-image VQA path (A) leans on TinyRS (small, authors'
  numbers unverified) until a GPU box lets us reproduce GeoChat; deployment claims
  involving TEOChat are barred by its non-commercial licence.
- **Consequence:** `docs/19` EXP-004 concretized + EXP-008 added; `model_inventory.md`
  now tracks DOCUMENTED/REPRODUCED/MEASURED/INTEGRATED separately (INTEGRATED = 0);
  PROJECT_STATUS NEXT-3 reordered to EXP-004 → adapters → TinyRS. No change to the
  pipeline architecture (ADR-001) or any rule. Implementation starts only after
  this matrix is reviewed.

## ADR-004 — First SatQuery specialist stack = RemoteCLIP + ChangeFormer (from G1 evidence)

- **Date:** 2026-09-01
- **Status:** Accepted (revisit when a GPU box exists — `docs/28`/open-mindedness rule)
- **Context:** G1 runtime validation (`docs/research/runtime_validation.md`) ran the
  smallest official inference example for each of the 5 candidate repos on the dev
  host (Windows 11, RTX 3050 Ti **4 GB**, no conda/Docker/WSL).
  - **RemoteCLIP** — RUNNING. Pure pip, CPU, Apache-2.0, official zero-shot example
    correct (97.8% airport), ~150 ms/query, ~1.6 GB RSS. Integration cost LOW.
  - **ChangeFormer** — RUNNING with **no source edits**, env pins only
    (`numpy<1.24` for removed `np.str`; `torch<2.6` for its `torch.load`). MIT,
    `demo_LEVIR.py` exit 0, change-IoU 0.83 / F1 0.91 on 7 bundled labelled
    samples (reproduction, n=7), 41 M params, ~790 ms/pair CPU. Cost LOW–MEDIUM.
  - **GeoChat** — BLOCKED. 7B merged model > 4 GB VRAM (even 4-bit ≈5–6 GB);
    `deepspeed==0.9.5` fails to build on Windows; `bitsandbytes==0.41.0` Linux-only.
  - **Change-Agent** — BLOCKED. `mmcv==1.3.1` unbuildable (no wheels; ancient
    setup.py; needs CUDA toolkit + MSVC); internal `transformers` 4.33 vs ≥4.34.
  - **ChangeChat** — BLOCKED. No released weights, no `requirements.txt`.
- **Alternatives considered:** (a) block all SatQuery progress on a GPU box —
  rejected, RemoteCLIP + ChangeFormer already cover V0 + the V1 change path;
  (b) port ChangeFormer / build mmcv now — rejected, environment cost with no
  measured payoff yet (scope rule); (c) drop change detection until GeoChat is
  available — rejected, ChangeFormer is the stronger evidence today.
- **Decision:** The **first specialist stack is RemoteCLIP + ChangeFormer.**
  Write their adapters next (they are the only two with a proven runnable path).
  GeoChat integration is **gated on provisioning a Linux GPU ≥16 GB** and blocks
  EXP-001 until then; use a small CPU-runnable control VLM for EXP-001 in the
  interim where the task allows. Change-Agent stays a TEST-FURTHER item for
  EXP-003 on Linux+conda. ChangeChat is **rejected for now**.
- **Trade-off:** No single-image VQA/grounding capability in the local prototype
  until a GPU is available — the demo's single-image path leans on RemoteCLIP
  (retrieval/zero-shot) rather than free-form VQA at first.
- **Consequence:** `.venvs/remoteclip` and `.venvs/changeformer` are the reference
  environments (gitignored); checkpoints in `models/cache/` (gitignored).
  `model_registry.yaml` capability entries to be updated with the measured facts.
  This does **not** change the pipeline architecture (ADR-001) or any rule.

## ADR-003 — `chatgpt.context.md` as persistent strategic memory; `docs/PROJECT_STATUS.md` as living status

- **Date:** 2026-08-31
- **Status:** Accepted
- **Context:** Strategy, SIH evaluation criteria, the winning objective, model
  candidates, experiment plan, red-team questions and jury lenses were living in
  chat history and would be lost between sessions. Claude needs a fixed place to
  read strategic intent and a fixed place to record honest project state.
- **Alternatives considered:** (a) keep it only in `CLAUDE.md` — too long, mixes
  operating rules with strategy; (b) split across the numbered docs — dilutes the
  "read this first" signal; (c) a Claude-memory file only — not visible to the
  team or in the repo.
- **Decision:** Commit `chatgpt.context.md` at the repo root as canonical,
  non-disposable strategic memory (synced with reality, esp. §33). Add
  `docs/PROJECT_STATUS.md` as the living status file (DONE / IN PROGRESS / BLOCKED
  / MISSING / RESEARCH NEEDED / METRICS / RISKS / NEXT 3 ACTIONS / WIN SCORECARD),
  updated every significant session. Wire both into `CLAUDE.md` "Read first",
  `docs/21`, and the `documentation` rule.
- **Trade-off:** Two more files to keep current; drift is a real risk if sessions
  skip the end-of-session update.
- **Consequence:** `chatgpt.context.md` §11 experiments are the seed for
  `docs/19_EXPERIMENT_REGISTRY.md`; §21 structure matches ADR-001; §24 defines the
  status schema now implemented. The three-numbers rule (doc 18) is echoed in
  context §10/§16.

## ADR-002 — Research repos isolated in `external/research/`, never merged

- **Date:** 2026-08-31
- **Status:** Accepted
- **Context:** Six upstream repos (GeoChat, Change-Agent, ChangeChat, ChangeFormer,
  RemoteCLIP, awesome-rs-vlms) are needed as references. Their environments
  mutually conflict — Python 3.8–3.10, PyTorch 1.10 vs 2.0, CUDA 10.2 vs 11.8,
  `transformers` 4.31/4.33/≥4.34, an OpenMMLab 1.x stack, `pydantic<2` via
  `gradio==3.35.2` — and every one conflicts with SatQuery's Python 3.11 /
  Pydantic v2 product environment. Details in `docs/research/`.
- **Decision:** Clone them (shallow, pinned commits) into `external/research/`,
  which is **gitignored and read-only**. Do not install their deps into the main
  environment; do not merge requirements. Each model gets its own isolated env or
  container (`docs/research/environment_strategy.md`). Product code never imports
  from `external/research/`; future integration goes through
  `packages/model_adapters/` invoking an isolated env by subprocess.
- **Consequences:** Reproducible references without dependency hell. Re-clone via
  `make clone-research`. Integration cost per model is one env/container + one
  adapter. `awesome-rs-vlms` is literature only. Checkpoints/datasets deferred.

## ADR-001 — Monorepo split: apps/ + packages/

- **Date:** 2026-08-31
- **Status:** Accepted
- **Context:** The initial scaffold put everything under `backend/` (with an inner
  `satquery/` package) and `frontend/`, `models/`, `research/`, `infra/`. As the
  pipeline stages, the geospatial engine, the adapter layer and the evidence
  system grow, they need independent test/lint/versioning and clear dependency
  directions; a single backend package blurs that.
- **Decision:** Adopt a monorepo: `apps/{backend,frontend}` for deployables and
  `packages/{core,geospatial,agents,evidence,model_adapters}` as installable
  src-layout packages. Move `backend/satquery/<stage>` into the matching package,
  `models/adapters` → `packages/model_adapters`, `research/` → `external/research`,
  `infra/` → `infrastructure/`. Pipeline stage order and all `.claude/rules/` are
  unchanged; only the file locations move. Package deps are one-way (no cycles):
  `core` ← `agents`, `evidence`; `geospatial`, `model_adapters` standalone;
  `apps/backend` depends on all.
- **Consequences:** Per-package `pyproject.toml`, editable installs via
  `make setup-packages`. Docker build context is the repo root. Import paths
  change (`satquery.routing` → `satquery_core.routing`, `models.adapters.geochat`
  → `satquery_model_adapters.geochat`). CLAUDE.md, `architecture` rule and the
  `satquery-architecture` skill updated to match.

## ADR-000 — Template

- **Date:** YYYY-MM-DD
- **Status:** Proposed | Accepted | Superseded by ADR-XXX
- **Context:** _What forces are at play?_
- **Decision:** _What did we choose?_
- **Consequences:** _Trade-offs, follow-ups._
