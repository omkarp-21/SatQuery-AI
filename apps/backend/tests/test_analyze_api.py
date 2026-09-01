"""POST /analyze - unified layer tests. Slow tests execute specialists."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.analyze import interpret_query, run_analyze

_REPO = Path(__file__).resolve().parents[3]
_CF = _REPO / ("models/cache/changeformer/CD_ChangeFormerV6_LEVIR_b16_lr0.0001_adamw"
               "_train_test_200_linear_ce_multi_train_True_multi_infer_False_shuffle_AB_False_embed_dim_256")
_ENV = (_CF / "best_ckpt.pt").exists() and (_REPO / "data/demo/temporal/t1.tif").exists()
_RC = (_REPO / "models/cache/remoteclip/RemoteCLIP-ViT-B-32.pt").exists()

client = TestClient(app)


# --- deterministic interpretation ---

@pytest.mark.parametrize("q,intent", [
    ("what changed between these dates?", "change"),
    ("describe what kind of change happened", "semantic-change"),
    ("what land cover is this scene?", "scene"),
    ("how many buildings are there?", "vqa"),
    ("", "unknown"),
    ("banana", "unknown"),
])
def test_interpret_query(q, intent):
    assert interpret_query(q).intent == intent


# --- routing / guards (fast) ---

def test_analyze_vqa_is_blocked_never_routed_to_remoteclip():
    r = client.post("/analyze", json={"query": "how many planes?", "images": ["airport.jpg"]})
    b = r.json()
    assert b["routing"]["routing_code"] == "NO_VQA_SPECIALIST"
    assert b["routing"]["selected_specialists"] == []
    assert b["ok"] is False


def test_analyze_too_many_images_400():
    r = client.post("/analyze", json={"query": "x", "images": ["a", "b", "c"]})
    assert r.status_code == 400


def test_analyze_traversal_rejected():
    r = client.post("/analyze", json={"query": "scene", "images": ["../../etc/passwd"]})
    assert r.status_code in (400, 404)


def test_analyze_missing_file_404():
    r = client.post("/analyze", json={"query": "scene", "images": ["demo/nope.tif"]})
    assert r.status_code == 404


@pytest.mark.slow
@pytest.mark.skipif(not _ENV, reason="changeformer env/demo absent")
def test_analyze_misregistered_pair_blocked():
    r = client.post("/analyze", json={"query": "what changed?",
                                      "images": ["demo/temporal/t1.tif", "demo/temporal/t2_shifted.tif"]})
    b = r.json()
    assert b["routing"]["routing_code"] == "VALIDATION_FAILED"
    assert b["ok"] is False and b["metadata_valid"] is False


# --- end-to-end dispatch (slow) ---

@pytest.mark.slow
@pytest.mark.skipif(not _ENV, reason="changeformer env/demo absent")
def test_analyze_change_path_aggregates_evidence():
    r = client.post("/analyze", json={"query": "what changed between these images?",
                                      "images": ["demo/temporal/t1.tif", "demo/temporal/t2.tif"]})
    b = r.json()
    assert r.status_code == 200 and b["ok"] is True
    assert b["routing"]["routing_code"] == "TEMPORAL"
    assert b["routing"]["selected_specialists"] == ["changeformer"]
    assert b["evidence"] and b["evidence"][0]["evidence_type"] == "change-mask"
    assert b["verification"]["status"] == "SUPPORTED"
    assert b["provenance"]["layer"] == "analyze"
    assert "no confidence value" in b["provenance"]["note"]
    assert "confidence" not in b["result"].get("provenance", {})
    # failure-aware routing (G8): a SUPPORTED result resolves to RESULT_OK, answer surfaced
    assert b["resolution"]["qualifier"] == "RESULT_OK"
    assert b["resolution"]["answer_surfaced"] is True
    assert b["resolution"]["fallback_used"] is None
    assert "NOT a confidence" in b["resolution"]["note"]


@pytest.mark.slow
@pytest.mark.skipif(not (_ENV and _RC), reason="changeformer/remoteclip absent")
def test_analyze_semantic_change_uses_composed_baseline():
    r = client.post("/analyze", json={"query": "describe what kind of change happened",
                                      "images": ["demo/temporal/t1.tif", "demo/temporal/t2.tif"]})
    b = r.json()
    assert b["ok"] is True
    assert b["result"]["baseline_name"] == "COMPOSED_SEMANTIC_CHANGE_BASELINE"
    assert "NOT a temporal VLM" in b["result"]["disclaimer"]
    assert b["result"]["description"]
    assert len(b["evidence"]) >= 2  # mask + >=1 region ranking


@pytest.mark.slow
@pytest.mark.skipif(not _RC, reason="remoteclip absent")
def test_analyze_scene_path():
    r = client.post("/analyze", json={"query": "what land cover is this scene?",
                                      "images": ["airport.jpg"],
                                      "context": {"prompts": ["an airport", "a farm", "a forest"]}})
    b = r.json()
    assert b["ok"] is True and b["routing"]["routing_code"] == "SINGLE_IMAGE_SCENE"
    assert b["result"]["answer"]["top_label"] == "an airport"
    assert "not a calibrated confidence" in b["result"]["answer"]["score_meaning"]
