"""EXP-005 — structural verifier detection metrics.

Measures what `satquery_evidence.verify()` actually detects. The verifier is
**structural / deterministic only** (`packages/evidence/src/satquery_evidence/verifier.py`)
- this experiment quantifies (a) how well it catches *structural* defects and
(b) how many *semantic* defects it necessarily misses (the gap that motivates a
future semantic verifier).

Corpus buckets (hand-curated, 24 cases):
    CLEAN            no structural defect, semantically correct   -> expect SUPPORTED
    STRUCTURAL       a structural defect is present               -> expect CONTRADICTED
    SEMANTIC         structurally clean but semantically wrong    -> verifier SUPPORTED (a miss)
    INSUFFICIENT     nothing to check                             -> expect INSUFFICIENT_EVIDENCE

Detection scoring (positive class = "structural defect present"):
    TP = STRUCTURAL and status == CONTRADICTED
    FN = STRUCTURAL and status != CONTRADICTED
    TN = (CLEAN or SEMANTIC) and status != CONTRADICTED
    FP = (CLEAN or SEMANTIC) and status == CONTRADICTED
    (INSUFFICIENT cases are reported separately, not in the confusion matrix.)

Run:  python evaluation/scripts/exp005_verifier_detection.py
Exit 0 always; writes evaluation/reports/exp005_verifier_<ts>.json
"""

from __future__ import annotations

import json
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "packages" / "evidence" / "src"))

from satquery_evidence import EvidenceItem, verify  # noqa: E402

Bucket = Literal["CLEAN", "STRUCTURAL", "SEMANTIC", "INSUFFICIENT"]


@dataclass
class Case:
    case_id: str
    bucket: Bucket
    why: str
    result: dict[str, Any]
    evidence: list[EvidenceItem]
    context: dict[str, Any]
    expected_status: str


def _mask_ev(mask_path: str = "/data/mask.png", cf: float = 0.25, **over: Any) -> EvidenceItem:
    payload = {"mask_path": mask_path, "changed_fraction": cf}
    payload.update(over.pop("payload", {}))
    return EvidenceItem(
        source_model="changeformer", task="change-detection", modality="optical-bitemporal",
        claim_supported="pixels changed between T1 and T2", evidence_type="change-mask",
        payload=payload, **over,
    )


def _rank_ev(ranking: list[list[Any]], **over: Any) -> EvidenceItem:
    return EvidenceItem(
        source_model="remoteclip", task="zero-shot-classification", modality="optical-single",
        claim_supported="scene label", evidence_type="ranking", payload={"ranking": ranking}, **over,
    )


def _emb_ev(dim: int, **over: Any) -> EvidenceItem:
    return EvidenceItem(
        source_model="croma", task="representation", modality="optical-sar",
        claim_supported="joint embedding", evidence_type="embedding", payload={"dim": dim}, **over,
    )


