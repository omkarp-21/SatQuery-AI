# G20.1 — Visual QA

> The four investigation states, reviewed as a non-technical judge at 1920×1080.
> Screenshots in `docs/sih/evidence/ui/`. **BLOCKED** and **SUCCESS** were
> captured from **live runs** through the real backend; **PARTIAL** and
> **FAILED** were rendered from constructed result objects through the shipped
> render code (the panels are identical to the live paths, exercised by
> `test_g20_1_status.py`).

The 5-second questions (Part 22): *What happened? · Can I see the evidence? · Do I
know what to do next?*

---

## BLOCKED — `g20_1_blocked.png` (live: two 483×676 / 478×667 GeoTIFFs)

| element | shows |
|---|---|
| Banner | **INVESTIGATION · BLOCKED · "The two observations are not spatially co-registered."** (amber, left-rule) |
| Centre | **⊘ Spatial comparison unavailable** — the input rasters are **not** shown as a result |
| Findings | "No validated finding is available. **Why:** …not co-registered. **Technical detail:** T1 grid 483×676 / T2 grid 478×667" |
| What happened | Completed ✓ Validate imagery · Could not complete ✕ Compare temporal imagery · **How to fix this:** "Provide two observations aligned to the same CRS, transform, and raster grid." |
| Verification | *(of the evidence, not the outcome)* — **NOT APPLICABLE** — "No analytical conclusion was produced, so there is nothing to verify." |
| Confidence | **INSUFFICIENT EVIDENCE** |
| Warnings | the raw co-registration messages, verbatim |

*What happened?* → the two images aren't aligned, so the comparison was refused.
*Evidence?* → none, correctly (nothing was produced). *Next?* → the "How to fix"
line. **Passes.** No "N step(s) failed", no "Verification: SUPPORTED", no map.

## SUCCESS (early stop) — `g20_1_success.png` (live: CASE B, no-change pair)

| element | shows |
|---|---|
| Banner | **INVESTIGATION · SUCCESS · "no significant temporal change detected"** (green) |
| Findings | 0.0 % scene changed · 0.000 ha · "No significant change (below the 1 % threshold)" |
| What happened | Completed ✓ Validate / Compare temporal · Could not complete ✕ Extract changed regions / Locate structures (skipped) |
| Adaptive execution | plain language — "Observation: changed_fraction 0.0 → Decision: No significant change was found, so the localisation steps were not needed → Outcome: 2 downstream steps skipped … Investigation stopped early". Enum names (`NEW_EVIDENCE`, `TOOL_FAILURE`) are only inside "Step-by-step observations & internal codes". |
| Verification | **SUPPORTED** — *"checks on the evidence that was produced — not a success signal."* |
| Confidence | **MEDIUM** — "Capped at MEDIUM: only one specialist ran, no cross-check." |

**Passes.** The early stop reads as a decision, not a failure.

## SUCCESS (full) — CASE A (regenerated capture `flagship_caseA_change.json`)

`investigation_status = SUCCESS`, `ok = true`, conclusion *"~25.3 % of the scene
changed, 6 changed region(s) isolated, 1 structure region(s) located, optical+SAR
representation computed."* — no "Verification: SUPPORTED" suffix, no failure
count. Banner green, map of 6 regions, confidence HIGH, verification SUPPORTED.

## PARTIAL — `g20_1_partial.png` (constructed: temporal OK, grounding failed)

| element | shows |
|---|---|
| Banner | **INVESTIGATION · PARTIAL · "Completed: compare temporal imagery, extract changed regions. Could not complete: locate affected structures."** (amber) |
| Centre | the **valid** output only — the 6-region map; no fabricated grounding box |
| What happened | Completed ✓✓✓ · Could not complete ✕ Locate affected structures |
| Adaptive execution | "Observation: Locate affected structures → Decision: A step produced nothing usable, so no result was asserted from it." |
| Confidence | **MEDIUM** — reasons name the failed step |

**Passes.** The user knows exactly what succeeded and what didn't (Part 11).

## FAILED — `g20_1_failed.png` (constructed: services unavailable)

| element | shows |
|---|---|
| Banner | **INVESTIGATION · FAILED · "Neither the agent plan nor the deterministic fallback path could complete."** (red) |
| Centre | **⊘ Spatial comparison unavailable** |
| Findings | "No validated finding is available. Why: …" |
| Confidence | **INSUFFICIENT EVIDENCE** |
| Verification | *(of the evidence, not the outcome)* — INSUFFICIENT_EVIDENCE |

**Passes.** Reads as an intentional error state, not a crash.

---

## Issues found & fixed during the pass

| sev | issue | fix |
|-----|-------|-----|
| P1 | co-reg failure rendered "2 step(s) failed. Verification: SUPPORTED." + input image as a result | new `investigation_status` hierarchy; BLOCKED banner; verification `NOT_APPLICABLE`; centre "Spatial comparison unavailable" |
| P2 | fallback/plan-rejected path classified as generic FAILED with no step view | `_deterministic_fallback` now classifies pre-condition problems as BLOCKED and synthesises a minimal step view (Completed / Could not complete) |
| P2 | `Understood as: unknown` on the fallback path | `missionPanel` derives the label from the plan's specialist tasks when `intent` / `mission_family` are absent |
| P3 | adaptive panel surfaced raw enum names (`TOOL_FAILURE`, `NEW_EVIDENCE`) in the primary view | `_REASON_PLAIN` map; enum names only in the "internal codes" `<details>` |
| P3 | fallback confidence "why" leaked `PLAN_REJECTED` | plain-language mapping for the fallback reason |
| P3 | `t1_shape`/`t2_shape` unavailable when the plan is rejected before execution | UI parses `NNNxNNN vs NNNxNNN` out of the warnings as a fallback |

## Responsive

3-column workspace at ≥ 1240 px; single-column stack below. Verified at 1920×1080
(all four states) and 1366×768 (BLOCKED, SUCCESS). The bottom row (`What happened`
/ Adaptive / Evidence / Warnings / Report) is full-width and stacks cleanly.
Known cosmetic: on a short right column the centre area has whitespace above the
bottom row — content is complete and readable; not a blocker.
