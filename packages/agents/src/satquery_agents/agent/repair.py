"""Schema-repair + attempt tracking for LLM-produced plans (G16).

An LLM planner is allowed to make mistakes; the *system* is not allowed to
execute a malformed plan. This module sits between the raw model output and
`AgentPlan.model_validate`:

    raw text -> parse (first JSON object) -> safe deterministic repair -> validate
             -> ok  : return the plan + a PlannerAttempt record
             -> fail: caller falls back to RuleBasedPlanner

"Safe" repairs only touch structure that cannot change the plan's intent:

* renumber / add missing ``step_id`` (s1, s2, ... in array order)
* coerce ``depends_on`` from str -> [str], drop refs to unknown/later steps
* map a near-miss tool name to the canonical one (``ground`` -> ``run_grounding``)
* uppercase a lowercase task name that matches the ontology
* drop unknown top-level / step keys
* prepend VALIDATE_INPUT when images exist and it is missing
* append VERIFY + FINALIZE when missing
* clamp an over-long plan is NOT attempted -- that is a real planning error -> fallback

Nothing here invents a specialist step, a modality, or a coordinate.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any

from pydantic import ValidationError

from .registry import tool_names
from .schemas import AgentPlan, TaskType

_TASKS = {t.value for t in TaskType}
_TOOLS = set(tool_names())

# canonical task for a tool (used to fix a mismatched/misspelled task label)
_TASK_OF_TOOL = {
    "validate_geospatial_input": "VALIDATE_INPUT",
    "run_vqa": "VQA",
    "run_grounding": "GROUND_OBJECT",
    "run_scene_retrieval": "SCENE_UNDERSTANDING",
    "run_temporal_change": "TEMPORAL_CHANGE",
    "run_semantic_temporal_baseline": "SEMANTIC_CHANGE",
    "run_optical_sar": "OPTICAL_SAR_ANALYSIS",
    "extract_changed_regions": "EXTRACT_CHANGED_REGIONS",
    "cross_check_evidence": "CROSS_CHECK_EVIDENCE",
    "verify_result": "VERIFY",
    "inspect_evidence": "SUMMARIZE",
    "finalize_answer": "FINALIZE",
}
_TOOL_OF_TASK = {v: k for k, v in _TASK_OF_TOOL.items()}

# common near-miss tool spellings an LLM emits
_TOOL_ALIASES = {
    "ground": "run_grounding", "grounding": "run_grounding", "run_ground": "run_grounding",
    "detect_change": "run_temporal_change", "change_detection": "run_temporal_change",
    "temporal_change": "run_temporal_change", "run_change": "run_temporal_change",
    "vqa": "run_vqa", "question_answering": "run_vqa",
    "scene": "run_scene_retrieval", "scene_retrieval": "run_scene_retrieval",
    "optical_sar": "run_optical_sar", "run_sar": "run_optical_sar", "sar_analysis": "run_optical_sar",
    "semantic_change": "run_semantic_temporal_baseline",
    "extract_regions": "extract_changed_regions", "changed_regions": "extract_changed_regions",
    "cross_check": "cross_check_evidence", "verify": "verify_result",
    "validate": "validate_geospatial_input", "validate_input": "validate_geospatial_input",
    "inspect": "inspect_evidence", "summarize": "inspect_evidence",
    "finalize": "finalize_answer", "finish": "finalize_answer",
}

_ALLOWED_STEP_KEYS = {"step_id", "task", "tool", "inputs", "depends_on", "reason",
                      "required_verification", "success_condition"}
_ALLOWED_PLAN_KEYS = {"goal", "inputs", "steps", "constraints", "expected_output", "planner"}


@dataclass
class PlannerAttempt:
    """Full provenance of one planning attempt - stored, not shown to users by default."""

    planner: str = "llm"
    raw_output: str = ""                 # the model's raw completion (audit only)
    parse_status: str = "not_attempted"  # ok | no_json | json_error
    schema_status: str = "not_attempted"  # ok | invalid
    repair_status: str = "none"          # none | applied | applied_insufficient
    repairs: list[str] = field(default_factory=list)
    schema_errors: list[str] = field(default_factory=list)
    final_source: str = "none"           # llm | llm_repaired | rule_based_fallback
    fallback_reason: str | None = None
    gen_s: float | None = None

    def public(self) -> dict[str, Any]:
        """A user-safe view - never includes the raw model text."""
        return {
            "planner": self.planner,
            "parse_status": self.parse_status,
            "schema_status": self.schema_status,
            "repair_status": self.repair_status,
            "repairs": list(self.repairs),
            "final_source": self.final_source,
            "fallback_reason": self.fallback_reason,
            "gen_s": self.gen_s,
        }


def first_json_object(text: str) -> tuple[dict | None, str]:
    """Return (obj, status) where status in {ok, no_json, json_error}."""
    if not text or not text.strip():
        return None, "no_json"
    stripped = re.sub(r"```(?:json)?", "", text)
    depth = 0
    start = -1
    saw_brace = False
    for i, ch in enumerate(stripped):
        if ch == "{":
            if depth == 0:
                start = i
            depth += 1
            saw_brace = True
        elif ch == "}":
            depth -= 1
            if depth == 0 and start >= 0:
                try:
                    return json.loads(stripped[start:i + 1]), "ok"
                except json.JSONDecodeError:
                    start = -1
    return None, ("json_error" if saw_brace else "no_json")


def salvage_truncated(text: str) -> tuple[dict | None, list[str]]:
    """A 2B model often runs past the token budget mid-JSON. If we can still read
    ``"goal"`` and one or more COMPLETE step objects, rebuild a minimal dict from
    them (VERIFY + FINALIZE get appended by :func:`repair_plan_dict`). Returns
    (obj|None, notes)."""
    notes: list[str] = []
    if not text:
        return None, notes
    t = re.sub(r"```(?:json)?", "", text)
    gm = re.search(r'"goal"\s*:\s*"([^"]{0,300})"', t)
    goal = gm.group(1) if gm else "geospatial mission"
    im = re.search(r'"inputs"\s*:\s*(\[[^\]]{0,200}\])', t)
    try:
        inputs = json.loads(im.group(1)) if im else []
    except json.JSONDecodeError:
        inputs = []
    # collect EVERY complete balanced {...} span (at any nesting depth), then keep
    # the ones that parse as a step object (have "tool", not the outer "goal").
    spans: list[tuple[int, int]] = []
    stack: list[int] = []
    for i, ch in enumerate(t):
        if ch == "{":
            stack.append(i)
        elif ch == "}" and stack:
            spans.append((stack.pop(), i))
    seen: set[str] = set()
    steps: list[dict] = []
    for s, e in sorted(spans):
        frag = t[s:e + 1]
        if '"tool"' not in frag or '"goal"' in frag:
            continue
        try:
            d = json.loads(frag)
        except json.JSONDecodeError:
            continue
        if not isinstance(d, dict) or "tool" not in d:
            continue
        d.pop("steps", None)  # drop any mis-nested steps key
        key = f"{d.get('tool')}|{json.dumps(d.get('inputs'), sort_keys=True)}"
        if key in seen:
            continue
        seen.add(key)
        steps.append(d)
    if not steps:
        return None, notes
    notes.append(f"salvaged {len(steps)} complete step object(s) from truncated JSON")
    return {"goal": goal, "inputs": inputs, "steps": steps, "planner": "llm"}, notes


def _canon_tool(name: Any) -> str | None:
    if not isinstance(name, str):
        return None
    n = name.strip()
    if n in _TOOLS:
        return n
    low = n.lower().replace("-", "_").replace(" ", "_")
    if low in _TOOLS:
        return low
    return _TOOL_ALIASES.get(low)


def repair_plan_dict(obj: dict, *, image_count: int) -> tuple[dict, list[str]]:
    """Apply only intent-preserving structural fixes. Returns (obj, repairs)."""
    repairs: list[str] = []
    obj = {k: v for k, v in obj.items() if k in _ALLOWED_PLAN_KEYS} or dict(obj)
    if set(obj) - _ALLOWED_PLAN_KEYS:
        repairs.append("dropped unknown top-level keys")

    obj.setdefault("goal", "geospatial mission")
    if not isinstance(obj.get("goal"), str) or not obj["goal"].strip():
        obj["goal"] = "geospatial mission"
        repairs.append("filled empty goal")

    steps = obj.get("steps")
    if not isinstance(steps, list) or not steps:
        return obj, repairs  # nothing to work with -> validation will fail -> fallback

    fixed: list[dict] = []
    for idx, st in enumerate(steps, start=1):
        if not isinstance(st, dict):
            repairs.append(f"dropped non-object step #{idx}")
            continue
        s = {k: v for k, v in st.items() if k in _ALLOWED_STEP_KEYS}
        if set(st) - _ALLOWED_STEP_KEYS:
            repairs.append(f"s{idx}: dropped unknown step keys")

        # tool
        tool = _canon_tool(s.get("tool"))
        if tool is None:
            repairs.append(f"s{idx}: unresolvable tool {s.get('tool')!r} -> step dropped")
            continue
        if tool != s.get("tool"):
            repairs.append(f"s{idx}: tool {s.get('tool')!r} -> {tool!r}")
        s["tool"] = tool

        # task: trust the tool's canonical task if missing / not in ontology / mismatched
        task = s.get("task")
        want = _TASK_OF_TOOL[tool]
        if not isinstance(task, str) or task.upper() not in _TASKS:
            s["task"] = want
            repairs.append(f"s{idx}: task set to {want} (from tool)")
        elif task.upper() != task:
            s["task"] = task.upper()
            repairs.append(f"s{idx}: task upper-cased")
        elif task != want:
            s["task"] = want
            repairs.append(f"s{idx}: task {task} -> {want} (matches tool)")

        # step_id
        s["step_id"] = f"s{idx}"
        if st.get("step_id") not in (None, f"s{idx}"):
            repairs.append(f"step_id {st.get('step_id')!r} -> s{idx}")

        # depends_on
        dep = s.get("depends_on", [])
        if isinstance(dep, str):
            dep = [dep]
            repairs.append(f"s{idx}: depends_on str -> list")
        if not isinstance(dep, list):
            dep = []
        clean = [d for d in dep if isinstance(d, str) and re.fullmatch(r"s[0-9]{1,2}", d)
                 and int(d[1:]) < idx]
        if clean != dep:
            repairs.append(f"s{idx}: pruned depends_on {dep} -> {clean}")
        if not clean and idx > 1:
            clean = [f"s{idx - 1}"]
            repairs.append(f"s{idx}: empty depends_on -> [s{idx - 1}]")
        s["depends_on"] = clean

        s.setdefault("reason", f"{s['task'].lower()} step")
        if not isinstance(s.get("reason"), str) or not s["reason"].strip():
            s["reason"] = f"{s['task'].lower()} step"
        s.setdefault("inputs", {})
        if not isinstance(s["inputs"], dict):
            s["inputs"] = {}
        fixed.append(s)

    # structural guarantees
    if fixed and image_count >= 1 and fixed[0]["tool"] != "validate_geospatial_input":
        fixed.insert(0, {
            "step_id": "s1", "task": "VALIDATE_INPUT", "tool": "validate_geospatial_input",
            "inputs": {"images": [f"img{i}" for i in range(max(image_count, 1))]},
            "depends_on": [], "reason": "validate imagery before use",
            "success_condition": "validation ok",
        })
        repairs.append("prepended VALIDATE_INPUT")

    tools_present = {s["tool"] for s in fixed}
    if fixed and "verify_result" not in tools_present:
        fixed.append({"step_id": f"s{len(fixed) + 1}", "task": "VERIFY", "tool": "verify_result",
                      "inputs": {}, "depends_on": [fixed[-1]["step_id"]],
                      "reason": "aggregate verification", "success_condition": "verification computed"})
        repairs.append("appended VERIFY")
    if fixed and fixed[-1]["tool"] != "finalize_answer":
        fixed.append({"step_id": f"s{len(fixed) + 1}", "task": "FINALIZE", "tool": "finalize_answer",
                      "inputs": {}, "depends_on": [fixed[-1]["step_id"]],
                      "reason": "produce the evidence-first report", "success_condition": "report assembled"})
        repairs.append("appended FINALIZE")

    # renumber after inserts/appends so ids stay contiguous and deps still resolve
    remap = {s["step_id"]: f"s{i}" for i, s in enumerate(fixed, start=1)}
    for i, s in enumerate(fixed, start=1):
        s["step_id"] = f"s{i}"
        s["depends_on"] = [remap.get(d, d) for d in s["depends_on"]
                           if remap.get(d, d) != f"s{i}"]
    obj["steps"] = fixed
    obj.setdefault("planner", "llm")
    return obj, repairs


def build_plan_from_raw(raw: str, *, image_count: int, gen_s: float | None = None) -> tuple[AgentPlan | None, PlannerAttempt]:
    """Parse -> repair -> validate. Returns (plan|None, attempt). None => caller must fall back."""
    att = PlannerAttempt(raw_output=raw or "", gen_s=gen_s)
    obj, att.parse_status = first_json_object(raw)
    salvaged = False
    if obj is None and att.parse_status == "json_error":
        obj, salv_notes = salvage_truncated(raw or "")
        if obj is not None:
            att.repairs.extend(salv_notes)
            att.parse_status = "salvaged"
            salvaged = True
    if obj is None:
        att.schema_status = "invalid"
        att.fallback_reason = f"parse_{att.parse_status}"
        return None, att

    # attempt 1: validate as-is (skip for a salvaged dict -- it always needs repair
    # to re-append the VERIFY/FINALIZE that were truncated away)
    obj.setdefault("planner", "llm")
    if not salvaged:
        try:
            plan = AgentPlan.model_validate(obj)
            att.parse_status = "ok"
            att.schema_status = "ok"
            att.final_source = "llm"
            return plan, att
        except ValidationError as e1:
            att.schema_status = "invalid"
            att.schema_errors = [f"{'.'.join(str(x) for x in err['loc'])}: {err['msg']}"
                                 for err in e1.errors()][:12]
    else:
        att.schema_status = "invalid"

    # attempt 2: safe repair, then validate
    repaired, repairs = repair_plan_dict(dict(obj), image_count=image_count)
    att.repairs = att.repairs + repairs
    try:
        plan = AgentPlan.model_validate(repaired)
        if salvaged and plan.tool_step_count() == 0:
            # a truncation skeleton (validate/verify/finalize only) is not a plan
            att.repair_status = "applied_insufficient"
            att.fallback_reason = "salvage_skeleton_no_specialist"
            return None, att
        att.repair_status = "applied"
        att.final_source = "llm_repaired"
        return plan, att
    except ValidationError as e2:
        att.repair_status = "applied_insufficient"
        att.schema_errors = (att.schema_errors + ["-- after repair --"]
                             + [f"{'.'.join(str(x) for x in err['loc'])}: {err['msg']}"
                                for err in e2.errors()])[:20]
        att.fallback_reason = "schema_invalid_after_repair"
        return None, att
