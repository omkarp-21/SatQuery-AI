# Agent Architecture

> Status: **Draft outline** · Owner: _TBD_ · Last updated: 2026-09-01
> Design detail: `.claude/skills/agent-orchestration/SKILL.md`. Routing is tested
> in EXP-006 (`docs/19_EXPERIMENT_REGISTRY.md`).

## Purpose

Define how the system decides what to run — deterministically, auditable, and
without free-form LLM tool use.

## The loop

1. Interpret the query (LLM disambiguates intent into a typed task + parameters,
   validated against a schema).
2. Inspect input — image count, modality, format, metadata.
3. Validate compatibility (CRS, alignment, GSD, date ordering).
4. Select tools from the registry by declared capability — never a hardcoded name.
5. Build a constrained `ExecutionPlan` (typed DAG); execute through observable
   state, with bounded retries.
6. Verify where independent evidence exists.
7. Return the answer plus the full audit trace.

## Principle

**Deterministic execution, LLM-assisted planning.** The LLM helps build a plan; it
does not decide mid-run which model to call next. Same query + same inputs → same
plan (seeds fixed), stored verbatim in provenance.

Prefer constrained / deterministic routing wherever it improves reliability
(EXP-006 exists to measure this vs LLM-only routing). LangGraph only if it
genuinely simplifies DAG execution — no open-ended agent node.

## Open questions

- Plan repair vs hard fail when a required specialist is unavailable.
- How much the LLM is allowed to set parameters vs a fixed allowlist.
- Multi-turn / follow-up queries over the same evidence graph.
