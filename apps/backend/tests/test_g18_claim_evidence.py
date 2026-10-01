"""G18 Part 8 — claim-level evidence audit.

Every substantive factual claim in a SatQuery final synthesis must trace to an
observed specialist output, and no forbidden / overclaiming phrasing may appear.

Sources audited:
  * the 15 captured demo responses in docs/sih/evidence/demos/*.json (real runs,
    G13-G17) — >= 30 individual key_findings / answer claims
  * 8 constructed synthesis scenarios through agent_runner._synthesize covering
    each claim template + the "never say this" cases
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[3]
_DEMOS = sorted((_REPO / "docs" / "sih" / "evidence" / "demos").glob("*.json"))

# phrasing that must NEVER appear in a user-facing claim
_FORBIDDEN = [
    r"sar confirms", r"sar shows (that )?construction", r"radar confirms",
    r"fully autonomous", r"state[- ]of[- ]the[- ]art", r"\breal[- ]time\b",
    r"hallucination[- ]free", r"\b\d{1,3}\s?% confiden", r"we are certain",
    r"definitely (a |an )", r"guaranteed",
]
_FORBIDDEN_RE = re.compile("|".join(_FORBIDDEN), re.I)

# a claim prefix -> the evidence_type(s) or observed step that must back it
_CLAIM_BACKING = {
    "change detected": {"evidence": {"change-mask"}, "step_task": {"TEMPORAL_CHANGE", "SEMANTIC_CHANGE"}},
    "no significant change": {"step_task": {"TEMPORAL_CHANGE"}},
    "changed region": {"step_task": {"EXTRACT_CHANGED_REGIONS"}},
    "grounding located": {"evidence": {"grounding"}, "step_task": {"GROUND_OBJECT"}},
    "grounding: no": {"step_task": {"GROUND_OBJECT"}},
    "optical+sar": {"evidence": {"embedding"}, "step_task": {"OPTICAL_SAR_ANALYSIS"}},
    "cross-check": {"step_task": {"CROSS_CHECK_EVIDENCE"}},
    "scene:": {"step_task": {"SCENE_UNDERSTANDING"}},
    "vqa:": {"step_task": {"VQA"}},
}


def _iter_demo_claims():
    for f in _DEMOS:
        d = json.loads(f.read_text())
        claims = list(d.get("key_findings") or [])
        if not claims:
            a = d.get("answer") or d.get("conclusion")
            if a:
                claims = [a]
        for c in claims:
            yield f.name, c, d


_ALL_DEMO_CLAIMS = list(_iter_demo_claims())


def test_at_least_30_representative_claims_audited():
    assert len(_ALL_DEMO_CLAIMS) >= 30, len(_ALL_DEMO_CLAIMS)


@pytest.mark.parametrize("name,claim,doc", _ALL_DEMO_CLAIMS,
                         ids=[f"{n}:{i}" for i, (n, c, d) in enumerate(_ALL_DEMO_CLAIMS)])
def test_demo_claim_has_no_forbidden_phrasing(name, claim, doc):
    m = _FORBIDDEN_RE.search(claim)
    assert not m, f"{name}: forbidden phrasing {m.group(0)!r} in claim: {claim!r}"


@pytest.mark.parametrize("name,claim,doc", _ALL_DEMO_CLAIMS,
                         ids=[f"{n}:{i}" for i, (n, c, d) in enumerate(_ALL_DEMO_CLAIMS)])
def test_demo_claim_traces_to_an_observation(name, claim, doc):
    """A substantive claim must be backed by a matching evidence item OR an
    observed step of the right task. Generic summary lines are exempt."""
    low = claim.lower()
    backing = next((v for k, v in _CLAIM_BACKING.items() if low.startswith(k) or f" {k}" in low), None)
    if backing is None:
        # not a templated factual claim (e.g. a plain VQA answer or scene phrase) -
        # only the forbidden-phrasing check applies to those.
        return
    ev_types = {e.get("evidence_type") for e in (doc.get("evidence") or [])}
    step_tasks = {s.get("task") for s in (doc.get("steps") or [])}
    ok = bool(backing.get("evidence", set()) & ev_types) or bool(backing.get("step_task", set()) & step_tasks)
    assert ok, (f"{name}: claim {claim!r} has no backing evidence "
                f"(evidence={ev_types}, step_tasks={step_tasks}, need {backing})")


def test_no_demo_asserts_a_sar_semantic_conclusion():
    """The optical+SAR specialist returns an embedding. No demo may claim SAR
    'confirms', 'shows construction', etc. It must say representation-level only."""
    for name, claim, _ in _ALL_DEMO_CLAIMS:
        if "optical+sar" in claim.lower() or "sar:" in claim.lower():
            assert ("representation-level only" in claim.lower()
                    or "not performed" in claim.lower()
                    or "insufficient" in claim.lower()), f"{name}: {claim!r}"


# --------------------------------------------------------------------------- #
# constructed synthesis scenarios
# --------------------------------------------------------------------------- #

import sys  # noqa: E402

sys.path.insert(0, str(_REPO / "packages" / "agents" / "src"))
from satquery_agents.agent import AgentInvestigationResult, AgentMemory, AgentPlan  # noqa: E402
from satquery_agents.agent.schemas import PlanStep, StepObservation, TaskType  # noqa: E402


def _obs(sid, task, tool, status="completed", verdict="COHERENT", **findings):
    return StepObservation(step_id=sid, task=task, tool=tool, status=status, verdict=verdict,
                           summary="", findings=findings)


def _synth(specs, mem_results, mem_kw=None):
    """specs: list of (task, tool, status, verdict). mem_results: {tool: payload}."""
    from app.services.agent_runner import _synthesize

    steps = [_obs(f"s{i}", *sp) for i, sp in enumerate(specs, start=1)]
    res = AgentInvestigationResult(mission="m", inputs=["img0", "img1"])
    res.steps = steps
    res.mission_family = "multi_step"
    mem = AgentMemory(goal="m", image_ids=["img0", "img1"], image_paths={})
    mem.results = {f"s{i}": mem_results.get(sp[1], {}) for i, sp in enumerate(specs, start=1)}
    for k, v in (mem_kw or {}).items():
        setattr(mem, k, v)
    plan = AgentPlan(goal="m", inputs=["img0", "img1"], steps=[
        PlanStep(step_id=o.step_id, task=o.task, tool=o.tool, inputs={}, depends_on=[], reason="x")
        for o in steps])
    _synthesize(res, mem, plan)
    return res


def test_synthesis_change_claim_requires_changed_fraction():
    res = _synth([(TaskType.TEMPORAL_CHANGE, "run_temporal_change", "completed", "COHERENT")],
                 {"run_temporal_change": {"stats": {"changed_fraction": 0.25, "changed_area_ha": 0.41}}},
                 {"numeric": {"changed_fraction": 0.25}})
    assert any("25" in f and "changed" in f.lower() for f in res.key_findings), res.key_findings
    assert not _FORBIDDEN_RE.search(" ".join(res.key_findings))


def test_synthesis_no_change_states_no_change_not_a_number_claim():
    res = _synth([(TaskType.TEMPORAL_CHANGE, "run_temporal_change", "completed", "COHERENT")],
                 {"run_temporal_change": {"stats": {"changed_fraction": 0.002}}},
                 {"numeric": {"changed_fraction": 0.002}})
    joined = " ".join(res.key_findings).lower()
    assert "no significant change" in joined or "below the" in joined, res.key_findings


def test_synthesis_grounding_no_box_is_explicit_not_fabricated():
    res = _synth([(TaskType.GROUND_OBJECT, "run_grounding", "completed", "INSUFFICIENT")],
                 {"run_grounding": {"bbox_xyxy": None, "validation_status": "NO_REGION"}})
    joined = " ".join(res.key_findings).lower()
    assert "no matching region" in joined or "no region" in joined, res.key_findings
    assert not res.spatial_findings and (not res.geojson or not res.geojson.get("features"))


def test_synthesis_optical_sar_is_representation_only():
    res = _synth([(TaskType.OPTICAL_SAR_ANALYSIS, "run_optical_sar", "completed", "COHERENT")],
                 {"run_optical_sar": {"repr_dim": 768}})
    joined = " ".join(res.key_findings).lower()
    assert "representation-level only" in joined, res.key_findings
    assert "confirms" not in joined and "construction" not in joined


def test_synthesis_incoherent_step_withholds_its_claim():
    res = _synth([(TaskType.GROUND_OBJECT, "run_grounding", "completed", "INCOHERENT")],
                 {"run_grounding": {"bbox_xyxy": [1, 2, 3, 4], "validation_status": "PASS"}})
    joined = " ".join(res.key_findings).lower()
    assert "withheld" in joined or "disputed" in joined, res.key_findings
