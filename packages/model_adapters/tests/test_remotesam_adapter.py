"""RemoteSAM adapter contract tests (fast - no model load)."""

from __future__ import annotations

from pathlib import Path

import pytest

from satquery_model_adapters import ADAPTERS, AdapterRequest, RemoteSamAdapter
from satquery_model_adapters.errors import (
    AdapterConfigError,
    AdapterExecutionError,
    UnsupportedTaskError,
)

_REPO = Path(__file__).resolve().parents[3]
_CKPT = _REPO / "models/cache/remotesam/RemoteSAM/RemoteSAMv1.pth"
_IMG = _REPO / "data/demo/temporal/t1.tif"


def _a(**kw):
    return RemoteSamAdapter(checkpoint=str(kw.pop("checkpoint", _CKPT)), **kw)


def test_registered_and_metadata():
    assert ADAPTERS["remotesam"] is RemoteSamAdapter
    a = _a()
    assert a.name == "remotesam"
    assert a.capabilities == ("grounding", "referring-segmentation")
    assert a.modalities == ("optical-single",)
    assert "NOT STATED" in a.license  # honest about the missing upstream licence


def test_rejects_vqa_task():
    a = _a()
    with pytest.raises(UnsupportedTaskError):
        a.validate(AdapterRequest(query="how many planes?", images=[str(_IMG)],
                                  context={"task": "vqa"}))


def test_rejects_captioning_task():
    a = _a()
    with pytest.raises(UnsupportedTaskError):
        a.validate(AdapterRequest(query="describe the scene", images=[str(_IMG)],
                                  context={"task": "captioning"}))


def test_rejects_two_images():
    a = _a()
    with pytest.raises(AdapterExecutionError):
        a.validate(AdapterRequest(query="the runway", images=[str(_IMG), str(_IMG)],
                                  context={"task": "grounding"}))


def test_rejects_empty_phrase():
    a = _a()
    with pytest.raises(AdapterExecutionError):
        a.validate(AdapterRequest(query="   ", images=[str(_IMG)], context={"task": "grounding"}))


def test_missing_image_is_execution_error():
    a = _a()
    with pytest.raises(AdapterExecutionError):
        a.validate(AdapterRequest(query="the runway", images=["/no/such.jpg"],
                                  context={"task": "grounding"}))


def test_missing_checkpoint_is_config_error():
    a = _a(checkpoint="/no/such/RemoteSAMv1.pth")
    # image + phrase valid, but the checkpoint path does not exist
    if not _IMG.exists():
        pytest.skip("demo image absent")
    with pytest.raises(AdapterConfigError):
        a.validate(AdapterRequest(query="the runway", images=[str(_IMG)],
                                  context={"task": "grounding"}))
