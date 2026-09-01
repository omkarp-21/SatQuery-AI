# G6 — Capability Closure status

> Date: **2026-09-01**. G6 = "stop searching for models, acquire evidence,
> measure, select, integrate." This file scores the current state against the G6
> exit criteria and says exactly what is done, what ran, and what is blocked
> **only** on the remote GPU box (`docs/deployment/REMOTE_GPU_SETUP.md`).
>
> Commit baseline: 275cd09 (G5A). No new repositories. No architecture change. No
> polished frontend. No fabricated metrics. No confidence number.

## What G6 actually executed (local, real)

| Phase | Ran? | Result |
|-------|------|--------|
| **1. Remote lab** | provisioning **NOT done** (needs a cloud account) | `docs/deployment/REMOTE_GPU_SETUP.md` — turnkey runbook + sizing + acquisition + run commands; every box value `<PENDING>` |
| **2. EXP-002 final** | ✘ BLOCKED | 6th artifact-acquisition failure stands (G5A). Harness + frozen samples committed and dry-run-clean. |
| **3. Model selection** | ✘ not possible | no measurement → no winner |
| **4. Integrate winner** | ✘ not possible | would be fabrication; `/analyze` routing unchanged (`NO_VQA_SPECIALIST`, never RemoteCLIP) |
| **5. EXP-004 Run 2** | ✘ BLOCKED | **smallest valid dataset chosen** — DFC2020 `ROIs0000_validation` raw, ≈1.5–2 GB, 400/200 subsample (`EXP-004.md`). Acquisition needs the box. |
| **6. EXP-008** | ✘ BLOCKED (on 5) | method definitions locked (linear probe ≠ LoRA ≠ fine-tune), hyperparameter record spec written (`EXP-008.md`) |
| **7. Semantic-change crops** | ✔ **RAN** | `crop_strategy` ∈ {tight, expanded, mask_aware} added to the composed baseline; 3-way run on the demo pair: **agreement 4/6 regions**; `expanded`/`mask_aware` rescued a `tight` miss; `mask_aware` monoculture risk logged. `EXP-003.md` §EXP-003b. Not a learned VLM. |
| **8. EXP-005 verifier** | ✔ **RAN** | structural-defect detection **P/R/F1 = 1.00** on a curated n=24 corpus; **semantic-defect miss rate = 1.00**. Semantic-verifier extension points documented. `EXP-005.md`. 3 lock tests. |
| **9. Confidence** | ✔ doc only | `CONFIDENCE_PLAN.md`: EXP-C1 (calibration) + EXP-C2 (disagreement) fully specified; both blocked on the same artifacts as EXP-002 / EXP-004 Run 2. **No number emitted.** |
| **10. Status** | ✔ | this file + the 8 docs listed in the brief updated; ADR-014 |

**Tests: 97 passed, 0 failed** (was 92; +3 EXP-005, +2 crop-strategy). No test weakened.

## G6 exit criteria — scored

| Crit. | Target | Actual | Met? |
|-------|--------|--------|------|
| **A** | VQA = MEASURED | DOCUMENTED — reproduction blocked on artifact acquisition (6 attempts); harness + frozen RSVQA-LR sample ready | ✘ (blocked, not failed) |
| **B** | grounding OR captioning = MEASURED | DOCUMENTED — same block; frozen DIOR-RSVG sample ready; grounding is the chosen B task | ✘ (blocked) |
| **C** | mask = INTEGRATED + MEASURED; semantic = experimental baseline | mask **INTEGRATED + MEASURED** (ChangeFormer IoU 0.83 / F1 0.91, n=7); semantic = **experimental composed baseline**, now with a measured crop-strategy comparison (EXP-003b) | ✔ |
| **D** | real optical-SAR task = MEASURED | REPRODUCED (encoders) + Run-1 synthetic sanity only; Run 2 blocked, smallest dataset chosen | ✘ (blocked) |
| **E** | adaptation = MEASURED before/after | NONE — blocked on D; method definitions locked | ✘ (blocked) |
| **F** | deterministic routing = INTEGRATED; LLM planning deferred | deterministic router **INTEGRATED** in `/analyze` (8 tests); LLM planning **deferred** | ✔ |
| **G** | geospatial validation = VALIDATED structural | **VALIDATED (structural)** — EXP-007 15/15; live in 3 endpoints | ✔ |
| **H** | evidence+provenance INTEGRATED; structural verification VALIDATED; semantic experimental; confidence only after calibration | evidence + provenance **INTEGRATED**; structural verifier now **MEASURED** (EXP-005, P/R/F1=1.00) → **VALIDATED (structural)**; semantic verification = **experimental / extension points only**; confidence = **none** (EXP-C1/C2 specified, blocked) | ✔ |

**4 / 8 criteria met (C, F, G, H). 4 blocked (A, B, D, E) — every one solely on
artifact/dataset acquisition, i.e. the remote GPU box.** No criterion is blocked
by a capability gap, a design problem, or a measured model failure.

## The single remaining blocker

**One Linux GPU box with working bandwidth.** It unblocks A, B (EXP-002 +
references), D (EXP-004 Run 2), E (EXP-008), and the confidence experiments
(EXP-C1/C2) — in that order, all with committed or specified harnesses. The dev
host has failed 6 multi-GB downloads across 2 HF namespaces; this is not
retryable from here.

## After the box: definition of "capability-closed"

A, B MEASURED → one adapter INTEGRATED → `/analyze` routes VQA/grounding to it →
D MEASURED (CROMA vs DOFA decided) → E MEASURED (before/after) → EXP-C1 run →
*then* build the agentic `/analyze` planning layer (EXP-006) on top of a closed
capability set.
