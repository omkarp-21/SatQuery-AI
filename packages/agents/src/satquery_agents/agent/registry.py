"""Typed tool registry — the ONLY tools the planner may select (G14).

The planner sees these as schemas (name + metadata), never as importable Python.
The executor binds each `ToolName` to a concrete wrapper in
`apps/backend/app/services/agent_runner.py`; the registry itself imports no model
code.

Every entry declares its task type, input contract, output schema name, the
frozen-stack specialist behind it, its geospatial + modality requirements, which
follow-up tasks are allowed after it, and its known failure modes — so the policy
layer can reject an impossible plan before anything runs.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from .schemas import TaskType, ToolName


class ToolSpec(BaseModel):
    tool_name: ToolName
    task_type: TaskType
    summary: str
    required_inputs: list[str]
    optional_inputs: list[str] = Field(default_factory=list)
    output_schema: str  # name of the result shape the executor returns
    specialist: str  # frozen-stack model / component, or "none (deterministic)"
    image_count: tuple[int, int]  # (min, max) images this tool consumes
    modality_requirements: list[str] = Field(default_factory=list)  # e.g. ["optical"], ["optical","sar"]
    geospatial_requirements: str = "none"  # "none" | "valid_crs_optional" | "co_registered_pair"
    allowed_followup_tasks: list[TaskType] = Field(default_factory=list)
    failure_modes: list[str] = Field(default_factory=list)
    caveats: list[str] = Field(default_factory=list)


_FINALIZE_OR_VERIFY = [TaskType.VERIFY, TaskType.CROSS_CHECK_EVIDENCE, TaskType.SUMMARIZE, TaskType.FINALIZE]

TOOL_REGISTRY: dict[ToolName, ToolSpec] = {
    "validate_geospatial_input": ToolSpec(
        tool_name="validate_geospatial_input",
        task_type=TaskType.VALIDATE_INPUT,
        summary="Validate imagery: format, dimensions, bands, NoData, CRS/transform, and "
        "(for a pair) co-registration. Nothing else may run before this on a GeoTIFF path.",
        required_inputs=["images"],
        output_schema="GeoValidationResult",
        specialist="none (packages/geospatial)",
        image_count=(1, 4),
        geospatial_requirements="none",
        allowed_followup_tasks=[
            TaskType.SCENE_UNDERSTANDING, TaskType.VQA, TaskType.GROUND_OBJECT,
            TaskType.TEMPORAL_CHANGE, TaskType.SEMANTIC_CHANGE, TaskType.OPTICAL_SAR_ANALYSIS,
        ],
        failure_modes=["unreadable raster", "bad dimensions", "pair not co-registered"],
    ),
    "run_vqa": ToolSpec(
        tool_name="run_vqa",
        task_type=TaskType.VQA,
        summary="Answer an open-ended question about ONE image (TinyRS-2B; Qwen2-VL-2B fallback).",
        required_inputs=["image", "question"],
        output_schema="VqaResult",
        specialist="TinyRS-2B (Qwen2-VL-2B fallback)",
        image_count=(1, 1),
        modality_requirements=["optical"],
        geospatial_requirements="none",
        allowed_followup_tasks=_FINALIZE_OR_VERIFY,
        failure_modes=["weights absent", "empty question", "adapter subprocess crash"],
        caveats=["greedy-decoded answer; NO confidence value is produced"],
    ),
    "run_grounding": ToolSpec(
        tool_name="run_grounding",
        task_type=TaskType.GROUND_OBJECT,
        summary="Given ONE image + a referring phrase, return a bounding box + mask, or an "
        "explicit no-region result. NEVER hallucinates a box.",
        required_inputs=["image", "phrase"],
        optional_inputs=["region_ref"],
        output_schema="GroundingResult",
        specialist="RemoteSAM",
        image_count=(1, 1),
        modality_requirements=["optical"],
        geospatial_requirements="valid_crs_optional",
        allowed_followup_tasks=[TaskType.OPTICAL_SAR_ANALYSIS, TaskType.CROSS_CHECK_EVIDENCE,
                                *(_FINALIZE_OR_VERIFY)],
        failure_modes=["checkpoint absent", "no region grounded (explicit, not a failure)",
                       "box out of bounds"],
        caveats=["RemoteSAM upstream licence is NOT STATED — grounding output is prototype-only",
                 "score is a raw foreground softmax probability, NOT a calibrated confidence"],
    ),
    "run_scene_retrieval": ToolSpec(
        tool_name="run_scene_retrieval",
        task_type=TaskType.SCENE_UNDERSTANDING,
        summary="Zero-shot scene tagging / retrieval over candidate labels for ONE image (RemoteCLIP). "
        "NOT a VQA model.",
        required_inputs=["image"],
        optional_inputs=["prompts"],
        output_schema="SceneResult",
        specialist="RemoteCLIP",
        image_count=(1, 1),
        modality_requirements=["optical"],
        geospatial_requirements="none",
        allowed_followup_tasks=_FINALIZE_OR_VERIFY,
        failure_modes=["checkpoint absent"],
        caveats=["score is a softmax over the supplied prompts, NOT a calibrated confidence"],
    ),
    "run_temporal_change": ToolSpec(
        tool_name="run_temporal_change",
        task_type=TaskType.TEMPORAL_CHANGE,
        summary="Bi-temporal binary change mask + changed fraction / area / bbox / centroid "
        "for a co-registered T1/T2 pair (ChangeFormer; image-difference fallback).",
        required_inputs=["t1", "t2"],
        output_schema="ChangeSliceResult",
        specialist="ChangeFormer",
        image_count=(2, 2),
        modality_requirements=["optical"],
        geospatial_requirements="co_registered_pair",
        allowed_followup_tasks=[TaskType.EXTRACT_CHANGED_REGIONS, TaskType.GROUND_OBJECT,
                                TaskType.SEMANTIC_CHANGE, TaskType.OPTICAL_SAR_ANALYSIS,
                                *_FINALIZE_OR_VERIFY],
        failure_modes=["checkpoint absent", "pair not co-registered (blocked earlier)"],
    ),
    "run_semantic_temporal_baseline": ToolSpec(
        tool_name="run_semantic_temporal_baseline",
        task_type=TaskType.SEMANTIC_CHANGE,
        summary="EXPERIMENTAL composed baseline: ChangeFormer mask → connected regions → "
        "RemoteCLIP tags each region → rule-assembled change description.",
        required_inputs=["t1", "t2"],
        output_schema="ComposedSemanticChangeResult",
        specialist="ChangeFormer + RemoteCLIP (composed)",
        image_count=(2, 2),
        modality_requirements=["optical"],
        geospatial_requirements="co_registered_pair",
        allowed_followup_tasks=[TaskType.GROUND_OBJECT, TaskType.OPTICAL_SAR_ANALYSIS,
                                *_FINALIZE_OR_VERIFY],
        failure_modes=["checkpoint absent", "no region above size threshold"],
        caveats=["EXPERIMENTAL — not a learned temporal VLM, not validated semantic reasoning"],
    ),
    "run_optical_sar": ToolSpec(
        tool_name="run_optical_sar",
        task_type=TaskType.OPTICAL_SAR_ANALYSIS,
        summary="Joint optical + SAR representation for a paired Sentinel-2 (>=12 band) + "
        "Sentinel-1 (2 band) input (CROMA primary; DOFA fallback). Representation-level only.",
        required_inputs=["optical", "sar"],
        output_schema="JointReprResult",
        specialist="CROMA (DOFA fallback)",
        image_count=(2, 2),
        modality_requirements=["optical", "sar"],
        geospatial_requirements="valid_crs_optional",
        allowed_followup_tasks=[TaskType.CROSS_CHECK_EVIDENCE, *_FINALIZE_OR_VERIFY],
        failure_modes=["checkpoint absent", "SAR raster not 2-band", "optical raster < 12 band"],
        caveats=["representation-level only — an embedding must NOT be turned into an invented textual fact",
                 "EXP-004 Run 2 SAR benefit is positive but NOT significance-tested"],
    ),
    "extract_changed_regions": ToolSpec(
        tool_name="extract_changed_regions",
        task_type=TaskType.EXTRACT_CHANGED_REGIONS,
        summary="Connected-component regions from a change mask (deterministic; no model). "
        "Produces per-region pixel bbox + lon/lat bbox (when CRS present) + area.",
        required_inputs=["change_result_ref"],
        output_schema="RegionList",
        specialist="none (scipy.ndimage)",
        image_count=(0, 0),
        geospatial_requirements="none",
        allowed_followup_tasks=[TaskType.GROUND_OBJECT, TaskType.OPTICAL_SAR_ANALYSIS,
                                TaskType.CROSS_CHECK_EVIDENCE, *_FINALIZE_OR_VERIFY],
        failure_modes=["no prior change result", "no region above size threshold"],
    ),
    "cross_check_evidence": ToolSpec(
        tool_name="cross_check_evidence",
        task_type=TaskType.CROSS_CHECK_EVIDENCE,
        summary="Deterministic cross-check between two prior observations (e.g. does a grounded "
        "box fall inside a changed region?). No model.",
        required_inputs=["refs"],
        output_schema="CrossCheckResult",
        specialist="none (deterministic)",
        image_count=(0, 0),
        allowed_followup_tasks=_FINALIZE_OR_VERIFY,
        failure_modes=["fewer than two comparable observations"],
    ),
    "verify_result": ToolSpec(
        tool_name="verify_result",
        task_type=TaskType.VERIFY,
        summary="Aggregate the structural + geospatial + evidential verification of the "
        "observations so far (reuses packages/evidence + derive_resolution).",
        required_inputs=[],
        output_schema="VerificationSummary",
        specialist="none (packages/evidence)",
        image_count=(0, 0),
        allowed_followup_tasks=[TaskType.SUMMARIZE, TaskType.FINALIZE],
        failure_modes=["nothing to verify"],
    ),
    "inspect_evidence": ToolSpec(
        tool_name="inspect_evidence",
        task_type=TaskType.SUMMARIZE,
        summary="Collate the evidence items gathered so far into the audit surface. No model.",
        required_inputs=[],
        output_schema="EvidenceDigest",
        specialist="none",
        image_count=(0, 0),
        allowed_followup_tasks=[TaskType.FINALIZE],
        failure_modes=[],
    ),
    "finalize_answer": ToolSpec(
        tool_name="finalize_answer",
        task_type=TaskType.FINALIZE,
        summary="Build the evidence-first investigation report from observations + evidence + "
        "verification + geo results + failures + warnings. Deterministic template; the optional "
        "LLM summary may ONLY rephrase observed facts.",
        required_inputs=[],
        output_schema="AgentInvestigationResult",
        specialist="none (optional constrained LLM summary)",
        image_count=(0, 0),
        allowed_followup_tasks=[],
        failure_modes=[],
        caveats=["may NOT create unsupported factual claims"],
    ),
}


def tool_names() -> list[str]:
    return list(TOOL_REGISTRY.keys())


def registry_digest() -> list[dict[str, object]]:
    """Compact view for the planner prompt — no Python objects leak through."""
    return [
        {
            "tool": s.tool_name,
            "task": s.task_type.value,
            "summary": s.summary,
            "required_inputs": s.required_inputs,
            "optional_inputs": s.optional_inputs,
            "images": list(s.image_count),
            "modalities": s.modality_requirements,
            "geo": s.geospatial_requirements,
            "allowed_next": [t.value for t in s.allowed_followup_tasks],
        }
        for s in TOOL_REGISTRY.values()
    ]


def registry_lines() -> str:
    """One line per tool — a ~10x smaller prompt block for a small local planner."""
    out = []
    for s in TOOL_REGISTRY.values():
        lo, hi = s.image_count
        imgs = f"{lo}" if lo == hi else f"{lo}-{hi}"
        mod = f" [{','.join(s.modality_requirements)}]" if s.modality_requirements else ""
        one = s.summary.split(".")[0].strip()
        out.append(f"- {s.tool_name} (task {s.task_type.value}, images {imgs}{mod}): {one}")
    return "\n".join(out)
