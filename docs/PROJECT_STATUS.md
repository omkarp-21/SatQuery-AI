# SatQuery — Project Status

> Living status file (see `chatgpt.context.md` §24). Update every significant
> session. No fabricated numbers — "not measured" is the honest value until a real
> run exists. Last updated: **2026-09-01 (G7)**. Tests: **108 passed, 0 failed**.

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
| **No GPU-backed research env** (Windows 11, 4 GB laptop GPU, no conda/Docker/WSL) | CUDA-only stacks and 7B models can't run locally; CPU-only for the two that work | decide GPU path: cloud Linux box vs local WSL2+Docker+NVIDIA toolkit |

---

## MISSING (required, not yet built)

- Reproduced model **benchmarks** (number #2) — none on a real benchmark. (Two
  smoke-level reproductions exist from G1: RemoteCLIP official example correct;
  ChangeFormer IoU 0.83 on 7 bundled samples. Not benchmarks.)
- Baseline metrics and full SatQuery metrics (number #3) — none.
- Fine-tuning / adaptation proof (BigEarthNet requirement, PS §Adaptation) — not scoped.
- Real evaluation harness — `evaluation/scripts/run_suite.py` is a stub; no metrics, no cases.
- Datasets — none downloaded (RSVQA, VRSBench, CDVQA, LEVIR-MCI, BigEarthNet).
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

No **benchmark** numbers yet; all `docs/19` experiments are `PLANNED`. The only
real measurements are two G1 runtime smoke checks (tiny n — sanity, not benchmark).
Do not add anything that is not a real run, tagged and labelled paper /
reproduction / SatQuery.

| Metric | Value | Dataset | Split | Date | Number type | Notes |
|--------|-------|---------|-------|------|-------------|-------|
| ChangeFormerV6 change-IoU | 0.832 | LEVIR-CD bundled `samples_LEVIR` | 7 labelled samples (demo) | 2026-09-01 | **reproduction** | CPU, `.venvs/changeformer` torch 2.5.1; n=7 — sanity check only |
| ChangeFormerV6 change-F1 | 0.908 | LEVIR-CD bundled `samples_LEVIR` | 7 labelled samples (demo) | 2026-09-01 | **reproduction** | same run |
| ChangeFormerV6 overall acc (LEVIR-CD test) | 0.9495 | LEVIR-CD | test | (upstream) | **paper / author** | from checkpoint `log.txt` — not ours |
| RemoteCLIP-ViT-B-32 zero-shot | correct (97.8% top-1) | `assets/airport.jpg` | n=1 | 2026-09-01 | **reproduction** | official example; not a benchmark |
| RemoteCLIP inference latency | ~150 ms/query | — | — | 2026-09-01 | measured (host) | CPU, warm, ViT-B-32, 1 img + ~4 prompts |
| ChangeFormer inference latency | ~790 ms / 256² pair | — | — | 2026-09-01 | measured (host) | CPU; ~1–2 OOM faster expected on GPU |
| **Temporal slice / `POST /change` e2e (demo pair)** | changed_fraction **0.2526**, area 4138 m² / 0.414 ha, change bbox + centroid | LEVIR sample `test_2_0000_0000` wrapped as EPSG:32650 GeoTIFF pair | n=1 pair | 2026-09-01 | **integrated (SatQuery API path)** | matches G1 `demo_LEVIR.py` (25.3%); via `/change` → `run_change_slice` → `ChangeFormerAdapter`; **not a benchmark** |
| RemoteCLIP adapter smoke (via `run()`) | top = "an airport", score 0.989 | `assets/airport.jpg`, 3 prompts | n=1 | 2026-09-01 | **reproduction (integrated path)** | score = softmax over given prompts, not calibrated |
| CROMA / DOFA adapter smoke | dim-768 embeddings, finite | random tensors | n/a | 2026-09-01 | **reproduction (integrated path)** | representations only; no task metric |
| **EXP-004 sanity: SAR-only signal recovery** | optical-only 0.485/0.502 (chance) · CROMA-joint 1.00 · DOFA-fused 1.00 | **synthetic** paired S1/S2, controlled injected signal | train 240 / test 160, seed 20260901 | 2026-09-01 | **sanity check — NOT a benchmark** | validates the 3-arm probe machinery + directional H3; real DFC2020/reBEN run pending |
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

1. **Provision one remote Linux GPU box (≥ 16 GB, working bandwidth)** — the local
   A/B path is now exhausted (G5A: 6th weight-download failure; RSVQA-LR/DIOR-RSVG
   also unfetchable). On that box run the committed `evaluation/scripts/exp002_ab_gate.py`
   for **RSCoVLM-3B / TinyRS-2B / Qwen2-VL-2B** (@ 4-bit — still the 4 GB budget
   logically) **and** the reference arm **EarthDial-4B / GeoChat-7B** on the
   *identical* frozen RSVQA-LR + DIOR-RSVG samples → balanced acc / acc@IoU0.5 /
   latency / memory + absolute & relative local-vs-reference deltas. Same box
   unblocks DFC2020 → **EXP-004 Run 2** → **EXP-008**. Then select the production
   A/B model on the 7 G5A criteria and write **one** SpecialistAdapter + update
   `/analyze` routing to point VQA/grounding at it.
2. **Integrate the EXP-002 winner + EXP-004/008** (on the same box, in order) —
   pick the A/B model on the 7 criteria, write **one** `SpecialistAdapter`
   (validate/execute/normalize_output/provenance/run, subprocess, no research-repo
   import) + smoke/provenance/normalization tests, route `/analyze` VQA+grounding
   to it (grounding → mappable spatial evidence). Then EXP-004 Run 2 (DFC2020 val
   ROIs, smallest valid set) → CROMA-vs-DOFA decision → EXP-008 before/after →
   EXP-C1 calibration.
3. **EXP-006 — agentic `/analyze` planning** (after the capability set is closed):
   add the LLM intent→typed-task step, schema-validated against the registry, on
   top of the deterministic router. `/analyze` hardening (composed-semantic
   failure corpus, `MULTIMODAL_REPR` real `.npy` path, OpenAPI examples) rides
   along.

~~EXP-005 verifier~~ — **done**: structural P/R/F1 = 1.00 (G6, n=24); model-independent
semantic verifier P/R/F1 = 1.00 (G7/EXP-005b, n=34), INTEGRATED into the composed
baseline. Residual label-correctness gap → EXP-002 + EXP-C2. `FAILURE_AWARE_ROUTING.md`
design is ready; implementation queued **after the model freeze**. EXP-C1/C2 specified,
blocked on the A/B model.

Remote GPU: **the one blocking action for capability closure.** 4/8 G6 exit
criteria are met locally; A/B/D/E are blocked solely on provisioning
(`G6_CAPABILITY_CLOSURE.md`, `docs/deployment/REMOTE_GPU_SETUP.md`).

---

## WIN SCORECARD (0–10 — honest)

| Dimension | Score | Δ (since G1) | Why |
|-----------|:----:|:--:|-----|
| Problem fit | 5 | +1 | one unified `/analyze` entrypoint maps queries → the A–H capabilities honestly |
| Novelty | 2 | — | contribution areas named; none measured on a benchmark |
| Technical depth | 8 | — | `/analyze` unified layer + composed semantic baseline + EXP-007; 92 tests |
| Prototype completeness | 6 | +1 | 3 endpoints (`/analyze`, `/change`, `/scene`) + composed-semantic + joint-repr; no agent/UI |
| Accuracy | 1 | — | still only ChangeFormer reproduction (n=7); no benchmark |
| Multimodal (optical–SAR) reasoning | 3 | — | joint-representation contract; **EXP-004 Run 2 blocked (dataset unacquirable)** |
| Temporal reasoning | 6 | +1 | mask integrated + **composed semantic-change baseline** (isolated, disclaimed); learned semantic still NONE |
| Geospatial integrity | 6 | +1 | **EXP-007: 15/15 safeguard cases pass**; live in all 3 endpoints |
| Evidence / verification | 7 | +1 | `verify()` in all 3 APIs; **EXP-005 structural P/R/F1 = 1.00 (n=24)**; **EXP-005b (G7): model-independent semantic verifier P/R/F1 = 1.00 (n=34), INTEGRATED into the composed baseline**; residual label-correctness gap needs EXP-002/EXP-C2; confidence NONE (EXP-C1/C2 specified) |
| UI / UX | 1 | — | skeleton + design skill |
| Benchmark readiness | 2 | — | harnesses ready; **real datasets unacquirable from this host** (needs a better-connected machine) |
| Feasibility | 7 | -1 | system is solid, but EXP-002/004/008 now need a remote box — local-only path is exhausted for those |
| Impact | 4 | — | clear institutional relevance |
| PPT quality | 4 | +1 | one unified endpoint + a demonstrable analysis story; still no measured numbers |
| Demo quality | 3 | +1 | `POST /analyze` runs a real query → routed specialist → structured evidence |

**Read:** **G4 unified the system.** One deterministic `POST /analyze` entrypoint
(interpret → validate → route → specialist → aggregate evidence/verification/
provenance), a composed semantic-change baseline for C (isolated, honestly
disclaimed), and EXP-007 proving the geospatial safeguards (15/15). **92 tests, no
regressions.** But the intelligence-stack experiments are now **hard-blocked on
data**: EXP-002 (TinyRS/RSCoVLM weights) and EXP-004 Run 2 / EXP-008 (real S1+S2)
cannot be fetched from this host — every candidate is multi-GB and the network
drops them. **A remote Linux GPU box is now justified** (bandwidth + GPU). Still
**no LLM agent, no UI, no confidence value (by design), and no *measured
benchmark* number for A/D/E.**
