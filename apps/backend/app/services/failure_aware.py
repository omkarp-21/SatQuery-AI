"""Failure-aware routing — post-execution qualifier (G8 Phase 10).

`derive_resolution(...)` is a **pure, deterministic, model-independent** function
of the two verifier statuses plus the sub-service ok/degraded flags. It produces
one qualifier and says whether the answer should be surfaced as-is. No LLM, no
loop, no recursion. Design: `docs/research/FAILURE_AWARE_ROUTING.md`.

Qualifiers (one per result):
- RESULT_OK                 structural SUPPORTED and semantic COHERENT/NOT_ENOUGH
- RESULT_STRUCTURAL_FAIL    structural verifier CONTRADICTED       -> answer withheld
- RESULT_SEMANTIC_INCOHERENT semantic verifier INCOHERENT          -> answer disputed
- RESULT_UNVERIFIED         nothing checkable either way            -> answer surfaced, flagged
- SPECIALIST_DEGRADED       a declared fallback produced the result -> answer surfaced, flagged
- SPECIALIST_FAILED         the sub-service returned ok=false and no fallback helped
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from satquery_evidence import SemanticVerificationResult, VerificationResult

_Qualifier = str


class ResolutionInfo(BaseModel):
    qualifier: _Qualifier
    answer_surfaced: bool
    disputed: bool = False
    reasons: list[str] = []
    fallback_used: str | None = None
    structural_status: str | None = None
    semantic_status: str | None = None
    note: str = (
        "deterministic post-execution qualifier - a function of verify() + "
        "verify_semantic() + sub-service status; NOT a confidence value"
    )


def derive_resolution(
    *,
    sub_ok: bool,
    verification: VerificationResult | None,
    semantic_verification: SemanticVerificationResult | None = None,
    fallback_used: str | None = None,
) -> ResolutionInfo:
    v = verification.status if verification else None
    s = semantic_verification.status if semantic_verification else None
    common: dict[str, Any] = {"structural_status": v, "semantic_status": s,
                              "fallback_used": fallback_used}

    if not sub_ok and not fallback_used:
        return ResolutionInfo(qualifier="SPECIALIST_FAILED", answer_surfaced=False,
                              reasons=["sub-service returned ok=false; no fallback"], **common)

    if v == "CONTRADICTED":
        return ResolutionInfo(
            qualifier="RESULT_STRUCTURAL_FAIL", answer_surfaced=False,
            reasons=[c.name for c in verification.failed()] or ["structural checks failed"],
            **common,
        )

    if s == "INCOHERENT":
        return ResolutionInfo(
            qualifier="RESULT_SEMANTIC_INCOHERENT", answer_surfaced=False, disputed=True,
            reasons=[c.name for c in semantic_verification.failed()] or ["semantic incoherence"],
            **common,
        )

    if fallback_used:
        return ResolutionInfo(
            qualifier="SPECIALIST_DEGRADED", answer_surfaced=True,
            reasons=[f"primary specialist failed; used declared fallback '{fallback_used}'"],
            **common,
        )

    structural_blank = v in (None, "INSUFFICIENT_EVIDENCE", "NOT_APPLICABLE")
    semantic_blank = s in (None, "NOT_ENOUGH_EVIDENCE", "NOT_APPLICABLE")
    if structural_blank and semantic_blank:
        return ResolutionInfo(qualifier="RESULT_UNVERIFIED", answer_surfaced=True,
                              reasons=["no applicable verification checks - result is not checked"],
                              **common)

    return ResolutionInfo(qualifier="RESULT_OK", answer_surfaced=True, reasons=[], **common)
