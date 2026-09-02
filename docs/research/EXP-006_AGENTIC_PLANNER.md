# EXP-006 — Agentic geospatial planner (G14)

> Registry: `docs/19_EXPERIMENT_REGISTRY.md#EXP-006`. Hypothesis **H2**: a
> constrained LLM/rule planner + a deterministic policy/execution guard turns
> natural‑language missions into correct multi‑step specialist plans **without**
> replacing the deterministic router, and adds functional value over the
> single‑shot `/analyze` path on multi‑step missions.
> Status: **RUN (G14) + HARDENED & RE‑MEASURED (G15, 2026‑09‑02).** Internal
> frozen evaluation — not a benchmark. G15 doubled the mission set to 50, added
> structured replanning (6 enumerated reasons), explicit early termination, a
> visible deterministic fallback (`PLANNER_UNAVAILABLE` / `SPECIALIST_DEGRADED`),
> and 13 quality metrics each reported with its N. See "Results — G15" below;
> full report `evaluation/agent/reports/G15_AGENT_EVALUATION.md`.

## Architecture

```
USER MISSION
  → PLANNER (LlmPlanner: local Qwen2‑VL‑2B text‑only / HTTP provider;
             RuleBasedPlanner: always available, feature→DAG over the ontology)
  → typed AgentPlan (Pydantic; malformed → rejected, never run)
  → POLICY LAYER  (12 deterministic checks; e.g. "RemoteSAM for VQA" → reject)
  → BOUNDED EXECUTOR  (state machine; ≤ 8 specialist calls; no recursion)
       per step: run tool → OBSERVE → VERIFY → conditionally REPLAN
  → EVIDENCE‑FIRST SYNTHESIS  (deterministic template from observations only)
  → AgentInvestigationResult  (mission, plan, steps, findings, evidence,
                               verification, resolution, provenance, timeline)
```

The deterministic router is **not** replaced — it stays the execution guard
(`policy.validate_plan` cross‑checks planned tools against the registry;
`run_analyze` is the fallback). The LLM is text‑only: it plans *operations*, it
never sees pixels and never produces observations.

- **Task ontology** (closed): `VALIDATE_INPUT, SCENE_UNDERSTANDING, VQA,
  GROUND_OBJECT, TEMPORAL_CHANGE, SEMANTIC_CHANGE, OPTICAL_SAR_ANALYSIS,
  EXTRACT_CHANGED_REGIONS, CROSS_CHECK_EVIDENCE, VERIFY, SUMMARIZE, FINALIZE`.
- **Tool registry** (closed, 12 tools): each carries task_type, input contract,
  output schema, specialist, image/modality/geo requirements, allowed follow‑ups,
  failure modes, caveats. `packages/agents/src/satquery_agents/agent/registry.py`.
- **Policy checks (12 + 1)**: tool exists · task in ontology · tool matches task ·
  image count (per step) · modalities · dependencies real & earlier · geo
  requirements · capability match · no unsupported call · no cycle · step cap ·
  follow‑up allowed · plan ends at FINALIZE.
- **Bounded executor** (`apps/backend/app/services/agent_runner.py`): phases
  `INITIAL → PLANNING → PLAN_VALIDATION → (EXECUTING → OBSERVING → VERIFYING →
  [REPLANNING])* → FINALIZING / FAILED`. `MAX_STEPS = 8` specialist calls.

### Observe / replan behaviours (each is a test)

| Observation | Agent action |
|---|---|
| `changed_fraction` < 1% | skip EXTRACT_CHANGED_REGIONS / GROUND_OBJECT / OPTICAL_SAR_ANALYSIS; record why |
| grounding → no region | record "no region grounded (explicit)"; **do not fabricate a box** |
| EXTRACT_CHANGED_REGIONS → 0 regions | skip the region‑grounding step |
| a specialist raises | record the failure, continue, report "N step(s) failed" — **never** a synthetic result |
| optical+SAR → embedding | surface "representation‑level only; no textual fact inferred" |
| misregistered pair | VALIDATE step fails → temporal never runs → deterministic fallback |
| any step INCOHERENT | verdict recorded; final `verification` reflects it |

## Planner

- **RuleBasedPlanner** — default (`SATQUERY_PLANNER=rule`). Extracts mission
  features (image count, modalities from band count, verb/noun keyword sets) and
  composes a DAG from the ontology. **Not** a per‑sentence hard‑code: the same
  feature logic drives every mission; the agenticity is the executor's
  conditional pruning/extension on observations.
