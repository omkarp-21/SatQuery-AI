# EXP-GROUNDING — RemoteSAM as the local capability-B (grounding) specialist

> Registry: candidate for mandatory capability **B** (grounding OR captioning).
> Resolves B **independently of the download-blocked VQA models** by using a
> dedicated grounding specialist rather than making a 3B VLM emit coordinates.
> Status: **RemoteSAM REPRODUCED on this host (CPU, 2026-09-02) + INTEGRATED
> behind an adapter + routed by `/analyze`. NOT MEASURED** (DIOR-RSVG
> unacquirable). Three-numbers rule (`docs/18`) applied throughout.

## The three numbers

| | value |
|--|--|
| **PAPER RESULT** (authors, ACM MM 2025) | referring-seg oIoU 76.21 / mIoU 64.79 (their setup) |
| **OUR REPRODUCTION** | ✅ checkpoint loads on CPU; `visual_grounding` + `referring_seg` produce in-bounds box + mask with foreground prob ≈ 0.97–1.0 on 3/5 smoke phrases |
| **OUR MEASUREMENT** | ✗ — DIOR-RSVG acc@IoU0.5 not run (dataset is Google-Drive-only, no HF mirror; DIOR images are a multi-GB set this host cannot fetch) |
| **OUR INTEGRATED RESULT** | adapter + `/analyze` grounding path live; no benchmark number yet |

## Phase 1 — current repository audit (`1e12Leon/RemoteSAM`, branch `master`, commit `ebb7bc2`)

| Field | Verified value |
|-------|----------------|
| Paper | "RemoteSAM: Towards Segment Anything for Earth Observation", ACM MM 2025 (oral), arXiv 2505.18022 |
| Model type | **Referring-Expression-Segmentation specialist** (LAVT lineage: multimodal Swin-Base + BERT). **Not** a conversational VLM. |
| Tasks (released code) | `referring_seg` (text→mask), `visual_grounding` (text→box, via connected-components on the mask), semantic seg, detection, classification, captioning, counting |
| Checkpoint | HF `1e12Leon/RemoteSAM` → single file `RemoteSAMv1.pth`, **2,566,704,235 B**. `state_dict` (`sd['model']`, 1107 entries): 854 `backbone.*`, 197 `text_encoder.*` (BERT weights are IN the checkpoint), 56 decoder. |
| **License** | **NOT STATED.** No LICENSE file in the repo; the HF checkpoint page has **no model card**. Recorded as `NOT STATED` in the registry — **must be clarified before any non-prototype use.** |
| README env | conda py3.8 / `torch==1.13.0+cu116` / **`mmcv-full==1.7.1`** / `mmsegmentation==0.17.0` (the last two conflict: mmseg 0.17.0 asserts `mmcv<1.4.0`) |
| **Actual inference deps** | `tasks/code/model.py` + `lib/segmentation.py` → **pure PyTorch + `timm.models.layers` + `transformers.BertModel`**, no mmcv/mmdet/mmseg ops. The `mmseg` import in `backbone.py` is commented out. The **only** mmcv touch is `lib/mmcv_custom/checkpoint.py` importing pure-Python `mmcv.fileio/parallel/utils/runner` — satisfied by **`mmcv` (lite) 1.7.1**, which does **not** compile ops. `mmdet`/`mmsegmentation`/`pycocotools` are training-only (captioning is stubbed in the bridge). |
| Windows wheel | `mmcv-full==1.7.1` cp38 win wheels exist only on the **cu116** index (CUDA build). `mmcv` (lite) 1.7.1 builds from source (pure Python) — needs `pkg_resources` in the build env → installs with `pip install mmcv==1.7.1 --no-build-isolation` after `pip install setuptools wheel`. |
| Repo activity | 247★, 15 commits, last update 2025-07 (ACM MM acceptance) |
| Inference API | `mask = model.referring_seg(image=rgb_ndarray, sentence="...")`; `box = model.visual_grounding(image=rgb_ndarray, sentence="...")` → `[xmin,ymin,xmax,ymax]` or `None`. Input resized to **896×896**. |

## Phase 2 — environment (`.venvs/remotesam`, isolated)

