# SIH Evidence Pack

> Purpose: **traceability, not slides.** Every claim that could appear in the SIH
> PPT (problem 26167) must trace to (a) a cited external source or (b) a SatQuery
> experiment with a recorded result. Slides are built later, from this. No claim
> is added to a slide until its row here says `TRACEABLE`.
>
> Status vocabulary: `TRACEABLE` (source or experiment recorded) ·
> `PARTIAL` (some support, gap noted) · `BLOCKED` (needs the remote GPU box) ·
> `TODO` (not yet collected).
> Date: **2026-09-01 (G8)**.

## The three numbers rule applies here

Any performance/accuracy figure is tagged **paper** (authors', cited) /
**reproduction** (we ran their code) / **SatQuery** (integrated, our evaluation).
A slide may say "SatQuery achieves X" **only** for a SatQuery-tagged number.

---

## 1. Problem evidence — the task is real and hard

| Item | Source | Status |
|------|--------|--------|
| PS 26167 wording + mandatory capabilities A–H | `chatgpt.context.md` §4; `docs/20_PROTOTYPE_ROADMAP.md` | TRACEABLE |
| Why NL-over-imagery matters (analyst workload, multi-sensor) | `docs/01_*` / `docs/16_SIH_JUDGING_STRATEGY.md` | PARTIAL — add 1–2 external refs on EO analyst bottlenecks |

## 2. Existing-system limitation — why current tools fall short

| Item | Source | Status |
|------|--------|--------|
| RS-VLMs are 7B+ and GPU-bound (GeoChat, TEOChat, SkyEyeGPT) | `docs/research/MODEL_TOURNAMENT.md`; `model_inventory.md` (GeoChat 7B, deepspeed/bnb unbuildable on Windows 4 GB) | TRACEABLE |
| Heavy models are hard to reproduce / license-unclear | `LIGHTWEIGHT_AUDIT.md` (SkyEyeGPT no inference recipe; ISRO-GeoNLI 36 GB wrapper; GeoChat no LICENSE file) | TRACEABLE |
| Generic VLMs are not RS-domain adapted | `LIGHTWEIGHT_AUDIT.md` (Qwen2-VL-2B = generic control) | TRACEABLE |
| No existing system threads geospatial-metadata integrity + verifiable evidence | `docs/03_SYSTEM_ARCHITECTURE.md`, `docs/07_EVIDENCE_ENGINE.md` | PARTIAL — this is our differentiation claim; keep it modest |

## 3. Research gap — what is unmeasured / unsolved

| Item | Source | Status |
|------|--------|--------|
| Capability gap matrix A–H with evidence levels | `docs/research/CAPABILITY_GAP_MATRIX.md` | TRACEABLE |
| A/B (VQA, grounding) unreproduced — artifact acquisition blocked ×6 | `EXP-002.md` (6-row attempt log) | TRACEABLE (as a documented blocker) |
| D (real optical-SAR benefit) unmeasured | `EXP-004.md` (Run 1 synthetic only) | TRACEABLE |
| E (RS adaptation before/after) unmeasured | `EXP-008.md` | TRACEABLE |
| Semantic verification / calibrated confidence unbuilt | `EXP-005.md`, `CONFIDENCE_PLAN.md` | PARTIAL — EXP-005b now measures a model-independent subset |

## 4. Model comparison — evidence-based selection, not prestige

| Item | Source | Status |
|------|--------|--------|
| 15-repo tournament + verdicts | `MODEL_TOURNAMENT.md` | TRACEABLE |
| Lightweight replacement audit (5 candidates vs TinyRS/GeoChat) | `LIGHTWEIGHT_AUDIT.md` | TRACEABLE |
| Frozen role hierarchy (ADR-011/012) | `docs/DECISIONS.md` | TRACEABLE |
| A/B decision table (measured cells) | `EXP-002.md` §"Phase 3 decision table" | **BLOCKED** — measured cells empty until the box |

## 5. Baseline vs adapted (capability E)

| Item | Source | Status |
|------|--------|--------|
| Method definitions locked (linear probe ≠ LoRA ≠ MLP head ≠ fine-tune) | `EXP-008.md` | TRACEABLE |
| Dataset chosen: DFC2020 val ROIs, 400/200 subsample | `EXP-004.md` | TRACEABLE |
| before → after numbers | `EXP-008.md` | **BLOCKED** |

## 6. Optical-only vs SAR (capability D)

| Item | Source | Status |
|------|--------|--------|
| 3-arm probe machinery validated (synthetic control) | `EXP-004.md` Run 1 — SAR-only signal: joint/fused 1.00 vs optical-only ~0.49 | TRACEABLE (**labelled sanity, NOT a benchmark**) |
| Real DFC2020 abs + rel SAR delta | `EXP-004.md` Run 2 | **BLOCKED** |
| CROMA vs DOFA both reproduced (CPU, MIT) | `runtime_validation.md`; `EVIDENCE_LEDGER.md` | TRACEABLE (reproduction) |

## 7. Change detection (capability C)

| Item | Source | Status |
|------|--------|--------|
| ChangeFormer reproduced: change-IoU 0.832 / F1 0.908 | `EVIDENCE_LEDGER.md` — n=7 bundled LEVIR-CD, CPU, 2026-09-01 (**reproduction**) | TRACEABLE |
| Temporal slice `/change` e2e: changed_fraction 0.2526, area 0.414 ha, bbox+centroid | `PROJECT_STATUS.md` METRICS — demo pair, integrated path | TRACEABLE (SatQuery integrated) |
| Composed semantic-change baseline + crop-strategy comparison | `EXP-003.md` §EXP-003b — agreement 4/6, `expanded` provisional default | TRACEABLE (experimental; **not** a learned VLM) |

## 8. Routing

| Item | Source | Status |
|------|--------|--------|
| Deterministic router: 6 rules, registry-driven, no LLM, 8 tests | `ROUTING_SPEC.md`; `packages/core/src/satquery_core/routing/` | TRACEABLE |
| Observable routing info in every `/analyze` response | `docs/API_CONTRACT.md` | TRACEABLE |
| VQA never routed to RemoteCLIP (`NO_VQA_SPECIALIST`) | `analyze.py`; `test_analyze_api.py` | TRACEABLE |
| **Failure-aware routing IMPLEMENTED** — `derive_resolution()` (6 qualifiers, pure fn of `verify()` + `verify_semantic()` + sub status) + single-step `image_difference_fallback` | `FAILURE_AWARE_ROUTING.md`; `apps/backend/app/services/failure_aware.py`; `test_failure_aware.py` (10); `API_CONTRACT.md` `resolution` field | TRACEABLE |

## 9. Geospatial safeguards

| Item | Source | Status |
|------|--------|--------|
| `validate_geotiff` + `check_pair_compatibility` — CRS/transform/bounds/GSD/bands/NoData/co-registration | `docs/08_GEOSPATIAL_ENGINE.md`; `packages/geospatial/` | TRACEABLE |
| EXP-007 stress: **15/15** malformed-pair classes rejected before any model runs | `EXP-007.md`; `test_exp007_geospatial_stress.py` | TRACEABLE (VALIDATED structural) |
| Live in `/analyze`, `/change`, `/scene` | `API_CONTRACT.md` | TRACEABLE |

## 10. Verification

| Item | Source | Status |
|------|--------|--------|
| Structural verifier P/R/F1 = 1.00 (n=24 curated); semantic miss rate 1.00 | `EXP-005.md`; `exp005_verifier_detection.py` + 3 lock tests | TRACEABLE (with the "curated, not coverage" caveat) |
| Model-independent semantic verifier P/R/F1 = 1.00 (n=34); BEYOND_SCOPE miss 1.00 | `EXP-005.md` §EXP-005b; `exp005b_semantic_verifier.py` + 9 lock tests | TRACEABLE (same caveat) |
| `verify_semantic` integrated into the composed baseline (additive field) | `semantic_change_baseline.py`; `test_semantic_change_baseline.py` | TRACEABLE |
| Confidence: none emitted; EXP-C1/C2 specified | `CONFIDENCE_PLAN.md` | TRACEABLE |

## 11. Latency

| Item | Source | Status |
|------|--------|--------|
| RemoteCLIP ~150 ms/query; ChangeFormer ~790 ms/256² pair; CROMA ~340 ms; DOFA ~120 ms (CPU, host) | `PROJECT_STATUS.md` METRICS | TRACEABLE (measured, host) |
| VQA/grounding p50/p95 | `exp002_ab_gate.py` output | **BLOCKED** |

## 12. Architecture

| Item | Source | Status |
|------|--------|--------|
| Monorepo split + fixed pipeline stage order | `docs/03_SYSTEM_ARCHITECTURE.md`; ADR-001 | TRACEABLE |
| SpecialistAdapter contract (validate/execute/normalize_output/provenance/run) | `docs/architecture/SPECIALIST_CONTRACT.md` | TRACEABLE |
| Research repos isolated, never imported | `.claude/rules/architecture.md`; `external/research/` gitignored | TRACEABLE |
| 3 live endpoints, 97 tests | `PROJECT_STATUS.md` | TRACEABLE |

## 13. User workflow

| Item | Source | Status |
|------|--------|--------|
| `POST /analyze` — NL query + 0–2 images → interpret → validate → route → specialist → evidence + verification + provenance | `API_CONTRACT.md` | TRACEABLE |
| Demo captures (real outputs) | `docs/sih/evidence/demos/` (Phase 14) | PARTIAL — DEMO 2/4/5 captured; DEMO 1/3 BLOCKED |

---

## Open items before the PPT

- Fill every **BLOCKED** row from the remote-box experiment runs.
- Add 2–3 external citations for rows marked **PARTIAL** (rows 1, 2).
- Keep the differentiation claim (row 2, last line) modest until D/E are measured.