def corpus() -> list[Case]:
    C: list[Case] = []

    # ---- CLEAN (6) : structurally fine + semantically plausible ----
    C.append(Case("clean-change-ok", "CLEAN", "co-registered pair, cf in range, mask present",
                  {"changed_fraction": 0.25}, [_mask_ev(cf=0.25)],
                  {"pair_co_registered": True, "input_paths": ["t1.tif", "t2.tif"]}, "SUPPORTED"))
    C.append(Case("clean-change-small", "CLEAN", "tiny but valid change fraction",
                  {}, [_mask_ev(cf=0.004)], {"pair_co_registered": True}, "SUPPORTED"))
    C.append(Case("clean-scene-ok", "CLEAN", "ranking probs in [0,1], modality matches",
                  {}, [_rank_ev([["an airport", 0.91], ["a harbour", 0.06], ["a farm", 0.03]])],
                  {"requested_modality": "optical-single", "model_modalities": ["optical-single"]},
                  "SUPPORTED"))
    C.append(Case("clean-embed-ok", "CLEAN", "embedding dim > 0",
                  {}, [_emb_ev(768)], {"requested_modality": "optical-sar",
                                       "model_modalities": ["optical-sar"]}, "SUPPORTED"))
    C.append(Case("clean-change-inputs-exist", "CLEAN", "declared inputs all exist",
                  {}, [_mask_ev()], {"pair_co_registered": True, "input_paths": ["a.tif", "b.tif"],
                                     "inputs_exist": {"a.tif": True, "b.tif": True}}, "SUPPORTED"))
    C.append(Case("clean-scene-twoclass", "CLEAN", "binary ranking, valid",
                  {}, [_rank_ev([["water", 0.55], ["land", 0.45]])], {}, "SUPPORTED"))

    # ---- STRUCTURAL (8) : a deterministic check must fail ----
    C.append(Case("struct-cf-over-1", "STRUCTURAL", "changed_fraction = 1.9 (out of range)",
                  {}, [_mask_ev(cf=1.9)], {"pair_co_registered": True}, "CONTRADICTED"))
    C.append(Case("struct-cf-negative", "STRUCTURAL", "changed_fraction = -0.2",
                  {}, [_mask_ev(cf=-0.2)], {"pair_co_registered": True}, "CONTRADICTED"))
    C.append(Case("struct-no-mask", "STRUCTURAL", "mask_path missing from payload",
                  {}, [_mask_ev(payload={"mask_path": None})], {"pair_co_registered": True},
                  "CONTRADICTED"))
    C.append(Case("struct-not-coreg", "STRUCTURAL", "pair not co-registered",
                  {}, [_mask_ev()], {"pair_co_registered": False}, "CONTRADICTED"))
    C.append(Case("struct-modality-mismatch", "STRUCTURAL", "SAR asked of an optical-only model",
                  {}, [_rank_ev([["a", 0.9], ["b", 0.1]])],
                  {"requested_modality": "sar-single", "model_modalities": ["optical-single"]},
                  "CONTRADICTED"))
    C.append(Case("struct-ranking-prob-gt1", "STRUCTURAL", "ranking prob = 1.4",
                  {}, [_rank_ev([["a", 1.4], ["b", -0.4]])], {}, "CONTRADICTED"))
    C.append(Case("struct-embed-zerodim", "STRUCTURAL", "embedding dim = 0",
                  {}, [_emb_ev(0)], {}, "CONTRADICTED"))
    C.append(Case("struct-input-missing", "STRUCTURAL", "declared input does not exist",
                  {}, [_mask_ev()], {"pair_co_registered": True, "input_paths": ["a.tif", "b.tif"],
                                     "inputs_exist": {"a.tif": True, "b.tif": False}},
                  "CONTRADICTED"))

    # ---- SEMANTIC (6) : structurally clean, semantically wrong -> verifier CANNOT catch ----
    C.append(Case("sem-wrong-region", "SEMANTIC",
                  "cf valid (0.25) but the mask flags a cloud, not real change",
                  {}, [_mask_ev(cf=0.25)], {"pair_co_registered": True}, "SUPPORTED"))
    C.append(Case("sem-absurd-label", "SEMANTIC",
                  "ranking well-formed but top label 'a submarine' for a desert scene",
                  {}, [_rank_ev([["a submarine", 0.88], ["a desert", 0.12]])], {}, "SUPPORTED"))
    C.append(Case("sem-confident-wrong", "SEMANTIC",
                  "probs in range, but the class is wrong with high score",
                  {}, [_rank_ev([["dense urban", 0.97], ["forest", 0.03]])], {}, "SUPPORTED"))
    C.append(Case("sem-embed-wrong-sensor", "SEMANTIC",
                  "dim 768 ok, but the vector was computed from the wrong tile",
                  {}, [_emb_ev(768)], {"requested_modality": "optical-sar",
                                       "model_modalities": ["optical-sar"]}, "SUPPORTED"))
    C.append(Case("sem-change-missed", "SEMANTIC",
                  "cf = 0.002: model says 'almost no change' but a building was demolished",
                  {}, [_mask_ev(cf=0.002)], {"pair_co_registered": True}, "SUPPORTED"))
    C.append(Case("sem-swapped-temporal", "SEMANTIC",
                  "mask fine, but T1/T2 were swapped so 'built' reads as 'demolished'",
                  {}, [_mask_ev(cf=0.31, temporal_context={"t1": "2020", "t2": "2016"})],
                  {"pair_co_registered": True}, "SUPPORTED"))

    # ---- INSUFFICIENT (4) : nothing to check ----
    C.append(Case("insuf-empty", "INSUFFICIENT", "no evidence, no context",
                  {}, [], {}, "INSUFFICIENT_EVIDENCE"))
    C.append(Case("insuf-ctx-only-unknown", "INSUFFICIENT", "context has no checkable keys",
                  {}, [], {"note": "n/a"}, "INSUFFICIENT_EVIDENCE"))
    C.append(Case("insuf-metadata-ev", "INSUFFICIENT", "evidence type the verifier has no rule for",
                  {}, [EvidenceItem(source_model="x", task="metadata", modality="optical-single",
                                    claim_supported="crs", evidence_type="metadata",
                                    payload={"crs": "EPSG:32643"})], {}, "INSUFFICIENT_EVIDENCE"))
    C.append(Case("insuf-citation-ev", "INSUFFICIENT", "citation evidence, no structural rule",
                  {}, [EvidenceItem(source_model="x", task="report", modality="n/a",
                                    claim_supported="ref", evidence_type="citation",
                                    payload={"doi": "10.0/x"})], {}, "INSUFFICIENT_EVIDENCE"))
    return C


