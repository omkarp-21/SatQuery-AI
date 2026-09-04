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

**Shortest path: [`QUICKSTART.md`](QUICKSTART.md) — clone → install → launch → demo in ~5 min.**

```bash
cp .env.example .env          # fill in secrets
make setup                    # install packages + backend + frontend deps
make clone-research           # clone reference repos into external/research/ (read-only)
make download-models          # pull model checkpoints
make dev-backend              # uvicorn -> http://127.0.0.1:8000/  (self-contained UI, no build)
```

See the [`Makefile`](Makefile) for all targets.

---

## Release candidate (G18) — the 10-point run experience

| # | | |
|--:|---|---|
| 1 | **Prerequisites** | Python **3.11+**, `git`, ~12 GB disk, 8 GB+ RAM. No internet at run time. CPU-only is fully supported. |
| 2 | **Install** | `make setup`; place checkpoints under `models/cache/` (`scripts/download_models/`, ids + hashes in [`docs/G18_RELEASE_MANIFEST.md`](docs/G18_RELEASE_MANIFEST.md)). |
| 3 | **Launch** | `make dev-backend` → `http://127.0.0.1:8000/`. `make dev-frontend` for the React dashboard (optional). |
| 4 | **Demo** | Secondary (~15–60 s): *"Where is the largest ship?"* on `data/demo/grounding/scene.jpg`. Flagship (INVESTIGATE tab, ~90 s cold): the 4 tiles in `data/demo/investigation/` + the mission in `QUICKSTART.md`. Headless: `python scripts/demo/run_final_demo.py`. |
| 5 | **Test** | `make test`, or `pytest packages apps/backend/tests -q -m "not slow and not gpu and not integration"` (**419 fast tests**). |
| 6 | **CPU fallback** | every specialist + the agent run CPU-only; verified on the dev host. One model resident at a time (subprocess per specialist). |
| 7 | **GPU caveat** | **GPU FIT = UNVERIFIED** — `torch.cuda.is_available() == False` on the dev host; no numerical VRAM claim is made. |
| 8 | **Model caveats** | frozen stack (ADR-021). Deterministic planner is the **production default**; pure local LLM planner **rejected** (G16); hybrid LLM-intent planner **optional** (`SATQUERY_PLANNER=hybrid`, G17). Semantic-change *language* is an **experimental** composed baseline. |
| 9 | **Licence caveat** | **RemoteSAM checkpoint licence NOT STATED** (upstream repo, HF card and paper are silent) → RemoteSAM is packaged as an **optional** component; the rest of the product works without it. |
| 10 | **Known limitations** | see the box below and [`docs/PROJECT_STATUS.md`](docs/PROJECT_STATUS.md). |

### Known limitations (nothing hidden)

- Evaluation is **sanity-scale** (n = tens–hundreds), not a full benchmark; every number carries its N and a significance caveat.
- **DFC2020: adding SAR did not improve the downstream task** — the G12 +0.067 delta was within noise and **reversed** on the larger independent split (G18 Part 2). No statistical significance was established for any comparison.
- **4 GB GPU fit UNVERIFIED**; **RemoteSAM licence NOT STATED**.
- Confidence is an **evidence-derived category** (`HIGH/MEDIUM/LOW/INSUFFICIENT_EVIDENCE`), **never a probability or a number**.
- The pure local LLM planner is **rejected for production**; the hybrid intent planner is **optional** and does not beat the deterministic planner on this hardware.

Release audit + gate + final decision: [`docs/G18_RELEASE_REPORT.md`](docs/G18_RELEASE_REPORT.md) ·
[`docs/G18_RELEASE_AUDIT.md`](docs/G18_RELEASE_AUDIT.md) · claim wording: [`docs/sih/CLAIM_MATRIX.md`](docs/sih/CLAIM_MATRIX.md).

### SIH package (G19 — `FINAL_TECH_FREEZE = TRUE`)

The single reference for every slide, script and judge answer is
[`docs/G19_SIH_SOURCE_OF_TRUTH.md`](docs/G19_SIH_SOURCE_OF_TRUTH.md) (what we can /
cannot claim, exact metrics with N, exact limitation wording, frozen flagship
facts). Presentation set under [`docs/sih/`](docs/sih/): core story · pitch +
30-second explanation · architecture diagram · demo storyboard · 3-minute script ·
backup demo · results-slide data · novelty argument · competitor comparison ·
top-30 judge Q&A · negative-results defense · demo runbook · final checklist ·
product roadmap. After G19: bug fixes, demo reliability, docs and presentation
assets only — no new features / models / architecture.

