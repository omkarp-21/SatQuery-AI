"""SatQuery agentic geospatial investigator (G14).

The LLM (or the rule planner) is the PLANNER. The deterministic system is the
POLICY / EXECUTION GUARD. The planner never invents tools, capabilities,
coordinates, or evidence, and never bypasses validation.

Contracts live here; the executor that binds tools to the frozen-stack
specialist slices lives in ``apps/backend/app/services/agent_runner.py``.
"""

from __future__ import annotations

from .memory import AgentMemory, RegionRef
from .planner import (
    LlmPlanner,
    MissionFeatures,
    Planner,
    RuleBasedPlanner,
    make_planner,
    plan_with_fallback,
    plan_with_fallback_ex,
)
from .policy import PlanContext, PolicyResult, validate_plan
from .repair import PlannerAttempt, build_plan_from_raw, repair_plan_dict
from .registry import TOOL_REGISTRY, ToolSpec, registry_digest, tool_names
from .schemas import (
    MAX_STEPS,
    AgentInvestigationResult,
    AgentPhase,
    AgentPlan,
    PlanStep,
    ReplanEvent,
    ReplanReason,
    SpatialFinding,
    StepObservation,
    StepVerdict,
    TaskType,
    TimelineEntry,
    ToolName,
)
from .verifier import assess_step

__all__ = [
    "AgentInvestigationResult", "AgentMemory", "AgentPhase", "AgentPlan", "MAX_STEPS",
    "MissionFeatures", "PlanContext", "PlanStep", "Planner", "PlannerAttempt", "PolicyResult",
    "RegionRef", "LlmPlanner", "ReplanEvent", "ReplanReason", "RuleBasedPlanner", "SpatialFinding",
    "StepObservation", "StepVerdict",
    "TOOL_REGISTRY", "TaskType", "TimelineEntry", "ToolName", "ToolSpec",
    "assess_step", "build_plan_from_raw", "make_planner", "plan_with_fallback",
    "plan_with_fallback_ex", "registry_digest", "repair_plan_dict", "tool_names",
    "validate_plan",
]
