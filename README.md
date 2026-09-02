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

## Run the SatQuery MVP locally  *(G13)*

The frozen model stack (G12) runs **CPU-only** — no CUDA required. Each specialist
runs in its own `.venvs/<model>` and is loaded lazily per request (subprocess,
nothing stays resident). First call to a model is a cold start; later calls are warm.

```bash
# 1. one-time: per-model venvs + checkpoints (see docs/G13_PRODUCTIZATION_REPORT.md)
#    .venvs/{satquery,tinyrs,remotesam,changeformer,remoteclip,croma,dofa}
#    models/cache/{tinyrs,remotesam,changeformer,remoteclip,croma,dofa}

# 2. launch the API + UI (Windows PowerShell / Git Bash)
cd apps/backend
../../.venvs/satquery/Scripts/python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000

# 3. open the UI
#    http://127.0.0.1:8000/          -> upload 1-2 images, type a query, Analyze
#    http://127.0.0.1:8000/docs      -> OpenAPI (POST /analyze/upload, /analyze, /change, /scene)
```

**Run the 5 demo scenarios (real outputs, nothing faked):**

```bash
.venvs/satquery/Scripts/python.exe scripts/demo/run_demos.py            # all 5
.venvs/satquery/Scripts/python.exe scripts/demo/run_demos.py --demo 2   # just grounding
# captures written to docs/sih/evidence/demos/g13_demo*.json
```

### Agentic investigator  *(G14)*

In the UI, toggle **INVESTIGATE** (or `POST /investigate`). A natural-language
**mission** is decomposed by a text-only planner into a typed plan, checked by a
12-rule deterministic policy layer, then run by a bounded executor (≤ 8 specialist
calls) that observes each result and decides the next action. The deterministic
router is not replaced — it is the execution guard; if the planner is unavailable
the request falls back to `/analyze`.

```bash
# flagship mission (planner-produced, not a hard-coded workflow)
.venvs/satquery/Scripts/python.exe evaluation/agent/run_agent_eval.py --only inv-1

# full agent evaluation — 30 frozen missions
.venvs/satquery/Scripts/python.exe evaluation/agent/run_agent_eval.py            # plan phase
.venvs/satquery/Scripts/python.exe evaluation/agent/run_agent_eval.py --exec 2   # + exec 2/category
# report -> evaluation/agent/reports/latest.json ; see docs/G14_AGENTIC_REPORT.md

# optional local LLM planner (Qwen2-VL-2B text-only; always falls back to the rule planner)
SATQUERY_PLANNER=llm .venvs/satquery/Scripts/python.exe -m uvicorn app.main:app --port 8000
```

| Demo | Query | Task → model |
|------|-------|--------------|
| 1 | "What objects are visible in this satellite image?" | VQA → TinyRS-2B |
| 2 | "Where is the largest building?" | Grounding → RemoteSAM |
| 3 | "What changed between these two images?" | Temporal → ChangeFormer |
| 4 | "Compare the optical and SAR information for this area." | Optical+SAR → CROMA |
| 5 | "Describe what changed and where, with supporting evidence." | Composed semantic baseline (ChangeFormer + RemoteCLIP) |

**Tests:**

```bash
.venvs/satquery/Scripts/python.exe -m pytest packages apps/backend -q -m "not slow"   # fast, ~3 min, 179 tests
.venvs/satquery/Scripts/python.exe -m pytest apps/backend/tests/test_g13_integration.py apps/backend/tests/test_g14_agent.py -q -m slow   # real models, slow
```

**Known limitations (G13 — not hidden):** evaluation samples are sanity-scale;
the CROMA optical+SAR delta and the LoRA adaptation gain are **not
significance-tested**; **4 GB VRAM is unverified** (CPU-only host, no VRAM figure);
**RemoteSAM licence is NOT STATED**; no confidence value is produced (by design);
no learned temporal semantic VLM; the LoRA adapter is not yet persisted into
production. See [`docs/G13_PRODUCTIZATION_REPORT.md`](docs/G13_PRODUCTIZATION_REPORT.md).

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
