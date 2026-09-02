# G16 — Real LLM Agent Validation

> **Internal frozen evaluation — NOT an external benchmark.** G15 proved the
> agent *runtime*. G16 asks whether the **actual local LLM planner** can convert
> natural-language remote-sensing missions into valid, policy-compliant,
> execution-ready plans, and whether agentic planning adds measurable value over
> the deterministic baseline on multi-step missions.

## What changed since G15

G15's planning numbers were produced **100 % by `RuleBasedPlanner`** — the
`LlmPlanner` had never run (wrong checkpoint path, 60 s timeout vs a >600 s cold
call, ~2 800-token prompt on a CPU-only 2 B model). See `docs/G16_PLANNER_AUDIT.md`.

G16 makes the LLM arm actually measurable:

| | |
|---|---|
| checkpoint | path resolver finds `models/cache/qwen2vl2b/Qwen2-VL-2B-Instruct/` |
| prompt | **compact** (~1.4 k tokens): one-line tool list, JSON skeleton (not a copyable few-shot — a 2 B model copies a full example verbatim), "keep strings short / emit only JSON" |
| serving | `planner_infer.py --serve` — persistent JSON-lines model server, load the 4 GB model **once** (`SATQUERY_PLANNER_PERSISTENT=1`) |
| decoding | greedy, deterministic, `set_num_threads(cpu_count)`, `max_new_tokens=620` |
| repair | `agent/repair.py` — parse → **safe** structural repair (renumber ids, coerce `depends_on`, map near-miss tool names, prepend VALIDATE / append VERIFY+FINALIZE, drop unknown keys, **salvage** complete step objects from truncated JSON) → validate; else deterministic fallback. Over-long plans and specialist-less skeletons are **not** accepted — they fall back |
| provenance | `PlannerAttempt` (raw output, parse/schema/repair status, repairs, `final_source`, `fallback_reason`) in `provenance.planner_attempt`; **raw model text is never shown to users** |
| fallback tag | `planner_used` ∈ `{rule_based, llm, llm_repaired, rule_based_fallback}` |

## Method

- **Same 50 frozen missions** (`evaluation/agent/frozen_missions.json`, 5×10).
- **ARM A** `RuleBasedPlanner` (all 50). **ARM B** local LLM
  (`Qwen2-VL-2B-Instruct`, text-only, CPU) on a **stratified N = 20 subset**
  (4 / category) — full 50 on this CPU-only host is ~4 h; N is stated on every
  ARM B metric. (A GPU host would run all 50; the harness already supports it.)
- **Semantic** plan scoring (`evaluation/agent/plan_scorer.py`, Part 6): a plan
  is valid if it covers the required tools, uses no forbidden tool, has valid
  dependencies + order + modality, and has VERIFY + FINALIZE — **not** if it
  matches one gold sequence. `EXACT_MATCH_RATE` is reported but does not gate.
- **Execution** phase (Part 7): `<FILL n>` real-model missions, BASELINE
  (`/analyze`) vs LLM-AGENT (`LlmPlanner` + policy guard + observe/replan).
- Reproduce: `evaluation/agent/run_g16_eval.py` → `G16_REAL_LLM_EVALUATION.{md,json}`.

## Planning results — ARM A vs ARM B

Full table + by-category in `evaluation/agent/reports/G16_REAL_LLM_EVALUATION.md`.
**ARM A N = 50** (RuleBasedPlanner). **ARM B N = 15** (local LLM, stratified 3/category;
35 not attempted — ~100 s/plan on this CPU-only host, full 50 ≈ 1.5 h; a GPU host
runs all 50 and the harness supports it).

