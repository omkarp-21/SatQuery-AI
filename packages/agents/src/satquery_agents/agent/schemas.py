"""Typed contracts for the SatQuery agentic investigator (G14).

The planner (an LLM, or the deterministic rule planner) emits an `AgentPlan` that
is **only ever executed after `policy.validate_plan` passes**. Every field is
typed; a malformed plan is rejected, never run.

No model code is imported here — these are pure contracts shared by the planner,
the policy layer, and the executor.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

# --------------------------------------------------------------------------- #
# Task ontology — a FINITE set. The planner may not invent task names.
# --------------------------------------------------------------------------- #


class TaskType(str, Enum):
    VALIDATE_INPUT = "VALIDATE_INPUT"
    SCENE_UNDERSTANDING = "SCENE_UNDERSTANDING"
    VQA = "VQA"
    GROUND_OBJECT = "GROUND_OBJECT"
    TEMPORAL_CHANGE = "TEMPORAL_CHANGE"
    SEMANTIC_CHANGE = "SEMANTIC_CHANGE"
    OPTICAL_SAR_ANALYSIS = "OPTICAL_SAR_ANALYSIS"
    EXTRACT_CHANGED_REGIONS = "EXTRACT_CHANGED_REGIONS"
    CROSS_CHECK_EVIDENCE = "CROSS_CHECK_EVIDENCE"
    VERIFY = "VERIFY"
    SUMMARIZE = "SUMMARIZE"
    FINALIZE = "FINALIZE"


#: Tools the planner may select — a CLOSED set mirrored by ``registry.TOOL_REGISTRY``.
ToolName = Literal[
    "validate_geospatial_input",
    "run_vqa",
    "run_grounding",
    "run_scene_retrieval",
    "run_temporal_change",
    "run_semantic_temporal_baseline",
    "run_optical_sar",
    "extract_changed_regions",
    "cross_check_evidence",
    "verify_result",
    "inspect_evidence",
    "finalize_answer",
]

MAX_STEPS = 8  # bounded autonomy — hard cap on tool actions per mission


# --------------------------------------------------------------------------- #
# Typed INTENT (G17) — what the LLM produces. NOT an execution graph.
#
# The hybrid architecture is: mission text -> LLM intent extraction -> typed
# ``Intent`` -> deterministic ``PlanSynthesizer`` -> ``AgentPlan`` -> policy ->
# bounded adaptive execution. The LLM classifies the goal; it never chooses
# tools or builds a plan. G16 measured that the 2 B model can echo but not plan;
# asking it only for this small typed object removes the part it fails at.
# --------------------------------------------------------------------------- #


class TaskFamily(str, Enum):
    VQA = "VQA"
    GROUNDING = "GROUNDING"
    SCENE = "SCENE"
    TEMPORAL_CHANGE = "TEMPORAL_CHANGE"
    SEMANTIC_CHANGE = "SEMANTIC_CHANGE"
    OPTICAL_SAR = "OPTICAL_SAR"
    INVESTIGATION = "INVESTIGATION"
    UNSUPPORTED = "UNSUPPORTED"


class Capability(str, Enum):
    VQA = "VQA"
    GROUNDING = "GROUNDING"
    SCENE_RETRIEVAL = "SCENE_RETRIEVAL"
    TEMPORAL_CHANGE = "TEMPORAL_CHANGE"
    SEMANTIC_CHANGE = "SEMANTIC_CHANGE"
    CHANGED_REGIONS = "CHANGED_REGIONS"
    OPTICAL_SAR = "OPTICAL_SAR"
    CROSS_CHECK = "CROSS_CHECK"


class Intent(BaseModel):
    """A compact, typed classification of the user's mission."""

    goal: str = Field(min_length=1, description="the mission restated in one line")
    task_family: TaskFamily
    required_capabilities: list[Capability] = Field(default_factory=list)
    objects: list[str] = Field(default_factory=list, description="nouns to locate, e.g. ['building']")
    temporal_required: bool = False
    spatial_required: bool = False           # grounding / changed-region extraction
    comparison_required: bool = False        # optical vs SAR
    investigation_required: bool = False     # >= 2 distinct analyses
    requested_outputs: list[str] = Field(default_factory=list)  # change_map|regions|evidence|verification|geojson
    constraints: list[str] = Field(default_factory=list)
    ambiguity: Literal["none", "low", "high"] = "none"
    ambiguity_note: str = ""
    source: str = "unknown"                  # rule_based | llm | llm_repaired | rule_based_fallback

    @field_validator("required_capabilities")
    @classmethod
    def _dedup(cls, v: list[Capability]) -> list[Capability]:
        seen: list[Capability] = []
        for c in v:
            if c not in seen:
                seen.append(c)
        return seen


