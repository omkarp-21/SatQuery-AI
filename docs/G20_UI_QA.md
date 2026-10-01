# G20 — UI Visual QA

> Review of the rebuilt `apps/backend/app/static/index.html` at 1920×1080 and
> 1366×768. Screenshots in `docs/sih/evidence/ui/`. Every result screen was
> rendered from the **real captured** flagship / secondary responses
> (`docs/sih/evidence/demos/final/*.json`) through the shipped render functions —
> no synthetic data. States that need no backend (landing, empty forms, loading,
> error) were captured live.

Severity: **P1** fixed before commit · **P2** fixed before commit · **P3**
acceptable / noted.

---

## Screens reviewed

| # | Screen | File | State |
|---|--------|------|-------|
| 1 | Landing (hero) | `01_landing_1920.png`, `12_landing_1366.png` | ✅ |
| 2 | Ask — empty | `02_ask_empty_1920.png` | ✅ |
| 3 | Investigate — input | `03_investigate_input_1920.png` | ✅ |
| 4 | Ask — result (grounding) | `04_ask_result_1920.png` | ✅ |
| 5 | Investigate — loading | `05_loading_1920.png` | ✅ |
| 6 | Investigate — CASE A result | `06_caseA_result_1920.png`, `06_caseA_result_full_1920.png`, `11_caseA_1366.png` | ✅ |
| 7 | Investigate — CASE B result | `07_caseB_result_1920.png` | ✅ |
| 9 | Error state | `09_error_1920.png` | ✅ |
| 10 | About | `10_about_1920.png` | ✅ |

---

## Issues found and fixed (during the pass)

| # | Sev | Issue | Fix | Before → After |
|---|-----|-------|-----|----------------|
| Q1 | P1 | `verificationPanel` did `(v.notes||[]).map(...)` — the `/analyze` response returns `notes` as a **string**, so the ASK result crashed with "map is not a function". | Coerce: `vnotes = Array.isArray(v.notes) ? v.notes : v.notes ? [v.notes] : []`. | ASK result blank → renders grouped Structural / Geospatial / Evidence checks. |
| Q2 | P2 | `num(x, 5)` truncated longitudes (`114.9487 → "114.9"`) because of the `abs(x) ≥ 100 → 1 dp` metric shortcut. Coordinates were unreadable. | Added `coord(x) = x.toFixed(5)`; the shortcut now only applies when `d ≤ 3`. Spatial-findings table and axis labels use full precision. | `114.9, 28.912` → `114.94877, 28.91187`. |
| Q3 | P2 | Huge empty band in the centre column on CASE A (viewer ~400 px, side columns ~1100 px). | Moved the **spatial-findings coordinate table + GeoJSON line** out of the right-hand Findings panel into a panel **under the viewer** in the centre column. | Centre column now carries the map + the coordinates; right column is metrics + narrative only. |
| Q4 | P2 | CASE B centre was a bare "No spatial geometry" box — a meaningless void for the demo's most important case. | The empty-viewer state now explains *why*: "The agent stopped early — no significant temporal change detected — before the localisation and optical+SAR steps. See Adaptive execution." | Void → a sentence that ties the empty map to the adaptive story. |
| Q5 | P3 | Adaptive-execution panel repeated an "OBSERVATION" kicker for every step (8×) — noisy, and for CASE A (no replans) it duplicated the plan. | Restructured: when there are replans, the **DECISION** events are prominent and the plain observations collapse into a `<details>`; when there are none, a one-line "no replans — every step ran" note + a compact observation list. | 8 stacked kickers → 2 decision cards (CASE B) / 1 note + list (CASE A). |
| Q6 | P3 | Dead `GROUNDING` layer toggle in geometry mode — the flagship's grounded box has no lon/lat, only pixels, so the toggle controlled nothing. | The `GROUNDING` layer button is only shown when there is raster imagery or a lon/lat grounding box. The pixel-only grounded box still appears in Findings + Spatial findings. | Non-functional control removed from the geo view. |
| Q7 | P3 | `RESET` in the viewer header did nothing distinct from `FIT`. | `RESET` now restores all layer toggles to on and re-fits; `FIT` re-fits the current layers. | Both header buttons have a real function. |
| Q8 | P3 | Landing hero had a large empty lower half. | Added a centred, non-interactive capability chip row (Bi-temporal change · Optical + SAR · Text-guided grounding · Scene & VQA). | Balanced hero; still restrained. |

## Verified good (no change needed)

- **Map is the visual centrepiece.** On CASE A the EPSG:4326 plot of the six
  changed regions with lon/lat axis labels dominates the viewport at both
  resolutions.
- **CASE A vs CASE B is obvious**: 4 tool calls / not-early-stopped / HIGH
  with a populated map, vs 2 tool calls / "stopped early" / MEDIUM with an
  explained empty map and a visible `NEW_EVIDENCE` + `TOOL_FAILURE` timeline.
- **Trust** is a large category chip (HIGH green / MEDIUM amber /
  INSUFFICIENT_EVIDENCE red) with a ✓/• "why" checklist; the "NOT a probability
  or a score" caveat sits next to it; the internal `score` is never rendered.
- **Verification** groups the real checks into Structural / Geospatial / Evidence
  with their real `detail` strings; nothing is force-green (CASE B shows the
  aggregate honestly).
- **Warnings** render verbatim from `warnings[]` / `failures[]`; standing caveats
  (RemoteSAM licence) use the muted note style, real failures the red style.
- **Error state** reads as a designed panel — REASON / RESOLUTION — not a stack
  trace.
- **Loading state** says what is happening ("executing specialist models on CPU …
  up to ~90 seconds") with a real elapsed timer and **no fake percentage or
  progress bar**.
- **ASK** stays a single simple column; the grounding box is drawn on the real
  scene image; the model score is labelled "raw model score, NOT a calibrated
  confidence".
- **Responsive**: 3-column workspace at ≥ 1240 px (350 / 1fr / 380); single
  column stack (viewer → mission → findings → …) below that. 1366×768 holds the
  3-column layout without overflow.
- **No forbidden wording** anywhere in the served page (`test_g20_ui.py`).
- **Accessibility**: `:focus-visible` ring, `prefers-reduced-motion` disables the
  spinner and all transitions, `role="status"` / `role="alert"` on the live
  regions, `aria-pressed` on layer toggles, `alt` text on the viewer image,
  status conveyed by glyph **and** colour.

## Known limitations (acceptable for G20)

- **No live per-step progress.** `/investigate` is a single response, so the
  plan shows pending until it returns — the loading panel says so explicitly
  rather than animate a fake sequence. (P3 — honest by design.)
- **GeoTIFF imagery is not shown inline** — the centre view plots the derived
  EPSG:4326 geometry instead, captioned "source imagery is GeoTIFF — not shown
  inline". A raster base layer appears only when an input is PNG/JPEG (ASK
  grounding demo). (P3 — no fabricated imagery.)
- The geometry plot is a static SVG (layer toggles + fit/reset); there is no
  pan/pinch zoom. (P3 — out of scope; Part 10 says "do not add unnecessary GIS
  complexity".)