@dataclass
class Metrics:
    tp: int = 0
    fp: int = 0
    tn: int = 0
    fn: int = 0
    insufficient: int = 0
    per_case: list[dict[str, Any]] = field(default_factory=list)

    @property
    def precision(self) -> float | None:
        d = self.tp + self.fp
        return None if d == 0 else round(self.tp / d, 4)

    @property
    def recall(self) -> float | None:
        d = self.tp + self.fn
        return None if d == 0 else round(self.tp / d, 4)

    @property
    def f1(self) -> float | None:
        p, r = self.precision, self.recall
        if not p or not r or (p + r) == 0:
            return None
        return round(2 * p * r / (p + r), 4)


def run() -> Metrics:
    m = Metrics()
    for c in corpus():
        vr = verify(c.result, c.evidence, c.context)
        got = vr.status
        is_defect = c.bucket == "STRUCTURAL"
        flagged = got == "CONTRADICTED"
        if c.bucket == "INSUFFICIENT":
            m.insufficient += 1
            outcome = "insufficient"
        elif is_defect and flagged:
            m.tp += 1
            outcome = "TP"
        elif is_defect and not flagged:
            m.fn += 1
            outcome = "FN"
        elif not is_defect and flagged:
            m.fp += 1
            outcome = "FP"
        else:
            m.tn += 1
            outcome = "TN"
        m.per_case.append(
            {"case_id": c.case_id, "bucket": c.bucket, "why": c.why,
             "expected_status": c.expected_status, "got_status": got,
             "outcome": outcome, "failed_checks": [ch.name for ch in vr.failed()]}
        )
    return m


def main() -> int:
    m = run()
    sem_cases = [r for r in m.per_case if r["bucket"] == "SEMANTIC"]
    sem_missed = sum(1 for r in sem_cases if r["outcome"] == "TN")  # not flagged
    report = {
        "experiment": "EXP-005 structural verifier detection",
        "date": time.strftime("%Y-%m-%d"),
        "corpus_size": len(m.per_case),
        "confusion_matrix": {"TP": m.tp, "FP": m.fp, "TN": m.tn, "FN": m.fn,
                             "insufficient": m.insufficient},
        "structural_defect_detection": {
            "precision": m.precision, "recall": m.recall, "f1": m.f1,
            "note": "positive class = a structural defect is present",
        },
        "semantic_defect_gap": {
            "semantic_cases": len(sem_cases),
            "missed_by_structural_verifier": sem_missed,
            "miss_rate": round(sem_missed / len(sem_cases), 4) if sem_cases else None,
            "note": "expected miss_rate ~1.0 - the structural verifier is not designed "
                    "to catch semantic errors; this number sizes the gap EXP-005 flags "
                    "for a future semantic verifier.",
        },
        "per_case": m.per_case,
    }
    out = REPO / "evaluation" / "reports" / f"exp005_verifier_{time.strftime('%Y%m%dT%H%M%S')}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2))
    print(json.dumps(report["confusion_matrix"], indent=2))
    print(json.dumps(report["structural_defect_detection"], indent=2))
    print(json.dumps(report["semantic_defect_gap"], indent=2))
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
