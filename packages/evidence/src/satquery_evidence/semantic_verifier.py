"""Semantic verification - first version (model-independent checks only).

`verify_semantic(result, evidence, context) -> SemanticVerificationResult`

Where `verify()` (structural) asks *"is this result well-formed and consistent
with its inputs?"*, `verify_semantic()` asks a narrower semantic question:
*"do the pieces of evidence, the dates, and the geometry contradict the claim?"*

It is **deterministic and model-independent**. It does NOT re-run a model and it
does NOT judge whether a label is correct in the world - it only catches
**internal semantic incoherence** that can be seen by cross-referencing what is
already in `evidence` + `context`:

- a claimed number that disagrees with the evidence payload,
- a claimed label that appears in no evidence item,
- a forward-in-time change phrase on a T1 > T2 (swapped) pair,
- a spatial region outside the image, or one that *is* the whole scene,
- region areas that sum to more than the reported total.

Checks that need a second model or another modality (independent-model agreement,
optical<->SAR agreement, grounding round-trip) are **declared in `coverage` as
NOT AVAILABLE** - they are the gap this first version does not close.

Statuses:
- COHERENT              - every applicable semantic check passed
- INCOHERENT            - at least one semantic check found a contradiction
- NOT_ENOUGH_EVIDENCE   - nothing semantic to check
- NOT_APPLICABLE        - semantic verification does not apply to this result
"""

from __future__ import annotations

import re
from typing import Any, Literal

from pydantic import BaseModel

from .models import EvidenceItem
from .verifier import Check

SemanticStatus = Literal["COHERENT", "INCOHERENT", "NOT_ENOUGH_EVIDENCE", "NOT_APPLICABLE"]

# checks that would need a second model / another modality - not implemented here
_UNAVAILABLE_CHECKS = (
    "independent_model_agreement",   # needs >= 2 VQA models (EXP-002, blocked)
    "optical_sar_agreement",         # needs the EXP-004 Run 2 predictions
    "grounding_roundtrip",           # needs a grounding model to re-locate the phrase
)

_FORWARD_CHANGE_TOKENS = (
    "new ", "newly", "added", "constructed", "construction", "built", "appears",
    "expansion", "expanded", "gain", "increase", "emerged",
)
_TOL = 0.02


class SemanticVerificationResult(BaseModel):
    status: SemanticStatus
    checks: list[Check]
    coverage_available: list[str]
    coverage_unavailable: list[str] = list(_UNAVAILABLE_CHECKS)
    notes: str = (
        "model-independent semantic-coherence checks only - catches internal "
        "contradictions between claim, evidence, dates and geometry; does NOT "
        "judge real-world label correctness (that needs an independent model)"
    )

    def failed(self) -> list[Check]:
        return [c for c in self.checks if not c.passed]


def _year(v: Any) -> int | None:
    m = re.search(r"(\d{4})", str(v))
    return int(m.group(1)) if m else None


def _pct_in_text(text: str) -> float | None:
    m = re.search(r"(\d+(?:\.\d+)?)\s*%", text)
    if m:
        return float(m.group(1)) / 100.0
    m = re.search(r"(\d+(?:\.\d+)?)\s*percent", text)
    return float(m.group(1)) / 100.0 if m else None


def _label_in_text(text: str) -> str | None:
    m = re.search(r"resembles\s+'([^']+)'", text) or re.search(r'resembles\s+"([^"]+)"', text)
    return m.group(1) if m else None


