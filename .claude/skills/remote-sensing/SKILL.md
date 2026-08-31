---
name: remote-sensing
description: Remote-sensing domain knowledge for SatQuery — SAR vs optical, polarimetry (VV/VH, sigma-nought), multispectral bands, GSD, co-registration, orthorectification, cloud masking, spectral indices, temporal normalization, and change detection. Invoke whenever code or analysis touches imagery physics, sensor characteristics, or preprocessing choices. Also states what NOT to assume.
---

# Remote Sensing

## Modalities — keep them distinct

- **Optical / multispectral** — reflected sunlight. Has bands (e.g. Sentinel-2:
  B2 blue, B3 green, B4 red, B8 NIR, B11/B12 SWIR). Blocked by clouds. Values are
  reflectance (0–1 after scaling) or DN.
- **SAR** — active microwave, side-looking. Sees through cloud and at night.
  Values are **backscatter**, not brightness. Geometry effects: foreshortening,
  layover, shadow, speckle. **Never render or model SAR as RGB.**

### SAR specifics

- **Polarization**: VV, VH (and VH/VV ratio) carry different structure —
  VV ~ surface/rough, VH ~ volume (vegetation), ratio useful for classification.
- **σ⁰ (sigma-nought)**: calibrated radar backscatter coefficient, usually in dB
  (`10·log10`). Compare in dB, not linear, for visualization/thresholds.
- **Speckle**: multiplicative noise — needs multilook or a speckle filter
  (Lee, Refined Lee) before pixel comparison. Filtering is a logged operation.
- SAR needs radiometric calibration + terrain correction (RTC) before analysis.

## Key concepts

- **GSD / resolution** — ground sample distance per pixel. Two rasters at different
  GSD are not directly comparable; resample explicitly and record it.
- **CRS** — coordinate reference system (e.g. EPSG:4326 geographic, EPSG:32643 UTM
  43N). Always known, always recorded.
- **GeoTIFF / COG** — raster + geodata (CRS, affine transform, nodata). COG adds
  internal tiling + overviews for range reads.
- **Co-registration** — aligning two images to the same grid. Required before any
  paired (bi-temporal) analysis. Sub-pixel misregistration creates fake "change".
- **Orthorectification** — removing terrain/viewing-geometry distortion using a DEM
  so pixels map to true ground position.
- **Temporal normalization** — accounting for sun angle, look angle, seasonality,
  atmospheric state so that "difference" reflects real change, not acquisition
  conditions. Histogram matching / relative radiometric normalization for optical.
- **Cloud masking** — optical only. Use the provider's scene classification / cloud
  probability (s2cloudless, Fmask, QA bands). Masked pixels are nodata, not zero.
- **Spectral indices** — NDVI `(NIR−Red)/(NIR+Red)` vegetation, NDWI water,
  NDBI built-up, BSI bare soil. Compute from surface reflectance, guard divide-by-zero.
- **Change detection** — image differencing, ratioing (better for SAR), CVA,
  post-classification comparison, or a learned model. Output is a change map +
  (ideally) a change type.

## Do NOT assume

- That two images "line up" — verify co-registration.
- That higher backscatter = brighter/more vegetation — it depends on polarization
  and geometry.
- That NDVI works on raw DN — needs reflectance.
- That a cloud-free-looking tile is cloud-free — check the mask.
- That optical and SAR change maps should agree — they measure different things;
  disagreement is a signal to surface, not to average away.
- That pixel count = area — convert via pixel size in the CRS's units.
- That EPSG:4326 distances are metres — they are degrees.
- That a model trained on one sensor/region transfers to ISRO data unchanged.
