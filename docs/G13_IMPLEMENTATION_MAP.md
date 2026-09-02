# G13 — Implementation Map (Step 1 audit)

Audit of the backend **before** G13. `existing → missing → to integrate`. No
functionality is duplicated; G13 wires the existing pieces into one product +
adds a UI, a normalized response, upload, and demos.

## EXISTING (working — keep, do not rebuild)

| Area | What's there | File(s) |
|------|--------------|---------|
| **API** | `GET /health`; `POST /change` → `ChangeSliceResult`; `POST /scene` → `SceneResult`; `POST /analyze` → `AnalyzeResult` | `apps/backend/app/api/{change,scene,analyze}.py`, `app/main.py` |
| **Unified orchestrator** | `run_analyze()` — validate → `interpret_query()` (deterministic keyword→intent) → `route()` → dispatch 6 codes → aggregate evidence + verification + provenance + `resolution` | `app/services/analyze.py` |
| **Deterministic router** | `route(RoutingRequest) → RoutingDecision`; reads capabilities from `model_registry.yaml`; codes `TEMPORAL / MULTIMODAL_REPR / SINGLE_IMAGE_SCENE / SINGLE_IMAGE_GROUNDING / SINGLE_IMAGE_VQA / NO_VQA_SPECIALIST / VALIDATION_FAILED / NO_MATCH` | `packages/core/.../routing/router.py` |
| **Failure-aware resolution** | `derive_resolution()` → 6 qualifiers (`RESULT_OK / RESULT_STRUCTURAL_FAIL / RESULT_SEMANTIC_INCOHERENT / RESULT_UNVERIFIED / SPECIALIST_DEGRADED / SPECIALIST_FAILED`) + non-blocking `advisories` (`LOW_MARGIN`) | `app/services/failure_aware.py` |
| **Specialist slices** (each: validate → adapter → normalize → `EvidenceItem` + `Provenance` + `verify()`) | `run_scene` (RemoteCLIP), `run_vqa` (TinyRS), `run_grounding` (RemoteSAM), `run_change_slice` + `run_change_fallback` (ChangeFormer + image-diff), `run_composed_semantic_change` (ChangeFormer+RemoteCLIP), `run_joint_representation` (CROMA/DOFA) | `app/services/{scene,vqa,grounding,temporal,semantic_change_baseline,multimodal}_slice.py` |
| **Adapters** (frozen stack, G12) | `SpecialistAdapter` contract + subprocess isolation via `.venvs/<model>` + `scripts/research/*_infer.py`; `changeformer, remoteclip, croma, dofa, remotesam, tinyrs` | `packages/model_adapters/` |
| **Evidence / verification** | `EvidenceItem` (no confidence field, by design), `Provenance.from_adapter` + `scrub()`, `verify()` (structural), `verify_semantic()` (model-independent) | `packages/evidence/` |
| **Geospatial** | `validate_geotiff`, `check_pair_compatibility`, `read_raster_meta`, `RasterMeta` | `packages/geospatial/` |
| **Model registry** | frozen stack + routing table + measured facts | `packages/model_adapters/model_registry.yaml` |
| **Tests** | 166 collected (unit + contract + failure + slow e2e) | `apps/backend/tests/`, `packages/*/tests/` |
| **Local assets** | all 6 model checkpoints in `models/cache/`; 7 `.venvs/`; `data/demo/temporal/{t1,t2,t2_shifted}.tif` (EPSG:32650); `external/research/RemoteSAM/assets/*.jpg`, `RemoteCLIP/assets/airport.jpg`; DFC2020 zips (`models/cache/dfc2020/`) |

## MISSING (build in G13)

| # | Gap | Plan |
|---|-----|------|
| 1 | **Normalized user-facing response** — `AnalyzeResult.result` is a raw per-service dict; a UI must know 6 shapes | `NormalizedResponse` model + `normalize(AnalyzeResult) → NormalizedResponse` in a new `app/services/normalize.py`; flat fields (`answer, task, model_used, regions, boxes, masks, area_ha, centroid_lonlat, changed_fraction, labels, latency_s, warnings, …`), only populated when relevant |
| 2 | **File upload** — `/analyze` only accepts paths under `data/` | `POST /analyze/upload` (multipart: 1–2 files + `query` + optional `context` JSON) → save to sandboxed `data/uploads/<uuid>/` → `run_analyze` → `normalize` |
| 3 | **Artifact serving** — mask PNGs written to disk, no route to fetch them | `GET /artifact?path=…` sandboxed to the artifact dir; `normalize` rewrites `mask_path` → `/artifact?...` URL |
| 4 | **Static UI** — `apps/frontend/src/` is empty `.gitkeep`s, no `node_modules` | one self-contained `app/static/index.html` (vanilla JS + `<canvas>` overlay), served at `GET /`; **no npm, no build step** — "simplest reliable stack already present" |
| 5 | **Optical+SAR from GeoTIFFs** — `run_joint_representation` takes `.npy`; `/analyze` `MULTIMODAL_REPR` half-handles it | `run_joint_from_geotiffs(s2_tif, s1_tif)` in `multimodal_slice.py` (rasterio read → band-select/normalize → temp `.npy` → `run_joint_representation`); `/analyze` uses it when inputs are `.tif` |
| 6 | **Demo runner** — `scripts/demo/run_demo.sh` is a stub | real `scripts/demo/run_demos.py` — 5 deterministic scenarios against real local models; prints + writes real outputs to `docs/sih/evidence/` |
| 7 | **Demo fixtures** — only temporal tifs; need single-image + an S2/S1 pair | `data/demo/{vqa,grounding,scene}/` from RemoteSAM/RemoteCLIP assets (copied, attributed); `data/demo/optical_sar/{s2,s1}.tif` extracted from one DFC2020 patch |
| 8 | **Integration tests** — 15 cases from the brief | `apps/backend/tests/test_g13_integration.py` |
| 9 | **Docs** | README run block; `PROJECT_STATUS.md`; `docs/G13_PRODUCTIZATION_REPORT.md`; `docs/sih/evidence/` real captures; `API_CONTRACT.md` |
| 10 | **Model lifecycle / latency** | already lazy + sequential (each adapter is a fresh subprocess that exits → nothing resident); **document** it + record real cold/warm/e2e latency per workflow. No code needed beyond notes. |

## TO INTEGRATE (existing pieces, newly wired)

- `normalize()` consumes each slice's existing `payload / evidence / verification / resolution` → one schema. **No slice changes.**
- UI → `POST /analyze/upload` → renders `NormalizedResponse`; draws boxes/mask on `<canvas>`; panels for evidence / verification / execution-trace / provenance.
- `scripts/demo/run_demos.py` → `run_analyze` directly (no HTTP) for determinism; captures real outputs.
- `GET /` (UI) + `GET /artifact` + `POST /analyze/upload` added to `main.py`.

## NON-GOALS (explicit, per the G13 brief)

LLM planner (stays deterministic); new models / stack changes; core-architecture
redesign; confidence values; removing caveats; a heavy JS framework / `npm`
toolchain; PPT/marketing.
