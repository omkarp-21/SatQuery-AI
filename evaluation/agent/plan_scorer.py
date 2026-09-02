"""Semantic plan scorer (G16 Part 6).

A planner must not be judged only against one expected token sequence — several
orderings can be equally valid. This scorer checks a plan against the mission's
*constraints*, not a gold plan:

* REQUIRED_TOOL_COVERAGE  — every tool in `expected_tool_set` appears
* forbidden actions        — no tool in `forbid_tools` appears in an executable plan
* dependency validity      — every depends_on points to a real, earlier step
* order constraints        — every "A < B" (task names) holds
* modality / image sanity  — SAR tool only if a SAR modality is present;
                             pair tools only with >= 2 images
* verification requirement  — a verify_result step exists
* valid termination        — last step is finalize_answer
* unnecessary tools        — executable specialist tools not in the expected set
                             and not a reasonable connective (extract/cross_check)

`semantic_valid` = required covered AND no forbidden AND deps ok AND order ok
AND modality ok AND verify present AND valid termination.

`exact_match` is reported too (plan tool sequence == expected_tool_set as a
sub-sequence) but is NOT what gates validity.
"""

from __future__ import annotations

from typing import Any

_PAIR_TOOLS = {"run_temporal_change", "run_semantic_temporal_baseline"}
_SAR_TOOLS = {"run_optical_sar"}
_CONNECTIVE = {"extract_changed_regions", "cross_check_evidence", "inspect_evidence",
               "verify_result", "finalize_answer", "validate_geospatial_input"}


def _order_ok(constraints: list[str], plan_tasks: list[str]) -> bool:
    idx: dict[str, int] = {}
    for i, t in enumerate(plan_tasks):
        idx.setdefault(t, i)
    for c in constraints:
        if "<" not in c:
            continue
        a, b = [x.strip() for x in c.split("<", 1)]
        if a in idx and b in idx and idx[a] >= idx[b]:
            return False
    return True


def score_plan(
    plan: Any,
    mission: dict,
    *,
    policy_ok: bool,
    image_count: int,
    modalities: list[str],
) -> dict:
    tools = [s.tool for s in plan.steps]
    tasks = [s.task.value if hasattr(s.task, "value") else str(s.task) for s in plan.steps]
    executable = tools if policy_ok else []
    exp = list(mission.get("expected_tool_set", []))
    forbid = set(mission.get("forbid_tools", []))
    unsupported = bool(mission.get("unsupported"))

    # --- required tool coverage ---
    covered = [t for t in exp if t in tools]
    required_coverage = (len(covered) / len(exp)) if exp else (0.0 if unsupported else 1.0)
    required_covered = not exp or all(t in tools for t in exp)
    if unsupported and not exp:
        # an unsupported mission's "correct" plan runs no specialist
        required_covered = True
        required_coverage = 1.0

    # --- forbidden ---
    forbidden_used = sorted(forbid & set(executable))

    # --- dependency validity ---
    pos = {s.step_id: i for i, s in enumerate(plan.steps)}
    deps_total = deps_valid = 0
    for s in plan.steps:
        for d in s.depends_on:
            deps_total += 1
            if d in pos and pos[d] < pos[s.step_id]:
                deps_valid += 1
    deps_ok = deps_total == deps_valid

    # --- order ---
    order_ok = _order_ok(mission.get("expected_order_constraints", []), tasks)

    # --- modality / image sanity ---
    has_sar = "sar" in [m.lower() for m in modalities]
    modality_ok = True
    if not has_sar and (_SAR_TOOLS & set(executable)):
        modality_ok = False
    if image_count < 2 and (_PAIR_TOOLS & set(executable)):
        modality_ok = False

    verify_present = "verify_result" in tools
    valid_termination = tools[-1] == "finalize_answer" if tools else False

    # --- unnecessary specialist tools ---
    # specialists the mission does not call for. For an UNSUPPORTED mission a
    # benign generic specialist (e.g. run_vqa for "predict the weather") is not
    # "unnecessary" unless it is forbidden - the mission has no right answer.
    exp_set = set(exp)
    unnecessary = sorted(
        t for t in executable
        if t.startswith("run_") and t not in exp_set and t not in _CONNECTIVE
        and (not unsupported or t in forbid)
    )

    semantic_valid = bool(
        required_covered and not forbidden_used and deps_ok and order_ok
        and modality_ok and verify_present and valid_termination
        and (not unsupported or not any(t.startswith("run_") for t in executable))
    )
    # exact match = expected list is an ordered sub-sequence of the plan's tools
    exact_match = _is_subsequence(exp, tools) if exp else (not unsupported)

    return {
        "semantic_valid": semantic_valid,
        "exact_match": bool(exact_match),
        "required_covered": bool(required_covered),
        "required_tool_coverage": round(required_coverage, 3),
        "forbidden_used": forbidden_used,
        "unsupported_action": bool(forbidden_used),
        "deps_ok": deps_ok, "deps_total": deps_total, "deps_valid": deps_valid,
        "order_ok": bool(order_ok),
        "modality_ok": bool(modality_ok),
        "verify_present": bool(verify_present),
        "valid_termination": bool(valid_termination),
        "unnecessary_tools": unnecessary,
        "n_specialist_steps": plan.tool_step_count(),
        "plan_tools": tools,
        "plan_tasks": tasks,
    }


def _is_subsequence(sub: list[str], seq: list[str]) -> bool:
    it = iter(seq)
    return all(x in it for x in sub)
