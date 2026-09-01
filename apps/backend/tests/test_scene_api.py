"""POST /scene - API tests. Slow test subprocesses into .venvs/remoteclip."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app

_REPO = Path(__file__).resolve().parents[3]
_CKPT = _REPO / "models/cache/remoteclip/RemoteCLIP-ViT-B-32.pt"
_IMG = _REPO / "external/research/RemoteCLIP/assets/airport.jpg"
_ENV_OK = _CKPT.exists() and _IMG.exists() and (_REPO / ".venvs/remoteclip/Scripts/python.exe").exists()

client = TestClient(app)


def test_scene_traversal_rejected():
    r = client.post("/scene", json={"image_path": "../../../etc/passwd", "prompts": ["x"]})
    assert r.status_code in (400, 404)


def test_scene_missing_file_404():
    r = client.post("/scene", json={"image_path": "demo/nope.jpg", "prompts": ["x"]})
    assert r.status_code == 404


def test_scene_requires_prompts():
    r = client.post("/scene", json={"image_path": "airport.jpg", "prompts": []})
    assert r.status_code == 422  # pydantic min_length


@pytest.mark.slow
@pytest.mark.skipif(not _ENV_OK, reason="remoteclip env/ckpt/asset absent")
def test_scene_happy_path():
    r = client.post("/scene", json={"image_path": "airport.jpg",
                                    "prompts": ["an airport", "a farm", "a harbour"]})
    assert r.status_code == 200
    b = r.json()
    assert b["ok"] is True
    assert b["answer"]["top_label"] == "an airport"
    assert 0.0 <= b["answer"]["score"] <= 1.0
    assert "not a calibrated confidence" in b["answer"]["score_meaning"]
    assert b["evidence"][0]["evidence_type"] == "ranking"
    assert "confidence" not in b["evidence"][0]
    assert b["verification"]["status"] == "SUPPORTED"
    assert b["provenance"]["model"] == "remoteclip"
    assert b["provenance"]["status"] == "ok"
