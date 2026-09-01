"""EXP-005b — semantic verifier (model-independent) detection metrics.

`verify_semantic()` catches *internal* semantic incoherence: claim-vs-evidence
number/label mismatch, forward-time phrasing on a swapped pair, out-of-bounds or
whole-scene regions, region areas exceeding the total. It does **not** judge
real-world label correctness (needs an independent model).

Corpus buckets (28 cases):
    COHERENT       internally consistent                     -> expect COHERENT
    INCOHERENT     a model-independent check must fire        -> expect INCOHERENT
    BEYOND_SCOPE   wrong only in a way an independent model   -> expect COHERENT (a residual miss)
                   could catch (label absurd but present)
    NOT_ENOUGH     nothing semantic to check                 -> expect NOT_ENOUGH_EVIDENCE

Detection (positive class = "a model-independent semantic incoherence is present"):
    TP = INCOHERENT and status == INCOHERENT
    FN = INCOHERENT and status != INCOHERENT
    TN = (COHERENT or BEYOND_SCOPE) and status != INCOHERENT
    FP = (COHERENT or BEYOND_SCOPE) and status == INCOHERENT

Run:  python evaluation/scripts/exp005b_semantic_verifier.py
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

from satquery_evidence import EvidenceItem, verify_semantic  # noqa: E402

Bucket = Literal["COHERENT", "INCOHERENT", "BEYOND_SCOPE", "NOT_ENOUGH"]


@dataclass
class Case:
    case_id: str
    bucket: Bucket
    why: str
    result: dict[str, Any]
    evidence: list[EvidenceItem]
    context: dict[str, Any]


def _mask_ev(cf: float = 0.25, claim: str | None = None, **over: Any) -> EvidenceItem:
    return EvidenceItem(
        source_model="changeformer", task="change-detection", modality="optical-bitemporal",
        claim_supported=claim or f"~{cf:.0%} of pixels changed between T1 and T2",
        evidence_type="change-mask",
        payload={"mask_path": "/d/m.png", "changed_fraction": cf}, **over,
    )


def _region_ev(label: str, bbox_pixel=None, bbox_lonlat=None, **over: Any) -> EvidenceItem:
    sr: dict[str, Any] = {}
    if bbox_pixel:
        sr["bbox_pixel"] = list(bbox_pixel)
    if bbox_lonlat:
        sr["bbox_lonlat"] = list(bbox_lonlat)
    return EvidenceItem(
        source_model="remoteclip", task="zero-shot-classification", modality="optical-single",
        spatial_region=sr or None,
        claim_supported=f"changed region most resembles {label!r}",
        evidence_type="ranking", payload={"top_label": label, "ranking": [[label, 0.9]]}, **over,
    )


def corpus() -> list[Case]:
    C: list[Case] = []

    # ---- COHERENT (8) ----
    C.append(Case("coh-num-match", "COHERENT", "description % matches evidence changed_fraction",
                  {"description": "Detected change over ~25% of the scene."},
                  [_mask_ev(cf=0.25)], {}))
    C.append(Case("coh-label-match", "COHERENT", "quoted label appears as a top_label",
                  {"description": "Region 1 resembles 'new buildings'."},
                  [_mask_ev(0.2), _region_ev("new buildings")], {}))
    C.append(Case("coh-temporal-forward-ok", "COHERENT", "'new' phrasing on a T1<T2 pair",
                  {"description": "New buildings appeared."},
                  [_mask_ev(0.2, temporal_context={"t1": "2016", "t2": "2020"})], {}))
    C.append(Case("coh-region-in-bounds", "COHERENT", "bbox_pixel inside the image",
                  {"description": "change in the NE."},
                  [_region_ev("bare soil or clearing", bbox_pixel=(10, 20, 60, 90))],
                  {"image_shape": (256, 256)}))
    C.append(Case("coh-lonlat-valid", "COHERENT", "bbox_lonlat within valid ranges",
                  {}, [_region_ev("new water body", bbox_lonlat=(77.10, 28.40, 77.12, 28.42))], {}))
    C.append(Case("coh-region-area-sane", "COHERENT", "region is a small fraction of the scene",
                  {"regions": [{"region_id": 1, "area_px": 1600, "area_ha": 0.14}]},
                  [_mask_ev(0.05)], {"scene_pixels": 65536}))
    C.append(Case("coh-areas-within-total", "COHERENT", "region areas sum below the total",
                  {"changed_area_ha": 0.41,
                   "regions": [{"region_id": 1, "area_ha": 0.2}, {"region_id": 2, "area_ha": 0.15}]},
                  [_mask_ev(0.06)], {}))
    C.append(Case("coh-plain", "COHERENT", "consistent multi-piece result",
                  {"description": "Detected change over ~12% of the scene. Region 1 resembles 'new road or paved surface'."},
                  [_mask_ev(0.12), _region_ev("new road or paved surface", bbox_pixel=(5, 5, 40, 40))],
                  {"image_shape": (128, 128)}))

    # ---- INCOHERENT (10) : a model-independent check must fire ----
    C.append(Case("inc-num-mismatch", "INCOHERENT", "description says 60% but evidence is 25%",
                  {"description": "Detected change over ~60% of the scene."},
                  [_mask_ev(cf=0.25)], {}))
    C.append(Case("inc-label-absent", "INCOHERENT", "quoted label appears in NO evidence item",
                  {"description": "Region 1 resembles 'a stadium'."},
                  [_mask_ev(0.2), _region_ev("new vegetation")], {}))
    C.append(Case("inc-temporal-swapped", "INCOHERENT", "'newly constructed' on a T1>T2 pair",
                  {"description": "Buildings were newly constructed."},
                  [_mask_ev(0.3, temporal_context={"t1": "2021", "t2": "2016"})], {}))
    C.append(Case("inc-temporal-swapped-2", "INCOHERENT", "'expansion' on a swapped pair",
                  {"description": "Urban expansion is visible."},
                  [_mask_ev(0.22, temporal_context={"t1": "2020", "t2": "2018"})], {}))
    C.append(Case("inc-region-oob-rows", "INCOHERENT", "bbox_pixel rmax exceeds image height",
                  {}, [_region_ev("new buildings", bbox_pixel=(10, 20, 400, 90))],
                  {"image_shape": (256, 256)}))
    C.append(Case("inc-region-oob-neg", "INCOHERENT", "bbox_pixel has negative origin",
                  {}, [_region_ev("new buildings", bbox_pixel=(-5, 20, 60, 90))],
                  {"image_shape": (256, 256)}))
    C.append(Case("inc-lonlat-bad", "INCOHERENT", "latitude 128 is out of range",
                  {}, [_region_ev("new water body", bbox_lonlat=(77.1, 28.4, 77.2, 128.0))], {}))
    C.append(Case("inc-region-is-whole-scene", "INCOHERENT", "changed region covers ~99% of the scene",
                  {"regions": [{"region_id": 1, "area_px": 65000}]},
                  [_mask_ev(0.99)], {"scene_pixels": 65536}))
    C.append(Case("inc-areas-exceed-total", "INCOHERENT", "region areas sum to 0.9 ha but total is 0.41 ha",
                  {"changed_area_ha": 0.41,
                   "regions": [{"region_id": 1, "area_ha": 0.6}, {"region_id": 2, "area_ha": 0.3}]},
                  [_mask_ev(0.06)], {}))
    C.append(Case("inc-num-mismatch-pct-word", "INCOHERENT", "'80 percent' vs evidence 0.15",
                  {"description": "roughly 80 percent of the area changed."},
                  [_mask_ev(cf=0.15)], {}))

    # ---- BEYOND_SCOPE (6) : wrong, but only an independent model could tell ----
    C.append(Case("bs-absurd-label-present", "BEYOND_SCOPE",
                  "label 'a submarine' is absurd for the scene but IS the evidence top_label",
                  {"description": "Region 1 resembles 'a submarine'."},
                  [_mask_ev(0.2), _region_ev("a submarine")], {}))
    C.append(Case("bs-confident-wrong-class", "BEYOND_SCOPE",
                  "'dense urban' where it's actually forest - internally consistent",
                  {"description": "Scene resembles 'dense urban'."},
                  [_region_ev("dense urban")], {}))
    C.append(Case("bs-cloud-as-change", "BEYOND_SCOPE",
                  "mask flags a cloud; number + label all self-consistent",
                  {"description": "Detected change over ~18% of the scene."},
                  [_mask_ev(cf=0.18)], {}))
    C.append(Case("bs-missed-demolition", "BEYOND_SCOPE",
                  "cf 0.3% 'almost no change' but a building was demolished - self-consistent",
                  {"description": "Detected change over ~0% of the scene."},
                  [_mask_ev(cf=0.003)], {}))
    C.append(Case("bs-wrong-but-plausible-region", "BEYOND_SCOPE",
                  "tag 'new vegetation' actually bare soil - in bounds, label present",
                  {"description": "Region 1 resembles 'new vegetation'."},
                  [_region_ev("new vegetation", bbox_pixel=(3, 3, 30, 30))],
                  {"image_shape": (128, 128)}))
    C.append(Case("bs-right-number-wrong-story", "BEYOND_SCOPE",
                  "25% correct, but described as 'deforestation' when it's construction",
                  {"description": "Detected change over ~25% of the scene (deforestation)."},
                  [_mask_ev(cf=0.25)], {}))

    # ---- NOT_ENOUGH (4) ----
    C.append(Case("ne-empty", "NOT_ENOUGH", "no evidence, no result content", {}, [], {}))
    C.append(Case("ne-embedding-only", "NOT_ENOUGH", "embedding evidence, nothing semantic to check",
                  {}, [EvidenceItem(source_model="croma", task="representation", modality="optical-sar",
                                    claim_supported="joint embedding", evidence_type="embedding",
                                    payload={"dim": 768})], {}))
    C.append(Case("ne-no-numbers-no-labels", "NOT_ENOUGH", "claim with no checkable number/label/geometry",
                  {"description": "Some change was detected."},
                  [_mask_ev(0.2, claim="change was detected")], {}))
    C.append(Case("ne-metadata", "NOT_ENOUGH", "metadata evidence only",
                  {}, [EvidenceItem(source_model="x", task="metadata", modality="optical-single",
                                    claim_supported="crs", evidence_type="metadata",
                                    payload={"crs": "EPSG:32643"})], {}))
    return C


@dataclass
class Metrics:
    tp: int = 0
    fp: int = 0
    tn: int = 0
    fn: int = 0
    not_enough: int = 0
    per_case: list[dict[str, Any]] = field(default_factory=list)

    def _pr(self, a: int, b: int) -> float | None:
        return None if (a + b) == 0 else round(a / (a + b), 4)

    @property
    def precision(self) -> float | None:
        return self._pr(self.tp, self.fp)

    @property
    def recall(self) -> float | None:
        return self._pr(self.tp, self.fn)

    @property
    def f1(self) -> float | None:
        p, r = self.precision, self.recall
        return None if not p or not r else round(2 * p * r / (p + r), 4)


def run() -> Metrics:
    m = Metrics()
    for c in corpus():
        vr = verify_semantic(c.result, c.evidence, c.context)
        got = vr.status
        flagged = got == "INCOHERENT"
        if c.bucket == "NOT_ENOUGH":
            m.not_enough += 1
            outcome = "not_enough"
        elif c.bucket == "INCOHERENT" and flagged:
            m.tp += 1
            outcome = "TP"
        elif c.bucket == "INCOHERENT" and not flagged:
            m.fn += 1
            outcome = "FN"
        elif c.bucket in ("COHERENT", "BEYOND_SCOPE") and flagged:
            m.fp += 1
            outcome = "FP"
        else:
            m.tn += 1
            outcome = "TN"
        m.per_case.append({"case_id": c.case_id, "bucket": c.bucket, "why": c.why,
                           "got_status": got, "outcome": outcome,
                           "failed_checks": [ch.name for ch in vr.failed()],
                           "coverage_available": vr.coverage_available})
    return m


def main() -> int:
    m = run()
    bs = [r for r in m.per_case if r["bucket"] == "BEYOND_SCOPE"]
    bs_missed = sum(1 for r in bs if r["outcome"] == "TN")
    report = {
        "experiment": "EXP-005b model-independent semantic verifier",
        "date": time.strftime("%Y-%m-%d"),
        "corpus_size": len(m.per_case),
        "confusion_matrix": {"TP": m.tp, "FP": m.fp, "TN": m.tn, "FN": m.fn,
                             "not_enough": m.not_enough},
        "internal_incoherence_detection": {"precision": m.precision, "recall": m.recall, "f1": m.f1,
                                           "note": "positive class = a model-independent semantic "
                                                   "incoherence is present"},
        "residual_gap": {
            "beyond_scope_cases": len(bs),
            "missed": bs_missed,
            "miss_rate": round(bs_missed / len(bs), 4) if bs else None,
            "note": "these need an independent model / second modality - "
                    "verify_semantic() is not expected to catch them (EXP-C2, EXP-002).",
        },
        "coverage_unavailable": list(
            __import__("satquery_evidence").SemanticVerificationResult(
                status="COHERENT", checks=[], coverage_available=[]).coverage_unavailable
        ),
        "per_case": m.per_case,
    }
    out = REPO / "evaluation" / "reports" / f"exp005b_semverif_{time.strftime('%Y%m%dT%H%M%S')}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2))
    print(json.dumps(report["confusion_matrix"], indent=2))
    print(json.dumps(report["internal_incoherence_detection"], indent=2))
    print(json.dumps(report["residual_gap"], indent=2))
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
