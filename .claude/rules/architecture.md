# Architecture Rules

- The pipeline stage order is fixed:
  `ingestion → metadata → routing → planning → registry → agents → specialists →
  fusion → verification → evidence → geospatial → confidence → provenance → reports`.
  Do not reorder, merge, or add top-level stages without an ADR in `docs/DECISIONS.md`.
- Each stage lives in `backend/satquery/<stage>/`, takes a typed Pydantic input,
  and returns a typed output. The contract is documented in the stage's module docstring.
- A stage never reaches around the `registry` to call a model directly. Models are
  invoked only through their adapter (`models/adapters/`).
- Orchestration logic lives in `backend/app/services/`. Pipeline logic lives in
  `backend/satquery/`. Model code lives in `models/`. Do not mix these.
- `research/repos/` is vendored reference code. Product code must never import from it.
- Data flows forward only. A later stage does not mutate an earlier stage's output;
  it produces a new typed object.
- Provenance is threaded through every stage. No code path returns a result without
  a provenance record attached.
- No new runtime dependency without a one-line justification in the PR description
  and, if non-trivial, an ADR.
- Frontend talks to the backend only through the documented API contracts
  (`docs/09_API_CONTRACTS.md`). No hidden endpoints.
