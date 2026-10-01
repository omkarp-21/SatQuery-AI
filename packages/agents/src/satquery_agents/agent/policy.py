"""Deterministic plan validation / policy layer (G14).

Runs BEFORE any LLM-generated plan executes. Twelve checks; a plan that fails any
of them is rejected and never run. This is the execution guard — it makes an
impossible plan (e.g. "RemoteSAM for VQA") impossible at execution time, no
matter what the planner produced.
"""

from __future__ import annotations

from pydantic import BaseModel

from .registry import TOOL_REGISTRY
from .schemas import MAX_STEPS, AgentPlan, TaskType


class PolicyResult(BaseModel):
    ok: bool
    reasons: list[str] = []
    checks: dict[str, bool] = {}


class PlanContext(BaseModel):
    """What the executor knows about the mission before planning."""

    image_count: int
    modalities: list[str] = []          # e.g. ["optical"] or ["optical", "sar"]
    has_valid_crs: bool = False
    pair_co_registered: bool | None = None
    available_capabilities: list[str] = []  # from the model registry (informational)


# tool -> the capability the model registry must expose for it to be runnable
_TOOL_CAPABILITY = {
    "run_vqa": "vqa",
    "run_grounding": "grounding",
    "run_scene_retrieval": "zero-shot-classification",
    "run_temporal_change": "change-detection",
    "run_semantic_temporal_baseline": "change-detection",
    "run_optical_sar": "representation",
}


