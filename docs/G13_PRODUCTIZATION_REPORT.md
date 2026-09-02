# G13 — Productization Report

> Goal: **make SatQuery work as one coherent product** — a teammate or judge can
> run it locally, upload imagery, ask a question, and get a spatially-grounded,
> verified, evidence-backed answer. No new models, no architecture redesign, no
> confidence values, no removed caveats.
> Date: **2026-09-02**. Branch: `docs/lightweight-model-audit`.

---

## 1. Before vs after

| | Before G13 | After G13 |
|--|-----------|-----------|
| Entry point | `POST /analyze` returning `AnalyzeResult` with `result` = raw per-specialist dict (6 different shapes) | `POST /analyze/upload` (multipart) → **one flat `NormalizedResponse`**; `POST /analyze` still there |
| Input | file **paths under `data/`** only | **file upload** (1–2 files, sandboxed `data/uploads/<id>/`) |
| UI | `apps/frontend/src/` = empty `.gitkeep`s, no `node_modules` | **self-contained `GET /`** page (vanilla JS + `<canvas>` overlay), served by FastAPI, **no build step** |
| Artifacts (masks) | written to scattered temp dirs, unreachable by a client | copied into the request sandbox, served by `GET /artifact?req=&name=` |
| Optical+SAR via `/analyze` | half-wired (`.npy` only; picked `paths[0]` as optical) | **paired GeoTIFF S2+S1 → CROMA** via `run_joint_from_geotiffs` |
| Ungeoreferenced GeoTIFF | `read_raster_meta` raised → **HTTP 500** on a corrupt file; a CRS-less tile was fully blocked | corrupt → clean `VALIDATION_FAILED`; CRS-less-but-sound tile → pixel-level analysis with an explicit "no geographic coordinates" flag |
| Demo runner | `scripts/demo/run_demo.sh` = `echo "not implemented"` | `scripts/demo/run_demos.py` — 5 real scenarios → real captures in `docs/sih/evidence/demos/` |
| Tests | 166 collected | **166 + 17 G13 integration** (12 fast always-run + 5 slow real-model) |

## 2. Implemented components

| Component | File | What it does |
|-----------|------|--------------|
| `NormalizedResponse` + `normalize()` | `apps/backend/app/services/normalize.py` | flattens any of the 6 specialist outputs into one schema — `answer, model_used, latency_s, yesno, labels, boxes, regions, mask_url, image_dimensions, changed_fraction, area_ha, centroid_lonlat, representation_dim, score(+meaning), crs, geospatial_available/note, evidence, verification, resolution, provenance, execution_trace, failures, warnings`. Only relevant fields populated; **nothing invented**; caveats pushed into `warnings`. |
| Product API | `apps/backend/app/api/product.py` | `GET /` (UI), `POST /analyze/upload` (multipart, per-request sandbox, 64 MB/file cap, type allow-list), `GET /artifact` (sandboxed). Wired in `app/main.py`. |
| Local UI | `apps/backend/app/static/index.html` | upload + query console, example queries, result panel (answer/task/model/latency), image preview with box/region overlay on `<canvas>`, mask link, zero-shot ranking table, changed-regions table, evidence (collapsible), verification checks, failure-aware resolution, execution trace, provenance. Loading + error + empty states. |
| Optical+SAR from GeoTIFFs | `apps/backend/app/services/multimodal_slice.py::run_joint_from_geotiffs` | reads S2 (≥12 band) + S1 (2 band), selects the 12 CROMA bands, nearest-resizes to 120, writes temp `.npy`, defers to `run_joint_representation`. SAR kept as backscatter, never RGB. |
| Geo carve-out | `apps/backend/app/services/analyze.py` | a GeoTIFF whose *only* validation failures are `{transform_valid, bounds, crs_present}` is allowed for pixel-level analysis with a non-blocking `geo_warnings` entry; hard failures (unreadable/dimensions/bands/nodata) still block; unreadable rasters now caught → `VALIDATION_FAILED` not 500. |
| `artifact_dir` threading | `analyze.py` → `run_grounding` / `run_change_slice` / `run_change_fallback` / `run_composed_semantic_change` | lets the upload endpoint collect masks; additive param, default unchanged. |
| Demo runner | `scripts/demo/run_demos.py` | 5 deterministic scenarios through the real pipeline → prints a summary + writes `docs/sih/evidence/demos/g13_demo*.json`. BLOCKED/ERROR recorded honestly. |
| Integration tests | `apps/backend/tests/test_g13_integration.py` | the 15 required cases + upload-endpoint + UI-served + doc-exists. |
| Dependency | `apps/backend/pyproject.toml` | `python-multipart>=0.0.9` — required for multipart form parsing (file upload). One line, justified inline. |

## 3. API changes

