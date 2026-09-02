# SatQuery Experiment Registry

> Status: **Active — binding** · Owner: _TBD_ · Last updated: 2026-09-01
> No experiment has a **benchmark** result yet. EXP-004 Run 1 is a *synthetic
> sanity check* (labelled as such); ChangeFormer's IoU 0.83 (n=7) is a
> *reproduction sanity*, not a benchmark. Results are filled only from real runs
> (see [`18_RESEARCH_TO_ACCURACY.md`](18_RESEARCH_TO_ACCURACY.md)). Do not invent numbers.
> The canonical set of seven experiments is defined in `chatgpt.context.md` §11.

## Why this file exists

Without a registry, model trials happen off the record and we keep rediscovering
the same things. This file is the scientific history of SatQuery: what we asked,
what we measured, what we decided.

## Rules

- One experiment = one ID (`EXP-NNN`), allocated in order, never reused.
- An experiment must exist **before** the work starts, in status `PLANNED`.
- Every hypothesis in doc 18 (H1–H5) maps to at least one experiment. Some
  experiments are **selection bake-offs** (no hypothesis) — that is fine.
- The **three numbers** stay separate (paper / reproduction / SatQuery). State
  which one each result is.
- Every finished experiment ends with a `DECISION: KEEP | REJECT | INVESTIGATE`.
- Link the experiment from the PR and from the `evaluation/cases/` entry it uses.

## Status lifecycle

`PLANNED → RUNNING → MEASURED → DECIDED` (or `BLOCKED`, with reason).

## Entry schema

```
## EXP-NNN — <short title>
- Status: PLANNED | RUNNING | MEASURED | DECIDED | BLOCKED
- Hypothesis: H# (or "n/a — selection")
- Question: <the one question this answers>
- Owner: <name>              Date: <start> → <end>
- Models / methods: <exact repos, checkpoints, commits, configs>
- Dataset: <source, license, region, sensor>   Split: <train/val/test, leakage check>
- Metric: <precise definition>
- Preprocessing: <steps>      Inference config: <params, seed>
- Hardware: <GPU/CPU, VRAM, batch>
- Baseline: <what, and its measured value — number type: reproduction/SatQuery>
- Result: <measured value — number type>   Δ vs baseline: <with n, seed>
- Failure cases: <concrete inputs where it breaks>
- Notes / threats to validity:
- DECISION: KEEP | REJECT | INVESTIGATE — <one line why>
- Artifacts: evaluation/reports/EXP-NNN/... ; evaluation/cases/... ; PR #
```

---

## EXP-001 — Generic VLM vs RS-adapted VLM

- Status: PLANNED
- Hypothesis: H1
- Question: Does a remote-sensing-adapted VLM outperform a generic VLM on RS VQA
  and visual grounding?
- Models / methods: GeoChat (`external/research/GeoChat`, released checkpoint) vs a
  generic open VLM baseline (TBD — e.g. LLaVA-1.5-7B, same size class).
- Dataset: TBD held-out RS VQA + grounding set (candidates: RSVQA-LR/HR, VRSBench,
  DIOR-RSVG subset). License and region to be recorded.
- Split: held-out test only; check no overlap with GeoChat instruction data.
- Metric: VQA exact-match / accuracy; grounding acc@IoU0.5.
- Baseline: the generic VLM (our reproduction number).
- Result: _not measured_.
- Failure cases: _tbd_.
- DECISION: _pending_.

## EXP-002 — Candidate single-image RS-VLM comparison

- Status: **DONE (G11, 2026-09-02) — A + B both MEASURED + INTEGRATED.**
  `HF_HUB_ENABLE_HF_TRANSFER=1` pulled TinyRS-2B + Qwen2-VL-2B + RemoteSAM weights
  (previously failed 7×); non-gated HF mirrors found for both eval sets.
  **A (VQA):** TinyRS-2B **balanced acc 0.8736** on 40 RSVQA-LR yes/no (CPU,
  p50 4.45 s) → PRIMARY; Qwen2-VL-2B control 0.7033 → FALLBACK. **RSCoVLM-3B does
  not exist** (only 7B released). **B (grounding):** RemoteSAM **acc@IoU0.5 = 0.84
  (21/25)** on frozen DIOR-RSVG (CPU, p50 29 s). Both integrated: `TinyRsAdapter`
  + `RemoteSamAdapter`, `/analyze` `SINGLE_IMAGE_VQA` / `SINGLE_IMAGE_GROUNDING`.
  `docs/research/EXP-002.md` §G11, `EXP-GROUNDING.md`, ADR-020. Reports:
  `evaluation/reports/exp002_vqa_*.json`, `exp_grounding_dior_*.json`.
  Open: larger samples (n=40/25 are sanity-scale) + GPU/4 GB-VRAM verification.
  _Earlier (G5A): BLOCKED on artifact acquisition, 6 download failures (ADR-013)._
