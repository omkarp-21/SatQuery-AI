# SatQuery Experiment Registry

> Status: **Active — binding** · Owner: _TBD_ · Last updated: 2026-09-01
> Every experiment gets an ID. Nothing here is measured yet — all entries are
> **PLANNED**. Results are filled in only from real runs (see
> [`18_RESEARCH_TO_ACCURACY.md`](18_RESEARCH_TO_ACCURACY.md) and
> `docs/11_EVALUATION_PLAN.md`). Do not invent numbers.
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

- Status: PLANNED
- Hypothesis: n/a — selection bake-off
- Question: Among candidate single-image RS-VLMs, which gives the best
  accuracy / latency / integration-cost trade-off for SatQuery's single-image path?
- Models / methods: GeoChat vs RemoteCLIP (zero-shot classification / retrieval) vs
  any further candidate found in `external/research/awesome-rs-vlms`. Same prompts,
  same preprocessing where the task allows.
- Dataset: the EXP-001 held-out set for VQA/grounding; a scene-classification /
  retrieval set (e.g. from RESISC45 / AID, or VRSBench) for RemoteCLIP-style tasks.
- Metric: per-task accuracy + measured p50/p95 latency + a recorded integration-cost
  note (env size, deps, adapter effort) — the accuracy-to-engineering-cost ratio
  from `docs/18`.
- Baseline: whichever candidate is wired first (its reproduction number).
- Result: _not measured_.
- Notes: compare each model only on tasks it actually supports; do not force one
  shared metric across incompatible tasks.
- DECISION: _pending_ — output is a chosen single-image specialist stack.

## EXP-003 — Temporal stack: Change-Agent vs ChangeChat vs ChangeFormer

- Status: PLANNED
- Hypothesis: n/a — selection bake-off (informs H2)
- Question: Which temporal stack gives the best combination of change-mask quality,
  semantic change interpretation, speed, and integration stability?
- Models / methods: `external/research/Change-Agent` `MCI_model.pth` (mask + caption)
  vs `external/research/ChangeFormer` V6 (mask only) vs `external/research/ChangeChat`
  (⚠ weights unreleased at pinned commit — **BLOCKED** until then).
- Dataset: LEVIR-CD (mask) and LEVIR-MCI (mask + caption) test splits (HF
  `lcybuaa/LEVIR-MCI`), not yet downloaded.
- Metric: change-mask IoU / F1; change-captioning BLEU-4 / CIDEr / METEOR; p50/p95
  latency; a stability note (crashes, env fragility).
- Baseline: image-difference + threshold (mask) and a rule-based captioner.
- Result: _not measured_.
- Notes: compare on the parts each actually supports.
- DECISION: _pending_ — output is a chosen temporal specialist stack.

## EXP-004 — Optical-only vs optical + SAR  ⭐ next experiment (G1.5, ADR-005)

- Status: PLANNED — **highest-value next** (`docs/research/CAPABILITY_GAP_MATRIX.md`).
- Hypothesis: H3
- Question: For suitable queries (built-up / informal-settlement classification),
  does a **joint optical+SAR** representation improve the result vs optical-only?
- Models / methods: **CROMA** (`antofuller/CROMA`, MIT, HF) joint S1+S2 encoder
  with a linear-probe head **vs** an optical-only head (CROMA-optical, or RemoteCLIP
  image features). Runs on the 4 GB laptop / CPU — no GPU box needed.
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
- DECISION: _pending_ — KEEP / REJECT / INVESTIGATE CROMA for the SAR path.

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

## EXP-005 — Unverified answer vs verified answer

- Status: PLANNED
- Hypothesis: H4
- Question: Does the verification layer detect unsupported or contradictory model
  outputs better than chance (and better than a confidence threshold)?
- Models / methods: verifier design TBD (consistency checks, independent-method
  cross-check, optical↔SAR agreement) in `packages/evidence` (verification stage).
- Dataset: a curated set of query+image cases with **known** correct/incorrect
  model answers (hand-labelled), in `evaluation/cases/`.
- Metric: detection precision / recall of "answer is wrong or unsupported";
  false-flag rate on correct answers.
- Baseline: no verifier (accept all) and a naive confidence-threshold rule.
- Result: _not measured_.
- DECISION: _pending_.

## EXP-006 — LLM-only routing vs constrained deterministic/agentic routing

- Status: PLANNED
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
| EXP-002 | single-image RS-VLM bake-off (incl. TinyRS) | selection | PLANNED | — |
| EXP-003 | temporal stack bake-off (incl. TEOChat / caption pipeline) | selection (→H2) | PLANNED | — |
| **EXP-004** | **optical vs optical+SAR (CROMA + reBEN)** | **H3** | **PLANNED — ⭐ next** | — |
| EXP-005 | unverified vs verified | H4 | PLANNED | — |
| EXP-006 | LLM vs constrained routing | H2 | PLANNED (needs ≥2 adapters) | — |
| EXP-007 | geospatial validation on/off | H5 | PLANNED | — |
| EXP-008 | RS adaptation probe on BigEarthNet v2 (req. E) | n/a | PLANNED (shares EXP-004 infra) | — |

Hypothesis coverage: H1→EXP-001, H2→EXP-006 (informed by EXP-003), H3→EXP-004,
H4→EXP-005, H5→EXP-007. Mandatory-capability coverage without a hypothesis:
req. E → EXP-008.
