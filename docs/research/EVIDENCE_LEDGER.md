# Evidence Ledger

> One row per model × claim. The level is the **highest** we have actually
> reached, with the artifact that proves it. Never promote a row without a real
> run. Levels: `PAPER-REPORTED < DOCUMENTED < REPRODUCED < MEASURED < INTEGRATED
> < VALIDATED`.
> Updated: **2026-09-01 (G2.5)**.

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
| **CROMA** | joint radar-optical embedding | **REPRODUCED** | `use_croma.py` official example; `CromaAdapter` smoke (random) → dim 768 | |
| CROMA | SAR-signal recovery vs optical-only | **MEASURED (sanity)** | EXP-004 Run 1: bal-acc 1.00 (SAR-only) vs 0.49 optical-only, synthetic control, N=240/160, seed 20260901 | **NOT a benchmark** — synthetic injected signal |
| CROMA | linear-probe accuracy on DFC2020 / BigEarthNet | PAPER-REPORTED | CROMA paper (NeurIPS 2023) | not reproduced by us |
| **DOFA** | multi-sensor (S1/S2) embedding | **REPRODUCED** | `forward_features` for S1 + S2; `DofaAdapter` smoke (random) → dim 768 | |
| DOFA | fused SAR-signal recovery | **MEASURED (sanity)** | EXP-004 Run 1: bal-acc 1.00 (S2⊕S1) vs 0.50 optical-only | same synthetic control |
| DOFA | GEO-Bench results | PAPER-REPORTED | DOFA paper | not reproduced by us |
| GeoChat | single-image VQA / grounding | DOCUMENTED | repo + `model_inventory.md` | BLOCKED locally (7B > 4 GB; deepspeed/bnb) |
| Change-Agent | temporal semantic + caption | DOCUMENTED | repo | BLOCKED (mmcv 1.3.1) |
| TinyRS | lightweight RS VQA / grounding | DOCUMENTED | HF card; `.venvs/tinyrs` set up | EXP-002 — weight download unreliable (N=0) |
| RSCoVLM-3B | multi-task RS VLM | DOCUMENTED | HF card | EXP-002 challenger — not started |
| ChangeChat | temporal change caption/VQA | DOCUMENTED | repo | REJECT — no released weights |
| RS-MoE | RS caption + VQA | DOCUMENTED | repo | REJECT — no released weights / inference path |

## SatQuery-owned components (not models)

| Component | Level | Proof |
|-----------|:-----:|-------|
| GeoTIFF validation (`validate_geotiff`) | **VALIDATED** | 13 tests; live in `/change` + `/scene` + slices |
| Pair co-registration gate (`check_pair_compatibility`) | **VALIDATED** | tests + blocks misregistered pairs in the slice/API |
| Temporal vertical slice (`run_change_slice`) | **INTEGRATED** | e2e tests; `POST /change`; now emits evidence + verification |
| `POST /change` API | **INTEGRATED** | `test_change_api.py` — 200 + structured JSON incl. evidence/verification; guards |
| `POST /scene` API | **INTEGRATED** (G3) | `test_scene_api.py` — RemoteCLIP ranking + evidence + verification; NOT a VQA endpoint |
| Multimodal joint-repr contract (`run_joint_representation`) | **INTEGRATED** (internal, G3) | `test_multimodal_slice.py`; representation-level only |
| SpecialistAdapter interface | **INTEGRATED** | 4 adapters implement `validate/execute/normalize_output/provenance` + `run()`; `AdapterResult` carries status/timing/model_meta |
| `EvidenceItem` + `Provenance` (`packages/evidence`) | **INTEGRATED** (G3) | 9 tests; wired into `/change`, `/scene`, multimodal |
| Deterministic verifier (`verify()`) | **INTEGRATED** (G3) | structural checks only — SUPPORTED/CONTRADICTED/INSUFFICIENT/NA; `notes` say "not semantic" |
| Constrained router (`satquery_core.routing`) | **INTEGRATED** (spec + code + 8 tests, G3) | deterministic rules; `docs/research/ROUTING_SPEC.md`; not yet called from an endpoint |
| Confidence methodology | **NONE** (by design) | nothing emits a confidence value; `EvidenceItem` has no confidence field |
| Semantic verification | **NONE** | verifier is structural only |
| Agentic (LLM) router / `POST /analyze` | **DESIGNED** | `ROUTING_SPEC.md` §"not covered"; deterministic router is the current substrate |

**Reminder:** no row here is VALIDATED for a *model on a task* — that needs a real
benchmark under our evaluation (EXP-004 Run 2, EXP-002, EXP-003).
