# Evidence Ledger

> One row per model × claim. The level is the **highest** we have actually
> reached, with the artifact that proves it. Never promote a row without a real
> run. Levels: `PAPER-REPORTED < DOCUMENTED < REPRODUCED < MEASURED < INTEGRATED
> < VALIDATED`.
> Updated: **2026-09-02 (G12)**.

## Level definitions

| Level | Bar | Who can cite it as ours |
|-------|-----|-------------------------|
| PAPER-REPORTED | the authors' number, their setup | nobody — always attributed |
| DOCUMENTED | the repo/card states the capability; we have not run it | nobody |
| REPRODUCED | we ran the official example → sane output on ≥1 input | "we reproduced the example" |
| MEASURED | we scored it vs reference data; dataset + split + metric + hardware + date recorded | "we measured X on split S" |
| INTEGRATED | runs inside a SatQuery pipeline via an adapter, with provenance | "SatQuery runs it" |
| VALIDATED | end-to-end in the pipeline under our evaluation, verified | "SatQuery's result is X" |

## Ledger

| Model | Capability | Level | Proof / artifact | Notes |
|-------|-----------|:-----:|------------------|-------|
| **RemoteCLIP** | zero-shot scene classification | **INTEGRATED** | `RemoteClipAdapter` (G2.5) + smoke test; `run()` → airport 0.989; provenance block | not a benchmark; score = softmax over given prompts |
| RemoteCLIP | retrieval / embedding | REPRODUCED | official `use` path (`runtime_validation.md`) | |
| **ChangeFormer** | bi-temporal change mask | **INTEGRATED** | `ChangeFormerAdapter` + `/change` API + `temporal_slice.run_change_slice`; e2e tests pass | provenance: checkpoint sha256, input digest, bridge |
| ChangeFormer | change-mask accuracy | **MEASURED** | change-IoU 0.832 / F1 0.908, 7 bundled LEVIR-CD samples, CPU, 2026-09-01 | n=7 — **sanity, not a benchmark** |
| ChangeFormer | LEVIR-CD test accuracy | PAPER-REPORTED | checkpoint `log.txt`: overall acc 0.9495 | authors' number |
| **CROMA** | joint radar-optical embedding (capability D **PRIMARY**) | **REPRODUCED + INTEGRATED** | `use_croma.py` official example; `CromaAdapter` smoke → dim 768; `run_joint_representation(model=croma)` in `/analyze` `MULTIMODAL_REPR` path | representation-level; MIT (code + weights) |
| **CROMA** | optical+SAR downstream benefit (H3) | **MEASURED** | EXP-004 Run 2 (G12): frozen `joint_GAP` → linear probe on DFC2020 dominant-land-cover, 400 train / 200 eval, seed 20260902, CPU → **macro-F1 0.793 vs optical-only 0.726 (+0.067)**; bootstrap 95% CI [−0.024,+0.153] **includes 0**, McNemar p=0.45 | **positive but NOT significant at n=200**; sanity-scale (600/986); `exp004_run2_*.json` |
| **CROMA** | RS adaptation — LoRA vs frozen (capability E) | **MEASURED** | EXP-008 (G12): LoRA r=8 (811 k trainable params, 3.24 MB adapter) on the frozen DFC2020 split → held-out macro-F1 **0.643 → 0.704 (+0.061)** vs same-head frozen baseline; clears the pre-registered +0.03 bar → **ADOPT LoRA** as the E method | sanity-scale (400/200); **not significance-tested**; prod default stays frozen pending a larger-split re-run; CPU (no VRAM) |
| CROMA | SAR-signal recovery vs optical-only | MEASURED (sanity) | EXP-004 Run 1: bal-acc 1.00 (SAR-only) vs 0.49 optical-only, synthetic control | **NOT a benchmark** — synthetic injected signal |
| CROMA | linear-probe accuracy on DFC2020 / BigEarthNet | PAPER-REPORTED | CROMA paper (NeurIPS 2023) | not reproduced by us |
| **DOFA** | multi-sensor (S1/S2) embedding (capability D **CHALLENGER/FALLBACK**) | **REPRODUCED + INTEGRATED** | `forward_features` for S1 + S2; `DofaAdapter` smoke → dim 768; available in `/analyze` `MULTIMODAL_REPR` | MIT (code + weights) |
| **DOFA** | optical+SAR downstream benefit (H3) | **MEASURED** | EXP-004 Run 2 (G12): frozen S2⊕S1 concat → linear probe, same split → **macro-F1 0.708 vs DOFA-optical 0.725 (−0.018)** | late concat-fusion gave **no** SAR gain; lost the bake-off to CROMA (0.793) |
| DOFA | fused SAR-signal recovery | MEASURED (sanity) | EXP-004 Run 1: bal-acc 1.00 (S2⊕S1) vs 0.50 optical-only | same synthetic control |
| DOFA | GEO-Bench results | PAPER-REPORTED | DOFA paper | not reproduced by us |
| RSCoVLM | RS multi-task VLM | **DOCUMENTED / no artifact** | `Qingyun/rscovlm` — **only 7B released** (`RSCoVLM-7B-2512`); NO 3B checkpoint (paper claim only) | REMOTE-ONLY (7B). "RSCoVLM-3B" is void — same as RS-MoE-1B. |
| **TinyRS-2B** | single-image RS **VQA** (PRODUCTION PRIMARY, capability A) | **REPRODUCED + MEASURED + INTEGRATED** (G11) | `.venvs/tinyrs` CPU, 2026-09-02: **balanced acc 0.8736** on 40 RSVQA-LR yes/no (`dmarsili/RSVQA-LR-2k` mirror), fail_rate 0.0, p50 4.45 s, RSS peak 9.1 GB. `TinyRsAdapter` + `run_vqa` + router `SINGLE_IMAGE_VQA` + `/analyze` VQA path + `vqa` `EvidenceItem`. `exp002_vqa_rsvqa.py`. PAPER: authors ≈ 83.5 %. |
| Qwen2-VL-2B | single-image VQA (control / FALLBACK) | **REPRODUCED + MEASURED** (G11) | same harness: **balanced acc 0.7033** — passes the 0.60 gate; the +0.17 TinyRS gap = measured value of RS instruction-tuning |
| **Qwen2-VL-2B** | generic VQA / native bbox grounding (GENERIC CONTROL) | **DOCUMENTED** | HF `Qwen/Qwen2-VL-2B-Instruct` card | **G5A: N=0** — 6th acquisition failure (0-byte safetensors, 8-min bound); PAPER (generic, not RS): DocVQA 90.1 / MMBench-EN 74.9 |
| **EarthDial-4B** | RS multi-task VLM +SAR +temporal (PRIMARY HIGH-CAPABILITY REFERENCE) | **DOCUMENTED** | README + HF `akshaydudhane/EarthDial_4B_*` (checkpoints verified to exist; weights licence unconfirmed) | REFERENCE CANDIDATE — remote-only; PAPER: 44-dataset eval, no README # |
| GeoChat-7B | single-image VQA / grounding (SECONDARY / HISTORICAL REFERENCE) | DOCUMENTED | repo + `model_inventory.md` | BLOCKED locally (7B > 4 GB; deepspeed/bnb) — **not a project blocker**; PAPER: authors ≈ 90 % RSVQA-LR |
| Change-Agent | temporal semantic + caption | DOCUMENTED | repo | BLOCKED (mmcv 1.3.1) |
| ChangeChat | temporal change caption/VQA | DOCUMENTED | repo | REJECT — no released weights |
| **RemoteSAM** | text-guided grounding (box + mask; PRODUCTION, capability B) | **REPRODUCED + INTEGRATED + MEASURED** (G10 → G11) | G11: **acc@IoU0.5 = 0.84 (21/25)** on a frozen DIOR-RSVG sample (`pzhang1990/DIOR-RSVG` non-gated mirror), CPU, via the integrated bridge; 0 no_box, mean IoU 0.762, p50 29 s, RSS peak 6.08 GB. `RemoteSamAdapter` + `run_grounding` + `/analyze` `SINGLE_IMAGE_GROUNDING`. `exp_grounding_dior.py`. Sanity-scale n=25. |
| RemoteSAM | referring segmentation (mask) | REPRODUCED | same smoke — mask dims match image, fg fraction sensible | not scored (no GT mask) |
| RemoteSAM | 4 GB VRAM fit | **NOT VERIFIED** | CPU only on this host (~8 GB RSS, ~16–22 s/query) | classified `CPU-FALLBACK`; GPU measurement pending |
| **DynamicVis** | vision encoder (Mamba SSM) — classif/detect/seg/change/retrieval | **DOCUMENTED** | `KyanChen/DynamicVis` README + HF | **REJECT for product** — Mamba is Windows + CPU incompatible; NOT a VLM (no A/B). Watch-item. |
| RS-MoE (2 repos) | RS caption + VQA (claimed) | DOCUMENTED | repo | REJECT — no released weights / no inference code; `CongcongWen1208/RS-MoE` README: "MoE not yet implemented", base Vicuna-13B |

