"""Internal optical-SAR joint-representation contract (no public endpoint)."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.services.multimodal_slice import JointReprResult, run_joint_representation

_REPO = Path(__file__).resolve().parents[3]
_CROMA_OK = (_REPO / "models/cache/croma/CROMA_base.pt").exists() and (
    _REPO / ".venvs/croma/Scripts/python.exe"
).exists()
_DOFA_OK = (_REPO / "models/cache/dofa/DOFA_ViT_base_e100.pth").exists() and (
    _REPO / ".venvs/dofa/Scripts/python.exe"
).exists()


def test_missing_inputs_returns_error_not_raise():
    r = run_joint_representation("no_opt.npy", "no_sar.npy", model="croma")
    assert isinstance(r, JointReprResult)
    assert r.ok is False and r.errors


def test_result_carries_the_disclaimer():
    r = run_joint_representation("x", "y", model="croma")
    assert "NOT full optical-SAR reasoning" in r.note


@pytest.mark.slow
@pytest.mark.skipif(not _CROMA_OK, reason="croma env/ckpt absent")
def test_croma_joint_repr_smoke():
    r = run_joint_representation(None, None, model="croma", smoke_random=True)
    assert r.ok is True and r.model == "croma"
    assert r.representation["dim"] == 768
    assert len(r.representation["joint_gap"]) == 768
    assert r.evidence[0].evidence_type == "embedding"
    assert r.verification.status in ("SUPPORTED", "NOT_APPLICABLE")
    assert r.provenance["model"] == "croma"
    assert "confidence" not in r.model_dump()  # representation only


@pytest.mark.slow
@pytest.mark.skipif(not _DOFA_OK, reason="dofa env/ckpt absent")
def test_dofa_repr_smoke():
    r = run_joint_representation(None, None, model="dofa", smoke_random=True)
    assert r.ok is True and r.model == "dofa"
    assert r.representation["dim"] == 768
