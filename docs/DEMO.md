# SatQuery — 2-minute demo script

## Setup state (before the audience looks)

1. Backend running: `make dev-backend` → `http://127.0.0.1:8000/` open in a browser.
2. Demo tiles present under `data/demo/` (shipped with the repo).
3. Cold start expected: the first model call per specialist loads weights (seconds to ~a minute on CPU); later calls are warm.

## The script

**0:00–0:30 — The question.** "SatQuery answers plain-English questions about satellite imagery — and shows its work. Everything on screen comes from executed models, not canned text."

**0:30–1:00 — ASK (single image).** Upload `data/demo/grounding/scene.jpg`, ask *"Where is the largest ship?"* Point out: the bounding box + mask overlay, the verification line, and the evidence entry tracing the box to the grounding model.

**1:00–2:00 — INVESTIGATE (multi-image mission).** Switch tabs, upload the four `data/demo/investigation/` tiles (`t1_optical.tif`, `t2_optical.tif`, `s2_dfc_optical.tif`, `s1_dfc_sar.tif`), ask for significant changes and affected structures. While it runs, point out the plan steps and adaptive execution log. When done: the overlay preview (change tint + box on post-event optical), the findings tiles, the confidence category with its "why" list, verification, and warnings.

**2:00–2:30 — The honest failure.** "If the image pair isn't co-registered, it refuses instead of guessing." Mention the BLOCKED state: status banner, *"Spatial comparison unavailable"*, and the what-happened/how-to-fix panel. Close on the report export (`Export report` → HTML) and GeoJSON.

## Screenshot/GIF checklist

- [ ] ASK result: box + mask overlay with evidence panel visible
- [ ] INVESTIGATE workspace: plan + spatial viewer + findings in one frame
- [ ] Overlay preview close-up (change tint + grounding box)
- [ ] Confidence + verification + warnings panels
- [ ] BLOCKED state banner with the unavailable-map message
- [ ] Exported HTML report
- [ ] GIF: upload → analyze → evidence flow (~60s)
