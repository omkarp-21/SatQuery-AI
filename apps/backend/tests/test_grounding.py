"""G10 - grounding slice + routing + /analyze grounding path.

Fast tests use no model. The slow e2e is gated on the RemoteSAM checkpoint +
`.venvs/remotesam` being present.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.analyze import interpret_query
from app.services.grounding_slice import GroundingResult, run_grounding
from satquery_core.routing import RoutingRequest, route
from satquery_evidence import EvidenceItem, verify

_REPO = Path(__file__).resolve().parents[3]
_CKPT = _REPO / "models/cache/remotesam/RemoteSAM/RemoteSAMv1.pth"
_VENV = _REPO / ".venvs/remotesam/Scripts/python.exe"
_SCR = _REPO / "external/research/RemoteSAM"
_DEMO_IMG = _SCR / "assets/demo.jpg"
_ENV = _CKPT.exists() and _VENV.exists() and (_SCR / "tasks/code/model.py").exists()

client = TestClient(app)


# ---------- intent + routing (fast) ----------
@pytest.mark.parametrize("q,intent", [
    ("where is the runway", "grounding"),
    ("locate the largest building", "grounding"),
    ("segment the river", "grounding"),
    ("how many aircraft are parked", "vqa"),
    ("what is this scene", "scene"),
])
def test_grounding_intent_detection(q, intent):
    assert interpret_query(q).intent == intent


def test_grounding_routes_to_remotesam():
    d = route(RoutingRequest(query_intent="grounding", image_count=1,
                             modalities=["optical"], metadata_valid=True))
    assert d.code == "SINGLE_IMAGE_GROUNDING"
    assert d.specialists == ["remotesam"]


def test_vqa_never_routes_to_remotesam():
    d = route(RoutingRequest(query_intent="vqa", image_count=1,
                             modalities=["optical"], metadata_valid=True))
    assert d.code == "NO_VQA_SPECIALIST"
    assert "remotesam" not in d.specialists
    assert "RemoteSAM" in d.reason  # explicitly says not to route it as VQA


def test_grounding_blocked_when_capability_absent():
    d = route(RoutingRequest(query_intent="grounding", image_count=1, modalities=["optical"],
                             metadata_valid=True, available_capabilities=["change-detection"]))
    assert d.specialists == [] and d.code == "NO_MATCH"


# ---------- structural verification of grounding evidence (fast) ----------
def _ground_ev(box, dims, mask_path=None):
    return EvidenceItem(source_model="remotesam", task="grounding", modality="optical-single",
                        claim_supported="phrase refers to region", evidence_type="grounding",
                        payload={"bbox_xyxy": box, "image_dims": dims, "mask_path": mask_path})


def test_valid_box_passes_structural_check():
    vr = verify({}, [_ground_ev([10, 20, 100, 140], [256, 256])], {})
    assert vr.status == "SUPPORTED"
    assert any(c.name.startswith("grounding_box_valid") and c.passed for c in vr.checks)


def test_out_of_bounds_box_is_contradicted():
    vr = verify({}, [_ground_ev([10, 20, 400, 140], [256, 256])], {})
    assert vr.status == "CONTRADICTED"
    assert any(c.name.startswith("grounding_box_valid") and not c.passed for c in vr.checks)


def test_degenerate_box_is_contradicted():
    vr = verify({}, [_ground_ev([100, 100, 50, 50], [256, 256])], {})
    assert vr.status == "CONTRADICTED"


def test_missing_mask_artifact_is_contradicted():
    vr = verify({}, [_ground_ev([10, 20, 100, 140], [256, 256], mask_path="/no/such/mask.png")], {})
    assert vr.status == "CONTRADICTED"
    assert any("grounding_mask_artifact" in c.name and not c.passed for c in vr.checks)


# ---------- grounding_slice failure paths (fast) ----------
def test_missing_image_returns_error():
    r = run_grounding("/no/such/img.jpg", "the runway")
    assert isinstance(r, GroundingResult) and r.ok is False and r.errors


def test_empty_query_returns_error():
    r = run_grounding(str(_DEMO_IMG) if _DEMO_IMG.exists() else __file__, "")
    assert r.ok is False and any("phrase" in e for e in r.errors)


def test_missing_checkpoint_returns_error(tmp_path):
    img = tmp_path / "x.png"
    from PIL import Image
    Image.new("RGB", (32, 32)).save(img)
    r = run_grounding(str(img), "the runway", checkpoint="/no/such/RemoteSAMv1.pth")
    assert r.ok is False and any("checkpoint" in e.lower() for e in r.errors)


def test_analyze_grounding_missing_file_is_404():
    resp = client.post("/analyze", json={"query": "where is the runway", "images": ["nope.jpg"]})
    assert resp.status_code in (404, 400)


# ---------- slow e2e ----------
@pytest.mark.slow
@pytest.mark.skipif(not _ENV, reason="RemoteSAM checkpoint / .venvs/remotesam absent")
def test_run_grounding_e2e_produces_mapped_box_and_evidence():
    r = run_grounding(str(_DEMO_IMG), "the airplane on the right", timeout_s=400)
    assert r.ok is True
    assert r.bbox_xyxy is not None and len(r.bbox_xyxy) == 4
    w, h = r.image_dimensions
    x0, y0, x1, y1 = r.bbox_xyxy
    assert 0 <= x0 < x1 <= w and 0 <= y0 < y1 <= h  # box maps into the image
    assert r.validation_status == "PASS"
    assert r.evidence and r.evidence[0].evidence_type == "grounding"
    assert r.verification.status in ("SUPPORTED", "CONTRADICTED")
    assert r.mask_path and Path(r.mask_path).exists()
    assert "calibrated confidence" in r.score_meaning.lower()
    assert "NOT STATED" in str(r.provenance)


@pytest.mark.slow
@pytest.mark.skipif(not _ENV, reason="RemoteSAM checkpoint / .venvs/remotesam absent")
def test_analyze_grounding_path_routes_and_runs():
    # call the service directly: the HTTP layer's path allow-list (a security
    # feature) would reject an abs path outside data/ - not what this test checks.
    from app.services.analyze import run_analyze

    r = run_analyze("locate the airplane on the right", [str(_DEMO_IMG)])
    b = r.model_dump()
    assert b["ok"] is True
    assert b["interpretation"]["intent"] == "grounding"
    assert b["routing"]["routing_code"] == "SINGLE_IMAGE_GROUNDING"
    assert b["routing"]["selected_specialists"] == ["remotesam"]
    assert b["evidence"][0]["evidence_type"] == "grounding"
    assert b["result"]["bbox_xyxy"] is not None
    assert "no confidence value is produced" in b["provenance"]["note"]
    assert b["resolution"]["qualifier"] in ("RESULT_OK", "RESULT_UNVERIFIED",
                                            "RESULT_STRUCTURAL_FAIL")