- **New:** `GET /`, `POST /analyze/upload`, `GET /artifact` (see `docs/API_CONTRACT.md`).
- **Unchanged:** `GET /health`, `POST /analyze`, `POST /change`, `POST /scene` —
  same request/response, no behaviour change. `AnalyzeResult` gained an additive
  `geo_warnings: list[str]` field.
- **No** LLM planner. **No** confidence value anywhere.

## 4. UI changes

New `apps/backend/app/static/index.html` (≈ 320 lines, one file, no framework).
Left: query console + frozen-stack reference. Right: result, failure-aware
resolution, warnings/caveats, map/image with overlay, ranking/regions tables,
evidence, verification, execution trace, provenance. Theme-neutral dark palette,
system fonts, monospace for technical panels. `apps/frontend/` (the React
skeleton) is untouched and unused — the brief called for "the simplest reliable
stack already present"; FastAPI serving one static file needs zero new tooling.

## 5. Integration flow (unchanged spine, now end-to-end)

```
UPLOAD (1-2 files) + QUERY
  -> sandbox save (data/uploads/<id>/)
  -> run_analyze:
       validate_geotiff + check_pair_compatibility   (safeguards preserved)
       interpret_query   (deterministic keyword -> intent, NO LLM)
       route()           (deterministic, registry-driven)
       specialist        (SpecialistAdapter, subprocess-isolated .venvs/<model>)
       EvidenceItem + Provenance + verify()
       derive_resolution()   (6 qualifiers; failure-aware)
  -> normalize()  -> NormalizedResponse
  -> copy mask into sandbox, rewrite mask_url
```

## 6. Demo scenarios (real captures — `docs/sih/evidence/demos/`)

| # | Query | Task → model | Result (see the JSON capture) |
|---|-------|--------------|-------------------------------|
| 1 | "What objects are visible in this satellite image?" | `SINGLE_IMAGE_VQA` → TinyRS-2B | text answer, `evidence:[vqa]`, `verification`, `resolution`; `score:null` (greedy, no confidence) |
| 2 | "Where is the largest building?" | `SINGLE_IMAGE_GROUNDING` → RemoteSAM | box (or explicit no-region), mask PNG, `evidence:[grounding]`; warning: RemoteSAM licence NOT STATED |
| 3 | "What changed between these two images?" | `TEMPORAL` → ChangeFormer | `changed_fraction`, `area_ha`, `centroid_lonlat` (CRS EPSG:32650 preserved), change mask, `evidence:[change-mask]` |
| 4 | "Compare the optical and SAR information for this area." | `MULTIMODAL_REPR` → CROMA | dim-768 joint representation, `evidence:[embedding]`, `geospatial_available:false` (DFC tiles ungeoreferenced), warning: representation-level only |
| 5 | "Describe what changed and where, with supporting evidence." | composed semantic baseline (ChangeFormer + RemoteCLIP) | rule-assembled description + changed regions + per-region tags; warning: EXPERIMENTAL SEMANTIC BASELINE |

## 7. Latency (measured 2026-09-02, this host — ASUS Zephyrus G14, CPU-only, cold start includes model load)

From `scripts/demo/run_demos.py` (real end-to-end, `run_analyze` + `normalize`):

| Demo | Task → model | Cold end-to-end (s) | Notes |
|------|--------------|--------------------:|-------|
| 1 | VQA → TinyRS-2B | **26.7** | subprocess load of Qwen2-VL-2B fp32 dominates |
| 2 | Grounding → RemoteSAM | **29.0** | Swin-B + BERT load + 896² inference |
| 3 | Temporal → ChangeFormer | **8.1** | 256² pair |
| 4 | Optical+SAR → CROMA | **6.3** | 2× GeoTIFF read + 120² joint encode |
| 5 | Investigation → ChangeFormer + RemoteCLIP ×6 regions | **44.9** | mask + 6 region crops each tagged by RemoteCLIP |

- **Cold start** = the whole cost above (each specialist is a fresh subprocess).
  **Warm inference** is not separately cached in this build — every `/analyze`
  call is a cold start by design (nothing resident). Earlier per-model warm
  numbers (RemoteCLIP ~150 ms, ChangeFormer ~790 ms, CROMA ~340 ms, DOFA ~120 ms,
  TinyRS p50 ~4.5 s, RemoteSAM p50 ~29 s) are in `PROJECT_STATUS.md` METRICS.
- **Total endpoint latency** ≈ the demo latency + upload save (< 50 ms for these
  fixture sizes) + `normalize` (< 5 ms).
- **Failures observed:** none in the 5-demo run (5/5 ok). The corrupt-GeoTIFF 500
  and the CRS-less-tile block were caught by integration tests and fixed.

Premature optimization was not done — the bottleneck is model **load**, which a
warm-process pool would fix, but that trades the "nothing resident" property the
4 GB target needs. Left as a documented tradeoff.

## 8. Memory

