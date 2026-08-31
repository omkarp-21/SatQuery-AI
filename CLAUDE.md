# SATQUERY AI

## Read first (every serious session)

1. [`chatgpt.context.md`](chatgpt.context.md) — persistent strategic memory and
   SIH evaluation brain. **Not disposable documentation.** Keep it in sync with reality.
2. This file (`CLAUDE.md`).
3. [`docs/PROJECT_STATUS.md`](docs/PROJECT_STATUS.md) — live DONE / BLOCKED /
   MISSING / METRICS / NEXT 3 / WIN SCORECARD. Update it every significant session.
4. [`docs/DECISIONS.md`](docs/DECISIONS.md), then the relevant numbered `docs/`.
5. [`docs/research/`](docs/research/) — model inventory + experiment registry
   ([`docs/19_EXPERIMENT_REGISTRY.md`](docs/19_EXPERIMENT_REGISTRY.md)).

## Mission

Build SatQuery AI for **SIH 2026 problem 26167**.

**Goal:** Create a reliable agentic multimodal remote-sensing intelligence system
that accepts natural-language queries over single-image, bi-temporal, and
optical–SAR imagery, and returns answers backed by verifiable evidence.

## Core principle

**Plan → Validate → Execute → Verify → Explain → Audit**

Every query flows through these six phases. No phase is skipped, even under time
pressure. If a phase cannot complete, the pipeline fails loudly with a reason —
it never guesses past it.

## Non-negotiables

- Never invent model capabilities.
- Never fabricate evaluation metrics.
- Never silently alter geospatial metadata.
- Never treat SAR as ordinary RGB.
- Every specialist must expose a standard adapter interface.
- Every execution must generate provenance metadata.
- Every model output must be independently verifiable where possible.
- Prefer reuse of proven open-source research implementations.
- Keep research repositories isolated from product code.
- Do not add dependencies without justification.
- Test before integrating.

## Repository layout (monorepo)

```
apps/
  backend/     FastAPI app — wires the packages into query endpoints (app/)
  frontend/    React dashboard (src/: maps, evidence, execution-trace, pages)
packages/      installable workspace packages (src layout):
  core/          satquery_core   — ingestion, metadata, routing, planning,
                                   registry, fusion, confidence, reports + contracts
  geospatial/    satquery_geospatial — raster/vector I/O, reprojection, alignment
  agents/        satquery_agents — agents + specialists stages (deterministic)
  evidence/      satquery_evidence — evidence, verification, provenance
  model_adapters/ satquery_model_adapters — specialist adapters + model_registry.yaml
external/research/  vendored reference repos — READ-ONLY, gitignored, never imported
models/        checkpoints/ + cache/  (gitignored)
data/          raw/ processed/ demo/  (raw/processed gitignored)
evaluation/    datasets, scripts, metrics, cases, reports
infrastructure/  docker/ nginx/ (+ research/ images later)
docs/          numbered specs + DECISIONS.md + research/ (inventory, compatibility)
```

## Pipeline

Stages run in this fixed order (across `packages/core`, `packages/agents`,
`packages/evidence`, `packages/geospatial`):

`ingestion → metadata → routing → planning → registry → agents → specialists →
fusion → verification → evidence → geospatial → confidence → provenance → reports`

Details:
- [`docs/03_SYSTEM_ARCHITECTURE.md`](docs/03_SYSTEM_ARCHITECTURE.md)
- [`docs/05_MODEL_ARCHITECTURE.md`](docs/05_MODEL_ARCHITECTURE.md)
- [`docs/06_AGENT_ARCHITECTURE.md`](docs/06_AGENT_ARCHITECTURE.md)
- [`docs/DECISIONS.md`](docs/DECISIONS.md) ADR-001 (monorepo split)

The custom [`satquery-architecture`](.claude/skills/satquery-architecture/SKILL.md)
skill holds the authoritative structure — consult it before any restructuring.

## Commands

