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
| Backend tests | `make test-backend` (or `pytest` in `backend/`) |
| Frontend tests | `make test-frontend` |
| All tests | `make test` |
| Lint + format | `make lint` |
| Evaluation suite | `make eval` |

## Code style

- **Python:** 3.11+, Pydantic v2, full type hints, `ruff` + `black`, Google-style docstrings.
- **TypeScript:** strict mode, no `any`, functional React components.
- Keep functions small; push orchestration into `backend/app/services/` and pipeline logic into `backend/satquery/<stage>/`.

## The pipeline

`ingestion → metadata → routing → planning → registry → agents → specialists → fusion → verification → evidence → geospatial → confidence → provenance → reports`

Each stage is a package under `backend/satquery/`. A stage takes a typed input,
returns a typed output, and never reaches around the registry to call a model.

## Models

Add a model by writing an adapter in `models/adapters/` and registering it in
`models/model_registry.yaml`. Adapters must implement the shared interface
(load, predict, describe capabilities). Checkpoints go in `models/checkpoints/`
(gitignored) — provide a downloader in `scripts/download_models/`.

## Pull requests

- One logical change per PR. Update the matching `docs/NN_*.md` in the same PR.
- Add or update an evaluation case in `evaluation/cases/` when behavior changes.
- Record architectural choices in `docs/DECISIONS.md`.
- Green `make lint` and `make test` before requesting review.

## Do not

- Commit `.env`, model checkpoints, or files under `data/raw/` and `data/processed/`.
- Edit anything in `research/repos/` — it is vendored reference code.
- Return a query result without an evidence trail and execution trace.
