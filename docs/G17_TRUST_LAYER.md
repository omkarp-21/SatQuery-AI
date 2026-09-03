# G17 — Trust / Confidence Layer

> **This is not a calibrated probability.** It is a deterministic function of
> observable signals from the executed investigation, producing one of four
> **categories**. Calibrated numeric confidence (EXP-C1/C2) remains future work.
> Nothing here is labelled a probability, and `confidence.score` is an internal
> tally, never surfaced as "% confident".

Implementation: `apps/backend/app/services/trust.py::assess_confidence`, called at
the end of `agent_runner._synthesize`. Result on
`AgentInvestigationResult.confidence`:

```json
{
  "category": "HIGH | MEDIUM | LOW | INSUFFICIENT_EVIDENCE",
  "score": 6.5,
  "reasons": ["All 4 planned specialist step(s) completed.", "Verification: SUPPORTED ...", ...],
  "signals": {"family": "multi_step", "verification": "SUPPORTED", "cross_check_inside": "1/1", ...},
  "hard_rule": null,
  "note": "evidence-derived category, deterministic rules. NOT a calibrated probability."
}
```

## Hard rules (force the category, regardless of score)

| condition | category |
|-----------|----------|
| verification == `CONTRADICTED` | `INSUFFICIENT_EVIDENCE` |
| the **primary** specialist for the mission family failed and no equivalent completed | `INSUFFICIENT_EVIDENCE` |
| specialist steps ran but **no evidence** was produced | `INSUFFICIENT_EVIDENCE` |

Primary specialist per family: `single_step` → `run_vqa` / `run_grounding` /
`run_scene_retrieval`; `temporal` → `run_temporal_change` /
`run_semantic_temporal_baseline`; `optical_sar` → `run_optical_sar`;
`multi_step` → `run_temporal_change`.

## Additive signals (summed, then mapped)

| signal | Δ score |
|--------|:------:|
| all planned specialist steps completed (no failures) | **+2** |
| each specialist step that failed | **−1** (floor −2) |
| ≥ 1 evidence item attached | **+1** |
| verification `SUPPORTED` | **+2** |
| verification did not reach `SUPPORTED` (soft) | 0 |
| a step verdict is `INCOHERENT` (claim withheld) | **−3** |
| spatially grounded output present (EPSG:4326 GeoJSON) | **+1** |
| cross-check: **all** grounded regions inside changed regions | **+2** |
| cross-check: **some** inside | **+1** |
| cross-check: **none** inside | **−1** |
| comparison required **and** optical+SAR actually ran | **+1** |
| a required modality was missing (e.g. no SAR) | **−1** |
| intent `ambiguity` == `high` / `low` | **−2** / **−1** |
| planner fell back to the deterministic intent/plan | **−1** |
| known-limitation signal present (RemoteSAM licence · experimental semantic-change · SAR representation-only) | **−0.5** each, floor **−1** |

## Mapping (after the hard rules)

**1. score → band:**

| total score | band |
|:-----------:|----------|
| ≥ 5.0 | HIGH |
| 2.0 – 4.99 | MEDIUM |
| < 2.0 | LOW |

**2. conservative caps** (lower the band; added G18, validated on 30 frozen cases
in `evaluation/agent/trust_cases.json` / `test_g18_trust_cases.py`):

| condition | cap |
|-----------|-----|
| verification ≠ `SUPPORTED` | LOW |
| any step verdict `INCOHERENT` (claim withheld) | LOW |
| any specialist step **failed** | MEDIUM |
| < 2 specialists completed **and** no completed `cross_check_evidence` | MEDIUM |
| intent `ambiguity` == `high` / `low` | LOW / MEDIUM |

So **HIGH is only ever reached by a multi-specialist investigation** whose
verification is SUPPORTED, with no failed or withheld step and an unambiguous
mission. A single-step answer or a bare 2-image temporal result caps at **MEDIUM**
by design — the category is deliberately conservative.

## Claim-level evidence (Part 7)

Every claim in `key_findings` is built **only** from an observed specialist
output — the synthesis never invents. Concretely:

| claim template | evidence it is built from | if the evidence is absent |
|----------------|---------------------------|---------------------------|
| "~X % of the scene changed (~Y ha)" | ChangeFormer `stats.changed_fraction` / `changed_area_ha` | the claim is not made; "No significant change" is stated instead when `changed_fraction < 0.01` |
| "N changed region(s) were isolated" | `extract_changed_regions` connected components | not made |
| "Grounding located a region at pixel box …" | RemoteSAM box **with `validation_status == PASS`** | "Grounding: no matching region could be localised (returned explicitly, not fabricated)." |
| "Cross-check: k/N grounded region(s) fall inside a changed region" | `cross_check_evidence.matches[*].centroid_in_changed_region` | not made |
| "Optical+SAR: a joint representation (dim D) was produced" | CROMA `representation.dim` — **representation-level only**; no textual fact is inferred from the embedding | "Optical+SAR analysis was not performed — no distinct SAR input was supplied." |
| a step whose verdict is `INCOHERENT` | — | "`<tool>`: result withheld — it failed verification (disputed, not asserted)." |

A claim like *"SAR confirms construction"* is **never** emitted — the optical+SAR
specialist returns an embedding, not a construction judgement, so the synthesis
says *"Optical+SAR result is representation-level only …"* and the confidence
layer applies the known-limitation penalty.

## Deterministic-fallback path

When the agent plan cannot run and the deterministic `/analyze` path answers,
`confidence.category` is `MEDIUM` (answer + verification `SUPPORTED`), `LOW`
(answer, weaker verification) or `INSUFFICIENT_EVIDENCE` (no answer), with
`score: null` and a reason naming the fallback.

## What this is NOT

- Not a probability, not calibrated, not comparable across missions as a number.
- Not a model output — it is computed by rules from the specialists' structured
  results and the verification aggregate.
- The `score` is internal; the UI shows only the **category** and the **reasons**.
