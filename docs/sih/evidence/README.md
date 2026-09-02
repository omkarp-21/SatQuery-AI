# SIH Evidence Pack

> Purpose: **traceability, not slides.** Every claim that could appear in the SIH
> PPT (problem 26167) must trace to (a) a cited external source or (b) a SatQuery
> experiment with a recorded result. Slides are built later, from this. No claim
> is added to a slide until its row here says `TRACEABLE`.
>
> Status vocabulary: `TRACEABLE` (source or experiment recorded) ·
> `PARTIAL` (some support, gap noted) · `BLOCKED` (needs the remote GPU box) ·
> `TODO` (not yet collected).
> Date: **2026-09-02 (G14)**. G14 added the agentic investigator (`/investigate`) — see rows 8 + 13. The G8 "BLOCKED — needs the remote box" rows are
> now mostly cleared: A/B (G11), D/E (G12) closed on the local CPU box via
> `hf_transfer` + non-gated mirrors; G13 added real end-to-end demo captures
> (`docs/sih/evidence/demos/g13_demo*.json`). Remaining hard gaps: 4 GB-VRAM
> verification, significance testing at larger n, calibrated confidence.

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
| A/B (VQA, grounding) — **MEASURED + INTEGRATED (G11)** | `EXP-002.md` §G11 — TinyRS-2B bal-acc 0.87 (RSVQA-LR n=40); RemoteSAM acc@IoU0.5 0.84 (DIOR-RSVG n=25); ADR-020 | TRACEABLE (sanity-scale) |
| D (real optical-SAR benefit) — **MEASURED (G12)** | `EXP-004.md` Run 2 — CROMA joint macro-F1 0.793 vs optical 0.726 (+0.067, DFC2020 n=200, 95% CI includes 0) | TRACEABLE (sanity-scale, **not significance-tested**) |
| E (RS adaptation before/after) — **MEASURED (G12)** | `EXP-008.md` — LoRA on frozen CROMA 0.643 → 0.704 (+0.061), 811 k params | TRACEABLE (sanity-scale, **not significance-tested**) |
| Semantic verification / calibrated confidence unbuilt | `EXP-005.md`, `CONFIDENCE_PLAN.md` | PARTIAL — EXP-005b now measures a model-independent subset |

## 4. Model comparison — evidence-based selection, not prestige

| Item | Source | Status |
|------|--------|--------|
| 15-repo tournament + verdicts | `MODEL_TOURNAMENT.md` | TRACEABLE |
| Lightweight replacement audit (5 candidates vs TinyRS/GeoChat) | `LIGHTWEIGHT_AUDIT.md` | TRACEABLE |
| Frozen role hierarchy (ADR-011/012) | `docs/DECISIONS.md` | TRACEABLE |
| A/B decision table (measured) | `EXP-002.md` §G11 — TinyRS-2B PRIMARY (0.87), Qwen2-VL-2B fallback (0.70), RSCoVLM-3B non-existent | TRACEABLE |

## 5. Baseline vs adapted (capability E)

| Item | Source | Status |
|------|--------|--------|
| Method definitions locked (linear probe ≠ LoRA ≠ MLP head ≠ fine-tune) | `EXP-008.md` | TRACEABLE |
| Dataset chosen: DFC2020 val ROIs, 400/200 subsample | `EXP-004.md` | TRACEABLE |
| before → after numbers | `EXP-008.md` — 0.643 (frozen) → 0.704 (LoRA), +0.061 macro-F1, DFC2020 n=200 | TRACEABLE (sanity-scale, not significance-tested) |

## 6. Optical-only vs SAR (capability D)

