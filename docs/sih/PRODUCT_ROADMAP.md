# SatQuery — Product Roadmap

> Realistic, no impossible timelines, no operational-readiness claims beyond a
> prototype. Aligned with `docs/20_PROTOTYPE_ROADMAP.md` and the G18/G19 freeze.
> Facts: `docs/G19_SIH_SOURCE_OF_TRUTH.md`.

## NOW — local research / demo prototype (frozen at G19)

- Natural-language `/analyze` (single-step) + `/investigate` (agentic multi-step)
  + self-contained UI + one-click HTML report.
- Frozen specialist stack (ADR-021): TinyRS-2B, RemoteSAM, ChangeFormer,
  CROMA/DOFA, RemoteCLIP.
- Deterministic planner (production default) + optional LLM-intent hybrid.
- 12-check policy, bounded observe/replan executor, geospatial validation,
  typed evidence + provenance, structural verification, evidence-derived
  confidence category, failure-aware resolution.
- CPU-only, offline, laptop-deployable. 383 fast tests green.
- **Known gaps:** sanity-scale evaluation; GPU/4 GB fit unverified; RemoteSAM
  licence not stated; SAR task-benefit not established; LoRA directional only.

`FINAL_TECH_FREEZE = TRUE` — after G19: bug fixes, demo reliability,
presentation assets only.

## NEXT — post-competition, months (each with an evaluation gate)

| Item | Why | Gate before it ships |
|---|---|---|
| **Larger, significance-tested evaluation** | move numbers from "sanity-scale" to defensible | bootstrapped before/after deltas, held-out splits, per-capability N in the hundreds+ |
| **GPU deployment profile** | measured VRAM fit + latency | actual VRAM measurement on a CUDA host; replace "UNVERIFIED" with a number |
| **Stronger intent model** | the 2 B local model misclassifies task family ~68 % of the time | intent task-accuracy clears the deterministic planner's plan-validity on the frozen missions |
| **Broader modality coverage** | more sensor types (hyperspectral, higher-res SAR, DEM) | each new modality has an adapter with a smoke test + a routing rule |
| **More domain adaptation** | LoRA direction replicates; make it earn "default" | epoch-matched, bootstrapped larger-split result that clears a pre-registered bar |
| **Resolve the RemoteSAM licence** | remove the "optional component" caveat | an explicit upstream licence, or a licensed replacement grounding model |

## LATER — direction, not commitment

- **Multi-AOI analysis** — run a mission over a set of areas, not one tile.
- **Continuous monitoring** — scheduled re-runs over an AOI with change alerts.
- **Domain-specific deployments** — curated specialist sets + missions for
  disaster response, infrastructure, agriculture.
- **Human-in-the-loop workflows** — analyst review/annotation folded back into
  the evidence trail; corrections captured.
- **Provenance / audit export** — signed, portable investigation records.

## What is explicitly NOT on the roadmap

- Replacing the frozen stack with one giant VLM.
- Making the LLM control execution.
- Claiming real-time or full autonomy.
- Adding capabilities without an adapter + a routing rule + an evaluation path.
