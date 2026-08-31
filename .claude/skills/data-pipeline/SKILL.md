---
name: data-pipeline
description: SatQuery's data flow — imagery ingestion from providers (Sentinel Hub, Planetary Computer, local ISRO files), STAC manifests, the raw/processed/demo/manifests layout, chipping, caching, and reproducible preprocessing. Invoke for work in the ingestion or metadata stages, or anything under data/ and scripts/download_data.
---

# Data Pipeline

## Directory contract

| Dir | Contents | VCS |
|-----|----------|-----|
| `data/raw/` | Untouched downloads (tiles, STAC dumps, provider scenes) | gitignored |
| `data/processed/` | Derived: chips, aligned stacks, indices, embeddings | gitignored |
| `data/demo/` | Small curated set for the scripted demo | committed |
| `data/manifests/` | STAC / CSV manifests: what exists, where, provenance | committed |

Nothing in `raw/` is edited in place. Processing reads `raw/`, writes `processed/`,
and records the operation in a manifest.

## Ingestion stage

1. Resolve the query's AOI + date range to candidate scenes via a STAC search
   (Planetary Computer / Sentinel Hub) or a local catalog for ISRO files.
2. Record for each scene: id, provider, sensor, acquisition datetime, CRS, bbox,
   GSD, cloud cover, bands/polarizations, asset hrefs, license.
3. Download or window-read only what's needed. Cache by content hash.
4. Emit a typed `IngestResult` (list of `SceneRef` + local paths) — the metadata
   stage takes it from here.

## Metadata stage

- Open each raster, extract CRS / transform / bounds / res / nodata / dtype /
  band descriptions / acquisition date. Attach to the scene object.
- Flag mismatches early: differing CRS across a bi-temporal pair, missing nodata,
  suspicious dtype, zero-area bbox.

## Reproducible preprocessing

- Preprocessing is a pure function of (inputs, params, code commit). Same inputs
  + same params → same output (byte-identical where feasible, else within tol).
- Every processed artifact has a manifest entry: source scene ids, operation
  chain (reproject, speckle-filter, cloud-mask, chip), params, code commit,
  output hash.
- Chipping records the parent scene, chip grid, and the transform per chip.

## Providers & secrets

- Provider credentials only from `.env` (`SENTINELHUB_*`, `PLANETARY_COMPUTER_KEY`).
- Respect rate limits; retry transient failures with backoff; never hammer.
- Local ISRO imagery: treat as untrusted input — validate format, dimensions, CRS
  before use.

## Demo data

`data/demo/` is frozen and versioned. The demo path must run offline from it.
Regenerating it is a deliberate, documented step in `scripts/download_data/`.
