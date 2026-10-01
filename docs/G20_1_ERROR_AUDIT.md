# G20.1 — Error Audit: "primary failed, but Verification: SUPPORTED"

> Triggered by a real live test: two observations with different raster grids
> (**T1 483×676, T2 478×667**) — genuinely **not co-registered**. The temporal
> pipeline correctly refused to run change detection. But the UI showed
> **"2 step(s) failed. Verification: SUPPORTED."** and a headline **"Overall:
> SUPPORTED"**, plus an input image that looked like a result. This document
> traces exactly why.

## Response path

```
GeoTIFF validation      packages/geospatial · validate_geotiff  -> both files individually valid  -> SUPPORTED
  ↓
pair compatibility      app/services/temporal_slice.check_pair_compatibility  -> pair.co_registered = False
  ↓
run_change_slice        strict=True + errors  -> returns ChangeSliceResult(ok=False, errors=[...], verification=None)
run_change_fallback     also strict on co-registration  -> ChangeSliceResult(ok=False, ... verification not set)
  ↓
_tool_temporal          payload = r.model_dump()  (ok=False, verification=None)
  ↓
executor                ok = payload["ok"] = False  -> obs.status="failed", mem.failures.append("s2 (run_temporal_change): ...")
                        v = out["verification"] = None  -> NOTHING appended to mem.verification_statuses
                        TOOL_FAILURE replan  -> downstream steps skipped (some marked failed, e.g. extract_changed_regions)
  ↓
_tool_verify            statuses = mem.verification_statuses = ["SUPPORTED"]   ← only the validate step
                        contradicted = False ; supported = 1
                        overall = "SUPPORTED"                                   ← ROOT CAUSE
  ↓
_synthesize             res.verification = {"status": "SUPPORTED", ...}
                        parts = ["2 step(s) failed"]   (from res.failures)
                        res.conclusion = "2 step(s) failed. Verification: SUPPORTED."
                        res.confidence = INSUFFICIENT_EVIDENCE  (trust.py hard rule fires — this part is CORRECT)
  ↓
res.ok                  res.verification["status"] != "CONTRADICTED" and tool_calls > 0  -> res.ok = True   ← WRONG
  ↓
/investigate -> AgentInvestigationResult -> UI
UI                      renders verification.status as "Overall: SUPPORTED" headline
                        renders res.conclusion verbatim
                        renders the first input raster as the "Spatial view"        ← misleading
```

## Root cause

**The verification aggregate answers the wrong question.** `_tool_verify`
(`apps/backend/app/services/agent_runner.py`) computes:

```python
statuses = [s for s in mem.verification_statuses if s]     # only steps that RETURNED a verification dict
overall  = "CONTRADICTED" if "CONTRADICTED" in statuses else ("SUPPORTED" if statuses.count("SUPPORTED") else "INSUFFICIENT_EVIDENCE")
```

Two compounding problems:

1. **A failed primary specialist is invisible to the aggregate.** On a
   co-registration failure `run_change_slice` returns `verification=None`, so the
   executor appends nothing to `mem.verification_statuses`. The failure is
   recorded in `mem.failures`, which the aggregate never consults.
2. **`validate_geospatial_input` contributes a `SUPPORTED` status.** Input
   validation is a *pre-condition*, not evidence for the requested conclusion —
   yet its `SUPPORTED` is enough to make the aggregate `SUPPORTED` all by itself.

So the aggregate says "some structural check somewhere passed", the UI reads it
as "the investigation succeeded", and the two get conflated.

**There is no top-level investigation-status concept.** The response carries
`ok` (bool), `verification.status`, `confidence.category`, `resolution.qualifier`,
`phase`, `early_stopped` — none of which answers *"did the analysis the user
asked for actually get done?"*. `ok` is derived from `verification.status` alone,
so a blocked primary leaves `ok = True`.

## Classification

| candidate | verdict |
|-----------|---------|
| verification semantics | **YES** — the aggregate conflates "a check passed" with "the investigation succeeded" |
| aggregation bug | **YES** — a failed primary / pre-condition failure is not reflected in `overall` |
| resolution bug | partial — `resolution.qualifier` becomes `RESULT_OK` off the wrong aggregate |
| UI rendering bug | **YES (secondary)** — the UI promotes `verification.status` to a headline and shows an input raster as a "result" on a blocked run |
| expected behavior, badly labelled | **YES** — the *refusal* to run change detection is correct and must stay; only the labelling/summary is wrong |

