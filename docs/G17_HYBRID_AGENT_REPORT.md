# G17 — Hybrid Agent + Trust Layer + Scale Validation

> **Internal frozen evaluation — NOT an external benchmark.** G16 proved the pure
> local 2 B LLM planner is not production-viable (semantic plan validity 0.25,
> tool-selection 0.40, ~100 s, example-echo). G17 turns that finding into a
> better architecture and re-measures on **100** frozen missions.
>
> The G16 negative result is preserved — see `docs/G16_REAL_LLM_EVALUATION.md`
> and ARM B below.

## Architecture (see `docs/G17_ARCHITECTURE_DECISION.md`)

```
mission text
  -> LLM INTENT EXTRACTOR      (local Qwen2-VL-2B, text-only; ~150-token typed JSON)
  -> typed Intent               (task_family + required_capabilities + flags + ambiguity)
  -> DETERMINISTIC PlanSynthesizer  (task ontology + tool registry + dependency rules)
  -> AgentPlan
  -> 12-check POLICY layer + G16 plan-intent cross-check
  -> BOUNDED ADAPTIVE EXECUTION  (observe each tool -> continue / replan / stop)
  -> EVIDENCE -> VERIFICATION -> TRUST LAYER (confidence CATEGORY) -> SYNTHESIS
```

The LLM classifies the goal. It **never** chooses a tool, orders a step, or
controls execution. `PlanSynthesizer` owns execution safety. If LLM intent
extraction fails, the deterministic keyword extractor is used and tagged
`source="rule_based_fallback"` — never silent (`docs/G17` Part 13).

New code:

| file | role |
|------|------|
| `packages/agents/src/satquery_agents/agent/schemas.py` | `Intent`, `TaskFamily`, `Capability` |
| `packages/agents/src/satquery_agents/agent/intent.py` | `derive_intent_rulebased`, `PlanSynthesizer`, `LlmIntentExtractor`, `intent_from_raw` (parse + safe repair), `HybridPlanner` |
| `apps/backend/app/services/trust.py` | `assess_confidence` — evidence-derived confidence CATEGORY (`docs/G17_TRUST_LAYER.md`) |
| `evaluation/agent/build_missions_100.py` | the 100-mission frozen set |
| `evaluation/agent/run_g17_eval.py` | 3-arm evaluation |
| `scripts/demo/run_g17_flagship.py` | flagship with the hybrid architecture, CASE A/B |

`PlanSynthesizer` reproduces `RuleBasedPlanner`'s plan tool-sequence exactly on a
10-mission equivalence check (`test_g17_agent.py`) — zero regression — and
additionally **trims the G16 over-planning flaw**: a `TEMPORAL_CHANGE +
CHANGED_REGIONS` intent that is *not* an investigation yields
`VALIDATE → TEMPORAL_CHANGE → EXTRACT_CHANGED_REGIONS → VERIFY → SUMMARIZE →
FINALIZE` (no grounding / SAR).

## Method

- **100 frozen missions** (`evaluation/agent/frozen_missions_100.json`): the 50
  from G15/G16 **verbatim** (+ an `expected_intent` annotation) plus 50
  paraphrase / scenario variants — 20 per category (single_step, temporal,
  optical_sar, multi_step, adversarial).
- **ARM A** `RuleBasedPlanner` (all 100). **ARM B** pure local LLM planner —
  **carried forward from G16** (N=15), not re-run. **ARM C** hybrid — LLM intent
  cached once via the persistent model server (**N = 100**, CPU-only 2 B,
  ~35–40 s/intent), then deterministic synthesis + policy.
- Semantic plan scoring (`plan_scorer.py`): alternative valid orderings accepted;
  `EXACT_MATCH_RATE` reported, not gating.
- Reproduce: `evaluation/agent/run_g17_eval.py` → `G17_HYBRID_EVALUATION.{md,json}`.

## Planning results — A vs B vs C

