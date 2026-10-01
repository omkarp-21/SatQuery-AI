# G15 — Audit of G14 (Part 1)

State of the agent stack coming into G15, tagged `EXISTS / WORKING / WEAK /
MISSING / TO IMPROVE`. G15 builds on G14 — it does not duplicate working code.

## EXISTS + WORKING (keep as-is)

| Piece | Where | Note |
|---|---|---|
| Typed `AgentPlan` / `PlanStep` (Pydantic; malformed → rejected) | `packages/agents/src/satquery_agents/agent/schemas.py` | schema-valid plans only |
| Closed 12-task ontology + closed 12-tool registry with full metadata | `schemas.py`, `registry.py` | planner may select only these |
| 12-check deterministic policy layer (+ "ends at FINALIZE") | `policy.py` | reasons prefixed with the check name |
| Planner: `RuleBasedPlanner` (default) + `LlmPlanner` (local Qwen2-VL-2B text-only) + `plan_with_fallback()` (never raises) | `planner.py`, `prompts.py`, `scripts/research/planner_infer.py` | provider abstraction present |
| Bounded executor state machine (≤ 8 specialist calls, no recursion) | `apps/backend/app/services/agent_runner.py` | 9 phases |
| Observe/verify per step (`assess_step` → COHERENT/INCOHERENT/INSUFFICIENT/NA) | `verifier.py`, executor | |
| Conditional pruning: tiny change → skip grounding/regions/SAR; grounding fail → no fabricated box; 0 regions → skip grounding; misregistered → `/analyze` fallback; embedding → "representation-level only" | executor | the agenticity |
| `POST /investigate` + UI ASK/INVESTIGATE toggle + agent plan/live-status panel | `apps/backend/app/api/investigate.py`, `app/static/index.html` | |
| 30 frozen missions + `run_agent_eval.py` (plan phase + a light exec + baseline) | `evaluation/agent/` | |
| ~30 tests incl. 18 failure cases | `apps/backend/tests/test_g14_agent.py` | |

**G14 measured:** plan validity 0.967, tool-selection 1.00, task-order 1.00 (30
missions); exec (12, real models) success/evidence/verification preservation 1.00,
forbidden-tool rate 0.00; agent runs 2.5 required specialists on multi-step
missions vs the baseline's 1.0.

## WEAK / TO IMPROVE

| # | Weakness | G15 fix |
|---|----------|---------|
| 1 | Replan is a free-text `replan_note` on a step — not a structured, enumerated event with reason / previous state / new plan / triggering step | `ReplanReason` literal (`NEW_EVIDENCE / TOOL_FAILURE / MISSING_INPUT / INSUFFICIENT_EVIDENCE / VERIFICATION_CONTRADICTION / TASK_COMPLETE`) + `ReplanEvent` model + `result.replans[]` |
| 2 | No explicit **mission-completion** check → the agent runs the whole plan (downstream is only skipped on tiny-change). No `EARLY_STOP_EFFICIENCY` metric | `_mission_complete(family, …)` per family + `TASK_COMPLETE` replan + `result.early_stopped` / `completion_reason` |
| 3 | `MISSING_INPUT` (SAR requested, no distinct SAR raster) → CROMA was still called (and failed on band count) | pre-check the SAR ref before the step; skip + `MISSING_INPUT` replan; report "not performed" |
| 4 | `VERIFICATION_CONTRADICTION` (a step ran but is INCOHERENT) → its claim was still asserted | verdict `INCOHERENT` → `VERIFICATION_CONTRADICTION` replan + the claim is withheld in synthesis |
| 5 | Deterministic fallback set `mode='ask-fallback'` but no `resolution.qualifier` | `PLANNER_UNAVAILABLE` (planner/plan-rejected) / `SPECIALIST_DEGRADED`; a visible `AGENT FALLBACK` warning; blocking policy-check names in the trace |
| 6 | 30 missions, thin schema | **50 missions**, richer schema (`expected_task_family / order_constraints / termination_behavior / failure_behavior`) |
| 7 | ~7 eval metrics | **13**: PLAN_VALIDITY, ADVERSARIAL_CORRECTLY_HANDLED, TOOL_SELECTION, TASK_ORDER, DEPENDENCY_VALIDITY, MISSION_COMPLETION, EVIDENCE/VERIFICATION_PRESERVATION, FACTUAL_CONSISTENCY, UNSUPPORTED_ACTION_RATE, RECOVERY_RATE, EARLY_STOP_EFFICIENCY, UNNECESSARY_TOOL_CALL_RATE — each with its **N** |
| 8 | No 10-paraphrase flagship test | `test_g15_agent.py::test_flagship_10_paraphrases` — the plan must emerge from planning, not keyword identity |
| 9 | UI investigation panel functional but not judge-facing | Part-15 flagship panel: STATUS / KEY FINDINGS / CHANGE SUMMARY / OPTICAL+SAR / SPATIAL / EVIDENCE / VERIFICATION / MODELS / WARNINGS + collapsible trace; the panel makes it obvious *the agent decided* |
| 10 | No GeoJSON | `result.geojson` = a `FeatureCollection` (EPSG:4326) of the spatial findings; surfaced in the response |
| 11 | Structured observation had `numeric` only | added `StepObservation.findings` (compact dict) + `contributed` flag (feeds UNNECESSARY_TOOL_CALL_RATE) |
| 12 | Policy pre-plan context passed `pair_co_registered=None` (executor caught it later) | `run_investigation` now pre-reads CRS + co-registration so the policy layer can reject a temporal plan on a genuinely misregistered pair |

## MISSING (build in G15)

- `ReplanEvent` model + `replans[]` + `ReplanReason` (done)
- `MISSING_INPUT` / `VERIFICATION_CONTRADICTION` handling (done)
- early-termination + `EARLY_STOP_EFFICIENCY` (done)
- 50-mission set + G15 eval harness (13 metrics) (done)
- `test_g15_agent.py` — per-policy-check + Part-7 conditional cases + 10 paraphrases
- real flagship capture `docs/sih/evidence/demos/g15_investigation_*.json`
- `evaluation/agent/reports/G15_AGENT_EVALUATION.{md,json}`
- docs: `docs/G15_AGENT_IMPLEMENTATION.md`, `docs/G15_AGENT_EVALUATION.md`, EXP-006, PROJECT_STATUS, README, API_CONTRACT, evidence

## Not doing (out of scope per the G15 brief)

New models · frozen-stack changes · core-architecture redesign · large UI redesign
/ animations · PPT · semantic-temporal VLM research · fake traces · hard-coded
flagship workflow · invented benchmark numbers.
