"""EXP-005b — model-independent semantic verifier: unit + corpus lock."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from satquery_evidence import EvidenceItem, verify_semantic

_REPO = Path(__file__).resolve().parents[3]
_SPEC = importlib.util.spec_from_file_location(
    "exp005b", _REPO / "evaluation" / "scripts" / "exp005b_semantic_verifier.py"
)
assert _SPEC and _SPEC.loader
exp005b = importlib.util.module_from_spec(_SPEC)
sys.modules["exp005b"] = exp005b
_SPEC.loader.exec_module(exp005b)


def _mask_ev(cf=0.25, **o):
    return EvidenceItem(source_model="changeformer", task="change-detection",
                        modality="optical-bitemporal", claim_supported="pixels changed",
                        evidence_type="change-mask",
                        payload={"mask_path": "/m.png", "changed_fraction": cf}, **o)


def test_number_mismatch_is_incoherent():
    r = verify_semantic({"description": "Detected change over ~60% of the scene."},
                        [_mask_ev(cf=0.25)], {})
    assert r.status == "INCOHERENT"
    assert any("claim_matches_evidence_number" in c.name and not c.passed for c in r.checks)


def test_number_match_is_coherent():
    r = verify_semantic({"description": "Detected change over ~25% of the scene."},
                        [_mask_ev(cf=0.25)], {})
    assert r.status == "COHERENT"


def test_swapped_temporal_with_forward_phrasing_is_incoherent():
    ev = _mask_ev(cf=0.3, temporal_context={"t1": "2021", "t2": "2016"})
    r = verify_semantic({"description": "Buildings were newly constructed."}, [ev], {})
    assert r.status == "INCOHERENT"


def test_out_of_bounds_region_is_incoherent():
    ev = EvidenceItem(source_model="remoteclip", task="zero-shot-classification",
                      modality="optical-single", spatial_region={"bbox_pixel": [10, 20, 400, 90]},
                      claim_supported="c", evidence_type="ranking",
                      payload={"top_label": "x", "ranking": [["x", 0.9]]})
    r = verify_semantic({}, [ev], {"image_shape": (256, 256)})
    assert r.status == "INCOHERENT"


def test_nothing_to_check_is_not_enough():
    r = verify_semantic({}, [], {})
    assert r.status == "NOT_ENOUGH_EVIDENCE"


def test_coverage_declares_the_unavailable_checks():
    r = verify_semantic({"description": "Detected change over ~25% of the scene."},
                        [_mask_ev(cf=0.25)], {})
    assert set(r.coverage_unavailable) == {
        "independent_model_agreement", "optical_sar_agreement", "grounding_roundtrip"
    }


def test_notes_do_not_overclaim():
    r = verify_semantic({"description": "Detected change over ~25% of the scene."},
                        [_mask_ev(cf=0.25)], {})
    assert "does NOT judge real-world label correctness" in r.notes


# ---- corpus lock (freezes the numbers in docs/research/EXP-005.md) ----
def test_exp005b_corpus_metrics_are_exact():
    m = exp005b.run()
    assert (m.tp, m.fp, m.tn, m.fn) == (10, 0, 14, 0)
    assert m.precision == 1.0 and m.recall == 1.0 and m.f1 == 1.0
    assert m.not_enough == 4


def test_exp005b_residual_gap_is_total():
    m = exp005b.run()
    bs = [r for r in m.per_case if r["bucket"] == "BEYOND_SCOPE"]
    assert len(bs) == 6
    assert all(r["outcome"] == "TN" for r in bs)  # not flagged - needs an independent model
