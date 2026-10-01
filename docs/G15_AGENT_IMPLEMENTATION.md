# G15 — Agent Validation + Flagship Mission Mode (implementation)

> Builds on G14. Turns the agent into the central product experience: 50 frozen
> missions, 13 measured quality metrics, structured replanning, explicit early
> termination, a judge-facing INVESTIGATE panel, and a deterministic fallback
> that is never invisible. No new models, no frozen-stack changes, no
> hard-coded flagship workflow.
> Date: **2026-09-02**. Audit: `docs/G15_AUDIT.md`.

## What "agentic" means here — A–J, each tested

| | Capability | Where it lives | Test |
|--|-----------|----------------|------|
| A | Goal understanding | `MissionFeatures` (planner) + `_mission_family` (executor) | `test_g14`/`g15` planner parametrize |
| B | Plan generation | `RuleBasedPlanner` / `LlmPlanner` → `AgentPlan` | plan-phase eval (validity 1.00) |
| C | Typed tool selection | closed `ToolName`; `registry.TOOL_REGISTRY` | `test_policy_01/03` |
| D | Dependency handling | `PlanStep.depends_on` + policy checks 6/10; executor topo order | `test_policy_06/10`, DEPENDENCY_VALIDITY 1.00 |
| E | Tool execution | `agent_runner.TOOL_IMPL` (wraps the frozen-stack slices) | exec-phase eval |
| F | Observation of outputs | `StepObservation.findings` + `assess_step` verdict | `_step_findings` |
| G | Conditional next-action | the OBSERVE/REPLAN block: 6 enumerated `ReplanReason`s | `test_missing_sar_*`, `test_early_termination_*` |
| H | Early stopping | `_mission_complete(family,…)` + `TASK_COMPLETE` replan + `early_stopped` | `test_early_termination_on_no_change` |
| I | Safe replanning after failure | `TOOL_FAILURE` / `INSUFFICIENT_EVIDENCE` replans prune dependents; no fabrication | `test_g14` 6/8, RECOVERY_RATE |
| J | Evidence-aware synthesis | `_synthesize` builds the report ONLY from observations; INCOHERENT steps' claims are withheld | `FINAL_ANSWER_FACTUAL_CONSISTENCY 1.00` |

A scripted `if "change": run A,B,C` is **not** the architecture — the plan is an
explicit typed object, the policy layer can reject it, and the executor's next
action is chosen from the *observed* result.

## New in G15

### 1. Structured replanning (`schemas.ReplanEvent`, `ReplanReason`)

Closed set: `NEW_EVIDENCE · TOOL_FAILURE · MISSING_INPUT · INSUFFICIENT_EVIDENCE ·
VERIFICATION_CONTRADICTION · TASK_COMPLETE`. Every replan records
`reason · triggering_step · previous_phase · detail · steps_skipped · ts` and is
surfaced in `result.replans[]`, the timeline (`REPLAN [REASON] from sN: …`), and
`provenance.replans`.

| Trigger | Reason | Action |
|---------|--------|--------|
| `changed_fraction < 1%` | `NEW_EVIDENCE` | skip region/grounding/SAR; `early_stopped=True` |
| a specialist returns `ok=false` | `TOOL_FAILURE` | prune steps that depended on it; **no fabricated result** |
| SAR requested, no distinct 2-band raster | `MISSING_INPUT` | **do not call CROMA/DOFA**; "not performed" in findings |
| grounding → no region / 0 changed regions | `INSUFFICIENT_EVIDENCE` | continue without a fabricated box; skip region grounding |
| a step ran but is `INCOHERENT` | `VERIFICATION_CONTRADICTION` | withhold that step's claim from the conclusion |
| mission-completion condition met | `TASK_COMPLETE` | skip the remaining specialist steps; `early_stopped=True` |

### 2. Explicit early termination (`_mission_complete`)

Per family: `single_step` completes after its specialist; `temporal` /
`optical_sar` after their specialist + VERIFY; `multi_step` once every planned
specialist step has run or been consciously skipped + VERIFY. When complete, any
remaining specialist steps are skipped with a `TASK_COMPLETE` replan. Measured by
`EARLY_STOP_EFFICIENCY` (only over missions where stopping early is *appropriate*).

### 3. Deterministic fallback — never invisible

Policy rejects a plan (or the planner is unavailable) → `_deterministic_fallback`
runs `/analyze`, sets `mode='ask-fallback'`, `resolution.qualifier ∈
{PLANNER_UNAVAILABLE, SPECIALIST_DEGRADED}`, adds an `AGENT FALLBACK: …` warning,
and names the blocking policy checks in the timeline. `run_investigation` now
pre-reads CRS + pair co-registration so the **policy layer** rejects a temporal
plan on a genuinely misregistered pair (not just the executor's validate step).

### 4. Structured observation + accounting

`StepObservation.findings` (compact dict, no arrays) + `contributed` flag →
`provenance.contributing_tool_calls` / `unnecessary_tool_calls` →
`UNNECESSARY_TOOL_CALL_RATE`.

### 5. GeoJSON

`result.geojson` = a `FeatureCollection` (EPSG:4326) of the spatial findings that
carry lon/lat boxes. Surfaced in the response and copyable from the UI.

### 6. Flagship INVESTIGATE panel (judge-facing)

`renderInvestigation` now leads with **Investigation result** (Status:
Verified / Partially verified / Insufficient evidence · models used · tool calls ·
replans · time · conclusion), then **Agent plan & execution** ("the agent
generated this plan"), a **Replans** table ("the agent adapted based on
observations"), Key findings, Spatial findings + GeoJSON copy, Verification +
resolution qualifier, Evidence, Warnings, and a collapsible detailed trace +
provenance. No fake "thinking" animation — real tool decisions and statuses.

## Evaluation

`evaluation/agent/frozen_missions.json` — **50 missions**, 5 categories ×10, each
with `expected_task_family / expected_tool_set / expected_order_constraints /
expected_termination_behavior / expected_failure_behavior` (what a correct agent
*should do*, never the answer). `run_agent_eval.py` computes 13 metrics, each with
its N; see `docs/G15_AGENT_EVALUATION.md` and
`evaluation/agent/reports/G15_AGENT_EVALUATION.{md,json}`.

## Claim discipline

"SatQuery **can decompose multi-step remote-sensing missions into validated
specialist actions and adapt its execution based on intermediate observations**"
— bounded agentic execution, typed tool planning, policy-constrained execution,
evidence-backed orchestration, **internal evaluation**. Not "state-of-the-art",
"fully autonomous", "hallucination-free", or "real-time".

## Files

New: `docs/G15_AUDIT.md`, `docs/G15_AGENT_IMPLEMENTATION.md`,
`docs/G15_AGENT_EVALUATION.md`, `apps/backend/tests/test_g15_agent.py`,
`evaluation/agent/reports/G15_AGENT_EVALUATION.{md,json}`,
`docs/sih/evidence/demos/g15_investigation_*.json`.
Changed: `schemas.py` (+`ReplanEvent`/`ReplanReason`/`findings`/`geojson`/
`replans`/`early_stopped`/`mission_family`), `planner.py` (keyword + SAR-modality
fixes), `agent_runner.py` (structured replans, MISSING_INPUT, VERIFICATION_
CONTRADICTION, early termination, pre-plan geo, geojson, PLANNER_UNAVAILABLE),
`run_agent_eval.py` (50 missions, 13 metrics), `index.html` (flagship panel),
`docs/research/EXP-006_AGENTIC_PLANNER.md`, `PROJECT_STATUS.md`, `README.md`,
`API_CONTRACT.md`, `docs/sih/evidence/README.md`.