| metric | ARM A (rule) | N | ARM B (LLM) | N |
|--------|:-----------:|:-:|:-----------:|:-:|
| SCHEMA_VALIDITY_RATE (parses + policy-accepts) | 0.96 | 50 | **1.00** | 15 |
| PLAN_VALIDITY_RATE (semantic, supported) | **1.00** | 44 | **0.25** | 12 |
| TOOL_SELECTION_ACCURACY | **1.00** | 50 | **0.40** | 15 |
| REQUIRED_TOOL_COVERAGE (mean) | **1.00** | 50 | **0.40** | 15 |
| EXACT_MATCH_RATE (not gating) | 0.90 | 50 | 0.20 | 15 |
| TASK_ORDER_CORRECTNESS | 1.00 | 50 | 1.00 | 15 |
| DEPENDENCY_VALIDITY | 1.00 | 203 | 1.00 | 45 |
| UNSUPPORTED_ACTION_RATE (plan, executable) | **0.00** | 47 | **0.27** | 15 |
| UNNECESSARY_TOOL_SELECTION_RATE | 0.125 | 48 | 0.60 | 15 |
| PLAN_COMPLETION_COMPATIBILITY | 1.00 | 50 | 1.00 | 15 |
| ADVERSARIAL_POLICY_REJECTION_RATE | 0.83 | 6 | 1.00 | 3 |
| AVG_PLAN_LENGTH (specialist steps) | 2.6 | 50 | 2.0 | 15 |
| PLANNING_LATENCY (median) | **<0.01 s** | 50 | **~100 s** | 15 |

By category (PLAN_VALIDITY / TOOL_SELECTION), rule vs llm:

| category | rule | llm (n=3) |
|----------|:----:|:---------:|
| single_step | 1.00 / 1.00 | **1.00 / 1.00** |
| temporal | 1.00 / 1.00 | **0.00 / 0.00** |
| optical_sar | 1.00 / 1.00 | **0.00 / 0.00** |
| multi_step | 1.00 / 1.00 | **0.00 / 0.00** |
| adversarial | 0.50 / 1.00 | 0.00 / 1.00 |

**What the LLM actually produced:** every one of the 15 outputs is clean,
schema-valid JSON (0 needed repair, 0 fell back). But the 2 B model **echoes the
in-prompt worked example almost verbatim** — for all 15 missions it returned the
same 4-step `VALIDATE → run_vqa → VERIFY → FINALIZE` plan, adapting only the
`goal` string. That is coincidentally correct for the 3 single-image VQA missions
(3/3) and wrong for every temporal / optical-SAR / multi-step mission (0/9): it
never selects `run_temporal_change`, `run_optical_sar`, `extract_changed_regions`,
or a multi-specialist chain. In 4/15 it placed `run_vqa` where the mission
explicitly forbids it (caught downstream by the policy layer — see below).
Earlier prompt variants without a worked example produced **malformed
recursively-nested JSON** (`"steps":[{"steps":[{…`) instead — neither prompt
regime yields a usable plan at this model size on CPU.

## LLM planner health (ARM B, N=15)

- parses to JSON: **15/15**
- schema-valid with **no** repair: **15/15**
- usable only after safe repair: 0/15
- fell back to RuleBasedPlanner: 0/15

The repair + truncation-salvage layer was exercised in unit tests
(`test_g16_agent.py`) and on the earlier malformed-JSON prompt regimes; with the
final compact prompt the model's output is already schema-clean, so the guard
that mattered here was the **policy layer** (it rejects/neutralises the
wrong-tool plans) and the **deterministic fallback** (which the agent uses on
every non-VQA mission in practice).

## Execution results — baseline vs LLM agent

**N = 6** real-model missions (ss-01, tm-01, mi-01, mi-02, mi-03, ad-06), LLM
planner in the loop, run **before** the intent cross-check below was added — i.e.
this is what the G15 stack did with a weak LLM planner:

| metric | value | N | reading |
|--------|:-----:|:-:|---------|
| planner actually used | `llm` ×6 | 6 | the LLM never failed to produce a plan — it produced the echo |
| MISSION_COMPLETION_RATE | 1.00 | 6 | every plan reached FINALIZING… |
| **FINAL_ANSWER_FACTUAL_CONSISTENCY** | **0.33** | 6 | …but only 2/6 answers actually addressed the mission |
| **UNSUPPORTED_ACTION_RATE (forbidden tools that RAN)** | **0.67** | 6 | 4/6 executed `run_vqa` on a mission whose spec forbids it |
| EVIDENCE_PRESERVATION_RATE | 1.00 | 6 | |
| VERIFICATION_PRESERVATION_RATE | 1.00 | 6 | |
| UNNECESSARY_TOOL_CALL_RATE | 0.00 | 6 | (only 1 tool call per mission — the echo) |
| avg tool calls / mission | 1.0 | 6 | vs the rule-agent's 2.33 on multi-step (G15) |
| avg latency | ~744 s | 6 | LLM plan + cold specialist loads, CPU |
| baseline vs agent (specialists run) | baseline 1.0 · agent 1.0 | 6 | the LLM-agent ran **one** specialist — the same as the baseline |

