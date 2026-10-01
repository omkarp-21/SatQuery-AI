# SatQuery — Architecture

Module-by-module walkthrough of the real data flow. For the six-phase principle and fixed stage order, see `CLAUDE.md`; for decisions, `DECISIONS.md`.

## Request lifecycle

### `POST /analyze` (single decision, one or two specialists)

1. `apps/backend/app/api/analyze.py` resolves image paths under `SATQUERY_DATA_DIR` (default: repo `data/`), with path-traversal guards.
2. `services/analyze.py::interpret_query` maps the query to an intent via keywords (no LLM).
3. `satquery_core.routing.router::route` reads `packages/model_adapters/model_registry.yaml` and returns a `RoutingDecision` (task, specialists, rule name, code, input order).
4. The matching slice in `services/` runs: `vqa_slice.py` (TinyRS) · `grounding_slice.py` (RemoteSAM) · `temporal_slice.py` (ChangeFormer) · `multimodal_slice.py` (CROMA/DOFA) · `scene_slice.py` (RemoteCLIP) · `semantic_change_baseline.py` (ChangeFormer + RemoteCLIP, composed).
5. `services/normalize.py::normalize` flattens the specialist output into `NormalizedResponse` — only relevant fields are filled; caveats go to `warnings`; nothing is invented.

### `POST /investigate` (multi-step agent)

1. `api/investigate.py` saves uploads to a per-request sandbox `data/uploads/<id>/` and calls `services/agent_runner.py::run_investigation`.
2. `order_investigation_inputs` re-orders images by content (co-registered pair first by shape+band group, SAR last) — upload order is not trusted.
3. `make_planner()` picks `RuleBasedPlanner` (default), `LlmPlanner`, or `HybridPlanner` per `SATQUERY_PLANNER`. The planner emits a typed `AgentPlan` from the closed 12-task / 12-tool ontology (`packages/agents/.../agent/registry.py`, `schemas.py`).
4. The 12-check policy layer (`agent/policy.py`) rejects illegal plans (wrong tool for task, cycles, >8 steps, misregistered temporal pairs, …).
5. The bounded executor runs tool calls one at a time (each a specialist adapter via subprocess), then observe → verify → structured replan (`ReplanReason` enum; `replans[]` surfaced) or early stop (`_mission_complete`, `early_stopped`).
6. `derive_investigation_status` sets the top-level `SUCCESS / PARTIAL / BLOCKED / FAILED`; on BLOCKED, verification is forced to `NOT_APPLICABLE` and the conclusion is rewritten in plain language.
7. `api/investigate.py` then burns `overlay.png` (`services/overlay.py`: T2 base + change-mask tint + grounding box) and prepends it to `provenance.input_files`.

### Other endpoints

- `POST /scene` → `scene_slice.py` (RemoteCLIP ranking only; explicitly not VQA).
- `POST /change` → `api/change.py` + temporal slice (ChangeFormer mask + metrics; gate-refused pairs never reach the model).
- `POST /investigate/report` → `services/report.py` (HTML report from an investigation result).
- `GET /artifact?req=<id>&name=<file>` → `api/product.py` (sandboxed file serving for masks/overlays). `GET /` serves `app/static/index.html`.

## Key abstractions

| Abstraction | Where | What it is |
|---|---|---|
| `AdapterRequest` / `RawOutput` / `NormalizedOutput` | `packages/model_adapters/.../base.py` | The contract every specialist adapter implements (`validate / execute / normalize_output / provenance` + `run()` template). VQA requests to non-VQA adapters raise `UnsupportedTaskError`. |
| `RemoteClipAdapter`, `ChangeFormerAdapter`, `CromaAdapter`, `DofaAdapter`, `TinyRsAdapter`, `RemoteSamAdapter` | `packages/model_adapters/src/satquery_model_adapters/` | Subprocess bridges: each shells out to `scripts/research/*_infer.py` under `.venvs/<model>` (`_bridge.py`: `venv_python`, `run_bridge`, `sha256`). Product code never imports weights or research repos. |
| `RoutingDecision` | `packages/core/.../routing/` | Deterministic routing result: task, specialists, rule, code, inputs, order, status. |
| `AgentPlan`, `Intent`, `TaskFamily`, `Capability` | `packages/agents/.../agent/` | Typed plan representation; `Intent` is the small object the hybrid LLM path is allowed to produce (never a tool choice). `repair.py` salvages malformed LLM JSON or falls back visibly. |
| `EvidenceItem` | `packages/evidence/.../models.py` | Typed observation (ranking, box, mask, embedding) with spatial region + payload. No confidence field by design. |
| `VerificationResult` | `packages/evidence/.../verifier.py` | Deterministic structural checks → `SUPPORTED / CONTRADICTED / INSUFFICIENT_EVIDENCE / NOT_APPLICABLE`. |
| `assess_confidence` | `apps/backend/app/services/trust.py` | Evidence-derived category `HIGH / MEDIUM / LOW / INSUFFICIENT_EVIDENCE` with additive rules and conservative caps. Not a probability; `score` is never rendered. |
| `Provenance` | `packages/evidence/.../provenance/` | Standardized `from_adapter` block + `scrub()`; per-request input digests, checkpoint hashes, timings, `planner_attempt`, `encoder_mode`. |
| `NormalizedResponse` | `apps/backend/app/services/normalize.py` | The single flat schema all `/analyze` paths return. |

## How components talk to each other

- **API → packages:** the backend imports the workspace packages (editable installs) and calls slice functions; slices call adapters; adapters call subprocess bridges. Dependencies point one way: `agents → core`, `evidence → core`, `model_adapters` standalone.
- **Routing reads the registry file:** `model_registry.yaml` (capabilities, modalities, routing table) is the only source of model truth at runtime — no hardcoded model names in routing code.
- **Executor ↔ specialists:** synchronous request/response per tool call; each call returns `(payload, evidence, verification, resolution, model)` and appends a timeline entry. Failures are structured (`failures[]`, `warnings[]`), never exceptions to the client.
- **Geospatial as a gate, not a stage:** `satquery_geospatial` (`validate_geotiff`, `check_pair_compatibility`) runs before any model executes on rasters; a failed gate short-circuits to `VALIDATION_FAILED` / `BLOCKED`.
- **UI ↔ backend:** the single-file UI calls the JSON endpoints with `fetch` and renders every value straight from the response (verified by contract tests against frozen captures). No separate BFF layer.
- **Eval ↔ product:** `evaluation/agent/*.py` and `evaluation/scripts/*.py` import the same slices/adapters the API uses, over frozen mission/dataset files, so measurements reflect production code paths.
