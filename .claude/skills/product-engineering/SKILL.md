---
name: product-engineering
description: Startup-style product engineering for SatQuery (Garry Tan / YC flavor) — move fast, ship a thin vertical slice, cut scope to the demo-critical path, prioritize leverage, simplify. The aggressive voice — explicitly bounded so "move fast" never becomes "fake the AI or the metrics". Invoke when planning scope, prioritizing a backlog, or deciding what to build next.
---

# Product Engineering

## The aggressive voice (with a hard boundary)

Ship fast. Build the thinnest thing that proves the idea. Prioritize leverage.
Simplify relentlessly.

**Boundary that overrides all of the above:** never fabricate metrics, never fake
model capability, never present a stub as working AI. If shipping speed conflicts
with research honesty or measurement, **honesty and measurement win.** Cut scope,
don't cut truth.

## Prioritization

- Optimize for the **demo-critical path** first: one query, end to end, one
  modality, real models, real evidence. Depth over breadth.
- Rank work by leverage: does it unblock multiple later things (the adapter
  interface, the plan schema, the evidence object) or is it a leaf feature?
- Timebox spikes. If a research repo won't integrate in a day, stub the adapter
  behind the real interface (clearly labeled) and move on — then come back.
- Prefer boring, proven tech. Reuse open-source implementations over building.

## Scope cutting

For every feature ask: does the SIH demo or the judging story need this? If no,
it goes to a "later" list in `docs/TODOS.md`, not into this week.

## Shipping cadence

- Small PRs, daily. Each merges a working vertical slice, not a horizontal layer
  with no consumer.
- `main` always runs the demo path. A change that breaks it doesn't merge.
- Feedback loop: run the real demo end to end often; let friction set priorities.

## Simplify

- Delete code that isn't on a path to the demo or a rule requirement.
- One way to do a thing. Collapse near-duplicate stages/utils.
- Fewer dependencies, fewer config knobs, fewer abstractions than feel clever.

## Where this skill defers

- Numbers, claims, generalization → `research-review`, `evaluation`.
- Correctness, boundaries, provenance → `code-review`, `.claude/rules/`.
Use this skill for *what to build and how fast*, not for *what to claim*.
