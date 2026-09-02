# SatQuery API Contract

> Status: **v0 (G3)**. Two endpoints live. No agent endpoint yet. No confidence
> value in any response. Full request/response types: `apps/backend/app/api/`.

## Conventions

- All request/response bodies are JSON. Response models are Pydantic
  (`ChangeSliceResult`, `SceneResult`).
- Errors use `{"error": {"code": "...", "message": "..."}}`, sanitized — no stack
  traces, no internal paths.
- Input file paths are resolved against an allow-listed base (`SATQUERY_DATA_DIR`,
  default repo `data/`; `/scene` also allows the RemoteCLIP demo-assets dir).
  Traversal → `400 path_not_allowed`; missing → `404 not_found`.
- Model unavailable on the host → `503 model_unavailable`.
- Every successful result carries **`provenance`** and, where applicable,
  **`evidence[]`** (list of `EvidenceItem`) and **`verification`**
  (`VerificationResult`, deterministic/structural only).

---

## `GET /health`

`200 → {"status": "ok"}`

---

## `POST /change`  — bi-temporal change (ChangeFormer)

**Request**
```json
{ "t1_path": "demo/temporal/t1.tif", "t2_path": "demo/temporal/t2.tif", "strict": true }
```

**Response `200` (`ChangeSliceResult`)** — key fields:
```json
{
  "ok": true,
  "t1_meta": { "...RasterMeta..." }, "t2_meta": { "..." },
  "pair": { "co_registered": true, "mismatches": [] },
  "stats": {
    "changed_pixels": 16552, "total_pixels": 65536, "changed_fraction": 0.2526,
    "changed_area_m2": 4138.0, "changed_area_ha": 0.4138,
    "change_bbox_native": [...], "change_bbox_lonlat": [...], "change_centroid_lonlat": [...]
  },
  "mask_path": "…/changeformer_mask_*.png",
  "evidence": [ { "evidence_id": "ev-change_…", "evidence_type": "change-mask",
                 "source_model": "changeformer", "temporal_context": {...},
                 "payload": { "mask_path": "...", "changed_fraction": 0.2526 } } ],
  "verification": { "status": "SUPPORTED", "checks": [ {"name":"geospatial_compatibility","passed":true}, ... ] },
  "provenance": {
    "stages": ["validate_geotiff","check_pair_compatibility","changeformer_adapter","spatial_stats","evidence","verify"],
    "standardized": { "model":"changeformer","checkpoint_sha256":"…","execution_time_s":2.5,"status":"ok", ... },
    "adapter_provenance": { ... },
    "score_meaning": "stats.changed_fraction is pixel coverage, not a confidence; this slice produces no confidence value"
  }
}
```

- `strict: true` (default): if the pair is not co-registered, returns `ok: false`,
  `stats: null`, no inference is run.
- `changed_area_*` is populated only when the grid is a projected CRS in metres.

---

## `POST /scene`  — single-image scene / retrieval (RemoteCLIP)

**Not a VQA endpoint.** Zero-shot ranking over supplied prompts. Does not satisfy
the mandatory single-image VQA requirement.

**Request**
```json
{ "image_path": "airport.jpg", "prompts": ["an airport","a farm","a harbour"], "top_k": 5 }
```

**Response `200` (`SceneResult`)** — key fields:
```json
{
  "ok": true,
  "image_meta": { "...RasterMeta or null (non-GeoTIFF)..." },
  "answer": { "top_label": "an airport",
              "ranking": [["an airport",0.995],["a harbour",0.003],...],
              "score": 0.995,
              "score_meaning": "softmax over supplied prompts - not a calibrated confidence" },
  "evidence": [ { "evidence_type": "ranking", "source_model": "remoteclip",
                  "payload": { "top_label": "...", "ranking": [...] } } ],
  "verification": { "status": "SUPPORTED", "checks": [ {"name":"modality_supported","passed":true}, ... ] },
  "provenance": { "model":"remoteclip","checkpoint_sha256":"…","execution_time_s":2.9,"status":"ok",
                  "parameters": {"prompts":[...],"top_k":5} }
}
```

---

## Internal (no endpoint): joint optical–SAR representation

`app.services.multimodal_slice.run_joint_representation(optical_npy, sar_npy, model="croma"|"dofa")`
→ `JointReprResult` (representation vectors + evidence + provenance + structural
verification). **Representation-level only** — a `/fusion` endpoint is deferred
until EXP-004 Run 2 shows a task-level benefit.

---

## `POST /analyze`  — unified deterministic analysis  *(G4, LIVE)*

Natural-language query + 0–2 images → `interpret_query` (keyword→intent, **no
LLM**) → input validation → `satquery_core.routing.route()` → dispatch to one of
{`/scene` logic, `/change` logic, composed-semantic baseline, joint-representation}
→ aggregate evidence + verification + provenance.

**Request**
```json
{ "query": "describe what kind of change happened",
  "images": ["demo/temporal/t1.tif", "demo/temporal/t2.tif"],
  "context": { "modalities": ["optical"], "prompts": ["..."] } }
```