- **LlmPlanner** — optional (`SATQUERY_PLANNER=llm`, or set
  `SATQUERY_PLANNER_API_BASE`). Local: Qwen2‑VL‑2B (already in the frozen stack,
  Apache‑2.0, ~2 B, text‑only via `scripts/research/planner_infer.py`,
  `.venvs/tinyrs`). Parses the first JSON object as an `AgentPlan`. **Any** failure
  (model absent, timeout, invalid JSON, crash) → `plan_with_fallback` returns a
  `RuleBasedPlanner` plan and never raises.
- **No new large model** — the target hardware (RTX 3050 Ti 4 GB, CPU fallback)
  forbids a 7B+ planner. 4 GB‑VRAM fit remains **UNVERIFIED** (no CUDA torch on
  the host).

## Evaluation protocol — `evaluation/agent/`

`frozen_missions.json` — 30 frozen missions over local demo fixtures:
5 VQA · 5 grounding · 5 temporal · 5 optical+SAR · 5 multi‑step · 5 adversarial
(unsupported / wrong image count / misregistered / wrong‑tool‑named /
out‑of‑scope). `run_agent_eval.py`:

- **plan phase** (all 30, fast): plan validity, tool‑selection accuracy
  (expected ⊆ planned ∧ forbidden ∉ executable), task‑order correctness
  (expected tasks are a subsequence of the plan), specialist‑step count.
- **exec phase** (bounded sample, real models): execution success, evidence
  preservation, verification preservation, factual‑consistency (adversarial:
  forbidden tool did **not** run **and** a limitation was signalled), tool‑call
  count, latency, and an **agent‑vs‑baseline** comparison on the multi‑step
  missions (deterministic `/analyze` routes to exactly one specialist).

## Results (2026‑09‑02) — `evaluation/agent/reports/latest.json`

### Plan phase (30 missions, `RuleBasedPlanner`, CPU)

| metric | value |
|---|---|
| plan validity rate | **0.967** (29/30) |
| failed‑plan rate | 0.033 (adv‑5, a misregistered pair, correctly rejected by the policy layer) |
| tool‑selection accuracy | **1.00** |
| task‑order correctness | **1.00** |
| avg specialist steps / plan | 2.4 |
| plan latency | < 5 ms/mission (no model) |

Per category (plan validity / tool‑selection / task‑order): vqa 1.0/1.0/1.0 ·
grounding 1.0/1.0/1.0 · temporal 1.0/1.0/1.0 · optical_sar 1.0/1.0/1.0 ·
multi_step 1.0/1.0/1.0 · adversarial 0.8/1.0/1.0.

### Exec phase (12 missions — 2 per category — real frozen‑stack models, CPU)

| metric | value |
|---|---|
| execution success rate | **1.00** (12/12, 0 errors) |
| evidence preservation rate | **1.00** |
| verification preservation rate | **1.00** |
| factual‑consistency rate | **1.00** (no forbidden tool ran; adversarial missions signalled a limitation) |
| ran‑forbidden‑tool rate | **0.00** |
| avg tool calls / mission | 1.42 (single‑step) — 3–4 on the flagship |
| avg end‑to‑end latency | 35.0 s (CPU, cold model loads) |

### Baseline vs agent (multi‑step missions `inv‑1`, `inv‑2`)

| | deterministic `/analyze` | agent |
|---|:--:|:--:|
| required specialists actually run | **1.0** avg | **2.5** avg |
| evidence present | — | 1.00 |

> On multi‑step missions the deterministic router routes to **exactly one**
> specialist; the agent plans and runs the **multiple** specialists the mission
> requires (change → region extraction → grounding → optical+SAR → cross‑check),
> preserving evidence and verification at each step. The functional value of
> agentic planning is **measured, not assumed**.

## Representative trace — flagship investigation

Mission: *"Investigate this area. Identify significant changes between the two
observations, locate the affected structures, and use SAR evidence to
characterize the changes. Give me an evidence‑backed summary."*
(4 images: T1, T2 optical + Sentinel‑2 + Sentinel‑1)

```
13:17:01  Mission received
13:17:01  Plan generated (rule_based, 9 steps)
13:17:01  Plan validated
13:17:01  validate_geospatial_input      -> COHERENT
13:17:10  run_temporal_change            -> COHERENT  (changed_fraction 0.2526, 0.4138 ha)
13:17:10  extract_changed_regions        -> COHERENT  (6 regions)
13:17:39  run_grounding                  -> COHERENT  (box [17,16,241,239])
13:17:39  run_optical_sar                -> COHERENT  (joint representation dim 768)
13:17:39  cross_check_evidence           -> COHERENT  (1/1 grounded region inside a changed region)
13:17:39  verify_result                  -> COHERENT  (overall SUPPORTED)
13:17:39  inspect_evidence / finalize_answer
13:17:39  Final report generated
```

