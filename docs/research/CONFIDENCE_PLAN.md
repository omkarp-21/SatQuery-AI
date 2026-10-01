# Confidence Plan (research preparation)

> Status: **plan only — no confidence number is emitted in production.**
> `.claude/rules/ai-models.md`: a value that is not a calibrated probability must
> be labelled as such; an ad-hoc score is never presented as "confidence: 0.9".
> `EvidenceItem` deliberately has **no** confidence field. This doc defines what
> we would need before reporting any confidence.

## Why not yet

- No model in the stack emits a calibrated probability.
- RemoteCLIP's softmax is over *supplied prompts* — a relative score, not P(correct).
- ChangeFormer's `changed_fraction` is pixel coverage, not a confidence.
- CROMA/DOFA return representations, no score.
- The verifier is **structural** only (SUPPORTED/CONTRADICTED/…), not a probability.

Reporting a number now would be fabrication.

## Candidate confidence sources (to be evaluated, not assumed)

| Source | Where it applies | What it needs before use |
|--------|------------------|--------------------------|
| **Model score** (softmax / logit margin) | RemoteCLIP ranking; a future VQA model's answer prob | calibration on a labelled set (reliability diagram, ECE); document as "raw margin" until then |
| **Calibrated probability** (temperature / isotonic on the model score) | any model with a score + a labelled calibration split | a held-out labelled set per task; recompute ECE after calibration |
| **Evidence agreement** | `/analyze` multi-evidence results | a rubric: do the `EvidenceItem`s corroborate the claim? needs labelled agree/disagree cases |
| **Verifier status** | every result | map {SUPPORTED, CONTRADICTED, INSUFFICIENT_EVIDENCE, NOT_APPLICABLE} to a coarse band — but this is *structural*, so at most "structurally consistent", never "correct" |
| **Model disagreement** | optical vs SAR (EXP-004), CROMA vs DOFA, or two VQA models | needs ≥2 models answering the same query on the same input; disagreement → lower band / re-route |
| **Geospatial trust** | any georeferenced output | already deterministic (co-reg passed, GSD known); a gate, not a probability |

## Experiments required before any confidence is reported

| ID | Question | Needs | Status |
|----|----------|-------|--------|
| **EXP-005** | Does the structural verifier detect defects, and what does it miss? | curated `(result, evidence, context)` corpus | **RUN (G6)** — structural detection P/R/F1 = 1.00 on n=24; **semantic-defect miss rate = 1.00** (`EXP-005.md`). → verifier `status` is usable as a *structural* band only; a semantic verifier is still required for a correctness signal. |
| **EXP-C1** | Is a model score calibrated after temperature / isotonic scaling? (ECE before → after; reliability diagram) | a labelled calibration split per task (RSVQA-LR yes/no, LEVIR-CD, …) + a model that emits a score | **BLOCKED** — no VQA model reproduced (EXP-002 artifact acquisition); RemoteCLIP margin is the only score available and it is over *supplied prompts*. Spec below. |
| **EXP-C2** | Does optical↔SAR (or CROMA↔DOFA) disagreement correlate with error? | EXP-004 Run 2 data + both encoders' predictions on the same split | **BLOCKED** — EXP-004 Run 2 needs the S1+S2 dataset (remote box). Spec below. |

### EXP-C1 spec (ready to run once a scored model exists)

1. Inputs: a task with a labelled test split and a model that emits a per-answer
   score `s` (RSVQA-LR yes/no + the EXP-002 winner's answer probability; or
   RemoteCLIP top-1 margin on a scene-label set).
2. Split the labelled set 50/50 into **calibration** and **evaluation**.
3. On calibration: fit **temperature scaling** (1-param) and **isotonic
   regression** (non-parametric) mapping `s → p̂`.
4. On evaluation: compute **ECE** (15 bins), **Brier score**, and a **reliability
   diagram**, for raw `s`, temperature-scaled, isotonic.
5. Report the three ECEs + the diagram. Decision: a score is "calibrated enough
   to surface" only if post-calibration **ECE ≤ 0.05** and the reliability
   diagram is monotone. Record split ids, seed, hardware, date.
6. Output: `docs/research/EXP-C1.md` + `evaluation/reports/expc1_*.json`. Still no
   production number until the "definition of done" (below) is fully met.

### EXP-C2 spec (ready to run once EXP-004 Run 2 has predictions)

1. Take the EXP-004 Run 2 evaluation split (real S1+S2, one task).
2. For each sample record: optical-only prediction, CROMA-joint prediction,
   DOFA-fused prediction, and the ground-truth label.
3. Define **disagreement** = (pred_optical ≠ pred_joint) and the softmax-margin
   gap between the two heads.
4. Measure: P(error | disagree) vs P(error | agree); AUROC of "disagreement
   flag" as an error detector; does routing "disagree → abstain/re-check" raise
   selective accuracy at fixed coverage?
5. Output: `docs/research/EXP-C2.md` + `evaluation/reports/expc2_*.json`.

## What ships in the interim

- `score` fields stay, each with an explicit `score_meaning` string.
- `verification.status` (structural) is the only "is this trustworthy?" signal, and
  its `notes` say it is not a semantic judgement. **EXP-005 (G6) confirms this is
  a structural band only** — it catches 100 % of the structural defects in the
  curated corpus and 0 % of the semantic ones.
- `/analyze` aggregates evidence + verification; it does **not** synthesize a number.

## G6–G7 status (2026-09-01)

**No confidence number is emitted anywhere.** EXP-005 (structural verifier) and
**EXP-005b (model-independent semantic verifier)** are done — both give a
**status band**, not a probability. `verify_semantic().status` ∈ {COHERENT,
INCOHERENT, NOT_ENOUGH_EVIDENCE} joins `verify().status` as a calibration input
for EXP-C1 (a second structural/coherence signal). EXP-C1 and EXP-C2 remain
**blocked on the same artifacts as EXP-002 / EXP-004 Run 2** (a scored VQA model;
a real S1+S2 split). The "definition of done" below is unchanged; 0 of its 4
conditions are met.

## Definition of done for "confidence"

A confidence value is only reported when: (1) its source is named; (2) it is
calibrated on a documented labelled split; (3) its ECE / reliability is recorded;
(4) `docs/11_EVALUATION_PLAN.md` states the calibration data and its distribution
gaps. Until all four hold, no number.
