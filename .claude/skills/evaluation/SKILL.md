---
name: evaluation
description: Evaluation discipline for SatQuery — obsessed with never fabricating numbers. Defines the required record for any measurement (baseline, experiment, metric, dataset split, seed, hardware, latency, failure cases) and how to run and report the eval suite. Invoke whenever a number about model quality, accuracy, or performance is produced, cited, or written down.
---

# Evaluation

## The one rule

**No fabricated numbers. Ever.** If a metric has not been computed from a real run
on a defined dataset, it does not get written into docs, the README, a slide, a
comment, or a commit message. Placeholders are literally `_TBD_`, never a
plausible-looking value.

## Every reported metric carries its record

An eval result is invalid unless it names all of:

| Field | Meaning |
|-------|---------|
| baseline | what it's compared against (prior method / naive / previous run) |
| experiment | the exact config / code commit that produced it |
| metric | precise definition (e.g. "IoU on change mask, macro-averaged") |
| dataset | source, license, region, sensor |
| split | how train/val/test were separated; leakage checks |
| seed | RNG seed(s) used |
| hardware | GPU/CPU model, VRAM, batch size |
| latency | wall-clock per query (p50/p95), and cold vs warm |
| failure cases | concrete examples where it breaks, with inputs |

Store this as a YAML/JSON sidecar next to each run in `evaluation/reports/`.

## Layout

- `evaluation/cases/` — one file per scenario: query, inputs, expected answer, rubric.
- `evaluation/datasets/` — held-out data (gitignored if large; manifest committed).
- `evaluation/metrics/` — metric implementations, unit-tested against known values.
- `evaluation/scripts/run_suite.py` — runs cases → writes a timestamped report.
- `evaluation/reports/` — generated, gitignored; the record sidecar is the artifact.

## Running

```bash
make eval          # python evaluation/scripts/run_suite.py
```

A run must: fix seeds, log hardware, record commit SHA, time each query, save
per-case pass/fail with the rubric, and list failures explicitly.

## The three numbers — never mix them (`docs/18_RESEARCH_TO_ACCURACY.md`)

| # | Name | May be written as |
|---|------|-------------------|
| 1 | **Paper result** | "GeoChat reports X on RSVQA (paper, [cite])" — always attributed |
| 2 | **Our reproduction** | "reproduction: we get X running their code + checkpoint on their benchmark" |
| 3 | **SatQuery result** | "SatQuery scores X on <our split>" — the integrated system under our eval |

Only #3 is "SatQuery's accuracy". Forbidden: *"the paper says X, therefore
SatQuery achieves X."* If only #1 exists, say so and mark #2/#3 "not yet measured".

## Experiment registry

Every model trial is an `EXP-NNN` entry in `docs/19_EXPERIMENT_REGISTRY.md`,
created **before** the work, ending in `KEEP / REJECT / INVESTIGATE`. Eval reports
and `evaluation/cases/` entries link back to their `EXP-NNN`. Baseline first,
always (`docs/18`).

## Reporting language

- "We measured X on split S (n=…, seed=…, GPU=…)." — allowed.
- "X% accuracy" with no record — not allowed.
- Improvement claims state the baseline and the delta with n.
- Unknown = "not yet evaluated", not an optimistic guess.
- State which of the three numbers every figure is.

## Generalization to ISRO / unseen data

State clearly what was and was not tested. If the model was only evaluated on
Sentinel/Landsat, say so — do not imply it will hold on unseen ISRO sensors.
Add a "known distribution gaps" section to `docs/11_EVALUATION_PLAN.md`.
