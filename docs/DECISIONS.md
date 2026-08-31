# Architecture Decision Log

Chronological record of significant technical decisions. Newest first.
Format inspired by ADRs (lightweight).

---

## ADR-004 — First SatQuery specialist stack = RemoteCLIP + ChangeFormer (from G1 evidence)

- **Date:** 2026-09-01
- **Status:** Accepted (revisit when a GPU box exists — `docs/28`/open-mindedness rule)
- **Context:** G1 runtime validation (`docs/research/runtime_validation.md`) ran the
  smallest official inference example for each of the 5 candidate repos on the dev
  host (Windows 11, RTX 3050 Ti **4 GB**, no conda/Docker/WSL).
  - **RemoteCLIP** — RUNNING. Pure pip, CPU, Apache-2.0, official zero-shot example
    correct (97.8% airport), ~150 ms/query, ~1.6 GB RSS. Integration cost LOW.
  - **ChangeFormer** — RUNNING with **no source edits**, env pins only
    (`numpy<1.24` for removed `np.str`; `torch<2.6` for its `torch.load`). MIT,
    `demo_LEVIR.py` exit 0, change-IoU 0.83 / F1 0.91 on 7 bundled labelled
    samples (reproduction, n=7), 41 M params, ~790 ms/pair CPU. Cost LOW–MEDIUM.
  - **GeoChat** — BLOCKED. 7B merged model > 4 GB VRAM (even 4-bit ≈5–6 GB);
    `deepspeed==0.9.5` fails to build on Windows; `bitsandbytes==0.41.0` Linux-only.
  - **Change-Agent** — BLOCKED. `mmcv==1.3.1` unbuildable (no wheels; ancient
    setup.py; needs CUDA toolkit + MSVC); internal `transformers` 4.33 vs ≥4.34.
  - **ChangeChat** — BLOCKED. No released weights, no `requirements.txt`.
- **Alternatives considered:** (a) block all SatQuery progress on a GPU box —
  rejected, RemoteCLIP + ChangeFormer already cover V0 + the V1 change path;
  (b) port ChangeFormer / build mmcv now — rejected, environment cost with no
  measured payoff yet (scope rule); (c) drop change detection until GeoChat is
  available — rejected, ChangeFormer is the stronger evidence today.
- **Decision:** The **first specialist stack is RemoteCLIP + ChangeFormer.**
  Write their adapters next (they are the only two with a proven runnable path).
  GeoChat integration is **gated on provisioning a Linux GPU ≥16 GB** and blocks
  EXP-001 until then; use a small CPU-runnable control VLM for EXP-001 in the
  interim where the task allows. Change-Agent stays a TEST-FURTHER item for
  EXP-003 on Linux+conda. ChangeChat is **rejected for now**.
- **Trade-off:** No single-image VQA/grounding capability in the local prototype
  until a GPU is available — the demo's single-image path leans on RemoteCLIP
  (retrieval/zero-shot) rather than free-form VQA at first.
- **Consequence:** `.venvs/remoteclip` and `.venvs/changeformer` are the reference
  environments (gitignored); checkpoints in `models/cache/` (gitignored).
  `model_registry.yaml` capability entries to be updated with the measured facts.
  This does **not** change the pipeline architecture (ADR-001) or any rule.

## ADR-003 — `chatgpt.context.md` as persistent strategic memory; `docs/PROJECT_STATUS.md` as living status

- **Date:** 2026-08-31
- **Status:** Accepted
- **Context:** Strategy, SIH evaluation criteria, the winning objective, model
  candidates, experiment plan, red-team questions and jury lenses were living in
  chat history and would be lost between sessions. Claude needs a fixed place to
  read strategic intent and a fixed place to record honest project state.
- **Alternatives considered:** (a) keep it only in `CLAUDE.md` — too long, mixes
  operating rules with strategy; (b) split across the numbered docs — dilutes the
  "read this first" signal; (c) a Claude-memory file only — not visible to the
  team or in the repo.
- **Decision:** Commit `chatgpt.context.md` at the repo root as canonical,
  non-disposable strategic memory (synced with reality, esp. §33). Add
  `docs/PROJECT_STATUS.md` as the living status file (DONE / IN PROGRESS / BLOCKED
  / MISSING / RESEARCH NEEDED / METRICS / RISKS / NEXT 3 ACTIONS / WIN SCORECARD),
  updated every significant session. Wire both into `CLAUDE.md` "Read first",
  `docs/21`, and the `documentation` rule.
- **Trade-off:** Two more files to keep current; drift is a real risk if sessions
  skip the end-of-session update.
- **Consequence:** `chatgpt.context.md` §11 experiments are the seed for
  `docs/19_EXPERIMENT_REGISTRY.md`; §21 structure matches ADR-001; §24 defines the
  status schema now implemented. The three-numbers rule (doc 18) is echoed in
  context §10/§16.

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
