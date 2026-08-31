# SatQuery Experiment Registry

> Status: **Active — binding** · Owner: _TBD_ · Last updated: 2026-08-31
> Every experiment gets an ID. Nothing here is measured yet — all entries are
> **PLANNED**. Results are filled in only from real runs (see
> [`18_RESEARCH_TO_ACCURACY.md`](18_RESEARCH_TO_ACCURACY.md) and
> `docs/11_EVALUATION_PLAN.md`). Do not invent numbers.

## Why this file exists

Without a registry, model trials happen off the record and we keep rediscovering
the same things. This file is the scientific history of SatQuery: what we asked,
what we measured, what we decided.

## Rules

- One experiment = one ID (`EXP-NNN`), allocated in order, never reused.
- An experiment must exist **before** the work starts, in status `PLANNED`.
- Every hypothesis in doc 18 (H1–H5) maps to at least one experiment.
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
- Hypothesis: H# (or "n/a")
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

## EXP-001 — RS-adapted VLM vs generic VLM

- Status: PLANNED
- Hypothesis: H1
- Question: Does a remote-sensing-adapted VLM outperform a generic VLM on RS VQA
  and visual grounding?
- Models / methods: GeoChat (`external/research/GeoChat`, released checkpoint) vs a
  generic open VLM baseline (TBD — e.g. LLaVA-1.5-7B, same size class).
- Dataset: TBD held-out RS VQA + grounding set (candidates: RSVQA-LR/HR, DIOR-RSVG
  subset). License and region to be recorded.
- Split: held-out test only; check no overlap with GeoChat instruction data.
- Metric: VQA exact-match / accuracy; grounding acc@IoU0.5.
- Baseline: the generic VLM (our reproduction number).
- Result: _not measured_.
- Failure cases: _tbd_.
- DECISION: _pending_.

## EXP-002 — Temporal specialist: ChangeChat vs Change-Agent

- Status: PLANNED
- Hypothesis: H2
- Question: Which repo is the better bi-temporal ("temporal worker") specialist for
  SatQuery — ChangeChat or Change-Agent's Multi_change model?
- Models / methods: `external/research/ChangeChat` (⚠ weights unreleased — may be
  BLOCKED until then) vs `external/research/Change-Agent` `MCI_model.pth`.
- Dataset: LEVIR-MCI test split (HF `lcybuaa/LEVIR-MCI`), not yet downloaded.
- Metric: change-captioning (BLEU-4 / CIDEr / METEOR) and, for Change-Agent,
  change-mask IoU (building / road).
- Baseline: image-difference + rule-based captioner (trivial baseline).
- Result: _not measured_.
- Notes: compare on the parts each actually supports; do not force a shared metric
  where the tasks differ.
- DECISION: _pending_.

## EXP-003 — Optical + SAR evidence for built-up classification

- Status: PLANNED
- Hypothesis: H3
- Question: Does adding SAR evidence (VV/VH backscatter, in dB) improve built-up /
  informal-settlement classification vs optical-only?
- Models / methods: RemoteCLIP zero-shot (optical) as baseline; + a SAR-feature
  rule or a small classifier on σ⁰ VV/VH; fusion in `packages/*/fusion`.
- Dataset: TBD paired Sentinel-2 + Sentinel-1 tiles over a region with a built-up
  reference layer. Record CRS, GSD, dates, co-registration residual.
- Metric: F1 / IoU on the built-up class; also report where SAR *hurt*.
- Baseline: optical-only RemoteCLIP zero-shot (our reproduction number).
- Result: _not measured_.
- DECISION: _pending_.

## EXP-004 — Can the verifier catch wrong VLM answers?

- Status: PLANNED
- Hypothesis: H4
- Question: Does the verification layer detect unsupported or contradictory model
  outputs better than chance?
- Models / methods: verifier design TBD (consistency checks, independent method
  cross-check, optical↔SAR agreement) in `packages/evidence/verification`.
- Dataset: a curated set of query+image cases with **known** correct/incorrect
  model answers (hand-labelled), in `evaluation/cases/`.
- Metric: detection precision / recall of "answer is wrong or unsupported";
  false-flag rate on correct answers.
- Baseline: no verifier (accept all) and a naive confidence-threshold rule.
- Result: _not measured_.
- DECISION: _pending_.

## EXP-005 — Geospatial validation prevents invalid paired-image runs

- Status: PLANNED
- Hypothesis: H5
- Question: Does the geospatial integrity layer (CRS check, co-registration
  assertion, GSD check) reduce invalid bi-temporal executions and spatial-reasoning
  errors?
- Models / methods: `packages/geospatial` validation gate on vs off, feeding
  EXP-002's pipeline.
- Dataset: a stress set including deliberately mismatched pairs (different CRS,
  offset, different GSD) mixed with valid pairs.
- Metric: fraction of invalid pairs correctly rejected; downstream change-metric
  error with vs without the gate.
- Baseline: gate disabled.
- Result: _not measured_.
- DECISION: _pending_.

---

## Index

| ID | Hypothesis | Status | Decision |
|----|-----------|--------|----------|
| EXP-001 | H1 | PLANNED | — |
| EXP-002 | H2 | PLANNED | — |
| EXP-003 | H3 | PLANNED | — |
| EXP-004 | H4 | PLANNED | — |
| EXP-005 | H5 | PLANNED | — |
