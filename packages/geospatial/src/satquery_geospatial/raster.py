"""Raster metadata model + reader.

Contract:
    input:  a filesystem path to a raster (GeoTIFF / COG / TIFF).
    output: a :class:`RasterMeta` — CRS, affine transform, bounds, resolution,
            nodata, dtype, band info. **Header only** — no pixel data is read.
    side effects: none (opens the file read-only).
    failure modes: :class:`UnreadableRasterError` if the file is not a raster.

Geospatial metadata is never invented or silently altered here (`.claude/rules/geospatial.md`).
Anything the file does not provide is ``None``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import rasterio
from pydantic import BaseModel, Field
from rasterio.errors import RasterioIOError

from .errors import UnreadableRasterError

Transform6 = tuple[float, float, float, float, float, float]
Bounds4 = tuple[float, float, float, float]


class RasterMeta(BaseModel):
    """Metadata that travels with a raster. Serializable; no rasterio objects."""

    path: str
    driver: str
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    count: int = Field(gt=0, description="number of bands")
    dtype: str

    crs: str | None = Field(default=None, description="CRS as an authority string or WKT")
    crs_epsg: int | None = None
    is_projected: bool | None = None
    linear_units: str | None = None

    transform: Transform6 = Field(description="affine (a, b, c, d, e, f); pixel -> world")
    bounds: Bounds4 = Field(description="(left, bottom, right, top) in CRS units")
    res: tuple[float, float] = Field(description="(x, y) pixel size in CRS units, absolute")

    nodata: float | None = None
    band_descriptions: list[str | None] = Field(default_factory=list)

    @property
    def shape(self) -> tuple[int, int]:
        return (self.height, self.width)

    @property
    def pixel_count(self) -> int:
        return self.width * self.height * self.count


def _crs_fields(crs: Any) -> dict[str, Any]:
    if crs is None:
        return {"crs": None, "crs_epsg": None, "is_projected": None, "linear_units": None}
    epsg = None
    try:
        epsg = crs.to_epsg()
    except Exception:  # noqa: BLE001 - epsg lookup is best-effort
        epsg = None
    units: str | None
    try:
        units = crs.linear_units if crs.is_projected else "degree"
    except Exception:  # noqa: BLE001
        units = None
    return {
        "crs": (f"EPSG:{epsg}" if epsg else crs.to_wkt()),
        "crs_epsg": epsg,
        "is_projected": bool(crs.is_projected),
        "linear_units": units,
    }


def read_raster_meta(path: str | Path) -> RasterMeta:
    """Open ``path`` read-only and return its :class:`RasterMeta` (header only)."""
    p = Path(path)
    try:
        with rasterio.open(p) as ds:
            t = ds.transform
            b = ds.bounds
            descriptions = list(ds.descriptions) if ds.descriptions else [None] * ds.count
            return RasterMeta(
                path=str(p),
                driver=ds.driver,
                width=ds.width,
                height=ds.height,
                count=ds.count,
                dtype=str(ds.dtypes[0]) if ds.dtypes else "unknown",
                transform=(t.a, t.b, t.c, t.d, t.e, t.f),
                bounds=(b.left, b.bottom, b.right, b.top),
                res=(abs(t.a), abs(t.e)),
                nodata=ds.nodata,
                band_descriptions=descriptions,
                **_crs_fields(ds.crs),
            )
    except RasterioIOError as exc:
        raise UnreadableRasterError(f"cannot open raster {p}: {exc}") from exc
