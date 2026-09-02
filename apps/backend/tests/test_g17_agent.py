"""G17 — hybrid architecture: typed Intent, deterministic PlanSynthesizer,
HybridPlanner + fallback, and the evidence-derived trust/confidence layer.

The live local LLM is NOT exercised here (CPU-only 2B). Those runs live in
`evaluation/agent/run_g17_eval.py` + `scripts/demo/run_g17_flagship.py`.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_REPO / "packages" / "agents" / "src"))

from satquery_agents.agent import (  # noqa: E402
    Capability,
    HybridPlanner,
    Intent,
    PlanSynthesizer,
    RuleBasedPlanner,
    TaskFamily,
    derive_intent_rulebased,
    intent_from_raw,
)


# --------------------------------------------------------------------------- #
# typed Intent + repair
# --------------------------------------------------------------------------- #

def test_intent_from_raw_accepts_clean_json():
    raw = json.dumps({
        "goal": "find changes", "task_family": "TEMPORAL_CHANGE",
        "required_capabilities": ["TEMPORAL_CHANGE"], "objects": [],
        "temporal_required": True, "spatial_required": False,
        "comparison_required": False, "investigation_required": False,
        "requested_outputs": ["evidence"], "constraints": [], "ambiguity": "none",
    })
    it, att = intent_from_raw(raw, "what changed?")
    assert it is not None and it.task_family is TaskFamily.TEMPORAL_CHANGE
    assert att.final_source == "llm" and att.schema_status == "ok"


def test_intent_from_raw_repairs_aliases_and_junk_caps():
    raw = "sure: {\"goal\":\"x\",\"task_family\":\"change\",\"required_capabilities\":\"REGIONS\",\"weird\":1}"
    it, att = intent_from_raw(raw, "which regions changed?")
    assert it is not None and it.task_family is TaskFamily.TEMPORAL_CHANGE
    assert Capability.CHANGED_REGIONS in it.required_capabilities
    assert att.final_source == "llm_repaired"
    assert any("task_family" in r for r in att.repairs)


def test_intent_from_raw_no_json_falls_back():
    it, att = intent_from_raw("I can't help with that.", "mission")
    assert it is None and att.fallback_reason


def test_intent_from_raw_unknown_family_becomes_unsupported():
    it, _ = intent_from_raw('{"goal":"g","task_family":"TELEPORT","required_capabilities":[]}', "m")
    assert it is not None and it.task_family is TaskFamily.UNSUPPORTED


# --------------------------------------------------------------------------- #
# deterministic intent extractor
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("mission, n, mods, fam", [
    ("What is in this image?", 1, ["optical"], "VQA"),
    ("Where is the largest ship?", 1, ["optical"], "GROUNDING"),
    ("What type of scene is this?", 1, ["optical"], "SCENE"),
    ("What changed between these two images?", 2, ["optical"], "TEMPORAL_CHANGE"),
    ("Describe what kind of change occurred.", 2, ["optical"], "SEMANTIC_CHANGE"),
    ("Compare the optical and SAR imagery.", 2, ["optical", "sar"], "OPTICAL_SAR"),
    ("Investigate: changes, buildings, and SAR evidence.", 4, ["optical", "sar"], "INVESTIGATION"),
])
def test_derive_intent_rulebased_classifies(mission, n, mods, fam):
    it = derive_intent_rulebased(mission, n, mods)
    assert it.task_family.value == fam
    assert it.source == "rule_based"


# --------------------------------------------------------------------------- #
# PlanSynthesizer reproduces RuleBasedPlanner  (zero regression)
# --------------------------------------------------------------------------- #

_MISSIONS = [
    ("What is in this image?", 1, ["optical"]),
    ("Where is the largest ship?", 1, ["optical"]),
    ("What kind of scene is this?", 1, ["optical"]),
    ("What changed between these two images?", 2, ["optical"]),
    ("Describe what kind of change occurred between these images.", 2, ["optical"]),
    ("Which regions changed significantly?", 2, ["optical"]),
    ("Compare the optical and SAR imagery for this area.", 2, ["optical", "sar"]),
    ("Investigate this area: identify significant changes, locate the affected buildings, "
     "and use SAR to characterise them.", 4, ["optical", "sar"]),
    ("Predict next week's weather.", 1, ["optical"]),
    ("the image", 1, ["optical"]),
]


def test_synth_matches_rulebased_plan_tool_sequence():
    syn = PlanSynthesizer()
    for m, n, mods in _MISSIONS:
        rb = [s.tool for s in RuleBasedPlanner().plan(m, n, mods).steps]
        it = derive_intent_rulebased(m, n, mods)
        sy = [s.tool for s in syn.synthesize(it, n, mods, mission=m).steps]
        assert rb == sy, f"{m!r}\n rule : {rb}\n synth: {sy}"


def test_synth_trims_regions_only_missions_no_grounding():
    """A TEMPORAL_CHANGE + CHANGED_REGIONS intent (not investigation) -> regions but
    NOT grounding / SAR (the G16 over-planning flaw, fixed in the synthesizer)."""
    it = Intent(goal="which regions changed", task_family=TaskFamily.TEMPORAL_CHANGE,
                required_capabilities=[Capability.TEMPORAL_CHANGE, Capability.CHANGED_REGIONS])
    tools = [s.tool for s in PlanSynthesizer().synthesize(it, 2, ["optical"]).steps]
    assert "run_temporal_change" in tools and "extract_changed_regions" in tools
    assert "run_grounding" not in tools and "run_optical_sar" not in tools


# --------------------------------------------------------------------------- #
# HybridPlanner + fallback (Part 13)
# --------------------------------------------------------------------------- #

class _MockExtractor:
    def __init__(self, intent=None, raise_exc=None):
        self._intent, self._raise = intent, raise_exc
        self.last_attempt = None

    def extract(self, mission, image_count, modalities):
        from satquery_agents.agent.intent import IntentAttempt
        if self._raise:
            raise self._raise
        att = IntentAttempt(final_source="llm" if self._intent else "none")
        return self._intent, att


def test_hybrid_uses_llm_intent_when_available():
    it = Intent(goal="g", task_family=TaskFamily.TEMPORAL_CHANGE,
                required_capabilities=[Capability.TEMPORAL_CHANGE], source="llm")
    hp = HybridPlanner(extractor=_MockExtractor(intent=it))
    plan, intent, att = hp.plan_ex("what changed?", 2, ["optical"])
    assert [s.tool for s in plan.steps][1] == "run_temporal_change"
    assert intent.source == "llm" and att.final_source == "llm"


def test_hybrid_falls_back_to_rule_intent_visibly():
    hp = HybridPlanner(extractor=_MockExtractor(raise_exc=RuntimeError("model gone")))
    plan, intent, att = hp.plan_ex("investigate changes and buildings and SAR", 4, ["optical", "sar"])
    assert intent.source == "rule_based_fallback"
    assert att.final_source == "rule_based_fallback" and att.fallback_reason
    assert "run_temporal_change" in [s.tool for s in plan.steps]  # still a real plan


def test_hybrid_none_intent_falls_back():
    hp = HybridPlanner(extractor=_MockExtractor(intent=None))
    _plan, intent, att = hp.plan_ex("what changed?", 2, ["optical"])
    assert intent.source == "rule_based_fallback"


# --------------------------------------------------------------------------- #
# trust / confidence layer
# --------------------------------------------------------------------------- #

def _fake(**kw):
    class _O:
        pass

    o = _O()
    o.steps = kw.get("steps", [])
    o.verification = kw.get("verification", {"status": "SUPPORTED"})
    o.evidence = kw.get("evidence", [{"x": 1}])
    o.mission_family = kw.get("family", "temporal")
    o.geojson = kw.get("geojson")
    o.warnings = kw.get("warnings", [])
    o.planner_used = kw.get("planner_used", "hybrid_llm")
    return o


class _Step:
    def __init__(self, tool, status="completed", verdict="COHERENT"):
        self.tool, self.status, self.verdict = tool, status, verdict
        self.step_id = tool
        self.task = type("T", (), {"value": "X"})()


class _Mem:
    results: dict = {}


def test_confidence_supported_change_is_high_or_medium():
    from app.services.trust import assess_confidence
    res = _fake(steps=[_Step("run_temporal_change")], verification={"status": "SUPPORTED"},
               geojson={"type": "FeatureCollection", "features": [1, 2]})
    a = assess_confidence(res, _Mem(), None)
    assert a.category in ("HIGH", "MEDIUM") and a.hard_rule is None
    assert any("SUPPORTED" in r for r in a.reasons)


def test_confidence_contradicted_is_insufficient():
    from app.services.trust import assess_confidence
    res = _fake(steps=[_Step("run_temporal_change")], verification={"status": "CONTRADICTED"})
    a = assess_confidence(res, _Mem(), None)
    assert a.category == "INSUFFICIENT_EVIDENCE" and "CONTRADICTED" in a.hard_rule


def test_confidence_no_evidence_is_insufficient():
    from app.services.trust import assess_confidence
    res = _fake(steps=[_Step("run_temporal_change")], evidence=[])
    a = assess_confidence(res, _Mem(), None)
    assert a.category == "INSUFFICIENT_EVIDENCE"


def test_confidence_primary_specialist_failed_is_insufficient():
    from app.services.trust import assess_confidence
    res = _fake(steps=[_Step("run_temporal_change", status="failed")], family="temporal")
    a = assess_confidence(res, _Mem(), None)
    assert a.category == "INSUFFICIENT_EVIDENCE"


def test_confidence_never_reports_a_probability():
    from app.services.trust import assess_confidence
    a = assess_confidence(_fake(steps=[_Step("run_vqa")], family="single_step"), _Mem(), None)
    pub = a.public()
    assert "probability" not in json.dumps(pub).lower() or "not a calibrated probability" in pub["note"].lower()
    assert pub["category"] in ("HIGH", "MEDIUM", "LOW", "INSUFFICIENT_EVIDENCE")


# --------------------------------------------------------------------------- #
# G17 artifacts
# --------------------------------------------------------------------------- #

def test_g17_scaffolding_exists():
    for rel in ("docs/G17_ARCHITECTURE_DECISION.md", "docs/G17_TRUST_LAYER.md",
                "evaluation/agent/run_g17_eval.py", "evaluation/agent/build_missions_100.py",
                "evaluation/agent/frozen_missions_100.json",
                "packages/agents/src/satquery_agents/agent/intent.py",
                "apps/backend/app/services/trust.py"):
        assert (_REPO / rel).exists(), rel


def test_100_frozen_missions_have_expected_intent():
    d = json.loads((_REPO / "evaluation/agent/frozen_missions_100.json").read_text())
    ms = d["missions"]
    assert len(ms) == 100
    from collections import Counter
    assert Counter(m["category"] for m in ms) == {
        "single_step": 20, "temporal": 20, "optical_sar": 20, "multi_step": 20, "adversarial": 20}
    assert all("expected_intent" in m and "task_family" in m["expected_intent"] for m in ms)
    # first 50 unchanged ids
    assert [m["mission_id"] for m in ms[:10]] == [f"ss-{i:02d}" for i in range(1, 11)]
