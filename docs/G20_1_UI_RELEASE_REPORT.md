# G20.1 — Error Handling + UI Simplification — Release Report

> Fixes the "primary failed, but Verification: SUPPORTED" defect
> (`docs/G20_1_ERROR_AUDIT.md`) and rebuilds the investigation result UI around a
> calm, semantically-correct status hierarchy. No model / routing / claim change;
> the geospatial-safety refusal of misregistered pairs is **kept** (no silent
> resample). Companion: `docs/G20_1_ERROR_AUDIT.md`, `docs/G20_1_VISUAL_QA.md`.

## The bug, in one line

The verification aggregate answered *"did some check pass?"* — not *"did the
investigation succeed?"* — and there was no top-level status to tell them apart.
A co-registration failure therefore rendered as **"2 step(s) failed.
Verification: SUPPORTED."** with an apparently-successful map.

## Backend changes (additive, backward-compatible — no pipeline / model change)

| # | Change | File |
|---|--------|------|
| 1 | **New derived field `investigation_status ∈ {SUCCESS, PARTIAL, BLOCKED, FAILED}`** + `investigation_status_reason` (one human sentence). Computed by the pure function `derive_investigation_status(res, mem, plan)` from the observed steps / replans / failures. | `agent_runner.py`, `schemas.py` |
| 2 | `res.ok = investigation_status in {SUCCESS, PARTIAL}` — a BLOCKED / FAILED run is no longer "ok" just because a structural check passed. | `agent_runner.py` |
| 3 | Verification aggregate (`_tool_verify`) no longer counts the `validate_geospatial_input` pre-condition, and downgrades to `INSUFFICIENT_EVIDENCE` when a specialist failed and no substantive specialist is `SUPPORTED`. | `agent_runner.py` |
| 4 | On BLOCKED, `res.verification.status` is reported as **`NOT_APPLICABLE`** with the note *"no analytical conclusion was produced to verify"*. | `agent_runner.py` |
| 5 | **Human-readable conclusion per status class** — "Analysis could not be completed. The two observations are not spatially co-registered." / "No significant change was detected …" — never *"N step(s) failed. Verification: X."* | `agent_runner.py` |
| 6 | The deterministic-fallback path (plan rejected on a misregistered pair) now classifies as **BLOCKED** (pre-condition), not FAILED, and synthesises a minimal step view so the UI can show *what completed vs what could not*. T1 / T2 grid shapes are surfaced on the failed temporal step. Enum reason names in the fallback confidence "why" are plain-language. | `agent_runner.py` |
| 7 | HTML report leads with **Investigation status: BLOCKED** + reason; the Verification section reads *"No analytical conclusion was produced, so there is nothing to verify."* — never SUPPORTED-as-success. | `report.py` |
| 8 | `AgentPhase` gains `"BLOCKED"`. | `schemas.py` |

## UI changes (`apps/backend/app/static/index.html` — one file, no build step)

- **Status banner** is the primary element: `INVESTIGATION · <STATUS> · <one
  sentence>`, colour-coded (SUCCESS green / PARTIAL amber / BLOCKED amber /
  FAILED red).
- **Verification is demoted** to a compact line titled *"Verification (of the
  evidence, not the outcome)"*; on BLOCKED it shows **NOT APPLICABLE** with the
  reason. The full checks are behind a `<details>`.
- **The map is never misleading**: on BLOCKED / FAILED the centre shows *"⊘
  Spatial comparison unavailable"* + the reason — the input raster is not shown
  as a result.
- **Findings** are status-aware: BLOCKED → *"No validated finding is available.
  Why: … Technical detail: T1 grid 483×676 / T2 grid 478×667"*.
- **"What happened"** panel: Completed ✓ / Could not complete ✕ / How to fix this.
- **Plan** is compact plain-language rows (*Validate imagery · Compare temporal
  imagery · …*); a failed step gets a **"why ▾"** toggle with the reason.
- **Adaptive execution** uses plain sentences; the enum names (`TOOL_FAILURE`,
  `NEW_EVIDENCE`, …) live only inside a "details" table.
- **Confidence** panel unchanged in intent — a category with a "why", never a
  number; on BLOCKED it is **INSUFFICIENT EVIDENCE**.
- Copy: "Investigation status", "What happened", "How to fix this", "Could not
  complete" replace "steps failed", "tool failure", "resolution.qualifier".
- Status hierarchy is explicit and never mixed: **SYSTEM** (READY) ·
  **INVESTIGATION** (SUCCESS/PARTIAL/BLOCKED/FAILED) · **VERIFICATION**
  (SUPPORTED/NOT APPLICABLE/…) · **CONFIDENCE** (HIGH/…/INSUFFICIENT EVIDENCE).

## What is NOT changed

- No silent resample / reproject of misregistered pairs. The `strict=True`
  co-registration assert stays. An `[ALIGN IMAGERY]` workflow is a future item.
- Model stack, routing, evidence contract, claim wording, the confidence
  category rules.
- CASE A / CASE B behaviour: both still **SUCCESS** (A: 4 tool calls, HIGH;
  B: 2 calls, early stop, MEDIUM, no fabricated change) — verified.

## Tests

| suite | result |
|-------|--------|
| `test_g20_1_status.py` (new, 11) | co-reg failure → BLOCKED, `ok=False`, verification ≠ SUPPORTED, confidence INSUFFICIENT_EVIDENCE, human-readable conclusion, no fabricated geometry, report leads with status; + unit tests of `derive_investigation_status` for SUCCESS / early-stop-SUCCESS / PARTIAL / FAILED |
| `test_g20_ui.py` (+4 → 40) | four statuses referenced; "Verification (of the evidence, not the outcome)"; "Spatial comparison unavailable"; "NOT APPLICABLE"; `_REASON_PLAIN` mapping; `investigation_status` / `investigation_status_reason` read from the response |
| `test_g18_failure_matrix.py` | `_assert_agent_ok` updated to accept the BLOCKED phase and to assert a BLOCKED/FAILED run is never `ok` and never SUPPORTED |
| full fast suite (`-m "not slow and not gpu and not integration"`) | **434 passed, 0 failed, 0 regressions** (419 pre-G20.1 + 11 status + 4 UI) |
| agent suites g14–g18 (slow) | green — `_assert_agent_ok` updated for the BLOCKED phase |

## The 5-second test (Part 22 / final criterion)

**BLOCKED** — a non-technical judge sees: *"BLOCKED — the two satellite images
are not spatially aligned, so SatQuery refused to compare them. Nothing was
fabricated. Provide aligned imagery."* — in the banner + the "How to fix this"
line, with a *"Spatial comparison unavailable"* centre and a *Completed ✓ /
Could not complete ✕* summary.

**SUCCESS** — *"SatQuery found these changes, here is where they are, here is the
evidence, and the result is trusted (HIGH)."* — banner + findings metrics + map +
confidence.
