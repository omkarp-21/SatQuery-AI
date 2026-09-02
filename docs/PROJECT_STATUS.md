# SatQuery — Project Status

> Living status file (see `chatgpt.context.md` §24). Update every significant
> session. No fabricated numbers — "not measured" is the honest value until a real
> run exists. Last updated: **2026-09-02 (G16)**. Tests: **fast suite green + 23
> new G16 tests** (rerun pending clean). **MODEL STACK FROZEN (ADR-021).**
> **G14 + G15: agentic geospatial investigator** — `POST /investigate`; typed
> planner + 12-check policy guard + bounded observe/**structured-replan**
> executor; 50 frozen missions, 13 measured quality metrics. **G16: real local
> LLM planner validated — it cannot plan.** Qwen2-VL-2B (text-only, CPU) echoes
> its prompt example (semantic plan validity **0.25** vs rule **1.00**, N=15);
> exec (N=6) caught structurally-valid wrong plans running the wrong specialist →
> G16 adds a **plan-intent cross-check**; `RuleBasedPlanner` stays the default.
> `docs/G16_*`. The differentiating feature. EXP-006.

---

## DONE (and how it was verified)

| Item | Verification |
|------|--------------|
| PS 26167 requirements captured | `chatgpt.context.md` §4; mapped in `docs/20_PROTOTYPE_ROADMAP.md` |
| Monorepo structure `apps/` + `packages/` + `external/` | `git ls-files`; ADR-001 in `docs/DECISIONS.md` |
| Claude Code harness: `CLAUDE.md`, 10 rules, 18 skills, 11 subagents | files present under `.claude/`; frontmatter checked |
| `docs/19` reconciled to canonical 7 experiments (EXP-001…007); doc stubs 03/05/06/07/08/11/16 fleshed out; `.claude/rules/scope.md` added | reviewed `SatQuery_Claude_Bootstrap` (2026-09-01); it was a thinner earlier draft — only the missing routing/single-image experiments + scope rule were additive |
| **G1 runtime validation** — 5 repos, isolated venvs, official examples run | `docs/research/runtime_validation.md`. **RUNNING:** RemoteCLIP (CPU, correct), ChangeFormer (CPU, IoU 0.83/n=7, no source edits). **BLOCKED:** GeoChat (7B>4 GB VRAM; deepspeed/bnb), Change-Agent (mmcv 1.3.1 build), ChangeChat (no weights). Host GPU = RTX 3050 Ti 4 GB, no conda/Docker/WSL. |
| **G1.5 capability gap matrix** — 8 mandatory reqs (A–H) mapped; candidates scouted | `docs/research/CAPABILITY_GAP_MATRIX.md` (ADR-005). Candidates recorded (not adopted): TinyRS, TEOChat, CROMA, DOFA, MaRS. |
| **G1.6 model tournament** — 15-repo pool validated; CROMA + DOFA reproduced | `docs/research/MODEL_TOURNAMENT.md` + `EXPERIMENT_DECISION_TREE.md` (ADR-006). **REPRODUCED (CPU):** CROMA (194 M, MIT), DOFA (111 M, MIT). **RE-VERIFIED REJECT:** ChangeChat, RS-MoE. **TEST FURTHER local:** TinyRS, RSCoVLM-3B. Remote-GPU only: GeoChat, GeoGround, TEOChat, UniRS, LRS-VQA. |
| **G2 · Track C — geospatial vertical slice** | `packages/geospatial/{raster,validation,errors}.py` + 13 passing tests. `validate_geotiff` (format/dims/CRS/transform/bounds/bands/NoData) + `check_pair_compatibility` (co-registration gate). `.venvs/satquery`. |
| **G2 · Track D — temporal vertical slice (real end-to-end)** | `scripts/research/changeformer_infer.py` bridge + real `ChangeFormerAdapter` (subprocess to `.venvs/changeformer`, no repo import) + `apps/backend/app/services/temporal_slice.py`. T1/T2 GeoTIFF → validate → co-reg → ChangeFormer → mask → area/bbox/centroid → `ChangeSliceResult` + provenance. Demo pair `data/demo/temporal/`; 4 fast + 2 slow tests pass; changed_fraction **0.2526** matches G1 `demo_LEVIR.py`. Misregistered pairs blocked by the gate. **No confidence value produced.** |
| **G2 · Track B — EXP-004 controlled sanity check** | `docs/research/EXP-004.md`. 3-arm probe on real CROMA + DOFA encoders (synthetic paired S1/S2, N=240/160, seed 20260901, CPU): SAR-only signal recovered by CROMA-joint & DOFA-fused (1.00), at chance for optical-only (~0.49). **Directional H3 signal — NOT a benchmark** (no S1+S2 labelled set: DFC2020 = 11 GB). |
| **G2 · Track A — EXP-002 setup** | `docs/research/EXP-002.md`. `.venvs/tinyrs` + transformers 4.49 built; usability threshold fixed. **N=0.** |
| **G2.5 · adapters** | Standard `SpecialistAdapter` interface (`validate / execute / normalize_output / provenance` + `run()` template). Real adapters for **ChangeFormer, RemoteCLIP, CROMA, DOFA** — all subprocess to `.venvs/<model>` via `scripts/research/*_infer.py`; no research-repo imports. Smoke tests pass (RemoteCLIP → airport 0.989; CROMA/DOFA → dim-768 embeddings). |
| **G2.5 · model registry** | `packages/model_adapters/model_registry.yaml` v2 — measured facts per model (env, checkpoint size, latency, params, licence, **evidence_level**, status). `ADAPTERS` name→class map + `routing` table (rule-over-registry). |
| **G2.5 · first API — `POST /change`** | `apps/backend/app/api/change.py` wired into `main.py`. `{t1_path,t2_path}` → validate → co-reg gate → ChangeFormer adapter → mask → area/bbox/centroid → provenance → JSON. Path-traversal + 404 + model-unavailable guards. `test_change_api.py`: happy path 200 + structured body; **33/33 tests pass**. |
| **G2.5 · EXP-002** | **TEST FURTHER — blocked on artifact acquisition.** 3 download attempts (2× `ChunkedEncodingError`, 1 DNS fail, hf_xet inconclusive) over ~50 min; TinyRS safetensors never completed. Not a capability/compute blocker. |
| **G2.5 · EVIDENCE_LEDGER.md** | new — one row per model×claim at its highest real level. |
| **G3 · evidence + verification package** | `packages/evidence`: `EvidenceItem` (no confidence field, by design), standardized `Provenance.from_adapter` + `scrub()`, deterministic `verify()` → `SUPPORTED / CONTRADICTED / INSUFFICIENT_EVIDENCE / NOT_APPLICABLE` (structural checks only). 9 tests. |
| **G3 · constrained router** | `packages/core/routing`: `RoutingRequest → RoutingDecision`, 6 deterministic rules, reads capabilities from the registry, honest `NO_VQA_SPECIALIST` code. `docs/research/ROUTING_SPEC.md`. 8 tests. **No LLM.** |
| **G3 · `POST /scene`** | RemoteCLIP single-image slice — validate → adapter → ranking → EvidenceItem + Provenance + verification → JSON. Path guards. Explicitly not a VQA endpoint. 4 tests (1 slow). |
| **G3 · `/change` upgraded** | now emits `evidence[]` (change-mask) + `verification` (SUPPORTED) + a `standardized` provenance block, **without changing existing fields** — regression test asserts changed_fraction 0.2526 unchanged. |
| **G3 · multimodal internal contract** | `run_joint_representation(optical, sar, model=croma\|dofa)` → `JointReprResult` (rep vectors + evidence + provenance + structural verify). **No `/fusion` endpoint** — representation-level only until EXP-004 Run 2. 4 tests. |
| **G3 · adapter contract finalized** | `AdapterResult` now carries `status`, `timing_s`, `model_meta`. Registry entries got a `fallback` field. `docs/architecture/SPECIALIST_CONTRACT.md`, `docs/API_CONTRACT.md`. |
| **G3 · tests** | **59 passed, 0 failed** (baseline was 33). No regressions. |
| **G4 · `POST /analyze`** | Unified deterministic layer: query → `interpret_query` (keyword→intent, NO LLM) → validate (safeguards preserved) → `route()` → dispatch (scene / change / composed-semantic / joint-repr) → aggregate evidence + verification + provenance. Returns observable routing info (task, specialist, rule, code, inputs, order, status). VQA → `NO_VQA_SPECIALIST` (never routed to RemoteCLIP); misregistered pair → `VALIDATION_FAILED`. 13 tests. |
| **G4 · COMPOSED_SEMANTIC_CHANGE_BASELINE** | `apps/backend/app/services/semantic_change_baseline.py` — ChangeFormer mask → `scipy.ndimage` connected components → per-region T2 crop → RemoteCLIP tagging (fixed RS-change vocab) → rule-assembled description + regions + evidence + provenance + `failures[]`. Explicit disclaimers ("NOT a temporal VLM / learned / validated"). On the demo pair: 0.41 ha over 6 regions, tags noisy on 8–32 px crops (documented failure mode). 5 tests. |
| **G4 · EXP-007 geospatial stress** | `docs/research/EXP-007.md` — **15/15 safeguard cases pass** (CRS/transform/shape/res mismatch, missing CRS, invalid raster, bomb guard ×2, path traversal, NoData, `/change` gate). Safeguards **not weakened**. |
| **G4 · confidence plan** | `docs/research/CONFIDENCE_PLAN.md` — candidate sources + required experiments (EXP-005, EXP-C1, EXP-C2). **No confidence number emitted anywhere.** |
| **G4 · EXP-002 / EXP-004 Run 2 / EXP-008** | **BLOCKED — artifact/dataset acquisition fails from this host** (TinyRS 4 attempts <1 MB/s; DFC 11 GB / So2Sat 7 GB / EuroSAT-SAR 922 MB all too large). **Remote GPU now justified on infrastructure grounds.** |
| **G4 · tests** | **92 passed, 0 failed** (baseline 59). No regressions. |
| **G16 — real LLM agent validation** | Audit `docs/G16_PLANNER_AUDIT.md` — G15's planning numbers were **100 % `RuleBasedPlanner`**; the `LlmPlanner` had never run (wrong checkpoint path, 60 s timeout vs a >600 s cold call, ~2 800-token prompt on a CPU-only 2 B model). **Fixed:** checkpoint-path resolver; **compact ~1.4 k-token prompt** (one-line tool list + JSON skeleton, not a copyable few-shot); `planner_infer.py --serve` **persistent model server**; **`agent/repair.py`** — parse → safe intent-preserving repair (renumber ids, coerce `depends_on`, map near-miss tool names, prepend VALIDATE / append VERIFY+FINALIZE, **salvage** complete step objects from truncated JSON) → validate, else deterministic fallback; over-long / specialist-less plans are **not** accepted. **`PlannerAttempt`** provenance (parse/schema/repair status, `final_source`, `fallback_reason`) in `provenance.planner_attempt` — **raw model text never surfaced**. `planner_used` gains `llm` / `llm_repaired`. **Eval** `evaluation/agent/run_g16_eval.py` — **2 arms** over the frozen set: **ARM A** RuleBasedPlanner **n=50**, **ARM B** local Qwen2-VL-2B text-only CPU **n=15** (stratified 3/category; ~100 s/plan) × **10 planning metrics each with N**, **semantic** plan scorer (`plan_scorer.py` — alternative valid orderings accepted). **Result:** ARM A PLAN_VALIDITY **1.00** / TOOL_SELECTION **1.00**; **ARM B PLAN_VALIDITY 0.25 / TOOL_SELECTION 0.40** — the 2 B model **echoes the prompt example** (same `VALIDATE→run_vqa→VERIFY→FINALIZE` for every mission; correct only for the 3 VQA missions, 0/9 on temporal/opt-SAR/multi-step). SCHEMA_VALIDITY **1.00** (0 repairs, 0 fallbacks). **Exec (N=6, LLM planner in the loop):** the structurally-valid echo plans **passed the policy layer and ran** — FINAL_ANSWER_FACTUAL_CONSISTENCY **0.33**, forbidden-tool-that-RAN **0.67** (VQA answers to investigation missions, marked "SUPPORTED"). **Fix (Part 22):** `agent_runner._plan_intent_mismatch` — an intent cross-check vs the deterministic query interpreter, LLM-plans only, after policy; mission-wrong plans → visible `PLAN_INTENT_MISMATCH` fallback (fires 5/6 of the exec missions). Paraphrase (`run_paraphrase_eval.py`, 40/5 families): rule arm **1.00** family-consistency after a grounding-keyword patch. Flagship with the actual LLM in two environments → `docs/sih/evidence/demos/g16_llm_flagship_case{A,B}.json`. **+23 G16 tests** (`test_g16_agent.py`). **Decision:** KEEP the agent; **`RuleBasedPlanner` stays the DEFAULT** (and in practice the primary); LLM opt-in behind repair + policy + intent-check + fallback. The agent's multi-step value (2.33× baseline specialists) comes from the rule planner, not the LLM. Weakest measured component = the planner *model* — needs GPU + ≥7 B / planning-tuned, or an LLM-proposes/rules-fill hybrid. Docs: `docs/G16_PLANNER_AUDIT.md`, `G16_REAL_LLM_EVALUATION.md`, `G16_AGENT_VALUE_ANALYSIS.md`, `G16_ADVERSARIAL_TESTS.md`, `G16_SUCCESS_CRITERIA.md`. No new model; frozen stack unchanged; no confidence values. |
| **G15 — agent validation + flagship mission mode** | Audit `docs/G15_AUDIT.md`. **Structured replanning** — closed `ReplanReason` enum (`NEW_EVIDENCE / TOOL_FAILURE / MISSING_INPUT / INSUFFICIENT_EVIDENCE / VERIFICATION_CONTRADICTION / TASK_COMPLETE`) + `ReplanEvent` (`reason/triggering_step/previous_phase/detail/steps_skipped/ts`) surfaced in `result.replans[]` + the timeline. **Explicit early termination** (`_mission_complete` per family + `TASK_COMPLETE` + `early_stopped`/`completion_reason`). **MISSING_INPUT** (SAR requested, no distinct 2-band raster → CROMA/DOFA never called). **VERIFICATION_CONTRADICTION** (INCOHERENT step → its claim withheld from the conclusion). **Deterministic fallback is never invisible** — `resolution.qualifier ∈ {PLANNER_UNAVAILABLE, SPECIALIST_DEGRADED}`, an `AGENT FALLBACK` warning, blocking-policy-check names in the trace; `run_investigation` pre-reads CRS + co-registration so the **policy layer** rejects a temporal plan on a misregistered pair. **GeoJSON** (`result.geojson`, EPSG:4326 FeatureCollection). **Judge-facing INVESTIGATE panel** — Investigation result → agent plan & execution → replans table → key/spatial findings → verification → evidence → warnings → collapsible trace. **50 frozen missions** (5×10, richer schema) + `run_agent_eval.py` computing **13 metrics each with N**: plan validity **1.00** (44 supported), adversarial-correctly-handled **1.00** (6), tool-selection **1.00** (49), task-order **1.00**, dependency-validity **1.00** (203 edges); exec phase (N=14, real frozen-stack models, CPU): **MISSION_COMPLETION 1.00**, **EVIDENCE_PRESERVATION 1.00** (n=13), **VERIFICATION_PRESERVATION 1.00**, **FACTUAL_CONSISTENCY 1.00**, **UNSUPPORTED_ACTION_RATE 0.00** (17 tool attempts), **UNNECESSARY_TOOL_CALL_RATE 0.00** (20 calls), **EARLY_STOP_EFFICIENCY 1.00** (n=1, tm-10 → `NEW_EVIDENCE` replan), avg 1.43 tool calls / 0.07 replans / 62 s per mission; **baseline-vs-agent** (N=3 multi-step): agent runs **2.33** required specialists vs deterministic **1.0**. Flagship captured with real models → `docs/sih/evidence/demos/g15_investigation_flagship_{0,2}.json` (2 phrasings, identical 9-step plan, SUPPORTED). **+27 tests** (`test_g15_agent.py` — per-policy-check + 10-paraphrase flagship + conditional-execution) + 2 slow real-model tests green. **203 fast pass, 0 regressions.** No new model; 4 GB-VRAM UNVERIFIED; RemoteSAM caveat + experimental-baseline label preserved; no confidence values. `docs/G15_AGENT_IMPLEMENTATION.md`, `docs/G15_AGENT_EVALUATION.md`, EXP-006, API_CONTRACT, README. |
| **G14 — agentic geospatial investigator (the differentiating feature)** | Audit → `docs/G14_AGENT_IMPLEMENTATION_MAP.md`. **New:** `packages/agents/src/satquery_agents/agent/` — typed `AgentPlan` + closed 12-task ontology + closed 12-tool registry (`registry.py`) + **12-check deterministic POLICY layer** (`policy.py`; blocks "RemoteSAM for VQA", cycles, >8 steps, misregistered pairs, …) + **planner** (`RuleBasedPlanner` default; `LlmPlanner` = local Qwen2-VL-2B text-only via `scripts/research/planner_infer.py`, opt-in, always falls back) + bounded executor `apps/backend/app/services/agent_runner.py` (state machine, ≤8 specialist calls, **observe → verify → conditionally replan**: tiny change → skip grounding; grounding fail → no fabricated box; misregistered → deterministic `/analyze` fallback; embedding → no invented fact). `POST /investigate` + UI **ASK / INVESTIGATE** toggle + agent plan/live-status panel. The deterministic router is **NOT** replaced — it's the execution guard. **Eval** `evaluation/agent/` (30 frozen missions, 6 categories): plan validity **0.967**, tool-selection **1.00**, task-order **1.00**; exec (12, real models) success **1.00**, evidence/verification preservation **1.00**, forbidden-tool rate **0.00**; **agent-vs-baseline** on multi-step missions: agent runs **2.5** required specialists avg vs deterministic **1.0**. **+~30 tests** (`test_g14_agent.py`, incl. the 18 failure cases). **179 fast pass, 0 regressions.** No new large model; 4 GB-VRAM still UNVERIFIED; no confidence values; RemoteSAM caveat + experimental-baseline label preserved. `docs/G14_AGENTIC_REPORT.md`, `docs/research/EXP-006_AGENTIC_PLANNER.md`, `API_CONTRACT.md`, `README.md`. |
| **G13 — end-to-end SatQuery MVP (one coherent product)** | Audit → implementation map (`docs/G13_IMPLEMENTATION_MAP.md`). **New product surface:** `GET /` self-contained local UI (vanilla JS + canvas overlay, no npm/build), `POST /analyze/upload` (multipart, per-request sandbox `data/uploads/<id>/`, 64 MB/file cap, type allow-list), `GET /artifact` (sandboxed mask serving). **`NormalizedResponse` + `normalize()`** (`app/services/normalize.py`) — flattens all 6 specialist outputs into one flat schema (answer/task/model/boxes/regions/mask_url/changed_fraction/area_ha/centroid_lonlat/score+meaning/crs/evidence/verification/resolution/provenance/execution_trace/warnings), only relevant fields filled, nothing invented, caveats → `warnings`. **`run_joint_from_geotiffs`** — paired S2+S1 GeoTIFF → CROMA (optical+SAR now works via `/analyze`). **Geo carve-out** — CRS-less-but-structurally-sound GeoTIFF → pixel-level analysis + explicit "no geographic coordinates"; **corrupt raster no longer 500s** → clean `VALIDATION_FAILED` (bug found by integration test). **`scripts/demo/run_demos.py`** — 5 real deterministic scenarios → real captures in `docs/sih/evidence/demos/`. **+17 tests** (`test_g13_integration.py`: 12 fast + 5 slow real-model), all green; **153 fast total, 0 regressions**. New dep: `python-multipart` (upload only). No LLM planner, no confidence value, no architecture change (additive fields/params). `docs/G13_PRODUCTIZATION_REPORT.md`, `API_CONTRACT.md`, `README.md` updated. |
| **G12 — D + E closed on real DFC2020; MODEL STACK FROZEN (ADR-021)** | Same `hf_transfer` + non-gated mirror recipe cleared the S1+S2 dataset wall that blocked EXP-004 Run 2 for 4 gates. `125oii/dfc2020` → DFC2020 `ROIs0000_validation` (S1 947 MB + S2 633 MB + labels) in ~2.5 min. **No synthetic substitution.** Frozen split `evaluation/datasets/dfc2020_exp004_split.json` (400 train / 200 eval, seed 20260902), task = dominant DFC land-cover (8 classes). **EXP-004 Run 2 (D):** frozen encoder → LogisticRegression probe + 2000× bootstrap + McNemar. **CROMA joint macro-F1 0.793 vs CROMA optical 0.726 (+0.067; 95% CI [−0.024,+0.153] includes 0 → positive, NOT significant at n=200; McNemar p=0.45).** DOFA concat-fusion −0.018 (no gain). **KEEP CROMA** (optical-SAR PRIMARY; won 0.793 vs DOFA 0.708); DOFA = fallback. H3 = lean-KEEP. **EXP-008 (E):** LoRA r=8 (811k trainable params = 0.4% of CROMA, 3.24 MB adapter) on the same split → held-out macro-F1 0.643 (frozen) → 0.704 (adapted), **+0.061 ≥ +0.03 threshold → ADOPT LoRA** as the E method (prod default stays frozen pending a larger-split bootstrap; adapter not yet persisted). CPU throughout — no VRAM figure. New `exp004_run2_{extract,features,probe}.py` + `exp008_adapt.py`. Registry: croma/dofa `evidence_level: measured`. **FREEZE GATE: A✅ B✅ D✅ E✅ + routing/geo/evidence pass + no arch blocker → MODEL STACK FROZEN.** 141 fast tests green. ADR-021. |
| **G11 — A + B both MEASURED + INTEGRATED; download wall cleared** | `HF_HUB_ENABLE_HF_TRANSFER=1` pulled TinyRS-2B / Qwen2-VL-2B / RemoteSAM weights (all previously failed 7×); non-gated HF mirrors found for DIOR-RSVG (`pzhang1990`) + RSVQA-LR (`dmarsili`). **A (VQA):** TinyRS-2B = **balanced acc 0.8736** on 40 RSVQA-LR yes/no (CPU, p50 4.45 s) → PRODUCTION PRIMARY; Qwen2-VL-2B control 0.7033 → FALLBACK. `TinyRsAdapter` + `run_vqa` + router `SINGLE_IMAGE_VQA` + `/analyze` VQA path + `vqa` `EvidenceItem`. **RSCoVLM-3B confirmed non-existent** (only 7B). **B (grounding):** RemoteSAM = **acc@IoU0.5 = 0.84 (21/25)** on frozen DIOR-RSVG (CPU, p50 29 s, 0 no_box). Registry: tinyrs + remotesam `evidence_level: measured`. **RemoteSAM licence: NOT STATED** (`REMOTESAM_LICENSE.md`, verified). GPU/4 GB-VRAM unverified for both (CPU host). **Track F (resolution):** on 10 in-domain DIOR cases downscaled to 256 px, native-256 grounding = acc@IoU0.5 **0.90 / 0 no_box**; 2× pre-upscale did not help (0.90), padded canvas hurt (0.70) → **production preprocessing unchanged**; the G10 LEVIR `no_box` reclassified as a **domain** limit, not resolution (`REMOTE_SAM_RESOLUTION.md`). +15 tests. **Two-specialist A/B design is real + measured.** ADR-020. |
| **G10 — RemoteSAM grounding specialist REPRODUCED + INTEGRATED** | Capability **B: DOCUMENTED → REPRODUCED + INTEGRATED** (not MEASURED). RemoteSAM (`1e12Leon/RemoteSAM`, ~200 M Swin-B+BERT, ACM MM 2025) runs locally on **CPU** via `.venvs/remotesam` (`mmcv` **lite** 1.7.1 — the grounding path needs no compiled mmcv/mmdet/mmseg). Checkpoint `RemoteSAMv1.pth` 2.57 GB downloaded. Smoke: **3/5** phrases → in-bounds box+mask, prob ≈ 0.97–1.0; 2 `no_box` (1 OOD 256 px tile). Peak RSS ~8 GB, ~16–22 s/query steady-state. `RemoteSamAdapter` + `grounding_slice.run_grounding` + router `SINGLE_IMAGE_GROUNDING → [remotesam]` + `/analyze` grounding intent + grounding `EvidenceItem` + structural `verify()` (box-valid, mask-artifact). **VQA still `NO_VQA_SPECIALIST`** (RemoteSAM never routed for VQA). **Licence: NOT STATED** upstream — recorded verbatim. **DIOR-RSVG acc@IoU0.5 NOT measured** (Google-Drive-only dataset). GPU/4 GB-VRAM **unverified** → classified `CPU-FALLBACK`. +25 tests → **131/131**. Docs: `EXP-GROUNDING.md`, `GROUNDING_PIPELINE.md`. ADR-019. |
| **Local Lightweight Model Tournament** | `docs/research/LOCAL_LIGHTWEIGHT_MODEL_TOURNAMENT.md`. Inspected 3 new candidates from official GitHub/HF (no capability inferred from titles). **RemoteSAM** (`1e12Leon/RemoteSAM`, ~200 M Swin-B+BERT referring-seg + visual-grounding, mask+box, ACM MM 2025) → **TEST FURTHER, lead capability-B candidate** — a dedicated grounding *specialist*, not a VLM side-task; `LOCAL-FITS-4GB`, repro BLOCKED on `mmcv-full==1.7.1` env + unstated licence. **RS-MoE** (`CongcongWen1208/RS-MoE`) → **REJECT** — training-only, "MoE not yet implemented", base Vicuna-13B, "RS-MoE-1B" is a paper claim. **DynamicVis** (`KyanChen/DynamicVis`) → **REJECT for product** — Mamba SSM is Windows + CPU incompatible (breaks the 4 GB ASUS + CPU-fallback target); encoder-only, no A/B. **Product confirmed to have NO mandatory 7B/16 GB dependency** — EarthDial/GeoChat/GeoGround stay research-only. `model_registry.yaml` excluded block + `MODEL_TOURNAMENT.md` + `CAPABILITY_GAP_MATRIX.md` (B row) + `model_inventory.md` + `EVIDENCE_LEDGER.md` updated. No code, no new deps, no repos cloned. ADR-018. |
| **G9 — LOW_MARGIN advisory; remote loop halted** | Provisioning a cloud GPU is not an in-session action (5th identical block). **Built:** `ChangeRegion.tag_margin` / `.low_margin` (RemoteCLIP rank-1−rank-2 < 0.05); `derive_resolution(low_margin_regions=N)` → non-blocking `resolution.advisories` (`LOW_MARGIN: N region tag(s)…`) — answer still surfaced, weak tags flagged not dropped. +3 tests → **121/121**. `API_CONTRACT.md` + `FAILURE_AWARE_ROUTING.md` step 3 DONE. **Decision (ADR-017): stop re-running the remote-execution gate** — no new evidence is produced by another "still blocked" report; the next move is provisioning one Linux GPU box + running the 3 committed batch scripts. A/B/D/E, confidence, model freeze all remain blocked on that. |
| **G8 — failure-aware routing IMPLEMENTED (partial)** | Remote batches (A/B, optical-SAR, adaptation, confidence) still need the GPU box — not provisionable in-session. **Built locally:** **Phase 10** — `derive_resolution()` (`app/services/failure_aware.py`): pure deterministic function of `verify()` + `verify_semantic()` + sub-service status → 6 qualifiers (`RESULT_OK` / `RESULT_STRUCTURAL_FAIL` (withheld) / `RESULT_SEMANTIC_INCOHERENT` (disputed) / `RESULT_UNVERIFIED` / `SPECIALIST_DEGRADED` / `SPECIALIST_FAILED`) + `answer_surfaced`. Additive `resolution` field on `AnalyzeResult` (`ok` semantics unchanged). **`run_change_fallback()`** — image-difference + fixed-threshold change baseline (same geo-gate, own evidence+verify+provenance, `is_fallback:true`, "NOT ChangeFormer quality"); `/analyze` `TEMPORAL` calls it once if ChangeFormer fails → `SPECIALIST_DEGRADED`. No LLM, no loop, no recursion, **not a confidence**. `test_failure_aware.py` (10) + `API_CONTRACT.md` + `FAILURE_AWARE_ROUTING.md` marked IMPLEMENTED. **118/118 tests** (was 108). **Model stack NOT frozen** (A/B/D/E unmeasured). ADR-016. |
| **G7 — semantic verifier + evidence pack (partial)** | Remote-lab provisioning is a human infra action (not doable in-session); runbook ready. **Ran locally:** **EXP-005b** — new model-independent `verify_semantic()` (6 checks: claim↔number, claim↔label, temporal direction on swapped pairs, region-in-bounds/lon-lat, whole-scene region, area arithmetic; declares 3 model-dependent checks unavailable). Curated 34-case corpus → **precision/recall/F1 = 1.00** for internal-incoherence detection (TP 10/FP 0/TN 14/FN 0); **BEYOND_SCOPE miss rate 1.00** (label-correctness needs an independent model). Wired into `COMPOSED_SEMANTIC_CHANGE_BASELINE` as an additive `semantic_verification` field. `docs/research/EXP-005.md` §EXP-005b, 9 lock tests. **Also:** `docs/research/FAILURE_AWARE_ROUTING.md` (design — post-execution routing qualifiers + fallback ladder), `docs/sih/evidence/` (13-topic traceability pack + **real** captured DEMO 2/4/5 outputs; DEMO 1/3 explicit BLOCKED placeholders, no fake output), `model_registry.yaml` enriched (paper / quantization / memory / benchmark-vs-our-measured split). **Model stack NOT frozen** — A/B/D/E still unmeasured. **108/108 tests** (was 97). ADR-015. |
| **G6 — capability closure (partial)** | Model discovery **stopped**; hierarchy frozen. **Ran locally:** (1) **EXP-005** — structural verifier detection **precision/recall/F1 = 1.00** on a curated 24-case corpus (TP 8/FP 0/TN 12/FN 0); **semantic-defect miss rate = 1.00** (`docs/research/EXP-005.md`, 3 lock tests). (2) **EXP-003b** — added `crop_strategy` ∈ {tight,expanded,mask_aware} to the composed baseline; 3-way run on the demo pair → **agreement 4/6 regions**, `expanded` rescued a `tight` miss, `mask_aware` monoculture risk logged (`docs/research/EXP-003.md`, default unchanged in code). **Docs/specs:** `docs/deployment/REMOTE_GPU_SETUP.md` (turnkey runbook), `CONFIDENCE_PLAN.md` (EXP-C1/C2 specified, **no number**), `EXP-004.md` (smallest valid dataset = DFC2020 val ROIs raw ~1.5–2 GB), `EXP-008.md` (linear-probe/LoRA definitions locked), `docs/research/G6_CAPABILITY_CLOSURE.md` (scorecard: **4/8 exit criteria met** — C,F,G,H; A,B,D,E blocked **only** on remote-GPU provisioning). **97/97 tests pass** (was 92). No product-code behaviour change (crop default preserved), no new deps, no new repos, no confidence value. ADR-014. |
| **G5A — A/B reproduction gate** | **Ran. LOCAL REPRODUCTION BLOCKED — 6th documented artifact-acquisition failure** (bounded Qwen2-VL-2B download, fresh `Qwen/` HF org: config landed instantly, both `.safetensors` shards stuck at **0 bytes** for the 8-min window — same signature as the 5 prior TinyRS attempts → host↔HF-CDN path is the blocker). RSVQA-LR + DIOR-RSVG also unfetchable. **N=0, no numbers fabricated.** Delivered ready-to-run: `evaluation/datasets/{rsvqa_lr,dior_rsvg}_sample.json` (frozen deterministic 40-Q / 25-expr selection specs) + `evaluation/scripts/exp002_ab_gate.py` (full measurement harness — compiles; `--resolve` → clean `DATASET_MISSING`). **Remote reference gate OPEN (ADR-013).** No production A/B model selected, no adapter written (would be fabrication), `/analyze` routing unchanged (`NO_VQA_SPECIALIST`, never RemoteCLIP). 92/92 tests unchanged — doc + eval-scaffold only, no product code. Three-numbers table in `EXP-002.md` + `EVIDENCE_LEDGER.md`. |
| **Model hierarchy — role labels (ADR-012)** | "GeoChat = ceiling" retired. Roles: **LOCAL A/B PRIMARY** RSCoVLM-3B · **FALLBACK** TinyRS-2B · **GENERIC CONTROL** Qwen2-VL-2B · **TEMPORAL** ChangeFormer · **OPTICAL-SAR PRIMARY** CROMA · **CHALLENGER** DOFA · **GROUNDING REFERENCE** GeoGround · **AUXILIARY** RemoteCLIP · **PRIMARY HIGH-CAPABILITY REFERENCE** EarthDial (REFERENCE CANDIDATE — checkpoints verified to exist, weights licence unconfirmed, 4B, not reproduced) · **SECONDARY / HISTORICAL REFERENCE** GeoChat (not on the critical path; local-run inability is **not** a blocker) · **RESEARCH REFERENCE** SARLANG-1M. Nothing is a "ceiling" until reproduced + measured. Docs: `MODEL_TOURNAMENT.md` (authoritative), `model_inventory.md`, `CAPABILITY_GAP_MATRIX.md`, ADR-012. **No new repos, no code, no artifacts downloaded.** |
| **Lightweight Model Replacement Audit** | `docs/research/LIGHTWEIGHT_AUDIT.md` (ADR-011). 5 candidates inspected from released artifacts (not paper titles), compared vs TinyRS + GeoChat. **RSCoVLM-3B** (MIT, `Qingyun/rscovlm`, RS multi-task VQA+grounding+caption) → **primary** EXP-002 arm; **TinyRS-2B** fallback; **Qwen2-VL-2B** generic control; **EarthDial-4B** (MIT weights, +SAR +temporal) replaces TEOChat as the remote SAR/temporal VLM; **SkyEyeGPT** BLOCKED (no inference recipe); **ISRO-GeoNLI** REJECT (wrapper, 36 GB). All still **#1 DOCUMENTED** — no reproduction. TinyRS download failed a **5th** time (11/12 files; 4.4 GB shard incomplete). `model_registry.yaml` `excluded:` block updated. **No new repos, no code, no fabricated numbers.** |
| Strategy docs `docs/17`–`docs/21` | files present; cross-linked from `CLAUDE.md` |
| `chatgpt.context.md` committed as persistent strategic memory | this session; ADR-003 |
| 6 research repos cloned into `external/research/` at pinned commits | `git -C <repo> rev-parse HEAD` matches `docs/research/model_inventory.md`; gitignored (`!!`) |
| Research inventory + compatibility + env strategy | `docs/research/{model_inventory,repository_compatibility,environment_strategy}.md` |
| Package skeletons (`pyproject.toml`, src layout) + adapter stubs | `python -m py_compile` passes; adapters raise `NotImplementedError` |
| `model_registry.yaml` with capability + routing entries | file present; dotted paths resolve to `satquery_model_adapters.*` |

**First SatQuery API exists** — `POST /change` (GeoTIFF pair → validated → co-reg
gate → ChangeFormer adapter → mask → area/bbox → provenance → JSON), 4 models
behind a standard `SpecialistAdapter` interface, registry with measured facts.
Still **no agent, no UI, no confidence value, and no *measured benchmark* number for
A/D/E.**


---

## IN PROGRESS

- V0 vertical slice — *not started*. Next: EXP-004 (local), then adapters, then V0.
- Adapters — RemoteCLIP / ChangeFormer / CROMA / DOFA all reproduced in `.venvs/*`;
  no adapter written yet.
- 4 reference venvs built: `.venvs/{remoteclip,changeformer,croma,dofa}` (gitignored);
  checkpoints in `models/cache/*` (gitignored, ~2.2 GB total).

---

## BLOCKED

| Blocker | Impact | Path forward |
|---------|--------|--------------|
| **GeoChat un-runnable on the dev host** — 7B merged model > 4 GB VRAM (RTX 3050 Ti); `deepspeed==0.9.5` fails to build on Windows; `bitsandbytes==0.41.0` Linux-only | **Not a project blocker** (ADR-012) — GeoChat is now the *secondary / historical* reference. The A/B path is local: RSCoVLM-3B / TinyRS-2B / Qwen2-VL-2B. GeoChat + EarthDial are reproduced on a remote box as references only. | provision a Linux GPU ≥16 GB (cloud) *after* the local EXP-002 arms are measured, then reproduce `geochat_demo.py` / `batch_geochat_*` + EarthDial |
| **Change-Agent un-runnable** — `mmcv==1.3.1` unbuildable (no wheels; ancient setup.py; needs CUDA toolkit + MSVC); internal `transformers` 4.33 vs ≥4.34 conflict | Temporal bake-off (EXP-003) can't include Change-Agent yet | Linux + conda + `mmcv` source build, or port to modern mmcv/mmseg |
| **ChangeChat has no released weights** + no `requirements.txt` at pinned commit | Nothing to run — **REJECT for now** | revisit only on a weights + dependency release |
| **No GPU-backed research env** (Windows 11, 4 GB laptop GPU, no conda/Docker/WSL) | **No longer a capability blocker** — A/B (G11) + D/E (G12) all closed on CPU via `hf_transfer` + non-gated mirrors. GPU now only needed to (a) verify 4 GB-VRAM fit for TinyRS / RemoteSAM / CROMA, (b) reproduce the 7B *reference* models (EarthDial, GeoChat) — neither on the critical path. | a short cloud GPU session for the VRAM check + reference repro |

---

## MISSING (required, not yet built)

- **Full benchmarks** (larger n, significance) — every real result so far is
  *sanity-scale* (VQA n=40, grounding n=25, optical-SAR n=200, adaptation n=200).
  Larger-split re-runs with bootstrapped deltas are the top post-freeze action.
- ~~Fine-tuning / adaptation proof~~ — **DONE (EXP-008, G12):** LoRA on frozen
  CROMA, +0.061 macro-F1, on real DFC2020. Sanity-scale; not significance-tested.
- Real evaluation harness — `evaluation/scripts/run_suite.py` is a stub; per-EXP
  harnesses exist (`exp002_*`, `exp004_run2_*`, `exp008_*`, `exp_grounding_*`).
- Datasets — RSVQA-LR, DIOR-RSVG, DFC2020 acquired (G11/G12, `models/cache/`,
  gitignored). Still not local: VRSBench, CDVQA, LEVIR-MCI, full BigEarthNet.
- End-to-end prototype (V0) — not started.
- API — only `/health`; no `/query`.
- Frontend — directory skeleton only.
- Optical–SAR fusion, verification layer, confidence method — designed in docs, no code.
- Provenance / audit persistence — designed, no code.
- Adversarial / red-team testing pass, `hackathon-jury` run — not done.
- PPT evidence content (Slides 3–6) — no measured material.

---

## RESEARCH NEEDED (open questions, `chatgpt.context.md` §32)

**G1.5 partially answered — `docs/research/CAPABILITY_GAP_MATRIX.md`:**
- ~~Best optical–SAR fusion approach~~ → **CROMA** (S1+S2, MIT, HF, runs on 4 GB) is
  the first candidate to evaluate; DOFA alt; MaRS watch-item (release unverified).
- ~~BigEarthNet access~~ → **reBEN / BigEarthNet v2** on Zenodo `10891137` (S1+S2,
  19-class multilabel, 549 k patches — use a **subset**).
- ~~Best grounding / lightweight VQA model~~ → **RSCoVLM-3B** (MIT, `Qingyun/rscovlm`,
  RS multi-task) is the primary local arm at 4-bit; **TinyRS-2B** fallback;
  **Qwen2-VL-2B** generic control; **EarthDial-4B** (MIT weights, +SAR +temporal)
  for the remote box in place of TEOChat; GeoChat = ceiling. See
  `docs/research/LIGHTWEIGHT_AUDIT.md` (ADR-011). Still #1 DOCUMENTED — EXP-002
  reproduction pending (blocked on multi-GB download from this host).
- ~~GPU environment decision~~ → **one cloud Linux GPU ≥16 GB** (24 ideal) unblocks
  GeoChat + TEOChat + (with conda) Change-Agent. Don't provision until EXP-004/EXP-E
  (local) are done.

**Still open:**
1. Exact packaging + held-out split construction for RSVQA / VRSBench / CDVQA
   (leakage vs model pretraining data).
2. Confirm licences for GeoChat / ChangeChat weights (no LICENSE file); confirm
   TinyRS weight licence (Qwen2-VL base) and MaRS release + licence.
3. Exact input/output contracts per model (bands, size, dtype, prompt format) —
   especially CROMA's Sentinel-1/2 preprocessing.
4. How confidence will be derived (probability vs margin vs heuristic) + calibration data.
5. How large the adaptation (E) must be to satisfy the PS — target a bounded
   linear/LoRA probe, measure if that's enough.
6. Semantic-change language path: cheap (ChangeFormer + region-caption) vs TEOChat
   vs Change-Agent — decided by EXP-003.

---

## METRICS

No **full benchmark** numbers. Real **integrated, sanity-scale** results now exist
for A (VQA), B (grounding), D (optical–SAR), E (adaptation) — all labelled
sanity-scale, none a full benchmark. Do not add anything that is not a real run,
tagged and labelled paper / reproduction / SatQuery.

| Metric | Value | Dataset | Split | Date | Number type | Notes |
|--------|-------|---------|-------|------|-------------|-------|
| **EXP-004 Run 2 — CROMA optical+SAR vs optical-only** | joint macro-F1 **0.793** vs optical-only **0.726** (+0.067; 95% CI [−0.024,+0.153] **includes 0**; McNemar p=0.45) | **real DFC2020** `ROIs0000_validation` (`125oii/dfc2020` mirror), dominant-land-cover 8-class | 400 train / 200 eval, seed 20260902 | 2026-09-02 | **integrated (SatQuery, sanity-scale)** | CPU; frozen CROMA `joint_GAP` → LogisticRegression probe; SAR help **positive, not significant at n=200**; DOFA concat-fusion −0.018 (no gain) → **KEEP CROMA** |
| **EXP-008 — LoRA adaptation of frozen CROMA** | macro-F1 **0.643 (frozen) → 0.704 (adapted), +0.061** | same DFC2020 split | 400 / 200, seed 20260902 | 2026-09-02 | **integrated (SatQuery, sanity-scale)** | CPU; LoRA r=8, 811k trainable params (0.4% of backbone), 3.24 MB adapter; clears +0.03 adopt bar → **ADOPT LoRA** as the E method; not significance-tested |
| ChangeFormer / RemoteCLIP / CROMA / DOFA rows below | — | — | — | 2026-09-01 | — | — |
| ChangeFormerV6 change-IoU | 0.832 | LEVIR-CD bundled `samples_LEVIR` | 7 labelled samples (demo) | 2026-09-01 | **reproduction** | CPU, `.venvs/changeformer` torch 2.5.1; n=7 — sanity check only |
| ChangeFormerV6 change-F1 | 0.908 | LEVIR-CD bundled `samples_LEVIR` | 7 labelled samples (demo) | 2026-09-01 | **reproduction** | same run |
| ChangeFormerV6 overall acc (LEVIR-CD test) | 0.9495 | LEVIR-CD | test | (upstream) | **paper / author** | from checkpoint `log.txt` — not ours |
| RemoteCLIP-ViT-B-32 zero-shot | correct (97.8% top-1) | `assets/airport.jpg` | n=1 | 2026-09-01 | **reproduction** | official example; not a benchmark |
| RemoteCLIP inference latency | ~150 ms/query | — | — | 2026-09-01 | measured (host) | CPU, warm, ViT-B-32, 1 img + ~4 prompts |
| ChangeFormer inference latency | ~790 ms / 256² pair | — | — | 2026-09-01 | measured (host) | CPU; ~1–2 OOM faster expected on GPU |
| **Temporal slice / `POST /change` e2e (demo pair)** | changed_fraction **0.2526**, area 4138 m² / 0.414 ha, change bbox + centroid | LEVIR sample `test_2_0000_0000` wrapped as EPSG:32650 GeoTIFF pair | n=1 pair | 2026-09-01 | **integrated (SatQuery API path)** | matches G1 `demo_LEVIR.py` (25.3%); via `/change` → `run_change_slice` → `ChangeFormerAdapter`; **not a benchmark** |
| RemoteCLIP adapter smoke (via `run()`) | top = "an airport", score 0.989 | `assets/airport.jpg`, 3 prompts | n=1 | 2026-09-01 | **reproduction (integrated path)** | score = softmax over given prompts, not calibrated |
| CROMA / DOFA adapter smoke | dim-768 embeddings, finite | random tensors | n/a | 2026-09-01 | **reproduction (integrated path)** | representations only; no task metric |
| EXP-004 **Run 1** sanity: SAR-only signal recovery | optical-only 0.485/0.502 (chance) · CROMA-joint 1.00 · DOFA-fused 1.00 | **synthetic** paired S1/S2, controlled injected signal | train 240 / test 160, seed 20260901 | 2026-09-01 | **sanity check — NOT a benchmark** | validated the 3-arm probe machinery; **superseded by Run 2 above (real DFC2020)** |
| CROMA-base reproduced | official example OK (joint SAR+optical embeddings, shapes correct, finite) | random S1/S2 tensors | n/a | 2026-09-01 | **reproduction** | CPU `.venvs/croma`; 194 M params; NOT measured on a task |
| CROMA-base latency | ~340 ms/sample (joint forward) | — | — | 2026-09-01 | measured (host) | CPU, batch 8 |
| DOFA ViT-B reproduced | `forward_features` OK for S1 (2ch) + S2 (12ch), finite (B,768) | random tensors | n/a | 2026-09-01 | **reproduction** | CPU `.venvs/dofa`; 111 M params; NOT measured on a task |
| DOFA ViT-B latency | ~120 ms/sample | — | — | 2026-09-01 | measured (host) | CPU, batch 4 |

---

## RISKS

| Risk | Severity | Mitigation |
|------|----------|------------|
| Environment fragmentation across 5 research models | High | per-model container/venv (`docs/research/environment_strategy.md`); integrate one at a time |
| No GPU-backed research env → GeoChat + Change-Agent blocked, slow iteration | High | **confirmed in G1.** First stack (RemoteCLIP + ChangeFormer) runs CPU-only; a cloud Linux GPU ≥16 GB is needed before EXP-001 / GeoChat |
| Adaptation requirement (BigEarthNet) not scoped | High | scope a minimal LoRA/adapter fine-tune on one component before freezing architecture |
| Novelty currently asserted, not measured | High | EXP-004–EXP-007 must produce real deltas before any novelty claim in the PPT |
| ChangeChat + RS-MoE have no released weights → narrower temporal/VQA options | Medium | ChangeFormer + composed caption pipeline (EXP-003); TinyRS/RSCoVLM-3B for VQA (EXP-002) |
| "SAR helps" is only reproduced, not measured → don't claim it | High | EXP-004 must produce the abs+rel delta before any optical–SAR novelty claim |
| Scope creep vs hackathon time budget | Medium | scope-control checklist (`chatgpt.context.md` §27); cut anything without an eval path |
| Six-slide PPT claims outrunning the prototype | Medium | slide claims gated on `docs/PROJECT_STATUS.md` METRICS + demo path |
| Overfitting / gaming the public benchmarks (numbers that won't hold on unseen ISRO/SAC data) | Medium | held-out splits + leakage checks; report a "known distribution gaps" section (`docs/11`); prefer robustness stress tests (EXP-007) over leaderboard chasing |
| `scope.md` justification skipped under time pressure | Medium | `.claude/rules/scope.md` is always-loaded; every feature PR answers the 7 questions |

---

## NEXT 3 ACTIONS (highest leverage only)

**Model stack is FROZEN (ADR-021).** These are post-freeze — confirmation +
additive layers, none changes which models are in the stack.

1. **Larger-split D + E re-run + significance.** Re-run EXP-004 Run 2 and EXP-008
   on the full 986-patch DFC2020 validation (and/or the 5128-patch test ROIs)
   with **bootstrapped before→after deltas**, so the SAR benefit (D) and the LoRA
   gain (E) get a significance verdict instead of "positive at n=200". Persist the
   LoRA adapter (`--save-adapter`) and add the opt-in `--lora-weights` load path
   to `CromaAdapter`; flip the production default frozen→adapted only if it holds.
2. **GPU / 4 GB-VRAM verification.** On any CUDA machine, measure peak **VRAM**
   for TinyRS-2B (4-bit), RemoteSAM, and CROMA to confirm `LOCAL-FITS-4GB`
   (all CPU-only so far — no VRAM figure exists). Also chase the **RemoteSAM
   licence** (still NOT STATED — `REMOTESAM_LICENSE.md`).
3. **EXP-006 — agentic `/analyze` planning + EXP-C1/C2 confidence.** Add the LLM
   intent→typed-task step (schema-validated against the registry) on top of the
   deterministic router; then EXP-C1/C2 (a defined confidence method) now that
   the A/B models exist. `/analyze` hardening (composed-semantic failure corpus,
   `MULTIMODAL_REPR` real `.npy` path, OpenAPI examples) rides along.

~~EXP-005 verifier~~ — done (structural + semantic P/R/F1 = 1.00). ~~Remote GPU~~ —
no longer a blocker: `hf_transfer` + non-gated HF mirrors closed A/B (G11) and
D/E (G12) on the local CPU box. GPU is now only needed for the VRAM verification
in action 2 and the high-capability *reference* reproductions (EarthDial/GeoChat),
which are not on the critical path.

---

## WIN SCORECARD (0–10 — honest)

| Dimension | Score | Δ (since G1) | Why |
|-----------|:----:|:--:|-----|
| Problem fit | 6 | +2 | one unified `/analyze` entrypoint maps queries → the A–H capabilities; **every mandatory capability now has a real integrated measurement** |
| Novelty | 6 | +1 | **the system-level composition is the contribution** — NL mission → constrained agentic planning → deterministic policy guard → multi-specialist observe/**structured-replan**/early-stop → geospatial + evidence + verification, all local + resource-aware. **G15 measured** on 50 frozen missions: plan validity / tool-selection / task-order / dependency-validity 1.00; unsupported-action & unnecessary-tool-call rate 0.00; agent runs ~2.5× the baseline's specialists on multi-step. Plus optical+SAR delta (+0.067, not yet significant) + LoRA adaptation. |
| Technical depth | 8 | — | `/analyze` unified layer + composed semantic baseline + EXP-007 + real DFC2020 probe/adaptation harness + G13 product surface; 183 tests |
| Prototype completeness | 9 | — | **G13** one coherent product + **G14** agentic investigator (`POST /investigate`: plan → policy → observe/replan executor → evidence-first report); all 6 specialist paths + multi-step missions run end-to-end |
| Accuracy | 5 | +1 | **G12 adds D + E:** optical+SAR macro-F1 0.793 (DFC2020 n=200); LoRA adaptation +0.061. Plus G11 VQA 0.87 / grounding 0.84 / change 0.83. **All sanity-scale, honestly labelled; none significance-tested.** |
| Multimodal (optical–SAR) reasoning | 5 | +2 | **EXP-004 Run 2 MEASURED on real DFC2020** — CROMA joint 0.793 vs optical 0.726 (+0.067, CI includes 0). CROMA = PRIMARY, DOFA = fallback. No `/fusion` endpoint yet (delta not significant). |
| Capability A (VQA) | 6 | — | TinyRS-2B MEASURED (bal acc 0.87) + INTEGRATED (G11); n=40 sanity-scale, GPU unverified |
| Capability D (optical–SAR) | 6 | new | **CROMA MEASURED (macro-F1 0.793 vs 0.726) + INTEGRATED (G12)** — won the CROMA-vs-DOFA bake-off; n=200 sanity-scale, SAR delta not significant, GPU-VRAM unverified |
| Capability E (RS adaptation) | 6 | new | **EXP-008 MEASURED (G12)** — LoRA on frozen CROMA +0.061 macro-F1, 811k params; ADOPTED as the method; prod default still frozen pending a larger-split bootstrap; adapter not yet persisted |
| Temporal reasoning | 6 | — | mask integrated + composed semantic-change baseline (disclaimed); learned semantic still NONE |
| Geospatial integrity | 7 | +1 | EXP-007 15/15; + 986 real DFC2020 GeoTIFFs read with 0 failures in EXP-004 |
| Evidence / verification | 7 | — | `verify()` + `verify_semantic()` P/R/F1 = 1.00 (n=24 / n=34), INTEGRATED; confidence NONE (EXP-C1/C2 specified) |
| UI / UX | 5 | +4 | **G13: working local UI** at `GET /` — upload, query, answer, image + box/mask overlay on canvas, evidence/verification/execution-trace/provenance panels, warnings, loading/error/empty states. Vanilla JS, one file, no build. Not polished, but real and end-to-end. |
| Benchmark readiness | 4 | +2 | real datasets now acquired (RSVQA-LR, DIOR-RSVG, DFC2020) via `hf_transfer` + non-gated mirrors; harnesses run end-to-end; **need larger splits + significance** |
| Feasibility | 8 | +1 | **the local CPU box closed A/B/D/E** — the "needs a remote box" premise is retired; GPU now only for VRAM verification + reference models |
| Impact | 4 | — | clear institutional relevance |
| PPT quality | 5 | +1 | one unified endpoint + real (sanity-scale) numbers for every mandatory capability + a frozen stack story |
| Demo quality | 4 | — | `POST /analyze` runs a real query → routed specialist → structured evidence; grounding + VQA demos work end-to-end (CPU) |
| Capability B (grounding) | 7 | — | RemoteSAM MEASURED (acc@IoU0.5 0.84) + INTEGRATED; n=25 sanity-scale, licence NOT STATED, GPU-VRAM unverified |

**Read:** **G12 froze the model stack.** Every mandatory capability A–H now has a
real *integrated* measurement on real data, not a paper number: VQA 0.87
(TinyRS-2B), grounding 0.84 (RemoteSAM), change IoU 0.83 (ChangeFormer),
optical+SAR macro-F1 0.793 (CROMA joint, DFC2020), adaptation +0.061 (LoRA on
CROMA), routing / geospatial / evidence all integrated + verified. The
`hf_transfer` + non-gated-mirror recipe retired the "needs a remote GPU box"
premise — A/B (G11) and D/E (G12) all closed on the local CPU machine. **Model
stack FROZEN (ADR-021).** What's left is *confirmation and additive layers*:
larger-split D/E re-runs with bootstrapped significance, GPU-VRAM verification,
the LLM planner (EXP-006), and a defined confidence method (EXP-C1/C2). Still
**no LLM agent, no UI, no confidence value (by design)**; D/E deltas are
**sanity-scale (n=200), not significance-tested**.
