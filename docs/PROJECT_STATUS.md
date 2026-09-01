# SatQuery — Project Status

> Living status file (see `chatgpt.context.md` §24). Update every significant
> session. No fabricated numbers — "not measured" is the honest value until a real
> run exists. Last updated: **2026-09-01**.

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
| **GeoChat un-runnable on the dev host** — 7B merged model > 4 GB VRAM (RTX 3050 Ti); `deepspeed==0.9.5` fails to build on Windows; `bitsandbytes==0.41.0` Linux-only | No single-image VQA/grounding specialist locally; **EXP-001 blocked** | provision a Linux GPU ≥16 GB (cloud), then reproduce `geochat_demo.py` / `batch_geochat_*` |
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
- ~~Best grounding / lightweight VQA model~~ → **TinyRS** (Qwen2-VL-2B, Apache-2.0,
  HF) as the local option; GeoChat/TEOChat need a GPU box.
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

1. **EXP-004 Run 2 (real)** — acquire a small labelled S1+S2 set (DFC2020 val split
   ~1 GB carved from the 11 GB `.pt`, or a reBEN shard), run the 3-arm frozen-feature
   linear probe → first **measured** SAR delta (gap D, H3); then EXP-008 (gap E) on
   the winning encoder. **Local, no GPU.**
2. **EXP-002 — get the artifacts** — TinyRS weights failed to download 3×; next
   session use `hf_hub_download` per-file with `resume_download` on a stable
   connection (or `hf transfer` / a mirror), then run the smoke + the RSVQA-LR /
   DIOR-RSVG sample vs the fixed threshold. RSCoVLM-3B as the backup.
3. **Build the confidence + verifier stub (gap H)** and wire RemoteCLIP into a
   `/scene` or `/retrieve` endpoint — the second API surface, and the prerequisite
   for constrained routing (Track 7 / EXP-006).

Remote GPU: **still not justified** — EXP-004 Run 2 and EXP-002 both run on the
laptop. Gate stays closed until EXP-002 measures the local VLMs below threshold.

---

## WIN SCORECARD (0–10 — honest)

| Dimension | Score | Δ (since G1) | Why |
|-----------|:----:|:--:|-----|
| Problem fit | 4 | — | requirements mapped (A–H); coherent system skeleton now |
| Novelty | 2 | — | contribution areas named; none measured on a benchmark |
| Technical depth | 8 | +1 | 2 APIs, standard adapter + evidence + verification + router contracts, 4 adapters, 59 tests |
| Prototype completeness | 5 | +1 | 2 API surfaces (`/change`, `/scene`) + internal multimodal contract; no agent/UI |
| Accuracy | 1 | — | still only ChangeFormer reproduction (n=7); no benchmark |
| Multimodal (optical–SAR) reasoning | 3 | — | joint-representation **contract + adapters + internal service**; no real task number (EXP-004 Run 2) |
| Temporal reasoning | 5 | — | integrated behind adapter + `/change` + evidence + verification; language side unbuilt |
| Geospatial integrity | 5 | — | live in both API paths; not yet stress-tested (EXP-007) |
| Evidence / verification | 5 | +2 | `EvidenceItem` + deterministic `verify()` **implemented and wired into both slices**; semantic verification + confidence still NONE (by design) |
| UI / UX | 1 | — | skeleton + design skill |
| Benchmark readiness | 2 | — | harnesses ready; real benchmarks still not acquired |
| Feasibility | 8 | — | all local, CPU-only, no source edits; remote GPU still not needed |
| Impact | 4 | — | clear institutional relevance |
| PPT quality | 3 | — | blueprint + story; two callable APIs now exist |
| Demo quality | 2 | — | `/change` + `/scene` return real structured results; no UI |

**Read:** **G3 made SatQuery structurally real.** Two APIs (`/change`, `/scene`),
an internal optical–SAR contract, and standard `SpecialistAdapter` / `EvidenceItem`
/ `verify()` / router contracts — all deterministic, all CPU-only, **59 tests, no
regressions**. Evidence/verification jumped from designed → implemented+wired.
Still **no LLM agent, no UI, no confidence value (by design), and no *measured
benchmark* number for A/D/E**. The intelligence stack is still being decided by
experiments: EXP-002 (artifact-blocked), EXP-004 Run 2 (needs a small S1+S2 set),
EXP-008. Next value: get those datasets/weights.
