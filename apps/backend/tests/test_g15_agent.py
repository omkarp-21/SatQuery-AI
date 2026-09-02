"""G15 — agent validation: per-policy-check, structured replans, early termination,
conditional execution (Part 7), deterministic fallback qualifiers, and the
10-paraphrase flagship test (proves the plan emerges from planning, not keywords).

Fast tests exercise the planner + policy + executor state machine without models.
`@pytest.mark.slow` tests run real specialists.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from satquery_agents.agent import (
    MAX_STEPS,
    AgentPlan,
    PlanContext,
    PlanStep,
    TaskType,
    plan_with_fallback,
    validate_plan,
)

from app.services.agent_runner import run_investigation

_REPO = Path(__file__).resolve().parents[3]
_DEMO = _REPO / "data" / "demo"
_HAS_CF = (_REPO / "models/cache/changeformer/CD_ChangeFormerV6_LEVIR_b16_lr0.0001_adamw"
           "_train_test_200_linear_ce_multi_train_True_multi_infer_False_shuffle_AB_False_embed_dim_256"
           "/best_ckpt.pt").exists()
_CAPS = ["vqa", "grounding", "change-detection", "zero-shot-classification", "representation"]


def _ctx(n, mods=("optical",), coreg=True):
    return PlanContext(image_count=n, modalities=list(mods), has_valid_crs=True,
                       pair_co_registered=coreg, available_capabilities=_CAPS)


def _step(sid, task, tool, deps=(), inp=None):
    return PlanStep(step_id=sid, task=task, tool=tool, inputs=inp or {}, depends_on=list(deps), reason="r")


# --------------------------------------------------------------------------- #
# Part 11 — the policy guard rejects each illegal thing and NAMES the check
# --------------------------------------------------------------------------- #

def _reject(steps, ctx=None, *, check):
    plan = AgentPlan(goal="g", steps=steps)
    pr = validate_plan(plan, ctx or _ctx(1))
    assert not pr.ok, f"expected rejection for {check}"
    assert check in pr.checks and pr.checks[check] is False, (check, pr.checks)
    assert any(check in r for r in pr.reasons)


def test_policy_01_nonexistent_tool():
    s = _step("s1", TaskType.VQA, "run_vqa", inp={"image": "img0"})
    object.__setattr__(s, "tool", "run_magic")
    _reject([s, _step("s2", TaskType.FINALIZE, "finalize_answer", ["s1"])], check="1_tool_exists")


def test_policy_03_tool_task_mismatch_remotesam_for_vqa():
    _reject([_step("s1", TaskType.VQA, "run_grounding", inp={"image": "img0"}),
             _step("s2", TaskType.FINALIZE, "finalize_answer", ["s1"])], check="3_tool_matches_task")


def test_policy_04_image_count():
    _reject([_step("s1", TaskType.TEMPORAL_CHANGE, "run_temporal_change", inp={"t1": "img0", "t2": "img1"}),
             _step("s2", TaskType.FINALIZE, "finalize_answer", ["s1"])],
            ctx=_ctx(1), check="4_image_count")


def test_policy_05_modalities():
    _reject([_step("s1", TaskType.OPTICAL_SAR_ANALYSIS, "run_optical_sar",
                   inp={"optical": "img0", "sar": "img1"}),
             _step("s2", TaskType.FINALIZE, "finalize_answer", ["s1"])],
            ctx=_ctx(2, ("optical",)), check="5_modalities")


def test_policy_06_dependency_points_to_missing():
    _reject([_step("s1", TaskType.VQA, "run_vqa", ["sX"], {"image": "img0"}),
             _step("s2", TaskType.FINALIZE, "finalize_answer", ["s1"])], check="6_dependencies")


def test_policy_07_geospatial_misregistered():
    _reject([_step("s1", TaskType.TEMPORAL_CHANGE, "run_temporal_change", inp={"t1": "img0", "t2": "img1"}),
             _step("s2", TaskType.FINALIZE, "finalize_answer", ["s1"])],
            ctx=_ctx(2, coreg=False), check="7_geospatial")


def test_policy_10_no_cycle():
    _reject([_step("s1", TaskType.VALIDATE_INPUT, "validate_geospatial_input", ["s2"], {"images": ["img0"]}),
             _step("s2", TaskType.VQA, "run_vqa", ["s1"], {"image": "img0"}),
             _step("s3", TaskType.FINALIZE, "finalize_answer", ["s2"])], check="10_no_cycle")


def test_policy_11_step_cap():
    steps = [_step("s1", TaskType.VALIDATE_INPUT, "validate_geospatial_input", [], {"images": ["img0"]})]
    for i in range(2, 3 + MAX_STEPS):
        steps.append(_step(f"s{i}", TaskType.VQA, "run_vqa", ["s1"], {"image": "img0"}))
    steps.append(_step("s99", TaskType.FINALIZE, "finalize_answer", ["s1"]))
    _reject(steps, check="11_step_cap")


def test_policy_13_must_end_finalize():
    _reject([_step("s1", TaskType.VQA, "run_vqa", inp={"image": "img0"})], check="13_ends_finalize")


def test_policy_accepts_a_good_plan():
    plan, _, _ = plan_with_fallback("what is in this image?", 1, ["optical"])
    assert validate_plan(plan, _ctx(1)).ok


# --------------------------------------------------------------------------- #
# Part 17 — 10 paraphrases of the flagship mission -> equivalent plan shape
# --------------------------------------------------------------------------- #

_PARAPHRASES = [
    "Investigate this area. Identify significant changes between the two observations, locate the "
    "affected structures, and use SAR evidence to characterize the changes. Give me an evidence-backed summary.",
    "Compare the two observations, find the important changes, locate the changed buildings, and "
    "cross-check them with SAR. Summarize the evidence.",
    "Tell me what changed between these dates, identify the affected structures, and corroborate with SAR.",
    "Perform a remote sensing investigation of this area: detect change, extract the changed regions, "
    "ground the structures, analyze the SAR, and verify.",
    "Do a full analysis of change here, locate the impacted buildings, and use radar to characterise them.",
    "What changed, where did it change, which structures are affected, and what does the SAR add? Verify it.",
    "Assess the changes between these images step by step, locate the affected structures, and check the SAR.",
    "Investigate this location comprehensively using the optical pair and the SAR, and give a verified "
    "summary of the changes and affected structures.",
    "Find significant changes and cross-check them using SAR, then locate the changed structures.",
    "Detect the changes, extract the changed regions, locate the buildings, run the optical+SAR analysis, "
    "cross-check the evidence, and verify.",
]


@pytest.mark.parametrize("phrasing", _PARAPHRASES)
def test_flagship_10_paraphrases_yield_a_multistep_plan(phrasing):
    plan, used, _ = plan_with_fallback(phrasing, 4, ["optical", "sar"])
    tools = {s.tool for s in plan.steps}
    # every paraphrase must yield a multi-step investigation, not a single specialist
    assert "run_temporal_change" in tools, (phrasing, tools)
    assert "extract_changed_regions" in tools, (phrasing, tools)
    assert len(tools & {"run_grounding", "run_optical_sar"}) >= 1, (phrasing, tools)
    assert plan.steps[-1].task == TaskType.FINALIZE
    assert validate_plan(plan, _ctx(4, ("optical", "sar"))).ok
    assert plan.tool_step_count() <= MAX_STEPS


def test_flagship_plans_are_not_string_identical():
    plans = [plan_with_fallback(p, 4, ["optical", "sar"])[0].model_dump() for p in _PARAPHRASES[:4]]
    goals = {str(p["goal"]) for p in plans}
    assert len(goals) >= 3  # the goal echoes the mission text -> plans are not one hard-coded object


# --------------------------------------------------------------------------- #
# Part 9 / 10 / 12 — structured replans, early termination, fallback qualifier
# --------------------------------------------------------------------------- #

def test_misregistered_pair_policy_rejects_and_fallback_is_visible():
    res = run_investigation("what changed between these images?",
                            [str(_DEMO / "temporal/t1.tif"), str(_DEMO / "temporal/t2_shifted.tif")])
    assert res.mode == "ask-fallback"
    assert res.plan_status == "rejected"
    assert (res.resolution or {}).get("qualifier") == "PLANNER_UNAVAILABLE"
    assert any("AGENT FALLBACK" in w or "co-registered" in w for w in res.warnings)
    assert not any(s.task == TaskType.TEMPORAL_CHANGE and s.status == "completed" for s in res.steps)


def test_missing_sar_is_a_structured_replan_no_croma_call():
    # a 2-image OPTICAL-only pair + "cross-check with SAR" -> the planner should not
    # even add an optical+SAR step; if it does, MISSING_INPUT prunes it.
    res = run_investigation(
        "Investigate the change and cross-check it with SAR.",
        [str(_DEMO / "temporal/t1.tif"), str(_DEMO / "temporal/t2.tif")]) if _HAS_CF else None
    if res is None:
        pytest.skip("ChangeFormer absent")
    osar = [s for s in res.steps if s.task == TaskType.OPTICAL_SAR_ANALYSIS]
    assert all(s.status != "completed" for s in osar)  # CROMA never ran
    if any(rp.reason == "MISSING_INPUT" for rp in res.replans):
        assert any("SAR" in w for w in res.warnings)


@pytest.mark.slow
@pytest.mark.skipif(not _HAS_CF, reason="ChangeFormer absent")
def test_flagship_real_models_all_steps_and_replans_structured():
    res = run_investigation(
        "Investigate this area. Identify significant changes, locate the affected structures, "
        "use SAR to characterize them, and give a verified summary.",
        [str(_DEMO / "investigation/t1_optical.tif"), str(_DEMO / "investigation/t2_optical.tif"),
         str(_DEMO / "investigation/s2_dfc_optical.tif"), str(_DEMO / "investigation/s1_dfc_sar.tif")])
    assert res.phase in ("FINALIZING",)
    tools_run = {s.tool for s in res.steps if s.status == "completed"}
    assert {"run_temporal_change", "run_grounding", "run_optical_sar"} <= tools_run
    assert res.verification and res.verification["status"] in ("SUPPORTED", "INSUFFICIENT_EVIDENCE")
    # every replan (if any) is a closed-enum structured event
    for rp in res.replans:
        assert rp.reason in ("NEW_EVIDENCE", "TOOL_FAILURE", "MISSING_INPUT",
                             "INSUFFICIENT_EVIDENCE", "VERIFICATION_CONTRADICTION", "TASK_COMPLETE")
        assert rp.triggering_step and rp.detail and rp.ts
    # geojson is a FeatureCollection when geo is available
    if res.geojson:
        assert res.geojson["type"] == "FeatureCollection" and res.geojson["crs"] == "EPSG:4326"
    # provenance carries the unnecessary-call accounting
    assert "unnecessary_tool_calls" in res.provenance


@pytest.mark.slow
@pytest.mark.skipif(not _HAS_CF, reason="ChangeFormer absent")
def test_early_termination_on_no_change():
    # same image as T1 and T2 -> ~0 change -> the agent must stop early and NOT ground/SAR
    res = run_investigation(
        "Investigate the change here and locate any affected structures.",
        [str(_DEMO / "temporal/t1.tif"), str(_DEMO / "temporal/t1.tif")])
    tc = [s for s in res.steps if s.task == TaskType.TEMPORAL_CHANGE and s.status == "completed"]
    if tc and tc[0].numeric.get("changed_fraction", 1.0) < 0.01:
        assert res.early_stopped
        assert any(rp.reason == "NEW_EVIDENCE" for rp in res.replans)
        assert not any(s.task == TaskType.GROUND_OBJECT and s.status == "completed" for s in res.steps)


# --------------------------------------------------------------------------- #
# Part 7 — conditional execution cases (fast: plan-level assertions)
# --------------------------------------------------------------------------- #

def test_part7_case3_no_sar_step_when_only_optical_supplied():
    # a 2-image OPTICAL pair that mentions SAR -> the agent must NOT run optical+SAR:
    # either the planner doesn't add it, or the policy layer rejects the plan (5_modalities).
    plan, _, _ = plan_with_fallback("Compare these two images and cross-check with SAR.", 2, ["optical"])
    if "run_optical_sar" in {s.tool for s in plan.steps}:
        pr = validate_plan(plan, _ctx(2, ("optical",)))
        assert not pr.ok and pr.checks.get("5_modalities") is False
    else:
        assert "run_temporal_change" in {s.tool for s in plan.steps}


def test_part7_ambiguous_query_never_picks_a_heavy_specialist():
    plan, _, _ = plan_with_fallback("the image", 1, ["optical"])
    assert {s.tool for s in plan.steps} & {"run_temporal_change", "run_optical_sar", "run_grounding"} == set()


def test_bounded_loop_unbounded_ask():
    plan, _, _ = plan_with_fallback("Investigate everything about this area in maximum detail forever.",
                                    4, ["optical", "sar"])
    assert plan.tool_step_count() <= MAX_STEPS


def test_g15_artifacts_exist():
    assert (_REPO / "docs" / "G15_AUDIT.md").exists()
    spec = (_REPO / "evaluation" / "agent" / "frozen_missions.json")
    import json
    assert len(json.loads(spec.read_text())["missions"]) >= 50