| Item | Source | Status |
|------|--------|--------|
| 3-arm probe machinery validated (synthetic control) | `EXP-004.md` Run 1 — SAR-only signal: joint/fused 1.00 vs optical-only ~0.49 | TRACEABLE (**labelled sanity, NOT a benchmark**) |
| Real DFC2020 abs + rel SAR delta | `EXP-004.md` Run 2 — +0.067 abs macro-F1 (CROMA joint 0.793 vs optical 0.726); rel +9.2%; 95% CI [-0.024,+0.153] | TRACEABLE (sanity-scale, not significance-tested) |
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
| **G14: AGENTIC investigator** — typed planner (`RuleBasedPlanner` / local `LlmPlanner`) → 12-check deterministic POLICY layer → bounded observe/replan executor (≤ 8 tool calls); router NOT replaced (execution guard). Eval (30 frozen missions): plan validity 0.967, tool-selection 1.00, task-order 1.00; exec success/evidence/verification preservation 1.00, forbidden-tool rate 0.00; agent runs 2.5× the specialists of the single-shot baseline on multi-step missions | `docs/G14_AGENTIC_REPORT.md`; `docs/research/EXP-006_AGENTIC_PLANNER.md`; `evaluation/agent/reports/latest.json`; `test_g14_agent.py` (~30, incl. 18 failure cases) | TRACEABLE (internal frozen eval, **not a benchmark**) |

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
| RemoteCLIP ~150 ms/query; ChangeFormer ~790 ms/256² pair; CROMA ~340 ms; DOFA ~120 ms (CPU, host, warm) | `PROJECT_STATUS.md` METRICS | TRACEABLE (measured, host) |
| VQA/grounding p50 — TinyRS 4.5 s, RemoteSAM 29 s (CPU, warm) | `EXP-002.md` §G11, `EXP-GROUNDING.md` | TRACEABLE (sanity-scale) |
| **G13 end-to-end (cold, incl. model load):** VQA 26.7 s · grounding 29.0 s · temporal 8.1 s · optical+SAR 6.3 s · investigation 44.9 s | `docs/G13_PRODUCTIZATION_REPORT.md` §7; demo captures | TRACEABLE (measured, host, CPU) |

## 12. Architecture

| Item | Source | Status |
|------|--------|--------|
| Monorepo split + fixed pipeline stage order | `docs/03_SYSTEM_ARCHITECTURE.md`; ADR-001 | TRACEABLE |
| SpecialistAdapter contract (validate/execute/normalize_output/provenance/run) | `docs/architecture/SPECIALIST_CONTRACT.md` | TRACEABLE |
| Research repos isolated, never imported | `.claude/rules/architecture.md`; `external/research/` gitignored | TRACEABLE |
| 6 endpoints (`/`, `/health`, `/analyze`, `/analyze/upload`, `/change`, `/scene`, `/artifact`), 183 tests | `PROJECT_STATUS.md`; `docs/G13_PRODUCTIZATION_REPORT.md` | TRACEABLE |

## 13. User workflow

| Item | Source | Status |
|------|--------|--------|
| `POST /analyze` — NL query + 0–2 images → interpret → validate → route → specialist → evidence + verification + provenance | `API_CONTRACT.md` | TRACEABLE |
| **G13: `POST /analyze/upload` + `GET /` UI + `NormalizedResponse`** — upload → same pipeline → one flat schema; local UI renders answer + overlay + evidence + verification + trace + provenance | `docs/G13_PRODUCTIZATION_REPORT.md`; `API_CONTRACT.md` | TRACEABLE |
| **G14: `POST /investigate` — natural-language MISSION → agent plan → policy → observe/replan → evidence-first report** | `docs/G14_AGENTIC_REPORT.md`; `API_CONTRACT.md`; flagship capture `docs/sih/evidence/demos/g14_flagship_investigation.json` (9 steps COHERENT, ChangeFormer+RemoteSAM+CROMA, verification SUPPORTED) | TRACEABLE — **real models, planner-produced plan** |
| Demo captures (real outputs, all 5) | `docs/sih/evidence/demos/g13_demo{1..5}_*.json` — VQA 26.7 s, grounding 29.0 s (box `[169,453,380,650]`), temporal 8.1 s (25.3% changed, EPSG:32650), optical+SAR 6.3 s (dim-768), investigation 44.9 s (6 regions) | TRACEABLE — **5/5 real, nothing faked** |

---

## Open items before the PPT

- ~~Fill every BLOCKED row from the remote box~~ - done on the local CPU box (G11/G12). Remaining: larger-n significance runs, 4 GB-VRAM check, EXP-C1/C2 confidence.
- Add 2–3 external citations for rows marked **PARTIAL** (rows 1, 2).
- D/E are now measured (sanity-scale, not significance-tested) - keep the differentiation claim modest until larger-n significance exists.
