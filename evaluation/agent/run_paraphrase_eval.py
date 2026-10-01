"""G16 Part 10 - prompt robustness. Feeds >=6 paraphrases per capability family
to BOTH planner arms and checks the SAME family is inferred (must_contain /
must_not_contain over the planned tool set), i.e. the planner is not keyword-brittle.

The RuleBasedPlanner arm is always run (fast). The LLM arm reads
`G16_paraphrase_llm_cache.json` (built by `--llm-cache`, slow) and falls back to
the rule planner per-paraphrase when the LLM produced nothing usable.

Usage:
  SATQUERY_PLANNER_PERSISTENT=1 .venvs/satquery/Scripts/python.exe evaluation/agent/run_paraphrase_eval.py --llm-cache
  .venvs/satquery/Scripts/python.exe evaluation/agent/run_paraphrase_eval.py
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO / "packages" / "agents" / "src"))

from satquery_agents.agent import (  # noqa: E402
    LlmPlanner,
    RuleBasedPlanner,
    build_plan_from_raw,
    plan_with_fallback_ex,
)

_SET = _REPO / "evaluation" / "agent" / "paraphrase_missions.json"
_OUT = _REPO / "evaluation" / "agent" / "reports"
_CACHE = _OUT / "G16_paraphrase_llm_cache.json"


def _check(tools: list[str], fam: dict) -> bool:
    return (all(t in tools for t in fam["must_contain"])
            and not any(t in tools for t in fam.get("must_not_contain", [])))


def llm_cache(fams: list[dict], redo: bool) -> dict:
    cache = json.loads(_CACHE.read_text()) if _CACHE.exists() else {}
    pl = LlmPlanner()
    from satquery_agents.agent.prompts import build_prompt
    for fam in fams:
        for i, para in enumerate(fam["paraphrases"]):
            key = f"{fam['family']}::{i}"
            if key in cache and not redo:
                continue
            prompt = build_prompt(para, fam["image_count"], fam["modalities"], compact=pl.compact)
            t0 = time.time()
            try:
                raw, gen_s = pl._local_qwen(prompt)  # noqa: SLF001
                err = None
            except Exception as exc:  # noqa: BLE001
                raw, gen_s, err = "", None, f"{type(exc).__name__}: {exc}"
            cache[key] = {"para": para, "raw": raw, "gen_s": gen_s, "error": err,
                          "wall_s": round(time.time() - t0, 1)}
            _CACHE.write_text(json.dumps(cache, indent=1))
            print(f"  {key} gen={gen_s}s" + (f" ERR {err}" if err else ""), flush=True)
    return cache


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--llm-cache", action="store_true")
    ap.add_argument("--redo-cache", action="store_true")
    a = ap.parse_args()

    spec = json.loads(_SET.read_text())
    fams = spec["families"]
    if a.llm_cache:
        llm_cache(fams, a.redo_cache)
        return 0

    cache = json.loads(_CACHE.read_text()) if _CACHE.exists() else {}
    rows = []
    for fam in fams:
        for i, para in enumerate(fam["paraphrases"]):
            # rule arm
            rplan, rused, _, _ = plan_with_fallback_ex(para, fam["image_count"], fam["modalities"],
                                                       planner=RuleBasedPlanner())
            rtools = [s.tool for s in rplan.steps]
            rok = _check(rtools, fam)
            # llm arm
            c = cache.get(f"{fam['family']}::{i}")
            lused, ltools, lok = "rule_based_fallback", [], None
            if c and not c.get("error") and c.get("raw"):
                lplan, att = build_plan_from_raw(c["raw"], image_count=fam["image_count"])
                if lplan is not None:
                    ltools = [s.tool for s in lplan.steps]
                    lused = "llm_repaired" if att.final_source == "llm_repaired" else "llm"
                    lok = _check(ltools, fam)
            if lok is None and c:
                fb, *_ = plan_with_fallback_ex(para, fam["image_count"], fam["modalities"],
                                               planner=RuleBasedPlanner())
                ltools = [s.tool for s in fb.steps]
                lok = _check(ltools, fam)
            rows.append({"family": fam["family"], "i": i, "para": para,
                         "rule_ok": rok, "rule_tools": rtools,
                         "llm_ok": lok, "llm_used": lused, "llm_tools": ltools})

    def _agg(key):
        by_fam = {}
        for fam in fams:
            fr = [r for r in rows if r["family"] == fam["family"] and r[key] is not None]
            by_fam[fam["family"]] = {"n": len(fr),
                                     "consistent": round(sum(r[key] for r in fr) / len(fr), 3) if fr else None}
        allr = [r for r in rows if r[key] is not None]
        return {"overall": round(sum(r[key] for r in allr) / len(allr), 3) if allr else None,
                "n": len(allr), "by_family": by_fam}

    report = {
        "evaluation": "G16 Part 10 - prompt robustness (paraphrase family-consistency)",
        "date": time.strftime("%Y-%m-%dT%H%M%S"),
        "n_paraphrases": len(rows),
        "n_families": len(fams),
        "llm_cached": len(cache),
        "RULE_arm_family_consistency": _agg("rule_ok"),
        "LLM_arm_family_consistency": _agg("llm_ok"),
        "rows": rows,
    }
    _OUT.mkdir(parents=True, exist_ok=True)
    (_OUT / "G16_PARAPHRASE_ROBUSTNESS.json").write_text(json.dumps(report, indent=2))
    print(json.dumps({k: report[k] for k in
                      ("n_paraphrases", "RULE_arm_family_consistency", "LLM_arm_family_consistency")},
                     indent=2))
    # a compact MD
    L = [f"# G16 Paraphrase Robustness - {report['date']}", "",
         f"{len(rows)} paraphrases across {len(fams)} capability families; "
         f"a planner passes a row if the planned tool set matches the family "
         f"(must_contain all / must_not_contain none).", "",
         "| family | N | RULE consistent | LLM consistent |", "|---|:-:|:-:|:-:|"]
    for fam in fams:
        rf = report["RULE_arm_family_consistency"]["by_family"][fam["family"]]
        lf = report["LLM_arm_family_consistency"]["by_family"][fam["family"]]
        L.append(f"| {fam['family']} | {rf['n']} | {rf['consistent']} | {lf['consistent']} |")
    L += ["", f"**Overall** - RULE {report['RULE_arm_family_consistency']['overall']} "
          f"(N={report['RULE_arm_family_consistency']['n']}) · "
          f"LLM {report['LLM_arm_family_consistency']['overall']} "
          f"(N={report['LLM_arm_family_consistency']['n']})."]
    (_OUT / "G16_PARAPHRASE_ROBUSTNESS.md").write_text("\n".join(L))
    print(f"\nwrote {_OUT / 'G16_PARAPHRASE_ROBUSTNESS.json'} + .md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