Concrete failure: for mi-01 *"Investigate this area. Identify significant changes
between the two observations, locate the affected structures, and use SAR
evidence…"* the LLM-agent answered **"The image shows a large area of land
covered in green vegetation. (Verification: SUPPORTED.)"** — a VQA answer to img0,
marked verified.

### The gap this exposed, and the fix (Part 22 — improve the weakest measured component)

The 12-check **policy layer verifies a plan is *structurally* legal** (right tool
for its *own declared* task, valid deps, image count, co-registration, no cycle,
step cap, …). It **cannot** tell that a plan which answers "investigate the
changes between two images" with a single `run_vqa` step is *under-scoped for the
mission* — that plan is internally consistent. So the weak LLM plan passed policy
and executed.

**Fix:** `agent_runner._plan_intent_mismatch` — an independent second opinion
from the deterministic query interpreter, applied to LLM plans only, **after**
the policy check. If the mission intent is `change` / `semantic-change` /
`optical-sar` (or a ≥2-image mission) but the plan does nothing but single-image
analysis (`run_vqa` / `run_scene_retrieval`), the plan is rejected with
`PLAN_INTENT_MISMATCH` → the **visible deterministic fallback**
(`resolution.qualifier = PLANNER_UNAVAILABLE`, `AGENT FALLBACK` warning). It is
deliberately conservative — a merely *different* valid plan (alternative
ordering, an extra check) is not a mismatch.

On the 6 exec missions this cross-check fires for **5/6** (all but ss-01, which is
a genuine VQA mission) → those missions now fall back to `RuleBasedPlanner` and
run the correct specialists. Validated by `apps/backend/tests/test_g16_agent.py`
(`test_plan_intent_cross_check_*`); the exec numbers above are the **pre-fix**
measurement kept for the record.

Net: with the cross-check, an LLM plan is executed only when it passes **both**
the policy layer **and** the intent check — in practice, only single-image VQA
missions. Everything else uses the deterministic planner. The LLM planner adds no
execution value; it is safely contained.

## Paraphrase robustness (Part 10)

40 paraphrases across 5 capability families
(`evaluation/agent/reports/G16_PARAPHRASE_ROBUSTNESS.md`). **RULE arm: 1.00
family-consistency** (40/40) after a grounding-keyword patch (3 locative
paraphrases — "outline the main road", "which part of the image contains…",
"show me where … is" — had fallen through to VQA). The **LLM-arm paraphrase
sweep was not run**: the N=15 plan cache already shows the echo failure mode is
mission-independent (same plan for every mission across all 5 families), so a
paraphrase sweep — ~40 × 100 s on CPU — would only reproduce it. The harness
(`run_paraphrase_eval.py --llm-cache`) supports it on a GPU host.

## Replanning & early stopping (Parts 11–12) + flagship adaptivity (Parts 15–16)

Exec phase (N=6, echo plans): 0 replans, EARLY_STOP_RATE 0.00,
MAX_STEP_VIOLATION_RATE 0.00, UNNECESSARY_TOOL_CALL_RATE 0.00 — the 1-step echo
plan has nothing to replan or stop. G15 measured all 6 `ReplanReason`s and the
`NEW_EVIDENCE` early stop (tm-10). `repair.salvage_truncated` covers the
malformed-JSON regime.

**Flagship, actual local LLM, two environments** — same mission text, same
planner, only the post-event image differs
(`scripts/demo/run_g16_flagship.py` → `docs/sih/evidence/demos/g16_llm_flagship_case{A,B}.json`):

| | CASE A (real change) | CASE B (near-identical T1/T2) |
|---|---|---|
| LLM plan | echo `VALIDATE→run_vqa→VERIFY→FINALIZE` | echo `VALIDATE→run_vqa→VERIFY→FINALIZE` |
| intent cross-check | **PLAN_INTENT_MISMATCH** → re-plan | **PLAN_INTENT_MISMATCH** → re-plan |
| executed plan (`rule_based_fallback`) | `VALIDATE→TEMPORAL_CHANGE→EXTRACT_CHANGED_REGIONS→GROUND_OBJECT→OPTICAL_SAR→CROSS_CHECK→VERIFY→SUMMARIZE→FINALIZE` | same plan… |
| tool calls | **4** | **2** |
| replans | — | **`NEW_EVIDENCE`** (negligible change → skip region/ground/SAR) + `TOOL_FAILURE` (grounding found nothing on the unchanged scene, handled) |
| early_stopped | False | **True** |
| conclusion | "~25.3 % of the scene changed, 6 changed regions, 1 structure located, optical+SAR computed. Verification: SUPPORTED." | "1 step(s) failed. Verification: SUPPORTED." (no fabricated change) |

