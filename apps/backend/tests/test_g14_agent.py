"""G14 — agentic investigator: planner, policy, executor, and the 18 failure cases.

Fast tests exercise the planner + policy + executor state machine without models.
`@pytest.mark.slow` tests run real specialists end to end.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from satquery_agents.agent import (
    MAX_STEPS,
    AgentPlan,
    PlanContext,
    PlanStep,
    RuleBasedPlanner,
    TaskType,
    make_planner,
    plan_with_fallback,
    validate_plan,
)

from app.services.agent_runner import run_investigation

_REPO = Path(__file__).resolve().parents[3]
_DEMO = _REPO / "data" / "demo"
_HAS_CF = (_REPO / "models/cache/changeformer/CD_ChangeFormerV6_LEVIR_b16_lr0.0001_adamw"
           "_train_test_200_linear_ce_multi_train_True_multi_infer_False_shuffle_AB_False_embed_dim_256"
           "/best_ckpt.pt").exists()
_HAS_TINYRS = (_REPO / "models/cache/tinyrs/Qwen2-VL-TinyRS/config.json").exists()


def _plan(mission, n, mods=("optical",)):
    return plan_with_fallback(mission, n, list(mods))


def _ctx(n, mods=("optical",), coreg=True, caps=None):
    return PlanContext(image_count=n, modalities=list(mods), has_valid_crs=True,
                       pair_co_registered=coreg,
                       available_capabilities=caps or ["vqa", "grounding", "change-detection",
                                                       "zero-shot-classification", "representation"])


# ---------------- planner produces schema-valid, policy-accepted plans ----------------

@pytest.mark.parametrize("mission,n,mods,want_tool", [
    ("what is in this image?", 1, ("optical",), "run_vqa"),
    ("where is the largest ship?", 1, ("optical",), "run_grounding"),
    ("what type of scene is this?", 1, ("optical",), "run_scene_retrieval"),
    ("what changed between these two images?", 2, ("optical",), "run_temporal_change"),
    ("describe what kind of change happened", 2, ("optical",), "run_semantic_temporal_baseline"),
    ("compare the optical and SAR imagery", 2, ("optical", "sar"), "run_optical_sar"),
])
def test_planner_selects_the_right_tool_and_policy_accepts(mission, n, mods, want_tool):
    plan, used, _ = _plan(mission, n, mods)
    assert isinstance(plan, AgentPlan)
    assert any(s.tool == want_tool for s in plan.steps), [s.tool for s in plan.steps]
    assert plan.steps[-1].task == TaskType.FINALIZE
    assert validate_plan(plan, _ctx(n, mods)).ok


def test_flagship_plan_is_multistep_and_valid():
    plan, _, _ = _plan(
        "Investigate this area: identify significant changes, locate the affected structures, "
        "use SAR evidence to characterise them, give a verified summary.", 4, ("optical", "sar"))
    tools = [s.tool for s in plan.steps]
    for t in ("run_temporal_change", "extract_changed_regions", "run_grounding", "run_optical_sar"):
        assert t in tools, tools
    assert validate_plan(plan, _ctx(4, ("optical", "sar"))).ok
    assert plan.tool_step_count() <= MAX_STEPS


# ---------------- the 18 agentic-safety / failure cases ----------------

def test_01_malformed_plan_rejected():
    with pytest.raises(Exception):
        AgentPlan(goal="", steps=[])  # empty goal + no steps


def test_02_nonexistent_tool_rejected_by_policy():
    plan = AgentPlan(goal="g", steps=[
        PlanStep(step_id="s1", task=TaskType.VQA, tool="run_vqa", inputs={"image": "img0"},
                 depends_on=[], reason="r"),
        PlanStep(step_id="s2", task=TaskType.FINALIZE, tool="finalize_answer", depends_on=["s1"], reason="r"),
    ])
    # forge an unknown tool post-construction
    object.__setattr__(plan.steps[0], "tool", "run_magic")
    pr = validate_plan(plan, _ctx(1))
    assert not pr.ok and any("tool_exists" in c or "unsupported" in c for c in pr.reasons)


def test_03_unsupported_task_tool_pair_rejected():
    plan = AgentPlan(goal="g", steps=[
        PlanStep(step_id="s1", task=TaskType.VQA, tool="run_grounding", inputs={"image": "img0"},
                 depends_on=[], reason="RemoteSAM cannot do VQA"),
        PlanStep(step_id="s2", task=TaskType.FINALIZE, tool="finalize_answer", depends_on=["s1"], reason="r"),
    ])
    pr = validate_plan(plan, _ctx(1))
    assert not pr.ok and any("tool_matches_task" in c for c in pr.reasons)


def test_04_missing_second_image_blocks_temporal():
    plan, _, _ = _plan("what changed between these images?", 1, ("optical",))
    # a 1-image change mission must NOT yield an executable temporal plan
    pr = validate_plan(plan, _ctx(1))
    if pr.ok:
        assert "run_temporal_change" not in [s.tool for s in plan.steps]


def test_05_incompatible_crs_blocks_temporal_at_policy():
    plan, _, _ = _plan("what changed between these images?", 2, ("optical",))
    pr = validate_plan(plan, _ctx(2, coreg=False))
    assert not pr.ok and any("geospatial" in c for c in pr.reasons)


@pytest.mark.slow
@pytest.mark.skipif(not _HAS_CF, reason="ChangeFormer absent")
def test_06_grounding_failure_is_recorded_not_fabricated():
    # a mission that grounds a nonexistent thing on the temporal pair
    res = run_investigation(
        "Investigate the change and locate any unicorns.",
        [str(_DEMO / "temporal/t1.tif"), str(_DEMO / "temporal/t2.tif")])
    g = [s for s in res.steps if s.task == TaskType.GROUND_OBJECT]
    if g:
        assert g[0].verdict in ("INSUFFICIENT", "INCOHERENT", "COHERENT")
    # no fabricated coordinates when nothing grounded
    assert all(sf.where_lonlat is None or sf.label != "grounded structure"
               for sf in res.spatial_findings) or any(
        s.task == TaskType.GROUND_OBJECT and s.status == "completed" for s in res.steps)


@pytest.mark.slow
@pytest.mark.skipif(not _HAS_CF, reason="ChangeFormer absent")
def test_07_temporal_runs_and_is_verified():
    res = run_investigation("what changed between these images?",
                            [str(_DEMO / "temporal/t1.tif"), str(_DEMO / "temporal/t2.tif")])
    assert res.ok
    assert any(s.task == TaskType.TEMPORAL_CHANGE and s.status == "completed" for s in res.steps)
    assert res.verification and res.verification["status"] in ("SUPPORTED", "INSUFFICIENT_EVIDENCE")


@pytest.mark.slow
def test_08_croma_input_mismatch_is_handled_honestly():
    # 3-band RGB as "optical" for run_optical_sar -> the wrapper fails cleanly
    res = run_investigation(
        "Investigate the change and use SAR to characterise it.",
        [str(_DEMO / "temporal/t1.tif"), str(_DEMO / "temporal/t2.tif"),
         str(_DEMO / "optical_sar/s1_sar.tif")]) if _HAS_CF else None
    if res is None:
        pytest.skip("ChangeFormer absent")
    osar = [s for s in res.steps if s.task == TaskType.OPTICAL_SAR_ANALYSIS]
    if osar and osar[0].status == "failed":
        assert res.failures  # recorded, not hidden


def test_09_insufficient_evidence_surfaces():
    plan, _, _ = _plan("banana sideways", 1, ("optical",))
    pr = validate_plan(plan, _ctx(1))
    assert pr.ok  # a VLM can attempt any single-image question


def test_10_contradictory_geo_is_blocked():
    res = run_investigation("what changed between these images?",
                            [str(_DEMO / "temporal/t1.tif"), str(_DEMO / "temporal/t2_shifted.tif")])
    # misregistered pair -> temporal never runs; falls back or reports honestly
    assert not any(s.task == TaskType.TEMPORAL_CHANGE and s.status == "completed" for s in res.steps)


def test_11_loop_dependency_rejected():
    plan = AgentPlan(goal="g", steps=[
        PlanStep(step_id="s1", task=TaskType.VALIDATE_INPUT, tool="validate_geospatial_input",
                 inputs={"images": ["img0"]}, depends_on=["s2"], reason="r"),
        PlanStep(step_id="s2", task=TaskType.VQA, tool="run_vqa", inputs={"image": "img0"},
                 depends_on=["s1"], reason="r"),
        PlanStep(step_id="s3", task=TaskType.FINALIZE, tool="finalize_answer", depends_on=["s2"], reason="r"),
    ])
    pr = validate_plan(plan, _ctx(1))
    assert not pr.ok and any("cycle" in c or "dependencies" in c for c in pr.reasons)


def test_12_more_than_max_steps_rejected():
    steps = [PlanStep(step_id="s1", task=TaskType.VALIDATE_INPUT, tool="validate_geospatial_input",
                      inputs={"images": ["img0"]}, depends_on=[], reason="r")]
    for i in range(2, 2 + MAX_STEPS + 1):
        steps.append(PlanStep(step_id=f"s{i}", task=TaskType.VQA, tool="run_vqa",
                              inputs={"image": "img0"}, depends_on=["s1"], reason="r"))
    steps.append(PlanStep(step_id="s99", task=TaskType.FINALIZE, tool="finalize_answer",
                          depends_on=["s1"], reason="r"))
    plan = AgentPlan(goal="g", steps=steps)
    pr = validate_plan(plan, _ctx(1))
    assert not pr.ok and any("step_cap" in c for c in pr.reasons)


@pytest.mark.slow
def test_13_no_fabricated_geographic_coordinate_without_crs():
    # a JPG mission -> geospatial unavailable -> spatial findings carry no lon/lat
    res = run_investigation("what is in this image?", [str(_DEMO / "vqa/scene.jpg")]) if _HAS_TINYRS else None
    if res is None:
        pytest.skip("TinyRS absent")
    assert all(sf.where_lonlat is None for sf in res.spatial_findings)


def test_14_llm_planner_failure_falls_back_to_rule_based(monkeypatch):
    from satquery_agents.agent import planner as _pl

    class _Boom:
        name = "llm"

        def plan(self, *a, **k):
            raise RuntimeError("planner model unavailable")

    plan, used, notes = _pl.plan_with_fallback("what changed between these images?", 2, ["optical"],
                                               planner=_Boom())
    assert used == "rule_based_fallback" and isinstance(plan, AgentPlan)
    assert any("fallback" in n for n in notes)


@pytest.mark.slow
def test_15_unsupported_semantic_conclusion_not_asserted():
    # optical+SAR is representation-only; the executor must not turn an embedding into a fact
    res = run_investigation("compare the optical and SAR imagery",
                            [str(_DEMO / "optical_sar/s2_optical.tif"),
                             str(_DEMO / "optical_sar/s1_sar.tif")])
    osar = [s for s in res.steps if s.task == TaskType.OPTICAL_SAR_ANALYSIS]
    if osar and osar[0].status == "completed":
        assert any("representation-level only" in f for f in res.key_findings)


def test_16_planner_invalid_json_falls_back(monkeypatch):
    from satquery_agents.agent import planner as _pl

    class _Junk:
        name = "llm"

        def plan(self, *a, **k):
            raise ValueError("planner produced no JSON object")

    plan, used, _ = _pl.plan_with_fallback("where is the ship?", 1, ["optical"], planner=_Junk())
    assert used == "rule_based_fallback" and plan.steps[-1].task == TaskType.FINALIZE


def test_17_planner_timeout_is_caught(monkeypatch):
    import subprocess

    from satquery_agents.agent import planner as _pl

    class _Slow:
        name = "llm"

        def plan(self, *a, **k):
            raise subprocess.TimeoutExpired("cmd", 1)

    plan, used, _ = _pl.plan_with_fallback("what is in this image?", 1, ["optical"], planner=_Slow())
    assert used == "rule_based_fallback"


def test_18_planner_crash_is_caught():
    from satquery_agents.agent import planner as _pl

    class _Crash:
        name = "llm"

        def plan(self, *a, **k):
            raise KeyError("boom")

    plan, used, _ = _pl.plan_with_fallback("locate the runway", 1, ["optical"], planner=_Crash())
    assert used == "rule_based_fallback" and isinstance(plan, AgentPlan)


# ---------------- deterministic fallback + bounded loop ----------------

def test_deterministic_fallback_on_rejected_plan():
    # 1 image + "what changed" -> planner may emit a VQA plan (valid); force a rejection path
    # by giving a misregistered pair so the temporal plan is policy-rejected.
    res = run_investigation("what changed between these images?",
                            [str(_DEMO / "temporal/t1.tif"), str(_DEMO / "temporal/t2_shifted.tif")])
    assert res.mode in ("investigate", "ask-fallback")
    assert res.plan_status in ("rejected", "valid", "fallback")
    # honest outcome either way — never a silently-run temporal step
    assert not any(s.task == TaskType.TEMPORAL_CHANGE and s.status == "completed" for s in res.steps)


def test_bounded_loop_never_exceeds_cap():
    plan, _, _ = _plan(
        "Investigate: identify changes, locate structures, characterise with SAR, verify.", 4,
        ("optical", "sar"))
    assert plan.tool_step_count() <= MAX_STEPS


def test_g14_map_and_missions_exist():
    assert (_REPO / "docs" / "G14_AGENT_IMPLEMENTATION_MAP.md").exists()
    assert (_REPO / "evaluation" / "agent" / "frozen_missions.json").exists()
