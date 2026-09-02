# G15 Agent Evaluation — 2026-09-02T191706

> **Internal frozen evaluation — NOT an external benchmark.** Metrics measure the PLANNER + POLICY + EXECUTOR, not model accuracy. Every rate carries its N.

Missions: **50** — single_step 10, temporal 10, optical_sar 10, multi_step 10, adversarial 10. Planner: `rule_based` (default; `LlmPlanner` opt-in, always falls back).

## Plan phase (all missions, no models)

| metric | value | N | definition |
|--------|:-----:|:-:|------------|
| PLAN_VALIDITY_RATE | **1.0** | 44 | SUPPORTED missions whose plan the policy layer accepts / total supported |
| FAILED_PLAN_RATE | **0.0** | 44 | supported missions the policy layer rejected |
| ADVERSARIAL_CORRECTLY_HANDLED_RATE | **1.0** | 6 | adversarial missions the policy rejected OR flagged as runtime-detected (blocked by the executor's validate step) |
| TOOL_SELECTION_ACCURACY | **1.0** | 49 | missions where expected tools are planned AND no forbidden tool is in an executable plan (excludes runtime-detected bad input) |
| TASK_ORDER_CORRECTNESS | **1.0** | 50 | missions where every 'A < B' order constraint holds in the plan |
| DEPENDENCY_VALIDITY | **1.0** | 203 | depends_on edges that point to a real, earlier step / total edges |
| avg specialist steps / plan | 2.6 | 50 | |

By category (PLAN_VALIDITY / TOOL_SELECTION / TASK_ORDER):

- **single_step** (n=10): 1.0 / 1.0 / 1.0
- **temporal** (n=10): 1.0 / 1.0 / 1.0
- **optical_sar** (n=10): 1.0 / 1.0 / 1.0
- **multi_step** (n=10): 1.0 / 1.0 / 1.0
- **adversarial** (n=10): 0.8 / 1.0 / 1.0

## Exec phase (N=14, real frozen-stack models, CPU)

| metric | value | N | definition |
|--------|:-----:|:-:|------------|
| MISSION_COMPLETION_RATE | **1.0** | 14 | missions reaching a valid terminal state (FINALIZING, or an honest refusal for an unsupported mission) / total |
| EVIDENCE_PRESERVATION_RATE | **1.0** | 13 | executed missions where specialist evidence survives to the final result / executed missions |
| VERIFICATION_PRESERVATION_RATE | **1.0** | 14 |  |
| FINAL_ANSWER_FACTUAL_CONSISTENCY | **1.0** | 14 |  |
| UNSUPPORTED_ACTION_RATE | **0.0** | 17 | forbidden/illegal tool calls that RAN / total specialist tool attempts |
| RECOVERY_RATE | **None** | 0 | recoverable-failure missions that still reached a valid final state / total such missions |
| EARLY_STOP_EFFICIENCY | **1.0** | 1 | missions where stopping early is APPROPRIATE (negligible change / unbounded ask) and the agent actually stopped early / total such missions |
| UNNECESSARY_TOOL_CALL_RATE | **0.0** | 20 | completed specialist calls that did not contribute to mission completion / total tool calls |
| avg tool calls / mission | 1.43 | 14 | |
| avg replans / mission | 0.07 | 14 | |
| avg end-to-end latency (s) | 62.0 | 14 | CPU, cold model loads |

Replan reasons observed: `{'NEW_EVIDENCE': 1}`

## Baseline vs agent — multi-step missions (N=3)

| | deterministic `/analyze` | agent |
|---|:--:|:--:|
| required specialists run (avg) | **1.0** | **2.33** |
| evidence present | — | 1.0 |
| unnecessary-tool-call rate | — | 0.0 |

> on multi-step missions the agent plans and runs the multiple required specialists; the deterministic baseline routes to one. Value is measured, not assumed.

## Claim discipline

SatQuery **can decompose multi-step remote-sensing missions into validated specialist actions and adapt its execution based on intermediate observations** (bounded agentic execution, typed tool planning, policy-constrained execution, evidence-backed orchestration). This is an *internal evaluation*. No claim of "state-of-the-art", "fully autonomous", "hallucination-free", or "real-time".