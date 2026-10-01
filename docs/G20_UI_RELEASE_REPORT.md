# G20 — UI/UX Release Report

> UI/UX only. `FINAL_TECH_FREEZE = TRUE` — no backend, model, agent, routing,
> evidence, confidence, or API-schema change. The single production file changed
> is `apps/backend/app/static/index.html` (vanilla JS, no build step, no CDN).
> Companion docs: `docs/G20_UI_AUDIT.md`, `docs/G20_UI_QA.md`. Screenshots:
> `docs/sih/evidence/ui/`.

## What changed

`apps/backend/app/static/index.html` was rebuilt from a 2-column form + card
stack into a **geospatial-intelligence workstation**:

- **Top nav** — brand · ASK · INVESTIGATE · ABOUT · a live **● system status**
  chip (polls `/health`) → popover (planner *deterministic*, models *local*,
  geo ✓, evidence ✓, agent ✓, **GPU UNVERIFIED**).
- **Hero / landing** — headline *"Investigate satellite imagery with natural
  language."*, one supporting line, two primary actions, a
  `MISSION → PLAN → … → VERIFIED MAP & REPORT` strip, four capability chips.
- **ASK** — one compact column: image · question · examples · run → result
  (answer, task, model, latency, raw model score *labelled not-a-confidence*),
  raster viewer with box/region overlays, grouped verification, evidence,
  warnings.
- **INVESTIGATE** — the hero. A 3-column workspace
  (`minmax(290px,350px) / 1fr / minmax(300px,380px)` + a full-width bottom row):
  - **LEFT** — MISSION (understood-as, planner, models, tool calls, conclusion),
    PLAN (typed steps with real completed/failed/skipped states + summaries),
    **ADAPTIVE EXECUTION** (OBSERVATION → DECISION → OUTCOME built only from real
    `steps[]` + `replans[]`; `early_stopped` → a "stopped early" terminator).
  - **CENTRE** — **SPATIAL VIEW**: a raster `<img>` + `<canvas>` overlay when an
    input is PNG/JPEG; otherwise an SVG plot of the real `geojson` polygons /
    grounded box in EPSG:4326 with lon/lat axis labels, layer toggles
    (REGIONS / GROUNDING / FOOTPRINT) and FIT / RESET; below it the
    spatial-findings coordinate table + GeoJSON copy.
  - **RIGHT** — FINDINGS (metric tiles from real `findings` + `key_findings`),
    **CONFIDENCE** (large category chip + ✓/• "why" list + hard-rule +
    INSUFFICIENT_EVIDENCE sentence; never a number), VERIFICATION (checks grouped
    Structural / Geospatial / Evidence, real `detail`, never force-green),
    EVIDENCE (claim · source · recorded + payload), WARNINGS (verbatim; standing
    caveats muted, failures red).
  - **BOTTOM** — Export investigation report ↗ (unchanged `POST
    /investigate/report`), New investigation, collapsible execution trace,
    collapsible provenance.
- **States** — loading ("executing specialist models on CPU … up to ~90 s",
  real elapsed timer, **no fake progress**); error ("ANALYSIS COULD NOT BE
  COMPLETED" → REASON / RESOLUTION); partial ("PARTIAL INVESTIGATION" listing
  completed vs not-completed from real `steps[]`).
- **DEMO mode** — a toggle in INVESTIGATE prefills the *official* flagship
  mission and lists the demo tile filenames. It still submits to the **real**
  `/investigate` endpoint — no canned execution, no recorded output, no fixture
  fetch in the shipped file.

## What did NOT change

Endpoints, request shapes, response schemas, `viewReport()` behaviour, the
`/artifact` URL scheme, every computed value (findings, coordinates, confidence
category, verification status, warnings all read straight from the response), and
the single-file no-build deployment model.

## Data integrity

Every field the UI renders is asserted to exist in the real captured responses
(`test_g20_ui.py::test_ui_reads_only_fields_the_backend_actually_returns`), so a
backend shape drift fails a test instead of silently blanking a panel. No
fabricated data, progress, reasoning, metric, or confidence appears anywhere.
`test_no_forbidden_claims_in_ui` blocks "state-of-the-art", "real-time", "fully
autonomous", "hallucination-free", "SOTA", "SAR improves", and any "4 GB" claim
in the served page. RemoteSAM-licence and GPU-UNVERIFIED caveats are kept.

## Testing

| suite | result |
|-------|--------|
| `apps/backend/tests/test_g20_ui.py` (new) | **36 passed** — page loads / nav / hero copy / mode structure / render-function presence / terminology / forbidden-claim absence / confidence-never-a-number / accessibility markers / `/health` / OpenAPI routes intact / `/investigate/report` still renders / UI↔data contract / CASE A vs CASE B differ |
| full fast suite (`-m "not slow and not gpu and not integration"`) | **419 passed, 0 failed, 0 regressions** (383 pre-G20 + 36 G20) |
| JS syntax | `new Function(<inline script>)` parses clean |
| Visual QA | `docs/G20_UI_QA.md` — 8 issues found and fixed during the pass (1 P1 crash on the ASK path, 2 P2, 5 P3); layout verified at 1920×1080 and 1366×768 |

## Screenshots (PPT assets)

`docs/sih/evidence/ui/` — landing, ask (empty + result), investigate (input +
loading + CASE A + CASE B + error), about; at 1920×1080 and 1366×768. Result
screens rendered from the frozen `demos/final` captures through the shipped
code — real data.

## Definition of Done (Part 35)

- [x] landing clearly explains SatQuery
- [x] ASK and INVESTIGATE are obvious (nav + hero + distinct layouts)
- [x] INVESTIGATE is the hero workflow (3-column workspace, map centre)
- [x] mission input is clear
- [x] plan is visible with real step states
- [x] real execution events are visible (no fabrication)
- [x] adaptive behaviour is visible (OBSERVATION → DECISION → OUTCOME)
- [x] map is the visual centrepiece
- [x] findings immediately readable (metric tiles + key findings)
- [x] confidence **category** visible; never a number
- [x] evidence visible (claim · source · recorded)
- [x] verification visible (grouped, real detail, not all-green)
- [x] warnings visible (verbatim, weighted)
- [x] trace expandable (collapsed by default)
- [x] report button works (unchanged endpoint)
- [x] all errors structured (REASON / RESOLUTION; partial-investigation panel)
- [x] no fake progress / reasoning / metrics
- [x] no architecture / model / backend change
- [x] no backend regressions (419 pass)
- [x] 1366×768 works · 1920×1080 works
- [x] all tests pass
- [x] final screenshots captured
- [x] demo flow rehearsal-ready (`docs/sih/FINAL_DEMO_SCRIPT.md` unaffected;
      DEMO toggle added for the judge path)

## The 30-second design test (Part 34)

From the CASE A screenshot alone, a cold viewer can see: **(1)** it investigates
satellite imagery from a plain-English mission (MISSION panel, top-left);
**(2)** the agent planned typed steps and adapted (PLAN + ADAPTIVE EXECUTION);
**(3)** the geospatial output is the centre map (6 changed regions in lon/lat) +
the coordinate table; **(4)** trust is the HIGH chip with a "why" list, backed by
grouped VERIFICATION and EVIDENCE, with WARNINGS shown, not hidden. It does not
read as a chatbot.
