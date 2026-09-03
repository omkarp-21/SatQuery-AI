"""G18 Part 7 — validate the trust/confidence RULE ENGINE against its own
written policy (docs/G17_TRUST_LAYER.md) on 30 frozen synthetic cases.

This is NOT calibration and NOT a probability check. It asserts that
`assess_confidence` produces the category the deterministic rules require for
each constructed executed-investigation state, across the seven required
scenario families: strong / partial / contradictory / missing evidence, failed
specialist, invalid geometry, ambiguous request.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.services.trust import assess_confidence

_CASES = json.loads((Path(__file__).resolve().parents[3]
                     / "evaluation" / "agent" / "trust_cases.json").read_text())["cases"]


class _Task:
    def __init__(self, v: str) -> None:
        self.value = v


class _Step:
    _TASK = {
        "run_temporal_change": "TEMPORAL_CHANGE", "run_semantic_temporal_baseline": "SEMANTIC_CHANGE",
        "run_grounding": "GROUND_OBJECT", "run_vqa": "VQA", "run_scene_retrieval": "SCENE_UNDERSTANDING",
        "run_optical_sar": "OPTICAL_SAR_ANALYSIS", "extract_changed_regions": "EXTRACT_CHANGED_REGIONS",
        "cross_check_evidence": "CROSS_CHECK_EVIDENCE",
    }

    def __init__(self, tool: str, status: str, verdict: str, idx: int) -> None:
        self.tool, self.status, self.verdict = tool, status, verdict
        self.step_id = f"s{idx}"
        self.task = _Task(self._TASK.get(tool, "VQA"))


class _Res:
    def __init__(self, c: dict) -> None:
        self.steps = [_Step(t, s, v, i + 1) for i, (t, s, v) in enumerate(c.get("steps", []))]
        self.verification = {"status": c.get("verification", "INSUFFICIENT_EVIDENCE")}
        self.evidence = [{"i": i} for i in range(c.get("evidence", 0))]
        self.mission_family = c.get("family", "unknown")
        nf = c.get("geojson_features", 0)
        self.geojson = {"type": "FeatureCollection", "features": list(range(nf))} if nf else None
        self.warnings = list(c.get("warnings", []))
        self.planner_used = c.get("planner_used", "rule_based")


class _Mem:
    def __init__(self, c: dict) -> None:
        self.results = {}
        cc = c.get("cross_check_inside")
        if cc is not None:
            inside, total = cc
            self.results["cc"] = {"matches": [{"centroid_in_changed_region": k < inside}
                                              for k in range(total)]}
        # attach the cross-check payload to a synthetic step id the assessor scans by task
        self._cc_payload = self.results.get("cc")

    def get_cc_for(self, res: _Res):
        for o in res.steps:
            if o.task.value == "CROSS_CHECK_EVIDENCE":
                self.results[o.step_id] = self._cc_payload
        return self


class _Intent:
    def __init__(self, c: dict) -> None:
        self.task_family = c.get("family")
        self.required_capabilities = []
        self.comparison_required = bool(c.get("comparison_required"))
        self.ambiguity = c.get("ambiguity", "none")


def _mk(c: dict):
    res = _Res(c)
    # synthesise a cross_check_evidence step when the case gives cross_check_inside
    if c.get("cross_check_inside") is not None and not any(
            o.task.value == "CROSS_CHECK_EVIDENCE" for o in res.steps):
        res.steps.append(_Step("cross_check_evidence", "completed", "COHERENT", len(res.steps) + 1))
    mem = _Mem(c).get_cc_for(res)
    # sar skip
    if c.get("sar_skipped"):
        res.steps.append(_Step("run_optical_sar", "skipped", "NOT_APPLICABLE", len(res.steps) + 1))
    return res, mem, _Intent(c)


@pytest.mark.parametrize("case", _CASES, ids=[c["id"] for c in _CASES])
def test_trust_category_matches_policy(case):
    res, mem, intent = _mk(case)
    a = assess_confidence(res, mem, None, intent=intent)
    assert a.category == case["expect"], (
        f"{case['id']} ({case['cat']}): got {a.category} (score {a.score}, "
        f"hard_rule={a.hard_rule}) expected {case['expect']}\n  reasons: {a.reasons}")
    # invariants that must hold for every case
    assert a.category in ("HIGH", "MEDIUM", "LOW", "INSUFFICIENT_EVIDENCE")
    pub = a.public()
    assert "not a calibrated probability" in pub["note"].lower()
    assert isinstance(pub["reasons"], list) and pub["reasons"]  # a WHY is always given


def test_all_seven_scenario_families_covered():
    cats = {c["cat"] for c in _CASES}
    assert cats == {"strong_evidence", "partial_evidence", "contradictory_evidence",
                    "missing_evidence", "failed_specialist", "invalid_geometry", "ambiguous_request"}
    assert len(_CASES) >= 30


def test_hard_rules_dominate_score():
    """A CONTRADICTED verification is INSUFFICIENT_EVIDENCE no matter how much
    other positive evidence there is."""
    res, mem, intent = _mk({"family": "multi_step", "verification": "CONTRADICTED",
                            "steps": [["run_temporal_change", "completed", "COHERENT"],
                                      ["run_grounding", "completed", "COHERENT"],
                                      ["run_optical_sar", "completed", "COHERENT"]],
                            "evidence": 9, "geojson_features": 9, "cross_check_inside": [3, 3]})
    a = assess_confidence(res, mem, None, intent=intent)
    assert a.category == "INSUFFICIENT_EVIDENCE" and a.hard_rule
