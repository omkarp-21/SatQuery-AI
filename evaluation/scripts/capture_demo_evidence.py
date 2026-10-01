"""G7 Phase 14 — capture reproducible REAL demo outputs.

Writes trimmed, real result JSON to docs/sih/evidence/demos/ for the demos that
can run without the blocked A/B models:

    DEMO 2  "what changed?"            -> run_change_slice (ChangeFormer)
    DEMO 4  misregistered pair rejected -> run_change_slice on t1 vs t2_shifted
    DEMO 5  evidence + verification     -> composed semantic-change baseline
                                          (structural verify + verify_semantic)

DEMO 1 (single-image VQA) and DEMO 3 (optical+SAR question) are BLOCKED - a
placeholder note is written instead of a fake output.

Run:  python evaluation/scripts/capture_demo_evidence.py
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "apps" / "backend"))

OUT = REPO / "docs" / "sih" / "evidence" / "demos"
OUT.mkdir(parents=True, exist_ok=True)

_CF = REPO / ("models/cache/changeformer/CD_ChangeFormerV6_LEVIR_b16_lr0.0001_adamw"
              "_train_test_200_linear_ce_multi_train_True_multi_infer_False_shuffle_AB_False_embed_dim_256")
_DEMO = REPO / "data" / "demo" / "temporal"


def _dump(name: str, obj: dict) -> None:
    obj["_captured"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    obj["_note"] = "REAL output of the committed pipeline on the bundled demo pair. Not edited."
    (OUT / name).write_text(json.dumps(obj, indent=2, default=str))
    print(f"wrote {OUT / name}")


def main() -> int:
    if not (_CF / "best_ckpt.pt").exists():
        print("ARTIFACT_MISSING: ChangeFormer checkpoint - cannot capture demos")
        return 1

    from app.services.semantic_change_baseline import run_composed_semantic_change
    from app.services.temporal_slice import run_change_slice

    # DEMO 2 — what changed?
    r2 = run_change_slice(_DEMO / "t1.tif", _DEMO / "t2.tif", checkpoint_dir=_CF, strict=True)
    _dump("demo2_what_changed.json", {
        "demo": "DEMO 2 - 'what changed?' (POST /change logic)",
        "query": "what changed between these two images?",
        "inputs": ["data/demo/temporal/t1.tif", "data/demo/temporal/t2.tif"],
        "ok": r2.ok,
        "pair_co_registered": (r2.pair.co_registered if r2.pair else None),
        "stats": (r2.stats.model_dump() if r2.stats else None),
        "mask_path": r2.mask_path,
        "evidence": [e.model_dump() for e in r2.evidence],
        "verification": (r2.verification.model_dump() if r2.verification else None),
        "provenance_keys": list(r2.provenance.keys()),
        "standardized_provenance": r2.provenance.get("standardized"),
    })

    # DEMO 4 — misregistered pair rejected
    r4 = run_change_slice(_DEMO / "t1.tif", _DEMO / "t2_shifted.tif", checkpoint_dir=_CF, strict=True)
    _dump("demo4_misregistered_rejected.json", {
        "demo": "DEMO 4 - misregistered pair rejected before any model runs",
        "inputs": ["data/demo/temporal/t1.tif", "data/demo/temporal/t2_shifted.tif"],
        "ok": r4.ok,
        "errors": r4.errors,
        "pair": (r4.pair.model_dump() if r4.pair else None),
        "stats_is_null": r4.stats is None,
        "note": "strict=True: the co-registration gate fails -> ok:false, stats:null, "
                "NO inference is run. This is the geospatial safeguard (EXP-007) live.",
    })

    # DEMO 5 — evidence + structural + semantic verification
    r5 = run_composed_semantic_change(_DEMO / "t1.tif", _DEMO / "t2.tif",
                                      checkpoint_dir=_CF, max_regions=4)
    _dump("demo5_evidence_and_verification.json", {
        "demo": "DEMO 5 - evidence + structural + semantic verification "
                "(COMPOSED_SEMANTIC_CHANGE_BASELINE)",
        "disclaimer": r5.disclaimer,
        "ok": r5.ok,
        "description": r5.description,
        "n_regions": len(r5.regions),
        "regions": [reg.model_dump() for reg in r5.regions],
        "evidence_types": [e.evidence_type for e in r5.evidence],
        "verification": (r5.verification.model_dump() if r5.verification else None),
        "semantic_verification": (r5.semantic_verification.model_dump()
                                  if r5.semantic_verification else None),
        "failures": r5.failures,
        "provenance_stages": r5.provenance.get("stages"),
        "note": "verify() = structural (SUPPORTED/CONTRADICTED). verify_semantic() = "
                "model-independent semantic coherence (COHERENT/INCOHERENT). Neither is "
                "a confidence value. Region tags are RemoteCLIP similarity to fixed "
                "phrases, not calibrated labels.",
    })

    # DEMO 1 / DEMO 3 — blocked, no fake output
    _dump("demo1_single_image_vqa_BLOCKED.json", {
        "demo": "DEMO 1 - single-image question (VQA)",
        "status": "BLOCKED",
        "reason": "no VQA specialist reproduced - EXP-002 artifact acquisition failed "
                  "6x from this host. Harness evaluation/scripts/exp002_ab_gate.py + "
                  "frozen RSVQA-LR sample are ready; runs on the remote GPU box.",
        "no_fake_output": True,
    })
    _dump("demo3_optical_sar_question_BLOCKED.json", {
        "demo": "DEMO 3 - optical + SAR question",
        "status": "BLOCKED",
        "reason": "joint optical-SAR is representation-level only (CROMA/DOFA reproduced, "
                  "no task head). EXP-004 Run 2 (real DFC2020) needed for a task-level "
                  "answer; dataset acquisition needs the remote box.",
        "no_fake_output": True,
    })
    return 0


if __name__ == "__main__":
    sys.exit(main())
