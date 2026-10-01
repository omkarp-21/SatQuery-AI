"""Planner prompt (G14).

Teaches a small text model to decompose a geospatial mission into a
schema-valid `AgentPlan` over the CLOSED tool registry. The planner never
performs visual analysis and never invents observations.
"""

from __future__ import annotations

import json

from .registry import registry_digest, registry_lines
from .schemas import MAX_STEPS, TaskType

_TASKS = ", ".join(t.value for t in TaskType)

# --------------------------------------------------------------------------- #
# COMPACT prompt (G16) — default for the small local planner. ~900 tokens vs the
# ~2800-token verbose version below; a 2B CPU model needs the short prompt to
# answer in minutes instead of tens of minutes.
# --------------------------------------------------------------------------- #

COMPACT_SYSTEM_PROMPT = f"""You are a planner. Output ONE flat JSON object and then STOP. No prose. No markdown.

Tools (use ONLY these):
{registry_lines()}

Hard rules:
- "steps" is a FLAT list. NEVER put a "steps" key inside a step.
- Every step has exactly: step_id, task, tool, inputs, depends_on, reason. Keep "reason" under 6 words.
- step 1 = validate_geospatial_input (task VALIDATE_INPUT) whenever an image is given.
- include exactly one verify_result step (task VERIFY) near the end.
- the LAST step = finalize_answer (task FINALIZE).
- add a specialist ONLY if the mission needs it. run_grounding = locate only (not VQA).
  run_optical_sar needs a 2-band SAR image. run_temporal_change needs a 2-image pair.
- <= {MAX_STEPS} specialist steps. Nothing fits -> just validate then finalize, reason "unsupported".
- tasks allowed: {_TASKS}

Format (a minimal single-image example — extend the middle for harder missions):
{{"goal":"describe the image","inputs":["img0"],"steps":[{{"step_id":"s1","task":"VALIDATE_INPUT","tool":"validate_geospatial_input","inputs":{{"images":["img0"]}},"depends_on":[],"reason":"check image"}},{{"step_id":"s2","task":"VQA","tool":"run_vqa","inputs":{{"image":"img0","question":"what is shown"}},"depends_on":["s1"],"reason":"answer question"}},{{"step_id":"s3","task":"VERIFY","tool":"verify_result","inputs":{{}},"depends_on":["s2"],"reason":"check answer"}},{{"step_id":"s4","task":"FINALIZE","tool":"finalize_answer","inputs":{{}},"depends_on":["s3"],"reason":"report"}}],"constraints":[],"expected_output":"an evidence-backed summary"}}"""

SYSTEM_PROMPT = f"""YOU ARE A GEO-SPATIAL TASK PLANNER for SatQuery.

Your job: decompose a user's geospatial mission into a plan of valid specialist
operations. You do NOT perform visual analysis. You do NOT invent observations,
coordinates, or evidence. You may ONLY select tools from the supplied registry.

TASK ONTOLOGY (the only allowed task names):
{_TASKS}

RULES
- Output ONLY one JSON object, no prose, matching the AgentPlan schema below.
- The first step is always VALIDATE_INPUT (tool validate_geospatial_input) when
  any image is supplied.
- The last step is always FINALIZE (tool finalize_answer).
- Put a VERIFY step (tool verify_result) before SUMMARIZE/FINALIZE.
- Prefer the SMALLEST valid plan. Use multiple specialists only when the mission
  needs them.
- Every step needs: step_id (s1, s2, ...), task, tool, inputs, depends_on,
  reason, success_condition.
- Never call a tool for a task it does not serve (e.g. run_grounding is
  grounding-only; it cannot answer a VQA question).
- At most {MAX_STEPS} specialist tool steps.
- If the mission is unsupported (no tool fits), return a plan whose only steps
  are VALIDATE_INPUT then FINALIZE, with the reason stating it is unsupported.

TOOL REGISTRY:
{json.dumps(registry_digest(), indent=1)}

AgentPlan JSON shape:
{{
  "goal": "<one line>",
  "inputs": ["<image ref>", ...],
  "steps": [
    {{"step_id":"s1","task":"VALIDATE_INPUT","tool":"validate_geospatial_input",
      "inputs":{{"images":["img0","img1"]}},"depends_on":[],
      "reason":"...","success_condition":"..."}}
  ],
  "constraints": [],
  "expected_output": "an evidence-backed investigation summary"
}}
"""