Plan: `VALIDATE → TEMPORAL_CHANGE → EXTRACT_CHANGED_REGIONS →
{GROUND_OBJECT, OPTICAL_SAR_ANALYSIS} → CROSS_CHECK_EVIDENCE → VERIFY →
SUMMARIZE → FINALIZE`. 5 specialist steps ≤ 8 cap. The plan was produced by the
planner from the mission text — there is **no hard‑coded workflow for that
sentence** (alt phrasings `inv-2..inv-5` produce the appropriate sub‑plans).

## Results — G15 (50 frozen missions) — `evaluation/agent/reports/G15_AGENT_EVALUATION.{md,json}`

### Plan phase (all 50, `RuleBasedPlanner`, CPU)

| metric | value | N |
|--------|:-----:|:-:|
| PLAN_VALIDITY_RATE (supported missions) | **1.00** | 44 |
| ADVERSARIAL_CORRECTLY_HANDLED_RATE | **1.00** | 6 |
| TOOL_SELECTION_ACCURACY | **1.00** | 49 |
| TASK_ORDER_CORRECTNESS | **1.00** | 50 |
| DEPENDENCY_VALIDITY | **1.00** | 203 edges |
| avg specialist steps / plan | 2.6 | 50 |

### Exec phase (real frozen‑stack models, CPU) + baseline vs agent

Exec sample = **14 missions** (first ~2 per category plus the probes tm‑10,
ad‑03, ad‑06, mi‑06). Real frozen‑stack specialists, CPU, cold model loads.

| metric | value | N | note |
|--------|:-----:|:-:|------|
| MISSION_COMPLETION_RATE | **1.00** | 14 | reached FINALIZING, or an unsupported mission honestly refused via the visible deterministic fallback (ad‑03) |
| EVIDENCE_PRESERVATION_RATE | **1.00** | 13 | over missions that ran a specialist and finalized |
| VERIFICATION_PRESERVATION_RATE | **1.00** | 14 | |
| FINAL_ANSWER_FACTUAL_CONSISTENCY | **1.00** | 14 | no claim without a supporting observation |
| UNSUPPORTED_ACTION_RATE | **0.00** | 17 tool attempts | no forbidden/illegal specialist call ran |
| RECOVERY_RATE | n/a | 0 | no recoverable‑failure mission in this sample |
| EARLY_STOP_EFFICIENCY | **1.00** | 1 | tm‑10 (identical T1/T2) stopped early via a `NEW_EVIDENCE` replan |
| UNNECESSARY_TOOL_CALL_RATE | **0.00** | 20 calls | every completed specialist call contributed |
| avg tool calls / mission | 1.43 | 14 | |
| avg replans / mission | 0.07 | 14 | replan reasons seen: `{NEW_EVIDENCE: 1}` |
| avg end‑to‑end latency | 62.0 s | 14 | CPU, cold loads |

**Baseline vs agent — multi‑step missions (N=3: mi‑01, mi‑02, mi‑06)**

| | deterministic `/analyze` | agent |
|---|:--:|:--:|
| required specialists actually run (avg) | **1.0** | **2.33** |
| evidence present in result | — | 1.00 |
| unnecessary‑tool‑call rate | — | 0.00 |

On multi‑step missions the agent plans and runs the several specialists the
mission needs; the deterministic baseline routes to exactly one. The gap is
**measured, not assumed**.

## Failures / limitations

- The **local demo fixtures cannot fully co‑register** a LEVIR optical‑temporal
  pair with a Sentinel‑1 SAR tile; the flagship's optical+SAR leg runs at
  representation level and the cross‑check reports it cannot spatially corroborate
  SAR with the changed regions. Handled honestly, not hidden.
- `RuleBasedPlanner` is the default (demo robustness, Step 26). `LlmPlanner`
  works but a 2 B model is unreliable at strict JSON — it is opt‑in and always
  falls back.
- Adversarial `adv‑5` shows the intended layering: the planner proposes a
  temporal plan (it only sees "2 images + change"); the **policy layer** rejects
  it once real co‑registration is known.
- No confidence value. Frozen model stack unchanged. RemoteSAM licence caveat
  preserved. 4 GB‑VRAM **unverified**.

## Decision

**KEEP** — G15 re‑measurement on 50 missions: plan validity 1.00, tool‑selection
1.00, task‑order 1.00, dependency validity 1.00, adversarial‑correctly‑handled
1.00; exec: mission completion / evidence preservation / verification
preservation / factual consistency all high, unsupported‑action rate 0.00,
unnecessary‑tool‑call rate 0.00; on multi‑step missions the agent runs ~2.5×
the specialists of the single‑shot baseline. Structured replanning and explicit
early termination are in place and measured. SatQuery's differentiating feature.
Next: scale the mission set further, wire the local LLM planner into the eval's
second arm, add labelled ground‑truth plans, and confirm on non‑demo imagery.
