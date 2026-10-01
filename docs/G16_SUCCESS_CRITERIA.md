# G16 — Success Criteria (Part 21) + Final Decision (Part 22)

Status legend: ✅ done · 🔄 measured on a bounded N (CPU-only 2 B model) · ⬜ pending

| # | criterion | status | evidence |
|--:|-----------|:------:|----------|
| 1 | actual local LLM planner runs | ✅ | path fix + `planner_infer.py --serve`; `evaluation/agent/reports/G16_llm_raw_cache.json` |
| 2 | RuleBasedPlanner remains fallback | ✅ | `plan_with_fallback_ex` hierarchy; `test_g16_agent.py::test_fallback_is_visible_*` |
| 3 | same 50 frozen missions used | ✅ | `evaluation/agent/frozen_missions.json` unchanged; ARM A on all 50 |
| 4 | both planner arms evaluated | ✅ | ARM A **n=50**, ARM B **n=15** (stratified 3/category; CPU-only 2 B ≈ 100 s/plan) |
| 5 | schema validity measured | ✅ | SCHEMA_VALIDITY_RATE **rule 0.96 / llm 1.00**; llm_health 15/15 parse+schema ok, 0 repair, 0 fallback |
| 6 | tool-selection quality measured | ✅ | TOOL_SELECTION_ACCURACY **rule 1.00 / llm 0.40**; REQUIRED_TOOL_COVERAGE **1.00 / 0.40** |
| 7 | dependency validity measured | ✅ | DEPENDENCY_VALIDITY **1.00 / 1.00** (203 / 45 edges) |
| 8 | unsupported actions measured | ✅ | plan UNSUPPORTED_ACTION_RATE **rule 0.00 (47) / llm 0.27 (15)**; ADVERSARIAL_POLICY_REJECTION **0.83 / 1.00**; **exec (pre intent cross-check): 0.67 (6)** — the key finding; **fix added** (`_plan_intent_mismatch`) |
| 9 | execution comparison completed | 🔄 | `G16_REAL_LLM_EVALUATION.json` `exec_metrics` |
| 10 | ≥ 20 real missions executed | ⚠️ **6** | exec is ~12 min/mission on this CPU-only host (LLM plan + cold specialist loads); N=6 (ss/tm/mi×3/ad). The plan phase — the core comparison — ran on all 50 (A) / 15 (B). |
| 11 | baseline vs LLM agent comparison | ✅ | `baseline_vs_agent`: baseline 1.0 · LLM-agent 1.0 specialists (N=6); rule-agent 2.33 (G15/G16 ARM A) |
| 12 | adversarial tests completed | ✅ | `docs/G16_ADVERSARIAL_TESTS.md` — plan phase + exec finding + `test_g16_agent.py` |
| 13 | replan behaviour tested | ✅ (G15) + N/A here | the echo plan never triggers a replan; G15 measured all 6 `ReplanReason`s. `repair.salvage_truncated` covers the malformed-JSON regime |
| 14 | early stopping tested | ✅ (G15) | EARLY_STOP_RATE 0.0 / MAX_STEP_VIOLATION_RATE 0.0 on N=6 (echo plan has no change step); G15 measured tm-10 `NEW_EVIDENCE` early stop |
| 15 | flagship uses actual LLM planner | ✅ | `scripts/demo/run_g16_flagship.py` — `LlmPlanner()` → echo → `PLAN_INTENT_MISMATCH` → rule re-plan; CASE A/B → `docs/sih/evidence/demos/g16_llm_flagship_case{A,B}.json` (real models, SUPPORTED) |
| 16 | flagship not hard-coded | ✅ | plan comes from `LlmPlanner`, then its visible re-plan; two environments, same mission text |
| 17 | low-change case → shorter plan/execution | ✅ | **CASE A: 4 tool calls, not early-stopped. CASE B (no change): 2 tool calls, `NEW_EVIDENCE` replan, `early_stopped=True`.** Execution path depends on observations (via the rule re-plan + executor; the LLM echoed the same plan for both) |
| 18 | evidence preserved | ✅ | EVIDENCE_PRESERVATION_RATE 1.00 (N=6 exec); 1.00 (N=13 G15) |
| 19 | verification preserved | ✅ | VERIFICATION_PRESERVATION_RATE 1.00 (N=6) — though of the *wrong* result pre-cross-check |
| 20 | deterministic fallback works | ✅ | `test_g16_agent.py`; `PLANNER_UNAVAILABLE` / `PLAN_REJECTED` / `PLAN_INTENT_MISMATCH` → `AGENT FALLBACK` warning |
| 21 | all existing tests remain green | ✅ | **226 fast pass, 0 fail** (`packages` + `apps/backend/tests`, `-m "not slow and not gpu and not integration"`) |
| 22 | new G16 tests pass | ✅ | `apps/backend/tests/test_g16_agent.py` (**23**) |
| 23 | no fake metrics | ✅ | every rate carries N; ARM B N stated everywhere; no fabricated numbers |
| 24 | no new giant model | ✅ | Qwen2-VL-2B already vendored (G14); frozen stack (ADR-021) unchanged |

