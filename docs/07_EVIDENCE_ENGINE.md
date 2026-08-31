# Evidence Engine

> Status: **Draft outline** · Owner: _TBD_ · Last updated: 2026-09-01
> Design detail: `.claude/skills/evidence-provenance/SKILL.md`.

## Purpose

Make every important answer traceable to concrete, inspectable evidence, and keep
observation separate from inference.

## An answer decomposes into evidence

Evidence for a claim may include:

- source image(s) (which tiles, which pixels — by content hash)
- spatial region / bounding box / mask
- temporal relation (T1 vs T2, ordering)
- sensor / modality (optical band mapping, SAR polarization + dB range)
- specialist output (model + version + checkpoint hash)
- metadata validation result (CRS, alignment, GSD)
- cross-model agreement / disagreement

## Keep these separate

**Observed evidence** · **model inference** · **uncertainty** · **unsupported
claims**. The UI and the response never blur them. A claim that cannot be
independently checked is labelled "single-source".

## `EvidenceItem` (sketch)

`claim` · `kind` (tile/mask/bbox/caption/index/citation/metric) · `geometry` ·
`raster_ref` · `produced_by` (plan step id) · `model` · `confidence` (value +
qualifier) · `how_to_verify`.

Every top-level answer is a list of `EvidenceItem`s; clicking one highlights its
map geometry and its execution-trace step.

## Open questions

- Storage format for evidence artifacts (inline vs object store references).
- How much intermediate output to retain per run vs on demand.
