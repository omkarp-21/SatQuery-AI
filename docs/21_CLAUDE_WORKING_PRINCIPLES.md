# How Claude Must Work on SatQuery

> Status: **Active — binding** · Owner: _TBD_ · Last updated: 2026-08-31
> This governs how any AI agent (Claude Code, subagents) approaches work here. It
> sits alongside `CLAUDE.md`, `.claude/rules/`, `.claude/skills/`, `.claude/agents/`.

## Mental model

Do **not** think "I need to build a hackathon dashboard." Think:

```
                 SATQUERY
                     │
        ┌────────────┴────────────┐
        ▼                         ▼
     PRODUCT                   RESEARCH
        │                         │
    Prototype                  Baseline
        │                         │
    Integration               Experiment
        │                         │
        └────────────┬────────────┘
                     ▼
                  MEASURE
                     │
                     ▼
               IMPROVEMENT
                     │
                     ▼
              BETTER SATQUERY
```

Run this loop repeatedly. Small increments, each measured.

## Before implementing a major feature

1. **Read the relevant docs** (`docs/NN_*.md`, especially 02, 03, 05, 06, 17, 18, 20).
2. **Identify the SIH requirement** being addressed (problem 26167 — cite it).
3. **Check existing research / components** (`external/research/`, `docs/research/`,
   `packages/`). Has this been tried? See `19_EXPERIMENT_REGISTRY.md`.
4. **Determine whether reuse is possible** — an adapter over a research repo, an
   existing pipeline stage, an existing util.
5. **Define the baseline** (what we compare against).
6. **Define the success metric** (precise; which of the three numbers it is).
7. **Implement the minimum viable experiment** — the smallest thing that produces a
   measurement.
8. **Measure.** Record it in the experiment registry.
9. **Only then expand the implementation.**

## When uncertain

- Inspect the research repository.
- Inspect the documentation.
- Run a small experiment.
- **Do not invent behavior.** Do not invent numbers, capabilities, or results.

## Prefer / avoid

| Prefer | Avoid |
|--------|-------|
| small experiment → evidence → decision → integration | large rewrite → assumptions → unmeasured claims |
| adapter over a research model | rewriting academic code |
| baseline first, then change | "this looks better" merges |
| "not yet measured" | a plausible-looking placeholder number |
| paper / reproduction / SatQuery kept separate | quoting a paper's number as ours |
| failure classified, then remedied | swapping the model on first failure |

## Hard stops (never do these)

- Present a research paper's result as a SatQuery result.
- Write a metric that was not produced by a real run.
- Claim an improvement without a before/after measurement.
- Add a model to the registry without an adapter smoke test and an experiment entry.
- Return a pipeline result without provenance.
- Treat SAR as RGB.
- Restructure the architecture without an ADR.

## When to bring in a subagent

- Structural / cross-layer design → `architect`
- Imagery physics / preprocessing correctness, paper review → `remote-sensing-researcher`
- Wrapping a research model → `ml-engineer`
- Raster/vector correctness → `geospatial-engineer`
- Any number about model quality → `ai-evaluator`
- Before merging risky or demo-facing work → `red-team-reviewer`
- Before the demo, on every major feature → `hackathon-jury`

## Definition of done (short form)

Feature: implemented · tested · integrated · observable · errors handled · logged ·
eval case · docs updated.
Research: source · method · reproduction · baseline · limitation · experiment ·
decision · citation.

See [`17_ENGINEERING_STRATEGY.md`](17_ENGINEERING_STRATEGY.md) and
[`18_RESEARCH_TO_ACCURACY.md`](18_RESEARCH_TO_ACCURACY.md) for the full versions.
