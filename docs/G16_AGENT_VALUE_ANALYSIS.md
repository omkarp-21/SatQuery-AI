# G16 Part 8 / 18 — Real Agent Value + Scorecard

**Question:** does agentic planning add *measured* value over the deterministic
`/analyze` baseline? The honest test is **multi-step missions**; on single-step
tasks the baseline should stay excellent and the agent should not add cost.

The baseline is **not** handicapped: it runs its normal routing to exactly one
specialist. The agent plans and runs the several a mission needs.

## Required-specialist coverage

For each mission we know the specialists a correct answer needs
(`expected_tool_set`). We count how many each approach actually *ran*.

| segment | N | baseline specialists run (avg) | LLM-agent specialists run (avg) | agent mission completion |
|---------|:-:|:------------------------------:|:-------------------------------:|:-----------------------:|
| single_step | `<FILL>` | `<FILL>` | `<FILL>` | `<FILL>` |
| multi_step | `<FILL>` | `<FILL>` | `<FILL>` | `<FILL>` |
| all exec | `<FILL>` | `<FILL>` | `<FILL>` | `<FILL>` |

Example mission (`mi-…`): *"Detect significant changes, locate affected
structures, and cross-check optical and SAR evidence."*
Baseline: `<FILL — routes to which single specialist>`.
LLM agent: `<FILL — plan tasks + which specialists ran>`.

## Scorecard

Each metric with **baseline**, **LLM agent**, **delta**, **N**, and an
interpretation. Unrelated metrics are **not** combined into one score.

### A. Planner reliability — plan phase (ARM A N=50, ARM B N=15)

| metric | RuleBased | LLM | N (rule / llm) | interpretation |
|--------|:---------:|:---:|:--------------:|----------------|
| SCHEMA_VALIDITY_RATE | 0.96 | **1.00** | 50 / 15 | LLM output is clean JSON; the 2 rule "misses" are correct policy rejections of misregistered pairs |
| PLAN_VALIDITY_RATE (semantic) | **1.00** | **0.25** | 44 / 12 supported | LLM valid only on the 3 single-image VQA missions |
| TOOL_SELECTION_ACCURACY | **1.00** | **0.40** | 50 / 15 | LLM never picks temporal / optical-SAR / multi-step specialists |
| REQUIRED_TOOL_COVERAGE (mean) | **1.00** | **0.40** | 50 / 15 | |
| TASK_ORDER_CORRECTNESS | 1.00 | 1.00 | 50 / 15 | the echoed plan has a valid order |
| DEPENDENCY_VALIDITY | 1.00 | 1.00 | 203 / 45 edges | the echoed plan has valid deps |
| UNNECESSARY_TOOL_SELECTION_RATE | 0.125 | 0.60 | 48 / 15 | rule over-plans on ~6 region-only missions; LLM's lone `run_vqa` is "unnecessary" on 9 non-VQA missions |
| PLANNING_LATENCY (median) | **<0.01 s** | **~100 s** | 50 / 15 | CPU, 2 B, greedy |

**A verdict:** the RuleBasedPlanner is effectively perfect on this frozen set
(one measured flaw: mild over-planning). The local 2 B LLM cannot plan — it
echoes the prompt example. The gap is not close.

### B. Execution reliability — exec phase, N=6 (LLM planner in the loop, **pre** the G16 intent cross-check)

| metric | baseline | LLM agent | N | interpretation |
|--------|:--------:|:---------:|:-:|----------------|
| MISSION_COMPLETION_RATE | 1.00 | 1.00 | 6 | both "finish" — completion alone is not quality |
| FINAL_ANSWER_FACTUAL_CONSISTENCY | ~1.0 (routes correctly) | **0.33** | 6 | the LLM-agent answered investigation missions with a VQA sentence |
| VERIFICATION_PRESERVATION_RATE | 1.00 | 1.00 | 6 | verification present — but of the *wrong* result |
| EVIDENCE_PRESERVATION_RATE | n/a | 1.00 | 6 | |
| UNSUPPORTED_ACTION_RATE (forbidden tool RAN) | 0.00 | **0.67** | 6 | 4/6 ran `run_vqa` where the mission forbids it |
| avg latency | seconds | ~744 s | 6 | LLM plan + cold specialist loads |

