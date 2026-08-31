---
name: fullstack-engineering
description: General full-stack engineering practice for SatQuery — how the FastAPI backend, the satquery pipeline package, and the React frontend fit together; API contract discipline, error propagation from pipeline to UI, dev workflow, and where a given kind of change belongs. Invoke for cross-cutting work that spans backend and frontend or doesn't fit a single specialist skill.
---

# Full-Stack Engineering

## Where things belong

| Kind of change | Location |
|----------------|----------|
| New HTTP endpoint / request-response shape | `backend/app/api/` + `schemas/`, doc in `docs/09_API_CONTRACTS.md` |
| Orchestration across stages, background jobs | `backend/app/services/` |
| A step in the query pipeline | `backend/satquery/<stage>/` |
| Model wrapping | `models/adapters/` + registry |
| UI screen / component | `frontend/src/` (`pages/`, `features/`, `components/`) |
| Map layer / evidence overlay | `frontend/src/maps/`, `frontend/src/evidence/` |
| Config / secret | `.env` (+ `.env.example`), read via `app/core/` settings |

## API contract discipline

- The contract in `docs/09_API_CONTRACTS.md` is authored before the endpoint ships,
  with request + response examples.
- Backend response models (Pydantic) and frontend types are two mirrors of that
  one contract. Change the doc, then both sides.
- Versioned path prefix (`/api/v1`). Additive changes only within a version.
- Errors use a single typed envelope `{error: {code, message}}` — sanitized, no
  stack traces or internal paths.

## Error propagation

Pipeline raises specific `SatQueryError` subclasses → `services` maps them to the
error envelope + HTTP status → frontend renders the matching error state (which is
designed, per `frontend-design`). A partial result (some specialists failed) is a
**200 with lowered confidence and a note**, not an error — the trace shows what
happened.

## Dev workflow

```bash
make up            # db + redis + minio
make dev-backend   # :8000, --reload
make dev-frontend  # :5173, proxies /api -> :8000
make test && make lint
```

Or `make dev` for the full docker-compose stack.

## Cross-cutting checklist

- Contract doc updated on both sides.
- Pipeline error types map to UI states.
- Loading / empty / error states exist in the UI.
- Logging at the new boundary with the query id.
- Tests on both sides; demo path still runs.
- Docs (`docs/NN_*.md`) updated in the same change.

## When to defer to a specialist skill

Geospatial code → `geospatial-engineering`; model wrapping → `model-integration`;
orchestration internals → `agent-orchestration`; visuals → `frontend-design` /
`map-ui`; anything about numbers → `evaluation`.