| metric | A rule (N) | B pure-LLM (N) | C hybrid (N) |
|--------|:----------:|:--------------:|:------------:|
| PLAN_VALIDITY_RATE (semantic, supported) | **0.886** (88) | 0.25 (12) | **0.591** (88) |
| TOOL_SELECTION_ACCURACY | **0.90** (100) | 0.40 (15) | **0.66** (100) |
| REQUIRED_TOOL_COVERAGE (mean) | **0.905** (100) | — | 0.66 (100) |
| TASK_ORDER_CORRECTNESS | 1.00 (100) | — | 1.00 (100) |
| DEPENDENCY_VALIDITY | 1.00 (403 edges) | 1.00 (45) | 1.00 (486 edges) |
| UNSUPPORTED_ACTION_RATE (plan, executable) | **0.053** (94) | 0.267 (15) | 0.125 (96) |
| UNNECESSARY_TOOL_SELECTION_RATE | **0.20** (95) | — | **0.526** (97) |
| ADVERSARIAL_CORRECTLY_HANDLED_RATE | 0.917 (12) | — | 0.917 (12) |
| AVG_PLAN_LENGTH (specialist steps) | 2.58 | — | 3.07 |
| PLANNER_LATENCY (median) | **<0.01 s** | ~100 s | **~40 s** |

**ARM C is ~30 points worse than ARM A on plan validity, ~24 on tool selection,
over-plans 2.6× as often, and adds ~40 s/plan.** It is *better* than the pure
LLM planner (B) because the deterministic synthesizer + the plausibility guard +
the G16 cross-check + the rule fallback contain the bad intents — but it does
not beat A.

## LLM intent extraction quality (ARM C)

| | value | N |
|---|:---:|:-:|
| INTENT_SCHEMA_VALIDITY_RATE (parses + validates, post safe-repair) | **0.82** | 100 |
| INTENT_TASK_ACCURACY (`task_family` == `expected_intent.task_family`) | **0.317** | 82 |
| fell back to the deterministic intent (unparseable or image-count-implausible) | **29** | 100 |

**By category — PLAN_VALIDITY / TOOL_SELECTION (rule vs hybrid) · INTENT_TASK_ACCURACY (hybrid):**

| category (n=20) | rule | hybrid | intent-task-acc |
|-----------------|:----:|:------:|:---------------:|
| **multi_step** | 1.00 / 1.00 | **1.00 / 1.00** | **1.00** |
| **temporal** | 0.85 / 0.85 | **0.85 / 0.95** | 0.556 |
| optical_sar | 1.00 / 1.00 | **0.35 / 0.35** | 0.071 |
| single_step | 0.75 / 0.75 | **0.20 / 0.20** | 0.053 |
| adversarial | 0.75 / 0.90 | 0.50 / 0.80 | 0.00 |

**The one place the LLM intent is reliable is the INVESTIGATION family** —
verbose multi-capability missions ("investigate… changes… buildings… SAR") where
`INVESTIGATION` is unambiguous: intent accuracy **1.00**, and hybrid **ties** the
rule planner (1.00 / 1.00). On **temporal** the hybrid is marginally *ahead* on
tool selection (0.95 vs 0.85). Everywhere else — single-image VQA/GROUNDING (the
2 B model calls them SCENE) and OPTICAL_SAR (it calls them INVESTIGATION) — the
hybrid regresses hard.

## Multi-step value test (Part 10)

On the 20 **multi_step** missions the hybrid **matches** the rule planner
(PLAN_VALIDITY 1.00, TOOL_SELECTION 1.00) and the LLM intent is 100 % correct —
because "INVESTIGATION" is the one class the 2 B model reads reliably. Neither
arm is *worse* here; the hybrid adds ~40 s of latency for no gain. The pure LLM
planner (B) fails these entirely (0/9 on non-VQA in G16).

**Exec phase — hybrid agent, real frozen-stack models, N=8** (4 multi_step,
3 temporal, 1 optical_sar):

| metric | value | N |
|--------|:-----:|:-:|
| MISSION_COMPLETION_RATE | **1.00** | 8 |
| FINAL_ANSWER_FACTUAL_CONSISTENCY | **1.00** | 8 |
| EVIDENCE_PRESERVATION_RATE | **1.00** | 8 |
| VERIFICATION_PRESERVATION_RATE | **1.00** | 8 |
| **UNSUPPORTED_ACTION_RATE (forbidden tools that RAN)** | **0.00** | 14 attempts |
| UNNECESSARY_TOOL_CALL_RATE | **0.00** | 21 calls |
| EARLY_STOP / MAX_STEP_VIOLATION / REPLAN rate | 0.00 / 0.00 / 0.00 | 8 |
| avg tool calls / mission | 2.62 | 8 |
| avg total mission latency | 97.6 s | 8 |
| planner actually used | `hybrid_llm` ×6, `hybrid_rule_fallback` ×2 | 8 |
| confidence category | HIGH ×7, MEDIUM ×1 | 8 |

**Baseline (`/analyze`) vs hybrid agent — required specialists run:**
multi_step (N=4) baseline **1.0** vs hybrid **2.25**; all (N=8) 1.0 vs 1.75.

