# System Architecture

> Status: **Draft outline** · Owner: _TBD_ · Last updated: 2026-09-01
> Authoritative structure: `.claude/skills/satquery-architecture/SKILL.md` and
> ADR-001 in `docs/DECISIONS.md`. This document is the design narrative.

## Purpose

Describe how a natural-language query becomes an evidence-backed answer, and which
layer owns each responsibility.

## Target flow

```
User Query
→ Query Interpretation
→ Input / Metadata Validation
→ Execution Plan
→ Specialist Selection
→ Specialist Execution
→ Evidence Extraction
→ Verification
→ Confidence / Uncertainty
→ Evidence Fusion
→ Final Answer
→ Visual Evidence
→ Audit Trace
```

This maps onto the fixed pipeline stage order
(`ingestion → metadata → routing → planning → registry → agents → specialists →
fusion → verification → evidence → geospatial → confidence → provenance → reports`).

## Core layers

- **Geospatial gateway** — native raster/vector ingestion, CRS/transform/bounds/GSD
  extraction, NoData handling, pair-compatibility and alignment checks (`packages/geospatial`).
- **Planner / router** — infer task, inspect input, build a constrained
  deterministic execution plan, route to specialists (`packages/agents`, see the
  `agent-orchestration` skill).
- **Specialist registry** — capability-declared model adapters
  (`packages/model_adapters/model_registry.yaml`).
- **Evidence / verification** — assemble `EvidenceItem`s, cross-check where
  independent evidence exists, produce a qualified confidence (`packages/evidence`).
- **Presentation** — API responses + the dashboard's ask / investigate / trace
  screens (`apps/`).

## Open questions

- Sync vs async execution for multi-specialist plans; job queue vs in-request.
- Where fusion strategy is configured (registry vs plan vs per-query).
- Streaming partial results to the trace panel.