- Hypothesis: n/a — selection bake-off
- Question: Among candidate single-image RS-VLMs, which gives the best
  accuracy / latency / integration-cost trade-off for SatQuery's single-image path?
- Models / methods (**revised by the Lightweight Model Replacement Audit,
  2026-09-01 — `docs/research/LIGHTWEIGHT_AUDIT.md`, ADR-011**):
  **PRIMARY = RSCoVLM-3B** (`Qingyun/rscovlm`, Qwen2.5-VL-3B, MIT code / CC-BY-4.0
  data — RS multi-task VQA + grounding + captioning; 4 GB only at 4-bit).
  **FALLBACK = TinyRS-2B** (`aybora/Qwen2-VL-TinyRS`, Apache-2.0; surer 4 GB fit;
  download BLOCKED). **CONTROL = Qwen2-VL-2B-Instruct** (Apache-2.0, generic,
  native bbox grounding — value-of-RS-adaptation baseline). **CEILING = GeoChat**
  (+ **EarthDial-4B**, `akshaydudhane/EarthDial_4B_*`, MIT code+weights, +SAR
  +temporal) on a rented GPU ≥16 GB. **Rejected:** SkyEyeGPT (no inference recipe),
  ISRO-GeoNLI (wrapper, 36 GB), RS-MoE (no weights). RemoteCLIP zero-shot as the
  scene-classification reference.
- Dataset: an **RSVQA-LR** sample for VQA; a **DIOR-RSVG** sample for grounding
  (capability B). Held-out; check overlap with each model's instruction data.
- Metric: VQA accuracy; grounding acc@IoU0.5; measured p50/p95 latency (4-bit CPU
  vs GPU); integration-cost note. **Define a "usable" threshold before running**
  (`EXPERIMENT_DECISION_TREE.md`).
- Baseline: whichever candidate is wired first (its reproduction number).
- Result: _not measured_.
- Notes: compare each model only on tasks it supports; picks the model for **A + B**.
- DECISION: _pending_ — KEEP one local VLM, or trigger the remote-GPU gate.

## EXP-003 — Temporal stack: Change-Agent vs ChangeChat vs ChangeFormer

- Status: PLANNED
- Hypothesis: n/a — selection bake-off (informs H2)
- Question: Which temporal stack gives the best combination of change-mask quality,
  semantic change interpretation, speed, and integration stability?
- Models / methods (G1.6): **Arm 1 (local, first):** ChangeFormer mask → connected
  components → caption each region with the EXP-002 single-image VLM → rule-assemble
  a change description. **Arm 2 (remote ceilings):** Change-Agent `MCI_model.pth`
  (Linux+conda), TEOChat, UniRS — only if Arm 1 underperforms. ChangeChat
  **excluded** (no weights; README now ≥48 GB to train).
- Dataset: LEVIR-CD (mask) + **LEVIR-MCI / LEVIR-CC** (mask + caption) sample.
- Metric: change-mask IoU / F1; change-caption BLEU-4 / CIDEr / METEOR; change-QA
  accuracy where available; p50/p95 latency; stability note.
- Baseline: image-difference + threshold (mask); a rule-only captioner.
- Result: _not measured_.
- Notes: ChangeFormer already MEASURED as the mask worker (IoU 0.83 / n=7).
- DECISION: _pending_ — keep ChangeFormer + a chosen semantic/language layer.

## EXP-004 — Optical-only vs optical + SAR  ⭐ (G1.5, ADR-005)

- Status: **Run 1 done (synthetic sanity, NOT a benchmark); Run 2 BLOCKED**
  (`docs/research/EXP-004.md`). Run 1: 3-arm frozen-feature linear probe on real
  CROMA + DOFA — SAR-only signal recovered by fusion (1.00) vs chance for
  optical-only (~0.49); machinery + directional H3 only. **Run 2 blocker (G4):** no
  acquirable real S1+S2 set from this host — DFC `.pt` **11 GB**, So2Sat **7 GB**,
  EuroSAT-SAR **922 MB** (SAR-only). Needs a better-connected machine.
