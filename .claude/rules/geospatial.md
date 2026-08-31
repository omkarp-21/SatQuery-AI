# Geospatial Rules

- Preserve CRS.
- Preserve affine transform.
- Preserve spatial bounds.
- Never silently resize geospatial imagery.
- Record source CRS and target CRS.
- Record reprojection operations.
- Validate raster alignment before paired analysis.
- Record GSD / resolution when available.
- NoData values must be explicitly handled.

## Additional constraints

- Every raster read/write carries its `crs`, `transform`, `bounds`, `res`, `nodata`,
  and `dtype` in a metadata object that travels with the array.
- Reprojection, resampling, and cropping are explicit, logged operations with the
  method named (e.g. `nearest` for masks, `bilinear`/`cubic` for continuous data).
- Bi-temporal analysis requires the two rasters to be co-registered onto an
  identical grid (same CRS, transform, shape). Assert this before differencing.
- Pixel counts are never converted to area without the pixel size and CRS units.
- Coordinates are always tagged with their CRS. No "lat/lon" that is secretly
  projected metres, and no bare `(x, y)` without a CRS.
- Prefer Cloud-Optimized GeoTIFF (COG) for stored rasters; validate COG structure.
- Vector geometry uses Shapely with an explicit CRS (GeoPandas `GeoDataFrame.crs`
  set). GeoJSON output is EPSG:4326 per spec, and that conversion is logged.