The execution path **genuinely depends on the observations** — CASE B is shorter
and stops early. Note both cases show `planner_used: rule_based_fallback`: the
adaptivity is real, but it comes from the RuleBasedPlanner + the bounded
observe/replan executor, **not** the 2 B LLM (which produced the same echo for
both). This is the flagship "with the actual LLM planner" — and it demonstrates,
concretely, that the LLM adds nothing and the guard + deterministic planner carry
the mission.

## Final decision (Part 21)

1. **Is the local LLM planner reliable enough for production?**
   **No.** On this hardware (RTX 3050 Ti 4 GB, CPU-only torch) Qwen2-VL-2B
   text-only takes ~100 s/plan and does not plan — it echoes the prompt example
   (semantic PLAN_VALIDITY 0.25, TOOL_SELECTION 0.40 on N=15; 0/9 on non-VQA
   missions). Worse, its plans are *structurally* valid, so the exec phase
   measured it running the wrong specialist end-to-end
   (FINAL_ANSWER_FACTUAL_CONSISTENCY 0.33, forbidden-tool-that-RAN 0.67 on N=6)
   until the G16 intent cross-check was added.
2. **Does the agent materially outperform the deterministic baseline on
   multi-step missions?** *With the RuleBasedPlanner* — yes (G15/G16 ARM A: the
   rule-agent runs 2.33 required specialists vs the baseline's 1.0, plan validity
   1.00). *With the local LLM planner* — **no.** Pre-fix it was *worse* than the
   baseline (VQA answers to investigation missions, 0.33 factual consistency).
   Post-fix the intent cross-check routes those missions to the deterministic
   planner, so the LLM-agent equals the rule-agent and is never worse — but the
   LLM contributes nothing.
3. **Where does the agent fail?** The LLM planner: (a) example-echo — never
   selects the temporal / optical-SAR / multi-step specialists; (b) without an
   example, malformed recursive JSON; (c) ~100 s latency; (d) its wrong plans are
   structurally valid, so the *policy layer alone* did not stop them — the new
   intent cross-check does. The RuleBasedPlanner: mild over-planning — on ~6/50
   "which regions changed" / "investigation summary" missions it adds
   `run_grounding` / `run_optical_sar` the mission did not ask for
   (UNNECESSARY_TOOL_SELECTION_RATE 0.125).
4. **Should the local LLM remain / become the default planner?** **No.**
   `RuleBasedPlanner` stays the default. The LLM is opt-in
   (`SATQUERY_PLANNER=llm`) behind the repair + policy + deterministic-fallback
   guard.
5. **Should RuleBasedPlanner remain the fallback?** **Yes** — and in practice it
   is the *primary*: the LLM path falls back on every non-trivial mission.
6. **Is additional agent-architecture work necessary?** **One targeted addition,
   done in G16:** the **plan-intent cross-check** — the 12-check policy layer
   guards *structural* legality but not *mission fit*, and the exec phase proved
   that gap matters with a weak planner. `_plan_intent_mismatch` closes it
   (LLM-only, conservative, routes to the visible deterministic fallback). No
   other architecture change: schema-repair, policy, and the visible fallback
   otherwise held. The weakest *measured* component remains the **planner
   model** — a capable planner needs a GPU host + a ≥7 B or planning-tuned model,
   **or** a hybrid where the LLM only proposes a task list and the rule engine
   fills in dependencies / tools / bookkeeping. Secondary: trim the
   RuleBasedPlanner's over-planning on region-only missions.

## Claim discipline

Supported: *schema-constrained LLM planning*, *policy-constrained agentic
execution*, *bounded observe/replan*, *evidence-aware multi-step orchestration*,
*adaptive specialist selection based on intermediate observations*. **Not**
claimed: "fully autonomous", "hallucination-free", "state-of-the-art",
"real-time". Frozen model stack (ADR-021) unchanged. No numerical confidence —
categorical only (`verified / partially verified / insufficient evidence /
contradicted / planner fallback`).
