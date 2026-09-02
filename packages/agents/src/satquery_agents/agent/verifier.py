"""Per-step verdict for the agent's observe/verify phase (G14).

Wraps the structural verification a specialist slice already computed
(`packages/evidence.verify`) plus the failure-aware `resolution` qualifier, and
adds a few sanity checks, into one `StepVerdict`. No model, no LLM.
"""

from __future__ import annotations

from typing import Any

from .schemas import StepVerdict, TaskType


def assess_step(
    *,
    task: TaskType,
    ok: bool,
    payload: dict[str, Any],
    verification: dict[str, Any] | None,
    resolution: dict[str, Any] | None,
) -> tuple[StepVerdict, str]:
    """Return (verdict, one-line reason). COHERENT / INCOHERENT / INSUFFICIENT / NOT_APPLICABLE."""
    if not ok:
        return "INSUFFICIENT", "specialist returned ok=false"

    v_status = (verification or {}).get("status")
    r_qual = (resolution or {}).get("qualifier")

    if v_status == "CONTRADICTED" or r_qual == "RESULT_STRUCTURAL_FAIL":
        return "INCOHERENT", f"structural verification failed ({v_status or r_qual})"
    if r_qual == "RESULT_SEMANTIC_INCOHERENT":
        return "INCOHERENT", "semantic verifier flagged incoherence"

    # task-specific sanity
    if task == TaskType.GROUND_OBJECT:
        vstat = payload.get("validation_status")
        if payload.get("bbox_xyxy") is None or vstat in ("NO_REGION", None):
            return "INSUFFICIENT", "no region grounded (explicit, not fabricated)"
        if vstat != "PASS":
            return "INCOHERENT", f"grounded box failed spatial check ({vstat})"
    if task == TaskType.TEMPORAL_CHANGE:
        stats = payload.get("stats") or {}
        cf = stats.get("changed_fraction")
        if cf is None:
            return "INSUFFICIENT", "no changed-fraction produced"
    if task == TaskType.OPTICAL_SAR_ANALYSIS:
        rep = payload.get("representation") or {}
        if not rep.get("dim"):
            return "INSUFFICIENT", "no joint representation dimension"

    if v_status in ("SUPPORTED", "NOT_APPLICABLE", None):
        return ("COHERENT" if v_status == "SUPPORTED" else "NOT_APPLICABLE",
                f"verification {v_status or 'not applicable'}")
    if v_status == "INSUFFICIENT_EVIDENCE":
        return "INSUFFICIENT", "verifier had insufficient evidence"
    return "NOT_APPLICABLE", f"verification status {v_status}"
