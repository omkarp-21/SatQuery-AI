"""G18 Part 13 — investigation report HTML export."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.services.report import investigation_report_html, report_from_file

_DEMOS = sorted((Path(__file__).resolve().parents[3] / "docs" / "sih" / "evidence" / "demos")
                .glob("g1[4-7]*flagship*.json"))

_REQUIRED = ["Mission", "Understood as", "Plan &amp; execution", "Key findings",
             "Spatial findings", "Evidence", "Verification", "Confidence category",
             "Models used", "Warnings", "Execution time"]


@pytest.mark.parametrize("demo", _DEMOS, ids=[d.name for d in _DEMOS])
def test_report_renders_from_every_flagship_demo(demo):
    html = report_from_file(str(demo))
    assert html.startswith("<!doctype html>") and html.rstrip().endswith("</html>")
    for s in _REQUIRED:
        assert s in html, f"{demo.name}: missing section {s!r}"
    # the confidence caveat must be present and no numeric confidence rendered
    assert "not a calibrated probability" in html.lower() or "NOT a probability" in html
    assert "% confident" not in html.lower()


def test_report_handles_a_minimal_dict():
    html = investigation_report_html({"mission": "m", "planner_used": "rule_based"})
    assert "<!doctype html>" in html and "SatQuery" in html


def test_report_escapes_html_in_mission():
    html = investigation_report_html({"mission": "<script>alert(1)</script>", "planner_used": "rule_based"})
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;" in html


def test_investigate_report_endpoint_accepts_a_result_json():
    """G19: the UI 'View full report' button POSTs the AgentInvestigationResult
    JSON it already holds back to POST /investigate/report and opens the HTML."""
    import json

    from fastapi.testclient import TestClient

    from app.main import app

    demo = (Path(__file__).resolve().parents[3] / "docs" / "sih" / "evidence"
            / "demos" / "final" / "flagship_caseA_change.json")
    body = json.loads(demo.read_text(encoding="utf-8"))
    r = TestClient(app).post("/investigate/report", json=body)
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/html")
    assert r.text.startswith("<!doctype html>")
    assert "Investigation" in r.text or "Mission" in r.text
