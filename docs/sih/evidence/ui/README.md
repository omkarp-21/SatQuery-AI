# SatQuery UI — screenshot set (G20)

PPT-ready captures of the rebuilt geospatial-intelligence UI
(`apps/backend/app/static/index.html`). Empty/loading/error states were captured
live; every **result** screen was rendered from the **real captured** flagship /
secondary responses in `docs/sih/evidence/demos/final/*.json` through the shipped
render functions — no synthetic data, no mocked model output.

| File | Screen | Resolution |
|------|--------|-----------|
| `01_landing_1920.png` | Landing / hero | 1920×1080 |
| `02_ask_empty_1920.png` | Ask — input form | 1920×1080 |
| `03_investigate_input_1920.png` | Investigate — mission + inputs + demo toggle | 1920×1080 |
| `04_ask_result_1920.png` | Ask — grounding result (real scene + box overlay, verification, evidence, licence warning) | 1920×1080, full page |
| `05_loading_1920.png` | Investigate — "in progress" (real elapsed timer, no fake progress) | 1920×1080 |
| `06_caseA_result_1920.png` | Investigate — **CASE A** (real change): map of 6 changed regions, 4 tool calls, HIGH confidence | 1920×1080 |
| `06_caseA_result_full_1920.png` | CASE A — full page (mission · plan · adaptive · map · findings · trust · verification · evidence · warnings · trace) | full page |
| `07_caseB_result_1920.png` | Investigate — **CASE B** (minimal change): explained empty map, 2 tool calls, early stop, MEDIUM confidence | 1920×1080 |
| `09_error_1920.png` | Error state — REASON / RESOLUTION panel | 1920×1080 |
| `10_about_1920.png` | About — frozen stack, pipeline, endpoints, caveats | full page |
| `11_caseA_1366.png` | CASE A at the smaller target resolution | 1366×768 |
| `12_landing_1366.png` | Landing at the smaller target resolution | 1366×768 |

## Regenerate

Run the backend (`docs/sih/DEMO_RUNBOOK.md` §C) and, for the result screens,
either run the flagship live or load a captured JSON through the page's render
functions. The captures here were produced with a local static server + the
Chrome DevTools screenshot tool against the frozen `demos/final` JSON.

The CASE A / CASE B pair is the one to put on a slide: **same mission, different
execution because the data differed** — see `docs/sih/DEMO_STORYBOARD.md` screen 11.