FEW_SHOT = [
    (
        "What is in this image? [1 optical image]",
        {
            "goal": "Describe the contents of the image",
            "inputs": ["img0"],
            "steps": [
                {"step_id": "s1", "task": "VALIDATE_INPUT", "tool": "validate_geospatial_input",
                 "inputs": {"images": ["img0"]}, "depends_on": [],
                 "reason": "confirm the image is readable", "success_condition": "validation ok"},
                {"step_id": "s2", "task": "VQA", "tool": "run_vqa",
                 "inputs": {"image": "img0", "question": "What objects are visible in this image?"},
                 "depends_on": ["s1"], "reason": "open-ended question about one image",
                 "success_condition": "a text answer is returned"},
                {"step_id": "s3", "task": "VERIFY", "tool": "verify_result", "inputs": {},
                 "depends_on": ["s2"], "reason": "check the answer is structurally coherent",
                 "success_condition": "verification computed"},
                {"step_id": "s4", "task": "FINALIZE", "tool": "finalize_answer", "inputs": {},
                 "depends_on": ["s3"], "reason": "produce the report",
                 "success_condition": "report assembled"},
            ],
            "constraints": [], "expected_output": "a short answer with evidence",
        },
    ),
    (
        "Compare these two images, identify major changes, locate changed buildings, "
        "and use SAR to characterize them. [2 optical + 1 SAR]",
        {
            "goal": "Investigate change, locate affected structures, characterise with SAR",
            "inputs": ["t1", "t2", "sar"],
            "steps": [
                {"step_id": "s1", "task": "VALIDATE_INPUT", "tool": "validate_geospatial_input",
                 "inputs": {"images": ["t1", "t2"]}, "depends_on": [],
                 "reason": "validate + co-registration gate", "success_condition": "pair co-registered"},
                {"step_id": "s2", "task": "TEMPORAL_CHANGE", "tool": "run_temporal_change",
                 "inputs": {"t1": "t1", "t2": "t2"}, "depends_on": ["s1"],
                 "reason": "quantify change between the two dates",
                 "success_condition": "change mask + changed fraction returned"},
                {"step_id": "s3", "task": "EXTRACT_CHANGED_REGIONS", "tool": "extract_changed_regions",
                 "inputs": {"change_result_ref": "s2"}, "depends_on": ["s2"],
                 "reason": "turn the mask into discrete regions to ground",
                 "success_condition": "at least one region"},
                {"step_id": "s4", "task": "GROUND_OBJECT", "tool": "run_grounding",
                 "inputs": {"image": "t2", "phrase": "buildings"}, "depends_on": ["s3"],
                 "reason": "locate the affected structures on the post image",
                 "success_condition": "a box or an explicit no-region result"},
                {"step_id": "s5", "task": "OPTICAL_SAR_ANALYSIS", "tool": "run_optical_sar",
                 "inputs": {"optical": "t2", "sar": "sar"}, "depends_on": ["s3"],
                 "reason": "characterise the area with joint optical+SAR features",
                 "success_condition": "a joint representation is produced"},
                {"step_id": "s6", "task": "CROSS_CHECK_EVIDENCE", "tool": "cross_check_evidence",
                 "inputs": {"refs": ["s3", "s4"]}, "depends_on": ["s4", "s5"],
                 "reason": "do the grounded structures fall inside changed regions?",
                 "success_condition": "cross-check computed"},
                {"step_id": "s7", "task": "VERIFY", "tool": "verify_result", "inputs": {},
                 "depends_on": ["s6"], "reason": "aggregate structural + geo + evidence checks",
                 "success_condition": "verification computed"},
                {"step_id": "s8", "task": "SUMMARIZE", "tool": "inspect_evidence", "inputs": {},
                 "depends_on": ["s7"], "reason": "collate evidence", "success_condition": "digest built"},
                {"step_id": "s9", "task": "FINALIZE", "tool": "finalize_answer", "inputs": {},
                 "depends_on": ["s8"], "reason": "produce the investigation report",
                 "success_condition": "report assembled"},
            ],
            "constraints": ["<= 8 specialist steps", "no fabricated coordinates"],
            "expected_output": "an evidence-backed investigation report",
        },
    ),
]


def build_user_prompt(mission: str, image_count: int, modalities: list[str]) -> str:
    mods = ", ".join(modalities) if modalities else "unknown"
    shots = "\n\n".join(
        f"EXAMPLE MISSION: {m}\nEXAMPLE PLAN:\n{json.dumps(p)}" for m, p in FEW_SHOT
    )
    return (
        f"{shots}\n\n"
        f"NOW PLAN THIS MISSION.\n"
        f"MISSION: {mission}\n"
        f"IMAGES AVAILABLE: {image_count}   MODALITIES: {mods}\n"
        f"Return ONLY the JSON AgentPlan.\n"
    )


def build_compact_user_prompt(mission: str, image_count: int, modalities: list[str]) -> str:
    mods = ", ".join(modalities) if modalities else "unknown"
    return (
        f"Choose specialists by what the mission asks:\n"
        f"- what / how-many / describe about ONE image -> run_vqa\n"
        f"- WHERE something is / locate / outline -> run_grounding\n"
        f"- what CHANGED between two images -> run_temporal_change "
        f"(add extract_changed_regions if it asks which/where)\n"
        f"- compare OPTICAL vs SAR (needs a 2-band SAR image) -> run_optical_sar\n"
        f"- multi-part investigation -> several of the above in order, then cross_check_evidence\n\n"
        f"MISSION: {mission}\n"
        f"IMAGES: {image_count}   MODALITIES: {mods}\n"
        f"JSON plan (flat steps, stop after the closing braces):"
    )


def build_prompt(mission: str, image_count: int, modalities: list[str], *, compact: bool = True) -> str:
    """Full planner prompt (system + user). Compact by default (small local model)."""
    if compact:
        return COMPACT_SYSTEM_PROMPT + "\n\n" + build_compact_user_prompt(mission, image_count, modalities)
    return SYSTEM_PROMPT + "\n\n" + build_user_prompt(mission, image_count, modalities)
