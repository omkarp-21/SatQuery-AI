# AGENTS.md — SATQUERY

Contributor guide for humans and AI agents. Companion to [`CLAUDE.md`](CLAUDE.md).

## Setup

```bash
cp .env.example .env
make setup
```

## Build / test / lint

| Task | Command |
|------|---------|
| Run dev stack | `make dev` |
| Package tests | `make test-packages` (or `pytest packages/<pkg>`) |
| Backend tests | `make test-backend` (or `pytest` in `apps/backend/`) |
| Frontend tests | `make test-frontend` |
| All tests | `make test` |
| Lint + format | `make lint` |
| Evaluation suite | `make eval` |

## Code style

- **Python:** 3.11+, Pydantic v2, full type hints, `ruff` + `black`, Google-style docstrings.
- **TypeScript:** strict mode, no `any`, functional React components.
- Keep functions small; push orchestration into `apps/backend/app/services/` and pipeline logic into the matching `packages/*` stage module.

## The pipeline

`ingestion → metadata → routing → planning → registry → agents → specialists → fusion → verification → evidence → geospatial → confidence → provenance → reports`

Each stage is a package under `packages/`. A stage takes a typed input,
returns a typed output, and never reaches around the registry to call a model.

## Models

Add a model by writing an adapter in `packages/model_adapters/` and registering it in
`packages/model_adapters/model_registry.yaml`. Adapters must implement the shared interface
(load, predict, describe capabilities). Checkpoints go in `models/checkpoints/`
(gitignored) — provide a downloader in `scripts/download_models/`.

## Pull requests

- One logical change per PR. Update the matching `docs/NN_*.md` in the same PR.
- Add or update an evaluation case in `evaluation/cases/` when behavior changes.
- Record architectural choices in `docs/DECISIONS.md`.
- Green `make lint` and `make test` before requesting review.

## Do not

- Commit `.env`, model checkpoints, or files under `data/raw/` and `data/processed/`.
- Edit anything in `external/research/` — it is vendored reference code.
- Return a query result without an evidence trail and execution trace.
