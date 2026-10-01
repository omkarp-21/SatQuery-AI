# G20 — UI Audit (before)

> UI/UX only. Backend, models, agent, routing, evidence, confidence, API schemas
> are frozen (`FINAL_TECH_FREEZE = TRUE`). The single file changed is
> `apps/backend/app/static/index.html` (vanilla JS, no build step). Every value
> rendered comes from a real backend response field — no fabricated data,
> progress, reasoning, or metrics. Terminology and claims follow
> `docs/sih/CLAIM_MATRIX.md`.

Read for this audit: `apps/backend/app/static/index.html`,
`docs/API_CONTRACT.md`, `docs/G19_SIH_SOURCE_OF_TRUTH.md`,
`docs/sih/SIH_CORE_STORY.md`, `docs/sih/DEMO_STORYBOARD.md`,
`docs/sih/FINAL_DEMO_SCRIPT.md`, `docs/sih/CLAIM_MATRIX.md`,
`docs/sih/DEMO_RUNBOOK.md`.

---

## Format: CURRENT · PROBLEM · CHANGE · WHY

### A1 — Overall shell

- **CURRENT:** one `<header>` + a 2-column grid (`380px` left console, `1fr`
  right result). No navigation. Sub-title reads "Natural-language remote-sensing
  assistant".
- **PROBLEM:** reads as a form + output log — "academic prototype / chatbot",
  not an intelligence workstation. No sense of *place* (ASK vs INVESTIGATE vs
  about vs status). The word "assistant" undersells it.
- **CHANGE:** top nav bar — brand · **ASK** · **INVESTIGATE** · **ABOUT** · a
  right-aligned **● system status** chip. A landing/hero view. A footer status
  strip (local inference · deterministic planner · GPU: UNVERIFIED). INVESTIGATE
  gets a dedicated 3-column workspace.
- **WHY:** the judge must know within seconds this is a geospatial investigation
  system with distinct modes, not a single text box.

### A2 — No landing / hero

- **CURRENT:** the page opens directly on the query form; the right pane says
  "Run a query to see the answer…".
- **PROBLEM:** nothing explains *what SatQuery is* or *what to ask it*. Fails the
  "obvious in 30–60 s" test.
- **CHANGE:** a hero: headline *"Investigate satellite imagery with natural
  language."*, one supporting line, two primary actions
  **[ ASK A QUESTION ]** / **[ INVESTIGATE AN AREA ]**, and a one-line pipeline
  strip `MISSION → PLAN → ANALYSIS → OBSERVATION → EVIDENCE → VERIFIED MAP`.
- **WHY:** Part 3 / Part 34 — a cold viewer should answer "what does this do?"
  from the first screen.

### A3 — ASK and INVESTIGATE share one layout

- **CURRENT:** a `.modewrap` toggle swaps a few labels; both modes render into
  the same right-hand card stack.
- **PROBLEM:** INVESTIGATE — the differentiator — looks identical to a simple
  Q&A. The multi-step story is buried in a vertical scroll of ~9 cards.
- **CHANGE:** ASK stays a compact single-column card (image · query · run ·
  result). INVESTIGATE becomes the hero: **LEFT** mission + inputs + plan +
  adaptive execution · **CENTER** large spatial viewer · **RIGHT** findings +
  trust + verification + evidence · **BOTTOM** trace + report.
- **WHY:** Part 5 / Part 6 / Part 28 — INVESTIGATE must be visually the main
  event, with the map carrying the most weight.

### A4 — "dashboard full of cards"

- **CURRENT:** investigation result = 9 equally-weighted `.card` blocks stacked
  vertically (result, plan, replans, key findings, spatial findings,
  verification, confidence, evidence, warnings, trace).
- **PROBLEM:** no hierarchy — the map/geometry, the findings and the trust
  category compete with the audit block for attention. Part 28's priority order
  is inverted (trace and provenance are as prominent as findings).
- **CHANGE:** priority-ordered layout: (1) spatial viewer, (2) mission, (3)
  findings, (4) plan, (5) trust, (6) evidence, (7) collapsible technical trace.
  Provenance / raw JSON demoted to a collapsed `<details>`.
- **WHY:** Part 28 — communicate "SatQuery is doing geospatial work", not
  "SatQuery has lots of cards".