def verify_semantic(
    result: dict[str, Any],
    evidence: list[EvidenceItem],
    context: dict[str, Any] | None = None,
) -> SemanticVerificationResult:
    """Run the model-independent semantic-coherence checks."""
    ctx = context or {}
    checks: list[Check] = []
    available: list[str] = []

    payloads = [e.payload for e in evidence]
    # scan ONLY the model's assembled narrative for its stated numbers / labels /
    # direction - never the evidence items' own claim strings (those are the thing
    # we check against, folding them in would mask a mismatch).
    desc = str(result.get("description") or "")
    if not desc:
        desc = " ".join(e.claim_supported for e in evidence if e.evidence_type != "change-mask")

    # 1. a percentage in the claim/description must match an evidence number
    claimed_pct = _pct_in_text(desc)
    ev_fracs = [float(p["changed_fraction"]) for p in payloads
                if isinstance(p.get("changed_fraction"), (int, float))]
    if claimed_pct is not None and ev_fracs:
        available.append("claim_matches_evidence_number")
        ok = any(abs(claimed_pct - f) <= max(_TOL, 0.05 * f) for f in ev_fracs)
        checks.append(Check(name="claim_matches_evidence_number", passed=ok,
                            detail=f"claim {claimed_pct:.3f} vs evidence {ev_fracs}"))

    # 2. a quoted label in the description must appear as a top_label in some evidence item
    claimed_label = _label_in_text(desc)
    ev_labels = {str(p.get("top_label")).lower() for p in payloads if p.get("top_label")}
    if claimed_label is not None:
        available.append("claim_label_in_evidence")
        ok = claimed_label.lower() in ev_labels
        checks.append(Check(name="claim_label_in_evidence", passed=ok,
                            detail=f"claim label {claimed_label!r} vs evidence {sorted(ev_labels)}"))

    # 3. forward-in-time change phrasing on a swapped (T1 > T2) pair
    tctx = ctx.get("temporal_context") or {}
    for ev in evidence:
        tctx = tctx or (ev.temporal_context or {})
    y1, y2 = _year(tctx.get("t1")), _year(tctx.get("t2"))
    if y1 is not None and y2 is not None:
        available.append("temporal_direction_coherent")
        forward = any(tok in desc.lower() for tok in _FORWARD_CHANGE_TOKENS)
        ok = not (forward and y1 > y2)
        checks.append(Check(name="temporal_direction_coherent", passed=ok,
                            detail=f"t1={y1} t2={y2} forward_phrasing={forward}"))

    # 4. spatial region inside the image / valid lon-lat
    shape = ctx.get("image_shape")  # (H, W)
    for ev in evidence:
        sr = ev.spatial_region or {}
        bp = sr.get("bbox_pixel")
        if bp and shape:
            available.append("spatial_region_in_bounds")
            h, w = shape
            rmin, cmin, rmax, cmax = bp
            ok = (0 <= rmin < rmax <= h) and (0 <= cmin < cmax <= w)
            checks.append(Check(name=f"spatial_region_in_bounds[{ev.evidence_id}]", passed=ok,
                                detail=f"bbox_pixel={bp} image={shape}"))
        ll = sr.get("bbox_lonlat")
        if ll:
            available.append("lonlat_valid")
            lo0, la0, lo1, la1 = ll
            ok = (-180 <= lo0 < lo1 <= 180) and (-90 <= la0 < la1 <= 90)
            checks.append(Check(name=f"lonlat_valid[{ev.evidence_id}]", passed=ok,
                                detail=f"bbox_lonlat={ll}"))

    # 5. a "changed region" that is (almost) the whole scene is incoherent
    scene_px = ctx.get("scene_pixels")
    if scene_px:
        for reg in result.get("regions", []) or []:
            ap = reg.get("area_px") if isinstance(reg, dict) else getattr(reg, "area_px", None)
            if ap:
                available.append("region_area_sane")
                ok = 0 < ap < 0.95 * scene_px
                checks.append(Check(name=f"region_area_sane[{reg.get('region_id') if isinstance(reg, dict) else getattr(reg, 'region_id', '?')}]",
                                    passed=ok, detail=f"area_px={ap} scene_px={scene_px}"))

    # 6. sum of region areas must not exceed the reported total changed area
    regions = result.get("regions", []) or []
    total_ha = result.get("changed_area_ha") or ctx.get("changed_area_ha")
    reg_ha = [(r.get("area_ha") if isinstance(r, dict) else getattr(r, "area_ha", None)) for r in regions]
    reg_ha = [x for x in reg_ha if isinstance(x, (int, float))]
    if total_ha and reg_ha:
        available.append("region_areas_within_total")
        ok = sum(reg_ha) <= float(total_ha) * (1.0 + 0.10)
        checks.append(Check(name="region_areas_within_total", passed=ok,
                            detail=f"sum(regions)={sum(reg_ha):.3f} ha vs total {total_ha} ha"))

    available = sorted(set(available))
    if not checks:
        return SemanticVerificationResult(status="NOT_ENOUGH_EVIDENCE", checks=[],
                                          coverage_available=available)
    if all(c.passed for c in checks):
        return SemanticVerificationResult(status="COHERENT", checks=checks,
                                          coverage_available=available)
    return SemanticVerificationResult(status="INCOHERENT", checks=checks,
                                      coverage_available=available)
