# Architecture Rules

- Monorepo layout (ADR-001): `apps/{backend,frontend}`, `packages/{core,geospatial,
  agents,evidence,model_adapters}` (src layout, installable), `external/research/`
  (vendored, gitignored, read-only), `models/`, `data/`, `evaluation/`,
  `infrastructure/`, `docs/`. Do not add a new top-level dir without an ADR.
- The pipeline stage order is fixed:
  `ingestion → metadata → routing → planning → registry → agents → specialists →
  fusion → verification → evidence → geospatial → confidence → provenance → reports`.
  Do not reorder, merge, or add top-level stages without an ADR in `docs/DECISIONS.md`.
- Stages map to packages: core stages (ingestion, metadata, routing, planning,
  registry, fusion, confidence, reports) → `packages/core/src/satquery_core/<stage>/`;
  geospatial → `packages/geospatial`; agents + specialists → `packages/agents`;
  evidence + verification + provenance → `packages/evidence`. Each stage takes a
  typed Pydantic input, returns a typed output; contract in the module docstring.
- Package dependency direction is one-way: `core` depends on nothing internal;
  `agents` and `evidence` may depend on `core`; `geospatial` and `model_adapters`
  stand alone; `apps/backend` depends on all packages. No cycles.
- A stage never reaches around the `registry` to call a model directly. Models are
  invoked only through their adapter (`packages/model_adapters/`).
- Orchestration logic lives in `apps/backend/app/services/`. Pipeline logic lives in
  `packages/`. Do not mix these.
- `external/research/` is vendored reference code — read-only, gitignored. Product
  code in `apps/` and `packages/` must never import from it; integration is via a
  `model_adapters` adapter calling an isolated env/container by subprocess.
- Data flows forward only. A later stage does not mutate an earlier stage's output;
  it produces a new typed object.
- Provenance is threaded through every stage. No code path returns a result without
  a provenance record attached.
- No new runtime dependency without a one-line justification in the PR description
  and, if non-trivial, an ADR.
- Frontend talks to the backend only through the documented API contracts
  (`docs/09_API_CONTRACTS.md`). No hidden endpoints.
