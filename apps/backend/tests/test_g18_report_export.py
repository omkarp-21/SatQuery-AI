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