All specialists run CPU-only in isolated subprocesses that exit after each call —
**nothing stays resident**; peak RSS is one model at a time. Observed per-model
peak RSS (from EXP-002 / EXP-004 / G11): TinyRS ≈ 9 GB (fp32), RemoteSAM ≈ 6 GB,
ChangeFormer < 1.5 GB, RemoteCLIP < 1 GB, CROMA ≈ 1.5 GB. **No VRAM figure —
there is no CUDA torch on this host. 4 GB-VRAM fit is UNVERIFIED.**

## 9. Test counts

| Suite | Count | Status |
|-------|------:|--------|
| Fast (`-m "not slow"`), packages + backend | **153** | pass, 0 regressions (was 141 at G12) |
| G13 integration, fast subset | 12 | pass |
| G13 integration, slow (real models) | 5 | pass |
| G13 integration, total | 17 | — |
| Grand total collected | **183** | — |

## 10. Failures / bugs found and fixed

- **`/analyze` 500 on a corrupt GeoTIFF** — `validate_geotiff` → `read_raster_meta`
  raised `UnreadableRasterError` uncaught. Fixed: caught in `run_analyze` →
  `VALIDATION_FAILED`. (Found by integration test case 9.)
- **CRS-less GeoTIFF fully blocked** — DFC2020 release tiles carry a CRS tag but an
  identity transform, so every optical+SAR input failed the gate. Fixed with the
  narrow geo carve-out (pixel-level analysis + explicit "no geographic
  coordinates"; hard failures still block).

## 11. Known limitations (preserved, not hidden)

- Evaluation samples are **sanity-scale** (VQA n=40, grounding n=25, optical+SAR
  n=200, adaptation n=200).
- CROMA optical+SAR delta is **not significance-tested** (+0.067 macro-F1, 95% CI
  includes 0).
- LoRA adaptation gain is **not significance-tested** (+0.061, n=200).
- **4 GB VRAM is UNVERIFIED** — CPU-only host, no VRAM measurement exists.
- **RemoteSAM licence: NOT STATED** — surfaced as a warning on every grounding response.
- **No confidence value** is produced anywhere (by design).
- **No learned temporal semantic VLM** — capability C language path is a composed,
  disclaimed baseline.
- **LoRA adapter is not persisted into production** — the production optical+SAR
  encoder is the frozen CROMA; the adapted variant is a measured experiment.

## 12. Exact commands

**Launch:**
```bash
cd apps/backend
../../.venvs/satquery/Scripts/python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
# UI:   http://127.0.0.1:8000/
# docs: http://127.0.0.1:8000/docs
```

**Run demos:**
```bash
.venvs/satquery/Scripts/python.exe scripts/demo/run_demos.py            # all 5
.venvs/satquery/Scripts/python.exe scripts/demo/run_demos.py --demo 1   # VQA
.venvs/satquery/Scripts/python.exe scripts/demo/run_demos.py --demo 2   # grounding
.venvs/satquery/Scripts/python.exe scripts/demo/run_demos.py --demo 3   # temporal
.venvs/satquery/Scripts/python.exe scripts/demo/run_demos.py --demo 4   # optical+SAR
.venvs/satquery/Scripts/python.exe scripts/demo/run_demos.py --demo 5   # investigation
```

**Tests:**
```bash
.venvs/satquery/Scripts/python.exe -m pytest packages apps/backend -q -m "not slow"
.venvs/satquery/Scripts/python.exe -m pytest apps/backend/tests/test_g13_integration.py -q -m slow
```

## 13. Definition of Done

| Item | Status |
|------|:------:|
| user can launch SatQuery locally | ✅ `uvicorn app.main:app` |
| user can upload imagery | ✅ `POST /analyze/upload`, UI file picker |
| user can enter a natural-language query | ✅ |
| query is interpreted | ✅ deterministic `interpret_query` |
| correct specialist is selected | ✅ deterministic `route()` |
| specialist executes | ✅ all 5 real models, slow tests pass |
| result is normalized | ✅ `NormalizedResponse` |
| geospatial outputs appear when valid | ✅ centroid/bbox lon-lat on temporal; explicit "unavailable" otherwise |
| evidence appears | ✅ `evidence[]` in every response |
| verification appears | ✅ `verification` in every executed response |
| provenance appears | ✅ `provenance` (layer=analyze, routing, sub-service) |
| failures are handled | ✅ `resolution` + `warnings`/`failures`; corrupt-file 500 fixed |
| UI works end-to-end | ✅ `GET /` served + rendered; slow tests exercise every path |
| all existing tests pass | ✅ 153 fast, 0 regressions |
| new integration tests pass | ✅ 12 fast + 5 slow |
| demo fixtures work | ✅ `scripts/demo/run_demos.py`, real captures |
| README has exact run instructions | ✅ |
| no fake metrics | ✅ |
| no new model dependencies | ✅ (only `python-multipart`, a web dep for upload) |
| no architecture regression | ✅ spine unchanged; additive fields/params only |
