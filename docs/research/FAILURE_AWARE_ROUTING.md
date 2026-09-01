# Failure-Aware Routing (design)

> Status: **G8 — post-execution qualifier + single-step fallback IMPLEMENTED**
> (`apps/backend/app/services/failure_aware.py`, wired into `/analyze`;
> `run_change_fallback` in `temporal_slice.py`; `apps/backend/tests/test_failure_aware.py`,
> 10 tests). The deterministic router (`packages/core/src/satquery_core/routing/`)
> is unchanged — this is an `/analyze`-layer aggregation, not a routing-rule
> change. No LLM. No loop. No confidence number.
> Companion: `ROUTING_SPEC.md`, `EXP-005.md` (verifier), `CONFIDENCE_PLAN.md`,
> `docs/API_CONTRACT.md` (the `resolution` field).

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

## Implementation status

| Step | State |
|------|-------|
| 1. post-execution qualifier in `/analyze` aggregation (pure fn of `verify()` + `verify_semantic()` + sub `ok`) | **DONE (G8)** — `derive_resolution()`, additive `resolution` field on `AnalyzeResult`; 6 qualifiers |
| 2. single-step fallback in `analyze.py` dispatch | **DONE (G8)** — `TEMPORAL` path: ChangeFormer fail → one call to `run_change_fallback` (image-difference + threshold, same geo-gate) → `SPECIALIST_DEGRADED` |
| 3. `LOW_MARGIN` advisory on composed-baseline regions | **TODO** — small, additive; do with the C work |
| 4. tests | **DONE (G8)** — 10 (`test_failure_aware.py`): one per qualifier, determinism, "not a confidence", fallback rejects misregistered pair, fallback produces a mask + verification |
| 5. `docs/API_CONTRACT.md` — qualifier + `disputed` shape | **DONE (G8)** |
| `independent_model` / `optical_sar` disagreement qualifiers | **BLOCKED** — need EXP-002 + EXP-C2 |

### `ok` semantics (deliberately unchanged in G8)

`/analyze`'s top-level `ok` still mirrors the sub-service `ok`. A
`RESULT_STRUCTURAL_FAIL` / `SPECIALIST_FAILED` sets `resolution.answer_surfaced =
false` **without** flipping `ok` — callers gate on `resolution.answer_surfaced`.
Flipping `ok` on a failed verifier is a follow-up (needs a contract note + a
frontend that reads `resolution`).
