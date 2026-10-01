# SatQuery — Architecture Diagram (PPT)

> One clean diagram for the slide deck, plus a text description (accessibility +
> diffability). Colour/shape legend is for the slide designer. Facts:
> `docs/G19_SIH_SOURCE_OF_TRUTH.md` §6.

## The diagram (linear spine)

```
                        ┌───────────────────────────────┐
                        │        USER MISSION           │   natural language
                        │  text + 1–4 rasters (opt/SAR) │
                        └───────────────┬───────────────┘
                                        ▼
                        ┌───────────────────────────────┐
                        │      INTENT / PLANNER          │   ◆ SYSTEM
                        │  RuleBasedPlanner (default)    │
                        │  ┄ optional: LLM→Intent→       │
                        │      PlanSynthesizer (hybrid)  │
                        └───────────────┬───────────────┘
                                        ▼
                        ┌───────────────────────────────┐
                        │           POLICY              │   ■ SAFETY
                        │  12-check plan validation +   │
                        │  plan–intent cross-check      │
                        └───────────────┬───────────────┘
                                        ▼
                        ┌───────────────────────────────┐
                        │   SPECIALIST ORCHESTRATION    │   ◆ SYSTEM
                        │  bounded executor, ≤ 8 calls, │
                        │  one model resident at a time │
                        └───────────────┬───────────────┘
                                        ▼
         ┌───────────────┬──────────────┼──────────────┬───────────────┐
         ▼               ▼              ▼              ▼               ▼
   ┌──────────┐   ┌────────────┐  ┌───────────┐  ┌────────────┐  ┌──────────┐   ● MODEL
   │   VQA    │   │  GROUNDING │  │ TEMPORAL  │  │ OPTICAL+SAR│  │  SCENE   │
   │ TinyRS-2B│   │ RemoteSAM  │  │ChangeFormer│ │ CROMA/DOFA │  │RemoteCLIP│
   └────┬─────┘   └─────┬──────┘  └─────┬─────┘  └─────┬──────┘  └────┬─────┘
        └───────────────┴──────────────┼──────────────┴──────────────┘
                                        ▼
                        ┌───────────────────────────────┐
                        │         OBSERVATION           │   ◆ SYSTEM
                        │   inspect each step result    │
                        └───────────────┬───────────────┘
                                        ▼
                        ┌───────────────────────────────┐
                        │      ADAPTIVE DECISION        │   ◆ SYSTEM
                        │  continue · structured replan │
                        │  (6 reasons) · early-stop     │
                        └───────────────┬───────────────┘
                                        ▼
                        ┌───────────────────────────────┐
                        │          EVIDENCE            │   ■ SAFETY
                        │  typed EvidenceItem + prove-  │
                        │  nance on every path          │
                        └───────────────┬───────────────┘
                                        ▼
                        ┌───────────────────────────────┐
                        │        VERIFICATION          │   ■ SAFETY
                        │  structural / deterministic   │
                        │  checks → aggregate status    │
                        └───────────────┬───────────────┘
                                        ▼
                        ┌───────────────────────────────┐
                        │    TRUST / CONFIDENCE         │   ■ SAFETY
                        │  category + why  (NOT a       │
                        │  probability)                 │
                        └───────────────┬───────────────┘
                                        ▼
                        ┌───────────────────────────────┐
                        │  GEO-SPATIAL ANSWER / REPORT  │   ◆ SYSTEM
                        │  spatial findings + EPSG:4326 │
                        │  GeoJSON + one-click HTML      │
                        └───────────────────────────────┘

  Cross-cutting (not a stage):  GEOSPATIAL VALIDATION  ■ SAFETY
  CRS / transform / bounds / co-registration checked before any model runs;
  malformed or misregistered input → typed error, no fabricated coordinate.
```

## Legend

| Marker | Meaning | Examples |
|--------|---------|----------|
| ● **MODEL** | a frozen specialist model (ADR-021) | TinyRS-2B, RemoteSAM, ChangeFormer, CROMA, DOFA, RemoteCLIP |
| ◆ **SYSTEM** | deterministic orchestration code | planner, executor, observation, adaptive decision, report |
| ■ **SAFETY** | a guard / evidence / verification layer | policy, geospatial validation, evidence, verification, trust category |

## Text description (for the slide notes / accessibility)

A single vertical pipeline. A **user mission** (natural language plus one to four
rasters) enters an **intent/planner** stage — deterministic by default, with an
optional LLM-intent hybrid. The plan passes a **12-check policy** layer. A
**bounded executor** (at most 8 calls, one model resident at a time) dispatches
to the **specialist models**: VQA, grounding, temporal change, optical+SAR,
scene. After each specialist, an **observation** step inspects the result and an
**adaptive decision** chooses to continue, issue one of six structured replans,
or stop early. Results are assembled into typed **evidence** with provenance,
checked by **structural verification**, and summarised by a **trust/confidence
category** with an explicit "why". The output is a **geospatial answer** —
spatial findings, an EPSG:4326 GeoJSON, and a one-click HTML report. Running
across the whole pipeline is **geospatial validation**: CRS, transform, bounds
and co-registration are checked before any model runs, and malformed or
misregistered input is rejected with a typed error rather than guessed past.

## Simplified 6-box version (if the full diagram is too dense for one slide)

```
MISSION → PLAN (deterministic) + POLICY → SPECIALISTS (observe/replan, bounded)
        → EVIDENCE + VERIFICATION → CONFIDENCE CATEGORY → GEOSPATIAL REPORT
                     └─ geospatial validation gates the whole flow ─┘
```
