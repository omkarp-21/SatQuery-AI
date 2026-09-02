# EXP-006 — Agentic geospatial planner (G14)

> Registry: `docs/19_EXPERIMENT_REGISTRY.md#EXP-006`. Hypothesis **H2**: a
> constrained LLM/rule planner + a deterministic policy/execution guard turns
> natural‑language missions into correct multi‑step specialist plans **without**
> replacing the deterministic router, and adds functional value over the
> single‑shot `/analyze` path on multi‑step missions.
> Status: **RUN (G14, 2026‑09‑02).** Internal frozen evaluation — not a benchmark.

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

**KEEP** — the agent produces valid multi‑step plans (0.967 / 1.00 / 1.00 on plan
metrics), never runs a forbidden tool, preserves evidence + verification +
provenance, and on multi‑step missions selects and runs multiple required
specialists where the deterministic baseline routes to one. This is SatQuery's
differentiating feature. Next: scale the mission set, wire the local LLM planner
into the eval's second arm, and add a labelled ground‑truth plan per mission.
