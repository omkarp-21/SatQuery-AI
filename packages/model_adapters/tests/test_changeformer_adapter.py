"""ChangeFormer adapter - contract/failure tests (fast) + one slow real-inference smoke."""

from __future__ import annotations

from pathlib import Path

import pytest

from satquery_model_adapters import (
    ADAPTERS,
    AdapterConfigError,
    AdapterExecutionError,
    AdapterRequest,
    ChangeFormerAdapter,
    UnsupportedTaskError,
)

_REPO = Path(__file__).resolve().parents[3]
_CKPT = _REPO / "models/cache/changeformer/CD_ChangeFormerV6_LEVIR_b16_lr0.0001_adamw_train_test_200_linear_ce_multi_train_True_multi_infer_False_shuffle_AB_False_embed_dim_256"
_DEMO = _REPO / "data/demo/temporal"


def test_registered_and_describes_facts():
    assert ADAPTERS["changeformer"] is ChangeFormerAdapter
    d = ChangeFormerAdapter(checkpoint=str(_CKPT)).describe()
    assert d["capabilities"] == ["change-detection"]
    assert d["modalities"] == ["optical-bitemporal"]
    assert d["license"] == "MIT"
    assert d["source_repo"].endswith("ChangeFormer")


def test_unsupported_task_raises_not_approximated():
    a = ChangeFormerAdapter(checkpoint=str(_CKPT))
    with pytest.raises(UnsupportedTaskError):
        a.run(AdapterRequest(query="describe the change", images=["x", "y"],
                             context={"task": "change-captioning"}))


def test_wrong_image_count_raises():
    a = ChangeFormerAdapter(checkpoint=str(_CKPT))
    with pytest.raises(AdapterExecutionError):
        a.run(AdapterRequest(query="change", images=["only_one.tif", "and", "three"]))


def test_missing_input_is_execution_error():
    a = ChangeFormerAdapter(checkpoint=str(_CKPT))
    with pytest.raises(AdapterExecutionError):
        a.run(AdapterRequest(images=["nope_a.tif", "nope_b.tif"], context={"task": "change-detection"}))


def test_missing_checkpoint_is_config_error(tmp_path):
    a = ChangeFormerAdapter(checkpoint=str(tmp_path))  # no best_ckpt.pt inside
    (tmp_path / "a.tif").write_bytes(b"x")
    (tmp_path / "b.tif").write_bytes(b"x")
    with pytest.raises(AdapterConfigError):
        a.run(AdapterRequest(images=[str(tmp_path / "a.tif"), str(tmp_path / "b.tif")],
                             context={"task": "change-detection"}))


@pytest.mark.slow
def test_smoke_real_inference():
    if not (_REPO / ".venvs/changeformer/Scripts/python.exe").exists():
        pytest.skip("changeformer venv not present")
    if not (_CKPT / "best_ckpt.pt").exists():
        pytest.skip("changeformer checkpoint not downloaded")
    a = ChangeFormerAdapter(checkpoint=str(_CKPT))
    r = a.run(AdapterRequest(
        query="detect change",
        images=[str(_DEMO / "t1.tif"), str(_DEMO / "t2.tif")],
        context={"task": "change-detection"},
    ))
    assert r.model == "changeformer"
    assert r.answer["changed_pixels"] > 0
    assert 0.0 <= r.score <= 1.0
    assert r.provenance["checkpoint_sha256"]
    assert r.provenance["license"] == "MIT"
    assert "confidence" in r.provenance["score_meaning"].lower()
    assert "not" in r.provenance["score_meaning"].lower()
