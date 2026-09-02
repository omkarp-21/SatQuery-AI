"""G17 trust / confidence layer — an EVIDENCE-DERIVED confidence CATEGORY.

This is **not** a calibrated probability. It is a deterministic function of
observable signals from the executed investigation, producing one of:

    HIGH  ·  MEDIUM  ·  LOW  ·  INSUFFICIENT_EVIDENCE

The exact scoring rules are documented here and in `docs/G17_TRUST_LAYER.md`.
EXP-C1/C2 (calibrated numeric confidence) remains future work; nothing here is
labelled a probability.

Signals & points (added up, then mapped to a category):

| signal | contribution |
|--------|--------------|
| all planned specialists completed | +2 |
| some specialist failed (each) | -1 (floor -2) |
| the primary specialist for the mission family failed | HARD -> INSUFFICIENT_EVIDENCE |
| >= 1 evidence item present | +1 |
| no evidence at all | HARD -> INSUFFICIENT_EVIDENCE |
| verification SUPPORTED | +2 |
| verification CONTRADICTED | HARD -> INSUFFICIENT_EVIDENCE |
| a step verdict is INCOHERENT | -3 |
| geospatially grounded output present (GeoJSON) | +1 |
| cross-check: all grounded regions inside changed regions | +2 |
| cross-check: some inside | +1 |
| cross-check: none inside | -1 |
| comparison required and optical+SAR actually ran | +1 |
| a required modality was missing (e.g. no SAR) | -1 |
| intent ambiguity == high / low | -2 / -1 |
| planner fell back to the rule intent/plan | -1 |
| known-limitation signal present (RemoteSAM licence · experimental semantic-change · SAR representation-only) | -0.5 each, floor -1 |

Mapping (after the HARD rules): score >= 5 -> HIGH · 2 <= score < 5 -> MEDIUM ·
score < 2 -> LOW.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

_HIGH_MIN = 5.0
_MEDIUM_MIN = 2.0

# task -> the specialist tool that, if it fails, makes the whole mission unverifiable
_PRIMARY_TOOL = {
    "single_step": {"run_vqa", "run_grounding", "run_scene_retrieval"},
    "temporal": {"run_temporal_change", "run_semantic_temporal_baseline"},
    "optical_sar": {"run_optical_sar"},
    "multi_step": {"run_temporal_change"},
}


@dataclass
class ConfidenceAssessment:
    category: str = "INSUFFICIENT_EVIDENCE"     # HIGH | MEDIUM | LOW | INSUFFICIENT_EVIDENCE
    score: float = 0.0
    reasons: list[str] = field(default_factory=list)      # the user-facing "WHY"
    signals: dict[str, Any] = field(default_factory=dict)  # raw signal values (audit)
    hard_rule: str | None = None               # which hard rule forced the category, if any

    def public(self) -> dict[str, Any]:
        return {"category": self.category, "score": round(self.score, 2),
                "reasons": list(self.reasons), "signals": dict(self.signals),
                "hard_rule": self.hard_rule,
                "note": "evidence-derived category, deterministic rules (docs/G17_TRUST_LAYER.md). "
                        "NOT a calibrated probability."}


def assess_confidence(res, mem, plan, *, intent=None) -> ConfidenceAssessment:
    """Compute the confidence category from the executed `AgentInvestigationResult`."""
    a = ConfidenceAssessment()
    reasons: list[str] = []
    sig: dict[str, Any] = {}
    score = 0.0

    steps = list(res.steps or [])
    specialist_steps = [o for o in steps if o.tool.startswith("run_")]
    completed = [o for o in specialist_steps if o.status == "completed"]
    failed = [o for o in specialist_steps if o.status == "failed"]
    family = getattr(res, "mission_family", "unknown")
    vstatus = (res.verification or {}).get("status", "INSUFFICIENT_EVIDENCE")
    evidence_n = len(res.evidence or [])
    incoherent = [o for o in steps if getattr(o, "verdict", None) == "INCOHERENT"]

    sig.update(family=family, verification=vstatus, evidence_items=evidence_n,
               specialists_completed=len(completed), specialists_failed=len(failed),
               incoherent_steps=len(incoherent))

    # ---------- HARD rules ----------
    primary = _PRIMARY_TOOL.get(family, set())
    primary_failed = any(o.tool in primary for o in failed) and not any(o.tool in primary for o in completed)
    if vstatus == "CONTRADICTED":
        a.hard_rule = "verification CONTRADICTED"
    elif primary_failed:
        a.hard_rule = f"the primary specialist for a {family} mission failed"
    elif evidence_n == 0 and specialist_steps:
        a.hard_rule = "no evidence was produced"
    if a.hard_rule:
        a.category = "INSUFFICIENT_EVIDENCE"
        a.score = 0.0
        a.reasons = [f"Insufficient evidence: {a.hard_rule}."]
        a.signals = sig
        return a

    # ---------- additive signals ----------
    if specialist_steps and not failed:
        score += 2
        reasons.append(f"All {len(completed)} planned specialist step(s) completed.")
    for _ in failed[:2]:
        score -= 1
    if failed:
        reasons.append(f"{len(failed)} specialist step(s) failed (handled; downstream pruned).")

    if evidence_n:
        score += 1
        reasons.append(f"{evidence_n} evidence item(s) attached.")

    if vstatus == "SUPPORTED":
        score += 2
        reasons.append("Verification: SUPPORTED (aggregate of per-step checks).")
    elif vstatus == "INSUFFICIENT_EVIDENCE":
        reasons.append("Verification did not reach SUPPORTED.")

    if incoherent:
        score -= 3
        reasons.append(f"{len(incoherent)} step result was withheld as INCOHERENT.")

    if getattr(res, "geojson", None) and (res.geojson or {}).get("features"):
        score += 1
        reasons.append(f"{len(res.geojson['features'])} spatially grounded region(s) (EPSG:4326 GeoJSON).")

    # cross-check agreement
    cc = next((mem.results.get(o.step_id, {}) for o in steps
               if getattr(o.task, "value", str(o.task)) == "CROSS_CHECK_EVIDENCE"), None) \
        if hasattr(mem, "results") else None
    if cc and cc.get("matches"):
        matches = cc["matches"]
        inside = sum(1 for m in matches if m.get("centroid_in_changed_region"))
        sig["cross_check_inside"] = f"{inside}/{len(matches)}"
        if inside == len(matches) and matches:
            score += 2
            reasons.append(f"Cross-check: all {inside} grounded region(s) fall inside a changed region.")
        elif inside:
            score += 1
            reasons.append(f"Cross-check: {inside}/{len(matches)} grounded region(s) inside a changed region.")
        else:
            score -= 1
            reasons.append("Cross-check: no grounded region falls inside a changed region.")

    # modality completeness
    comparison_required = bool(getattr(intent, "comparison_required", False))
    sar_ran = any(o.tool == "run_optical_sar" and o.status == "completed" for o in steps)
    sar_skipped = any(o.tool == "run_optical_sar" and o.status == "skipped" for o in steps)
    if comparison_required and sar_ran:
        score += 1
        reasons.append("Optical+SAR comparison was requested and performed.")
    if sar_skipped or (comparison_required and not sar_ran):
        score -= 1
        reasons.append("A required modality (SAR) was missing — optical+SAR was not performed.")
        sig["missing_modality"] = "sar"

    # ambiguity (from the typed intent, when present)
    amb = getattr(intent, "ambiguity", "none")
    if amb == "high":
        score -= 2
        reasons.append("The mission wording was highly ambiguous.")
    elif amb == "low":
        score -= 1
        reasons.append("The mission wording was somewhat ambiguous.")
    sig["ambiguity"] = amb

    # planner fallback
    pu = getattr(res, "planner_used", "")
    if pu in ("rule_based_fallback", "hybrid_rule_fallback"):
        score -= 1
        reasons.append("The LLM intent/plan step fell back to the deterministic interpreter.")
    sig["planner_used"] = pu

    # known capability limitations
    warns = " ".join(res.warnings or []).lower()
    lim = 0.0
    if "licence not stated" in warns or "license not stated" in warns or "remotesam" in warns:
        lim += 0.5
    if "experimental" in warns or "composed baseline" in warns:
        lim += 0.5
    if any(o.tool == "run_optical_sar" and o.status == "completed" for o in steps):
        lim += 0.5
        reasons.append("Optical+SAR result is representation-level only (no textual claim from the embedding).")
    lim = min(lim, 1.0)
    score -= lim
    sig["known_limitation_penalty"] = lim

    # ---------- map to category ----------
    if score >= _HIGH_MIN:
        a.category = "HIGH"
    elif score >= _MEDIUM_MIN:
        a.category = "MEDIUM"
    else:
        a.category = "LOW"
        reasons.append("Overall evidence support is thin (LOW).")

    a.score = score
    a.reasons = reasons
    a.signals = sig
    return a
