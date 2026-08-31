---
name: testing
description: How to test SatQuery well — pytest and vitest patterns, synthetic raster fixtures, stage contract tests, adapter smoke tests, deterministic seeding, marking slow/gpu/integration tests, and starting bug fixes from a failing test. Invoke when writing or reviewing tests, or when a change lands without them.
---

# Testing

Enforces `.claude/rules/testing.md`. This is the practice.

## Backend (pytest)

Layout mirrors the package: `backend/tests/satquery/<stage>/test_*.py`,
`backend/tests/models/test_<adapter>.py`.

Per pipeline stage, write:
1. **Transform test** — representative input → expected output values.
2. **Contract test** — output validates against its Pydantic schema; provenance present.
3. **Failure test** — malformed input raises the specific typed error (not `Exception`).

## Synthetic raster fixtures

Do not download in a unit test. Build tiny rasters with known geodata:

```python
@pytest.fixture
def tiny_raster(tmp_path):
    transform = from_origin(75.0, 15.0, 0.0001, 0.0001)  # ~10m near equator
    data = np.arange(64, dtype="float32").reshape(1, 8, 8)
    profile = dict(driver="GTiff", height=8, width=8, count=1,
                   dtype="float32", crs="EPSG:4326", transform=transform, nodata=-9999)
    path = tmp_path / "t.tif"
    with rasterio.open(path, "w", **profile) as ds:
        ds.write(data)
    return path
```

Keep a small library of these in `backend/tests/fixtures/` (single, bi-temporal
aligned, bi-temporal misaligned, SAR-like dB, with-nodata).

## Adapter smoke tests

```python
@pytest.mark.slow
@pytest.mark.gpu
def test_geochat_adapter_runs(geochat_checkpoint, tiny_optical_scene):
    a = GeoChatAdapter(checkpoint=geochat_checkpoint)
    result = a.predict(AdapterRequest(query="what is in this image?",
                                      images=[tiny_optical_scene]))
    assert result.model == "geochat"
    assert result.provenance["checkpoint_sha256"]
```

## Markers (in `pyproject.toml`)

`slow`, `gpu`, `integration`. Default `pytest` run excludes `integration` and
(in CI without a GPU) `gpu`. `make test` runs the fast set.

## Determinism

- `numpy`, `random`, `torch` seeded in a fixture; record the seed.
- No real network (`pytest-socket` or a fixture that blocks it) outside `integration`.
- Freeze time (`freezegun`) where timestamps appear in assertions.

## Frontend (vitest)

- Colocated `*.test.tsx`. Test behavior and states (loading/empty/error), not
  implementation details.
- Mock the API layer, not `fetch` scattered through components.
- Map hooks: assert layer add/update/remove calls on a fake map, not pixels.

## Bug fixes

Reproduce with a failing test first, then fix, then keep the test.