**Response `200` (`AnalyzeResult`)** — key fields:
```json
{
  "ok": true,
  "interpretation": { "intent": "semantic-change", "notes": ["matched semantic-change keywords"] },
  "routing": {
    "selected_task": "semantic-change",
    "selected_specialists": ["changeformer"],
    "routing_code": "TEMPORAL",
    "routing_rule": "two images + a change intent -> the bi-temporal change specialist",
    "required_inputs": ["geotiff-validate","pair-co-registration-assert"],
    "execution_order": ["changeformer"],
    "status": "routed"
  },
  "metadata_valid": true,
  "result": { "...the sub-service's structured output (ChangeSliceResult / SceneResult / ComposedSemanticChangeResult / JointReprResult)..." },
  "evidence": [ { "evidence_type": "change-mask", ... }, { "evidence_type": "ranking", ... } ],
  "verification": { "status": "SUPPORTED", "checks": [ ... ] },
  "resolution": { "qualifier": "RESULT_OK", "answer_surfaced": true, "disputed": false,
                  "reasons": [], "fallback_used": null,
                  "structural_status": "SUPPORTED", "semantic_status": "COHERENT",
                  "note": "deterministic post-execution qualifier ... NOT a confidence value" },
  "provenance": { "layer": "analyze", "interpretation": {...}, "routing": {...},
                  "resolution": {...}, "sub_service_provenance": {...},
                  "note": "multimodal path is representation-level only; VQA has no specialist; no confidence value is produced; `resolution` is a deterministic failure-aware qualifier, not a confidence" }
}
```

**`resolution`** *(G8 — failure-aware routing, `docs/research/FAILURE_AWARE_ROUTING.md`)* —
a deterministic post-execution qualifier: a pure function of `verify()` +
`verify_semantic()` + the sub-service ok/degraded flags. **Not a confidence value.**

| `qualifier` | trigger | `answer_surfaced` |
|-------------|---------|:-----------------:|
| `RESULT_OK` | structural SUPPORTED, semantic COHERENT / not-enough | true |
| `RESULT_STRUCTURAL_FAIL` | `verify()` == CONTRADICTED | **false** (answer withheld; `reasons` = failed checks) |
| `RESULT_SEMANTIC_INCOHERENT` | `verify_semantic()` == INCOHERENT | **false** (`disputed: true`) |
| `RESULT_UNVERIFIED` | no applicable checks either way | true (flagged) |
| `SPECIALIST_DEGRADED` | a declared fallback produced the result | true (`fallback_used` set) |
| `SPECIALIST_FAILED` | sub-service `ok:false` and no fallback helped | **false** |

`resolution.advisories[]` — non-blocking flags that never withhold an answer.
Currently: `LOW_MARGIN: N region tag(s) with rank-1 margin < 0.05` (composed
semantic-change baseline; per-region `tag_margin` / `low_margin` are on each
`ChangeRegion`). `RESULT_OK` with a `LOW_MARGIN` advisory still surfaces the
answer — the weak tags are flagged, not dropped.

**Single-step fallback (deterministic, no loop):** for the `TEMPORAL` change path,
if the ChangeFormer adapter cannot run, `/analyze` falls back **once** to
`image_difference_fallback` (abs mean-RGB difference + fixed threshold; same
geospatial gate). The result then carries `resolution.qualifier ==
"SPECIALIST_DEGRADED"` and `provenance.sub_service_provenance.is_fallback == true`.
The fallback is **not** ChangeFormer quality and says so in its `score_meaning`.

**Deterministic routing outcomes** (observable, in `routing.routing_code`):

| Query / inputs | code | specialists | `ok` |
|----------------|------|-------------|------|
| 1 image + scene/retrieval intent | `SINGLE_IMAGE_SCENE` | `["remoteclip"]` | true |
| 1 image + **grounding** intent (`where is…`, `locate…`, `segment…`) | `SINGLE_IMAGE_GROUNDING` | `["remotesam"]` | true — text→box+mask |
| 2 images + change intent | `TEMPORAL` | `["changeformer"]` | true |
| 2 images + **semantic**-change intent | `TEMPORAL` (→ `COMPOSED_SEMANTIC_CHANGE_BASELINE`) | `["changeformer"]` | true |
| 2 images optical + SAR (non-change) | `MULTIMODAL_REPR` | `["croma"]`/`["dofa"]` | true (representation-level) |
| 1 image + **VQA** intent (`how many…`, `is there…`) | `NO_VQA_SPECIALIST` | `[]` | **false** — never routed to RemoteCLIP **or RemoteSAM** |
| invalid / misregistered pair | `VALIDATION_FAILED` | `[]` | **false** |
| no rule matches | `NO_MATCH` | `[]` | **false** |

**Grounding result** (`SINGLE_IMAGE_GROUNDING` → `result` is a `GroundingResult`,
`docs/architecture/GROUNDING_PIPELINE.md`): `bbox_xyxy` `[xmin,ymin,xmax,ymax]`
(image pixels) or `null`, `mask_path`, `image_dimensions [W,H]`, `score` (raw
foreground softmax prob — **not** a confidence), `validation_status`
(`PASS`/`NO_REGION`/`FAIL_BOX_OUT_OF_BOUNDS`/`FAIL_BOX_DEGENERATE`). `evidence[0]`
is `evidence_type: "grounding"` with `spatial_region.bbox_pixel` (row/col) for the
map. `verification` runs `grounding_box_valid` + `grounding_mask_artifact`
(structural). RemoteSAM upstream **licence: NOT STATED**; **not benchmarked**
(DIOR-RSVG); GPU/4 GB-VRAM **unverified** (CPU-only, ~16–22 s/query).

Errors: `>2 images → 400`; traversal → `400`; missing file → `404`; pipeline error
→ sanitized `500`.

**Not yet:** an LLM intent-parsing step (EXP-006), the `MULTIMODAL_REPR` real-data
`.npy` path, and any confidence value (`docs/research/CONFIDENCE_PLAN.md`).
