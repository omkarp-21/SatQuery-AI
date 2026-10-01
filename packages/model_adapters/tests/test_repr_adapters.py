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
_CROMA_LORA = _REPO / "models/checkpoints/exp008_croma_lora.pt"
_DOFA_CKPT = _REPO / "models/cache/dofa/DOFA_ViT_base_e100.pth"
_RC_IMG = _REPO / "external/research/RemoteCLIP/assets/airport.jpg"


def test_all_adapters_registered():
    assert set(ADAPTERS) == {"changeformer", "remoteclip", "croma", "dofa", "remotesam", "tinyrs"}


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


@pytest.mark.skipif(not _CROMA_CKPT.exists(), reason="croma ckpt absent (needed for the sha256 line)")
def test_croma_lora_weights_recorded_in_provenance():
    """G18 (EXP-008): the OPTIONAL --lora-weights path is wired through the
    adapter. Contract-level: no checkpoint needed. Production default stays
    frozen (lora_weights=None); passing a path flips encoder_mode + records the
    adapter hash. The default is NOT changed by G18 (larger-split result is
    directional only)."""
    from satquery_model_adapters.base import RawOutput

    req = AdapterRequest(context={"task": "embedding"})
    raw = RawOutput(data={}, runtime_s=0.0)
    frozen = CromaAdapter(checkpoint=str(_CROMA_CKPT))
    assert frozen.lora_weights is None
    assert frozen.provenance(req, raw, {})["encoder_mode"] == "frozen"

    # a real file is needed only for the sha256 line — reuse the CROMA ckpt as a stand-in path
    adapted = CromaAdapter(checkpoint=str(_CROMA_CKPT), lora_weights=str(_CROMA_CKPT))
    assert adapted.lora_weights == str(_CROMA_CKPT)
    prov_lora = adapted.provenance(req, raw, {})
    assert prov_lora["encoder_mode"] == "lora_adapted"
    assert prov_lora["lora_weights"] == str(_CROMA_CKPT)
    assert prov_lora["lora_weights_sha256"]


@pytest.mark.slow
@pytest.mark.skipif(not (_CROMA_CKPT.exists() and _CROMA_LORA.exists()
                         and (_REPO / ".venvs/croma/Scripts/python.exe").exists()),
                    reason="croma env/ckpt or persisted EXP-008 LoRA adapter absent")
def test_croma_lora_adapter_loads_and_changes_representation():
    """G18 Part 3: the persisted EXP-008 LoRA delta loads through the ACTUAL
    CromaAdapter pipeline (merged-delta apply in croma_infer.py), matches every
    wrapped Linear, and measurably alters the joint representation — it is never
    silently frozen."""
    req = AdapterRequest(context={"task": "embedding", "random": 1})
    frozen = CromaAdapter(checkpoint=str(_CROMA_CKPT)).run(req)
    adapted_a = CromaAdapter(checkpoint=str(_CROMA_CKPT), lora_weights=str(_CROMA_LORA))
    raw = adapted_a.execute(req)
    adapted = adapted_a.run(req)
    assert frozen.provenance["encoder_mode"] == "frozen"
    assert adapted.provenance["encoder_mode"] == "lora_adapted"
    assert adapted.provenance["lora_weights_sha256"]
    assert raw.data["encoder_mode"].startswith("lora_adapted (")
    assert "(0 layers)" not in raw.data["encoder_mode"]
    delta = max(abs(a - b) for a, b in zip(frozen.answer["joint_gap"], adapted.answer["joint_gap"]))
    assert delta > 1e-6, "LoRA delta did not change the representation"


@pytest.mark.slow
@pytest.mark.skipif(not (_DOFA_CKPT.exists() and (_REPO / ".venvs/dofa/Scripts/python.exe").exists()),
                    reason="dofa env/ckpt absent")
def test_dofa_smoke_random():
    a = DofaAdapter(checkpoint=str(_DOFA_CKPT))
    r = a.run(AdapterRequest(context={"task": "embedding", "modality": "s1", "random": 1}))
    assert r.answer["dim"] == 768
    assert r.answer["modality"] == "s1"
    assert r.provenance["license"] == "MIT"