**G20 — competition-grade UI (UI/UX only).** The local UI at
`http://127.0.0.1:8000/` was rebuilt into a geospatial-intelligence workstation:
top nav (ASK / INVESTIGATE / ABOUT / system status), a hero landing, and for
INVESTIGATE a 3-column workspace — MISSION + PLAN + ADAPTIVE EXECUTION on the
left, a spatial map/geometry viewer in the centre, FINDINGS + CONFIDENCE +
VERIFICATION + EVIDENCE + WARNINGS on the right, report export at the bottom.
Every value still comes straight from the backend response; no fabricated data,
progress, reasoning, or confidence. Same single file
(`apps/backend/app/static/index.html`), no build step, no CDN. See
[`docs/G20_UI_RELEASE_REPORT.md`](docs/G20_UI_RELEASE_REPORT.md),
[`docs/G20_UI_AUDIT.md`](docs/G20_UI_AUDIT.md),
[`docs/G20_UI_QA.md`](docs/G20_UI_QA.md); screenshots in
[`docs/sih/evidence/ui/`](docs/sih/evidence/ui/).

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
.venvs/satquery/Scripts/python.exe evaluation/agent/run_agent_eval.py --only mi-01

# full agent evaluation — 50 frozen missions, 13 quality metrics (each with its N)
.venvs/satquery/Scripts/python.exe evaluation/agent/run_agent_eval.py            # plan phase, all 50
.venvs/satquery/Scripts/python.exe evaluation/agent/run_agent_eval.py --exec 2   # + real-model exec sample
# reports -> evaluation/agent/reports/G15_AGENT_EVALUATION.{md,json}
# see docs/G15_AGENT_IMPLEMENTATION.md + docs/G15_AGENT_EVALUATION.md

# optional local LLM planner (Qwen2-VL-2B text-only; schema-repair + always falls back to the rule planner)
SATQUERY_PLANNER=llm .venvs/satquery/Scripts/python.exe -m uvicorn app.main:app --port 8000
```

**G16 — real LLM planner validation** (two planning arms, same 50 missions):

```bash
# 1. cache the local-LLM raw plans (slow: CPU-only 2B, ~5 min/mission -> a subset is used)
SATQUERY_PLANNER_PERSISTENT=1 .venvs/satquery/Scripts/python.exe evaluation/agent/run_g16_eval.py --llm-cache --only ss-01,tm-01,os-01,mi-01,ad-01
# 2. score ARM A (RuleBasedPlanner) vs ARM B (LLM) + write the report (fast)
.venvs/satquery/Scripts/python.exe evaluation/agent/run_g16_eval.py --plan
# 3. real-model execution: baseline (/analyze) vs LLM agent
.venvs/satquery/Scripts/python.exe evaluation/agent/run_g16_eval.py --exec 8
# reports -> evaluation/agent/reports/G16_REAL_LLM_EVALUATION.{md,json}
# see docs/G16_REAL_LLM_EVALUATION.md, docs/G16_AGENT_VALUE_ANALYSIS.md, docs/G16_ADVERSARIAL_TESTS.md

# flagship with the ACTUAL local LLM, two environments (change vs no-change) to show adaptivity
SATQUERY_PLANNER_PERSISTENT=1 .venvs/satquery/Scripts/python.exe scripts/demo/run_g16_flagship.py
```

**G16 finding (short):** the local 2 B LLM planner echoes its prompt example and
does not plan (semantic plan validity 0.25 vs the rule planner's 1.00, N=15).
Its plans are *structurally* valid, so a G16 **plan-intent cross-check**
(`_plan_intent_mismatch`) routes mission-wrong LLM plans to the visible
deterministic fallback. `RuleBasedPlanner` stays the default; the LLM is opt-in.
See `docs/G16_REAL_LLM_EVALUATION.md`.

**G17 — hybrid architecture** (`SATQUERY_PLANNER=hybrid`): the LLM produces a
small typed **`Intent`** only; a deterministic `PlanSynthesizer` builds the plan
from it. The LLM never picks a tool. Plus an **evidence-derived confidence
category** (`HIGH / MEDIUM / LOW / INSUFFICIENT_EVIDENCE` — not a probability;
`docs/G17_TRUST_LAYER.md`).

```bash
# cache the LLM intent JSON for all 100 frozen missions (persistent server; ~35 s/mission on CPU)
SATQUERY_PLANNER_PERSISTENT=1 .venvs/satquery/Scripts/python.exe evaluation/agent/run_g17_eval.py --intent-cache
# score ARM A (rule) vs ARM B (pure LLM, carried from G16) vs ARM C (hybrid)
.venvs/satquery/Scripts/python.exe evaluation/agent/run_g17_eval.py --plan
# real-model execution: hybrid agent vs the deterministic baseline
.venvs/satquery/Scripts/python.exe evaluation/agent/run_g17_eval.py --exec 12
# flagship with the hybrid architecture, change vs no-change
SATQUERY_PLANNER_PERSISTENT=1 .venvs/satquery/Scripts/python.exe scripts/demo/run_g17_flagship.py
# see docs/G17_HYBRID_AGENT_REPORT.md · docs/G17_ARCHITECTURE_DECISION.md · docs/G17_TRUST_LAYER.md
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
