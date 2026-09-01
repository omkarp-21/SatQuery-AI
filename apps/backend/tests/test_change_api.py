"""POST /change - API tests (TestClient). Slow: the happy path subprocesses into
.venvs/changeformer."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app

_REPO = Path(__file__).resolve().parents[3]
_CKPT = _REPO / "models/cache/changeformer/CD_ChangeFormerV6_LEVIR_b16_lr0.0001_adamw_train_test_200_linear_ce_multi_train_True_multi_infer_False_shuffle_AB_False_embed_dim_256"
_DEMO_OK = (_REPO / "data/demo/temporal/t1.tif").exists()
_ENV_OK = (_REPO / ".venvs/changeformer/Scripts/python.exe").exists() and (_CKPT / "best_ckpt.pt").exists()

client = TestClient(app)


def test_health():
    assert client.get("/health").json() == {"status": "ok"}


def test_change_path_traversal_rejected():
    r = client.post("/change", json={"t1_path": "../../../etc/passwd", "t2_path": "demo/temporal/t2.tif"})
    assert r.status_code in (400, 404)


def test_change_missing_file_404():
    r = client.post("/change", json={"t1_path": "demo/temporal/nope.tif", "t2_path": "demo/temporal/t2.tif"})
    assert r.status_code == 404


@pytest.mark.slow
@pytest.mark.skipif(not (_DEMO_OK and _ENV_OK), reason="demo data / changeformer env absent")
def test_change_happy_path():
    r = client.post("/change", json={"t1_path": "demo/temporal/t1.tif", "t2_path": "demo/temporal/t2.tif"})
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["pair"]["co_registered"] is True
    assert body["stats"]["changed_pixels"] > 0
    assert body["stats"]["changed_area_ha"] is not None
    assert body["provenance"]["adapter_provenance"]["checkpoint_sha256"]
    assert "not a confidence" in body["provenance"]["score_meaning"]


@pytest.mark.slow
@pytest.mark.skipif(not (_DEMO_OK and _ENV_OK), reason="demo data / changeformer env absent")
def test_change_misregistered_blocked():
    r = client.post("/change", json={"t1_path": "demo/temporal/t1.tif",
                                     "t2_path": "demo/temporal/t2_shifted.tif", "strict": True})
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is False
    assert body["stats"] is None
