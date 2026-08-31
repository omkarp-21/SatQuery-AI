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
| API | [`backend/app/`](backend/app/) | [`docs/09_API_CONTRACTS.md`](docs/09_API_CONTRACTS.md) |
| Core pipeline | [`backend/satquery/`](backend/satquery/) | [`docs/03_SYSTEM_ARCHITECTURE.md`](docs/03_SYSTEM_ARCHITECTURE.md) |
| Agents & routing | [`backend/satquery/agents/`](backend/satquery/agents/) | [`docs/06_AGENT_ARCHITECTURE.md`](docs/06_AGENT_ARCHITECTURE.md) |
| Model adapters | [`models/adapters/`](models/adapters/) | [`docs/05_MODEL_ARCHITECTURE.md`](docs/05_MODEL_ARCHITECTURE.md) |
| Evidence engine | [`backend/satquery/evidence/`](backend/satquery/evidence/) | [`docs/07_EVIDENCE_ENGINE.md`](docs/07_EVIDENCE_ENGINE.md) |
| Geospatial engine | [`backend/satquery/geospatial/`](backend/satquery/geospatial/) | [`docs/08_GEOSPATIAL_ENGINE.md`](docs/08_GEOSPATIAL_ENGINE.md) |
| Frontend | [`frontend/`](frontend/) | [`docs/10_FRONTEND_SPEC.md`](docs/10_FRONTEND_SPEC.md) |
| Evaluation | [`evaluation/`](evaluation/) | [`docs/11_EVALUATION_PLAN.md`](docs/11_EVALUATION_PLAN.md) |

## Quickstart

```bash
cp .env.example .env          # fill in secrets
make setup                    # install backend + frontend deps
make download-models          # pull model checkpoints
make dev                      # run API + frontend + supporting services
```

See the [`Makefile`](Makefile) for all targets.

## Repository layout

```
backend/     FastAPI app + satquery pipeline package
models/      Model adapters, checkpoints, registry
frontend/    React app (maps, evidence, execution-trace views)
data/        raw / processed / demo / manifests
evaluation/  datasets, scripts, metrics, cases, reports
research/    papers, benchmarks, reference repos, model comparison
scripts/     setup / download / benchmark / demo helpers
infra/       docker + nginx
docs/        numbered design docs + decision log
```

## Contributing

Read [`AGENTS.md`](AGENTS.md) and [`CLAUDE.md`](CLAUDE.md) before making changes.
Record notable decisions in [`docs/DECISIONS.md`](docs/DECISIONS.md).
