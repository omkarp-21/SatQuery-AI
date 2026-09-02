# G14 — Agent Implementation Map (Step 1 audit)

State of the repo after G13, mapped as `EXISTS / MISSING / REUSABLE / MODIFY /
NEW`. The G14 agent is built **on top of** the deterministic system — the router
stays the execution guard, the LLM becomes the planner.

## EXISTS (working — do not rebuild)

| Piece | Where | Notes |
|-------|-------|-------|
| `POST /analyze`, `POST /analyze/upload`, `GET /`, `GET /artifact` | `apps/backend/app/api/{analyze,product}.py` | G13 product surface |
| `run_analyze()` — validate → `interpret_query` (deterministic) → `route()` → dispatch 6 codes → evidence + verify + `resolution` | `apps/backend/app/services/analyze.py` | the deterministic spine |
| `NormalizedResponse` + `normalize()` | `apps/backend/app/services/normalize.py` | one flat schema; **reuse for the agent response** |
| Deterministic router `route(RoutingRequest) → RoutingDecision` | `packages/core/.../routing/router.py` | 8 codes; registry-driven; **this is the policy/execution guard — keep** |
| Specialist slices (each: validate → adapter → normalize → `EvidenceItem` + `Provenance` + `verify()`) | `app/services/{vqa,grounding,scene,temporal,semantic_change_baseline,multimodal}_slice.py` | `run_vqa`, `run_grounding`, `run_scene`, `run_change_slice` (+ `run_change_fallback`), `run_composed_semantic_change`, `run_joint_representation` / `run_joint_from_geotiffs` |
| `SpecialistAdapter` contract + subprocess isolation | `packages/model_adapters/` | frozen stack (G12); agent tools wrap the *slices*, never the adapters directly |
| Evidence / verification | `packages/evidence/` | `EvidenceItem`, `Provenance`, `verify()` (structural), `verify_semantic()` (model-independent) |
| Failure-aware `derive_resolution()` → 6 qualifiers | `app/services/failure_aware.py` | agent reuses this per step + at finish |
| Geospatial gate | `packages/geospatial/` | `validate_geotiff`, `check_pair_compatibility`, `read_raster_meta` |
| `model_registry.yaml` | `packages/model_adapters/` | frozen stack + routing table + capabilities |
| Vanilla UI | `apps/backend/app/static/index.html` | **modify, do not rewrite** — add MISSION/ASK + plan panel |
| Tests | `apps/backend/tests/`, `packages/*/tests/` | 153 fast + slow; **must stay green** |
| Demo fixtures | `data/demo/{vqa,grounding,scene,temporal,optical_sar}/` | reuse for agent missions |
| `packages/agents/` | `packages/agents/src/satquery_agents/` | **STUB** — empty `__init__` only; the natural home for the agent contracts |

## MISSING (build in G14)

| # | Gap |
|---|-----|
| 1 | A **typed tool registry** the planner sees as schemas (not Python access) — 10 tools with metadata (task_type, required/optional inputs, output schema, specialist, geo/modality requirements, allowed follow-ups, failure modes). |
| 2 | A **typed `AgentPlan`** (goal, inputs, steps[], constraints, expected_output; each step: id, task, tool, inputs, depends_on, reason, required_verification, success_condition). Pydantic; malformed → rejected, never executed. |
| 3 | A **finite task ontology** (`VALIDATE_INPUT`, `SCENE_UNDERSTANDING`, `VQA`, `GROUND_OBJECT`, `TEMPORAL_CHANGE`, `SEMANTIC_CHANGE`, `OPTICAL_SAR_ANALYSIS`, `EXTRACT_CHANGED_REGIONS`, `CROSS_CHECK_EVIDENCE`, `VERIFY`, `SUMMARIZE`, `FINALIZE`). |
| 4 | A **planner** — small/local, text-only, structured-JSON, pluggable. `Planner` protocol + `RuleBasedPlanner` (always available; feature→DAG over the ontology) + `LlmPlanner` (local Qwen2-VL-2B text mode via a new `scripts/research/planner_infer.py`, or an API provider via env) + `plan_with_fallback()`. |
| 5 | A **plan validation / policy layer** — the 12 checks (tool exists, task exists, modality available, image count, deps satisfied, tool allowed for task, geo requirements, capability match, no unsupported call, no cycle, step count ≤ max, output-schema compatibility). Rejects e.g. `RemoteSAM for VQA`. |
| 6 | A **bounded execution state machine** — `INITIAL → PLANNING → PLAN_VALIDATION → (EXECUTING → OBSERVING → VERIFYING → [REPLANNING])* → FINALIZING / FAILED`; ≤ 8 tool actions; no recursion; partial-but-honest result on cap. |
| 7 | **Observe / replan** — inspect intermediate results and conditionally choose next action (tiny change → skip grounding; grounding fail → record, no fabrication; geo fail → pixel-only; embedding → no invented fact; evidence contradiction → revise/withdraw claim). |
| 8 | **Agent memory** — bounded structured state (image ids, CRS, regions, masks, labels, model outputs by ref, evidence refs, verification statuses, failures). No images/embeddings in prompt context — refs only. |
| 9 | **Evidence-first synthesis** — final answer built from observations + evidence + verification + geo + failures + warnings. Deterministic template; optional constrained LLM summary. No unsupported claims. |
| 10 | **`POST /investigate`** → `AgentInvestigationResponse` (mission, plan, plan_status, steps, findings, spatial_results, evidence, verification, resolution, provenance, execution_trace, warnings, timings). Reuses normalized objects. |
| 11 | **UI: MISSION mode** — ASK / INVESTIGATE toggle; AGENT PLAN panel; LIVE STATUS (✓ / → / ○ / !); findings + map + evidence + verification + warnings + detailed trace. |
| 12 | **Deterministic fallback** — planner unavailable/timeout/malformed/unloadable → fall back to `run_analyze` where appropriate. Product usable without the planner. |
| 13 | **Agent eval** — `evaluation/agent/{frozen_missions.json (30), run_agent_eval.py, reports/}`; metrics: plan validity, tool-selection accuracy, task-order, execution success, evidence preservation, verification correctness, answer factual consistency, avg tool calls, failed-plan rate, latency. **Internal frozen eval, not a benchmark.** |
| 14 | **Baseline vs agent comparison** — deterministic `/analyze` vs agent on the multi-step missions. Prove functional value; do not assume it. |
| 15 | **Flagship investigation** — the T1/T2 optical + SAR mission, planner-produced (not hard-coded), several phrasings. |
| 16 | **Docs** — `docs/research/EXP-006_AGENTIC_PLANNER.md`, `docs/G14_AGENTIC_REPORT.md`; update `PROJECT_STATUS.md`, `README.md`, `API_CONTRACT.md`, `docs/sih/evidence/`. |

