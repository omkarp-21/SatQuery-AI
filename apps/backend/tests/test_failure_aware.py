"""Failure-aware routing (G8 Phase 10) — the deterministic post-execution qualifier
and the single-step image-difference fallback."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.services.failure_aware import derive_resolution
from satquery_evidence import EvidenceItem, verify, verify_semantic

_REPO = Path(__file__).resolve().parents[3]
_DEMO = _REPO / "data" / "demo" / "temporal"


def _mask_ev(cf: float):
    return EvidenceItem(source_model="changeformer", task="change-detection",
                        modality="optical-bitemporal", claim_supported="pixels changed",
                        evidence_type="change-mask",
                        payload={"mask_path": "/m.png", "changed_fraction": cf})


# ---------- derive_resolution: one test per qualifier ----------
def test_result_ok_when_structural_supported():
    vr = verify({}, [_mask_ev(0.25)], {"pair_co_registered": True})
    r = derive_resolution(sub_ok=True, verification=vr)
    assert r.qualifier == "RESULT_OK" and r.answer_surfaced is True and r.disputed is False


def test_structural_fail_withholds_answer():
    vr = verify({}, [_mask_ev(1.9)], {"pair_co_registered": True})
    r = derive_resolution(sub_ok=True, verification=vr)
    assert r.qualifier == "RESULT_STRUCTURAL_FAIL"
    assert r.answer_surfaced is False
    assert r.reasons  # the failed check names


def test_semantic_incoherent_disputes_answer():
    sv = verify_semantic({"description": "Detected change over ~90% of the scene."},
                         [_mask_ev(0.10)], {})
    vr = verify({}, [_mask_ev(0.10)], {"pair_co_registered": True})
    r = derive_resolution(sub_ok=True, verification=vr, semantic_verification=sv)
    assert r.qualifier == "RESULT_SEMANTIC_INCOHERENT"
    assert r.answer_surfaced is False and r.disputed is True


def test_unverified_when_no_checks_apply():
    r = derive_resolution(sub_ok=True, verification=None, semantic_verification=None)
    assert r.qualifier == "RESULT_UNVERIFIED" and r.answer_surfaced is True


def test_degraded_when_fallback_used():
    vr = verify({}, [_mask_ev(0.3)], {"pair_co_registered": True})
    r = derive_resolution(sub_ok=True, verification=vr, fallback_used="image_difference_fallback")
    assert r.qualifier == "SPECIALIST_DEGRADED"
    assert r.answer_surfaced is True and r.fallback_used == "image_difference_fallback"


def test_specialist_failed_when_sub_not_ok_and_no_fallback():
    r = derive_resolution(sub_ok=False, verification=None)
    assert r.qualifier == "SPECIALIST_FAILED" and r.answer_surfaced is False


def test_no_loop_no_recursion_pure_function():
    # calling twice with the same inputs yields identical output (deterministic)
    vr = verify({}, [_mask_ev(0.25)], {"pair_co_registered": True})
    a = derive_resolution(sub_ok=True, verification=vr)
    b = derive_resolution(sub_ok=True, verification=vr)
    assert a.model_dump() == b.model_dump()


def test_qualifier_is_not_a_confidence():
    vr = verify({}, [_mask_ev(0.25)], {"pair_co_registered": True})
    r = derive_resolution(sub_ok=True, verification=vr)
    assert "NOT a confidence" in r.note


# ---------- image-difference fallback ----------
def test_fallback_rejects_misregistered_pair():
    from app.services.temporal_slice import run_change_fallback

    r = run_change_fallback(_DEMO / "t1.tif", _DEMO / "t2_shifted.tif")
    assert r.ok is False
    assert any("co-registered" in e for e in r.errors)


@pytest.mark.skipif(not (_DEMO / "t1.tif").exists(), reason="demo pair absent")
def test_fallback_produces_a_mask_on_the_demo_pair():
    from app.services.temporal_slice import run_change_fallback

    r = run_change_fallback(_DEMO / "t1.tif", _DEMO / "t2.tif")
    assert r.ok is True
    assert r.stats is not None
    assert 0.0 <= r.stats.changed_fraction <= 1.0
    assert r.provenance["is_fallback"] is True
    assert r.provenance["model"] == "image_difference_fallback"
    # structural verification still runs on the fallback result
    assert r.verification is not None
    assert r.verification.status in ("SUPPORTED", "CONTRADICTED", "INSUFFICIENT_EVIDENCE")
    # this is NOT ChangeFormer quality
    assert "NOT ChangeFormer quality" in r.provenance["score_meaning"]
