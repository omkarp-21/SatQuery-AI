---
name: satquery-architecture
description: Authoritative map of SatQuery AI's structure — the six-phase principle, the fixed pipeline stage order, module boundaries, and data contracts. Invoke before adding a module, moving code between layers, changing how stages connect, or any restructuring. Prevents drift and ad-hoc reorganization.
---

# SatQuery Architecture

You are working inside a system with a **deliberate, fixed** shape. Do not
"improve" the structure in passing. Structural change goes through an ADR in
`docs/DECISIONS.md`.

## The six phases (never skip one)

`Plan → Validate → Execute → Verify → Explain → Audit`

- **Plan** — turn the NL query into a typed execution plan (which modality, which
  task, which specialists, what order).
- **Validate** — check inputs exist, imagery is readable, CRS/alignment are sane,
  requested area/date range are in bounds. Fail here loudly, not later.
- **Execute** — run specialists through adapters + registry.
- **Verify** — cross-check outputs (independent method, consistency, physical
  plausibility) where possible.
- **Explain** — assemble the evidence trail and execution trace.
- **Audit** — write provenance: what ran, on what, with which versions, producing what.

## Fixed pipeline stage order

Package: `backend/satquery/`. Order is load-bearing:

```
ingestion → metadata → routing → planning → registry → agents → specialists →
fusion → verification → evidence → geospatial → confidence → provenance → reports
```

| Stage | Responsibility |
|-------|----------------|
| ingestion | Fetch/resolve imagery + query into typed inputs |
| metadata | Extract CRS, transform, bounds, GSD, band info, acquisition dates |
| routing | Pick modality path (single / bi-temporal / optical–SAR) and candidate models |
| planning | Deterministic execution plan (DAG of specialist calls) |
| registry | Resolve model entries from `models/model_registry.yaml` to adapters |
| agents | Orchestrate the plan deterministically (no free-form LLM tool calls) |
| specialists | Invoke model adapters, collect normalized results |
| fusion | Combine multi-model outputs (weighted vote / rule-based per registry) |
| verification | Independent checks; flag disagreement (esp. SAR vs optical) |
| evidence | Build the human-inspectable evidence objects (tiles, masks, boxes, citations) |
| geospatial | Vectorize, reproject to output CRS, compute areas/geometries |
| confidence | Produce a documented, qualified confidence value |
| provenance | Persist the audit record |
| reports | Render the final answer + trace for API/frontend |

## Layer boundaries (do not cross)

- **API / orchestration** → `backend/app/` (`api/`, `core/`, `schemas/`, `services/`, `main.py`)
- **Pipeline logic** → `backend/satquery/<stage>/`
- **Model code** → `models/` (`adapters/`, `checkpoints/`, `model_registry.yaml`)
- **Reference research** → `research/repos/` — read-only, never imported by product code
- **Frontend** → `frontend/src/` — talks to backend only via `docs/09_API_CONTRACTS.md`

## Data contract rules

- Every stage: typed Pydantic input → typed Pydantic output. Contract in the module docstring.
- Forward flow only. A later stage creates new objects; it never mutates an earlier stage's output.
- Provenance rides along from `metadata` onward. No result without it.
- Models are reached only via adapter + registry. No hardcoded model names in stages.

## When asked to restructure

1. State which rule/boundary the request would break.
2. Propose the change as an ADR (context / decision / consequences).
3. Only proceed once the ADR is written and accepted.