## SatQuery-owned components (not models)

| Component | Level | Proof |
|-----------|:-----:|-------|
| GeoTIFF validation (`validate_geotiff`) | **VALIDATED** | 13 tests; live in `/change` + `/scene` + slices |
| Pair co-registration gate (`check_pair_compatibility`) | **VALIDATED** | tests + blocks misregistered pairs in the slice/API |
| Temporal vertical slice (`run_change_slice`) | **INTEGRATED** | e2e tests; `POST /change`; now emits evidence + verification |
| `POST /change` API | **INTEGRATED** | `test_change_api.py` — 200 + structured JSON incl. evidence/verification; guards |
| `POST /scene` API | **INTEGRATED** (G3) | `test_scene_api.py` — RemoteCLIP ranking + evidence + verification; NOT a VQA endpoint |
| Multimodal joint-repr contract (`run_joint_representation`) | **INTEGRATED + task-MEASURED** (G3; EXP-004 Run 2 G12) | `test_multimodal_slice.py`; `MULTIMODAL_REPR` route; **EXP-004 Run 2**: frozen CROMA `joint_GAP` → DFC2020 land-cover probe macro-F1 0.793 vs optical 0.726 (+0.067, not sig. at n=200). No `/fusion` endpoint yet. |
| SpecialistAdapter interface | **INTEGRATED** | 4 adapters implement `validate/execute/normalize_output/provenance` + `run()`; `AdapterResult` carries status/timing/model_meta |
| `EvidenceItem` + `Provenance` (`packages/evidence`) | **INTEGRATED** (G3) | 9 tests; wired into `/change`, `/scene`, multimodal |
| Deterministic verifier (`verify()`) — structural | **VALIDATED (structural)** (G6) | **EXP-005**: structural-defect detection **P/R/F1 = 1.00** on a curated n=24 corpus (TP 8/FP 0/TN 12/FN 0); `evaluation/scripts/exp005_verifier_detection.py` + 3 lock tests. Structural only. |
| Semantic verifier (`verify_semantic()`) — model-independent | **MEASURED + INTEGRATED (experimental)** (G7) | **EXP-005b**: internal-incoherence detection **P/R/F1 = 1.00** on a curated n=34 corpus (TP 10/FP 0/TN 14/FN 0); 6 model-independent checks; wired into `COMPOSED_SEMANTIC_CHANGE_BASELINE` (`semantic_verification` field). `evaluation/scripts/exp005b_semantic_verifier.py` + 9 lock tests. |
| Semantic verification — label correctness | **NONE — residual gap sized** (G7) | **EXP-005b**: BEYOND_SCOPE miss rate **1.00** (6/6). Needs `independent_model_agreement` (EXP-002) + `optical_sar_agreement` (EXP-C2). `coverage_unavailable` names them. |
| Semantic-change crop strategy (`crop_strategy=`) | **experimental — behaviour measured** (G6) | **EXP-003b**: tight/expanded/mask_aware on the demo pair, 3-way agreement 4/6 regions; `expanded` provisional default (not changed in code). Not a learned VLM. |
| Constrained router (`satquery_core.routing`) | **INTEGRATED** (G4) | deterministic; called by `POST /analyze`; 8 tests + `ROUTING_SPEC.md` |
| Failure-aware routing (`derive_resolution` + `image_difference_fallback`) | **INTEGRATED** (G8; `LOW_MARGIN` advisory G9) | pure deterministic qualifier (6 states) fn of `verify()` + `verify_semantic()` + sub status; single-step fallback; non-blocking `advisories` (`LOW_MARGIN`); additive `resolution` field on `/analyze`; 13 tests; `FAILURE_AWARE_ROUTING.md`, `API_CONTRACT.md`. No loop, no confidence. |
| `POST /analyze` unified layer | **INTEGRATED** (G4) | `test_analyze_api.py` (13) — interpret→validate→route→specialist→aggregate; observable routing info; VQA blocked, bad pair blocked |
| `COMPOSED_SEMANTIC_CHANGE_BASELINE` (capability C) | **INTEGRATED — experimental baseline** (G4; crop strategy measured G6) | `test_semantic_change_baseline.py` (7); mask→components→crop-tag→rule description; disclaimed; `crop_strategy` ∈ {tight,expanded,mask_aware} — EXP-003b |
| Geospatial safeguards (EXP-007) | **VALIDATED** (G4) | 15/15 stress cases pass; `docs/research/EXP-007.md`; not weakened |
| Confidence methodology | **NONE** (by design) | nothing emits a confidence value; `CONFIDENCE_PLAN.md` — EXP-C1/C2 specified, blocked |
| Learned semantic change / temporal VLM | **NONE** | only the composed baseline exists (not learned, not validated) |
| Agentic (LLM) router / true `/analyze` planning | **DESIGNED** | deterministic `/analyze` is the substrate; LLM intent step = EXP-006 |

## G5A A/B gate — the three numbers (kept separate, `docs/18`)

| Category | RSCoVLM-3B | TinyRS-2B | Qwen2-VL-2B | EarthDial-4B | GeoChat-7B |
|----------|-----------|-----------|-------------|--------------|------------|
| PAPER RESULT | no headline # | ≈83.5 % RS-VQA (authors) | DocVQA 90.1 (generic) | 44-dset eval, no # | ≈90 % RSVQA-LR (authors) |
| OUR REPRODUCTION | — | — | — | — | — |
| OUR MEASUREMENT | — | — | — | — | — |
| OUR INTEGRATED RESULT | — | — | — | — | — |

All non-PAPER cells empty: **artifact acquisition BLOCKED** (weights + datasets,
6 documented download failures), not a measured failure. Remote reference gate
OPEN (ADR-013). Harness + frozen samples committed:
`evaluation/scripts/exp002_ab_gate.py`, `evaluation/datasets/{rsvqa_lr,dior_rsvg}_sample.json`.

**Reminder:** no row here is VALIDATED for a *model on a task* — that needs a real
benchmark under our evaluation (EXP-004 Run 2, EXP-002, EXP-003).
