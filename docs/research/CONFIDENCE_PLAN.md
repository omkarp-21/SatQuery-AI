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

| ID | Question | Needs |
|----|----------|-------|
| **EXP-005** | Can structural + agreement checks detect wrong/unsupported answers better than a score threshold? | a curated set of query+image cases with known correct/incorrect answers |
| **EXP-C1** (new, later) | Is a model score calibrated after temperature/isotonic scaling? (ECE before/after) | a labelled calibration split per task (RSVQA-LR, LEVIR-CD, …) |
| **EXP-C2** (new, later) | Does optical↔SAR (or CROMA↔DOFA) disagreement correlate with error? | EXP-004 Run 2 data + both encoders' predictions |

## What ships in the interim

- `score` fields stay, each with an explicit `score_meaning` string.
- `verification.status` (structural) is the only "is this trustworthy?" signal, and
  its `notes` say it is not a semantic judgement.
- `/analyze` aggregates evidence + verification; it does **not** synthesize a number.

## Definition of done for "confidence"

A confidence value is only reported when: (1) its source is named; (2) it is
calibrated on a documented labelled split; (3) its ECE / reliability is recorded;
(4) `docs/11_EVALUATION_PLAN.md` states the calibration data and its distribution
gaps. Until all four hold, no number.
