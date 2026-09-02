# G17 — Definition of Done (Part 21) + Final Question (Part 22)

Legend: ✅ done · 🔄 measured on a bounded N (CPU-only 2 B) · ⬜ deferred (documented)

| # | criterion | status | evidence |
|--:|-----------|:------:|----------|
| 1 | hybrid architecture implemented | ✅ | `agent/intent.py` — `Intent` → `PlanSynthesizer` → `HybridPlanner`; `SATQUERY_PLANNER=hybrid` |
| 2 | pure LLM planner no longer production-default | ✅ | default is `RuleBasedPlanner`; `docs/G17_ARCHITECTURE_DECISION.md` records B = REJECTED FOR PRODUCTION |
| 3 | LLM intent extraction works | ✅ (runs) / measured poor | `LlmIntentExtractor` runs (~35–40 s/mission); **INTENT_SCHEMA_VALIDITY 0.82**, **INTENT_TASK_ACCURACY 0.317** (N=82) — the 2 B model misclassifies intent too (VQA/GROUNDING→SCENE, OPTICAL_SAR→INVESTIGATION); reliable only on the INVESTIGATION family (1.00) |
| 4 | deterministic plan synthesis works | ✅ | `PlanSynthesizer` == `RuleBasedPlanner` tool sequence on a 10-mission equivalence check (`test_g17_agent.py`) |
| 5 | bounded execution remains | ✅ | unchanged G15/G16 executor; `MAX_STEPS=8` |
| 6 | observation-driven continuation works | ✅ | G15 mechanism intact; flagship CASE A runs the full chain |
| 7 | observation-driven stopping works | ✅ | flagship CASE B: `NEW_EVIDENCE` replan → `early_stopped=True` |
| 8 | evidence-aware synthesis works | ✅ | `_synthesize` builds claims only from observed specialist output; `docs/G17_TRUST_LAYER.md` §claim-level evidence |
| 9 | confidence category works | ✅ | `trust.py::assess_confidence` → `HIGH/MEDIUM/LOW/INSUFFICIENT_EVIDENCE`; on `AgentInvestigationResult.confidence`; 8 tests |
| 10 | 100 frozen missions exist | ✅ | `evaluation/agent/frozen_missions_100.json` (20/category; first 50 verbatim + `expected_intent`) |
| 11 | RuleBased baseline evaluated | ✅ | ARM A, N=100 |
| 12 | pure LLM evaluated | ✅ | ARM B — carried from G16 (N=15), **preserved** in the G17 report |
| 13 | hybrid evaluated | ✅ | ARM C, **N=100** (full intent cache); PLAN_VALIDITY 0.591 / TOOL_SELECTION 0.66 vs ARM A 0.886 / 0.90 |
| 14 | metrics reported with N | ✅ | every rate in `G17_HYBRID_EVALUATION.{md,json}` carries N + a definition |
| 15 | multi-step value comparison completed | ✅ | plan: hybrid **ties** rule on `multi_step` (1.00/1.00, intent-acc 1.00); B fails these (G16). **Exec (N=8): baseline 1.0 specialists vs hybrid 2.25 on multi_step**; MISSION_COMPLETION / FACTUAL_CONSISTENCY / EVIDENCE / VERIFICATION all **1.00**; UNSUPPORTED_ACTION **0.00** |
| 16 | adversarial evaluation completed | ✅ | ADVERSARIAL_CORRECTLY_HANDLED_RATE **0.917 both A and C** (11/12); plan UNSUPPORTED_ACTION A 0.053 / C 0.125; "LLM cannot break deterministic planning" confirmed at plan phase |
| 17 | paraphrase robustness completed | ✅ | 50 paraphrase variants (10/family). Rule 1.00→0.886 plan validity on the 100-set; hybrid intent not phrasing-robust either (single_step intent-acc 0.053) — **only** multi_step paraphrases map consistently (intent-acc 1.00) |
| 18 | fallback works | ✅ | `HybridPlanner` → rule intent on any extractor failure, tagged `rule_based_fallback`; `_intent_plausible` image-count guard; UI states it; `test_g17_agent.py` |
| 19 | flagship works using hybrid architecture | ✅ | `run_g17_flagship.py` → `g17_hybrid_flagship_case{A,B}.json` (real models). CASE A: INVESTIGATION → 9-step plan → 4 specialists → SUPPORTED / HIGH. On this verbose phrasing the LLM intent was unusable → visible `rule_based_fallback`; exec `mi-02/03/04` show the `hybrid_llm` intent path working on other investigation phrasings |
| 20 | flagship not hard-coded | ✅ | plan synthesised from the extracted (or fallback) Intent; two environments, same mission text; executor early-stop is the G15/G16 mechanism |
| 21 | low-change case → shorter plan/execution | ✅ | **CASE A: 4 tool calls, not early-stopped. CASE B (no change): 2 tool calls, `NEW_EVIDENCE` + `TOOL_FAILURE` replans, `early_stopped=True`.** Execution responds to the real ChangeFormer output |
| 22 | evidence preserved | ✅ | EVIDENCE_PRESERVATION_RATE **1.00** (exec N=8) |
| 23 | verification preserved | ✅ | VERIFICATION_PRESERVATION_RATE **1.00** (exec N=8) |
| 24 | LoRA adapter persisted | 🔄 plumbing ✅ | `--lora-weights` optional on `CromaAdapter` + `croma_infer.py` (merged-delta apply, fails loudly if 0 layers match; provenance `encoder_mode`); production default = frozen. Persist run = `run_g17_larger_de.sh` step 4 → `models/checkpoints/exp008_croma_lora.pt` `<FILL — run status>` |
| 25 | larger D/E run completed where feasible | 🔄 extract ✅ | **full DFC2020 validation (986 patches)** extracted → `models/cache/dfc2020_g17_larger/` + `dfc2020_g17_larger_split.json` (G12 400/200 split **untouched**). Features/probe/LoRA = `run_g17_larger_de.sh` `<FILL — multi-hour CPU job; status>` |
| 26 | GPU status documented honestly | ✅ | CPU only; CUDA **UNVERIFIED** (`torch 2.13.0+cpu`); no numerical VRAM claim; measured latencies stated |
| 27 | RemoteSAM licensing status documented | ✅ | `model_registry.yaml` — **NOT STATED**, re-checked G17, upstream issue is the next step; caveat preserved, RemoteSAM not removed |
| 28 | all tests green | ✅ | **249 fast pass, 0 fail** (`packages` + `apps/backend/tests`, `-m "not slow and not gpu and not integration"`) — 226 pre-G17 + 23 G17 |
| 29 | no architecture regression | ✅ | `PlanSynthesizer` equivalence check; `RuleBasedPlanner` untouched; deterministic router still the guard |
| 30 | no fake claims | ✅ | G16 negative result preserved verbatim; every ARM B/C N stated; confidence explicitly NOT a probability |

