# SatQuery API Contract

> Status: **G15 — agent validation + flagship mission mode.** `POST /investigate`
> (mission → planner → policy → bounded agent loop with structured replanning +
> explicit early termination → evidence-first report; `resolution.qualifier`,
> `replans[]`, `early_stopped`, `geojson` on the response), `GET /` (UI with
> an ASK / INVESTIGATE toggle), `POST /analyze/upload` (single-shot, flat
> `NormalizedResponse`), `GET /artifact`, plus `POST /analyze`, `/change`,
> `/scene`, `/health`. The deterministic router is the execution guard, not
> replaced. **No confidence value in any response.**
> Full request/response types: `apps/backend/app/api/`.

---

## `POST /investigate`  — agentic geospatial investigator  *(G14, hardened G15)*

**Request** — `multipart/form-data`: `query` (the mission, str), `files` (1–4
images), optional `context` (JSON string).

**Flow:** mission → **planner** (`RuleBasedPlanner` default; `LlmPlanner` local
Qwen2-VL-2B text-only when `SATQUERY_PLANNER=llm`, always falls back) → typed
`AgentPlan` → **12-check deterministic policy layer** (rejects wrong-tool-for-task,
cycles, > 8 steps, misregistered pairs, …) → **bounded executor** (state machine,
≤ 8 specialist calls, observes each result and conditionally replans) →
evidence-first synthesis. Planner unavailable / plan rejected → deterministic
`/analyze` fallback.

**Response `200` (`AgentInvestigationResult`)** — key fields:

```json
{
  "mission": "...", "mode": "investigate", "mission_family": "multi_step",
  "plan": { "goal": "...", "steps": [ {"step_id":"s2","task":"TEMPORAL_CHANGE","tool":"run_temporal_change","depends_on":["s1"],"reason":"..."} ] },
  "plan_status": "valid", "planner_used": "rule_based", "plan_rejection_reasons": [],
  "phase": "FINALIZING", "ok": true, "tool_calls": 4, "max_steps": 8, "hit_step_cap": false,
  "early_stopped": false, "completion_reason": null,
  "steps": [ {"step_id":"s2","task":"TEMPORAL_CHANGE","tool":"run_temporal_change","status":"completed",
              "verdict":"COHERENT","summary":"changed_fraction 0.2526, area 0.4138 ha",
              "findings":{"changed_fraction":0.2526,"changed_area_ha":0.4138},
              "verification_status":"SUPPORTED","contributed":true,"runtime_s":8.1} ],
  "replans": [ {"reason":"NEW_EVIDENCE","triggering_step":"s2","previous_phase":"REPLANNING",
                "detail":"changed_fraction 0.003 < 0.01: no significant change — region/grounding/SAR steps unnecessary",
                "steps_skipped":["s3","s4","s5"],"ts":"13:17:10"} ],
  "conclusion": "~25.3% of the scene changed, 6 changed region(s) isolated, 1 structure region(s) located. Verification: SUPPORTED.",
  "key_findings": [ "Change detected: ~25.3% ...", "Cross-check: 1/1 grounded region(s) fall inside a changed region." ],
  "spatial_findings": [ {"label":"changed region","where_pixel":[50,36,94,79],"where_lonlat":[114.9488,28.9119,114.949,28.9121],"area_ha":null,"source_step":"s3"} ],
  "geojson": { "type":"FeatureCollection", "crs":"EPSG:4326", "features":[ {"type":"Feature","properties":{"label":"changed region","source_step":"s3"},"geometry":{"type":"Polygon","coordinates":[[[...]]]}} ] },
  "evidence": [ {"evidence_type":"change-mask", ...} ],
  "verification": { "status": "SUPPORTED", "checks": [ ... ] },
  "resolution": { "qualifier": "RESULT_OK", "answer_surfaced": true, "note": "deterministic post-execution qualifier — NOT a confidence value" },
  "provenance": { "layer": "agent", "planner_used": "rule_based", "plan_status": "valid", "mission_family": "multi_step",
                  "plan_steps": [...], "tool_calls": 4, "contributing_tool_calls": 4, "unnecessary_tool_calls": 0,
                  "replans": [...], "early_stopped": false, "mask_source": "...", "input_files": ["/artifact?req=<id>&name=t1_optical.tif"] },
  "execution_trace": [ {"ts":"13:17:01","event":"Mission received"}, {"ts":"13:17:10","event":"REPLAN [NEW_EVIDENCE] from s2: ..."} ],
  "warnings": [ "PLANNER FALLBACK: ...", "SAR input missing — optical+SAR analysis was not performed" ],
  "failures": [], "models_used": ["ChangeFormer","RemoteSAM","CROMA"], "timings": { "total_s": 41.2 }
}
```

- **Never** runs a tool the policy layer forbids; **never** fabricates a box,
  coordinate, or a result for a failed specialist. An optical+SAR step surfaces
  "representation-level only; no textual fact inferred".
- **Replans** are a closed enum: `NEW_EVIDENCE · TOOL_FAILURE · MISSING_INPUT ·
  INSUFFICIENT_EVIDENCE · VERIFICATION_CONTRADICTION · TASK_COMPLETE`. Each is a
  structured `ReplanEvent`.
- **Deterministic fallback is visible:** planner unavailable / plan
  policy-rejected → `mode:"ask-fallback"`, `resolution.qualifier` in
  `{PLANNER_UNAVAILABLE, SPECIALIST_DEGRADED}`, a `AGENT FALLBACK` warning, and
  the blocking policy-check names in `execution_trace`.
