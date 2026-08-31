---
name: demo-engineering
description: Building and hardening the SIH demo for SatQuery — the scripted narrative, offline demo data, a reliable happy path, graceful failure on stage, timing, and the judging-strategy framing. Invoke when working on scripts/demo, data/demo, docs/15_DEMO_SCRIPT.md, or docs/16_SIH_JUDGING_STRATEGY.md, or preparing to present.
---

# Demo Engineering

## The demo is a product surface — engineer it

- The happy path must work **every time**, offline, from `data/demo/` (frozen,
  versioned). No live provider calls during the demo.
- `scripts/demo/run_demo.sh` runs the full narrative end to end. It is CI-tested.
- Pre-warm models before the demo starts; measure and know the real latency.
- Every step has a fallback: if a model call fails on stage, the UI shows a clean
  "specialist unavailable" state with the trace so far — it never white-screens.

## The narrative (`docs/15_DEMO_SCRIPT.md`)

Structure each demo beat as: **question asked → plan shown → execution trace →
answer → evidence → "here's how you'd verify it"**. The six phases are visible to
the judge, not hidden.

Cover the three modalities on purpose:
1. Single-image query (grounding / VQA).
2. Bi-temporal change query (co-registration → change mask → area).
3. Optical–SAR query where the two **disagree**, and show how verification surfaces it.

## Judging strategy (`docs/16_SIH_JUDGING_STRATEGY.md`)

Anticipate and pre-answer the hard questions (see the `hackathon-jury` agent):
novelty, "is it actually agentic", provable confidence, unseen-ISRO-data behavior,
CRS-wrong behavior, clouds, SAR/optical disagreement, latency, no-GPU, "which part
is yours". Have a slide or a trace for each.

## Honesty on stage

- Show real metrics with their record, or say "not yet evaluated". Never invent a
  number under pressure.
- Distinguish "our contribution" (orchestration, verification, evidence, geospatial
  correctness, adapter layer) from "reused research" (the specialist models).
- If something is faked for the demo (e.g. a stubbed model), the script says so and
  it is not presented as working AI.

## Checklist before presenting

- [ ] `run_demo.sh` green in CI and on the demo machine
- [ ] Demo data present, offline path verified with network off
- [ ] Models pre-warmed; latency numbers known
- [ ] Every beat has a graceful failure state
- [ ] Jury questions have prepared answers with evidence
- [ ] Backup recording of a clean run
