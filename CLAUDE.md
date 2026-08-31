# SATQUERY AI

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

## Hard constraints live in `.claude/rules/`

Load-bearing engineering constraints are in [`.claude/rules/`](.claude/rules/):
`architecture`, `python`, `typescript`, `geospatial`, `ai-models`, `testing`,
`security`, `git`, `documentation`. Follow them literally.

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
