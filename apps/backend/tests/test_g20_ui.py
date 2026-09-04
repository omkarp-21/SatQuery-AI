"""G20 — UI/UX polish. The only file that changed is
`apps/backend/app/static/index.html` (vanilla JS, no build step). These tests
guard: (a) the page serves and carries the expected structure/terminology,
(b) no forbidden claim wording leaked in, (c) the backend contract the UI renders
from is unchanged, and (d) the frozen demo captures still contain every field the
UI reads.

There is no JS DOM runtime available, so rendering itself is asserted through the
served markup + a UI<->data contract check against the real captured responses.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app

_REPO = Path(__file__).resolve().parents[3]
_INDEX = _REPO / "apps" / "backend" / "app" / "static" / "index.html"
_FINAL = _REPO / "docs" / "sih" / "evidence" / "demos" / "final"

client = TestClient(app)


@pytest.fixture(scope="module")
def html() -> str:
    return _INDEX.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def served() -> str:
    r = client.get("/")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/html")
    return r.text


# ---------------------------------------------------------------- page + shell

def test_page_loads_and_is_the_static_file(served, html):
    assert served.strip() == html.strip()
    assert served.startswith("<!doctype html>")
    assert "SATQUERY" in served and "Geospatial Intelligence" in served


def test_top_nav_has_ask_investigate_about_and_system(served):
    assert 'data-nav="#/ask"' in served
    assert 'data-nav="#/investigate"' in served
    assert 'data-nav="#/about"' in served
    assert 'id="sysbtn"' in served


def test_hero_explains_the_product(served):
    assert "Investigate satellite imagery with natural language." in served
    assert "Plan, analyze, verify, and map geospatial findings" in served
    # the two primary actions
    assert "Investigate an area" in served and "Ask a question" in served
    # the pipeline strip
    for token in ("Mission", "Plan", "Specialist analysis", "Observation",
                  "Adaptive action", "Evidence", "Verification"):
        assert token in served


def test_footer_status_strip_present(served):
    assert 'id="status"' in served
    assert "Local inference" in served
    assert "GPU: UNVERIFIED" in served


# ---------------------------------------------------------------- modes

def test_ask_view_is_simple(served):
    assert 'id="view-ask"' in served
    assert 'id="run-ask"' in served
    assert 'id="ask-files"' in served and 'id="ask-q"' in served


def test_investigate_view_is_the_workspace(served):
    assert 'id="view-investigate"' in served
    assert 'id="mission"' in served
    assert 'id="run-investigate"' in served
    # 3-column workspace grid areas
    assert '"left center right"' in served and '"bottom bottom bottom"' in served
    assert "col-left" in served and "col-center" in served and "col-right" in served


def test_demo_mode_prefills_official_mission_but_still_calls_real_backend(served):
    assert 'id="demo-toggle"' in served
    assert "prefill the official flagship mission" in served
    assert "still runs the real backend" in served
    # the official mission text is present verbatim
    assert "compare optical and SAR evidence, and provide a verified summary." in served
    # demo mode must NOT ship canned execution: no fixture fetch, no hard-coded result object
    assert "flagship_caseA_change.json" not in served
    assert "fake" not in served.lower()


# ---------------------------------------------------------------- render functions

@pytest.mark.parametrize("fn", [
    "renderInvestigation", "renderAsk", "missionPanel", "planPanel", "adaptivePanel",
    "completionPanel", "viewerPanel", "mountViewer", "renderGeoSVG", "findingsPanel",
    "trustPanel", "verificationLine", "evidencePanel", "warningsPanel", "errState",
    "viewReport", "checkHealth", "route",
])
def test_render_function_present(served, fn):
    assert re.search(r"\bfunction\s+" + fn + r"\b", served) or re.search(fn + r"\s*=", served)


# ---------------------------------------------------------------- G20.1 status hierarchy

def test_ui_has_the_four_investigation_statuses(served):
    for s in ("SUCCESS", "PARTIAL", "BLOCKED", "FAILED"):
        assert s in served, f"status {s} not referenced in the UI"
    assert "STATUS_META" in served and "status-banner" in served


def test_ui_separates_investigation_status_from_verification(served):
    # verification is explicitly labelled as being about the evidence, not the outcome
    assert "of the evidence, not the outcome" in served
    # a blocked run shows "Spatial comparison unavailable", never the input image
    assert "Spatial comparison unavailable" in served
    # verification can read NOT APPLICABLE
    assert "NOT APPLICABLE" in served
    # enum reason names are mapped to plain language for the primary view
    assert "_REASON_PLAIN" in served
    assert "TOOL_FAILURE" in served  # only inside the mapping / details, not as a headline


def test_ui_uses_investigation_status_field_from_the_backend(served):
    assert "investigation_status" in served
    assert "investigation_status_reason" in served


def test_report_button_uses_the_existing_endpoint(served):
    assert "Export investigation report" in served
    assert '"/investigate/report"' in served
    assert '"/analyze/upload"' in served
    assert '"/investigate"' in served
    assert '"/health"' in served


def test_required_terminology_present(served):
    for term in ("Mission", "Plan", "Adaptive execution", "Findings", "Confidence",
                 "Verification", "Evidence", "Warnings", "Observation", "Decision"):
        assert term in served, f"missing UI term: {term}"
    assert "trace" in served.lower()


# ---------------------------------------------------------------- claim hygiene

_FORBIDDEN = [
    r"state-of-the-art", r"real-time", r"fully autonomous", r"hallucination-free",
    r"\bSOTA\b", r"SAR improves", r"\b4\s?GB\b",
]


def test_no_forbidden_claims_in_ui(served):
    for pat in _FORBIDDEN:
        assert not re.search(pat, served, re.I), f"forbidden claim wording in UI: {pat}"


def test_confidence_is_never_shown_as_a_number(served):
    # the UI must state it is a category, not a probability/score
    assert "NOT a probability" in served
    # never render the internal numeric score
    assert "conf.score" not in served and "confidence.score" not in served
    assert "% confiden" not in served.lower()


def test_remotesam_licence_and_gpu_caveats_kept(served):
    assert "licence NOT STATED" in served or "NOT STATED" in served
    assert "UNVERIFIED" in served


# ---------------------------------------------------------------- accessibility / motion

def test_reduced_motion_and_focus_styles(served):
    assert "prefers-reduced-motion" in served
    assert ":focus-visible" in served
    assert 'role="status"' in served and 'role="alert"' in served


# ---------------------------------------------------------------- backend contract unchanged

def test_health_ok(served):
    r = client.get("/health")
    assert r.status_code == 200 and r.json() == {"status": "ok"}


def test_analyze_and_investigate_routes_still_exist():
    schema = client.get("/openapi.json").json()["paths"]
    assert "/analyze/upload" in schema
    assert "/investigate" in schema
    assert "/investigate/report" in schema


def test_investigate_report_still_renders_from_a_captured_result():
    body = json.loads((_FINAL / "flagship_caseA_change.json").read_text(encoding="utf-8"))
    r = client.post("/investigate/report", json=body)
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/html")
    assert r.text.startswith("<!doctype html>")


# ------------------------------------------------ UI <-> data contract (regression guard)

@pytest.mark.parametrize("cap", ["flagship_caseA_change.json", "flagship_caseB_nochange.json"])
def test_ui_reads_only_fields_the_backend_actually_returns(cap):
    """Every field the investigate renderer touches must exist in the real
    captured responses, so a backend shape change fails a test instead of
    silently blanking the UI."""
    b = json.loads((_FINAL / cap).read_text(encoding="utf-8"))

    # mission panel
    assert isinstance(b.get("mission"), str)
    assert "planner_used" in b and "models_used" in b and "timings" in b
    assert "total_s" in b["timings"]

    # plan + steps
    assert "steps" in b["plan"] and isinstance(b["plan"]["steps"], list)
    for p in b["plan"]["steps"]:
        assert "step_id" in p and "task" in p and "tool" in p
    for s in b.get("steps", []):
        assert "step_id" in s and "status" in s

    # adaptive: replans structure
    for r in b.get("replans", []):
        assert "reason" in r and "triggering_step" in r and "detail" in r
        assert "steps_skipped" in r

    # findings
    assert isinstance(b.get("key_findings"), list)
    for sf in b.get("spatial_findings", []):
        assert "label" in sf

    # trust
    c = b.get("confidence") or {}
    assert c.get("category") in {"HIGH", "MEDIUM", "LOW", "INSUFFICIENT_EVIDENCE"}
    assert isinstance(c.get("reasons"), list)

    # verification
    v = b.get("verification") or {}
    assert "status" in v and isinstance(v.get("checks"), list)

    # evidence
    for e in b.get("evidence", []):
        assert "evidence_type" in e

    # warnings / early stop
    assert isinstance(b.get("warnings", []), list)
    assert "early_stopped" in b


def test_caseA_and_caseB_differ_in_the_way_the_ui_shows(cap="_"):
    a = json.loads((_FINAL / "flagship_caseA_change.json").read_text(encoding="utf-8"))
    bcase = json.loads((_FINAL / "flagship_caseB_nochange.json").read_text(encoding="utf-8"))
    # CASE A: more tool calls, not early stopped, HIGH
    assert a["tool_calls"] > bcase["tool_calls"]
    assert a["early_stopped"] is False and bcase["early_stopped"] is True
    assert a["confidence"]["category"] == "HIGH"
    assert bcase["confidence"]["category"] == "MEDIUM"
    # CASE B: has replans the adaptive panel will render
    assert len(bcase["replans"]) >= 1
