---
name: map-ui
description: The SatQuery map is part of the evidence system, not decoration. Covers MapLibre layer architecture, tile/COG sources, drawing AOIs, showing change masks and detections as inspectable layers, SAR vs optical rendering, coordinate readouts, and linking map features to the evidence panel. Invoke for any work in frontend/src/maps or evidence overlays.
---

# Map UI

## The map is evidence

Every pixel on the map that represents a model output must be:
- **traceable** — click it, get the specialist result, checkpoint, confidence, timestamp;
- **toggleable** — its own layer with opacity + legend;
- **honest** — rendered in a way that matches what the sensor/model actually produced.

The map is never a stylized backdrop with markers dropped on top.

## Layer architecture

```
frontend/src/maps/
  MapProvider.tsx      # owns the single maplibre-gl instance
  layers/
    basemap.ts         # neutral reference basemap
    imagery.ts         # source optical / SAR tiles (COG via titiler or pre-tiled)
    detections.ts      # boxes / points from grounding models
    changeMask.ts      # bi-temporal change raster or vector
    aoi.ts             # user-drawn area of interest
  hooks/useMapLayer.ts # declarative add/remove/update; components never touch map directly
```

Components declare layers; the hooks reconcile them. No component calls
`map.addLayer` itself.

## Sources

- Rasters served as COG through a tile endpoint (titiler-style) or pre-tiled.
  Keep the source CRS honest; MapLibre works in Web Mercator — the reprojection
  for display is a known, stated transform, and area/measurement is computed
  server-side in a projected CRS, not from screen pixels.
- Vectors (AOI, change polygons, detections) as GeoJSON EPSG:4326.

## Rendering optical vs SAR

- Optical: true/false-color composites with a stated band mapping in the legend.
- SAR: single-band backscatter in dB with a grayscale or perceptual ramp, legend
  showing dB range and polarization. **Never** put SAR into an RGB ramp shared
  with optical.
- Change mask: diverging ramp (loss / no-change / gain) or categorical by change
  type, with a legend and the method named.

## Interaction

- Draw AOI (polygon / bbox); show vertex count and area (from server, projected CRS).
- Live coordinate + CRS readout under the cursor.
- Click a detection / mask region → opens that item in the evidence panel and
  highlights the corresponding execution-trace step.
- Time slider for bi-temporal: A / B / swipe / difference.
- Layer panel: opacity, visibility, legend, and "what produced this" per layer.

## Performance

- Debounce viewport-driven fetches; cancel stale requests.
- Don't re-add layers on every render; diff and update.
- Large vector sets → simplify server-side by zoom, or use tiled vector.
