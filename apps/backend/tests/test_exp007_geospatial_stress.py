"""EXP-007 - geospatial safeguard stress test.

Battery of malformed / pathological inputs against validate_geotiff +
check_pair_compatibility + the /change gate. Safeguards are asserted, NOT weakened.
Results are also summarized in docs/research/EXP-007.md.
"""

from __future__ import annotations

import numpy as np
import pytest
import rasterio
from rasterio.transform import Affine, from_origin

from satquery_geospatial import (
    RasterTooLargeError,
    UnreadableRasterError,
    check_pair_compatibility,
    read_raster_meta,
    validate_geotiff,
)


def _tif(path, *, w=8, h=8, count=3, crs="EPSG:32643", origin=(6e5, 15e5), res=10.0,
         nodata=0.0, dtype="uint8", transform=None):
    tr = transform or from_origin(origin[0], origin[1], res, res)
    prof = dict(driver="GTiff", width=w, height=h, count=count, dtype=dtype, crs=crs,
                transform=tr, nodata=nodata)
    with rasterio.open(path, "w", **prof) as ds:
        ds.write((np.arange(w * h * count) % 255).reshape(count, h, w).astype(dtype))
    return str(path)


# --- single-raster validation ------------------------------------------------

def test_valid_raster_passes(tmp_path):
    r = validate_geotiff(_tif(tmp_path / "ok.tif"))
    assert r.ok and r.failed() == []


def test_missing_crs_warns_and_can_fail_when_required(tmp_path):
    p = _tif(tmp_path / "nocrs.tif", crs=None, nodata=None)
    assert validate_geotiff(p).ok is True                       # tolerated by default
    assert validate_geotiff(p, require_crs=True).ok is False     # enforced on demand


def test_identity_transform_flagged(tmp_path):
    p = _tif(tmp_path / "ident.tif", transform=Affine.identity())
    r = validate_geotiff(p)
    assert any(c.name == "transform_valid" and not c.passed for c in r.checks)
    assert any("identity" in w.lower() for w in r.warnings)


def test_invalid_raster_raises(tmp_path):
    (tmp_path / "junk.tif").write_bytes(b"not a raster")
    with pytest.raises(UnreadableRasterError):
        validate_geotiff(tmp_path / "junk.tif")


def test_missing_file_raises(tmp_path):
    with pytest.raises(UnreadableRasterError):
        validate_geotiff(tmp_path / "ghost.tif")


def test_decompression_bomb_guard_pixels(tmp_path):
    with pytest.raises(RasterTooLargeError):
        validate_geotiff(_tif(tmp_path / "ok.tif"), max_pixels=10)


def test_decompression_bomb_guard_bands(tmp_path):
    with pytest.raises(RasterTooLargeError):
        validate_geotiff(_tif(tmp_path / "ok.tif"), max_bands=1)


def test_path_traversal_rejected(tmp_path):
    from satquery_geospatial.errors import PathNotAllowedError
    base = tmp_path / "allowed"
    base.mkdir()
    outside = _tif(tmp_path / "outside.tif")
    with pytest.raises(PathNotAllowedError):
        validate_geotiff(outside, allowed_base_dir=base)


def test_nodata_absence_is_a_warning_not_a_failure(tmp_path):
    r = validate_geotiff(_tif(tmp_path / "nnd.tif", nodata=None))
    assert r.ok is True
    assert any("NoData" in w for w in r.warnings)


# --- pair compatibility ----------------------------------------------------

def test_pair_identical_is_co_registered(tmp_path):
    a = read_raster_meta(_tif(tmp_path / "a.tif"))
    b = read_raster_meta(_tif(tmp_path / "b.tif"))
    assert check_pair_compatibility(a, b).co_registered is True


def test_pair_crs_mismatch_detected(tmp_path):
    a = read_raster_meta(_tif(tmp_path / "a.tif", crs="EPSG:32643"))
    b = read_raster_meta(_tif(tmp_path / "b.tif", crs="EPSG:4326", origin=(77.0, 13.0), res=1e-4))
    pc = check_pair_compatibility(a, b)
    assert pc.co_registered is False and pc.same_crs is False


def test_pair_transform_mismatch_detected(tmp_path):
    a = read_raster_meta(_tif(tmp_path / "a.tif", origin=(6e5, 15e5)))
    b = read_raster_meta(_tif(tmp_path / "b.tif", origin=(6e5 + 50, 15e5)))
    pc = check_pair_compatibility(a, b)
    assert pc.co_registered is False and pc.same_transform is False


def test_pair_shape_mismatch_detected(tmp_path):
    a = read_raster_meta(_tif(tmp_path / "a.tif", w=8, h=8))
    b = read_raster_meta(_tif(tmp_path / "b.tif", w=16, h=8))
    pc = check_pair_compatibility(a, b)
    assert pc.co_registered is False and pc.same_shape is False


def test_pair_resolution_mismatch_detected(tmp_path):
    a = read_raster_meta(_tif(tmp_path / "a.tif", res=10.0))
    b = read_raster_meta(_tif(tmp_path / "b.tif", res=20.0))
    pc = check_pair_compatibility(a, b)
    assert pc.same_resolution is False


# --- /change gate end-to-end (safeguard must block, not pass) -------------

@pytest.mark.slow
def test_change_gate_blocks_misregistered_pair():
    from pathlib import Path

    from app.services.temporal_slice import run_change_slice

    repo = Path(__file__).resolve().parents[3]
    ckpt = repo / ("models/cache/changeformer/CD_ChangeFormerV6_LEVIR_b16_lr0.0001_adamw"
                   "_train_test_200_linear_ce_multi_train_True_multi_infer_False_shuffle_AB_False_embed_dim_256")
    demo = repo / "data/demo/temporal"
    if not (ckpt / "best_ckpt.pt").exists() or not demo.exists():
        pytest.skip("changeformer ckpt / demo data absent")
    r = run_change_slice(demo / "t1.tif", demo / "t2_shifted.tif", checkpoint_dir=ckpt, strict=True)
    assert r.ok is False and r.stats is None
    assert any("co-registered" in e for e in r.errors)
