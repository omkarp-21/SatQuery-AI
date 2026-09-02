"""Build the G17 frozen mission set: 100 missions.

- The first 50 are `frozen_missions.json` VERBATIM (so G15/G16 still reproduce),
  each annotated with an `expected_intent` (task_family + required_capabilities)
  derived deterministically from its `expected_tool_set`.
- 50 more are added: paraphrase / scenario variants, 10 per category, so every
  category reaches 20 (Part 8).

Output: `evaluation/agent/frozen_missions_100.json`. Re-run to regenerate.
"""

from __future__ import annotations

import json
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_SRC = _HERE / "frozen_missions.json"
_OUT = _HERE / "frozen_missions_100.json"

_TOOL_CAP = {
    "run_vqa": "VQA", "run_grounding": "GROUNDING", "run_scene_retrieval": "SCENE_RETRIEVAL",
    "run_temporal_change": "TEMPORAL_CHANGE", "run_semantic_temporal_baseline": "SEMANTIC_CHANGE",
    "extract_changed_regions": "CHANGED_REGIONS", "run_optical_sar": "OPTICAL_SAR",
    "cross_check_evidence": "CROSS_CHECK",
}


def _expected_intent(m: dict) -> dict:
    tools = [t for t in m.get("expected_tool_set", []) if t in _TOOL_CAP]
    caps = []
    for t in tools:
        c = _TOOL_CAP[t]
        if c not in caps:
            caps.append(c)
    cat = m["category"]
    if m.get("unsupported"):
        fam = "UNSUPPORTED"
        caps = []
    elif cat == "multi_step" or len([c for c in caps if c in
                                     ("TEMPORAL_CHANGE", "GROUNDING", "OPTICAL_SAR", "SEMANTIC_CHANGE")]) >= 2:
        fam = "INVESTIGATION"
    elif "SEMANTIC_CHANGE" in caps:
        fam = "SEMANTIC_CHANGE"
    elif "TEMPORAL_CHANGE" in caps:
        fam = "TEMPORAL_CHANGE"
    elif "OPTICAL_SAR" in caps:
        fam = "OPTICAL_SAR"
    elif "GROUNDING" in caps:
        fam = "GROUNDING"
    elif "SCENE_RETRIEVAL" in caps:
        fam = "SCENE"
    elif "VQA" in caps:
        fam = "VQA"
    else:
        fam = "UNSUPPORTED"
    return {"task_family": fam, "required_capabilities": caps}


# --- 50 new missions: paraphrase / scenario variants -----------------------------
# each reuses an existing mission's inputs + expected_* but rewords the query and
# (for a few) tweaks the scenario. mission_id prefixes: ss/tm/os/mi/ad + 11..20

def _variants(base: dict, new_id: str, query: str, note: str, **over) -> dict:
    v = json.loads(json.dumps(base))
    v["mission_id"] = new_id
    v["user_query"] = query
    v["notes"] = note
    v.update(over)
    return v


