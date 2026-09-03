# SatQuery — Pitch & 30-Second Explanation

> Backed by `docs/G19_SIH_SOURCE_OF_TRUTH.md`. Avoid: "revolutionary",
> "state-of-the-art", "fully autonomous", "AI-powered" as empty filler,
> "real-time".

## Part 3 — One-sentence pitch

### Five alternatives

1. **"SatQuery is an agentic multimodal remote-sensing system that turns
   natural-language geospatial missions into verified analysis across temporal
   imagery, optical/SAR data, and spatial grounding."**
   *(the preferred form from the brief — kept intact)*

2. "SatQuery takes a plain-English mission over satellite imagery, plans it into
   validated specialist steps, adapts as it observes each result, and returns a
   spatially grounded, evidence-backed answer."

3. "Instead of one large vision-language model, SatQuery orchestrates a frozen
   set of remote-sensing specialists behind a deterministic planner and a
   verification layer, and answers geospatial missions in natural language."

4. "SatQuery is a natural-language geospatial investigator: it routes a mission
   to the right imagery specialists, checks the geometry and the evidence, and
   produces a verified map and report — on a laptop."

5. "SatQuery turns 'what changed here, where, and does the radar agree?' into a
   bounded multi-step investigation with traceable evidence and an explicit
   confidence category."

### Final choice

> **SatQuery is an agentic multimodal remote-sensing system that turns
> natural-language geospatial missions into verified, spatially grounded
> analysis across temporal imagery, optical/SAR data, and object grounding —
> by orchestrating specialist models behind a deterministic planner and a
> verification layer.**

Trimmed variant for a slide title: **"Natural-language geospatial investigation,
specialist-orchestrated and verified."**

## Part 4 — 30-second judge explanation (spoken, ≤ 30 s)

> "Instead of forcing one large vision-language model to answer every satellite
> question, SatQuery treats the request as a geospatial *mission*. A
> deterministic planner breaks it into typed steps; a 12-check policy layer
> clears them; then a bounded agent runs the specialist models one at a time —
> change detection, object grounding, optical-plus-SAR — and *observes each
> result*. If there's no real change it skips the rest and stops early; if a
> step fails it says so and never fabricates. It validates the imagery's
> geometry, verifies the evidence, and returns a spatially grounded answer, a
> GeoJSON, an evidence trail, and a confidence *category* with a reason — all on
> a laptop, CPU-only."

Word count ≈ 105; reads in ~28 s at a normal pace.

### If you only get one line

> "SatQuery plans a natural-language imagery mission, runs the right specialist
> models, watches what they return, adapts, verifies, and hands back a
> spatially-grounded answer with its evidence."

### Three anchor facts to land

- **WHAT** — natural-language geospatial investigation over single-image,
  bi-temporal, and optical/SAR imagery.
- **WHY different** — not one VLM; a deterministic planner + policy + a bounded
  observe/replan agent + specialist models + verification.
- **HOW trust** — geometry validated, every claim traced to an observation,
  structural verification, evidence-derived confidence category (not a number),
  22/22 failure cases resolve cleanly.
