"""End-to-end test for the temporal vertical slice.

Slow: subprocesses into .venvs/changeformer. Skips cleanly if the env/checkpoint
or demo data are absent.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.services.temporal_slice import ChangeSliceResult, run_change_slice

_REPO = Path(__file__).resolve().parents[3]
_CKPT = _REPO / "models/cache/changeformer/CD_ChangeFormerV6_LEVIR_b16_lr0.0001_adamw_train_test_200_linear_ce_multi_train_True_multi_infer_False_shuffle_AB_False_embed_dim_256"
_DEMO = _REPO / "data/demo/temporal"

_have_env = (_REPO / ".venvs/changeformer/Scripts/python.exe").exists() and (_CKPT / "best_ckpt.pt").exists()
pytestmark = pytest.mark.skipif(not (_have_env and _DEMO.exists()), reason="changeformer env / demo data absent")


@pytest.mark.slow
def test_happy_path_produces_structured_result(tmp_path):
    r = run_change_slice(_DEMO / "t1.tif", _DEMO / "t2.tif",
                         checkpoint_dir=_CKPT, artifact_dir=tmp_path)
    assert isinstance(r, ChangeSliceResult)
    assert r.ok is True
    assert r.t1_valid and r.t2_valid
    assert r.pair.co_registered is True
    assert r.stats.changed_pixels > 0
    assert 0.0 < r.stats.changed_fraction < 1.0
    # projected CRS (EPSG:32650, metres) -> area is computed
    assert r.stats.changed_area_m2 is not None and r.stats.changed_area_m2 > 0
    assert r.stats.change_bbox_lonlat is not None
    # provenance is threaded, and score is NOT a confidence
    assert r.provenance["stages"][0] == "validate_geotiff"
    assert r.provenance["adapter_provenance"]["checkpoint_sha256"]
    assert "not a confidence" in r.provenance["score_meaning"]


@pytest.mark.slow
def test_misregistered_pair_is_blocked_when_strict():
    r = run_change_slice(_DEMO / "t1.tif", _DEMO / "t2_shifted.tif", checkpoint_dir=_CKPT, strict=True)
    assert r.ok is False
    assert r.pair.co_registered is False
    assert any("co-registered" in e for e in r.errors)
    assert r.stats is None  # no inference was run


@pytest.mark.slow
def test_change_slice_emits_evidence_and_verification():
    """G3 regression: existing /change behaviour + new evidence/verification fields."""
    r = run_change_slice(_DEMO / "t1.tif", _DEMO / "t2.tif", checkpoint_dir=_CKPT)
    assert r.ok is True
    # existing behaviour unchanged
    assert 0.24 < r.stats.changed_fraction < 0.27  # matches G1 demo_LEVIR.py (~0.253)
    assert r.stats.changed_area_ha is not None
    # new: structured evidence
    assert len(r.evidence) == 1
    ev = r.evidence[0]
    assert ev.evidence_type == "change-mask"
    assert ev.source_model == "changeformer"
    assert ev.temporal_context and ev.temporal_context["relation"] == "T1 before T2"
    assert "confidence" not in ev.model_dump()
    # new: deterministic verification
    assert r.verification.status == "SUPPORTED"
    assert {"geospatial_compatibility"} <= {c.name for c in r.verification.checks}
    # new: standardized provenance alongside the legacy block
    assert r.provenance["standardized"]["model"] == "changeformer"
    assert "checkpoint_sha256" in r.provenance["adapter_provenance"]
