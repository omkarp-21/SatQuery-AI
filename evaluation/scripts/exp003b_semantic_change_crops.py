"""G6 Phase 7 — COMPOSED_SEMANTIC_CHANGE_BASELINE crop-strategy comparison.

Runs the *same* baseline on the *same* changed regions with three T2 crop
strategies, feeding the *same* semantic worker (RemoteCLIP over the fixed change
vocabulary):

    A. tight       exact changed-region bbox
    B. expanded    bbox padded 75% each side (surrounding context)
    C. mask_aware  expanded crop, non-changed pixels dimmed to 0.35x

This is **not** a learned temporal VLM and produces **no** correctness metric on
the demo pair (no ground-truth semantic labels). It measures, per region:
  - which tag each strategy picks
  - the top-tag margin (rank-1 minus rank-2 similarity)
  - agreement across strategies

Run:  python evaluation/scripts/exp003b_semantic_change_crops.py
Writes evaluation/reports/exp003b_crops_<ts>.json
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "apps" / "backend"))

from app.services.semantic_change_baseline import run_composed_semantic_change  # noqa: E402

_CF = REPO / ("models/cache/changeformer/CD_ChangeFormerV6_LEVIR_b16_lr0.0001_adamw"
              "_train_test_200_linear_ce_multi_train_True_multi_infer_False_shuffle_AB_False_embed_dim_256")
_DEMO = REPO / "data/demo/temporal"
_STRATEGIES = ["tight", "expanded", "mask_aware"]


def _margin(ranking: list[list]) -> float | None:
    if len(ranking) < 2:
        return None
    return round(float(ranking[0][1]) - float(ranking[1][1]), 4)


def main() -> int:
    if not (_CF / "best_ckpt.pt").exists():
        print("ARTIFACT_MISSING: ChangeFormer checkpoint")
        return 1

    runs: dict[str, dict] = {}
    for strat in _STRATEGIES:
        t0 = time.time()
        r = run_composed_semantic_change(
            _DEMO / "t1.tif", _DEMO / "t2.tif", checkpoint_dir=_CF, crop_strategy=strat
        )
        runs[strat] = {
            "ok": r.ok,
            "runtime_s": round(time.time() - t0, 2),
            "changed_fraction": r.changed_fraction,
            "n_regions": len(r.regions),
            "failures": r.failures,
            "regions": [
                {"region_id": reg.region_id, "area_px": reg.area_px,
                 "top_tag": reg.top_tag, "margin": _margin(reg.tag_ranking),
                 "ranking": reg.tag_ranking}
                for reg in r.regions
            ],
            "description": r.description,
        }

    # cross-strategy agreement per region
    n_regions = min(runs[s]["n_regions"] for s in _STRATEGIES) if runs else 0
    per_region_agreement = []
    for i in range(n_regions):
        tags = {s: runs[s]["regions"][i]["top_tag"] for s in _STRATEGIES}
        per_region_agreement.append({
            "region_id": i + 1,
            "tags": tags,
            "all_agree": len(set(tags.values())) == 1,
            "tight_vs_expanded": tags["tight"] == tags["expanded"],
            "expanded_vs_mask_aware": tags["expanded"] == tags["mask_aware"],
        })
    n_agree = sum(1 for a in per_region_agreement if a["all_agree"])

    report = {
        "experiment": "G6 Phase 7 - semantic-change crop strategies (EXP-003b)",
        "date": time.strftime("%Y-%m-%d"),
        "pair": "data/demo/temporal/{t1,t2}.tif (LEVIR sample, EPSG:32650)",
        "note": "NO ground-truth semantic labels on this pair - this is a stability / "
                "behaviour comparison, NOT a correctness measurement. NOT a learned temporal VLM.",
        "strategies": _STRATEGIES,
        "runs": runs,
        "cross_strategy": {
            "regions_compared": n_regions,
            "regions_all_three_agree": n_agree,
            "agreement_rate": round(n_agree / n_regions, 4) if n_regions else None,
            "per_region": per_region_agreement,
        },
    }
    out = REPO / "evaluation" / "reports" / f"exp003b_crops_{time.strftime('%Y%m%dT%H%M%S')}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2))
    print(json.dumps(report["cross_strategy"], indent=2))
    for s in _STRATEGIES:
        print(f"\n[{s}] rt={runs[s]['runtime_s']}s regions={runs[s]['n_regions']} "
              f"failures={len(runs[s]['failures'])}")
        for reg in runs[s]["regions"]:
            print(f"  r{reg['region_id']} area={reg['area_px']}px "
                  f"tag={reg['top_tag']!r} margin={reg['margin']}")
    print(f"\nwrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