## Final decision (Part 22)

Full reasoning: `docs/G16_REAL_LLM_EVALUATION.md` §"Final decision" +
`docs/G16_AGENT_VALUE_ANALYSIS.md`. Summary:

1. **Is the local LLM planner reliable enough for production?** **No.**
   Qwen2-VL-2B (text-only, CPU) takes ~100 s/plan and echoes the prompt example —
   semantic PLAN_VALIDITY 0.25, TOOL_SELECTION 0.40 (N=15), 0/9 on non-VQA
   missions. It never once selected the temporal / optical-SAR / multi-step
   specialists.
2. **Does the agent materially outperform the deterministic baseline on
   multi-step missions?** With the **RuleBasedPlanner** — yes (ARM A: 2.33 vs 1.0
   specialists, plan validity 1.00). With the **local LLM planner** — no, and
   *pre-fix it was worse*: the exec phase (N=6) measured it answering
   investigation missions with a single VQA step (factual consistency 0.33,
   forbidden-tool-that-RAN 0.67). The G16 intent cross-check routes those to the
   deterministic planner. The agent's value is real; it comes from the *rule*
   planner + the bounded observe/replan executor, not the 2 B LLM.
3. **Where does the agent fail?** LLM planner: example-echo; malformed recursive
   JSON without an example; ~100 s latency; **structurally-valid wrong plans that
   the policy layer alone did not catch** (exec finding → intent cross-check
   added). RuleBasedPlanner: mild over-planning on ~6/50 region-only missions
   (UNNECESSARY_TOOL_SELECTION_RATE 0.125).
4. **Should the local LLM remain / become the default planner?** **No** —
   `RuleBasedPlanner` stays default; LLM is opt-in behind the repair + policy +
   fallback guard.
5. **Should RuleBasedPlanner remain the fallback?** **Yes** — it is effectively
   the primary.
6. **Is additional agent-architecture work necessary?** **One targeted addition,
   made in G16:** the **plan-intent cross-check** (`_plan_intent_mismatch`) — the
   12-check policy layer guards *structural* legality but not *mission fit*, and
   the exec phase proved that gap is real with a weak planner. No other
   architecture change. The weakest *measured* component remains the *planner
   model*: needs a GPU host + ≥7 B / planning-tuned model, or an LLM-proposes /
   rules-fill hybrid. Secondary: trim the rule planner's region-only
   over-planning.

**Milestone reached:** G16 provides *measured evidence* that (a) the local 2 B
LLM planner **cannot plan** at this size on CPU (semantic plan validity 0.25,
tool-selection 0.40, N=15 — it echoes the prompt example); (b) a
structurally-valid wrong plan **will execute** through the G15 stack unless
caught — so G16 adds the intent cross-check; (c) with that check, a weak LLM
planner is **safely contained** (mission-wrong plans route to the visible
deterministic fallback) and the *deterministic* planner is the right default. The
agent's multi-step value (2.33× the baseline's specialists) is real and comes
from the rule planner + bounded executor. This validates the G14 design choice
(LLM = planner, deterministic system = policy/execution guard) with real numbers
— and hardens it.
