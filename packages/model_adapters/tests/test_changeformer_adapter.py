"""ChangeFormer adapter — fast contract/failure tests (no venv needed) + one
slow smoke test that actually subprocesses to the research env."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from satquery_model_adapters.base import AdapterRequest
from satquery_model_adapters.changeformer import ChangeFormerAdapter
from satquery_model_adapters.errors import (
    AdapterConfigError,
    AdapterExecutionError,
    UnsupportedTaskError,
)

_REPO = Path(__file__).resolve().parents[3]
_CKPT = _REPO / "models/cache/changeformer/CD_ChangeFormerV6_LEVIR_b16_lr0.0001_adamw_train_test_200_linear_ce_multi_train_True_multi_infer_False_shuffle_AB_False_embed_dim_256"
_DEMO = _REPO / "data/demo/temporal"


def test_capabilities():
    a = ChangeFormerAdapter(checkpoint=str(_CKPT))
    caps = a.capabilities()
    assert caps["tasks"] == ("change-detection",)
    assert caps["modalities"] == ("optical-bitemporal",)


def test_unsupported_task_raises_not_approximated():
    a = ChangeFormerAdapter(checkpoint=str(_CKPT))
    with pytest.raises(UnsupportedTaskError):
        a.predict(AdapterRequest(query="describe the change", images=["x", "y"],
                                 context={"task": "change-captioning"}))


def test_wrong_image_count_raises():
    a = ChangeFormerAdapter(checkpoint=str(_CKPT))
    with pytest.raises(AdapterExecutionError):
        a.predict(AdapterRequest(query="change", images=["only_one.tif"]))


def test_missing_venv_is_config_error(tmp_path):
    a = ChangeFormerAdapter(checkpoint=str(_CKPT), venv_python=str(tmp_path / "nope.exe"))
    with pytest.raises(AdapterConfigError):
        a.load()


@pytest.mark.slow
def test_smoke_real_inference():
    """Subprocess into .venvs/changeformer and run one real pair."""
    if not (_REPO / ".venvs/changeformer/Scripts/python.exe").exists():
        pytest.skip("changeformer venv not present")
    if not (_CKPT / "best_ckpt.pt").exists():
        pytest.skip("changeformer checkpoint not downloaded")
    a = ChangeFormerAdapter(checkpoint=str(_CKPT))
    r = a.predict(AdapterRequest(
        query="detect change",
        images=[str(_DEMO / "t1.tif"), str(_DEMO / "t2.tif")],
        context={"task": "change-detection", "artifact_dir": None},
    ))
    assert r.model == "changeformer"
    assert 0.0 <= r.answer["changed_fraction"] <= 1.0
    assert r.answer["changed_pixels"] > 0  # this demo pair has real change
    assert r.provenance["checkpoint_sha256"]
    assert "not a confidence" in r.provenance["score_meaning"]