Python 3.11, `torch==2.2.2+cpu`, `torchvision==0.17.2+cpu`, **`mmcv==1.7.1` (LITE)** via
`--no-build-isolation`, `transformers==4.30.2`, `tokenizers==0.13.3`, `timm==0.6.13`,
`opencv-python-headless==4.11`, `numpy==1.26.4`, `scikit-image`, `scipy`, `psutil`.
`bert-base-uncased` (440 MB) cached at `models/cache/hf_home` for offline load
(passed to RemoteSAM as `--ck_bert <local dir>`; the hardcoded
`BertTokenizer.from_pretrained('bert-base-uncased')` resolves from the same cache
with `HF_HUB_OFFLINE=1`).

**Not BLOCKED — ENVIRONMENT.** The `mmcv-full` wall the earlier audit assumed does
not apply to the inference path.

## Phase 3 — checkpoint

`RemoteSAMv1.pth` (2.57 GB) downloaded to `models/cache/remotesam/RemoteSAM/` —
succeeded on a `hf_transfer`-enabled retry (259 s) after several plain-`requests`
attempts failed (one ran 16 h → 403). `sd.keys() == {model, optimizer, epoch, args,
lr_scheduler}`; loaded as `model.load_state_dict(sd['model'], strict=False)`.

## Phase 4 — smoke (CPU, `scripts/research/remotesam_infer.py`, 5 phrases)

| # | image (W×H) | phrase | box (xyxy) | mask fg | prob | latency | status |
|---|-------------|--------|------------|:------:|:----:|:-------:|--------|
| 1 | demo.jpg 800×800 | "the airplane on the right" | [452, 425, 767, 660] | 3.8 % | 1.00 | 96 s (first) | ok |
| 2 | demo.jpg 800×800 | "the largest building" | — | 0 % | ~1e-12 | 22 s | no_box |
| 3 | NUIST.jpg 333×333 | "the road" | [5, 0, 331, 331] | 65 % | 0.975 | 17 s | ok |
| 4 | HKUST.jpg 226×234 | "the water area" | [65, 1, 171, 219] | 26 % | 0.981 | 16 s | ok |
| 5 | t1.tif 256×256 (LEVIR) | "buildings in the scene" | — | 0 % | ~2e-14 | 17 s | no_box |

- **3 / 5 grounded** with a valid in-bounds box + mask and a high foreground prob.
- **#2, #5 → `no_box`**: #5 is a 256 px LEVIR tile — **out of distribution** for a
  model trained on ~800 px DIOR imagery (a documented failure mode, not a crash).
  #2 may be a legitimate "no single distinct object".

## Phase 5 — spatial correspondence (verified)

For every successful result: `mask.shape == (H, W)` matches the image; the box is
`[xmin,ymin,xmax,ymax]` with `xmin<xmax`, `ymin<ymax`, and `0 ≤ … ≤ W/H`; the box
is derived from the mask by `cv2.connectedComponentsWithStats`, so box↔mask
correspondence holds by construction. `GroundingResult` normalises to
`bbox_xyxy` + `mask_path` + `image_dimensions [W,H]` + a `validation_status`
(`PASS` / `NO_REGION` / `FAIL_BOX_OUT_OF_BOUNDS` / `FAIL_BOX_DEGENERATE`), and the
grounding `EvidenceItem` carries `spatial_region.bbox_pixel` (r,c order) for the map.

## Phase 6 — DIOR-RSVG evaluation

**BLOCKED.** `evaluation/datasets/dior_rsvg_sample.json` (frozen 25 expressions)
has empty `resolved_ids` because the dataset is not on disk: DIOR-RSVG is
distributed via Google Drive only (no HF mirror), and the DIOR image set is a
multi-GB download this host cannot complete. **acc@IoU0.5 is not measured.**

## Phase 7 — 4 GB feasibility

| metric | value (CPU, this host) |
|--------|------------------------|
| model load | ~22 s |
| CPU RSS after load | ~1.98 GB |
| **CPU RSS peak** | **~8.1 GB** (896² Swin-B forward, fp32 CPU) |
| first inference | ~96 s (lazy init) |
| steady-state / query | **~16–22 s** |

**Classification: `CPU-FALLBACK` (verified).** Runs on the ASUS's CPU + RAM
(16–32 GB) at ~16–22 s/query — over the ≤ 45 s internal gate after the first call,
under it in steady state. **`LOCAL-FITS-4GB` on GPU is plausible but NOT verified**
— no CUDA torch on this host; Swin-B at 896² fp16 on a 3050 Ti is likely ~2–3 GB
VRAM (activations dominate) but that must be measured on the actual GPU before the
claim is made.

## Phase 8 — failure analysis