# --------------------------------------------------------------------------- #
# The plan
# --------------------------------------------------------------------------- #


class PlanStep(BaseModel):
    step_id: str = Field(pattern=r"^s[0-9]{1,2}$", description="s1, s2, …")
    task: TaskType
    tool: ToolName
    inputs: dict[str, Any] = Field(default_factory=dict, description="image refs / phrase / region ref / …")
    depends_on: list[str] = Field(default_factory=list)
    reason: str = Field(min_length=1, description="why this step is in the plan")
    required_verification: bool = True
    success_condition: str = Field(default="tool returned ok and produced its declared output")

    @field_validator("depends_on")
    @classmethod
    def _no_self_dep(cls, v: list[str], info: Any) -> list[str]:
        sid = info.data.get("step_id")
        if sid and sid in v:
            raise ValueError(f"step {sid} depends on itself")
        return v


class AgentPlan(BaseModel):
    goal: str = Field(min_length=1)
    inputs: list[str] = Field(default_factory=list, description="image ids / paths available to the mission")
    steps: list[PlanStep] = Field(min_length=1)
    constraints: list[str] = Field(default_factory=list)
    expected_output: str = Field(default="an evidence-backed investigation summary")
    planner: str = Field(default="unknown", description="which planner produced this plan")

    @field_validator("steps")
    @classmethod
    def _cap_steps(cls, v: list[PlanStep]) -> list[PlanStep]:
        if len(v) > MAX_STEPS + 4:  # +4 head-room for VALIDATE/VERIFY/SUMMARIZE/FINALIZE bookkeeping
            raise ValueError(f"plan has {len(v)} steps; hard limit is {MAX_STEPS + 4}")
        ids = [s.step_id for s in v]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate step_id")
        return v

    def tool_step_count(self) -> int:
        """Steps that actually invoke a specialist (exclude pure bookkeeping)."""
        bookkeeping = {"verify_result", "inspect_evidence", "finalize_answer", "cross_check_evidence"}
        return sum(1 for s in self.steps if s.tool not in bookkeeping)


# --------------------------------------------------------------------------- #
# Execution state
# --------------------------------------------------------------------------- #

AgentPhase = Literal[
    "INITIAL", "PLANNING", "PLAN_VALIDATION", "EXECUTING", "OBSERVING",
    "VERIFYING", "REPLANNING", "FINALIZING", "FAILED", "BLOCKED",
]

StepStatus = Literal["pending", "running", "completed", "skipped", "failed"]
StepVerdict = Literal["COHERENT", "INCOHERENT", "INSUFFICIENT", "NOT_APPLICABLE"]

#: Why the executor deviated from the validated plan. A closed set — the executor
#: never "replans" for an un-enumerated reason.
ReplanReason = Literal[
    "NEW_EVIDENCE",                 # an observation makes downstream steps unnecessary
    "TOOL_FAILURE",                 # a specialist failed; downstream that needed it is pruned
    "MISSING_INPUT",               # a required modality/input is absent (e.g. no SAR)
    "INSUFFICIENT_EVIDENCE",       # a step produced nothing usable
    "VERIFICATION_CONTRADICTION",  # verification contradicts a proposed conclusion
    "TASK_COMPLETE",               # mission-completion condition met -> stop early
]


