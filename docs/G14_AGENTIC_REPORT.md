# G14 — Agentic Geospatial Investigator

> **G15 hardened this** — structured replanning (6 enumerated reasons), explicit
> early termination, a visible deterministic fallback, 50 frozen missions, 13
> measured quality metrics. See `docs/G15_AGENT_IMPLEMENTATION.md` +
> `docs/G15_AGENT_EVALUATION.md`.

> SatQuery's differentiating feature: a natural‑language **mission** becomes a
> planned, policy‑checked, observed, verified, evidence‑backed multi‑specialist
> investigation — **without** replacing the deterministic router and **without** a
> hard‑coded workflow.
> Date: **2026‑09‑02**. Branch: `docs/lightweight-model-audit`.

---

## 1. Architecture

```
USER MISSION  ──▶  PLANNER  ──▶  typed AgentPlan  ──▶  POLICY (12 checks)  ──▶  BOUNDED EXECUTOR
                (LLM or rule)     (Pydantic;            ("RemoteSAM for VQA"      (state machine,
                                  malformed→reject)      → reject)                 ≤ 8 tool calls)
                                                                                       │
   AUDIT TRACE  ◀──  AgentInvestigationResult  ◀──  EVIDENCE‑FIRST SYNTHESIS  ◀──  per step:
                                                    (deterministic template)       run → OBSERVE →
                                                                                   VERIFY → REPLAN?
```

- The **deterministic router is not replaced.** The policy layer cross‑checks
  every planned tool against the registry; `run_analyze` (the G4/G13 deterministic
  path) is the fallback when the planner is unavailable or its plan is rejected.
- The **LLM is text‑only.** It plans *operations*; it never sees pixels and never
  emits observations. Specialists see pixels.
- **Bounded autonomy**: `MAX_STEPS = 8` specialist calls, no recursion; on the cap
  the agent stops and returns a partial‑but‑honest result.

### Components — `packages/agents/src/satquery_agents/agent/`

| File | Role |
|---|---|
| `schemas.py` | `TaskType` ontology (12 closed tasks) · `PlanStep` · `AgentPlan` · `AgentInvestigationResult` · state phases · observations |
| `registry.py` | `ToolSpec` + `TOOL_REGISTRY` — 12 typed tools; each carries task_type, input contract, output schema, specialist, image/modality/geo requirements, allowed follow‑ups, failure modes, caveats |
| `policy.py` | `validate_plan()` — 12 checks + "ends at FINALIZE"; `PolicyResult` |
| `planner.py` | `Planner` protocol · `RuleBasedPlanner` (default) · `LlmPlanner` (local Qwen2‑VL‑2B text‑only / HTTP provider) · `plan_with_fallback()` (never raises) |
| `prompts.py` | planner system prompt + 2 few‑shot plans + the JSON schema |
| `memory.py` | `AgentMemory` — bounded structured state (refs only; no images/embeddings in context) |
| `verifier.py` | `assess_step()` → `COHERENT / INCOHERENT / INSUFFICIENT / NOT_APPLICABLE` from the step's own `verify()` + resolution + sanity |

`apps/backend/app/services/agent_runner.py` — the executor: binds each `ToolName`
to an existing slice (`run_vqa`, `run_grounding`, `run_scene`, `run_change_slice`
+ fallback, `run_composed_semantic_change`, `run_joint_from_geotiffs`), runs the
state machine, does observe/replan, and synthesises the report from observations
only. `apps/backend/app/api/investigate.py` — `POST /investigate`.

## 2. Task ontology & tool registry

**Tasks:** `VALIDATE_INPUT · SCENE_UNDERSTANDING · VQA · GROUND_OBJECT ·
TEMPORAL_CHANGE · SEMANTIC_CHANGE · OPTICAL_SAR_ANALYSIS ·
EXTRACT_CHANGED_REGIONS · CROSS_CHECK_EVIDENCE · VERIFY · SUMMARIZE · FINALIZE`.

**Tools (12):** `validate_geospatial_input · run_vqa · run_grounding ·
run_scene_retrieval · run_temporal_change · run_semantic_temporal_baseline ·
run_optical_sar · extract_changed_regions · cross_check_evidence · verify_result ·
inspect_evidence · finalize_answer`. The planner may select **only** these.

## 3. State machine

`INITIAL → PLANNING → PLAN_VALIDATION → (EXECUTING → OBSERVING → VERIFYING →
[REPLANNING])* → FINALIZING / FAILED`. Persists: goal, inputs, plan, completed
steps, observations, evidence refs, verification statuses, failures, models used,
timings.

## 4. Policy layer — the 12 (+1) checks

