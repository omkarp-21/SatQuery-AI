"""EXP-004 Run 2 — stage 3: frozen-feature linear probe + significance.

Answers "does adding SAR improve the downstream task?" — not "do the embeddings
contain SAR info?". A linear probe on FROZEN encoder features, evaluated on a
held-out DFC2020 split, with bootstrap CIs and a paired McNemar test.

Runs in `.venvs/croma` (needs scikit-learn + scipy). No network.

Arms (same patches, same split, same labels):
  A  optical-only   : CROMA optical_GAP   |  DOFA s2_feat        (each encoder's own optical path)
  B  CROMA joint     : CROMA joint_GAP     (SAR + optical, native cross-encoder)
  C  DOFA fused      : DOFA s2_feat (+) s1_feat  (concat fusion)

out: evaluation/reports/exp004_run2_<ts>.json  + a markdown sibling.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np
from scipy.stats import binomtest
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score
from sklearn.preprocessing import StandardScaler

REPO_ROOT = Path(__file__).resolve().parents[2]
DFC_CLASSES = {
    1: "Forest", 2: "Shrubland", 3: "Savanna", 4: "Grassland", 5: "Wetlands",
    6: "Croplands", 7: "Urban/Built-up", 8: "Snow/Ice", 9: "Barren", 10: "Water",
}
SEED = 20260902


def _probe(xtr, ytr, xev, yev):
    sc = StandardScaler().fit(xtr)
    clf = LogisticRegression(max_iter=5000, C=1.0, class_weight="balanced")
    clf.fit(sc.transform(xtr), ytr)
    pred = clf.predict(sc.transform(xev))
    return pred


def _metrics(y, pred):
    return {
        "macro_f1": round(float(f1_score(y, pred, average="macro")), 4),
        "accuracy": round(float(accuracy_score(y, pred)), 4),
        "per_class_f1": {
            DFC_CLASSES[int(c)]: round(float(f1_score(y == c, pred == c)), 3)
            for c in sorted(set(y.tolist()))
        },
    }


def _bootstrap_macro_f1(y, preds: dict[str, np.ndarray], n_boot: int) -> dict:
    rng = np.random.default_rng(SEED)
    idx_all = np.arange(len(y))
    samples: dict[str, list[float]] = {k: [] for k in preds}
    deltas: dict[str, list[float]] = {"B_minus_Acroma": [], "C_minus_Adofa": [], "B_minus_C": []}
    for _ in range(n_boot):
        bi = rng.choice(idx_all, size=len(idx_all), replace=True)
        yb = y[bi]
        mf = {k: f1_score(yb, p[bi], average="macro") for k, p in preds.items()}
        for k, v in mf.items():
            samples[k].append(v)
        deltas["B_minus_Acroma"].append(mf["B_croma_joint"] - mf["A_croma_optical"])
        deltas["C_minus_Adofa"].append(mf["C_dofa_fused"] - mf["A_dofa_s2"])
        deltas["B_minus_C"].append(mf["B_croma_joint"] - mf["C_dofa_fused"])

    def ci(v):
        a = np.array(v)
        return [round(float(np.percentile(a, 2.5)), 4), round(float(np.percentile(a, 97.5)), 4)]

    return {
        "macro_f1_ci95": {k: ci(v) for k, v in samples.items()},
        "delta_ci95": {k: ci(v) for k, v in deltas.items()},
        "delta_mean": {k: round(float(np.mean(v)), 4) for k, v in deltas.items()},
        "delta_p_gt_0": {k: round(float(np.mean(np.array(v) > 0)), 4) for k, v in deltas.items()},
    }


def _mcnemar(y, pred_a, pred_b) -> dict:
    """Paired: exact McNemar on discordant pairs (correct/incorrect)."""
    a_ok, b_ok = (pred_a == y), (pred_b == y)
    n01 = int(np.sum(~a_ok & b_ok))  # A wrong, B right
    n10 = int(np.sum(a_ok & ~b_ok))  # A right, B wrong
    n = n01 + n10
    p = binomtest(min(n01, n10), n, 0.5).pvalue if n > 0 else 1.0
    return {"b_fixes_a": n01, "b_breaks_a": n10, "discordant": n, "p_value": round(float(p), 4)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--croma-train", required=True)
    ap.add_argument("--croma-eval", required=True)
    ap.add_argument("--dofa-train", required=True)
    ap.add_argument("--dofa-eval", required=True)
    ap.add_argument("--meta-json", nargs="*", default=[], help="feature .meta.json files for runtime/memory")
    ap.add_argument("--n-boot", type=int, default=2000)
    ap.add_argument("--tag", default="", help="output filename tag, e.g. g18_larger (keeps G12 files untouched)")
    ap.add_argument("--split-file", default="evaluation/datasets/dfc2020_exp004_split.json")
    ap.add_argument("--note", default="")
    a = ap.parse_args()

    ct, ce = np.load(a.croma_train), np.load(a.croma_eval)
    dt, de = np.load(a.dofa_train), np.load(a.dofa_eval)
    ytr, yev = ct["y"], ce["y"]
    assert np.array_equal(ytr, dt["y"]) and np.array_equal(yev, de["y"]), "arm label mismatch"

    feats = {
        "A_croma_optical": (ct["optical_gap"], ce["optical_gap"]),
        "B_croma_joint": (ct["joint_gap"], ce["joint_gap"]),
        "A_dofa_s2": (dt["s2_feat"], de["s2_feat"]),
        "C_dofa_fused": (
            np.concatenate([dt["s2_feat"], dt["s1_feat"]], axis=1),
            np.concatenate([de["s2_feat"], de["s1_feat"]], axis=1),
        ),
    }
    nan_report = {
        k: int(np.sum(~np.isfinite(xev))) for k, (_, xev) in feats.items()
    }

    t0 = time.time()
    preds = {k: _probe(xt, ytr, xe, yev) for k, (xt, xe) in feats.items()}
    results = {k: _metrics(yev, preds[k]) for k in feats}
    boot = _bootstrap_macro_f1(yev, preds, a.n_boot)
    mcnemar = {
        "B_vs_A_croma": _mcnemar(yev, preds["A_croma_optical"], preds["B_croma_joint"]),
        "C_vs_A_dofa": _mcnemar(yev, preds["A_dofa_s2"], preds["C_dofa_fused"]),
    }

    metas = {}
    for m in a.meta_json:
        try:
            d = json.loads(Path(m).read_text())
            metas[d.get("encoder", Path(m).stem)] = d
        except Exception as e:  # noqa: BLE001
            metas[m] = {"error": str(e)}

    croma_mf = results["B_croma_joint"]["macro_f1"]
    dofa_mf = results["C_dofa_fused"]["macro_f1"]
    # Predeclared rule: PRIMARY = downstream macro-F1. Only fall through to the
    # lighter-deployment tie-breaker on a genuine practical tie (|delta| < 0.02).
    # A wide bootstrap CI at n=200 is low power, NOT equivalence -> not a tie.
    tie = abs(croma_mf - dofa_mf) < 0.02
    if tie:
        winner = "DOFA (practical tie on macro-F1 -> tertiary rule: lighter/simpler/faster)"
    else:
        best = "CROMA" if croma_mf > dofa_mf else "DOFA"
        winner = (
            f"{best} (primary criterion: macro-F1 {max(croma_mf, dofa_mf):.4f} vs "
            f"{min(croma_mf, dofa_mf):.4f}; CROMA is also the only arm where SAR helped)"
        )

    sar_helps_croma = boot["delta_ci95"]["B_minus_Acroma"][0] > 0
    sar_helps_dofa = boot["delta_ci95"]["C_minus_Adofa"][0] > 0

    payload = {
        "experiment": "EXP-004 Run 2 — DFC2020 optical vs optical+SAR downstream probe",
        "date": time.strftime("%Y-%m-%dT%H%M%S"),
        "dataset": "DFC2020 ROIs0000_validation (non-gated mirror 125oii/dfc2020)",
        "split_file": a.split_file,
        "n_train": int(ytr.size),
        "n_eval": int(yev.size),
        "task": "single-label patch classification: dominant DFC land-cover class",
        "classes_present": [DFC_CLASSES[int(c)] for c in sorted(set(yev.tolist()))],
        "probe": "StandardScaler + LogisticRegression(C=1.0, class_weight=balanced, max_iter=5000) on FROZEN features",
        "metric": "macro-F1 (primary), accuracy",
        "arms": results,
        "nonfinite_feature_values": nan_report,
        "bootstrap": boot,
        "mcnemar_paired": mcnemar,
        "probe_fit_predict_runtime_s": round(time.time() - t0, 2),
        "encoder_feature_extraction": metas,
        "sar_improves_task": {
            "croma_joint_vs_croma_optical": {
                "abs_delta_macro_f1": round(croma_mf - results["A_croma_optical"]["macro_f1"], 4),
                "ci95": boot["delta_ci95"]["B_minus_Acroma"],
                "significant_ci": bool(sar_helps_croma),
                "mcnemar_p": mcnemar["B_vs_A_croma"]["p_value"],
            },
            "dofa_fused_vs_dofa_optical": {
                "abs_delta_macro_f1": round(dofa_mf - results["A_dofa_s2"]["macro_f1"], 4),
                "ci95": boot["delta_ci95"]["C_minus_Adofa"],
                "significant_ci": bool(sar_helps_dofa),
                "mcnemar_p": mcnemar["C_vs_A_dofa"]["p_value"],
            },
        },
        "croma_vs_dofa_decision": {
            "rule": "1 downstream macro-F1  2 failure rate  3 resource  4 latency  (tie -> lighter)",
            "croma_joint_macro_f1": croma_mf,
            "dofa_fused_macro_f1": dofa_mf,
            "b_minus_c_ci95": boot["delta_ci95"]["B_minus_C"],
            "practically_tied": bool(tie),
            "winner": winner,
        },
        "note": a.note or ("Real integrated measurement (frozen encoder -> probe -> metric), "
                           f"NOT a full DFC2020 benchmark. Seed {SEED}. CPU. No confidence value produced."),
    }

    ts = time.strftime("%Y%m%dT%H%M%S")
    stem = f"exp004_run2_{a.tag}_{ts}" if a.tag else f"exp004_run2_{ts}"
    out = REPO_ROOT / "evaluation" / "reports" / f"{stem}.json"
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    _write_md(payload, out.with_suffix(".md"))
    print(json.dumps(payload["arms"], indent=2))
    print("\nSAR improves task:", json.dumps(payload["sar_improves_task"], indent=2))
    print("\ndecision:", json.dumps(payload["croma_vs_dofa_decision"], indent=2))
    print("\nwrote", out)
    return 0


def _write_md(p: dict, path: Path) -> None:
    a = p["arms"]
    s = p["sar_improves_task"]
    d = p["croma_vs_dofa_decision"]
    lines = [
        f"# EXP-004 Run 2 — {p['date']}",
        "",
        f"**Dataset:** {p['dataset']} — {p['n_train']} train / {p['n_eval']} eval patches "
        f"(`{p['split_file']}`).  ",
        f"**Task:** {p['task']} — classes: {', '.join(p['classes_present'])}.  ",
        f"**Probe:** {p['probe']}.  ",
        f"**Metric:** {p['metric']}.  CPU. Seed {SEED}. **Sanity-scale, not a full benchmark.**",
        "",
        "## Arms",
        "",
        "| arm | features | dim | macro-F1 | accuracy |",
        "|-----|----------|:---:|:--------:|:--------:|",
    ]
    dims = {
        "A_croma_optical": "768 (S2 only)", "B_croma_joint": "768 (S1+S2)",
        "A_dofa_s2": "768 (S2 only)", "C_dofa_fused": "1536 (S2+S1)",
    }
    label = {
        "A_croma_optical": "A · CROMA optical-only", "B_croma_joint": "B · CROMA joint (SAR+opt)",
        "A_dofa_s2": "A' · DOFA optical-only", "C_dofa_fused": "C · DOFA fused (SAR+opt)",
    }
    for k in ["A_croma_optical", "B_croma_joint", "A_dofa_s2", "C_dofa_fused"]:
        lines.append(f"| {label[k]} | {k} | {dims[k]} | **{a[k]['macro_f1']}** | {a[k]['accuracy']} |")
    lines += [
        "",
        "## Does adding SAR improve the task?",
        "",
        "| comparison | Δ macro-F1 | 95% CI | CI excludes 0 | McNemar p |",
        "|------------|:----------:|:------:|:-------------:|:---------:|",
        f"| CROMA joint − CROMA optical | {s['croma_joint_vs_croma_optical']['abs_delta_macro_f1']:+.4f} "
        f"| {s['croma_joint_vs_croma_optical']['ci95']} | {s['croma_joint_vs_croma_optical']['significant_ci']} "
        f"| {s['croma_joint_vs_croma_optical']['mcnemar_p']} |",
        f"| DOFA fused − DOFA optical | {s['dofa_fused_vs_dofa_optical']['abs_delta_macro_f1']:+.4f} "
        f"| {s['dofa_fused_vs_dofa_optical']['ci95']} | {s['dofa_fused_vs_dofa_optical']['significant_ci']} "
        f"| {s['dofa_fused_vs_dofa_optical']['mcnemar_p']} |",
        "",
        "## CROMA vs DOFA",
        "",
        f"- Rule: {d['rule']}",
        f"- CROMA joint macro-F1 **{d['croma_joint_macro_f1']}**  ·  DOFA fused macro-F1 **{d['dofa_fused_macro_f1']}**",
        f"- B−C 95% CI: {d['b_minus_c_ci95']}  ·  practically tied: **{d['practically_tied']}**",
        f"- **Winner: {d['winner']}**",
        "",
        f"> {p['note']}",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
