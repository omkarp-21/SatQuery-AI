"""G16 - real-LLM planner: schema repair, attempt tracking, fallback hierarchy,
compact prompt, semantic plan scorer, adaptivity fixtures.

The live local LLM is NOT exercised here (CPU-only 2B, minutes per call); those
runs live in `evaluation/agent/run_g16_eval.py` + `scripts/demo/run_g16_flagship.py`.
These tests pin the machinery around it.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_REPO / "packages" / "agents" / "src"))
sys.path.insert(0, str(_REPO / "evaluation" / "agent"))

from satquery_agents.agent import (  # noqa: E402
    AgentPlan,
    LlmPlanner,
    Planner,
    PlanContext,
    RuleBasedPlanner,
    build_plan_from_raw,
    plan_with_fallback_ex,
    repair_plan_dict,
    validate_plan,
)
from satquery_agents.agent.repair import first_json_object  # noqa: E402


# --------------------------------------------------------------------------- #
# first_json_object
# --------------------------------------------------------------------------- #

def test_first_json_object_extracts_from_prose_and_fences():
    obj, st = first_json_object('sure! ```json\n{"a": 1, "b": [2,3]}\n``` done')
    assert st == "ok" and obj == {"a": 1, "b": [2, 3]}


def test_first_json_object_flags_truncated_json():
    obj, st = first_json_object('{"goal":"x","steps":[{"step_id":"s1"')
    assert obj is None and st == "json_error"


def test_first_json_object_flags_no_json():
    obj, st = first_json_object("I cannot help with that.")
    assert obj is None and st == "no_json"


# --------------------------------------------------------------------------- #
# repair layer — safe, intent-preserving
# --------------------------------------------------------------------------- #

def test_repair_maps_near_miss_tool_names_and_tasks():
    raw = json.dumps({"goal": "g", "steps": [
        {"tool": "ground", "inputs": {"image": "img0"}, "reason": "loc"},
    ]})
    plan, att = build_plan_from_raw(raw, image_count=1)
    assert plan is not None
    tools = [s.tool for s in plan.steps]
    assert tools[0] == "validate_geospatial_input"          # prepended
    assert "run_grounding" in tools                          # 'ground' -> canonical
    assert tools[-1] == "finalize_answer" and "verify_result" in tools
    assert att.final_source == "llm_repaired" and att.repair_status == "applied"


def test_repair_coerces_depends_on_and_renumbers():
    obj = {"goal": "g", "steps": [
        {"step_id": "s5", "task": "VALIDATE_INPUT", "tool": "validate_geospatial_input",
         "inputs": {}, "depends_on": [], "reason": "v"},
        {"step_id": "s9", "task": "VQA", "tool": "run_vqa",
         "inputs": {"image": "img0"}, "depends_on": "s5", "reason": "q"},
    ]}
    fixed, repairs = repair_plan_dict(obj, image_count=1)
    ids = [s["step_id"] for s in fixed["steps"]]
    assert ids == [f"s{i}" for i in range(1, len(ids) + 1)]
    # the VQA step's dep now points at the (renumbered) validate step
    vqa = next(s for s in fixed["steps"] if s["tool"] == "run_vqa")
    assert vqa["depends_on"] == ["s1"]


def test_repair_does_not_invent_a_specialist():
    # empty / unusable steps -> no plan (caller must fall back), NOT a fabricated one
    plan, att = build_plan_from_raw('{"goal":"g","steps":[]}', image_count=1)
    assert plan is None and att.fallback_reason


def test_repair_rejects_overlong_plan_rather_than_trimming():
    steps = [{"step_id": f"s{i}", "task": "VQA", "tool": "run_vqa",
              "inputs": {"image": "img0"}, "depends_on": [], "reason": "q"} for i in range(1, 20)]
    plan, att = build_plan_from_raw(json.dumps({"goal": "g", "steps": steps}), image_count=1)
    assert plan is None  # 19 steps > hard cap -> fallback, not silent truncation


def test_attempt_public_view_hides_raw_text():
    raw = json.dumps({"goal": "g", "steps": [
        {"step_id": "s1", "task": "VALIDATE_INPUT", "tool": "validate_geospatial_input",
         "inputs": {}, "depends_on": [], "reason": "v"},
        {"step_id": "s2", "task": "VQA", "tool": "run_vqa", "inputs": {"image": "img0"},
         "depends_on": ["s1"], "reason": "q"},
        {"step_id": "s3", "task": "VERIFY", "tool": "verify_result", "inputs": {},
         "depends_on": ["s2"], "reason": "v"},
        {"step_id": "s4", "task": "FINALIZE", "tool": "finalize_answer", "inputs": {},
         "depends_on": ["s3"], "reason": "f"},
    ]})
    _plan, att = build_plan_from_raw(raw, image_count=1)
    pub = att.public()
    assert "raw_output" not in pub and "raw" not in json.dumps(pub)
    assert pub["parse_status"] == "ok" and pub["schema_status"] == "ok"


# --------------------------------------------------------------------------- #
# fallback hierarchy (Part 14) — LLM -> schema -> policy -> rule -> execution
# --------------------------------------------------------------------------- #

class _NoOutput(Planner):
    name = "llm"

    def plan(self, mission, image_count, modalities):  # noqa: D401
        raise ValueError("planner produced no JSON object")


def test_fallback_is_visible_and_typed_when_llm_yields_nothing():
    plan, used, notes, att = plan_with_fallback_ex("what changed here?", 2, ["optical"],
                                                   planner=_NoOutput())
    assert isinstance(plan, AgentPlan)
    assert used == "rule_based_fallback"
    assert any("fallback" in n for n in notes)


def test_rule_planner_never_reports_an_llm_attempt():
    plan, used, notes, att = plan_with_fallback_ex("what is in this image?", 1, ["optical"],
                                                   planner=RuleBasedPlanner())
    assert used == "rule_based" and att is None


def test_llm_repaired_plans_are_tagged_distinctly():
    class _Repairable(LlmPlanner):
        def _local_qwen(self, prompt):  # noqa: D401
            return (json.dumps({"goal": "g", "steps": [
                {"tool": "run_temporal_change", "inputs": {"t1": "img0", "t2": "img1"}, "reason": "c"},
            ]}), 0.1)

    plan, used, notes, att = plan_with_fallback_ex("what changed?", 2, ["optical"],
                                                   planner=_Repairable())
    assert used == "llm_repaired"
    assert att is not None and att.final_source == "llm_repaired"
    assert "run_temporal_change" in [s.tool for s in plan.steps]


# --------------------------------------------------------------------------- #
# compact prompt
# --------------------------------------------------------------------------- #

def test_compact_prompt_is_small_and_lists_every_tool():
    from satquery_agents.agent.prompts import build_prompt
    from satquery_agents.agent.registry import tool_names

    p = build_prompt("Investigate: change, buildings, SAR.", 4, ["optical", "sar"], compact=True)
    assert len(p) < 7000  # ~1.5k tokens, vs ~11k chars for the verbose prompt
    for t in tool_names():
        assert t in p


# --------------------------------------------------------------------------- #
# semantic plan scorer (Part 6) — does not penalise valid alternative orders
# --------------------------------------------------------------------------- #

def test_scorer_accepts_alternative_valid_order():
    from plan_scorer import score_plan

    mission = {
        "mission_id": "x", "category": "multi_step",
        "expected_tool_set": ["run_temporal_change", "run_grounding", "run_optical_sar"],
        "expected_order_constraints": ["VALIDATE_INPUT < TEMPORAL_CHANGE",
                                       "TEMPORAL_CHANGE < GROUND_OBJECT"],
        "forbid_tools": ["run_vqa"],
    }

    def _mk(order):
        steps = [{"step_id": "s1", "task": "VALIDATE_INPUT", "tool": "validate_geospatial_input",
                  "inputs": {}, "depends_on": [], "reason": "v"}]
        prev = "s1"
        tmap = {"run_temporal_change": "TEMPORAL_CHANGE", "run_grounding": "GROUND_OBJECT",
                "run_optical_sar": "OPTICAL_SAR_ANALYSIS"}
        for i, tool in enumerate(order, start=2):
            steps.append({"step_id": f"s{i}", "task": tmap[tool], "tool": tool,
                          "inputs": {}, "depends_on": [prev], "reason": "r"})
            prev = f"s{i}"
        steps.append({"step_id": f"s{len(order) + 2}", "task": "VERIFY", "tool": "verify_result",
                      "inputs": {}, "depends_on": [prev], "reason": "v"})
        steps.append({"step_id": f"s{len(order) + 3}", "task": "FINALIZE", "tool": "finalize_answer",
                      "inputs": {}, "depends_on": [f"s{len(order) + 2}"], "reason": "f"})
        return AgentPlan(goal="g", inputs=["img0", "img1"], steps=steps)

    a = score_plan(_mk(["run_temporal_change", "run_grounding", "run_optical_sar"]),
                   mission, policy_ok=True, image_count=4, modalities=["optical", "sar"])
    b = score_plan(_mk(["run_temporal_change", "run_optical_sar", "run_grounding"]),
                   mission, policy_ok=True, image_count=4, modalities=["optical", "sar"])
    assert a["semantic_valid"] and b["semantic_valid"]           # both orders valid
    assert a["exact_match"] and not b["exact_match"]             # exact-match differs, validity does not


def test_scorer_flags_forbidden_and_missing_verify():
    from plan_scorer import score_plan

    mission = {"mission_id": "y", "category": "single_step",
               "expected_tool_set": ["run_grounding"], "forbid_tools": ["run_vqa"]}
    plan = AgentPlan(goal="g", inputs=["img0"], steps=[
        {"step_id": "s1", "task": "VALIDATE_INPUT", "tool": "validate_geospatial_input",
         "inputs": {}, "depends_on": [], "reason": "v"},
        {"step_id": "s2", "task": "VQA", "tool": "run_vqa", "inputs": {"image": "img0"},
         "depends_on": ["s1"], "reason": "q"},
        {"step_id": "s3", "task": "FINALIZE", "tool": "finalize_answer", "inputs": {},
         "depends_on": ["s2"], "reason": "f"},
    ])
    sc = score_plan(plan, mission, policy_ok=True, image_count=1, modalities=["optical"])
    assert sc["unsupported_action"] and not sc["verify_present"]
    assert not sc["semantic_valid"] and not sc["required_covered"]


# --------------------------------------------------------------------------- #
# adaptivity fixtures (Part 16)
# --------------------------------------------------------------------------- #

def test_case_b_nochange_fixture_exists_and_differs_only_slightly():
    import numpy as np
    import rasterio

    t1 = _REPO / "data" / "demo" / "investigation" / "t1_optical.tif"
    b = _REPO / "data" / "demo" / "investigation" / "t2_nochange.tif"
    a = _REPO / "data" / "demo" / "investigation" / "t2_optical.tif"
    assert b.exists(), "CASE B fixture missing — scripts/demo/run_g16_flagship.py needs it"
    with rasterio.open(t1) as d:
        x = d.read().astype(int)
    with rasterio.open(b) as d:
        nb = d.read().astype(int)
    with rasterio.open(a) as d:
        na = d.read().astype(int)
    assert np.abs(nb - x).mean() < 5          # CASE B: essentially unchanged
    assert np.abs(na - x).mean() > 20         # CASE A: real change


# --------------------------------------------------------------------------- #
# plan-intent sanity cross-check (G16 exec finding) — a structurally-valid but
# under-scoped LLM plan must not be executed for a mission that needs more
# --------------------------------------------------------------------------- #

def _echo_vqa_plan(n_images: int):
    return AgentPlan(goal="g", inputs=[f"img{i}" for i in range(n_images)], steps=[
        {"step_id": "s1", "task": "VALIDATE_INPUT", "tool": "validate_geospatial_input",
         "inputs": {"images": [f"img{i}" for i in range(n_images)]}, "depends_on": [], "reason": "v"},
        {"step_id": "s2", "task": "VQA", "tool": "run_vqa", "inputs": {"image": "img0"},
         "depends_on": ["s1"], "reason": "q"},
        {"step_id": "s3", "task": "VERIFY", "tool": "verify_result", "inputs": {},
         "depends_on": ["s2"], "reason": "v"},
        {"step_id": "s4", "task": "FINALIZE", "tool": "finalize_answer", "inputs": {},
         "depends_on": ["s3"], "reason": "f"},
    ])


@pytest.mark.parametrize("mission, n, expect_mismatch", [
    ("What objects are visible in this satellite image?", 1, False),
    ("What changed between these two images?", 2, True),
    ("Investigate this area: identify significant changes and locate the affected buildings.", 4, True),
    ("Compare the optical and SAR imagery for this area.", 2, True),
    ("Where is the largest building?", 1, True),          # grounding answered with vqa
    ("Describe the contents of this image.", 1, False),
])
def test_plan_intent_cross_check_flags_underscoped_llm_plans(mission, n, expect_mismatch):
    from app.services.agent_runner import _plan_intent_mismatch

    got = _plan_intent_mismatch(mission, n, _echo_vqa_plan(n))
    assert bool(got) is expect_mismatch, f"{mission!r} -> {got!r}"


def test_plan_intent_cross_check_allows_a_real_multistep_plan():
    from app.services.agent_runner import _plan_intent_mismatch
    from satquery_agents.agent import RuleBasedPlanner

    plan = RuleBasedPlanner().plan(
        "Investigate: identify significant changes, locate the buildings, use SAR to characterise them.",
        4, ["optical", "sar"])
    assert _plan_intent_mismatch("Investigate: changes, buildings, SAR.", 4, plan) is None


# --------------------------------------------------------------------------- #
# G16 artifacts present
# --------------------------------------------------------------------------- #

def test_g16_scaffolding_exists():
    for rel in ("docs/G16_PLANNER_AUDIT.md",
                "evaluation/agent/run_g16_eval.py",
                "evaluation/agent/plan_scorer.py",
                "evaluation/agent/paraphrase_missions.json",
                "scripts/demo/run_g16_flagship.py",
                "scripts/research/planner_infer.py"):
        assert (_REPO / rel).exists(), rel
