# SatQuery AI — 5-minute Quickstart

The shortest path from a fresh clone to a running demo. Full detail is in
`README.md`; the reproducible manifest is `docs/G18_RELEASE_MANIFEST.md`.

> **CPU-only is fully supported.** No GPU is required. On this dev host CUDA is
> **UNVERIFIED** (no CUDA build); every specialist and the agent run on CPU.

## 0 · Prerequisites

- **Python 3.11+**, `git`, ~12 GB free disk (model checkpoints), 8 GB+ RAM.
- OS: Windows 11 / Linux / macOS. (Developed on Windows 11, Python 3.11.)
- No internet needed at run time — checkpoints are local.

## 1 · Install (once, ~2 min + checkpoint download)

```bash
git clone <repo> satquery && cd satquery
make setup                 # editable-installs the workspace packages + backend + frontend deps
# checkpoints: place under models/cache/ (see docs/G18_RELEASE_MANIFEST.md for ids + hashes)
#   scripts/download_models/  has the fetchers; models/ is gitignored
```

Isolated research venvs (`.venvs/tinyrs`, `.venvs/croma`, `.venvs/dofa`,
`.venvs/remotesam`, `.venvs/changeformer`, `.venvs/remoteclip`) hold the
conflicting model environments; the product venv is `.venvs/satquery`. `make
setup` does not build these — see `docs/research/environment_strategy.md`.

## 2 · Launch

```bash
make dev-backend           # uvicorn app.main:app --reload  ->  http://127.0.0.1:8000
# optional: make dev-frontend   ->  http://127.0.0.1:5173  (React dashboard)
```

## 3 · Open the UI + run a demo

Open **http://127.0.0.1:8000/** — a self-contained page (no build step).

- **Quick demo (~15–60 s):** upload `data/demo/grounding/scene.jpg`, ask
  *"Where is the largest ship?"* → box + mask overlay, geospatial position,
  verification.
- **Flagship (INVESTIGATE tab, ~90 s cold):** upload the 4 tiles in
  `data/demo/investigation/` (`t1_optical.tif`, `t2_optical.tif`,
  `s2_dfc_optical.tif`, `s1_dfc_sar.tif`) and ask:
  > *"Investigate this area. Identify significant changes between the two
  > observations, locate the affected structures, compare optical and SAR
  > evidence, and provide a verified summary."*
  → plan → 4 real specialists → change map + regions + grounded box + optical+SAR
  → cross-check → **verification** → **confidence category** (HIGH/MEDIUM/LOW) with
  a "why" list → GeoJSON export.

Or run the frozen demo set headless (real models):

```bash
.venvs/satquery/Scripts/python.exe scripts/demo/run_final_demo.py
# -> docs/sih/evidence/demos/final/{flagship_caseA_change,flagship_caseB_nochange,secondary_grounding}.json
#    CASE A: 4 tool calls, SUPPORTED, HIGH.  CASE B (no change): 2 tool calls, early-stopped, SUPPORTED, MEDIUM.
```

Export a report: `POST /investigate/report` (HTML), or
`scripts/demo/mission_report.py <investigation.json>`.

## 4 · Tests

```bash
make test                              # packages + backend + frontend
# or just the fast backend suite:
.venvs/satquery/Scripts/python.exe -m pytest packages apps/backend/tests -q -m "not slow and not gpu and not integration"
```

## Caveats you will see (by design — nothing is hidden)

| caveat | where |
|--------|-------|
| **GPU FIT = UNVERIFIED** — no CUDA on the dev host; CPU is the shipped path | `docs/G18_RELEASE_MANIFEST.md`, PROJECT_STATUS |
| **RemoteSAM checkpoint licence NOT STATED** — packaged as an optional component | `model_registry.yaml`, `docs/G18_RELEASE_REPORT.md` Part 6 |
| Deterministic planner is the **production default**; the pure local LLM planner is **rejected**; the hybrid intent planner is **optional** (`SATQUERY_PLANNER=hybrid`) | `docs/G17_ARCHITECTURE_DECISION.md` |
| Confidence is an **evidence-derived category**, never a probability or a number | `docs/G17_TRUST_LAYER.md` |
| Semantic-change *language* is an **experimental composed baseline**, not a learned temporal VLM | `docs/research/EVIDENCE_LEDGER.md` |
| Evaluation is **sanity-scale** (n = tens–hundreds), not a full benchmark; significance caveats stated per number | every eval report |
