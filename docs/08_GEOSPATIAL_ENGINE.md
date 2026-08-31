# Geospatial Engine

> Status: **Draft outline** · Owner: _TBD_ · Last updated: 2026-09-01
> Hard rules: `.claude/rules/geospatial.md`. How-to: `.claude/skills/geospatial-engineering/SKILL.md`.
> Value measured in EXP-007 (`docs/19_EXPERIMENT_REGISTRY.md`).

## Purpose

Guarantee that spatial metadata is preserved and validated end to end, so spatial
outputs and paired-image analysis are trustworthy.

## Preserve and validate

- CRS / EPSG
- affine transform
- bounds
- resolution / GSD (where available)
- band metadata (names, order, units)
- NoData value(s)
- dimensions (rows × cols)
- pair compatibility (same CRS + transform + shape for bi-temporal)
- registration / alignment (co-registration residual)

## Rules

- Metadata travels **with** the array — never a bare `numpy` array across a
  module boundary.
- Reprojection / resampling / cropping are explicit, logged operations with the
  method named (nearest for masks; bilinear/cubic for continuous).
- Bi-temporal analysis asserts an identical grid before differencing; otherwise
  reproject B onto A's grid and log it.
- Area / length only in a projected (equal-area or local UTM) CRS — never from
  EPSG:4326 degrees.
- **Never silently modify spatial metadata.**

## Open questions

- DEM source for orthorectification of SAR / off-nadir optical.
- Handling ISRO sensor products with non-standard or missing CRS tags.
- Tiling scheme for large scenes (windowed reads + cache keying).