At the **execution** level the hybrid is **safe and effective on the sample**:
every mission completed, every answer was factually consistent with an observed
result, **zero forbidden tool calls ran** (vs the pure LLM planner's 0.67 in
G16), and the guards (policy + G16 cross-check + rule fallback) absorbed the
intent misclassifications — `os-01` (OPTICAL_SAR, misclassified) and `mi-01`
(unparseable intent) both fell back to the rule intent, visibly, and still
completed with HIGH/MEDIUM confidence. On multi-step missions the hybrid runs
~2.25× the baseline's specialists — the same functional value the rule-agent
provides (G15). The plan-phase weakness (family misclassification) does **not**
translate into unsafe or wrong execution — but it does cost ~40 s of planning
latency and occasional over-planning (`tm-03`: 2 specialists where 1 was needed,
still coherent).

## Paraphrase robustness (Part 11)

The 50 new missions are 10 paraphrases per family (variants 11–20). The rule
planner drops from 1.00 (the 50-mission set) to **0.886** plan validity on the
100-set — the extra paraphrases stress its keyword matching, especially
single_step (0.75) and adversarial (0.75). The hybrid does **not** recover this:
its intent extraction is not phrasing-robust either (single_step intent accuracy
0.053). Only the **multi_step** family paraphrases map consistently
(intent-task-acc 1.00) — for those, the hybrid's plan is phrasing-independent
because every paraphrase still classifies as INVESTIGATION.

## Adversarial (Part 12)

`ADVERSARIAL_CORRECTLY_HANDLED_RATE` is **0.917** for *both* A and C (11/12) —
the deterministic policy layer + the G16 intent cross-check stop every
forbidden/illegal action regardless of what the LLM intent said. Plan-phase
`UNSUPPORTED_ACTION_RATE`: A 0.053, C 0.125 (the higher C figure is
mission-family mismatch, not an illegal tool — the executable plans still run no
*forbidden* specialist). **Exec `UNSUPPORTED_ACTION_RATE`: 0.00** (14 tool
attempts) — no forbidden tool reached execution. **The LLM cannot break
deterministic planning** — confirmed at both the plan and the exec phase.

## Flagship (Parts 14–15)

The N=8 exec sample already runs the hybrid flagship shape end-to-end: the four
`mi-*` missions each extract an `INVESTIGATION` intent (or fall back to the rule
intent — `mi-01`), synthesise the `VALIDATE → TEMPORAL_CHANGE →
EXTRACT_CHANGED_REGIONS → GROUND_OBJECT → OPTICAL_SAR_ANALYSIS → CROSS_CHECK →
VERIFY → SUMMARIZE → FINALIZE` plan, run 2–4 real specialists, finish
`SUPPORTED` with `HIGH` confidence. `scripts/demo/run_g17_flagship.py` captures
the dedicated CASE A (change) vs CASE B (near-identical T1/T2, expect
`NEW_EVIDENCE` early stop) contrast with the hybrid planner →
`docs/sih/evidence/demos/g17_hybrid_flagship_case{A,B}.json` (real models):

| | CASE A (real change) | CASE B (near-identical T1/T2) |
|---|---|---|
| intent | `INVESTIGATION` (source `rule_based_fallback` — the LLM intent for this verbose em-dashed phrasing was unusable) | `INVESTIGATION` (same, `rule_based_fallback`) |
| synthesised plan | `VALIDATE → TEMPORAL_CHANGE → EXTRACT_CHANGED_REGIONS → GROUND_OBJECT → OPTICAL_SAR → CROSS_CHECK → VERIFY → SUMMARIZE → FINALIZE` | identical |
| tool calls | **4** | **2** |
| replans | — | **`NEW_EVIDENCE`** (negligible change → skip region/ground/SAR) + `TOOL_FAILURE` (grounding found nothing on the unchanged scene) |
| early_stopped | False | **True** |
| verification / confidence | SUPPORTED / **HIGH** | SUPPORTED / **MEDIUM** (−1 for the intent fallback) |
| wall | 230 s | 145 s |

CASE B is shorter and stops early — **the execution path responds to the real
ChangeFormer output**, not a hard-coded outcome. On this particular verbose
phrasing the LLM intent was unusable and the hybrid **visibly** degraded to the
rule intent; the exec-sample `mi-02/03/04` rows show the `hybrid_llm` intent path
working on other investigation phrasings. The plan is synthesised from the
extracted (or fallback) Intent — never hard-coded for the flagship sentence.

