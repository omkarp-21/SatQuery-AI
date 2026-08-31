---
name: evidence-provenance
description: SatQuery's evidence and audit model — what an evidence object contains, how provenance is recorded at every stage, what makes a result independently verifiable, and how the frontend links claims to evidence. Invoke for work in the evidence, verification, confidence, or provenance stages, or the evidence panel UI.
---

# Evidence & Provenance

Two related obligations from the core principle (**Explain**, **Audit**):

## Provenance — the audit record

Built up from the `metadata` stage onward, persisted by the `provenance` stage.
For every run it records:

- **Query**: raw text, parsed intent, query id, timestamp, user/session.
- **Inputs**: scene ids, provider, sensor, acquisition dates, CRS, bbox, GSD,
  content hashes of the actual pixels used.
- **Plan**: the full `ExecutionPlan` verbatim (so the run is reproducible).
- **Per step**: model name + version, checkpoint sha256, adapter version, device,
  library versions, input digest, params, duration, outcome.
- **Geospatial ops**: every reproject / resample / crop with method and CRS pair.
- **Fusion**: strategy, weights, inputs combined.
- **Verification**: checks run, pass/fail, disagreements flagged.
- **Confidence**: value + its documented meaning + what lowered it.
- **Code**: repo commit SHA.

Rules: no secrets in the record (scrub first); append-only; serializable; stored
so the exact run can be replayed.

## Evidence — the human-inspectable trail

An `EvidenceItem` makes one claim checkable:

```python
class EvidenceItem(BaseModel):
    claim: str                     # "vegetation loss of ~2.1 ha in AOI"
    kind: Literal["tile","mask","bbox","caption","index","citation","metric"]
    geometry: GeoJSON | None       # where on the map
    raster_ref: str | None         # the tile/mask asset
    produced_by: str               # plan step id
    model: str | None              # registry key + version
    confidence: Confidence | None  # value + qualifier
    how_to_verify: str             # independent method a human could apply
```

Every top-level answer decomposes into `EvidenceItem`s. No claim without one.

## Independently verifiable

Where possible, `verification` re-derives a result a different way:
- change area cross-checked with a spectral-index difference, not just the model;
- a detection cross-checked against a second model or a rule;
- optical vs SAR agreement explicitly computed and reported (disagreement is
  surfaced, never averaged into a single confident number).

If a claim can't be independently checked, label it "single-source".

## Frontend link

The evidence panel lists `EvidenceItem`s; clicking one highlights its map
geometry and its execution-trace step. The trace, the map, and the evidence panel
are three views of the same provenance graph.