- Hypothesis: H3
- Question: For suitable queries (built-up / informal-settlement classification),
  does a **joint optical+SAR** representation improve the result vs optical-only?
- Models / methods (G1.6 — both encoders **REPRODUCED** on CPU): 3 arms, same
  linear-probe head, same split, same budget —
  (1) **optical-only** (CROMA `optical_GAP` or RemoteCLIP image features);
  (2) **CROMA** `joint_GAP` (native joint radar-optical);
  (3) **DOFA** S1⊕S2 features concatenated (downstream fusion).
  All run on the 4 GB laptop / CPU — no GPU box.
- Dataset: a **fixed, recorded subset** of reBEN / BigEarthNet v2 (Zenodo
  `10891137`) — paired Sentinel-1 (VV/VH, dB) + Sentinel-2 (12-band), held-out
  split, leakage-checked. **Subset only** (a few k patches), not the full 549 k.
- Preprocessing: CROMA's channel norm; S1 in dB; 120×120 tiling; record CRS/GSD.
- Metric: per-class F1 / mAP for built-up + 2–3 other classes; **explicitly report
  where SAR hurt**. p50 latency of the joint encoder.
- Baseline: optical-only head (its reproduction number).
- Result: _not measured_.
- Notes: also produces the adaptation evidence for requirement E — the probe head
  IS a bounded BigEarthNet adaptation (see EXP-008, shares this pipeline).
- DECISION: _pending_ — KEEP the better of CROMA/DOFA for the SAR path, or, if the
  SAR delta ≈ 0, INVESTIGATE preprocessing then re-measure (`EXPERIMENT_DECISION_TREE.md`).

## EXP-008 — RS adaptation probe on BigEarthNet v2 (requirement E)

- Status: PLANNED (shares infrastructure with EXP-004)
- Hypothesis: n/a — mandatory-capability evidence (PS §Adaptation)
- Question: Does a bounded adaptation (linear probe → LoRA) of a frozen RS encoder
  on a BigEarthNet-v2 subset measurably improve multilabel classification, and is a
  linear/LoRA probe *sufficient* to satisfy the PS adaptation requirement?
- Models / methods: frozen CROMA (or RemoteCLIP) encoder + (a) linear probe vs
  (b) LoRA-adapted, same reBEN subset + split as EXP-004.
- Metric: multilabel micro-F1 / mAP **before → after**, with n, seed, hardware, date.
- Baseline: frozen encoder + linear probe.
- Result: _not measured_.
- Notes: keep it a bounded probe — no full fine-tuning (`.claude/rules/scope.md`).
  Record exactly which patches.
- DECISION: _pending_.

## EXP-005 — Structural verifier detection

- Status: **RUN — structural part done (2026-09-01, G6). `docs/research/EXP-005.md`.**
- Hypothesis: H4
- Question: Does `verify()` detect structural defects, and what does it miss?
- Method: 24-case curated corpus (CLEAN 6 / STRUCTURAL 8 / SEMANTIC 6 /
  INSUFFICIENT 4) exercising every rule in `verifier.py`.
  `evaluation/scripts/exp005_verifier_detection.py` + 3 lock tests.
- Result: **structural-defect detection precision / recall / F1 = 1.00**
  (TP 8, FP 0, TN 12, FN 0; 4 INSUFFICIENT correct). **Semantic-defect miss rate
  = 1.00** (0/6 structurally-clean-but-wrong cases flagged) — by design.
- **EXP-005b (G7): model-independent semantic verifier built + measured.**
  `verify_semantic()` — 6 checks (claim↔number, claim↔label, temporal direction,
  region geometry, whole-scene region, area arithmetic). Curated n=34 corpus →
  **P/R/F1 = 1.00** for internal-incoherence detection (TP 10/FP 0/TN 14/FN 0);
  **BEYOND_SCOPE residual miss rate 1.00** (label-correctness needs a second
  model). INTEGRATED into `COMPOSED_SEMANTIC_CHANGE_BASELINE`.
  `evaluation/scripts/exp005b_semantic_verifier.py` + 9 lock tests.
- DECISION: structural verifier = **VALIDATED (structural)**; semantic verifier =
  **MEASURED + INTEGRATED (experimental, model-independent subset)**. Remaining:
  `independent_model_agreement` + `optical_sar_agreement` (EXP-002 / EXP-C2).
  Confidence: EXP-C1/C2 specified in `CONFIDENCE_PLAN.md`, blocked on a scored model.