## Trust layer (Parts 6–7)

`apps/backend/app/services/trust.py::assess_confidence` runs at the end of every
investigation (any planner) and sets `AgentInvestigationResult.confidence`:

```json
{ "category": "HIGH|MEDIUM|LOW|INSUFFICIENT_EVIDENCE", "score": 3.5,
  "reasons": ["All 4 planned specialist step(s) completed.", "Verification: SUPPORTED ...", ...],
  "signals": {"family":"multi_step","verification":"SUPPORTED","cross_check_inside":"1/1"},
  "hard_rule": null,
  "note": "evidence-derived category (docs/G17_TRUST_LAYER.md). NOT a calibrated probability." }
```

- **Hard rules** force `INSUFFICIENT_EVIDENCE`: verification `CONTRADICTED`, the
  primary specialist for the mission family failed, or no evidence was produced.
- **Additive signals** (documented in `docs/G17_TRUST_LAYER.md`): specialists
  completed (+2), evidence present (+1), verification SUPPORTED (+2), INCOHERENT
  step (−3), grounded GeoJSON (+1), cross-check agreement (+2/+1/−1), modality
  completeness (±1), ambiguity (−1/−2), planner fallback (−1), known limitations
  (−0.5 each). Map: ≥5 → HIGH, 2–5 → MEDIUM, <2 → LOW.
- It is **not** a probability and **not** a model output. `score` is internal;
  the UI shows only the category and the reasons ("WHY").
- Confidence-category distribution over the N=8 exec sample: **HIGH ×7, MEDIUM
  ×1** (the MEDIUM is `os-01` — the LLM intent was misclassified so the planner
  fell back to the rule intent, which the trust layer penalises −1).

**Claim-level evidence (Part 7):** every `key_findings` line is built only from an
observed specialist output. A grounding claim requires `validation_status ==
PASS`; an optical+SAR result is stated as "representation-level only — no textual
fact inferred"; a claim like *"SAR confirms construction"* is **never** emitted.
An `INCOHERENT` step's claim is withheld ("result withheld — it failed
verification"). See `docs/G17_TRUST_LAYER.md` §claim-level evidence for the table.

## UI trust panel (Part 16)