class ReplanEvent(BaseModel):
    reason: ReplanReason
    triggering_step: str
    previous_phase: AgentPhase
    detail: str
    steps_skipped: list[str] = Field(default_factory=list)
    ts: str


class StepObservation(BaseModel):
    step_id: str
    task: TaskType
    tool: ToolName
    status: StepStatus
    verdict: StepVerdict = "NOT_APPLICABLE"
    summary: str = ""
    # references only — never raw images/embeddings
    result_ref: str | None = None
    evidence_ids: list[str] = Field(default_factory=list)
    verification_status: str | None = None
    resolution_qualifier: str | None = None
    findings: dict[str, Any] = Field(default_factory=dict)  # compact structured observation
    numeric: dict[str, float] = Field(default_factory=dict)  # e.g. {"changed_fraction": 0.25}
    failure: str | None = None
    contributed: bool = True  # did this call contribute to mission completion? (for UNNECESSARY_TOOL_CALL_RATE)
    started_at: str | None = None
    finished_at: str | None = None
    runtime_s: float | None = None
    replan_note: str | None = None  # short human note; the structured record is in AgentInvestigationResult.replans


class TimelineEntry(BaseModel):
    ts: str
    event: str


class SpatialFinding(BaseModel):
    label: str
    where_pixel: list[float] | None = None
    where_lonlat: list[float] | None = None
    area_ha: float | None = None
    source_step: str


class AgentInvestigationResult(BaseModel):
    # --- request ---
    mission: str
    inputs: list[str] = Field(default_factory=list)
    mode: Literal["investigate", "ask-fallback"] = "investigate"

    # --- plan ---
    plan: AgentPlan | None = None
    plan_status: Literal["valid", "rejected", "fallback", "no_planner"] = "no_planner"
    plan_rejection_reasons: list[str] = Field(default_factory=list)
    planner_used: str = "none"
    intent: dict[str, Any] | None = None  # G17: the typed Intent the plan was synthesised from (hybrid)

    # --- execution ---
    phase: AgentPhase = "INITIAL"
    ok: bool = False
    # G20.1: top-level investigation outcome — DISTINCT from `verification` (which
    # judges only the evidence that was produced) and from `confidence`.
    #   SUCCESS  every planned specialist completed, or a legitimate early stop
    #   PARTIAL  some specialists completed, some failed / were pruned by a failure
    #   BLOCKED  a pre-condition (co-registration, CRS, unreadable input, missing
    #            required modality) stopped the analysis before any conclusion
    #   FAILED   the agent itself could not run (no plan, contradiction, 0 calls)
    investigation_status: Literal["SUCCESS", "PARTIAL", "BLOCKED", "FAILED"] | None = None
    investigation_status_reason: str | None = None  # one human-readable sentence
    mission_family: str = "unknown"  # single_step | temporal | optical_sar | multi_step | unsupported
    steps: list[StepObservation] = Field(default_factory=list)
    replans: list[ReplanEvent] = Field(default_factory=list)
    tool_calls: int = 0
    max_steps: int = MAX_STEPS
    hit_step_cap: bool = False
    early_stopped: bool = False
    completion_reason: str | None = None  # why the mission was considered complete

    # --- findings ---
    conclusion: str | None = None
    key_findings: list[str] = Field(default_factory=list)
    spatial_findings: list[SpatialFinding] = Field(default_factory=list)
    geojson: dict[str, Any] | None = None  # FeatureCollection of the spatial findings (EPSG:4326), when geo is available

    # --- audit ---
    evidence: list[dict[str, Any]] = Field(default_factory=list)
    verification: dict[str, Any] | None = None
    confidence: dict[str, Any] | None = None  # G17 trust layer: HIGH|MEDIUM|LOW|INSUFFICIENT_EVIDENCE + why
    resolution: dict[str, Any] | None = None
    provenance: dict[str, Any] = Field(default_factory=dict)
    execution_trace: list[TimelineEntry] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    failures: list[str] = Field(default_factory=list)
    models_used: list[str] = Field(default_factory=list)
    timings: dict[str, float] = Field(default_factory=dict)