tool exists · task in ontology · **tool matches task** (blocks "RemoteSAM for
VQA") · per‑step image count · modalities available · dependencies real & earlier ·
geo requirements (co‑registered pair) · capability match vs `model_registry.yaml` ·
no unsupported call · no dependency cycle · step count ≤ 8 · follow‑up task
allowed after the producing tool · **plan ends at FINALIZE**.

## 5. Observe / replan behaviours (each is a test — §7)

| Observation | Agent action |
|---|---|
| `changed_fraction` < 1 % | skip EXTRACT / GROUND / OPTICAL_SAR downstream; record why |
| grounding → no region | record "no region grounded (explicit)" — **no fabricated box** |
| 0 changed regions | skip the region grounding step |
| a specialist raises | record failure, continue, "N step(s) failed" — **no synthetic result** |
| optical+SAR → embedding | "representation‑level only; no textual fact inferred" |
| misregistered pair | VALIDATE fails → temporal never runs → deterministic fallback |
| evidence contradiction | verdict `INCOHERENT`; final `verification` reflects it |

## 6. Evaluation — internal frozen evaluation (NOT a benchmark)

`evaluation/agent/frozen_missions.json` — 30 missions: 5 VQA · 5 grounding · 5
temporal · 5 optical+SAR · 5 multi‑step · 5 adversarial. `run_agent_eval.py`.

### Plan phase (all 30, `RuleBasedPlanner`, CPU)

| metric | value |
|---|---|
| plan validity rate | **0.967** (29/30) |
| failed‑plan rate | 0.033 — adv‑5 (misregistered pair) correctly rejected by the policy layer |
| tool‑selection accuracy | **1.00** |
| task‑order correctness | **1.00** |
| avg specialist steps / plan | 2.4 |

### Exec phase (12 missions — 2/category — real frozen‑stack models, CPU)

| metric | value |
|---|---|
| execution success rate | **1.00** (12/12, 0 errors) |
| evidence preservation rate | **1.00** |
| verification preservation rate | **1.00** |
| factual‑consistency rate | **1.00** |
| ran‑forbidden‑tool rate | **0.00** |
| avg tool calls / mission | 1.42 (single‑step) — 4 on the flagship |
| avg end‑to‑end latency | 35 s (CPU, cold loads) |

### Baseline vs agent — multi‑step missions (`inv‑1`, `inv‑2`)

| | deterministic `/analyze` | agent |
|---|:--:|:--:|
| required specialists actually run (avg) | **1.0** | **2.5** |
| evidence present | — | 1.00 |

The single‑shot router routes to **one** specialist. The agent plans and runs the
**several** the mission needs (change → regions → grounding → optical+SAR →
cross‑check), preserving evidence + verification per step. **Measured, not
assumed.**

## 7. Agentic‑safety tests — `apps/backend/tests/test_g14_agent.py` (~30 tests)

The 18 required failure cases: malformed plan · nonexistent tool · unsupported
task/tool pair · missing second image · incompatible CRS · grounding failure ·
temporal runs+verified · CROMA input mismatch · insufficient evidence ·
contradictory geo (misregistered) · loop dependency · > 8 steps · no fabricated
coordinate without CRS · LLM planner failure → rule fallback · unsupported
semantic conclusion not asserted · planner invalid JSON → fallback · planner
timeout → fallback · planner crash → fallback. Plus: deterministic fallback on a
rejected plan · bounded loop never exceeds the cap · planner selects the right
tool for 6 mission types · flagship plan is multi‑step and valid. **176 fast pass
(0 regressions); the model‑running agent tests are `@pytest.mark.slow`.**

## 8. Flagship investigation (planner‑produced, not scripted)

Mission (one of several equivalent phrasings): *"Investigate this area. Identify
significant changes between the two observations, locate the affected structures,
and use SAR evidence to characterize the changes. Give me an evidence‑backed
summary."* — 4 images: T1, T2 optical + Sentinel‑2 + Sentinel‑1.

Plan the planner emitted:
`VALIDATE → TEMPORAL_CHANGE → EXTRACT_CHANGED_REGIONS →
{GROUND_OBJECT, OPTICAL_SAR_ANALYSIS} → CROSS_CHECK_EVIDENCE → VERIFY →
SUMMARIZE → FINALIZE` (5 specialist steps ≤ 8).

Result (real models, CPU, ~110 s, `docs/sih/evidence/demos/g14_flagship_investigation.json`):
all 9 steps completed COHERENT · 4 tool calls · 25.3 % of the scene changed
(0.41 ha) · 6 changed regions isolated (lon/lat boxes, EPSG:32650→4326) ·
structures grounded · 1/1 grounded region inside a changed region · joint
optical+SAR representation (dim 768, representation‑level, no invented fact) ·
`models_used = [ChangeFormer, RemoteSAM, CROMA]` · verification **SUPPORTED** ·
resolution **RESULT_OK**.

## 9. Limitations / known risks

- The local demo fixtures can't fully co‑register a LEVIR optical‑temporal pair
  with a Sentinel‑1 SAR tile — the flagship's optical+SAR leg is representation‑
  level and the cross‑check reports it cannot spatially corroborate SAR with the
  changed regions. Handled honestly.
- `RuleBasedPlanner` is the **default** (demo robustness). `LlmPlanner` works
  (local Qwen2‑VL‑2B text‑only, `scripts/research/planner_infer.py`) but a 2 B
  model is unreliable at strict JSON — opt‑in (`SATQUERY_PLANNER=llm`), always
  falls back.
- **No new large model.** 4 GB‑VRAM fit remains **UNVERIFIED** (no CUDA torch on
  the host). No confidence value. Frozen model stack unchanged. RemoteSAM licence
  caveat preserved. Semantic‑temporal baseline still labelled **experimental**.
- Bounded autonomy by design — the agent is not maximally autonomous.

## 10. Exact commands

```bash
# launch (API + UI, CPU-only)
cd apps/backend
../../.venvs/satquery/Scripts/python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
#   UI:   http://127.0.0.1:8000/     → toggle ASK / INVESTIGATE
#   docs: http://127.0.0.1:8000/docs → POST /investigate

# agent evaluation
.venvs/satquery/Scripts/python.exe evaluation/agent/run_agent_eval.py            # plan phase, all 30
.venvs/satquery/Scripts/python.exe evaluation/agent/run_agent_eval.py --exec 2   # + exec 2/category
.venvs/satquery/Scripts/python.exe evaluation/agent/run_agent_eval.py --only inv-1   # flagship only

# flagship demo (curl)
curl -s -F "query=Investigate this area: identify significant changes, locate the affected structures, use SAR to characterise them, give a verified summary." \
     -F "files=@data/demo/investigation/t1_optical.tif" \
     -F "files=@data/demo/investigation/t2_optical.tif" \
     -F "files=@data/demo/investigation/s2_dfc_optical.tif" \
     -F "files=@data/demo/investigation/s1_dfc_sar.tif" \
     http://127.0.0.1:8000/investigate | python -m json.tool

# tests
.venvs/satquery/Scripts/python.exe -m pytest apps/backend/tests/test_g14_agent.py -q -m "not slow"
.venvs/satquery/Scripts/python.exe -m pytest apps/backend/tests/test_g14_agent.py -q -m slow
```

## 11. Definition of Done

| Item | Status |
|---|:--:|
| LLM planner exists | ✅ `LlmPlanner` (local Qwen2‑VL‑2B text‑only + HTTP provider) |
| planner output is schema‑validated | ✅ Pydantic `AgentPlan`; malformed → rejected |
| typed tool registry exists | ✅ 12 tools, full metadata (`registry.py`) |
| deterministic safety/policy layer exists | ✅ 12 (+1) checks (`policy.py`) |
| bounded execution loop exists | ✅ state machine, ≤ 8 specialist calls, no recursion |
| agent observes specialist outputs | ✅ `assess_step` + `AgentMemory` per step |
| conditionally chooses next actions | ✅ tiny change → skip grounding; 0 regions → skip; deps‑skipped → skip |
| stops when evidence is sufficient / cap reached | ✅ FINALIZE / `hit_step_cap` partial result |
| handles failures honestly | ✅ recorded, never fabricated; 0 forbidden‑tool runs in eval |
| cannot invent tools / bypass validation | ✅ closed `ToolName`; policy layer rejects |
| evidence / verification / provenance preserved | ✅ preservation rate 1.00 in exec eval |
| multi‑step investigations work | ✅ flagship 9 steps COHERENT; `inv‑1..5` |
| `/investigate` endpoint works | ✅ + UI ASK/INVESTIGATE toggle + plan panel |
| deterministic fallback works | ✅ planner fail / plan rejected → `run_analyze` |
| 30 frozen internal missions exist | ✅ `evaluation/agent/frozen_missions.json` |
| baseline vs agent comparison exists | ✅ 2.5 vs 1.0 specialists on multi‑step |
| all existing tests remain green | ✅ 176 fast pass, 0 regressions |
| agent tests are green | ✅ ~30, incl. the 18 failure cases |
| flagship demo works with REAL models | ✅ ChangeFormer + RemoteSAM + CROMA, verification SUPPORTED |
| no fake agentic behavior | ✅ explicit plan, typed tools, deps, observe/replan, bounded, auditable |
| no new unnecessary large models | ✅ `LlmPlanner` reuses the frozen Qwen2‑VL‑2B; rule planner is the default |
| 4 GB VRAM honestly labelled unverified | ✅ preserved everywhere |
| RemoteSAM licence caveat remains | ✅ in the tool registry + every grounding output |
| no fabricated confidence values | ✅ none produced |
| learned temporal VLM stays experimental | ✅ `run_semantic_temporal_baseline` caveat preserved |

## 12. The success criterion

Typing *"Investigate this area. Tell me what changed, where it changed, identify
the affected structures, compare optical and SAR evidence, and give me a verified
summary."* into INVESTIGATE now: **understands the mission → generates a plan →
validates the plan → runs ChangeFormer, region extraction, RemoteSAM, CROMA →
inspects each result → cross‑checks and verifies → emits a geo‑grounded,
evidence‑backed report** — with **no hard‑coded workflow for that sentence**
(the eval's `inv‑1..5` use five different phrasings and each produces the
appropriate plan).
