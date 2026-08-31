---
name: performance
description: Performance engineering for SatQuery — measure before optimizing, windowed raster I/O, tiling, caching by content hash, GPU batching and VRAM budgeting, model warm-up, latency budgets per pipeline stage, and the no-GPU degradation path. Invoke when addressing speed, memory, throughput, or latency, or writing benchmark scripts.
---

# Performance

## Measure first

No optimization without a before-number from a real run. Benchmarks live in
`scripts/benchmark/`; results feed `docs/13_PERFORMANCE.md` with the full record
(hardware, input size, batch, cold/warm, p50/p95). Same discipline as `evaluation`.

## Latency budget (set targets, then measure against them)

Assign a wall-clock budget per stage in `docs/13_PERFORMANCE.md`, e.g.:

| Stage group | Target (warm) |
|-------------|---------------|
| ingestion + metadata | data-bound; window-read, don't fetch whole scenes |
| routing + planning | < 1s (small LLM call, cached prompt) |
| specialists | dominant cost; batch, keep models warm |
| fusion + verification + geospatial | < 2s |
| evidence + provenance + reports | < 1s |

Report the actual p50/p95 next to each target. Don't claim a number you didn't time.

## Raster I/O

- Windowed reads (`rasterio` windows) — never load a full scene to use a tile.
- Reproject once, cache the aligned stack (`data/processed/`, keyed by content hash).
- COG + overviews so zoomed-out views read less data.
- Vectorize masks at the needed resolution, not full-res then simplify.

## GPU

- Load each model once (warm pool); measure cold vs warm and report both.
- Batch specialist calls where the plan allows independent steps.
- Track VRAM per adapter (declared in the registry). On OOM: retry with a smaller
  tile/batch, deterministically — don't just fail.
- Move data to device once; avoid host↔device ping-pong in loops.

## Caching

- Content-hash keys: `(operation, input digest, params, code commit)` → artifact.
- Cache STAC search results, aligned stacks, embeddings, and tile renders.
- Cache is an optimization, never correctness: a cache miss must reproduce the
  same result.

## No-GPU path

The system must still *run* without a GPU: adapters that need one raise a clear
error, the planner routes to CPU-capable models or returns a partial answer with
lowered confidence and an explicit note. Benchmark this path too.

## Frontend

- Debounce viewport fetches, cancel stale requests, virtualize long trace lists,
  avoid layout shift, lazy-load the heavy map bundle.
