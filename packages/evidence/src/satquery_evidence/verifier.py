"""Verification contract - first version.

`verify(result, evidence, context) -> VerificationResult`

**Deterministic, structural checks only.** This layer decides whether a specialist
result is *structurally well-formed and consistent with its inputs* - NOT whether
it is semantically correct. Semantic verification (independent re-derivation,
optical/SAR agreement, calibration) comes later.

Statuses:
- SUPPORTED           - all applicable structural checks passed
- CONTRADICTED        - a structural check failed (bad shape, missing artifact, ...)
- INSUFFICIENT_EVIDENCE - nothing to check against (no evidence items / no context)
- NOT_APPLICABLE      - verification does not apply to this result type
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel

from .models import EvidenceItem

VerificationStatus = Literal[
    "SUPPORTED", "CONTRADICTED", "INSUFFICIENT_EVIDENCE", "NOT_APPLICABLE"
]


class Check(BaseModel):
    name: str
    passed: bool
    detail: str


class VerificationResult(BaseModel):
    status: VerificationStatus
    checks: list[Check]
    notes: str = (
        "structural / deterministic checks only - NOT a semantic correctness judgement"
    )

    def failed(self) -> list[Check]:
        return [c for c in self.checks if not c.passed]


def verify(
    result: dict[str, Any],
    evidence: list[EvidenceItem],
    context: dict[str, Any] | None = None,
) -> VerificationResult:
    """Run the applicable deterministic checks over a normalized result + evidence."""
    ctx = context or {}
    checks: list[Check] = []

    # 1. inputs existed
    inputs = ctx.get("input_paths") or ctx.get("input_ids") or []
    if inputs:
        missing = [p for p in inputs if isinstance(p, str) and ctx.get("inputs_exist", {}).get(p) is False]
        checks.append(Check(name="inputs_exist", passed=not missing,
                            detail=f"{len(inputs)} declared, missing={missing}"))

    # 2. requested modality is one the model declares
    want_mod = ctx.get("requested_modality")
    model_mods = ctx.get("model_modalities")
    if want_mod and model_mods is not None:
        ok = want_mod in model_mods
        checks.append(Check(name="modality_supported", passed=ok,
                            detail=f"requested {want_mod!r} vs model {list(model_mods)}"))

    # 3. geospatial compatibility (if a pair was involved)
    if "pair_co_registered" in ctx:
        ok = bool(ctx["pair_co_registered"])
        checks.append(Check(name="geospatial_compatibility", passed=ok,
                            detail="pair co-registered" if ok else "pair NOT co-registered"))

    # 4. artifact exists / output well-formed
    for ev in evidence:
        if ev.evidence_type == "change-mask":
            mp = ev.payload.get("mask_path")
            cf = ev.payload.get("changed_fraction")
            checks.append(Check(name=f"mask_artifact[{ev.evidence_id}]",
                                passed=bool(mp), detail=f"mask_path={mp}"))
            if cf is not None:
                checks.append(Check(name=f"changed_fraction_range[{ev.evidence_id}]",
                                    passed=(0.0 <= float(cf) <= 1.0), detail=f"cf={cf}"))
        elif ev.evidence_type == "embedding":
            dim = ev.payload.get("dim") or len(ev.payload.get("vector", []) or [])
            checks.append(Check(name=f"embedding_dim[{ev.evidence_id}]",
                                passed=dim and dim > 0, detail=f"dim={dim}"))
        elif ev.evidence_type == "ranking":
            r = ev.payload.get("ranking", [])
            probs_ok = all(0.0 <= float(p) <= 1.0 for _, p in r) if r else False
            checks.append(Check(name=f"ranking_probs[{ev.evidence_id}]",
                                passed=probs_ok, detail=f"n={len(r)}"))

    if not checks:
        return VerificationResult(status="INSUFFICIENT_EVIDENCE", checks=[])
    if all(c.passed for c in checks):
        return VerificationResult(status="SUPPORTED", checks=checks)
    return VerificationResult(status="CONTRADICTED", checks=checks)
