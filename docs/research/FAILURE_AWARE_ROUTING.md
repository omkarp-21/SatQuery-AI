# Failure-Aware Routing (design)

> Status: **design only (G7).** The deterministic router
> (`packages/core/src/satquery_core/routing/`) is unchanged. This doc specifies
> how routing + `/analyze` should **react to failure signals** — before, during,
> and after specialist execution — so that a weak or unsupported answer is
> *labelled or withheld*, never silently returned. No LLM. No confidence number.
> Companion: `ROUTING_SPEC.md`, `EXP-005.md` (verifier), `CONFIDENCE_PLAN.md`.

## Principle

`Plan → Validate → Execute → Verify → Explain → Audit` already fails loudly at
**Validate** (bad CRS, misregistered pair, missing specialist → typed error,
no inference). Failure-aware routing extends that discipline to the phases
**after** a specialist runs: a structurally- or semantically-incoherent result is
a routing outcome, not a 200 with a bad answer.

## Signal inventory (all already computed, none new)

| Signal | Source | Where it exists today |
|--------|--------|-----------------------|
| metadata invalid | `validate_geotiff` | `/analyze` pre-check → `VALIDATION_FAILED` |
| pair not co-registered | `check_pair_compatibility` | `/analyze` pre-check → `VALIDATION_FAILED` |
| no specialist for the task | registry lookup | `NO_VQA_SPECIALIST` / `NO_MATCH` |
| adapter execution error / timeout | `SpecialistAdapter.run()` | `AdapterResult.status != "ok"` |
| **structural verification** | `verify()` | `SUPPORTED` / `CONTRADICTED` / `INSUFFICIENT_EVIDENCE` |
| **semantic coherence** | `verify_semantic()` (EXP-005b) | `COHERENT` / `INCOHERENT` / `NOT_ENOUGH_EVIDENCE` |
| model score meaning | adapter `score_meaning` | present on every scored result (uncalibrated) |
| region-tag margin | RemoteCLIP ranking gap | composed baseline regions |
| independent-model / optical-SAR disagreement | — | **not available** (EXP-002 / EXP-C2 blocked) |

## Routing states (extends the current codes)

Current terminal codes: `SINGLE_IMAGE_SCENE`, `TEMPORAL`, `MULTIMODAL_REPR`,
`NO_VQA_SPECIALIST`, `VALIDATION_FAILED`, `NO_MATCH`. Add **post-execution
qualifiers** (attached to the response, not new routes):

| Qualifier | Trigger | `/analyze` behaviour |
|-----------|---------|----------------------|
| `RESULT_OK` | `verify()` == SUPPORTED **and** `verify_semantic()` ∈ {COHERENT, NOT_ENOUGH} | return result as-is |
| `RESULT_STRUCTURAL_FAIL` | `verify()` == CONTRADICTED | `ok: false`; return the failed checks; **no answer text surfaced** |
| `RESULT_SEMANTIC_INCOHERENT` | `verify_semantic()` == INCOHERENT | `ok: true` but `answer` carried under `disputed`; the failed semantic checks are the headline evidence |
| `RESULT_UNVERIFIED` | both verifiers return INSUFFICIENT / NOT_ENOUGH | return result, flag `verification: "insufficient"` — caller must not treat it as checked |
| `SPECIALIST_DEGRADED` | `AdapterResult.status` == "degraded" or a fallback adapter was used | return with `provenance.degraded = true` and the reason |
| `LOW_MARGIN` *(advisory)* | region-tag rank-1 margin < 0.05 (composed baseline) | tag kept, marked `low_margin: true` — never dropped silently |

## Fallback ladder (deterministic, registry-driven)

Each registry entry already has a `fallback:` field. On adapter failure the router
walks it **once**, records `provenance.fallback_from`, and re-verifies:

```
changeformer  -> image-difference + threshold (trivial)   [fallback declared]
remoteclip    -> none (auxiliary, not on a mandatory path)
croma <-> dofa (optical-SAR bake-off pair)
<VQA winner>  -> <the other passing EXP-002 candidate>, else NO_VQA_SPECIALIST
```

A fallback result is never presented as equivalent to the primary — it carries
`provenance.fallback_from` and its own (usually weaker) verification.

## What this is NOT

- Not a confidence score. `verify_semantic()` status is a **band**, not P(correct).
- Not an LLM re-router. The qualifier is a pure function of the signals above.
- Not silent suppression: a withheld answer always returns **why** (the failed
  checks), so the caller / UI can show the dispute.

## Implementation order (after the model freeze)

1. Add the post-execution qualifier to `/analyze`'s aggregation (pure function of
   `verify()` + `verify_semantic()` + `AdapterResult.status`). ~30 lines, additive.
2. Wire the single-step fallback walk in `analyze.py` dispatch.
3. Add `LOW_MARGIN` advisory to the composed baseline regions.
4. Tests: one per qualifier (contract), one fallback-path test per adapter with a
   declared fallback.
5. `docs/API_CONTRACT.md` — document the qualifier field + the `disputed` shape.

Blocked pieces (`independent-model` / `optical-SAR` disagreement qualifiers) wait
for EXP-002 + EXP-C2.
