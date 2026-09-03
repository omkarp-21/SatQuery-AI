# SatQuery — SIH Core Story

> For a non-ML judge. Every sentence here is backed by
> `docs/G19_SIH_SOURCE_OF_TRUTH.md`. No exaggeration.

## 1. Problem

Satellite imagery is abundant, but getting an answer out of it is not. A useful
question — *"what changed here between these two dates?"*, *"where are the
affected buildings?"*, *"does the radar view agree with the optical view?"* —
usually means opening specialist GIS software, knowing which tool and which model
to run, chaining them by hand, and checking the coordinates yourself. That
workflow needs expertise most decision-makers do not have and takes time they do
not have.

## 2. Insight

There is no single model that answers every remote-sensing question well.
Different questions need different analytical capabilities: reading a scene,
locating a described object, comparing two dates, combining optical and radar.
Forcing one large vision-language model to do all of it makes it worse at each.

So the right unit of work is not "a prompt to one model" — it is **a geospatial
mission** that gets broken into the right specialist steps, run in the right
order, and checked.

## 3. SatQuery

SatQuery is a natural-language geospatial **investigation** system. You give it a
mission in plain English and one to four images. It:

1. **plans** the mission into typed steps (a deterministic planner picks the
   tools and the order),
2. **validates** the plan against a 12-check safety policy,
3. **validates the imagery** — CRS, transform, bounds, co-registration — and
   rejects anything malformed instead of guessing,
4. runs the **specialist models** one at a time (change detection, grounding,
   optical+SAR representation, scene, VQA),
5. **observes each result and adapts** — if there is no change, it skips the
   downstream steps and stops early; if a step fails, it says so and does not
   fabricate a result,
6. **verifies** the evidence with structural checks,
7. returns a **spatially grounded answer**, an EPSG:4326 GeoJSON of the
   findings, an evidence trail, a confidence **category** with an explicit
   "why", and a one-click HTML report.

## 4. Differentiation

**Not one giant VLM.** Instead:

```
natural language
  → planning            (deterministic; a rejected LLM planner is opt-in only)
  → policy              (12 checks; nothing illegal reaches execution)
  → specialist models   (frozen stack: ChangeFormer, RemoteSAM, CROMA/DOFA, TinyRS, RemoteCLIP)
  → observation         (every intermediate result is inspected)
  → adaptive execution  (continue / structured replan / early-stop — bounded ≤ 8 steps)
  → evidence            (typed, with provenance on every path)
  → verification        (structural / deterministic checks)
  → geospatial report   (spatial findings + GeoJSON + HTML report)
```

The demonstration that makes this concrete is **CASE A vs CASE B**: the *same*
mission runs longer (4 specialist calls, HIGH confidence) when there is real
change, and shorter (2 calls, 2 structured replans, early-stop, MEDIUM
confidence) when the imagery shows none — and the shorter path is decided by the
actual change-detection output, not a hard-coded branch.

## 5. Impact

SatQuery turns a specialist multi-tool imagery workflow into a single
natural-language interface that returns a verified, spatially grounded answer and
a report — on a laptop, CPU-only. It is a research-backed working prototype:
sanity-scale evaluation, honest limitations, and a validation discipline that has
already made us **withdraw one of our own earlier claims** when a larger
experiment did not support it.

## What to remember

> **Natural-language geospatial investigation → specialist orchestration →
> evidence → verified map / report.**