def validate_plan(plan: AgentPlan, ctx: PlanContext) -> PolicyResult:
    reasons: list[str] = []
    checks: dict[str, bool] = {}

    def _check(name: str, ok: bool, why: str) -> None:
        checks[name] = ok
        if not ok:
            reasons.append(f"{name}: {why}")

    step_ids = {s.step_id for s in plan.steps}

    # 1. every tool exists in the registry
    unknown_tools = [s.tool for s in plan.steps if s.tool not in TOOL_REGISTRY]
    _check("1_tool_exists", not unknown_tools, f"unknown tool(s) {unknown_tools}")

    # 2. every task is in the ontology (Enum parse already guarantees it; double-check)
    bad_tasks = [s.task for s in plan.steps if not isinstance(s.task, TaskType)]
    _check("2_task_exists", not bad_tasks, f"unknown task(s) {bad_tasks}")

    # 3. tool is the one declared for that task
    mismatched = [
        (s.step_id, s.tool, s.task.value)
        for s in plan.steps
        if s.tool in TOOL_REGISTRY and TOOL_REGISTRY[s.tool].task_type != s.task
    ]
    _check("3_tool_matches_task", not mismatched,
           f"tool/task mismatch {mismatched} (e.g. RemoteSAM is grounding-only, not VQA)")

    # 4. required image count is available — per step, against the image refs the
    #    step declares (a grounding step consumes 1 image even in a 2-image mission)
    img_problems = []
    _IMG_KEYS = ("image", "t1", "t2", "optical", "sar")
    for s in plan.steps:
        if s.tool not in TOOL_REGISTRY:
            continue
        lo, hi = TOOL_REGISTRY[s.tool].image_count
        if hi == 0:
            continue
        refs = list(s.inputs.get("images") or []) if isinstance(s.inputs.get("images"), list) else []
        refs += [s.inputs[k] for k in _IMG_KEYS if isinstance(s.inputs.get(k), str)]
        n_refs = len(refs) if refs else ctx.image_count  # fall back to mission count if step is vague
        if not (lo <= n_refs <= hi):
            img_problems.append(f"{s.step_id}:{s.tool} needs {lo}-{hi} images, step declares {n_refs}")
        if n_refs > ctx.image_count:
            img_problems.append(f"{s.step_id}:{s.tool} references {n_refs} images, mission has {ctx.image_count}")
    _check("4_image_count", not img_problems, "; ".join(img_problems))

    # 5. modality requirements are met
    mod_problems = []
    have = {m.lower() for m in ctx.modalities}
    for s in plan.steps:
        if s.tool not in TOOL_REGISTRY:
            continue
        need = set(TOOL_REGISTRY[s.tool].modality_requirements)
        if need and not need <= (have or {"optical"}):
            mod_problems.append(f"{s.step_id}:{s.tool} needs {sorted(need)}, mission has {sorted(have)}")
    _check("5_modalities", not mod_problems, "; ".join(mod_problems))

    # 6. dependencies reference real, earlier steps
    order = {s.step_id: i for i, s in enumerate(plan.steps)}
    dep_problems = []
    for s in plan.steps:
        for d in s.depends_on:
            if d not in step_ids:
                dep_problems.append(f"{s.step_id} depends on missing {d}")
            elif order.get(d, 1e9) >= order[s.step_id]:
                dep_problems.append(f"{s.step_id} depends on later/self step {d}")
    _check("6_dependencies", not dep_problems, "; ".join(dep_problems))

    # 7. geospatial requirements
    geo_problems = []
    for s in plan.steps:
        if s.tool not in TOOL_REGISTRY:
            continue
        req = TOOL_REGISTRY[s.tool].geospatial_requirements
        if req == "co_registered_pair" and ctx.pair_co_registered is False:
            geo_problems.append(f"{s.step_id}:{s.tool} needs a co-registered pair; it is not")
    _check("7_geospatial", not geo_problems, "; ".join(geo_problems))

    # 8. model capability matches (informational registry check)
    cap_problems = []
    caps = set(ctx.available_capabilities)
    if caps:
        for s in plan.steps:
            need = _TOOL_CAPABILITY.get(s.tool)
            if need and need not in caps:
                cap_problems.append(f"{s.step_id}:{s.tool} needs capability {need!r}, registry lacks it")
    _check("8_capability", not cap_problems, "; ".join(cap_problems))

    # 9. no unsupported tool call (same as 1, kept as a named check for the DoD table)
    _check("9_no_unsupported_call", not unknown_tools, f"unsupported tool(s) {unknown_tools}")

    # 10. no circular dependency (topological sort must succeed)
    _check("10_no_cycle", _acyclic(plan), "dependency cycle detected")

    # 11. step count within the bound
    tsc = plan.tool_step_count()
    _check("11_step_cap", tsc <= MAX_STEPS, f"{tsc} specialist steps > cap {MAX_STEPS}")

    # 12. output-schema compatibility with declared follow-ups
    schema_problems = []
    for s in plan.steps:
        if s.tool not in TOOL_REGISTRY:
            continue
        allowed_next = set(TOOL_REGISTRY[s.tool].allowed_followup_tasks)
        for other in plan.steps:
            if s.step_id in other.depends_on and allowed_next and other.task not in allowed_next:
                schema_problems.append(
                    f"{other.step_id} ({other.task.value}) is not an allowed follow-up of "
                    f"{s.step_id} ({s.tool}); allowed: {[t.value for t in allowed_next]}"
                )
    _check("12_followup_allowed", not schema_problems, "; ".join(schema_problems))

    # a plan must end at FINALIZE
    _check("13_ends_finalize", plan.steps[-1].task == TaskType.FINALIZE,
           "plan does not end with a FINALIZE step")

    return PolicyResult(ok=not reasons, reasons=reasons, checks=checks)


def _acyclic(plan: AgentPlan) -> bool:
    graph = {s.step_id: set(s.depends_on) for s in plan.steps}
    state: dict[str, int] = {}  # 0=unseen 1=in-progress 2=done

    def dfs(node: str) -> bool:
        if state.get(node) == 1:
            return False
        if state.get(node) == 2:
            return True
        state[node] = 1
        for nxt in graph.get(node, ()):
            if nxt in graph and not dfs(nxt):
                return False
        state[node] = 2
        return True

    return all(dfs(n) for n in graph)
