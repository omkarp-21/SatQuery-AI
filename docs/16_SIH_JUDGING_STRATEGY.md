# SIH Judging Strategy

> Status: **Draft outline** · Owner: _TBD_ · Last updated: 2026-09-01
> Full strategic context: `chatgpt.context.md` §2, §17–§20, §26.
> Demo: `docs/15_DEMO_SCRIPT.md`. Jury attack set: `.claude/agents/hackathon-jury.md`.

## Purpose

Keep every design and claim aligned to how SIH evaluates, and to a coherent
six-slide story.

## Submission story

```
Problem
→ Existing limitations (fragmented RS-VLMs, no evidence-aware execution layer)
→ Research gap
→ SatQuery contribution (plan · validate · route · analyze · verify · explain · audit)
→ Technical approach
→ Experimental proof (research + benchmark + measurable improvement)
→ Impact (usable, scalable geospatial intelligence interface)
```

Every slide advances this story.

## Scoring lenses to survive (see `chatgpt.context.md` §18)

Domain · ML · Systems · Geospatial · Product · Jury (novelty) · Feasibility.

## Rules

- Never fabricate accuracy, latency, confidence, or novelty.
- The prototype must produce evidence that strengthens the PPT; the PPT must never
  claim what the prototype cannot credibly demonstrate.
- Novelty is in SatQuery's orchestration / evidence / verification / geospatial
  integrity — **not** in using any single open-source model — and every novelty
  claim needs a literature basis plus an experiment.
- Until measured, PPT numbers are labelled **TARGETS**.

## Six-slide blueprint (see `chatgpt.context.md` §19)

Problem+value · Solution+innovation · Technical approach+stack · Feasibility+risk
matrix · Impact metrics (quantified/targets) · Research & references. Do not exceed
six slides.

## Open questions

- Which two or three measured results are the headline evidence for Slide 5.
- The single "killer demo" query to feature (`docs/15_DEMO_SCRIPT.md`).
