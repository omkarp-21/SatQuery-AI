# G17 — Planner Architecture Decision

> This record is **append-only with respect to the G16 negative finding**. G16
> proved the pure local LLM planner is not production-viable; G17 does not delete
> that — it turns it into a better architecture.

## The three candidates

| id | architecture | planner owns |
|----|--------------|--------------|
| **A** | **pure deterministic** — `RuleBasedPlanner` (keyword/feature → plan) | everything |
| **B** | **pure local LLM planner** — `LlmPlanner` (mission → `AgentPlan` JSON) | intent **and** execution graph |
| **C** | **hybrid** — `HybridPlanner` = LLM **intent extraction** → deterministic **plan synthesis** | LLM: intent only · rules: the execution graph |

All three feed the **same** downstream: 12-check policy layer → bounded
observe/replan executor → evidence → verification → synthesis. The G14 principle
is unchanged: *the LLM never controls execution; the deterministic system is the
policy / execution guard.*

## What G16 measured (kept verbatim — see `docs/G16_REAL_LLM_EVALUATION.md`)

Pure local LLM planner — **Qwen2-VL-2B-Instruct, text-only, CPU**:

| metric | value | N |
|--------|:-----:|:-:|
| SCHEMA_VALIDITY_RATE | 1.00 | 15 |
| PLAN_VALIDITY_RATE (semantic) | **0.25** | 12 |
| TOOL_SELECTION_ACCURACY | **0.40** | 15 |
| by category (plan validity): single / temporal / opt-SAR / multi / adv | 1.0 / **0.0 / 0.0 / 0.0** / 0.0 | 3 each |
| planning latency (median) | **~100 s** | 15 |
| exec FINAL_ANSWER_FACTUAL_CONSISTENCY | **0.33** | 6 |
| exec forbidden-tool-that-RAN | **0.67** | 6 |

Failure mode: the 2 B model **echoes the prompt's worked example** — the same
`VALIDATE → run_vqa → VERIFY → FINALIZE` plan for every mission. Structurally
valid, so it passed the policy layer and executed; the G16 **plan-intent
cross-check** (`agent_runner._plan_intent_mismatch`) was added to contain it.

## G17 decisions (pre-evaluation — confirmed / revised by `G17_HYBRID_EVALUATION`)

| component | status | reason |
|-----------|--------|--------|
| **Pure LLM planner (B)** | **REJECTED FOR PRODUCTION** | 2 B planner quality (0.25 semantic validity, 0.40 tool-selection) + ~100 s latency + example-echo make reliable execution planning impossible on the hardware target |
| **RuleBasedPlanner (A)** | **PRIMARY / DEFAULT** | 1.00 plan validity + tool-selection on 50 frozen missions, <0.01 s; one measured flaw (over-plans ~6 region-only missions) |
| **G16 intent cross-check** | **MANDATORY, KEPT** | it is the only thing that stopped structurally-valid wrong LLM plans from executing |
| **LLM-assisted intent extraction (C)** | **BUILT + EVALUATED (G17). Not the default — shipped as an OPT-IN enhancement.** | The reduced task (typed `Intent`, not a plan) is *also* beyond the 2 B model on CPU: `INTENT_TASK_ACCURACY` **0.317** (N=82), `INTENT_SCHEMA_VALIDITY` 0.82. The deterministic `PlanSynthesizer` + a plausibility guard + the G16 cross-check + the rule fallback contain the bad intents, so C beats B — but **not A** (plan validity 0.591 vs 0.886, tool-selection 0.66 vs 0.90, +40 s/plan). C **ties A only on the INVESTIGATION family** (intent accuracy 1.00 there) and is marginally ahead on temporal tool-selection. |

## Hardware target (unchanged)

ASUS Zephyrus G14 · RTX 3050 Ti **4 GB** · CPU fallback. No numerical VRAM claim
is made; CUDA is **UNVERIFIED** on the dev host (`torch 2.13.0+cpu`). The intent
extractor emits a ~150-token JSON object (vs the planner's ~450-token graph), so
its latency is a fraction of the pure-LLM planner's.

## Final question G17 answers

> Which architecture is actually best for SatQuery — A, B, or C?

**A — pure deterministic — is the production default.** Measured on 100 frozen
missions: A plan-validity **0.886** / tool-selection **0.90** / latency **<0.01 s**;
C **0.591 / 0.66 / ~40 s**; B (G16) **0.25 / 0.40 / ~100 s**. A wins on
reliability; C helps only on the INVESTIGATION family (LLM intent accuracy 1.00
there, C ties A) — *language coverage on the flagship family*, which the brief's
rule classifies as an **enhancement**, not a reason to switch. C ships opt-in
(`SATQUERY_PLANNER=hybrid`); B stays rejected for production. Full reasoning:
`docs/G17_HYBRID_AGENT_REPORT.md` §Decision.
