"""G11 - VQA slice + routing + /analyze VQA path (TinyRS-2B)."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.services.analyze import interpret_query, run_analyze
from app.services.vqa_slice import VqaResult, run_vqa
from satquery_core.routing import RoutingRequest, route
from satquery_model_adapters import ADAPTERS, AdapterRequest, TinyRsAdapter
from satquery_model_adapters.errors import (
    AdapterConfigError,
    AdapterExecutionError,
    UnsupportedTaskError,
)

_REPO = Path(__file__).resolve().parents[3]
_W = _REPO / "models/cache/tinyrs/Qwen2-VL-TinyRS"
_VENV = _REPO / ".venvs/tinyrs/Scripts/python.exe"
_IMG = _REPO / "external/research/RemoteCLIP/assets/airport.jpg"
_ENV = (_W / "config.json").exists() and _VENV.exists() and _IMG.exists()


# ---------- intent + routing (fast) ----------
@pytest.mark.parametrize("q,intent", [
    ("how many aircraft are parked", "vqa"),
    ("is there a river in this image", "vqa"),
    ("what colour is the roof", "vqa"),
    ("where is the runway", "grounding"),
    ("what is this scene", "scene"),
])
def test_vqa_intent_detection(q, intent):
    assert interpret_query(q).intent == intent


def test_vqa_routes_to_tinyrs():
    d = route(RoutingRequest(query_intent="vqa", image_count=1, modalities=["optical"],
                             metadata_valid=True))
    assert d.code == "SINGLE_IMAGE_VQA" and d.specialists == ["tinyrs"]


def test_grounding_not_routed_to_tinyrs():
    d = route(RoutingRequest(query_intent="grounding", image_count=1, modalities=["optical"],
                             metadata_valid=True))
    assert "tinyrs" not in d.specialists


# ---------- adapter contract (fast) ----------
def test_registered():
    assert ADAPTERS["tinyrs"] is TinyRsAdapter


def test_rejects_grounding_task():
    a = TinyRsAdapter(weights=str(_W))
    with pytest.raises(UnsupportedTaskError):
        a.validate(AdapterRequest(query="the runway", images=[str(_IMG)],
                                  context={"task": "grounding"}))


def test_rejects_empty_question():
    a = TinyRsAdapter(weights=str(_W))
    with pytest.raises(AdapterExecutionError):
        a.validate(AdapterRequest(query="  ", images=[str(_IMG)], context={"task": "vqa"}))


def test_rejects_two_images():
    a = TinyRsAdapter(weights=str(_W))
    with pytest.raises(AdapterExecutionError):
        a.validate(AdapterRequest(query="q?", images=[str(_IMG), str(_IMG)], context={"task": "vqa"}))


def test_missing_weights_is_config_error(tmp_path):
    img = tmp_path / "x.png"
    from PIL import Image
    Image.new("RGB", (16, 16)).save(img)
    a = TinyRsAdapter(weights="/no/such/weights")
    with pytest.raises(AdapterConfigError):
        a.validate(AdapterRequest(query="q?", images=[str(img)], context={"task": "vqa"}))


# ---------- vqa_slice failure paths (fast) ----------
def test_run_vqa_missing_image():
    r = run_vqa("/no/img.jpg", "how many planes?")
    assert isinstance(r, VqaResult) and r.ok is False and r.errors


def test_run_vqa_empty_question():
    r = run_vqa(str(_IMG) if _IMG.exists() else __file__, "")
    assert r.ok is False


def test_run_vqa_missing_weights(tmp_path):
    img = tmp_path / "x.png"
    from PIL import Image
    Image.new("RGB", (16, 16)).save(img)
    r = run_vqa(str(img), "how many?", weights="/no/such/weights")
    assert r.ok is False and any("weights" in e.lower() for e in r.errors)


# ---------- slow e2e ----------
@pytest.mark.slow
@pytest.mark.skipif(not _ENV, reason="TinyRS weights / .venvs/tinyrs absent")
def test_run_vqa_e2e_yes_no():
    r = run_vqa(str(_IMG), "Is there an airport in this image?")
    assert r.ok is True
    assert r.answer_text
    assert r.yesno in (0, 1)  # airport.jpg -> should parse a yes/no
    assert r.evidence and r.evidence[0].evidence_type == "vqa"
    assert r.verification.status in ("SUPPORTED", "CONTRADICTED", "INSUFFICIENT_EVIDENCE")
    assert "no calibrated probability" in r.score_meaning
    assert r.score is None


@pytest.mark.slow
@pytest.mark.skipif(not _ENV, reason="TinyRS weights / .venvs/tinyrs absent")
def test_analyze_vqa_path_routes_and_runs():
    r = run_analyze("how many aircraft can you see", [str(_IMG)])
    b = r.model_dump()
    assert b["routing"]["routing_code"] == "SINGLE_IMAGE_VQA"
    assert b["routing"]["selected_specialists"] == ["tinyrs"]
    assert b["evidence"][0]["evidence_type"] == "vqa"
    assert "no confidence value" in b["provenance"]["note"]
