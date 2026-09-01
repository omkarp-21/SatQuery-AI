"""COMPOSED_SEMANTIC_CHANGE_BASELINE - contract + failure-case tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.services.semantic_change_baseline import (
    BASELINE_NAME,
    ComposedSemanticChangeResult,
    run_composed_semantic_change,
)
from app.services import semantic_change_baseline as _scb

_REPO = Path(__file__).resolve().parents[3]
_CF = _REPO / ("models/cache/changeformer/CD_ChangeFormerV6_LEVIR_b16_lr0.0001_adamw"
               "_train_test_200_linear_ce_multi_train_True_multi_infer_False_shuffle_AB_False_embed_dim_256")
_DEMO = _REPO / "data/demo/temporal"
_ENV = ((_CF / "best_ckpt.pt").exists()
        and (_REPO / "models/cache/remoteclip/RemoteCLIP-ViT-B-32.pt").exists()
        and _DEMO.exists())


def test_name_is_exact():
    assert BASELINE_NAME == "COMPOSED_SEMANTIC_CHANGE_BASELINE"


def test_misregistered_pair_returns_error_not_raise():
    r = run_composed_semantic_change(_DEMO / "t1.tif", _DEMO / "t2_shifted.tif", checkpoint_dir=_CF)
    assert isinstance(r, ComposedSemanticChangeResult)
    assert r.ok is False and r.errors


@pytest.mark.slow
@pytest.mark.skipif(not _ENV, reason="changeformer/remoteclip/demo absent")
def test_composed_baseline_happy_path():
    r = run_composed_semantic_change(_DEMO / "t1.tif", _DEMO / "t2.tif", checkpoint_dir=_CF)
    assert r.ok is True
    assert r.baseline_name == "COMPOSED_SEMANTIC_CHANGE_BASELINE"
    assert "NOT a temporal VLM" in r.disclaimer
    assert "NOT validated semantic reasoning" in r.disclaimer
    assert r.changed_area_ha and r.changed_area_ha > 0
    assert 1 <= len(r.regions) <= 6
    assert r.description and "Region 1" in r.description
    # evidence: 1 mask + one per tagged region
    kinds = [e.evidence_type for e in r.evidence]
    assert kinds[0] == "change-mask" and kinds.count("ranking") == sum(1 for x in r.regions if x.top_tag)
    assert r.verification.status in ("SUPPORTED", "CONTRADICTED", "INSUFFICIENT_EVIDENCE")
    assert "not calibrated" in r.provenance["note"] or "not calibrated labels" in r.provenance["note"]
    # no confidence field anywhere
    assert "confidence" not in r.model_dump()


def test_crop_strategy_default_is_tight_and_signature_accepts_it():
    import inspect

    sig = inspect.signature(run_composed_semantic_change)
    assert sig.parameters["crop_strategy"].default == "tight"
    # the literal type advertises exactly the three strategies
    assert set(_scb.CropStrategy.__args__) == {"tight", "expanded", "mask_aware"}


def test_result_model_exposes_semantic_verification_field():
    # additive field (EXP-005b) - present, optional, defaults to None
    assert "semantic_verification" in ComposedSemanticChangeResult.model_fields
    assert ComposedSemanticChangeResult(ok=False).semantic_verification is None


@pytest.mark.slow
@pytest.mark.skipif(not _ENV, reason="changeformer/remoteclip/demo absent")
def test_semantic_verification_runs_on_happy_path():
    r = run_composed_semantic_change(_DEMO / "t1.tif", _DEMO / "t2.tif", checkpoint_dir=_CF,
                                     max_regions=3)
    assert r.ok is True
    assert r.semantic_verification is not None
    assert r.semantic_verification.status in (
        "COHERENT", "INCOHERENT", "NOT_ENOUGH_EVIDENCE", "NOT_APPLICABLE")
    # the composed baseline's own assembled description should be internally coherent
    assert r.semantic_verification.status in ("COHERENT", "NOT_ENOUGH_EVIDENCE")
    assert "verify_semantic" in r.provenance["stages"]


@pytest.mark.slow
@pytest.mark.skipif(not _ENV, reason="changeformer/remoteclip/demo absent")
def test_crop_strategy_threads_into_provenance():
    r = run_composed_semantic_change(_DEMO / "t1.tif", _DEMO / "t2.tif", checkpoint_dir=_CF,
                                     crop_strategy="expanded", max_regions=2)
    assert r.ok is True
    assert r.provenance["crop_strategy"] == "expanded"
    assert any("region_crop[expanded]" in s for s in r.provenance["stages"])


@pytest.mark.slow
@pytest.mark.skipif(not _ENV, reason="changeformer/remoteclip/demo absent")
def test_failure_cases_are_logged_not_raised():
    # tiny max_regions still succeeds; failures list exists (may be empty)
    r = run_composed_semantic_change(_DEMO / "t1.tif", _DEMO / "t2.tif", checkpoint_dir=_CF,
                                     max_regions=1)
    assert r.ok is True
    assert isinstance(r.failures, list)
    assert len(r.regions) == 1
