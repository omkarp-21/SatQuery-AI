# SatQuery — Impact & Use Cases

> Three concrete scenarios. Each maps a real user need to the *actual* SatQuery
> pipeline and output. **We do not claim operational readiness beyond a
> prototype** — these describe what the demoed system does, at demo scale.
> Facts: `docs/G19_SIH_SOURCE_OF_TRUTH.md`.

Each scenario uses the same real capability set: `TEMPORAL_CHANGE`,
`EXTRACT_CHANGED_REGIONS`, `GROUND_OBJECT`, `OPTICAL_SAR_ANALYSIS`,
`CROSS_CHECK_EVIDENCE`, geospatial validation, verification, confidence category,
GeoJSON + HTML report.

---

## 1. Disaster / damage assessment

- **User:** a district disaster-response officer, after a flood or earthquake.
- **Mission:** *"Compare the pre-event and post-event imagery for this area,
  identify where structures changed, and give me a verified summary with
  coordinates."*
- **SatQuery does:** validates the two rasters are co-registered → ChangeFormer
  locates change → regions are extracted with lon/lat boxes → RemoteSAM grounds
  the affected structures → cross-check confirms grounded regions fall inside
  changed areas → structural verification → confidence category → EPSG:4326
  GeoJSON + report.
- **Output:** a map of changed regions with coordinates, a short verified
  summary, an evidence trail, and a confidence category with reasons.
- **Decision supported:** where to send assessment teams first; a shareable
  report for the response log.
- **Honest limit:** change quality is demonstrated at n = 7 (reproduction); this
  is decision *support*, not an authoritative damage count.

## 2. Infrastructure / urban development monitoring

- **User:** an urban-planning or land-authority analyst tracking unauthorised
  construction.
- **Mission:** *"Between these two dates, has new built-up area appeared near
  this boundary? Locate it and check the radar view."*
- **SatQuery does:** co-registration check → ChangeFormer change fraction +
  regions → grounding of built-up structures → CROMA joint optical+SAR
  representation computed (shown as representation-level only — no semantic
  over-claim) → verification → report.
- **Output:** flagged regions with coordinates and area (ha), the joint
  representation as supporting context, a verified summary.
- **Decision supported:** which sites warrant a field visit or a notice.
- **Honest limit:** SatQuery does **not** assert "this is new construction" from
  the SAR embedding — the analyst confirms; and adding SAR was not shown to
  improve the downstream task.

## 3. Agricultural / land-use monitoring

- **User:** an agriculture-department officer monitoring land-use change across a
  season.
- **Mission:** *"Identify where land cover changed between these two
  acquisitions and summarise the extent."*
- **SatQuery does:** validation → ChangeFormer change detection → region
  extraction with area → optional scene/tagging context (RemoteCLIP) → structural
  verification → GeoJSON + report. If there is **no** meaningful change, the
  agent stops early and says so (the CASE B behaviour) rather than manufacturing
  a result.
- **Output:** changed-area extent with coordinates, or an explicit
  "no significant change" with the threshold stated.
- **Decision supported:** where to focus a ground survey; a season-over-season
  record.
- **Honest limit:** land-cover class labels come from a sanity-scale probe
  (DFC2020, 8 classes); treat class-level output as indicative.

---

## The common shape

```
USER  →  natural-language MISSION  →  SATQUERY
      →  validated multi-step investigation (adapts to what it observes)
      →  spatially grounded OUTPUT + evidence + verification + confidence category + report
      →  a faster, checkable first pass that a human confirms
```

SatQuery is a **decision-support first pass**: it does the routing, the geometry
checks, the specialist runs and the evidence assembly, and hands a human a
verified, traceable result to act on.
