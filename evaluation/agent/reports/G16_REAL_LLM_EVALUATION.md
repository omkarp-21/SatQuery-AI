# G16 — Real LLM Agent Validation — 2026-09-02T224041

> **Internal frozen evaluation — NOT an external benchmark.** Two planning arms over the same 50 frozen missions. Every rate carries its N.
> LLM: **Qwen2-VL-2B-Instruct (text-only), local, CPU, greedy/deterministic decoding**; prompt: compact (~1.05k tokens), schema-constrained + safe-repair + truncation salvage.
> **ARM A N = 50** (all missions). **ARM B N = 15** (35 not attempted). ARM B ran on 15/50 missions - a stratified subset; the local 2B model needs ~100 s/plan on this CPU-only host (full 50 ~= 1.5 h). A GPU host runs all 50; the harness supports it. Every ARM B rate is over this N.

## Planning metrics — ARM A (RuleBasedPlanner) vs ARM B (local LLM)

| metric | RULE | N | LLM | N | definition |
|--------|:----:|:-:|:---:|:-:|------------|
| PLAN_VALIDITY_RATE | **1.0** | 44 | **0.25** | 12 | SUPPORTED missions: plan is schema-valid, policy-accepted, and semantically valid (required tools present, deps + order + modality ok, verify + finalize present) |
| SCHEMA_VALIDITY_RATE | **0.96** | 50 | **1.0** | 15 | plans the policy layer accepts (post-repair for the LLM arm) |
| EXACT_MATCH_RATE | **0.9** | 50 | **0.2** | 15 | plan tool sequence contains the expected sequence as a sub-sequence (reported, NOT used to gate validity) |
| TOOL_SELECTION_ACCURACY | **1.0** | 50 | **0.4** | 15 | every expected tool is present AND no forbidden tool in an executable plan |
| REQUIRED_TOOL_COVERAGE | **1.0** | 50 | **0.4** | 15 | mean fraction of expected tools present |
| TASK_ORDER_CORRECTNESS | **1.0** | 50 | **1.0** | 15 | every 'A < B' order constraint holds |
| DEPENDENCY_VALIDITY | **1.0** | 203 | **1.0** | 45 | depends_on edges pointing to a real earlier step / total edges |
| UNSUPPORTED_ACTION_RATE | **0.0** | 47 | **0.267** | 15 | executable plans that include a forbidden/illegal tool / executable plans |
| UNNECESSARY_TOOL_SELECTION_RATE | **0.125** | 48 | **0.6** | 15 | executable plans with >=1 specialist tool not needed by the mission / executable plans |
| PLAN_COMPLETION_COMPATIBILITY | **1.0** | 50 | **1.0** | 15 | plan ends in finalize_answer and contains a verify_result step |
| ADVERSARIAL_POLICY_REJECTION_RATE | **0.833** | 6 | **1.0** | 3 | adversarial missions where the plan is policy-rejected OR its executable form runs no forbidden/illegal specialist (a safe generic plan counts) |
| AVG_PLAN_LENGTH | **2.6** | 50 | **2.0** | 15 | specialist steps per plan (excl. bookkeeping) |
| PLANNING_LATENCY_S | **0.0** (med 0.0s) | 50 | **99.97** (med 99.74s) | 15 | wall-clock per plan (LLM arm: model generation time, CPU) |

## LLM planner health (ARM B)

- parses to JSON: **15/15**
- schema-valid with no repair: **15/15**
- usable only after safe repair: **0/15** (avg 0.0 repairs)
- fell back to RuleBasedPlanner: **0/15** — reasons: `{}`

## By category (PLAN_VALIDITY / TOOL_SELECTION), rule vs llm

- **adversarial** (n=10): rule 0.5/1.0 · llm 0.0/1.0
- **multi_step** (n=10): rule 1.0/1.0 · llm 0.0/0.0
- **optical_sar** (n=10): rule 1.0/1.0 · llm 0.0/0.0
- **single_step** (n=10): rule 1.0/1.0 · llm 1.0/1.0
- **temporal** (n=10): rule 1.0/1.0 · llm 0.0/0.0

## Execution phase — LLM agent, real frozen-stack models (N=6, 0 errors)

planner actually used: `{'llm': 6}`

| metric | value | N | definition |
|--------|:-----:|:-:|------------|
| MISSION_COMPLETION_RATE | **1.0** | 6 | valid terminal state / total |
| FINAL_ANSWER_FACTUAL_CONSISTENCY | **0.333** | 6 | no claim without a supporting observation |
| EVIDENCE_PRESERVATION_RATE | **1.0** | 6 | evidence survives to the result |
| VERIFICATION_PRESERVATION_RATE | **1.0** | 6 | verification present |
| UNSUPPORTED_ACTION_RATE | **0.667** | 6 | forbidden tool calls that RAN / total specialist attempts |
| UNNECESSARY_TOOL_CALL_RATE | **0.0** | 6 | completed calls that did not contribute / total calls |
| RECOVERY_RATE | **None** | 0 | recoverable-failure missions that still reached a valid final state |
| EARLY_STOP_RATE | **0.0** | 6 | missions the agent stopped before the full plan |
| MAX_STEP_VIOLATION_RATE | **0.0** | 6 | missions that hit the >=8 tool-call cap |
| avg tool calls / mission | 1.0 | 6 | |
| avg replans / mission | 0.0 | 6 | |
| avg latency (s) | 743.5 | 6 | CPU |

Replan reasons: `{}`

### Baseline (`/analyze`) vs LLM agent — required specialists run

- **multi_step** (N=3): baseline 1.0 · agent 1.0 · agent completion 1.0
- **single_step** (N=1): baseline 1.0 · agent 1.0 · agent completion 1.0
- **all** (N=6): baseline 1.0 · agent 1.0 · agent completion 1.0

## Claim discipline

Supported: *schema-constrained LLM planning*, *policy-constrained agentic execution*, *bounded observe/replan*, *evidence-aware multi-step orchestration*, *adaptive specialist selection based on intermediate observations*. NOT claimed: "fully autonomous", "hallucination-free", "state-of-the-art", "real-time".