### A5 — No map / spatial centrepiece

- **CURRENT:** for ASK, a single `<img>` of `input_files[0]` with a `<canvas>`
  overlay (boxes / region bboxes). For INVESTIGATE there is **no** viewer at all
  — spatial findings are a text table; the GeoJSON is a "copy" link.
- **PROBLEM:** the system's spatial nature is invisible in the hero flow. Also
  GeoTIFF inputs cannot render in `<img>`, so a naive image viewer would break
  on the flagship.
- **CHANGE:** a CENTER viewer with two honest modes:
  - **raster mode** (input is png/jpg): the image + `<canvas>` overlays for
    boxes / regions / mask link — as today, enlarged.
  - **geometry mode** (inputs are GeoTIFF, nothing browser-renderable): an SVG
    plot of the **real** `geojson` polygons + grounded box in EPSG:4326, with
    lon/lat extent labels, layer toggles `[ REGIONS ] [ GROUNDING ] [ FOOTPRINT ]`
    and FIT / RESET. Labelled "source imagery is GeoTIFF — not shown inline".
- **WHY:** Part 10 / Part 28 — a spatial centrepiece, without fabricating
  imagery we don't have.

### A6 — Adaptive behaviour is not legible

- **CURRENT:** replans render as a 2-column table (`reason` + `detail` →
  `steps_skipped`). `early_stopped` is a suffix on the "Tool calls" line.
- **PROBLEM:** the single most important proof point — *observe → decide → act* —
  is a dense table a judge will not parse. CASE A vs CASE B difference is not
  visually obvious.
- **CHANGE:** an **ADAPTIVE EXECUTION** timeline built from real data:
  per completed step → `OBSERVATION` (the step's `summary` / `findings`), and per
  `replans[]` entry → `OBSERVATION` (trigger step) · `DECISION` (`reason` +
  `detail`) · `OUTCOME` (`steps_skipped`, or "continued"). `early_stopped` →
  a bold "Investigation stopped early — <completion_reason>" terminator.
- **WHY:** Part 9 / Part 21 — make the agent's intelligence visible without
  showing chain-of-thought.

### A7 — Trust panel under-weighted

- **CURRENT:** confidence is one `kv` row in the result card plus a mid-stack
  "Confidence — evidence-derived category" card with a `Why` list.
- **PROBLEM:** trust should be one of the *most* visible elements (Part 12); it
  currently sits between verification and evidence with no visual emphasis.
- **CHANGE:** a dedicated **TRUST** block at the top of the RIGHT column: large
  category chip (HIGH / MEDIUM / LOW / INSUFFICIENT_EVIDENCE), a checklist-style
  "Why" from `confidence.reasons`, the `hard_rule` shown when present, and for
  INSUFFICIENT_EVIDENCE the sentence *"SatQuery could not establish this claim
  from the available evidence."* Never a number; `score` never shown.
- **WHY:** Part 12 / Part 33.

### A8 — Verification is a flat pass/fail table

- **CURRENT:** `verification.checks[]` rendered as `name` → pass/fail rows; for
  investigate only an "aggregate" row exists.
- **PROBLEM:** doesn't communicate *what* was verified (structural / geospatial /
  evidence). Everything green looks like rubber-stamping.
- **CHANGE:** group the real checks into **Structural / Geospatial / Evidence**
  buckets by name heuristic; show the real per-check `detail`; show the true
  state (pass / fail / not-applicable) — never force green. Overall status chip
  from `verification.status`.
- **WHY:** Part 14.

### A9 — Warnings styling

- **CURRENT:** `.warnbox` (amber) and `.badbox` (red) full-width blocks, one per
  warning; can dominate the view when several fire.
- **PROBLEM:** visible but heavy; the standing caveats (RemoteSAM licence, GPU
  unverified) look like errors.
- **CHANGE:** a compact **WARNINGS** list with a small ⚠ glyph per line;
  standing caveats get a muted "note" treatment, genuine failures the red
  treatment. All text still comes verbatim from `warnings[]` / `failures[]`.
- **WHY:** Part 15.

### A10 — Loading state

- **CURRENT:** `"<spin> Agent: planning → policy check → executing specialists →
  observe → verify …"` — a static string.