- Errors: 0 or > 4 files → `400 bad_file_count`; bad type → `400`; > 64 MB →
  `413`; agent exception → sanitized `500 agent_error`.

Task ontology (closed): `VALIDATE_INPUT, SCENE_UNDERSTANDING, VQA, GROUND_OBJECT,
TEMPORAL_CHANGE, SEMANTIC_CHANGE, OPTICAL_SAR_ANALYSIS, EXTRACT_CHANGED_REGIONS,
CROSS_CHECK_EVIDENCE, VERIFY, SUMMARIZE, FINALIZE`. Tools (closed, 12) mirror the
frozen stack — see `packages/agents/src/satquery_agents/agent/registry.py`.

---

## `GET /`  — local single-page UI  *(G13)*

Serves `apps/backend/app/static/index.html` (self-contained vanilla-JS page — no
build step, no `npm`). Upload 1–2 images + a query → renders the `NormalizedResponse`
(answer, task, model, visual overlay for boxes/mask, evidence, verification,
execution trace, provenance, warnings).

## `POST /analyze/upload`  — the product entry point  *(G13)*

**Request** — `multipart/form-data`:
- `query` (str, required)
- `files` (1–2 files; `.tif .tiff .png .jpg .jpeg .npy`; ≤ 64 MB each)
- `context` (optional JSON string: `{modalities, prompts, question}`)

Saves the uploads to a per-request sandbox `data/uploads/<id>/`, runs the same
deterministic `run_analyze` (validate → interpret → route → specialist → evidence
→ verify → resolution), then flattens with `normalize()`.

**Response `200` (`NormalizedResponse`)** — one flat schema for every task; only
the relevant fields are populated, nothing is invented:

```json
{
  "query": "...", "interpreted_task": "grounding", "task_code": "SINGLE_IMAGE_GROUNDING",
  "execution_plan": ["remotesam"],
  "ok": true, "answer": "1 region grounded for the referring phrase.",
  "model_used": "RemoteSAM", "latency_s": 31.4,
  "yesno": null, "labels": [], "boxes": [{"xyxy_pixel": [..], "bbox_lonlat": null, "score": 0.99}],
  "regions": [], "mask_url": "/artifact?req=<id>&name=mask.png", "image_dimensions": [800, 800],
  "changed_fraction": null, "area_ha": null, "centroid_lonlat": null, "representation_dim": null,
  "score": 0.99, "score_meaning": "RemoteSAM foreground softmax probability - NOT a calibrated confidence",
  "crs": null, "geospatial_available": false,
  "geospatial_note": "geospatial coordinates unavailable because CRS/transform is missing",
  "evidence": [ { "evidence_type": "grounding", ... } ],
  "verification": { "status": "SUPPORTED", "checks": [ ... ] },
  "resolution": { "qualifier": "RESULT_OK", "answer_surfaced": true, ... },
  "provenance": { "layer": "analyze", "routing": {...}, "input_files": ["/artifact?req=<id>&name=scene.jpg"] },
  "execution_trace": { "steps": ["validate_input","interpret_query","route","specialist:remotesam","evidence","verify","resolve"],
                       "routing_code": "SINGLE_IMAGE_GROUNDING", "routing_rule": "..." },
  "failures": [], "warnings": ["RemoteSAM upstream licence is NOT STATED — treat grounding output as prototype-only."]
}
```

- A **blocked / unmatched** query returns `ok:false`, `answer:null`, the reason in
  `warnings`, `resolution:null` (nothing executed) — never a silently mis-routed
  specialist.
- A **grounding no-object** result returns `ok:true`, `boxes:[]`, an explicit
  "No region could be grounded …" answer, and `warnings:["no_grounded_region"]` —
  **never a hallucinated box**.
- Errors: bad file type → `400 unsupported_file_type`; 0 or >2 files →
  `400 bad_file_count`; > 64 MB → `413 file_too_large`; bad `context` JSON →
  `400 bad_context`; pipeline exception → sanitized `500 pipeline_error`.

## `GET /artifact?req=<id>&name=<file>`  — request artifacts  *(G13)*

Serves a file from `data/uploads/<id>/` (the mask PNG, or an echoed input for
preview). Sandboxed: `req` must match `^[a-f0-9]{6,32}$`, `name` is basename-only.
Anything outside the sandbox or missing → `404 not_found`.

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
| 1 image + **VQA** intent (`how many…`, `is there…`, `?`) | `SINGLE_IMAGE_VQA` | `["tinyrs"]` | true — text answer + yes/no parse |
| 1 image + VQA intent, **no `vqa` capability in the registry** | `NO_VQA_SPECIALIST` | `[]` | **false** — never routed to RemoteCLIP **or RemoteSAM** |
| invalid / misregistered pair | `VALIDATION_FAILED` | `[]` | **false** |
| no rule matches | `NO_MATCH` | `[]` | **false** |

**VQA result** (`SINGLE_IMAGE_VQA` → `result` is a `VqaResult`): `answer_text`,
`yesno` (1 / 0 / null), `score: null` (greedy-decoded — **no confidence value**),
`evidence[0].evidence_type == "vqa"`. Model: **TinyRS-2B** (RS-instruction-tuned
Qwen2-VL-2B; balanced acc 0.87 on RSVQA-LR n=40, CPU — `EXP-002.md`); fallback
Qwen2-VL-2B. GPU/4 GB-VRAM unverified (CPU-only host, ~9 GB RSS, ~4.5 s/query).

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
