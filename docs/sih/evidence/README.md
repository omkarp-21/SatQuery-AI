# SIH Evidence Pack

> Purpose: **traceability, not slides.** Every claim that could appear in the SIH
> PPT (problem 26167) must trace to (a) a cited external source or (b) a SatQuery
> experiment with a recorded result. Slides are built later, from this. No claim
> is added to a slide until its row here says `TRACEABLE`.
>
> Status vocabulary: `TRACEABLE` (source or experiment recorded) ·
> `PARTIAL` (some support, gap noted) · `BLOCKED` (needs the remote GPU box) ·
> `TODO` (not yet collected).
> Date: **2026-09-04 (G20 — competition-grade UI/UX)**. G20 is UI/UX only — the
> local UI (`apps/backend/app/static/index.html`, still one file) rebuilt into a
> geospatial-intelligence workstation; PPT-ready screenshots in
> `docs/sih/evidence/ui/` (result screens rendered from the frozen `demos/final`
> captures through the shipped code — real data). No backend/model/API change.
> 419 fast tests pass. `docs/G20_UI_{AUDIT,QA,RELEASE_REPORT}.md`.
>
> Date: **2026-09-04 (G19 — SIH package + demo freeze)**. G19 is presentation
> packaging only (no new capability): `docs/G19_SIH_SOURCE_OF_TRUTH.md` +
> `docs/sih/*` (core story, pitch, architecture diagram, demo storyboard/runbook/
> script, backup demo, results-slide data, novelty argument, competitor
> comparison, top-30 judge Q&A, negative-results defense, research-honesty
> slide, use cases, roadmap, final checklist) + a distilled claim sheet in
> `CLAIM_MATRIX.md`. One code change: a "View full report ↗" button in the
> investigate UI. `FINAL_TECH_FREEZE = TRUE`. 383 fast tests pass.
> Date: **2026-09-03 (G18 — release candidate)**. G18 added: the larger-split D/E
> re-validation (§6 — the SAR benefit **did not survive**, claim withdrawn), the
> trust-layer rule validation (30 frozen cases / 7 families), the 22-condition
> failure matrix, the frozen final demo set (`demos/final/`), `POST
> /investigate/report` (HTML), and the release docs (`docs/G18_RELEASE_REPORT.md`,
> `docs/G18_RELEASE_AUDIT.md`, `docs/G18_RELEASE_MANIFEST.md`,
> `docs/sih/CLAIM_MATRIX.md`). G14+G15 added the agentic investigator
> (`/investigate`) — see rows 8 + 13. The G8 "BLOCKED — needs the remote box" rows are
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
| Real DFC2020 abs + rel SAR delta (G12, frozen 400/200 split) | `EXP-004.md` Run 2 — +0.067 abs macro-F1 (CROMA joint 0.793 vs optical 0.726); rel +9.2%; 95% CI [-0.024,+0.153] | TRACEABLE (sanity-scale, not significance-tested) |
| **G18 larger independent split (600/386): SAR benefit did NOT survive** | `evaluation/reports/exp004_run2_g18_larger_*` — CROMA joint 0.8247 vs optical-only 0.8505 (**Δ −0.026**, CI [−0.080,+0.027], McNemar p=1.0); DOFA fused 0.8177 vs optical 0.8374. **Sign flipped; never significant → CLAIM WITHDRAWN** (`docs/sih/CLAIM_MATRIX.md` §6). CROMA ≥ DOFA on both splits → CROMA stays capability-D primary. | TRACEABLE (**NEGATIVE** result, honestly reported) |
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
| **G17: HYBRID architecture + trust layer.** LLM produces a small typed `Intent` only; deterministic `PlanSynthesizer` builds the plan (reproduces `RuleBasedPlanner` exactly on a 10-mission equivalence check + fixes the G16 over-planning flaw). `HybridPlanner` + image-count plausibility guard + visible rule-intent fallback. **Trust layer** `assess_confidence` → evidence-derived category `HIGH/MEDIUM/LOW/INSUFFICIENT_EVIDENCE` (deterministic rules, `docs/G17_TRUST_LAYER.md`; **NOT a probability**). **100 frozen missions**, 3 arms (rule / pure-LLM carried from G16 / hybrid). Finding: the 2 B model misclassifies `task_family` on ~80 % of missions + ~25 % unparseable → **Architecture A (pure deterministic) stays the production default**; C is a built/safe/measured enhancement that doesn't beat A on this hardware. `--lora-weights` plumbed through `CromaAdapter`; larger DFC2020 D/E split (986) extracted (G12 split untouched). | `docs/G17_HYBRID_AGENT_REPORT.md`; `docs/G17_ARCHITECTURE_DECISION.md`; `docs/G17_TRUST_LAYER.md`; `docs/G17_SUCCESS_CRITERIA.md`; `evaluation/agent/reports/G17_HYBRID_EVALUATION.{md,json}`; `test_g17_agent.py` (23) | TRACEABLE (internal frozen eval, **not a benchmark**; ARM C N is CPU-limited and stated) |
| **G16: REAL LLM planner validated — it cannot plan.** The local `LlmPlanner` (Qwen2-VL-2B, text-only, CPU) now actually runs behind schema-repair + truncation-salvage + deterministic fallback; `PlannerAttempt` provenance (raw model text never surfaced). 2-arm eval `run_g16_eval.py`: **ARM A** RuleBasedPlanner n=50 (PLAN_VALIDITY **1.00** / TOOL_SELECTION **1.00**) vs **ARM B** local 2 B n=15 (**0.25 / 0.40** — echoes the prompt example; SCHEMA_VALIDITY 1.00, 0 repairs). Semantic plan scorer (alt orderings accepted). **Exec (N=6):** structurally-valid echo plans passed the policy layer and ran → FACTUAL_CONSISTENCY **0.33**, forbidden-tool-that-RAN **0.67** → **fix:** `_plan_intent_mismatch` (re-plans mission-wrong LLM plans with RuleBasedPlanner). Flagship CASE A/B: adaptivity holds (A=4 tool calls, B=2 + `NEW_EVIDENCE` early stop). Audit: G15's planning numbers were 100 % rule-based. | `docs/G16_PLANNER_AUDIT.md`; `docs/G16_REAL_LLM_EVALUATION.md`; `docs/G16_AGENT_VALUE_ANALYSIS.md`; `docs/G16_ADVERSARIAL_TESTS.md`; `docs/G16_SUCCESS_CRITERIA.md`; `evaluation/agent/reports/G16_REAL_LLM_EVALUATION.{md,json}`; `test_g16_agent.py` (23) | TRACEABLE (internal frozen eval, **not a benchmark**; ARM B N & exec N are CPU-limited and stated) |
| **G14+G15: AGENTIC investigator** — typed planner (`RuleBasedPlanner` / local `LlmPlanner`) → 12-check deterministic POLICY layer → bounded observe/**structured-replan** executor (closed 6-reason enum) + explicit **early termination** + visible deterministic fallback (`PLANNER_UNAVAILABLE`/`SPECIALIST_DEGRADED`); router NOT replaced. **G15 eval (50 frozen missions, 13 metrics each with N):** plan validity 1.00 (44 supported), adversarial-correctly-handled 1.00 (6), tool-selection 1.00 (49), task-order 1.00, dependency-validity 1.00 (203 edges); exec phase (N=14, real frozen-stack models, CPU): MISSION_COMPLETION 1.00, EVIDENCE_PRESERVATION 1.00 (n=13), VERIFICATION_PRESERVATION 1.00, FACTUAL_CONSISTENCY 1.00, UNSUPPORTED_ACTION_RATE 0.00 (17), UNNECESSARY_TOOL_CALL_RATE 0.00 (20), EARLY_STOP_EFFICIENCY 1.00 (n=1); baseline-vs-agent (N=3): agent 2.33 vs deterministic 1.0 specialists | `docs/G15_AGENT_IMPLEMENTATION.md`; `docs/G15_AGENT_EVALUATION.md`; `docs/research/EXP-006_AGENTIC_PLANNER.md`; `evaluation/agent/reports/G15_AGENT_EVALUATION.{md,json}`; `test_g14_agent.py` + `test_g15_agent.py` (~57) | TRACEABLE (internal frozen eval, **not a benchmark**) |

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
| **G15: flagship investigation, 2 phrasings** — `scripts/demo/run_g15_flagship.py` → `docs/sih/evidence/demos/g15_investigation_flagship_{0,2}.json` (real models, ~92 s; identical planner-produced 9-step plan `VALIDATE→TEMPORAL_CHANGE→EXTRACT_CHANGED_REGIONS→GROUND_OBJECT→OPTICAL_SAR_ANALYSIS→CROSS_CHECK→VERIFY→SUMMARIZE→FINALIZE`; 4 specialist calls; ChangeFormer+RemoteSAM+CROMA; ~25.3% changed, 6 regions, 6-feature GeoJSON; verification SUPPORTED) | TRACEABLE — **no hard-coded flagship workflow; plan emerges from planning** |
| **G17: flagship with the HYBRID architecture, CASE A vs CASE B** — `scripts/demo/run_g17_flagship.py` → `docs/sih/evidence/demos/g17_hybrid_flagship_case{A,B}.json` (real models). Both: `INVESTIGATION` intent (LLM intent unusable on this verbose phrasing → visible `rule_based_fallback`) → synthesised 9-step plan. **CASE A** (real change): 4 tool calls, SUPPORTED, **HIGH** confidence, 230 s. **CASE B** (near-identical T1/T2): 2 tool calls, `NEW_EVIDENCE`+`TOOL_FAILURE` replans, `early_stopped=True`, SUPPORTED, **MEDIUM** confidence, 145 s. Exec sample `mi-02/03/04` used the `hybrid_llm` intent path successfully. | TRACEABLE — **plan synthesised from the extracted/fallback Intent; execution responds to the real ChangeFormer output; evidence-derived confidence category** |
| **G16: flagship with the ACTUAL local LLM, CASE A vs CASE B** — `scripts/demo/run_g16_flagship.py` → `docs/sih/evidence/demos/g16_llm_flagship_case{A,B}.json` (real models). Both cases: LLM echoes `VALIDATE→run_vqa→VERIFY→FINALIZE` → `PLAN_INTENT_MISMATCH` → re-plan with RuleBasedPlanner. **CASE A** (real change): 4 tool calls, `~25.3% changed / 6 regions / 1 structure`, SUPPORTED, not early-stopped. **CASE B** (near-identical T1/T2): 2 tool calls, `NEW_EVIDENCE` replan, `early_stopped=True`, no fabricated change. | TRACEABLE — **execution path depends on observations; LLM contributed nothing (both `planner_used: rule_based_fallback`)** |
| Demo captures (real outputs, all 5) | `docs/sih/evidence/demos/g13_demo{1..5}_*.json` — VQA 26.7 s, grounding 29.0 s (box `[169,453,380,650]`), temporal 8.1 s (25.3% changed, EPSG:32650), optical+SAR 6.3 s (dim-768), investigation 44.9 s (6 regions) | TRACEABLE — **5/5 real, nothing faked** |
| **G18: FROZEN final demo set** — `scripts/demo/run_final_demo.py` (production `RuleBasedPlanner`) → `docs/sih/evidence/demos/final/`: **flagship CASE A** (real change: 4 tool calls, ~25.3% changed, 6 regions, 1 structure, SUPPORTED, **HIGH**, 93 s cold), **flagship CASE B** (minimal change: 2 tool calls, `NEW_EVIDENCE`+`TOOL_FAILURE` replans, `early_stopped`, SUPPORTED, **MEDIUM**, 17 s, **no fabricated change**), **secondary** ("Where is the largest ship?" → RemoteSAM box `[211,427,634,512]`, SUPPORTED, ~65 s cold). Each `*.report.html` is the `POST /investigate/report` render. | TRACEABLE — **one frozen mission, two cases; the shorter path is decided by the real ChangeFormer output, not hard-coded** |
| **G18: trust-layer rule validation + failure matrix** | `evaluation/agent/trust_cases.json` (30 cases / 7 families) + `test_g18_trust_cases.py` (32) — every confidence category matches the written policy; `test_g18_failure_matrix.py` (22) — every pathological input → structured resolution, no 500, no fabricated coordinate/box/confidence, no hidden fallback; `test_g18_claim_evidence.py` (69) — every demo claim traces to an observation, no forbidden wording | TRACEABLE (internal, rule-validated — **not calibration**) |

---

## Open items before the PPT

- ~~Fill every BLOCKED row from the remote box~~ - done on the local CPU box (G11/G12). Remaining: larger-n significance runs, 4 GB-VRAM check, EXP-C1/C2 confidence.
- Add 2–3 external citations for rows marked **PARTIAL** (rows 1, 2).
- D/E are now measured (sanity-scale, not significance-tested) - keep the differentiation claim modest until larger-n significance exists.
