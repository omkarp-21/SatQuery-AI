# SatQuery — "What We Learned" (Research Honesty Slide)

> A single slide that turns our negative and inconclusive findings into a
> credibility argument. Every line is true and traceable
> (`docs/G19_SIH_SOURCE_OF_TRUTH.md`).

## Slide title

**What we learned — and what we changed because of it**

## Slide body (5 points)

1. **We built a local LLM planner, measured it, and rejected it.**
   Qwen2-VL-2B (text-only, CPU) scored semantic plan-validity 0.25 vs the
   deterministic planner's 0.886 over 100 missions, and echoed its prompt
   example. → The **deterministic planner is the production default**; an
   LLM-*intent*-only hybrid is optional.

2. **We withdrew our own SAR-benefit claim after a larger validation.**
   The first split showed +0.067 macro-F1 for optical+SAR (already not
   significant). On a larger independent split (n = 386) it **reversed** to
   −0.026. → Claim withdrawn; CROMA kept only because it was the stronger
   representation in the bake-off.

3. **We kept adaptation optional, not default.**
   LoRA on frozen CROMA lifts the probe in the *same direction* on both splits,
   but the larger run was 3 CPU epochs with no significance test. → `--lora-weights`
   is an opt-in, provenance-tracked path; the **frozen encoder is the default**.

4. **Confidence is a category, not a fake probability.**
   We deliberately did **not** ship a number. `trust.py` applies documented
   deterministic rules to the evidence and verification, returns
   HIGH/MEDIUM/LOW/INSUFFICIENT with an explicit "why", and never exposes an
   internal score. Validated on 30 cases across 7 scenario families.

5. **Failures are visible by design.**
   22 pathological conditions — corrupt rasters, CRS mismatch, missing modality,
   unsupported query, specialist failure, planner failure — all resolve with
   **no HTTP 500, no fabricated result, no hidden fallback**. A failed step is
   listed; downstream steps are skipped; confidence drops.

## The line to say out loud

> "A team that only shows positive results is the one to be careful with. We
> tested our hypotheses, some didn't hold, and the architecture you're looking
> at is the one that survived that."

## Where each point is documented

| Point | Source |
|---|---|
| LLM planner rejected | `docs/G16_REAL_LLM_EVALUATION.md`, CLAIM_MATRIX §9 |
| SAR benefit withdrawn | `docs/G18_RELEASE_REPORT.md` Part 2, CLAIM_MATRIX §6, EXP-004 G18 addendum |
| LoRA optional | `docs/G18_RELEASE_REPORT.md` Part 3, CLAIM_MATRIX §7 |
| Confidence category | `docs/G17_TRUST_LAYER.md`, `test_g18_trust_cases.py` |
| Failures visible | `test_g18_failure_matrix.py`, `docs/research/FAILURE_AWARE_ROUTING.md` |
