# CLAUDE.md — SATQUERY

Guidance for AI coding agents working in this repo. Humans: see [`README.md`](README.md).

## What this project is

Agentic natural-language query system over satellite imagery. A query is planned,
routed to specialist vision-language models, fused, verified, and returned with an
evidence trail. Judged for SIH — correctness, explainability, and demo polish matter.

## Where things live

- `backend/app/` — FastAPI: `api/` routes, `core/` config+wiring, `schemas/` Pydantic models, `services/` orchestration, `main.py` entrypoint.
- `backend/satquery/` — the pipeline package. Stage order:
  `ingestion → metadata → routing → planning → registry → agents → specialists → fusion → verification → evidence → geospatial → confidence → provenance → reports`.
- `models/adapters/` — one file per model (`geochat`, `change_agent`, `changechat`, `changeformer`, `remoteclip`). Each exposes a uniform adapter interface. Registry: `models/model_registry.yaml`.
- `frontend/src/` — React. Feature dirs: `maps/`, `evidence/`, `execution-trace/`, `pages/`, shared `components/`, `features/`.
- `evaluation/` — datasets, scripts, metrics, cases, reports. Keep eval cases in `evaluation/cases/`.
- `docs/` — numbered specs are the source of truth. Update the relevant doc in the same change as the code.
- `research/repos/` — vendored reference implementations. Do not edit; read for reference only.

## Conventions

- **Python:** 3.11+, FastAPI, Pydantic v2, `ruff` + `black`, type hints required. Package manager per `backend/pyproject.toml`. Tests with `pytest` in `backend/tests/`.
- **Frontend:** TypeScript, keep components typed; colocate tests.
- **Adapters:** never call a model directly from the pipeline — go through its adapter and the registry.
- **Provenance:** every answer must carry evidence + execution trace. Don't add a code path that returns a result without recording provenance.
- **Secrets:** only via `.env` (see `.env.example`). Never commit checkpoints, raw data, or `.env`.
- **Decisions:** append to `docs/DECISIONS.md` for anything architectural.

## Common commands

```bash
make setup            # install deps
make dev              # run everything
make test             # backend + frontend tests
make lint             # ruff + black + eslint
make eval             # run evaluation suite
```

## Guardrails

- Large binaries (`models/checkpoints/`, `data/raw/`, `data/processed/`) are gitignored — keep it that way.
- Prefer editing an existing pipeline stage over adding a new top-level package.
- If a change spans stages, note the data contract in the stage's module docstring.
