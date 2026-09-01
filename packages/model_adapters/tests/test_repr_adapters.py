"""RemoteCLIP / CROMA / DOFA adapters - fast contract tests + slow real smokes."""

from __future__ import annotations

from pathlib import Path

import pytest

from satquery_model_adapters import (
    ADAPTERS,
    AdapterRequest,
    CromaAdapter,
    DofaAdapter,
    RemoteClipAdapter,
    UnsupportedModalityError,
    UnsupportedTaskError,
)

_REPO = Path(__file__).resolve().parents[3]
_RC_CKPT = _REPO / "models/cache/remoteclip/RemoteCLIP-ViT-B-32.pt"
_CROMA_CKPT = _REPO / "models/cache/croma/CROMA_base.pt"
_DOFA_CKPT = _REPO / "models/cache/dofa/DOFA_ViT_base_e100.pth"
_RC_IMG = _REPO / "external/research/RemoteCLIP/assets/airport.jpg"


def test_all_four_registered():
    assert set(ADAPTERS) == {"changeformer", "remoteclip", "croma", "dofa"}


def test_remoteclip_rejects_vqa():
    a = RemoteClipAdapter(checkpoint=str(_RC_CKPT))
    with pytest.raises(UnsupportedTaskError):
        a.run(AdapterRequest(query="what is this?", images=["x.jpg"], context={"task": "vqa"}))


def test_croma_rejects_single_modality():
    a = CromaAdapter(checkpoint=str(_CROMA_CKPT))
    with pytest.raises(UnsupportedModalityError):
        a.run(AdapterRequest(images=["only_s2.npy"], context={"task": "embedding"}))


def test_dofa_requires_modality():
    a = DofaAdapter(checkpoint=str(_DOFA_CKPT))
    with pytest.raises(UnsupportedModalityError):
        a.run(AdapterRequest(images=["x.npy"], context={"task": "embedding"}))


@pytest.mark.slow
@pytest.mark.skipif(not (_RC_CKPT.exists() and _RC_IMG.exists()
                         and (_REPO / ".venvs/remoteclip/Scripts/python.exe").exists()),
                    reason="remoteclip env/ckpt absent")
def test_remoteclip_smoke():
    a = RemoteClipAdapter(checkpoint=str(_RC_CKPT))
    r = a.run(AdapterRequest(query="an airport; a farm; a harbour", images=[str(_RC_IMG)],
                             context={"task": "zero-shot-classification"}))
    assert r.answer["top_label"] == "an airport"
    assert 0.0 <= r.score <= 1.0
    assert r.provenance["license"] == "Apache-2.0"


@pytest.mark.slow
@pytest.mark.skipif(not (_CROMA_CKPT.exists() and (_REPO / ".venvs/croma/Scripts/python.exe").exists()),
                    reason="croma env/ckpt absent")
def test_croma_smoke_random():
    a = CromaAdapter(checkpoint=str(_CROMA_CKPT))
    r = a.run(AdapterRequest(context={"task": "embedding", "random": 1}))
    assert r.answer["dim"] == 768
    assert len(r.answer["joint_gap"]) == 768
    assert r.score is None
    assert r.provenance["license"] == "MIT"


@pytest.mark.slow
@pytest.mark.skipif(not (_DOFA_CKPT.exists() and (_REPO / ".venvs/dofa/Scripts/python.exe").exists()),
                    reason="dofa env/ckpt absent")
def test_dofa_smoke_random():
    a = DofaAdapter(checkpoint=str(_DOFA_CKPT))
    r = a.run(AdapterRequest(context={"task": "embedding", "modality": "s1", "random": 1}))
    assert r.answer["dim"] == 768
    assert r.answer["modality"] == "s1"
    assert r.provenance["license"] == "MIT"