- Caveat: both corpora are n≈30, author-curated → prove the checks fire on their
  target defect classes, **not** a real-world coverage rate. Grow with real
  `/analyze` failures before quoting outside `EXP-005.md`.

## EXP-006 — LLM-only routing vs constrained deterministic/agentic routing

- Status: PLANNED (deferred until the capability stack is frozen).
- **Substrate ready (G8):** deterministic router INTEGRATED + **failure-aware
  routing INTEGRATED** — `derive_resolution()` (6 post-execution qualifiers,
  pure fn of `verify()` + `verify_semantic()` + sub status) + single-step
  `image_difference_fallback`. `docs/research/FAILURE_AWARE_ROUTING.md`. The LLM
  intent step (mode b) plugs in on top of this.
- Hypothesis: H2
- Question: Does structured (rule-over-registry) routing improve correct tool
  selection and reduce invalid execution vs letting an LLM freely choose tools?
- Models / methods: `packages/agents` routing stage in two modes — (a) LLM proposes
  the whole plan with no schema constraint; (b) LLM only disambiguates intent, then
  rules over `model_registry.yaml` capabilities build the plan (the design in the
  `agent-orchestration` skill).
- Dataset: a labelled set of queries + input bundles with a **known correct**
  task / modality / specialist selection, in `evaluation/cases/`.
- Metric: routing accuracy (correct specialist + task); rate of invalid executions
  (unsupported task/modality reaching a model); plan reproducibility across repeats.
- Baseline: mode (a), LLM-only.
- Result: _not measured_.
- DECISION: _pending_.

## EXP-007 — Geospatial validation ON vs OFF

- Status: PLANNED
- Hypothesis: H5
- Question: Does the geospatial integrity layer (CRS check, co-registration
  assertion, GSD check, NoData handling) measurably reduce invalid analyses and
  spatial-reasoning failures?
- Models / methods: `packages/geospatial` validation gate on vs off, feeding the
  EXP-003 / EXP-004 pipelines.
- Dataset: a stress set of deliberately mismatched pairs (different CRS, sub-pixel
  and gross offset, different GSD, missing NoData) mixed with valid pairs.
- Metric: fraction of invalid pairs correctly rejected; downstream change-metric
  error with vs without the gate; count of fake "change" from misregistration.
- Baseline: gate disabled.
- Result: _not measured_.
- DECISION: _pending_.

---

## Index

| ID | Focus | Hypothesis | Status | Decision |
|----|-------|-----------|--------|----------|
| EXP-001 | generic vs RS-adapted VLM | H1 | PLANNED (blocked on GPU box) | — |
| EXP-002 | single-image VLM A/B gate — **RSCoVLM-3B** primary / TinyRS-2B fallback / Qwen2-VL-2B control (local); EarthDial-4B + GeoChat-7B reference (remote) | selection | **BLOCKED** — G5A ran the gate; weights unfetchable (**6 dl attempts**, fresh org same failure); RSVQA-LR/DIOR-RSVG unfetchable; **remote reference gate OPEN (ADR-013)**; harness + frozen samples committed | — |
| EXP-003 | temporal-language — composed baseline vs remote VLMs (a); crop strategy (b) | selection (→H2) | **EXP-003b RUN** (crop strategy: agreement 4/6, `expanded` provisional); EXP-003a BLOCKED (remote) | `EXP-003.md` |
| **EXP-004** | **optical vs optical+SAR — CROMA vs DOFA** | **H3** | Run 1 (synthetic sanity) done; **Run 2 BLOCKED** — no acquirable S1+S2 set | — |
| EXP-005 | verifier detection — structural (a) + model-independent semantic (b) | H4 | **RUN** — 005a structural P/R/F1 = 1.00 (n=24); 005b semantic P/R/F1 = 1.00 (n=34), INTEGRATED; label-correctness gap remains | `EXP-005.md` |
| EXP-006 | LLM vs constrained routing | H2 | PLANNED (needs ≥2 adapters) | — |
| EXP-007 | geospatial safeguard stress test | H5 | **RUN — 15/15 pass** (`EXP-007.md`) | KEEP the gate |
| EXP-008 | RS adaptation probe (req. E) | n/a | **BLOCKED** on EXP-004 Run 2 | — |

Hypothesis coverage: H1→EXP-001, H2→EXP-006 (informed by EXP-003), H3→EXP-004,
H4→EXP-005, H5→EXP-007. Mandatory-capability coverage without a hypothesis:
req. E → EXP-008.
