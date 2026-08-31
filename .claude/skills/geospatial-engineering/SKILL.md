---
name: geospatial-engineering
description: Practical geospatial coding for SatQuery — GDAL, Rasterio, GeoPandas, Shapely, pyproj, COG, GeoJSON, raster alignment, coordinate transforms, windowed reads, area computation. Invoke for any code that reads/writes rasters or vectors, reprojects, crops, or converts between coordinate systems.
---

# Geospatial Engineering

Enforces `.claude/rules/geospatial.md`. This is the how-to.

## Metadata travels with the array

Never pass a bare `numpy` array between functions. Wrap it:

```python
@dataclass
class Raster:
    data: np.ndarray            # (bands, rows, cols)
    crs: CRS                    # rasterio.crs.CRS — always set
    transform: Affine          # pixel -> world
    nodata: float | None
    # derived: bounds, res via rasterio helpers
```

## Rasterio patterns

- Read: `with rasterio.open(path) as ds: arr = ds.read(); prof = ds.profile`.
- Windowed read for large rasters: `ds.read(window=from_bounds(*bbox, ds.transform))`.
- Write COG: driver `GTiff`, `tiled=True`, `blockxsize/ysize=512`,
  `compress='deflate'`, build overviews, or use `rio-cogeo` and validate.
- Always propagate `nodata`; mask with `ds.read(masked=True)` and keep the mask.

## Reprojection (explicit + logged)

```python
from rasterio.warp import calculate_default_transform, reproject, Resampling
# choose resampling by data type:
#   Resampling.nearest  -> class masks, categorical
#   Resampling.bilinear -> continuous (reflectance, backscatter)
#   Resampling.cubic    -> smoother continuous, upsampling
```

Record `{src_crs, dst_crs, resampling, src_res, dst_res}` in provenance.

## Raster alignment for bi-temporal

Before differencing two rasters, assert identical grid:

```python
assert a.crs == b.crs
assert a.transform == b.transform
assert a.data.shape == b.data.shape
```

If not equal: reproject B onto A's grid (`reproject` with A's transform+shape),
log it, and note residual co-registration error if known.

## Coordinate transforms

- `pyproj.Transformer.from_crs(src, dst, always_xy=True)` — mind axis order.
- Never mix degrees and metres. Tag every coordinate with its CRS.
- For area/length: work in an equal-area or local UTM CRS, not EPSG:4326.

## Vectors

- `GeoDataFrame` with `.crs` set. Set-then-reproject: `gdf.set_crs(...)`,
  `gdf.to_crs(...)`.
- Shapely 2.x vectorized ops; validate geometries (`make_valid`), fix winding.
- Raster → vector: `rasterio.features.shapes(mask, transform=...)`.
- API output GeoJSON is EPSG:4326; log the `to_crs(4326)` step.

## Area from a mask

```python
pixel_area = abs(transform.a * transform.e)      # in CRS units^2 (use a projected CRS)
area = int(mask.sum()) * pixel_area
```

Never report area from an EPSG:4326 raster without projecting first.

## GDAL CLI (when scripting)

`gdalwarp -t_srs`, `gdal_translate -of COG`, `gdalinfo -json`. Prefer Rasterio in
product code; GDAL CLI is fine in `scripts/`.