## REUSABLE (wire, don't reimplement)

- The 6 specialist slices → wrapped 1:1 as agent tool implementations in `agent_runner.py`.
- `route()` → the policy layer calls it to confirm a planned tool matches what the
  deterministic router would pick for that task+inputs (defense in depth).
- `derive_resolution()` → per-step verdict + final resolution.
- `normalize()` fields → the agent's `findings` / `spatial_results` surface.
- `interpret_query()` → a feature source for `RuleBasedPlanner` and for the
  deterministic fallback.
- G13 demo fixtures → agent mission inputs.

## MODIFY

| File | Change |
|------|--------|
| `apps/backend/app/main.py` | include `investigate` router |
| `apps/backend/app/static/index.html` | ASK/INVESTIGATE toggle + plan/live-status panels (additive) |
| `apps/backend/app/services/analyze.py` | none required; `interpret_query` reused as-is |
| `README.md`, `API_CONTRACT.md`, `PROJECT_STATUS.md`, `docs/sih/evidence/README.md` | document `/investigate` + the agent |

## NEW

```
packages/agents/src/satquery_agents/agent/
  __init__.py
  schemas.py      # TaskType ontology, ToolName, PlanStep, AgentPlan, AgentState, observations, result
  registry.py     # ToolSpec + TOOL_REGISTRY (10 typed tools + metadata)
  policy.py       # validate_plan() — 12 checks; PolicyError
  planner.py      # Planner protocol; RuleBasedPlanner; LlmPlanner; make_planner(); plan_with_fallback()
  prompts.py      # planner system prompt + few-shot + JSON schema
  memory.py       # AgentMemory (bounded structured state, refs only)
  verifier.py     # assess_step() -> StepVerdict (wraps evidence.verify + resolution + sanity)

apps/backend/app/services/agent_runner.py   # executor / state machine; TOOL_IMPL; run_investigation(); synthesize_answer()
apps/backend/app/api/investigate.py         # POST /investigate
scripts/research/planner_infer.py           # local Qwen2-VL-2B text-only planner bridge (.venvs/tinyrs)

evaluation/agent/
  frozen_missions.json        # 30 missions (5 VQA / 5 grounding / 5 temporal / 5 opt+SAR / 5 multi-step / 5 adversarial)
  run_agent_eval.py           # runs missions through agent + baseline; writes reports/<ts>.json + reports/latest.json
  reports/

apps/backend/tests/test_g14_agent.py        # policy, planner, executor, 18 failure cases, observe/replan
docs/research/EXP-006_AGENTIC_PLANNER.md
docs/G14_AGENTIC_REPORT.md
```

## Non-negotiables carried into G14

Deterministic router NOT replaced (planner ∥ policy/guard). LLM never invents
tools/capabilities/coordinates/evidence, never bypasses validation, never
substitutes a specialist silently, never fabricates a result for a failed
specialist. Frozen model stack unchanged. RemoteSAM licence caveat preserved.
4 GB VRAM stays **UNVERIFIED**. No confidence values. Semantic-temporal baseline
stays labelled **experimental**. Bounded autonomy (≤ 8 steps), not max autonomy.