**Post the intent cross-check** the 5 non-VQA missions route to
`RuleBasedPlanner` (`PLAN_INTENT_MISMATCH` → visible fallback), so the LLM-agent
collapses onto the rule-agent for those. Validated by `test_g16_agent.py`.

### C. Agentic value (multi-step)

| metric | baseline | rule-agent (G15/G16 ARM A) | LLM-agent (N=6 exec) |
|--------|:--------:|:--------------------------:|:--------------------:|
| required specialists run (avg) | 1.0 | **2.33** | **1.0** |
| plan validity (semantic) | — | 1.00 (N=44) | 0.25 (N=12) |

The agent's multi-step value is **real and comes from the RuleBasedPlanner**
(2.33× the baseline's specialists). The local LLM planner contributes none of it.

### D. Safety (all arms)

| metric | RuleBased | LLM | N (rule / llm) | interpretation |
|--------|:---------:|:---:|:--------------:|----------------|
| UNSUPPORTED_ACTION_RATE (plan, executable) | **0.00** | 0.27 | 47 / 15 | 4/15 LLM plans put `run_vqa` where forbidden — all neutralised by the policy layer |
| UNSUPPORTED_ACTION_RATE (exec — forbidden tools that actually RAN) | `<FILL — target 0>` | `<FILL — target 0>` | `<FILL>` | the real guarantee |
| ADVERSARIAL_POLICY_REJECTION_RATE | 0.83 | 1.00 | 6 / 3 | rule 5/6 (the 6th, ad-05, is a corrupt raster — runtime-only, executor catches it) |

**D verdict:** the schema layer + 12-check policy layer + visible fallback stop
every *malformed / structurally-illegal* plan. They did **not** stop a
*structurally-valid but mission-wrong* plan — the exec phase measured the weak
LLM's `run_vqa`-only plan passing policy and running on 4/6 missions that forbid
it. G16 adds the **plan-intent cross-check** to close that specific gap (see
§B and `docs/G16_ADVERSARIAL_TESTS.md`).

### E. Efficiency (exec phase, N=6, LLM planner)

| metric | value | N | interpretation |
|--------|:-----:|:-:|----------------|
| UNNECESSARY_TOOL_CALL_RATE | 0.00 | 6 | only 1 call/mission — the echo, so nothing "extra"; but the 1 call is often *wrong* |
| MAX_STEP_VIOLATION_RATE | 0.00 | 6 | the bounded loop held |
| EARLY_STOP_RATE | 0.00 | 6 | the echo plan has no change-detection step to trigger `NEW_EVIDENCE` |
| avg tool calls / mission | 1.0 | 6 | vs rule-agent 2.33 on multi-step |
| avg latency (s) | ~744 | 6 | LLM plan (~100 s) + cold specialist loads |

## Verdict

**The agent's value over the deterministic baseline is real on multi-step
missions — 2.33× the required specialists — and it comes entirely from the
`RuleBasedPlanner` + the bounded observe/replan executor, not from the local 2 B
LLM planner.** The LLM planner, measured directly, echoes its prompt example
(semantic plan validity 0.25, tool-selection 0.40, N=15) and — because those
plans are structurally valid — the exec phase caught it running the wrong
specialist end-to-end (factual consistency 0.33, forbidden-tool-that-RAN 0.67,
N=6). The single weakest measured component is the **planner model**. G16's one
architectural addition, the **plan-intent cross-check**, contains the damage
(routes mission-wrong LLM plans to the visible deterministic fallback); it does
not make the LLM planner useful. Keep `RuleBasedPlanner` as the default; the LLM
stays opt-in. A useful LLM planner needs a GPU host + a ≥7 B / planning-tuned
model, or an LLM-proposes / rules-fill hybrid.
