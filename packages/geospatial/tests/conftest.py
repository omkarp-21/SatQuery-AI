"""Shared synthetic-raster fixtures. Tiny in-memory GeoTIFFs with known geodata —
no downloads (`.claude/rules/testing.md`)."""

from __future__ import annotations

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin


def _write(path, *, width=8, height=8, count=3, crs="EPSG:32643", origin=(600000.0, 1500000.0),
           res=10.0, nodata=0.0, dtype="uint8"):
    transform = from_origin(origin[0], origin[1], res, res)
    data = (np.arange(width * height * count) % 255).reshape(count, height, width).astype(dtype)
    profile = dict(
        driver="GTiff", width=width, height=height, count=count, dtype=dtype,
        crs=crs, transform=transform, nodata=nodata,
    )
    with rasterio.open(path, "w", **profile) as ds:
        ds.write(data)
        ds.descriptions = tuple(f"band{i+1}" for i in range(count))
    return str(path)


@pytest.fixture
def tiny_geotiff(tmp_path):
    return _write(tmp_path / "a.tif")


@pytest.fixture
def tiny_pair_aligned(tmp_path):
    a = _write(tmp_path / "t1.tif")
    b = _write(tmp_path / "t2.tif")
    return a, b


@pytest.fixture
def tiny_pair_misregistered(tmp_path):
    a = _write(tmp_path / "t1.tif", origin=(600000.0, 1500000.0))
    b = _write(tmp_path / "t2.tif", origin=(600050.0, 1500000.0))  # 5-pixel x shift
    return a, b


@pytest.fixture
def tiny_pair_crs_mismatch(tmp_path):
    a = _write(tmp_path / "t1.tif", crs="EPSG:32643")
    b = _write(tmp_path / "t2.tif", crs="EPSG:4326", origin=(77.0, 13.0), res=0.0001)
    return a, b


@pytest.fixture
def geotiff_no_crs(tmp_path):
    return _write(tmp_path / "nocrs.tif", crs=None, nodata=None)


@pytest.fixture
def not_a_raster(tmp_path):
    p = tmp_path / "junk.tif"
    p.write_bytes(b"this is not a tiff")
    return str(p)
