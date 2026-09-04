"""G20.1 — top-level investigation status (SUCCESS / PARTIAL / BLOCKED / FAILED),
DISTINCT from `verification` and `confidence`.

The core guarantee (Part 23): a primary-specialist failure can NEVER render as a
successful investigation, and must NEVER surface a misleading "Verification:
SUPPORTED" headline when the requested conclusion was not established.
"""

from __future__ import annotations

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

from satquery_agents.agent import RuleBasedPlanner

from app.services.agent_runner import derive_investigation_status, run_investigation
from app.services.report import investigation_report_html


def _tif(path, *, w, h, count=3, crs="EPSG:32643", res=10.0):
    prof = dict(driver="GTiff", width=w, height=h, count=count, dtype="uint8",
                crs=crs, transform=from_origin(6e5, 15e5, res, res), nodata=0)
    with rasterio.open(path, "w", **prof) as ds:
        ds.write((np.arange(w * h * count) % 255).reshape(count, h, w).astype("uint8"))
    return str(path)


# --------------------------------------------------------------- BLOCKED (the reported bug)

@pytest.fixture(scope="module")
def blocked_run(tmp_path_factory):
    d = tmp_path_factory.mktemp("g201")
    t1 = _tif(d / "t1.tif", w=48, h=40)   # 48x40
    t2 = _tif(d / "t2.tif", w=44, h=36)   # 44x36  -> NOT co-registered
    return run_investigation("compare these two images and find what changed",
                             [t1, t2], {}, planner=RuleBasedPlanner())


def test_coregistration_failure_is_BLOCKED_not_success(blocked_run):
    r = blocked_run
    assert r.investigation_status == "BLOCKED", r.investigation_status
    assert r.ok is False
    assert r.phase == "BLOCKED"


def test_blocked_run_never_reports_SUPPORTED_verification(blocked_run):
    r = blocked_run
    assert (r.verification or {}).get("status") != "SUPPORTED", r.verification
    # NOT_APPLICABLE is the honest value for an analysis that produced no conclusion
    assert (r.verification or {}).get("status") in ("NOT_APPLICABLE", "INSUFFICIENT_EVIDENCE", "CONTRADICTED")


def test_blocked_run_confidence_is_insufficient(blocked_run):
    assert (blocked_run.confidence or {}).get("category") == "INSUFFICIENT_EVIDENCE"


def test_blocked_conclusion_is_human_readable_not_developer_phrasing(blocked_run):
    c = (blocked_run.conclusion or "")
    assert "step(s) failed. Verification:" not in c
    assert "Verification: SUPPORTED" not in c
    assert "could not be completed" in c.lower() or "unavailable" in c.lower()


def test_blocked_reason_explains_co_registration(blocked_run):
    reason = (blocked_run.investigation_status_reason or "").lower()
    assert "co-regist" in reason or "aligned" in reason or "pre-condition" in reason


def test_blocked_run_produces_no_fabricated_geometry(blocked_run):
    assert not blocked_run.spatial_findings
    assert not (blocked_run.geojson or {}).get("features")


def test_blocked_report_leads_with_investigation_status(blocked_run):
    html = investigation_report_html(blocked_run.model_dump())
    assert "Investigation status" in html
    assert "BLOCKED" in html
    # the report must NOT present verification SUPPORTED as if the run succeeded
    assert ">SUPPORTED<" not in html.split("Verification")[-1][:400]


# --------------------------------------------------------------- SUCCESS / early stop / PARTIAL


class _Step:
    def __init__(self, step_id, task, tool, status="completed", verdict="COHERENT",
                 summary="", failure=None, replan_note=None):
        self.step_id, self.task, self.tool = step_id, task, tool
        self.status, self.verdict, self.summary = status, verdict, summary
        self.failure, self.replan_note = failure, replan_note


class _Replan:
    def __init__(self, reason, triggering_step="s2", detail="", steps_skipped=()):
        self.reason, self.triggering_step = reason, triggering_step
        self.detail, self.steps_skipped = detail, list(steps_skipped)


class _Task:
    def __init__(self, v):
        self.value = v

    def __eq__(self, other):
        return getattr(other, "value", other) == self.value

    def __hash__(self):
        return hash(self.value)


class _PlanStep:
    def __init__(self, step_id, task, tool):
        self.step_id, self.task, self.tool = step_id, task, tool


class _Plan:
    def __init__(self, steps):
        self.steps = steps


class _Mem:
    results: dict = {}
    failures: list = []


class _Res:
    def __init__(self, **kw):
        self.steps = kw.get("steps", [])
        self.replans = kw.get("replans", [])
        self.early_stopped = kw.get("early_stopped", False)
        self.completion_reason = kw.get("completion_reason")
        self.plan_status = kw.get("plan_status", "valid")
        self.verification = kw.get("verification", {"status": "SUPPORTED"})
        self.failures = kw.get("failures", [])


_TC = _Task("TEMPORAL_CHANGE")
_ECR = _Task("EXTRACT_CHANGED_REGIONS")
_GO = _Task("GROUND_OBJECT")
_OS = _Task("OPTICAL_SAR_ANALYSIS")


def test_status_success_when_every_planned_specialist_completed():
    plan = _Plan([_PlanStep("s2", _TC, "run_temporal_change"),
                  _PlanStep("s3", _ECR, "extract_changed_regions"),
                  _PlanStep("s4", _GO, "run_grounding")])
    res = _Res(steps=[_Step("s2", _TC, "run_temporal_change", summary="changed_fraction 0.25"),
                      _Step("s3", _ECR, "extract_changed_regions", summary="6 regions"),
                      _Step("s4", _GO, "run_grounding", summary="grounded box")])
    st, _ = derive_investigation_status(res, _Mem(), plan)
    assert st == "SUCCESS"


def test_status_success_on_legitimate_no_change_early_stop():
    plan = _Plan([_PlanStep("s2", _TC, "run_temporal_change"),
                  _PlanStep("s3", _ECR, "extract_changed_regions"),
                  _PlanStep("s4", _GO, "run_grounding")])
    res = _Res(
        steps=[_Step("s2", _TC, "run_temporal_change", summary="changed_fraction 0.00"),
               _Step("s3", _ECR, "extract_changed_regions", status="failed",
                     failure="no region above size threshold"),
               _Step("s4", _GO, "run_grounding", status="skipped")],
        replans=[_Replan("NEW_EVIDENCE", steps_skipped=["s3", "s4"])],
        early_stopped=True, completion_reason="no significant temporal change detected")
    st, reason = derive_investigation_status(res, _Mem(), plan)
    assert st == "SUCCESS", reason
    assert "no significant" in reason.lower()


def test_status_partial_when_one_specialist_fails_but_another_succeeds():
    plan = _Plan([_PlanStep("s2", _TC, "run_temporal_change"),
                  _PlanStep("s4", _GO, "run_grounding")])
    res = _Res(steps=[_Step("s2", _TC, "run_temporal_change", summary="changed_fraction 0.25"),
                      _Step("s4", _GO, "run_grounding", status="failed",
                            failure="no matching region")])
    st, reason = derive_investigation_status(res, _Mem(), plan)
    assert st == "PARTIAL", reason
    assert "could not complete" in reason.lower()


def test_status_failed_on_verification_contradiction():
    plan = _Plan([_PlanStep("s2", _TC, "run_temporal_change")])
    res = _Res(steps=[_Step("s2", _TC, "run_temporal_change", status="completed",
                            verdict="INCOHERENT")],
               verification={"status": "CONTRADICTED"})
    st, _ = derive_investigation_status(res, _Mem(), plan)
    assert st == "FAILED"
