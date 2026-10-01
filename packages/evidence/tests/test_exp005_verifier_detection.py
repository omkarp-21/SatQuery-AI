"""EXP-005 — lock the structural verifier's detection behaviour on the curated corpus.

These assertions freeze the numbers reported in `docs/research/EXP-005.md`. If the
verifier changes, this test (and that doc) must be updated together.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[3]
_SPEC = importlib.util.spec_from_file_location(
    "exp005", _REPO / "evaluation" / "scripts" / "exp005_verifier_detection.py"
)
assert _SPEC and _SPEC.loader
exp005 = importlib.util.module_from_spec(_SPEC)
sys.modules["exp005"] = exp005  # so @dataclass can resolve cls.__module__
_SPEC.loader.exec_module(exp005)


def test_structural_detection_is_exact_on_corpus():
    m = exp005.run()
    # every structural defect is caught, nothing clean is mis-flagged
    assert (m.tp, m.fp, m.tn, m.fn) == (8, 0, 12, 0)
    assert m.precision == 1.0
    assert m.recall == 1.0
    assert m.f1 == 1.0
    assert m.insufficient == 4


def test_structural_verifier_misses_all_semantic_defects():
    m = exp005.run()
    sem = [r for r in m.per_case if r["bucket"] == "SEMANTIC"]
    assert len(sem) == 6
    # the documented gap: structural verification does NOT catch semantic errors
    assert all(r["outcome"] == "TN" for r in sem)


def test_corpus_buckets_are_balanced_enough():
    counts: dict[str, int] = {}
    for c in exp005.corpus():
        counts[c.bucket] = counts.get(c.bucket, 0) + 1
    assert counts == {"CLEAN": 6, "STRUCTURAL": 8, "SEMANTIC": 6, "INSUFFICIENT": 4}
