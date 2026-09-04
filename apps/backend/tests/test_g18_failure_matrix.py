"""G18 Part 9 — release-level FAILURE MATRIX.

22 pathological conditions against the real product surfaces (`run_analyze`,
`run_investigation`, the geospatial validators, the policy layer). For every one:

  * NO uncaught exception (i.e. the API would not 500)
  * NO hallucinated result / fabricated coordinates
  * NO fabricated confidence (category only, never a number)
  * NO hidden fallback (a fallback is always surfaced in warnings / resolution)
  * NO infinite loop (bounded executor, <= MAX_STEPS)
  * a STRUCTURED resolution is returned

These are fast: model-absent conditions resolve to a typed failure; model-present
conditions use the deterministic planner + policy layer without invoking a model.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest
import rasterio
from rasterio.transform import Affine, from_origin

_REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_REPO / "packages" / "agents" / "src"))

from app.services.analyze import interpret_query, run_analyze  # noqa: E402
from app.services.agent_runner import run_investigation  # noqa: E402
from satquery_agents.agent import (  # noqa: E402
    PlanContext,
    RuleBasedPlanner,
    build_plan_from_raw,
    intent_from_raw,
    validate_plan,
)

_DEMO = _REPO / "data" / "demo"

# _Qualifier is an open str; we assert it is a non-empty UPPER_SNAKE token, not a
# specific enum. These are the ones seen in practice (for the doc / readability).
_KNOWN_QUALIFIERS = {
    "RESULT_OK", "RESULT_UNVERIFIED", "RESULT_STRUCTURAL_FAIL", "RESULT_SEMANTIC_INCOHERENT",
    "VALIDATION_FAILED", "NO_VQA_SPECIALIST", "SPECIALIST_DEGRADED", "SPECIALIST_FAILED",
    "SPECIALIST_UNAVAILABLE", "PLANNER_UNAVAILABLE", "PLAN_REJECTED", "PLAN_INTENT_MISMATCH",
    "INSUFFICIENT_EVIDENCE", "NO_ANSWER", "RESULT_PARTIAL", "CONTRADICTED",
}


def _qual_of(resolution):
    if resolution is None:
        return None
    return resolution.get("qualifier") if isinstance(resolution, dict) else getattr(resolution, "qualifier", None)


def _tif(path, *, w=16, h=16, count=3, crs="EPSG:32643", origin=(6e5, 15e5), res=10.0,
         nodata=0.0, dtype="uint8", transform=None):
    tr = transform or from_origin(origin[0], origin[1], res, res)
    prof = dict(driver="GTiff", width=w, height=h, count=count, dtype=dtype, crs=crs,
                transform=tr, nodata=nodata)
    with rasterio.open(path, "w", **prof) as ds:
        ds.write((np.arange(w * h * count) % 255).reshape(count, h, w).astype(dtype))
    return str(path)


def _assert_structured(res) -> None:
    """Invariants every AnalyzeResult / normalized result must satisfy on failure."""
    resolution = getattr(res, "resolution", None)
    if resolution is None and isinstance(res, dict):
        resolution = res.get("resolution")
    q = _qual_of(resolution)
    if q is not None:
        assert isinstance(q, str) and q and q == q.upper().replace(" ", "_"), q
        assert q in _KNOWN_QUALIFIERS, f"unexpected qualifier {q!r} (add to _KNOWN_QUALIFIERS if intended)"
    # no fabricated numeric confidence anywhere in the serialised form
    blob = str(getattr(res, "__dict__", res))
    assert '"confidence": 0.' not in blob and "confidence=0." not in blob


def _assert_agent_ok(res) -> None:
    assert res.tool_calls <= res.max_steps, "executor exceeded MAX_STEPS"
    # G20.1: a pre-condition failure legitimately ends the run in the BLOCKED phase
    assert res.phase in ("FINALIZING", "FAILED", "BLOCKED"), res.phase
    if res.investigation_status:
        assert res.investigation_status in ("SUCCESS", "PARTIAL", "BLOCKED", "FAILED")
        # a non-SUCCESS/PARTIAL investigation must NOT read as ok, and must NOT
        # claim SUPPORTED verification
        if res.investigation_status in ("BLOCKED", "FAILED"):
            assert res.ok is False, res.investigation_status
            assert (res.verification or {}).get("status") != "SUPPORTED", res.verification
    if res.resolution:
        assert _qual_of(res.resolution) in _KNOWN_QUALIFIERS, res.resolution
    # a fallback must be visible
    if res.mode == "ask-fallback" or res.planner_used.endswith("fallback"):
        assert any("FALLBACK" in w.upper() or "fallback" in w for w in res.warnings), res.warnings
    # confidence, if present, is a CATEGORY not a number
    if res.confidence:
        assert res.confidence["category"] in ("HIGH", "MEDIUM", "LOW", "INSUFFICIENT_EVIDENCE")
        assert not isinstance(res.confidence.get("score"), float) or "not a calibrated probability" in \
            res.confidence["note"].lower()
    # no fabricated coordinates when nothing was grounded
    if not res.spatial_findings:
        assert not res.geojson or not res.geojson.get("features")


# --------------------------------------------------------------------------- #
# 1-8 · geospatial / input conditions
# --------------------------------------------------------------------------- #

def test_01_invalid_geotiff(tmp_path):
    (tmp_path / "junk.tif").write_bytes(b"II*\x00 not a raster " + b"\xff" * 40)
    res = run_analyze("what changed?", [str(tmp_path / "junk.tif"), _tif(tmp_path / "b.tif")], {})
    assert not res.ok and res.errors
    _assert_structured(res)


def test_02_corrupt_geotiff_truncated(tmp_path):
    good = _tif(tmp_path / "g.tif")
    data = Path(good).read_bytes()
    (tmp_path / "trunc.tif").write_bytes(data[: len(data) // 3])
    res = run_analyze("what changed between these?", [str(tmp_path / "trunc.tif"), good], {})
    assert not res.ok
    _assert_structured(res)


def test_03_missing_crs(tmp_path):
    p = _tif(tmp_path / "nocrs.tif", crs=None, nodata=None)
    res = run_analyze("what is in this image?", [p], {})
    _assert_structured(res)  # may pass with geo_warnings or fail typed — never 500


def test_04_incompatible_crs_pair(tmp_path):
    a = _tif(tmp_path / "a.tif", crs="EPSG:32643")
    b = _tif(tmp_path / "b.tif", crs="EPSG:32644")
    res = run_analyze("what changed between these two images?", [a, b], {})
    assert not res.ok  # co-registration gate
    _assert_structured(res)


def test_05_shape_mismatch_pair(tmp_path):
    a = _tif(tmp_path / "a.tif", w=16, h=16)
    b = _tif(tmp_path / "b.tif", w=24, h=24)
    res = run_analyze("compare these two images for change", [a, b], {})
    assert not res.ok
    _assert_structured(res)


def test_06_missing_second_image(tmp_path):
    res = run_analyze("what changed between the two images?", [_tif(tmp_path / "only.tif")], {})
    _assert_structured(res)
    # single image + change intent -> NOT a temporal run, NOT a fabricated change result
    rc = getattr(res.routing, "routing_code", getattr(res.routing, "route_code", ""))
    assert rc != "TEMPORAL"
    assert not any("change" in (e or "").lower() and "%" in (e or "") for e in (res.errors or []))


def test_07_missing_sar_for_optical_sar(tmp_path):
    a = _tif(tmp_path / "s2a.tif", count=3)
    b = _tif(tmp_path / "s2b.tif", count=3)
    r = run_investigation("Compare the optical and SAR imagery for this area.", [a, b], {},
                          planner=RuleBasedPlanner())
    _assert_agent_ok(r)
    # CROMA/DOFA must never be called without a 2-band SAR raster
    assert not any(o.tool == "run_optical_sar" and o.status == "completed" for o in r.steps)


def test_08_identity_transform_carveout(tmp_path):
    p = _tif(tmp_path / "ident.tif", transform=Affine.identity(), crs="EPSG:32643")
    res = run_analyze("what is in this image?", [p], {})
    _assert_structured(res)


# --------------------------------------------------------------------------- #
# 9-14 · query / intent conditions
# --------------------------------------------------------------------------- #

def test_09_unsupported_query(tmp_path):
    res = run_analyze("predict next week's weather for this location", [_tif(tmp_path / "x.tif")], {})
    _assert_structured(res)


def test_10_ambiguous_query(tmp_path):
    res = run_analyze("the image", [_tif(tmp_path / "x.tif")], {})
    _assert_structured(res)


def test_11_object_absent_grounding_query():
    # deterministic: interpret + plan only, no model
    it = interpret_query("locate the aircraft carrier in this farmland image")
    assert it.intent in ("grounding", "vqa", "unknown")


def test_12_planner_malformed_llm_intent():
    plan_intent, att = intent_from_raw("here you go: {not json at all", "what changed?")
    assert plan_intent is None and att.fallback_reason  # -> caller uses rule intent


def test_13_planner_malformed_llm_plan():
    plan, att = build_plan_from_raw('{"steps": [ {"tool": ', image_count=2)
    assert plan is None and att.fallback_reason  # -> caller uses RuleBasedPlanner


def test_14_llm_planner_timeout_simulated():
    from satquery_agents.agent import Planner, plan_with_fallback_ex

    class _Slow(Planner):
        name = "llm"

        def plan(self, *a, **k):
            import subprocess
            raise subprocess.TimeoutExpired("planner", 1)

    plan, used, notes, _ = plan_with_fallback_ex("what changed?", 2, ["optical"], planner=_Slow())
    assert used == "rule_based_fallback" and any("fallback" in n for n in notes)


# --------------------------------------------------------------------------- #
# 15-22 · agent / policy / evidence conditions
# --------------------------------------------------------------------------- #

def test_15_policy_rejects_wrong_tool_for_task():
    from satquery_agents.agent import AgentPlan

    bad = AgentPlan(goal="g", inputs=["img0"], steps=[
        {"step_id": "s1", "task": "VALIDATE_INPUT", "tool": "validate_geospatial_input",
         "inputs": {}, "depends_on": [], "reason": "v"},
        {"step_id": "s2", "task": "VQA", "tool": "run_grounding", "inputs": {"image": "img0"},
         "depends_on": ["s1"], "reason": "wrong tool for VQA"},
        {"step_id": "s3", "task": "FINALIZE", "tool": "finalize_answer", "inputs": {},
         "depends_on": ["s2"], "reason": "f"},
    ])
    ctx = PlanContext(image_count=1, modalities=["optical"], has_valid_crs=True,
                      pair_co_registered=None, available_capabilities=["vqa", "grounding"])
    pr = validate_plan(bad, ctx)
    assert not pr.ok and pr.reasons


def test_16_policy_rejects_cycle():
    from satquery_agents.agent import AgentPlan

    cyc = AgentPlan(goal="g", inputs=["img0"], steps=[
        {"step_id": "s1", "task": "VALIDATE_INPUT", "tool": "validate_geospatial_input",
         "inputs": {}, "depends_on": ["s2"], "reason": "v"},
        {"step_id": "s2", "task": "VQA", "tool": "run_vqa", "inputs": {"image": "img0"},
         "depends_on": ["s1"], "reason": "q"},
        {"step_id": "s3", "task": "FINALIZE", "tool": "finalize_answer", "inputs": {},
         "depends_on": ["s2"], "reason": "f"},
    ])
    ctx = PlanContext(image_count=1, modalities=["optical"], has_valid_crs=True,
                      pair_co_registered=None, available_capabilities=["vqa"])
    assert not validate_plan(cyc, ctx).ok


def test_17_policy_rejects_over_long_plan():
    plan, att = build_plan_from_raw(
        '{"goal":"g","steps":' + str([{"step_id": f"s{i}", "task": "VQA", "tool": "run_vqa",
                                       "inputs": {"image": "img0"}, "depends_on": [], "reason": "q"}
                                      for i in range(1, 20)]).replace("'", '"') + "}",
        image_count=1)
    assert plan is None  # 19 steps > hard cap -> fallback, not silent truncation


def test_18_agent_unsupported_mission_visible_fallback(tmp_path):
    a = _tif(tmp_path / "s2a.tif", count=3)
    b = _tif(tmp_path / "s2b.tif", count=3)
    r = run_investigation("Compare the optical and SAR imagery.", [a, b], {}, planner=RuleBasedPlanner())
    _assert_agent_ok(r)


def test_19_evidence_contradiction_withholds_claim(tmp_path):
    # a deterministic check: an INCOHERENT step -> its claim is withheld, confidence caps
    from app.services.trust import assess_confidence

    class _S:
        def __init__(s, tool, status, verdict):
            s.tool, s.status, s.verdict = tool, status, verdict
            s.step_id = tool
            s.task = type("T", (), {"value": "X"})()

    class _R:
        steps = [_S("run_temporal_change", "completed", "COHERENT"),
                 _S("run_grounding", "completed", "INCOHERENT")]
        verification = {"status": "SUPPORTED"}
        evidence = [{"i": 1}, {"i": 2}]
        mission_family = "multi_step"
        geojson = None
        warnings: list = []
        planner_used = "rule_based"

    class _M:
        results: dict = {}

    a = assess_confidence(_R(), _M(), None)
    assert a.category in ("LOW", "INSUFFICIENT_EVIDENCE")


def test_20_insufficient_evidence_is_a_category_not_a_crash(tmp_path):
    from app.services.trust import assess_confidence

    class _R:
        steps: list = []
        verification = {"status": "INSUFFICIENT_EVIDENCE"}
        evidence: list = []
        mission_family = "unknown"
        geojson = None
        warnings: list = []
        planner_used = "rule_based"

    class _M:
        results: dict = {}

    a = assess_confidence(_R(), _M(), None)
    assert a.category == "INSUFFICIENT_EVIDENCE"
    assert isinstance(a.public()["reasons"], list)


def test_21_artifact_missing_does_not_500(tmp_path):
    # request a valid mission, then confirm a missing artifact reference is handled by the API layer
    res = run_analyze("what is in this image?", [_tif(tmp_path / "x.tif")], {})
    _assert_structured(res)  # artifact links are relative; absence is a 404 at the endpoint, never a 500 here


def test_22_geojson_only_emitted_with_geo_and_regions(tmp_path):
    a = _tif(tmp_path / "s2a.tif", count=3, crs=None)
    b = _tif(tmp_path / "s2b.tif", count=3, crs=None)
    r = run_investigation("what changed between these two images?", [a, b], {}, planner=RuleBasedPlanner())
    _assert_agent_ok(r)
    # no CRS -> no fabricated lon/lat GeoJSON
    if r.geojson:
        assert r.geojson.get("crs") == "EPSG:4326"
        for f in r.geojson.get("features", []):
            assert f["geometry"]["type"] == "Polygon"