`apps/backend/app/static/index.html` INVESTIGATE view now shows, in order:
**Mission → Understood as** (`task_family · capabilities`, with the intent
`source`) **→ Status → Confidence** (category badge + "evidence-derived, NOT a
probability") **→ Models → Tool calls → Replans**; then the plan & execution
list, the replans table, key/spatial findings, verification, a dedicated
**Confidence + WHY** card (category, hard-rule if any, the reasons list), evidence,
warnings, and the collapsible trace. No fake "thinking", no chain-of-thought —
only actual system events.

## Deployment / GPU status (Part 17)

CPU mode only on the dev host (`torch 2.13.0+cpu`, `torch.cuda.is_available()` =
**False** — CUDA **UNVERIFIED**). No numerical VRAM claim is made. Measured
latencies on this run: LLM **intent** generation ~35–40 s/mission (persistent
model server; the ~150-token intent JSON is ~2–3× faster than the pure planner's
~450-token graph); LLM **planner** (G16) ~100 s/mission. Full hybrid-agent
mission latency (intent + specialists + synthesis, cold model loads): **~98 s
avg** over the N=8 exec sample. GPU mode was not tested (no CUDA build).

## RemoteSAM licence (Part 18)

**LICENSE NOT STATED** — preserved and re-checked on 2026-09-03: no LICENSE file
in `github.com/1e12Leon/RemoteSAM`, no model card on the HF checkpoint, and the
ACM MM 2025 paper does not state a weights licence. `model_registry.yaml` now
records this re-check and that an upstream issue asking for clarification is the
next step. RemoteSAM is **not removed** — it stays the capability-B grounding
specialist with the caveat intact, used only in the prototype.

## LoRA production path (Part 19)

- `CromaAdapter(lora_weights=...)` + `croma_infer.py --lora-weights` — an
  **optional** EXP-008 LoRA delta applied as a merged weight delta (fails loudly
  if 0 layers match — never silently frozen). `provenance` records
  `encoder_mode` (`frozen` / `lora_adapted (N layers)`) and the adapter hash.
- **Production default is `lora_weights=None` = frozen CROMA.** The adapted model
  is not the default and is not called such without larger validation.
- Persisting the adapter: `scripts/research/run_g17_larger_de.sh` step 4 runs
  `exp008_adapt.py --save-adapter models/checkpoints/exp008_croma_lora.pt` on the
  larger split. Run status: **launched** (`scripts/research/run_g17_larger_de.sh`,
  multi-hour CPU job — CROMA/DOFA feature extraction in progress); results land in
  `evaluation/reports/exp004_run2_*.{json,md}` and
  `models/checkpoints/exp008_croma_lora.pt`.

## Larger D/E validation (Part 20)

The **full DFC2020 validation split — 986 patches** (600 train / 386 eval) — was
extracted to `models/cache/dfc2020_g17_larger/` and
`evaluation/datasets/dfc2020_g17_larger_split.json`. **The G12 frozen 400/200
split and its results are untouched.** `scripts/research/run_g17_larger_de.sh`
chains: CROMA features → DOFA features → probe (CROMA optical-only vs joint vs
DOFA fused, bootstrap CIs) → EXP-008 frozen-vs-LoRA + persist. This is a
multi-hour CPU job — **launched** during G17; CROMA/DOFA feature extraction over
the 986 patches is in progress. Results land in
`evaluation/reports/exp004_run2_*.{json,md}` (probe: CROMA optical-only vs joint
vs DOFA fused, bootstrap CIs) + `models/checkpoints/exp008_croma_lora.pt`
(frozen-vs-LoRA). **Until it completes, the G12 n=200 result stands**: CROMA
joint macro-F1 0.793 vs optical-only 0.726 (DFC2020, n=200, *not* significant);
LoRA on frozen CROMA 0.643→0.704 (+0.061). No claim is upgraded on the strength
of the larger run before it finishes and is reviewed.

## Decision — which architecture is best for SatQuery? (A / B / C)

**A — pure deterministic — stays the production default.**

Measured, on 100 frozen missions:

| | A rule | C hybrid |
|---|:---:|:---:|
| PLAN_VALIDITY | **0.886** | 0.591 |
| TOOL_SELECTION | **0.90** | 0.66 |
| UNNECESSARY_TOOL_SELECTION | **0.20** | 0.526 |
| latency / plan | **<0.01 s** | ~40 s |
| adversarial handled | 0.917 | 0.917 |

Applying the brief's decision rule:

- **A wins on reliability** (validity, tool selection, over-planning, latency).
- **C does not win on mission completion** — it does not even hold plan validity;
  the 2 B model classifies `task_family` correctly only **31.7 %** of the time.
- **C helps only on one axis**: the INVESTIGATION family, where the LLM intent is
  reliable (accuracy 1.00) and the hybrid **ties** A while being phrasing-robust,
  and on temporal tool-selection (0.95 vs 0.85). That is *language coverage on
  the flagship family* — an **enhancement**, not a reason to switch the default.
- **When A and a candidate are comparable, prefer the simpler** — and A is
  simpler *and* better overall.

**Therefore:** `RuleBasedPlanner` (A) is the production default. `HybridPlanner`
(C) ships as an **opt-in enhancement** (`SATQUERY_PLANNER=hybrid`), useful today
only for verbose multi-step investigation missions, behind the same policy +
cross-check + fallback guards. The pure LLM planner (B) stays **rejected for
production** (G16). Revisit C broadly when a phrasing-robust intent classifier is
available — a GPU host with a larger instruction-tuned model, or a small
fine-tuned intent head. The **trust / confidence layer is kept regardless of
planner** — it is a function of the executed evidence, not the planner.

### What G17 delivered even though C is not the default

1. A clean, tested **separation of concerns** (LLM = intent, deterministic =
   execution) — the right shape for when a better intent model exists.
2. `PlanSynthesizer` — a single deterministic Intent→Plan mapping that both A's
   refactor target and C use; it **fixes the G16 over-planning flaw** on
   region-only missions.
3. The **trust / confidence layer** — evidence-derived category + claim-level
   evidence, on every investigation.
4. The mission set **doubled to 100** with `expected_intent` annotations.
5. The pure-LLM-planner failure (G16) is **preserved and contextualised**, not
   hidden — and now sits next to a measured hybrid.

## Claim discipline

Supported: *LLM-assisted intent understanding*, *deterministic plan synthesis*,
*policy-constrained execution*, *bounded observe/replan*, *evidence-derived
confidence category*. **Not** claimed: the LLM autonomously controls the system;
"fully autonomous"; "calibrated confidence"; "state-of-the-art"; "real-time".
Frozen model stack (ADR-021) unchanged. RemoteSAM licence caveat preserved.
