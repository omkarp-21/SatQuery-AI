# Architecture Decision Log

Chronological record of significant technical decisions. Newest first.
Format inspired by ADRs (lightweight).

---

## ADR-002 — Research repos isolated in `external/research/`, never merged

- **Date:** 2026-08-31
- **Status:** Accepted
- **Context:** Six upstream repos (GeoChat, Change-Agent, ChangeChat, ChangeFormer,
  RemoteCLIP, awesome-rs-vlms) are needed as references. Their environments
  mutually conflict — Python 3.8–3.10, PyTorch 1.10 vs 2.0, CUDA 10.2 vs 11.8,
  `transformers` 4.31/4.33/≥4.34, an OpenMMLab 1.x stack, `pydantic<2` via
  `gradio==3.35.2` — and every one conflicts with SatQuery's Python 3.11 /
  Pydantic v2 product environment. Details in `docs/research/`.
- **Decision:** Clone them (shallow, pinned commits) into `external/research/`,
  which is **gitignored and read-only**. Do not install their deps into the main
  environment; do not merge requirements. Each model gets its own isolated env or
  container (`docs/research/environment_strategy.md`). Product code never imports
  from `external/research/`; future integration goes through
  `packages/model_adapters/` invoking an isolated env by subprocess.
- **Consequences:** Reproducible references without dependency hell. Re-clone via
  `make clone-research`. Integration cost per model is one env/container + one
  adapter. `awesome-rs-vlms` is literature only. Checkpoints/datasets deferred.

## ADR-001 — Monorepo split: apps/ + packages/

- **Date:** 2026-08-31
- **Status:** Accepted
- **Context:** The initial scaffold put everything under `backend/` (with an inner
  `satquery/` package) and `frontend/`, `models/`, `research/`, `infra/`. As the
  pipeline stages, the geospatial engine, the adapter layer and the evidence
  system grow, they need independent test/lint/versioning and clear dependency
  directions; a single backend package blurs that.
- **Decision:** Adopt a monorepo: `apps/{backend,frontend}` for deployables and
  `packages/{core,geospatial,agents,evidence,model_adapters}` as installable
  src-layout packages. Move `backend/satquery/<stage>` into the matching package,
  `models/adapters` → `packages/model_adapters`, `research/` → `external/research`,
  `infra/` → `infrastructure/`. Pipeline stage order and all `.claude/rules/` are
  unchanged; only the file locations move. Package deps are one-way (no cycles):
  `core` ← `agents`, `evidence`; `geospatial`, `model_adapters` standalone;
  `apps/backend` depends on all.
- **Consequences:** Per-package `pyproject.toml`, editable installs via
  `make setup-packages`. Docker build context is the repo root. Import paths
  change (`satquery.routing` → `satquery_core.routing`, `models.adapters.geochat`
  → `satquery_model_adapters.geochat`). CLAUDE.md, `architecture` rule and the
  `satquery-architecture` skill updated to match.

## ADR-000 — Template

- **Date:** YYYY-MM-DD
- **Status:** Proposed | Accepted | Superseded by ADR-XXX
- **Context:** _What forces are at play?_
- **Decision:** _What did we choose?_
- **Consequences:** _Trade-offs, follow-ups._
