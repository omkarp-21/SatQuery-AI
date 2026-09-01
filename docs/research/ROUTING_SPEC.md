# Constrained Router Specification (v0)

> `packages/core/src/satquery_core/routing/`. **Deterministic. No LLM.** This is
> the routing *specification* + a rule implementation + tests — not an autonomous
> agent. An LLM planner comes later (`docs/06_AGENT_ARCHITECTURE.md`, EXP-006) and
> will only *fill in* the intent keyword, never override these rules.

## Inputs — `RoutingRequest`

| Field | Type | Meaning |
|-------|------|---------|
| `query_intent` | str | normalized keyword (spaces/underscores → `-`, lowercased) |
| `image_count` | int ≥ 0 | number of input images |
| `modalities` | list[str] | e.g. `["optical"]`, `["optical","sar"]` |
| `metadata_valid` | bool | did GeoTIFF validation + compatibility pass? |
| `available_capabilities` | list[str] \| None | override; else read from `model_registry.yaml` |

Intent buckets: `CHANGE_INTENTS` (change, change-detection, what-changed,
bitemporal), `SCENE_INTENTS` (scene, retrieval, classify, zero-shot, tag, …),
`VQA_INTENTS` (vqa, question, grounding, refer, count, describe-object).

## Output — `RoutingDecision`

`specialists: list[str]` · `code` · `reason` · `required_preprocessing: list[str]`
· `execution_order: list[str]`

## Rules (evaluated in order; first match wins)

| # | Condition | Decision `code` | Specialists |
|---|-----------|-----------------|-------------|
| 1 | `not metadata_valid` | `VALIDATION_FAILED` | `[]` |
| 2 | `image_count == 2` **and** intent ∈ CHANGE_INTENTS **and** `change-detection` ∈ caps | `TEMPORAL` | `["changeformer"]` |
| 3 | `image_count == 2` **and** modalities has optical **and** SAR (non-change intent) | `MULTIMODAL_REPR` | `["croma"]` (else `["dofa"]`) |
| 4 | `image_count == 1` **and** intent ∈ SCENE_INTENTS **and** {zero-shot-classification, retrieval} ∩ caps | `SINGLE_IMAGE_SCENE` | `["remoteclip"]` |
| 5 | `image_count == 1` **and** intent ∈ VQA_INTENTS | `NO_VQA_SPECIALIST` | `[]` |
| 6 | otherwise | `NO_MATCH` | `[]` |

Notes:
- **Rule 2 beats rule 3:** a change intent with optical+SAR still routes to
  ChangeFormer; the SAR then serves as *supporting evidence*, not the primary route.
- **Rule 5 is deliberately empty** — single-image VQA/grounding is mandatory and
  has **no integrated specialist** yet (EXP-002 pending). The router says so with a
  code the caller can explain; it never routes RemoteCLIP as a VQA model.
- **Rule 3 is representation-level** — `MULTIMODAL_REPR` produces joint embeddings,
  not an answer. Its `reason` says so.

## `required_preprocessing` vocabulary

`geotiff-validate` · `pair-co-registration-assert` · `image-open-check` ·
`s1-db-scale` · `s2-12band-select` · `channel-normalize` · `resample-120`

## Not covered yet (documented gaps)

- Bi-temporal **semantic** change → no route (EXP-003; would be a composed
  pipeline: ChangeFormer mask → region crops → single-image VLM).
- Optical+SAR **at the same timepoint vs T1/T2** — `image_count == 2` is
  ambiguous; a future `timepoints` field disambiguates. For now intent decides.
- Multi-step plans / DAGs — the LLM-planned `ExecutionPlan`
  (`agent-orchestration` skill) is future work.

## Tests

`packages/core/tests/test_routing.py` — 8 cases, one per rule + serialization.
