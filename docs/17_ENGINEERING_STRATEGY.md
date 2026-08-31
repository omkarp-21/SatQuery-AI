# SATQUERY — Engineering Strategy

> Status: **Active — binding** · Owner: _TBD_ · Last updated: 2026-08-31
> Companion docs: [`18_RESEARCH_TO_ACCURACY.md`](18_RESEARCH_TO_ACCURACY.md),
> [`19_EXPERIMENT_REGISTRY.md`](19_EXPERIMENT_REGISTRY.md),
> [`20_PROTOTYPE_ROADMAP.md`](20_PROTOTYPE_ROADMAP.md),
> [`21_CLAUDE_WORKING_PRINCIPLES.md`](21_CLAUDE_WORKING_PRINCIPLES.md)

## The premise

Prototype quality and research accuracy are **not** competing priorities for
SatQuery. They reinforce each other:

> Build a prototype that works, while continuously using research to improve
> accuracy, reliability, modality handling, and differentiation.

- **Not** a beautiful demo with weak models.
- **Not** endless research with no working system.
- The cadence is: **research → experiment → measure → integrate → improve → demonstrate.**

## Two parallel tracks

| Product track | Research track |
|---------------|----------------|
| Makes the complete workflow usable | Improves model / task performance |
| Connects ingestion → routing → models → verification → UI | Tests alternative models, studies failure modes |
| Produces demonstrable functionality | Evaluates fusion and routing, measures accuracy & reliability |

The tracks **continuously exchange information**:

```
Product exposes a failure  ──►  Research classifies & addresses it  ──►  Improved model returns to Product
```

Neither track runs ahead of the other for long. A week of pure research with no
integration, or a week of pure feature-building with no measurement, is a process
failure.

## Priority order (what to build next)

1. Mandatory SIH requirement (problem 26167)
2. Measurable impact on accuracy / reliability
3. Critical prototype functionality (unblocks the end-to-end path)
4. High-value innovation (a genuine SatQuery contribution — see novelty rule in doc 18)
5. Performance / latency
6. UI polish
7. Nice-to-have features

**Do not prioritize visual polish over core model correctness.**
**Do not pursue research that cannot improve SatQuery.**

## Cadence

- Small vertical slices, integrated often. `main` always runs the current
  prototype version's demo path (see [`20_PROTOTYPE_ROADMAP.md`](20_PROTOTYPE_ROADMAP.md)).
- Every capability that involves a model is gated by a baseline + a measurement
  (doc 18). No "it seems better" merges.
- Every model trial is an entry in [`19_EXPERIMENT_REGISTRY.md`](19_EXPERIMENT_REGISTRY.md)
  with a `KEEP / REJECT / INVESTIGATE` decision. We do not "try models" off the record.

## Definition of Feature Complete

A feature is complete only when:

1. implemented
2. tested
3. integrated (wired into the real pipeline, not a side script)
4. observable in the UI or API
5. error handling exists
6. logging exists (structured, with the query id)
7. an evaluation case exists in `evaluation/cases/`
8. documentation updated (the matching `docs/NN_*.md`)

(This extends the six-point Definition of Done in `CLAUDE.md`.)

## Definition of Research Complete

A research item is complete only when:

1. source identified (paper + repo + commit)
2. method understood (can explain the mechanism in plain terms)
3. implementation tested (it runs on our machine — the *reproduction*)
4. baseline measured (on our data, our metric, our hardware)
5. limitation documented
6. experiment conducted where relevant (registered in doc 19)
7. decision recorded (`KEEP / REJECT / INVESTIGATE`)
8. citation recorded

## Anti-patterns (do not do)

- Build features for the sake of features.
- Replace a failing model before classifying the failure (doc 18).
- Claim an improvement without a before/after measurement.
- Present a research paper's number as a SatQuery result (see the three-numbers
  rule in doc 18 — this is a firing-offense-level mistake for credibility).
- Rewrite academic code when an adapter would do.
- Let the SIH deck describe capability the prototype cannot demonstrate.

## Golden principle

> **Do not build features for the sake of features.**
>
> Build: research-backed capability → measurable improvement → integrated
> functionality → demonstrable value.
