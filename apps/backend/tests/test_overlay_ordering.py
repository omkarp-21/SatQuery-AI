"""Uncommitted-work regression tests: content-based input ordering + overlay preview.

Covers the G20.1+ working-tree changes before they are merged to master:
- ``order_investigation_inputs`` restores the planner contract (T1/T2 first,
  SAR last) regardless of browser upload order.
- ``build_investigation_overlay`` burns a PNG preview from executed specialist
  outputs only (T2 + change mask + grounding box); no mask/box -> no overlay.
"""

from __future__ import annotations

import numpy as np
import rasterio
from rasterio.transform import from_origin

from app.services.agent_runner import order_investigation_inputs
from app.services.overlay import build_investigation_overlay


def _tif(path, *, w, h, count=3):
    prof = dict(
        driver="GTiff",
        width=w,
        height=h,
        count=count,
        dtype="uint8",
        crs="EPSG:32643",
        transform=from_origin(6e5, 15e5, 10.0, 10.0),
        nodata=0,
    )
    with rasterio.open(path, "w", **prof) as ds:
        ds.write(np.zeros((count, h, w), dtype="uint8"))
    return str(path)


def test_single_input_returned_unchanged(tmp_path):
    p = _tif(tmp_path / "only.tif", w=16, h=16)
    assert order_investigation_inputs([p]) == [p]
    assert order_investigation_inputs([]) == []


def test_sar_goes_last_and_pair_goes_first(tmp_path):
    t1 = _tif(tmp_path / "t1_optical.tif", w=32, h=32, count=3)
    t2 = _tif(tmp_path / "t2_optical.tif", w=32, h=32, count=3)
    # S2 optical is 13-band in the real demo, so it never joins the 3-band
    # T1/T2 pair group even on the same grid.
    s2 = _tif(tmp_path / "s2_dfc_optical.tif", w=32, h=32, count=13)
    sar = _tif(tmp_path / "s1_dfc_sar.tif", w=32, h=32, count=2)
    # browser alphabetical upload order: s1, s2, t1, t2
    shuffled = [sar, s2, t1, t2]
    ordered = order_investigation_inputs(shuffled)
    assert ordered[-1] == sar
    assert ordered[0] == t1 and ordered[1] == t2
    assert ordered[2] == s2


def test_overlay_renders_base_and_box(tmp_path):
    t2 = _tif(tmp_path / "t2.tif", w=32, h=32, count=3)
    out = tmp_path / "overlay.png"
    # base T2 alone renders (the investigate endpoint decides whether an
    # overlay is warranted: mask exists or grounding box present).
    got = build_investigation_overlay(t2, None, None, None, out)
    assert got is not None
    assert out.exists()

    # box alone is enough to produce a preview
    got = build_investigation_overlay(
        t2, None, [4, 4, 20, 20], [32, 32], out
    )
    assert got is not None
    assert out.exists()