It is **not** a geospatial-safety regression: the pipeline correctly blocked
unsafe change detection. Nothing was fabricated. The confidence layer already
returns `INSUFFICIENT_EVIDENCE` with the hard rule *"the primary specialist for a
temporal mission did not complete"* — that part was right.

## Affected components

| component | file | issue |
|-----------|------|-------|
| verification aggregate | `apps/backend/app/services/agent_runner.py` · `_tool_verify` | counts `validate_geospatial_input`; ignores `mem.failures` |
| investigation-level status | `apps/backend/app/services/agent_runner.py` · `_synthesize` | no `investigation_status`; `res.ok` derived from verification only |
| conclusion text | `_synthesize` | `"N step(s) failed. Verification: <status>."` — developer phrasing |
| HTML report | `apps/backend/app/services/report.py` | leads with `Verification: SUPPORTED` |
| UI | `apps/backend/app/static/index.html` | verification headline; input raster shown on blocked runs; enum names surfaced |

## Correct behavior

1. **A new derived, additive field `investigation_status ∈ {SUCCESS, PARTIAL,
   BLOCKED, FAILED}`** (+ `investigation_status_reason`), computed by a pure
   function from the existing `steps` / `replans` / `failures` / `plan` — no new
   pipeline stage, no model change.
   - **BLOCKED** — the anchor specialist for the mission family
     (`run_temporal_change` / `run_semantic_temporal_baseline` /
     `run_optical_sar`, or the sole single-image specialist) failed on an input
     pre-condition (co-registration, CRS/transform mismatch, unreadable raster,
     incompatible grid, missing required modality) and no substantive specialist
     result was produced.
   - **FAILED** — the agent itself could not run (planner unavailable + fallback
     also failed, `verification == CONTRADICTED`, or 0 specialist calls on a
     real plan).
   - **PARTIAL** — at least one specialist produced a usable result **and** at
     least one planned specialist failed / was pruned by a failure (not by a
     legitimate early stop).
   - **SUCCESS** — every planned specialist completed with a non-disputed
     verdict, **or** a legitimate early stop (`NEW_EVIDENCE` for negligible
     change, `TASK_COMPLETE`) where stopping was an *observation*, not a failure.
     (This is CASE B: temporal ran, saw ~0 change, stopped early → SUCCESS with
     an "early stop" note, even though `extract_changed_regions` is marked
     failed as a downstream consequence.)
2. **`res.ok = investigation_status in {SUCCESS, PARTIAL}`** (BLOCKED / FAILED →
   `ok = False`), keeping the `CONTRADICTED` guard.
3. **Verification stays a separate concept.** When `investigation_status ==
   BLOCKED` the verification aggregate is reported as **`NOT_APPLICABLE`** with a
   note "no temporal conclusion was produced to verify" — it is dishonest to
   report `SUPPORTED` for an analysis that never ran. When `PARTIAL`, verification
   reflects only the checks that *did* run.
4. **`_tool_verify` aggregate no longer counts `validate_geospatial_input`, and
   downgrades to `INSUFFICIENT_EVIDENCE` when a specialist failed and no
   substantive specialist result is `SUPPORTED`.**
5. **Human-readable conclusion per status class** — "Temporal comparison
   unavailable — the two observations are not spatially co-registered." etc.
6. **UI**: `investigation_status` is the headline; verification is a secondary
   line; on BLOCKED the centre shows *"Spatial comparison unavailable"*, never an
   input raster dressed as a result; plan / adaptive execution use plain
   language and hide enum names behind "details".
7. **Report** leads with `Investigation status: BLOCKED` + reason; verification
   reads "No temporal conclusion was verified."

## Not changing

- The geospatial-safety refusal (`strict=True` co-registration assert). **No
  silent resample / reproject.** An explicit `[ALIGN IMAGERY]` workflow is a
  future item, not this patch.
- Model stack, routing, evidence contract, claim wording, the confidence
  category rules (already correct here).