## Final question (Part 22) — which architecture is best for SatQuery?

**A — pure deterministic — is the production default.** Measured on 100 frozen
missions:

| | A rule | B pure-LLM (G16) | C hybrid |
|---|:---:|:---:|:---:|
| PLAN_VALIDITY | **0.886** | 0.25 | 0.591 |
| TOOL_SELECTION | **0.90** | 0.40 | 0.66 |
| UNNECESSARY_TOOL_SELECTION | **0.20** | — | 0.526 |
| planner latency / plan | **<0.01 s** | ~100 s | ~40 s |
| adversarial handled | 0.917 | — | 0.917 |
| INTENT_TASK_ACCURACY | — | — | 0.317 (N=82) |

- **A wins on reliability.** **B stays rejected** (G16). **C does not beat A** —
  the 2 B model classifies intent correctly only 31.7 % of the time.
- **C helps on one axis only**: the INVESTIGATION family (LLM intent accuracy
  1.00, C ties A, phrasing-robust) + temporal tool-selection (0.95 vs 0.85).
  Per the brief's rule that is *language coverage* → C is an **enhancement**.
- **Comparable ⇒ prefer the simpler** — A is simpler *and* better overall.

**Decision:** `RuleBasedPlanner` (A) = production default. `HybridPlanner` (C) =
opt-in enhancement (`SATQUERY_PLANNER=hybrid`), useful today only for verbose
multi-step investigation missions, behind the same guards. Revisit C when a
phrasing-robust intent classifier is available (GPU + larger instruction-tuned
model, or a small fine-tuned intent head). The **trust / confidence layer is kept
regardless of planner** — it is a function of the executed evidence.
