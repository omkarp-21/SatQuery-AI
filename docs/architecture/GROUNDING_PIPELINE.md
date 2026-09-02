# Grounding pipeline (capability B)

> Text-guided grounding as a **dedicated specialist**, not a VQA side-task.
> Status: **REPRODUCED + INTEGRATED** (RemoteSAM, CPU). Not benchmarked.
> Design companions: `docs/research/EXP-GROUNDING.md`,
> `docs/research/FAILURE_AWARE_ROUTING.md`, `docs/API_CONTRACT.md`.

## Flow

```
POST /analyze { query: "locate the airplane on the right", images: [img] }
  -> interpret_query            _GROUNDING_KW  -> intent = "grounding"
  -> input validation           image opens; GeoTIFF metadata if applicable
  -> route()                    rule 4b: 1 image + grounding intent + "grounding" in caps
                                -> code SINGLE_IMAGE_GROUNDING, specialists ["remotesam"]
  -> run_grounding(img, query)  apps/backend/app/services/grounding_slice.py
       -> RemoteSamAdapter.run()         packages/model_adapters/.../remotesam.py
            -> subprocess: .venvs/remotesam/python scripts/research/remotesam_infer.py
                 -> RemoteSAM.visual_grounding(image, sentence) -> [xmin,ymin,xmax,ymax] | None
                 -> RemoteSAM.referring_seg(image, sentence)    -> binary mask (H,W)
       -> spatial-correspondence checks  box in bounds? mask dims == image? -> validation_status
       -> EvidenceItem(evidence_type="grounding", spatial_region.bbox_pixel, payload.bbox_xyxy)
       -> verify()                       grounding_box_valid + grounding_mask_artifact (STRUCTURAL)
       -> Provenance.from_adapter(...)   checkpoint sha256, repo commit, device, env
  -> derive_resolution(...)      failure-aware qualifier (RESULT_OK / RESULT_STRUCTURAL_FAIL / ...)
  -> AnalyzeResult              result = GroundingResult, evidence[], verification, resolution
```

## Contracts

**`GroundingResult`** (`grounding_slice.py`): `ok`, `query`, `image_dimensions [W,H]`,
`bbox_xyxy [xmin,ymin,xmax,ymax]` (image pixels) or `None`, `mask_path`, `score`
(+ `score_meaning` = "foreground softmax probability - NOT a calibrated
confidence"), `grounding_status` (`ok`|`no_box`|`error`), `validation_status`
(`PASS`|`NO_REGION`|`FAIL_BOX_OUT_OF_BOUNDS`|`FAIL_BOX_DEGENERATE`),
`execution_time_s`, `evidence[]`, `verification`, `provenance`.

**`RemoteSamAdapter`**: `capabilities = ("grounding","referring-segmentation")`,
`modalities = ("optical-single",)`, `license = "NOT STATED …"`. `validate()`
raises `UnsupportedTaskError` for `vqa`/`captioning`, `AdapterExecutionError` for
≠1 image / empty phrase / missing image, `AdapterConfigError` for a missing
checkpoint or repo.

## Evidence & verification

The grounding `EvidenceItem` is mappable: `spatial_region.bbox_pixel` is
`[rmin, cmin, rmax, cmax]` (row/col) and `payload.bbox_xyxy` is
`[xmin, ymin, xmax, ymax]` (x/y) in **original-image pixels**; `source_artifact`
is the mask PNG. `verify()` runs **structural** checks only:
`grounding_box_valid` (well-formed + inside `image_dims`) and
`grounding_mask_artifact` (file exists). A failed check → `CONTRADICTED` →
`resolution.qualifier == "RESULT_STRUCTURAL_FAIL"` (answer withheld). **No
semantic correctness is claimed from these checks. No confidence value.**

## Boundaries

- RemoteSAM is **not** routed for VQA or generic scene queries — `route()` keeps
  those on `NO_VQA_SPECIALIST` / `SINGLE_IMAGE_SCENE` and the code reason says so.
- **Licence NOT STATED upstream** — the registry records it; do not ship beyond a
  prototype without a licence from the authors.
- **Not benchmarked** — `acc@IoU0.5` on DIOR-RSVG is pending (dataset unacquirable
  from this host). B is REPRODUCED, not MEASURED.
- GPU / 4 GB-VRAM fit is **unverified** — CPU only on this host (~8 GB RSS,
  ~16–22 s/query). Classified `CPU-FALLBACK`; promote to `LOCAL-FITS-4GB` only
  after a real GPU measurement.
