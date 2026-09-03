# SatQuery — Results Slide Data

> Only validated, integrated-system numbers. **Every number carries its N and
> its context.** Nothing here is a benchmark or a paper number unless labelled.
> Source: `docs/G19_SIH_SOURCE_OF_TRUTH.md` §3, `docs/sih/CLAIM_MATRIX.md`,
> `docs/PROJECT_STATUS.md` METRICS.

Label key: **[integrated]** = measured on SatQuery's own pipeline ·
**[reproduction]** = we ran the upstream code · **[negative]** = measured, did
not hold.

---

## Specialist capability (sanity-scale)

| Capability | Number | N | Context |
|---|---|---|---|
| VQA — TinyRS-2B (primary) | balanced accuracy **0.87** | **40** | RSVQA-LR sample, CPU, integrated adapter. Generic Qwen2-VL-2B fallback: 0.70. **[integrated]** |
| Grounding — RemoteSAM | acc@IoU0.5 **0.84** (21/25), mean IoU 0.762, 0 no-box | **25** | DIOR-RSVG sample, CPU. Licence NOT STATED → optional component. **[integrated]** |
| Temporal change — ChangeFormer | change-IoU **≈ 0.83** (F1 ≈ 0.91) | **7** | bundled LEVIR-CD demo pairs, CPU. **[reproduction]** — not a SatQuery benchmark. |

## Optical + SAR (capability D)

| Comparison | Result | N | Verdict |
|---|---|---|---|
| CROMA joint vs optical-only — first split (G12) | +0.067 macro-F1 (0.793 vs 0.726); 95 % CI crosses 0; McNemar p ≈ 0.45 | 200 | positive, **not significant** **[integrated]** |
| CROMA joint vs optical-only — larger independent split (G18) | **−0.026** macro-F1 (0.8247 vs 0.8505); CI [−0.080, +0.027]; McNemar p = 1.0 | 386 | **[negative]** — sign flipped, never significant → **SAR-benefit claim WITHDRAWN** |
| CROMA vs DOFA (primary metric) | CROMA ≥ DOFA on **both** splits | 200 + 386 | CROMA stays the D component |

**Slide wording:** *"We tested whether adding SAR improves the downstream task.
On a larger independent split it did not — so we withdrew the claim. CROMA
remains our optical+SAR component because it is the stronger representation, not
because SAR was proven to help."*

## RS adaptation (capability E) — LoRA on frozen CROMA

| Arm | macro-F1 | N | Note |
|---|---|---|---|
| optical-only frozen | 0.5772 | 386 | G18 larger split, 3 CPU epochs |
| fused frozen | 0.5422 | 386 | |
| fused **LoRA-adapted** | **0.6686** | 386 | +0.126 vs frozen fused, +0.091 vs optical |
| (first split, G12, 8 epochs) | 0.643 → 0.704 (**+0.061**) | 200 | direction replicates |

**Caveats on the slide:** 3-epoch CPU run, **no bootstrap / no paired test**,
under-trained frozen baselines → *directional, not significance-tested*.
Production default stays the frozen encoder; `--lora-weights` is opt-in and
verified through the real adapter (42/42 layers).

## Agent / planner

| Metric | Value | N |
|---|---|---|
| RuleBasedPlanner (production default) — PLAN_VALIDITY | **0.886** | 100 frozen missions |
| — TOOL_SELECTION | **0.90** | 100 |
| — planning latency | **< 0.01 s** | 100 |
| Execution sample — MISSION_COMPLETION / FACTUAL_CONSISTENCY / EVIDENCE_PRESERVATION / VERIFICATION_PRESERVATION | **1.00 each** | 8 |
| — UNSUPPORTED_ACTION_RATE / MAX_STEP_VIOLATION_RATE / UNNECESSARY_TOOL_CALL_RATE | **0.00 each** | 8–20 |
| Agent leverage on multi-step missions | ≈ **2.25×** the deterministic baseline's specialist calls | small N — state it |
| Pure local LLM planner (rejected) — semantic plan validity / tool-selection | 0.25 / 0.40 | 15 |
| Hybrid LLM-intent planner (optional) — INTENT_TASK_ACCURACY / plan validity | 0.317 / 0.591 | 100 |

## Trust / confidence

| Metric | Value | N |
|---|---|---|
| Trust-category rule validation | category matches the written policy in **32/32** tests, across **7** scenario families | 30 frozen cases |
| Claim-level evidence audit | **69/69** — every templated claim traces to an observation; no forbidden phrasing | ~30 claims + 5 synth |

## Geospatial correctness

| Metric | Value | N |
|---|---|---|
| EXP-007 malformed-pair rejection | **15/15** classes rejected before any model runs | 15 |
| G18 failure matrix | **22/22** pathological inputs → structured resolution; no 500, no fabricated coordinate/box/confidence, no hidden fallback | 22 |
| Structural verifier (EXP-005) | precision / recall / F1 = **1.00** on a curated corpus | 24 |

## System

| Metric | Value |
|---|---|
| Fast test suite | **383 passed, 0 failed, 0 regressions** |
| Slow adapter suite | **9/9** |
| Endpoints | 8 (`/analyze`, `/analyze/upload`, `/investigate`, `/investigate/report`, `/change`, `/scene`, `/artifact`, `/health`) + self-contained UI |
| Deployment | CPU-only, verified; one model resident at a time |
| GPU / 4 GB VRAM | **UNVERIFIED** — no CUDA host; no VRAM number claimed |

## Flagship latency (frozen demo, CPU, cold)

| Run | Total | Breakdown |
|---|---|---|
| CASE A (real change) | **93 s** | validate 0.03 · temporal 16.0 · regions 0.02 · grounding 62.3 · optical+SAR 14.2 — ≈ 90 % is model loading |
| CASE B (no change) | **17 s** | validate 0.02 · temporal 16.7 · regions 0.01 → early-stop |
| Secondary grounding | **65 s** cold / seconds warm | one model |

---

## The "do not put on a slide as positive" list

- Any SAR-benefit delta as a gain.
- Any VRAM / "4 GB" figure.
- Any confidence percentage.
- The word "significant" / any p-value framed as a win.
- "benchmark", "state-of-the-art", "real-time", "fully autonomous".