def build() -> dict:
    spec = json.loads(_SRC.read_text())
    missions = spec["missions"]
    by_id = {m["mission_id"]: m for m in missions}
    for m in missions:
        m["expected_intent"] = _expected_intent(m)

    P: list[dict] = []
    # single_step (target 10 more -> ss-11..ss-20)
    P += [
        _variants(by_id["ss-01"], "ss-11", "Describe everything you can see in this scene.", "VQA paraphrase"),
        _variants(by_id["ss-01"], "ss-12", "Give me a rundown of the objects present in this image.", "VQA paraphrase"),
        _variants(by_id["ss-02"], "ss-13", "How many aircraft are on the apron?", "VQA counting"),
        _variants(by_id["ss-02"], "ss-14", "Is there any visible water in this scene?", "VQA yes/no"),
        _variants(by_id["ss-03"], "ss-15", "Point me to the runway in this image.", "grounding paraphrase"),
        _variants(by_id["ss-03"], "ss-16", "Outline where the largest building sits.", "grounding paraphrase"),
        _variants(by_id["ss-04"], "ss-17", "What land-cover type dominates this scene?", "scene paraphrase"),
        _variants(by_id["ss-04"], "ss-18", "Classify this patch: urban, farmland, forest or water?", "scene paraphrase"),
        _variants(by_id["ss-05"] if "ss-05" in by_id else by_id["ss-01"], "ss-19",
                  "Which corner of the image contains the storage tanks?", "grounding paraphrase"),
        _variants(by_id["ss-06"] if "ss-06" in by_id else by_id["ss-01"], "ss-20",
                  "Summarise the contents of this satellite tile.", "VQA paraphrase"),
    ]
    # temporal (tm-11..tm-20)
    P += [
        _variants(by_id["tm-01"], "tm-11", "What has changed substantially between these two dates?", "change paraphrase"),
        _variants(by_id["tm-01"], "tm-12", "Identify the major temporal differences in this area.", "change paraphrase"),
        _variants(by_id["tm-01"], "tm-13", "Compare the before and after images and report what moved.", "change paraphrase"),
        _variants(by_id["tm-02"] if "tm-02" in by_id else by_id["tm-01"], "tm-14",
                  "Where did the scene change the most between the two observations?", "change paraphrase"),
        _variants(by_id["tm-04"] if "tm-04" in by_id else by_id["tm-01"], "tm-15",
                  "Which regions saw significant change? Pull them out.", "change + regions paraphrase"),
        _variants(by_id["tm-04"] if "tm-04" in by_id else by_id["tm-01"], "tm-16",
                  "Extract the areas that changed between the two images.", "change + regions paraphrase"),
        _variants(by_id["tm-05"] if "tm-05" in by_id else by_id["tm-01"], "tm-17",
                  "Describe what KIND of change happened here.", "semantic-change paraphrase"),
        _variants(by_id["tm-05"] if "tm-05" in by_id else by_id["tm-01"], "tm-18",
                  "Characterise the nature of the change between these dates.", "semantic-change paraphrase"),
        _variants(by_id["tm-03"] if "tm-03" in by_id else by_id["tm-01"], "tm-19",
                  "Quantify how much of this area changed over time.", "change paraphrase"),
        _variants(by_id["tm-10"], "tm-20", "Compare these two identical-looking observations for any change.",
                  "no-change probe (paraphrase of tm-10)"),
    ]
    # optical_sar (os-11..os-20)
    P += [
        _variants(by_id["os-01"], "os-11", "Fuse the Sentinel-2 and Sentinel-1 views of this site.", "opt+SAR paraphrase"),
        _variants(by_id["os-01"], "os-12", "Combine the optical and backscatter data into one representation.", "opt+SAR paraphrase"),
        _variants(by_id["os-01"], "os-13", "What does the radar add to the optical picture here?", "opt+SAR paraphrase"),
        _variants(by_id["os-02"] if "os-02" in by_id else by_id["os-01"], "os-14",
                  "Analyse this location with optical and SAR together.", "opt+SAR paraphrase"),
        _variants(by_id["os-02"] if "os-02" in by_id else by_id["os-01"], "os-15",
                  "Give me a joint optical-plus-radar view of this scene.", "opt+SAR paraphrase"),
        _variants(by_id["os-03"] if "os-03" in by_id else by_id["os-01"], "os-16",
                  "Cross-reference the optical image with the SAR image.", "opt+SAR paraphrase"),
        _variants(by_id["os-03"] if "os-03" in by_id else by_id["os-01"], "os-17",
                  "Compute a CROMA joint embedding for this optical/SAR pair.", "opt+SAR paraphrase"),
        _variants(by_id["os-04"] if "os-04" in by_id else by_id["os-01"], "os-18",
                  "How do the optical and SAR observations complement each other here?", "opt+SAR paraphrase"),
        _variants(by_id["os-05"] if "os-05" in by_id else by_id["os-01"], "os-19",
                  "Merge the optical and SAR channels for this area.", "opt+SAR paraphrase"),
        _variants(by_id["os-06"] if "os-06" in by_id else by_id["os-01"], "os-20",
                  "Represent this scene using both optical and radar.", "opt+SAR paraphrase"),
    ]
    # multi_step investigation (mi-11..mi-20)
    P += [
        _variants(by_id["mi-01"], "mi-11",
                  "Something happened here between these two dates - work out what changed, where the changed "
                  "buildings are, and bring in the radar to back it up.", "investigation paraphrase"),
        _variants(by_id["mi-01"], "mi-12",
                  "Run a full change investigation: detect the change, pull out the changed regions, find the "
                  "buildings involved, and cross-check with the SAR.", "investigation paraphrase"),
        _variants(by_id["mi-01"], "mi-13",
                  "I need an evidence-backed report on what changed here, which structures were hit, and how the "
                  "SAR corroborates it.", "investigation paraphrase"),
        _variants(by_id["mi-02"] if "mi-02" in by_id else by_id["mi-01"], "mi-14",
                  "Do a comprehensive assessment of change at this site, pinpoint the impacted structures, and "
                  "verify with optical and SAR evidence.", "investigation paraphrase"),
        _variants(by_id["mi-02"] if "mi-02" in by_id else by_id["mi-01"], "mi-15",
                  "Work through this step by step: change detection, changed-region extraction, building "
                  "localisation, SAR characterisation, verification.", "investigation paraphrase"),
        _variants(by_id["mi-06"] if "mi-06" in by_id else by_id["mi-01"], "mi-16",
                  "Perform a remote-sensing investigation of this location covering change, affected structures, "
                  "and SAR corroboration.", "investigation paraphrase"),
        _variants(by_id["mi-03"] if "mi-03" in by_id else by_id["mi-01"], "mi-17",
                  "Analyse the temporal difference, extract the changed areas, ground the affected buildings, and "
                  "compare optical vs SAR.", "investigation paraphrase"),
        _variants(by_id["mi-04"] if "mi-04" in by_id else by_id["mi-01"], "mi-18",
                  "Investigate this area: find the changes and locate the affected structures.", "investigation (no SAR ask)"),
        _variants(by_id["mi-05"] if "mi-05" in by_id else by_id["mi-01"], "mi-19",
                  "Give me a verified summary of what changed and which buildings are involved, with evidence.",
                  "investigation paraphrase"),
        _variants(by_id["mi-07"] if "mi-07" in by_id else by_id["mi-01"], "mi-20",
                  "Full investigation please: temporal change, changed regions, grounded structures, SAR cross-check, "
                  "verification.", "investigation paraphrase"),
    ]
    # adversarial (ad-11..ad-20)
    P += [
        _variants(by_id["ad-01"], "ad-11", "What changed between these images?", "missing 2nd image (dup of ad-01 scenario)"),
        _variants(by_id["ad-02"], "ad-12", "Compare optical and SAR for this area.", "missing SAR (paraphrase)"),
        _variants(by_id["ad-06"], "ad-13", "Find the submarine in this desert scene.", "object absent (paraphrase)"),
        _variants(by_id["ad-08"] if "ad-08" in by_id else by_id["ad-06"], "ad-14",
                  "Tell me the population of this city from the image.", "out-of-scope"),
        _variants(by_id["ad-08"] if "ad-08" in by_id else by_id["ad-06"], "ad-15",
                  "Predict tomorrow's rainfall for this location.", "out-of-scope"),
        _variants(by_id["ad-09"] if "ad-09" in by_id else by_id["ad-06"], "ad-16",
                  "Use RemoteSAM to count the ships.", "wrong tool named (paraphrase)"),
        _variants(by_id["ad-10"] if "ad-10" in by_id else by_id["ad-06"], "ad-17",
                  "Analyse absolutely everything about this area in exhaustive detail, forever.", "unbounded ask (paraphrase)"),
        _variants(by_id["ad-07"] if "ad-07" in by_id else by_id["ad-06"], "ad-18",
                  "image", "degenerate one-word query"),
        _variants(by_id["ad-03"] if "ad-03" in by_id else by_id["ad-02"], "ad-19",
                  "Compare the optical and SAR imagery for this location.", "missing SAR replan (paraphrase of ad-03)"),
        _variants(by_id["ad-04"] if "ad-04" in by_id else by_id["ad-01"], "ad-20",
                  "What changed between these two images?", "misregistered pair (paraphrase of ad-04)"),
    ]

    for m in P:
        m["expected_intent"] = _expected_intent(m)

    all_missions = missions + P
    spec["missions"] = all_missions
    spec["name"] = "SatQuery Agent Evaluation - frozen mission set (G17, 100 missions)"
    spec["n_missions"] = len(all_missions)
    spec["note"] = (spec.get("note", "") + " | G17: first 50 = the G15/G16 frozen set verbatim "
                    "(+ expected_intent); ss/tm/os/mi/ad 11-20 = paraphrase / scenario variants. "
                    "expected_intent = the typed Intent a correct extractor should produce.")
    _OUT.write_text(json.dumps(spec, indent=1))
    cats: dict[str, int] = {}
    for m in all_missions:
        cats[m["category"]] = cats.get(m["category"], 0) + 1
    print(f"wrote {_OUT} : {len(all_missions)} missions {cats}")
    return spec


if __name__ == "__main__":
    build()