| category | observed |
|----------|----------|
| out-of-distribution resolution | #5 — 256 px LEVIR tile → `no_box`. RemoteSAM expects ~800 px DIOR-scale imagery. |
| query understanding / no distinct object | #2 — "the largest building" on an airport scene → `no_box` (plausibly correct). |
| latency | first call ~96 s (lazy init + 2.5 GB load); steady-state OK. |
| memory | ~8 GB CPU RSS — fine on the ASUS, would need GPU on a RAM-constrained box. |
| dependency | `mmcv` lite source build needs `--no-build-isolation`; `bert-base-uncased` must be pre-cached for offline. Both handled in `.venvs/remotesam` + the bridge. |
| licence | **NOT STATED** — the single most important open item. |
| box / mask quality | valid geometry on all successes; mask fidelity not scored (no GT). |

## Phase 9–11 — integration

- **Adapter:** `packages/model_adapters/src/satquery_model_adapters/remotesam.py`
  (`RemoteSamAdapter`) — implements `validate / execute / normalize_output /
  provenance / run`. Subprocess to `.venvs/remotesam` running
  `scripts/research/remotesam_infer.py`; **product code never imports the research
  repo**. Rejects VQA / captioning tasks with `UnsupportedTaskError`.
- **Registry:** `remotesam` entry in `model_registry.yaml` `models:` —
  `deployment_tier: LOCAL_PREFERRED`, `capabilities: [grounding,
  referring-segmentation]`, `evidence_level: reproduced`,
  `status: KEEP (local grounding specialist) — pending DIOR-RSVG measurement +
  GPU-VRAM check + licence`, `license: "NOT STATED …"`.
- **Routing:** `router.py` — new `GROUNDING_INTENTS`, rule 4b, code
  `SINGLE_IMAGE_GROUNDING → ["remotesam"]`. **VQA still → `NO_VQA_SPECIALIST`**
  and the reason explicitly says *do not route RemoteCLIP or RemoteSAM as a VQA
  model*. `single_image_grounding: [remotesam]` in the routing block.
- **`/analyze`:** `grounding` intent (`_GROUNDING_KW`) → `run_grounding` →
  `GroundingResult` with a **grounding** `EvidenceItem` + structural `verify()`
  (box-valid + mask-artifact checks added to the verifier) + provenance. The
  answer flows through the existing failure-aware `resolution`.
- **Service:** `apps/backend/app/services/grounding_slice.py`.
- **Tests:** `packages/model_adapters/tests/test_remotesam_adapter.py` (7 —
  contract, rejects VQA/captioning/2-images/empty-phrase/missing-image/missing-ckpt),
  `apps/backend/tests/test_grounding.py` (18 — intent, routing to remotesam,
  VQA-never-to-remotesam, capability-absent → NO_MATCH, structural checks for
  valid/OOB/degenerate box + missing mask, slice failure paths, `/analyze` 404,
  + 2 slow e2e).

## Verdict / Phase 13 decision

| criterion | RemoteSAM |
|-----------|-----------|
| grounding metric | **not measured** (DIOR-RSVG blocked) |
| spatial correctness | ✅ verified (box in bounds, mask dims match, box↔mask consistent) |
| reliability | 3/5 smoke ok; 2 `no_box` (1 OOD). No crashes. |
| VRAM / memory | CPU ~8 GB RSS; GPU/4 GB **unverified** |
| latency | ~16–22 s/query steady-state (CPU); over gate on first call |
| integration complexity | MEDIUM — done (adapter + routing + `/analyze` + evidence + 25 tests) |
| licence | ⚠️ **NOT STATED** |

**Decision: KEEP as the local grounding specialist — `evidence_level: reproduced`,
`status: KEEP … pending DIOR-RSVG measurement + GPU-VRAM check + licence.`**
Capability **B is now REPRODUCED + INTEGRATED**, not MEASURED. RemoteSAM is a
*dedicated grounding specialist* — the two-specialist A/B design (VQA model +
grounding model) is now real on the B side. It does **not** make SatQuery depend
on a large VLM for grounding.

## Next experiment

On a machine that can acquire DIOR-RSVG (or with a GPU): (1) resolve the frozen
25-expression sample and run `run_grounding` over it → **acc@IoU0.5** vs the 0.30
internal gate; (2) run the same on a CUDA build to record **peak VRAM** and
confirm `LOCAL-FITS-4GB`; (3) email/issue the authors for a licence statement.
