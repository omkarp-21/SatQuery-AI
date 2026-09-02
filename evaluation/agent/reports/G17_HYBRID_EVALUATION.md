# G17 — Hybrid Agent Evaluation — 2026-09-03T024745

> **Internal frozen evaluation — NOT an external benchmark.** Three planner architectures over the same **100** frozen missions (20 / category). Every rate carries its N.
> The **G16 negative result for the pure LLM planner is preserved** below (ARM B, carried forward — not re-run).

| architecture | what the planner owns |
|---|---|
| **A — RuleBasedPlanner** | everything (keyword/feature → plan) |
| **B — pure local LLM** | intent **and** execution graph (G16 — rejected for production) |
| **C — hybrid** | LLM: typed **intent only** · deterministic `PlanSynthesizer`: the execution graph |

ARM A N = 100. ARM C N = 100 (0 not attempted). LLM: Qwen2-VL-2B-Instruct (text-only), local, CPU, greedy decoding.

## Planning metrics

| metric | A rule | N | B pure-LLM | N | C hybrid | N | definition |
|--------|:------:|:-:|:---------:|:-:|:--------:|:-:|------------|
| PLAN_VALIDITY_RATE | **0.886** | 88 | 0.25 | 12 | **0.591** | 88 | SUPPORTED missions: schema-valid + policy-accepted + semantically valid (required tools, deps, order, modality, verify, finalize) / supported |
| TOOL_SELECTION_ACCURACY | **0.9** | 100 | 0.4 | 15 | **0.66** | 100 | every expected tool present AND no forbidden tool in an executable plan / all |
| REQUIRED_TOOL_COVERAGE | **0.905** | 100 | — |  | **0.66** | 100 | mean fraction of expected tools present |
| TASK_ORDER_CORRECTNESS | **1.0** | 100 | — |  | **1.0** | 100 | every 'A < B' order constraint holds / all |
| DEPENDENCY_VALIDITY | **1.0** | 403 | 1.0 | 45 | **1.0** | 486 | depends_on edges to a real earlier step / total edges |
| UNSUPPORTED_ACTION_RATE | **0.053** | 94 | 0.267 | 15 | **0.125** | 96 | executable plans with a forbidden/illegal tool / executable plans |
| UNNECESSARY_TOOL_SELECTION_RATE | **0.2** | 95 | — |  | **0.526** | 97 | executable plans with >=1 specialist not needed by the mission / executable plans |
| ADVERSARIAL_CORRECTLY_HANDLED_RATE | **0.917** | 12 | — |  | **0.917** | 12 | adversarial missions: plan policy-rejected OR executable form runs no forbidden specialist / adversarial |
| AVG_PLAN_LENGTH | **2.58** | 100 | — |  | **3.07** | 100 | specialist steps per plan (excl. bookkeeping) |
| PLANNER_LATENCY_S | **0.0** | 100 | 99.97 | 15 | **39.61** | 100 | wall-clock per plan; ARM C = LLM intent generation time (CPU) |

## ARM C — LLM intent extraction quality

- **INTENT_SCHEMA_VALIDITY_RATE**: 0.82 (N=100) — LLM intent JSON parses + validates (post safe-repair) / all
- **INTENT_TASK_ACCURACY**: 0.317 (N=82) — LLM intent task_family == expected_intent.task_family / scored
- fell back to the deterministic intent: **29** / 100

### By category — PLAN_VALIDITY / TOOL_SELECTION (rule vs hybrid) · INTENT_TASK_ACC (hybrid)

- **adversarial** (n=20): rule 0.75/0.9 · hybrid 0.5/0.8 · intent-task 0.0
- **multi_step** (n=20): rule 1.0/1.0 · hybrid 1.0/1.0 · intent-task 1.0
- **optical_sar** (n=20): rule 1.0/1.0 · hybrid 0.35/0.35 · intent-task 0.071
- **single_step** (n=20): rule 0.75/0.75 · hybrid 0.2/0.2 · intent-task 0.053
- **temporal** (n=20): rule 0.85/0.85 · hybrid 0.85/0.95 · intent-task 0.556

## ARM B — pure local LLM planner (G16, preserved)

- PLAN_VALIDITY 0.25 · TOOL_SELECTION 0.4 · SCHEMA_VALIDITY 1.0 · latency ~99.97 s (N=15)
- failure mode: example-echo: the same VALIDATE->run_vqa->VERIFY->FINALIZE plan for every mission
- G16 exec (N=6): FINAL_ANSWER_FACTUAL_CONSISTENCY 0.33, forbidden-tool-that-RAN 0.67 - structurally-valid echo plans passed policy and ran; the G16 intent cross-check was added to contain it.
- source: G16 (carried forward — NOT re-run in G17)

## Execution phase — ARM C hybrid agent, real frozen-stack models (N=8, 0 errors)

planner actually used: `{'hybrid_llm': 6, 'hybrid_rule_fallback': 2}` · confidence categories: `{'HIGH': 7, 'MEDIUM': 1}`

| metric | value | N | definition |
|--------|:-----:|:-:|------------|
| MISSION_COMPLETION_RATE | **1.0** | 8 | valid terminal state / total |
| FINAL_ANSWER_FACTUAL_CONSISTENCY | **1.0** | 8 | no claim without a supporting observation / total |
| EVIDENCE_PRESERVATION_RATE | **1.0** | 8 | evidence survives to the result / finalized missions |
| VERIFICATION_PRESERVATION_RATE | **1.0** | 8 | verification present / total |
| UNSUPPORTED_ACTION_RATE | **0.0** | 14 | forbidden tool calls that RAN / total specialist attempts |
| UNNECESSARY_TOOL_CALL_RATE | **0.0** | 21 | completed calls that did not contribute / total calls |
| EARLY_STOP_RATE | **0.0** | 8 | missions stopped before the full plan / total |
| MAX_STEP_VIOLATION_RATE | **0.0** | 8 | missions that hit the >=8 tool cap / total |
| REPLAN_RATE | **0.0** | 8 | missions with >=1 replan / total |
| avg tool calls / mission | 2.62 | 8 | |
| avg total mission latency (s) | 97.6 | 8 | CPU, cold loads |

Replan reasons: `{}`

### Baseline (`/analyze`) vs hybrid agent — required specialists run

- **multi_step** (N=4): baseline 1.0 · hybrid 2.25 · hybrid completion 1.0 · factual 1.0
- **all** (N=8): baseline 1.0 · hybrid 1.75 · hybrid completion 1.0 · factual 1.0

## Claim discipline

Supported: *LLM-assisted intent understanding*, *deterministic plan synthesis*, *policy-constrained execution*, *bounded observe/replan*, *evidence-derived confidence category*. NOT claimed: the LLM autonomously controls the system; "fully autonomous"; "calibrated confidence"; "state-of-the-art"; "real-time".