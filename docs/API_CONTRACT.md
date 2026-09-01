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

## Planned (not implemented): `POST /analyze`

The future general entrypoint: natural-language query + image(s) → constrained
router (`satquery_core.routing`) → specialist(s) → fusion → evidence → verification
→ answer + provenance. **Not built** — needs ≥1 single-image specialist integrated
and the composed-semantic-change baseline. Shape sketch:

```json
// request
{ "query": "what changed between these dates?", "images": ["a.tif","b.tif"], "context": {} }
// response
{ "answer": "...", "route": { "code": "TEMPORAL", "specialists": ["changeformer"] },
  "results": [ ... ], "evidence": [ ... ], "verification": { ... }, "provenance": { ... } }
```
