# Evaluation Plan

> Status: **Draft outline** · Owner: _TBD_ · Last updated: 2026-09-01
> Discipline: `.claude/skills/evaluation/SKILL.md` and `docs/18_RESEARCH_TO_ACCURACY.md`
> (the three numbers). Experiments: `docs/19_EXPERIMENT_REGISTRY.md`.

## Purpose

Define what we measure, on which data, so that every accuracy/reliability claim in
the prototype and the PPT is backed by a real run.

## SIH-aligned public benchmark areas (candidates)

- **VRSBench** — single-image RS VQA / captioning / grounding.
- **RSVQA** (LR / HR) — remote-sensing visual question answering.
- **CDVQA** — change-detection visual question answering.
- **BigEarthNet** (`BigEarthNet.txt`) — adaptation / fine-tuning source (satisfies
  the PS adaptation requirement).
- Change-mask: **LEVIR-CD / LEVIR-MCI**.

_None downloaded yet; packaging, licence, region and split must be recorded before use._

## Metrics (per task)

- VQA: exact-match / accuracy.
- Grounding: acc@IoU0.5.
- Change mask: IoU / F1.
- Change captioning: BLEU-4 / CIDEr / METEOR.
- Routing: correct-specialist accuracy; invalid-execution rate.
- Verification: precision / recall of "wrong-or-unsupported" detection.
- System: end-to-end latency p50 / p95 (cold / warm).

## Experiments

EXP-001…EXP-007 (`docs/19_EXPERIMENT_REGISTRY.md`). Each records dataset, split
(+ leakage check), preprocessing, hardware, metric, configuration, result (tagged
paper / reproduction / SatQuery), failure cases, and a `KEEP / REJECT / INVESTIGATE`
decision.

## Rules

- Never fabricate a number; `_TBD_` until a real run exists.
- Baseline first, always.
- Report a "known distribution gaps" section — e.g. tested on Sentinel/Landsat,
  untested on unseen ISRO sensors.

## Open questions

- Exact benchmark packaging + access.
- Held-out set construction to avoid overlap with model instruction/training data.
- How SatQuery-integrated results are scored end to end (rubric per `evaluation/cases/`).