```bash
make setup                 # editable-install packages, backend, frontend deps
make setup-packages        # just the workspace packages
make dev-backend           # uvicorn app.main:app --reload  (from apps/backend)
make dev-frontend          # vite dev server on :5173
make test                  # packages + backend + frontend
make test-packages         # pytest across packages/*
make lint                  # ruff + black --check (packages, apps/backend) + eslint
make fmt                   # auto-format
make eval                  # python evaluation/scripts/run_suite.py
make clone-research        # (re)clone external/research/ at pinned commits
```

## Research repos — hands off

`external/research/` holds vendored upstream repos (GeoChat, Change-Agent,
ChangeChat, ChangeFormer, RemoteCLIP, awesome-rs-vlms). They are **read-only,
gitignored, and never imported** by product code. Their environments conflict with
each other and with SatQuery — see [`docs/research/`](docs/research/)
(`model_inventory.md`, `repository_compatibility.md`, `environment_strategy.md`).
Integration happens later via `packages/model_adapters/` calling an isolated
env/container by subprocess.

## How work is done here — `docs/17`–`docs/21`

SatQuery is a **research-backed working prototype**. Prototype quality and research
accuracy reinforce each other; the cadence is
**research → experiment → measure → integrate → improve → demonstrate**.

- [`docs/17_ENGINEERING_STRATEGY.md`](docs/17_ENGINEERING_STRATEGY.md) — two
  parallel tracks (product ∥ research), priority order, Definition of Feature/Research Complete.
- [`docs/18_RESEARCH_TO_ACCURACY.md`](docs/18_RESEARCH_TO_ACCURACY.md) — the core
  loop (never skip the baseline), accuracy engineering, model-selection principle,
  hypotheses H1–H5, failure-driven development, the novelty rule.
- [`docs/19_EXPERIMENT_REGISTRY.md`](docs/19_EXPERIMENT_REGISTRY.md) — every model
  trial has an `EXP-NNN` id and a `KEEP / REJECT / INVESTIGATE` decision. No
  off-the-record "trying models".
- [`docs/20_PROTOTYPE_ROADMAP.md`](docs/20_PROTOTYPE_ROADMAP.md) — V0 → V2 capability
  milestones, each with a research gate.
- [`docs/21_CLAUDE_WORKING_PRINCIPLES.md`](docs/21_CLAUDE_WORKING_PRINCIPLES.md) —
  the pre-flight checklist for any major feature. Read it first.

**The three numbers — never mix them:** (1) *paper result* — what the authors
report; (2) *our reproduction* — what we measure running their code; (3) *SatQuery
result* — what the integrated system scores under our evaluation. Only #3 may be
called "SatQuery's accuracy". Never: "the paper says X, so SatQuery does X."

## Hard constraints live in `.claude/rules/`

Load-bearing engineering constraints are in [`.claude/rules/`](.claude/rules/):
`architecture`, `python`, `typescript`, `geospatial`, `ai-models`, `testing`,
`security`, `git`, `documentation`, `scope`. Follow them literally.

## Expert behaviors live in `.claude/skills/`

Model-invoked skills in [`.claude/skills/`](.claude/skills/) carry deep domain
knowledge (remote sensing, geospatial engineering, model integration, agent
orchestration, evaluation discipline, map UI, demo engineering, …). Invoke the
relevant skill when a task enters its domain.

## Delegated review lives in `.claude/agents/`

Subagents in [`.claude/agents/`](.claude/agents/) handle scoped work and review:
`architect`, `remote-sensing-researcher`, `ml-engineer`, `geospatial-engineer`,
`backend-engineer`, `frontend-engineer`, `ai-evaluator`, `security-engineer`,
`performance-engineer`, `red-team-reviewer`, `hackathon-jury`. Route a change to
the matching specialist; run risky changes through `red-team-reviewer` and
demo-facing features through `hackathon-jury` before merge.

## Three voices, held in tension

- **Product** (`product-engineering` skill): ship aggressively, simplify, prioritize leverage.
- **Research** (`research-review` skill): claim conservatively, cite sources, no fabricated numbers.
- **Engineering** (`testing` / `performance` skills): measure everything, handle every error.

When they conflict, **research rigor wins over shipping speed.** "Move fast" must
never become "fake the AI or the metrics."

## Definition of Done

A feature is not complete until:

1. code works
2. tests exist
3. logging exists
4. errors are handled
5. documentation is updated
6. demo path works
