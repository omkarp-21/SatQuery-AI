"""Transform + contract + failure tests for the geospatial vertical slice."""

from __future__ import annotations

import pytest

from satquery_geospatial import (
    GeoValidationResult,
    PairCompatibility,
    RasterMeta,
    RasterTooLargeError,
    UnreadableRasterError,
    check_pair_compatibility,
    read_raster_meta,
    validate_geotiff,
)


# --- read_raster_meta ---------------------------------------------------------

def test_read_meta_transform(tiny_geotiff):
    m = read_raster_meta(tiny_geotiff)
    assert isinstance(m, RasterMeta)
    assert (m.width, m.height, m.count) == (8, 8, 3)
    assert m.crs == "EPSG:32643"
    assert m.crs_epsg == 32643
    assert m.is_projected is True
    assert m.res == (10.0, 10.0)
    assert m.nodata == 0.0
    assert m.band_descriptions == ["band1", "band2", "band3"]
    # bounds derived from origin (600000, 1500000), 10 m, 8 px
    assert m.bounds == (600000.0, 1499920.0, 600080.0, 1500000.0)


def test_read_meta_contract_is_serializable(tiny_geotiff):
    m = read_raster_meta(tiny_geotiff)
    round_trip = RasterMeta.model_validate_json(m.model_dump_json())
    assert round_trip == m


def test_read_meta_no_crs(geotiff_no_crs):
    m = read_raster_meta(geotiff_no_crs)
    assert m.crs is None and m.crs_epsg is None
    assert m.nodata is None


# --- validate_geotiff -------------------------------------------------------

def test_validate_ok(tiny_geotiff):
    r = validate_geotiff(tiny_geotiff)
    assert isinstance(r, GeoValidationResult)
    assert r.ok is True
    names = {c.name for c in r.checks}
    assert {"format_readable", "dimensions", "bands", "crs_present", "transform_valid",
            "bounds", "nodata"} <= names
    assert r.failed() == []


def test_validate_no_crs_warns_but_passes_by_default(geotiff_no_crs):
    r = validate_geotiff(geotiff_no_crs)
    assert r.ok is True  # CRS not required by default
    assert any("no CRS" in w or "NoData" in w for w in r.warnings)


def test_validate_no_crs_fails_when_required(geotiff_no_crs):
    r = validate_geotiff(geotiff_no_crs, require_crs=True)
    assert r.ok is False
    assert any(c.name == "crs_present" and not c.passed for c in r.checks)


def test_validate_failure_not_a_raster(not_a_raster):
    with pytest.raises(UnreadableRasterError):
        validate_geotiff(not_a_raster)


def test_validate_failure_missing_file(tmp_path):
    with pytest.raises(UnreadableRasterError):
        validate_geotiff(tmp_path / "does_not_exist.tif")


def test_validate_failure_pixel_budget(tiny_geotiff):
    with pytest.raises(RasterTooLargeError):
        validate_geotiff(tiny_geotiff, max_pixels=10)


def test_validate_failure_band_budget(tiny_geotiff):
    with pytest.raises(RasterTooLargeError):
        validate_geotiff(tiny_geotiff, max_bands=1)


# --- check_pair_compatibility --------------------------------------------------

def test_pair_aligned_is_co_registered(tiny_pair_aligned):
    a, b = tiny_pair_aligned
    pc = check_pair_compatibility(read_raster_meta(a), read_raster_meta(b))
    assert isinstance(pc, PairCompatibility)
    assert pc.co_registered is True
    assert pc.mismatches == []


def test_pair_misregistered_detected(tiny_pair_misregistered):
    a, b = tiny_pair_misregistered
    pc = check_pair_compatibility(read_raster_meta(a), read_raster_meta(b))
    assert pc.co_registered is False
    assert pc.same_shape is True and pc.same_crs is True
    assert pc.same_transform is False
    assert any("transform" in m for m in pc.mismatches)


def test_pair_crs_mismatch_detected(tiny_pair_crs_mismatch):
    a, b = tiny_pair_crs_mismatch
    pc = check_pair_compatibility(read_raster_meta(a), read_raster_meta(b))
    assert pc.co_registered is False
    assert pc.same_crs is False
    assert any("CRS" in m for m in pc.mismatches)