- **PROBLEM:** doesn't reflect the *actual* current step; on a cold start (~90 s)
  it looks hung.
- **CHANGE:** a structured **INVESTIGATION IN PROGRESS** panel: the plan list
  rendered immediately with all-pending states, a "Current step: …" line, and a
  "Loading specialist model — first call is slow on CPU" note for cold starts.
  No fake percentage, no progress bar. (The API is single-response, so "current
  step" is best-effort from elapsed time against the plan; if that cannot be
  known honestly it shows "Executing specialists…" only.)
- **WHY:** Part 19.

### A11 — Error state

- **CURRENT:** `<div class="badbox">HTTP 400 · bad_file_count: …</div>` — a raw
  red string.
- **PROBLEM:** looks like a crash, not a designed outcome.
- **CHANGE:** an **ANALYSIS COULD NOT BE COMPLETED** panel: `Reason:` (the
  backend error message), `Resolution:` (a short, generic, non-fabricated hint
  keyed off the error code — e.g. co-registration → "provide imagery with a
  compatible CRS and transform"). For a *partial* investigation (`ok:false` but
  steps ran) a **PARTIAL INVESTIGATION** panel listing what completed vs what
  could not, from real `steps[]` / `failures[]` / `warnings[]`.
- **WHY:** Part 20.

### A12 — No system-status surface

- **CURRENT:** a static "Frozen model stack (G12)" card lists the models.
- **PROBLEM:** no readiness signal; nothing states GPU is unverified in the UI
  chrome; the model-stack card is the second-most-prominent thing on the page.
- **CHANGE:** a **SYSTEM** status chip in the nav → popover: Planner
  *Deterministic* · Models *Local* · Geo validation ✓ · Evidence ✓ · Agent ✓ ·
  **GPU UNVERIFIED**. The model list moves into ABOUT.
- **WHY:** Part 18 / Part 33 — never imply GPU support.

### A13 — Terminology drift

- **CURRENT:** "assistant", "Analyze", "Result", "Failure-aware resolution",
  "Score".
- **PROBLEM:** Part 29 wants a fixed vocabulary; "score" next to a raw model
  softmax reads like a confidence.
- **CHANGE:** ASK · INVESTIGATE · MISSION · PLAN · EXECUTION · OBSERVATION ·
  FINDINGS · EVIDENCE · VERIFICATION · CONFIDENCE · WARNINGS · TRACE · REPORT.
  Raw model scores stay labelled "RemoteSAM foreground softmax — not a
  calibrated confidence" (verbatim from `score_meaning`).
- **WHY:** Part 29 / Part 33.

### A14 — Accessibility gaps

- **CURRENT:** buttons are `<button>` (good), but colour is the only signal for
  status; no `prefers-reduced-motion`; the spinner animates unconditionally;
  focus styles are browser default on a dark ground (low visibility); file input
  label is not programmatically associated.
- **CHANGE:** text/glyph + colour for every status; a visible focus ring token;
  `@media (prefers-reduced-motion: reduce)` disables the spin and all
  transitions; `aria-label`s on icon-only controls; `alt` on the viewer image;
  `role="status"` on the loading region.
- **WHY:** Part 24 / Part 23.

### A15 — Demo affordance

- **CURRENT:** example chips fill the query box; nothing prefills the official
  flagship mission or points at the demo tiles.
- **PROBLEM:** the runbook's flagship flow requires typing a long mission and
  knowing four filenames.
- **CHANGE:** a **DEMO** toggle in INVESTIGATE that prefills the *official*
  mission text and shows the exact demo tile filenames to select
  (`data/demo/investigation/…`). It still submits to the **real** `/investigate`
  endpoint — no canned execution, no recorded output.
- **WHY:** Part 26 / Part 27 — a judge-friendly path that is still 100 % real.

---

## Not changing (explicitly)

- Endpoints, request shapes, response schemas.
- `viewReport()` → `POST /investigate/report` behaviour (kept; relabelled
  "Export investigation report").
- The `/artifact` URL scheme for input previews and the grounding mask link.
- Any computed value — findings, coordinates, confidence category, verification
  status, warnings — all still read straight from the response.
- The single-file, no-build, no-CDN deployment model.
