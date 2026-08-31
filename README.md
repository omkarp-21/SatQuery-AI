# SATQUERY

Natural-language querying of satellite imagery with agentic routing, multi-model
fusion, geospatial reasoning, and verifiable evidence.

> Built for SIH. See [`docs/00_PROJECT_VISION.md`](docs/00_PROJECT_VISION.md) for the north star
> and [`docs/16_SIH_JUDGING_STRATEGY.md`](docs/16_SIH_JUDGING_STRATEGY.md) for scoring focus.

## What it does

Ask questions like _"What changed along this coastline between 2019 and 2024?"_ or
_"Find informal settlements within 2 km of this river."_ SATQUERY plans the query,
routes it to the right specialist vision-language models, fuses their outputs,
verifies the result, and returns an answer backed by an inspectable evidence trail
and an execution trace.

## Architecture at a glance

| Layer | Path | Docs |
|-------|------|------|
| API | [`apps/backend/app/`](apps/backend/app/) | [`docs/09_API_CONTRACTS.md`](docs/09_API_CONTRACTS.md) |
| Pipeline spine | [`packages/core/`](packages/core/) | [`docs/03_SYSTEM_ARCHITECTURE.md`](docs/03_SYSTEM_ARCHITECTURE.md) |
| Agents & routing | [`packages/agents/`](packages/agents/) | [`docs/06_AGENT_ARCHITECTURE.md`](docs/06_AGENT_ARCHITECTURE.md) |
| Model adapters | [`packages/model_adapters/`](packages/model_adapters/) | [`docs/05_MODEL_ARCHITECTURE.md`](docs/05_MODEL_ARCHITECTURE.md) |
| Evidence engine | [`packages/evidence/`](packages/evidence/) | [`docs/07_EVIDENCE_ENGINE.md`](docs/07_EVIDENCE_ENGINE.md) |
| Geospatial engine | [`packages/geospatial/`](packages/geospatial/) | [`docs/08_GEOSPATIAL_ENGINE.md`](docs/08_GEOSPATIAL_ENGINE.md) |
| Frontend | [`apps/frontend/`](apps/frontend/) | [`docs/10_FRONTEND_SPEC.md`](docs/10_FRONTEND_SPEC.md) |
| Evaluation | [`evaluation/`](evaluation/) | [`docs/11_EVALUATION_PLAN.md`](docs/11_EVALUATION_PLAN.md) |
| Research refs | [`external/research/`](external/research/) | [`docs/research/`](docs/research/) |

## Quickstart

```bash
cp .env.example .env          # fill in secrets
make setup                    # install packages + backend + frontend deps
make clone-research           # clone reference repos into external/research/ (read-only)
make download-models          # pull model checkpoints (later)
make dev                      # run API + frontend + supporting services
```

See the [`Makefile`](Makefile) for all targets.

## Repository layout

```
apps/
  backend/     FastAPI app — wires the packages into query endpoints
  frontend/    React app (maps, evidence, execution-trace views)
packages/
  core/          pipeline spine + typed contracts (satquery_core)
  geospatial/    raster/vector engine (satquery_geospatial)
  agents/        deterministic orchestration + specialists (satquery_agents)
  evidence/      evidence, verification, provenance (satquery_evidence)
  model_adapters/ specialist adapters + model_registry.yaml
external/research/  vendored upstream repos — READ-ONLY, gitignored
models/      checkpoints/ + cache/ (gitignored)
data/        raw / processed / demo
evaluation/  datasets, scripts, metrics, cases, reports
infrastructure/  docker + nginx
scripts/     setup / download / benchmark / demo helpers
docs/        numbered design docs + decision log + research/ inventory
```

## Contributing

Read [`AGENTS.md`](AGENTS.md) and [`CLAUDE.md`](CLAUDE.md) before making changes.
Record notable decisions in [`docs/DECISIONS.md`](docs/DECISIONS.md).
