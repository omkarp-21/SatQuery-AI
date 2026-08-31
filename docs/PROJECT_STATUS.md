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
| Strategy docs `docs/17`–`docs/21` | files present; cross-linked from `CLAUDE.md` |
| `chatgpt.context.md` committed as persistent strategic memory | this session; ADR-003 |
| 6 research repos cloned into `external/research/` at pinned commits | `git -C <repo> rev-parse HEAD` matches `docs/research/model_inventory.md`; gitignored (`!!`) |
| Research inventory + compatibility + env strategy | `docs/research/{model_inventory,repository_compatibility,environment_strategy}.md` |
| Package skeletons (`pyproject.toml`, src layout) + adapter stubs | `python -m py_compile` passes; adapters raise `NotImplementedError` |
| `model_registry.yaml` with capability + routing entries | file present; dotted paths resolve to `satquery_model_adapters.*` |

**Nothing intelligent works yet.** All of the above is structure, process, and inventory.

---

## IN PROGRESS

- V0 vertical slice — *not started*. Next up (RemoteCLIP is validated and ready to wire).
- ChangeFormer adapter — model validated (`.venvs/changeformer`), adapter not written.
- Model comparison matrix — `docs/research/MODEL_COMPARISON.md` still a skeleton;
  `docs/research/runtime_validation.md` now has the G1 evidence.

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

1. Exact packaging + access for the eval benchmarks (RSVQA, VRSBench, CDVQA).
2. BigEarthNet access + the training/label format expected for adaptation.
3. Which checkpoints are actually downloadable; confirm licenses — GeoChat and
   ChangeChat repos have **no LICENSE file** (metadata says Apache; unconfirmed).
4. GPU environment decision (local WSL2/Docker vs cloud).
5. Real candidate-model performance on our data (EXP-001, EXP-002).
6. Exact input/output contracts per model (bands, size, dtype, prompt format).
7. Achievable end-to-end latency, with and without GPU.
8. How confidence will be derived (calibrated probability vs margin vs heuristic).
9. Best optical–SAR fusion approach for built-up / change tasks.
10. Best temporal model (Change-Agent vs ChangeFormer pipeline).
11. Best grounding model (GeoChat vs alternatives).
12. How much fine-tuning is genuinely required to satisfy the adaptation requirement.

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

---

## RISKS

| Risk | Severity | Mitigation |
|------|----------|------------|
| Environment fragmentation across 5 research models | High | per-model container/venv (`docs/research/environment_strategy.md`); integrate one at a time |
| No GPU-backed research env → GeoChat + Change-Agent blocked, slow iteration | High | **confirmed in G1.** First stack (RemoteCLIP + ChangeFormer) runs CPU-only; a cloud Linux GPU ≥16 GB is needed before EXP-001 / GeoChat |
| Adaptation requirement (BigEarthNet) not scoped | High | scope a minimal LoRA/adapter fine-tune on one component before freezing architecture |
| Novelty currently asserted, not measured | High | EXP-004–EXP-007 must produce real deltas before any novelty claim in the PPT |
| ChangeChat unusable → narrows temporal options | Medium | Change-Agent vs ChangeFormer decision via EXP-003 |
| Scope creep vs hackathon time budget | Medium | scope-control checklist (`chatgpt.context.md` §27); cut anything without an eval path |
| Six-slide PPT claims outrunning the prototype | Medium | slide claims gated on `docs/PROJECT_STATUS.md` METRICS + demo path |
| Overfitting / gaming the public benchmarks (numbers that won't hold on unseen ISRO/SAC data) | Medium | held-out splits + leakage checks; report a "known distribution gaps" section (`docs/11`); prefer robustness stress tests (EXP-007) over leaderboard chasing |
| `scope.md` justification skipped under time pressure | Medium | `.claude/rules/scope.md` is always-loaded; every feature PR answers the 7 questions |

---

## NEXT 3 ACTIONS (highest leverage only)

1. **Wrap the two validated models as adapters** in
   `packages/model_adapters/src/satquery_model_adapters/` — `remoteclip.py`
   (subprocess/inproc to `.venvs/remoteclip`) and `changeformer.py` (to
   `.venvs/changeformer`), each with the smoke test that G1 already proved runs.
   Update `model_registry.yaml` capability entries with the measured facts.
2. **Build V0**: `POST /query` → ingestion + metadata (real CRS/transform/bounds)
   → RemoteCLIP adapter → reports. One demo GeoTIFF, offline. Feature-complete per
   `docs/17`.
3. **Decide the GPU path** (cloud Linux ≥16 GB) so GeoChat (EXP-001) and
   Change-Agent (EXP-003) become runnable; until then EXP-001 uses a small
   CPU-runnable control VLM vs RemoteCLIP where the task allows.

---

## WIN SCORECARD (0–10 — honest)

| Dimension | Score | Δ | Why |
|-----------|:----:|:--:|-----|
| Problem fit | 4 | — | requirements understood + documented; nothing built against them |
| Novelty | 2 | — | contribution areas named; none validated |
| Technical depth | 4 | +1 | G1 proved two research models actually run + measured; real env constraints known |
| Prototype completeness | 1 | — | still no end-to-end path (adapters not written) |
| Accuracy | 1 | +1 | one real reproduction (ChangeFormer IoU 0.83, n=7) — sanity, not benchmark |
| Multimodal (optical–SAR) reasoning | 0 | — | not started; no SAR model in the runnable set |
| Temporal reasoning | 2 | +2 | ChangeFormer change-mask **runs** and reproduces plausibly (n=7) |
| Geospatial integrity | 2 | — | rules + skill written; no code |
| Evidence / verification | 1 | — | designed; not built |
| UI / UX | 1 | — | dir skeleton + design skill |
| Benchmark readiness | 2 | +1 | two validated venvs + `runtime_validation.md`; real benchmarks still not acquired |
| Feasibility | 6 | +1 | first stack (RemoteCLIP + ChangeFormer) proven runnable CPU-only, no source edits; GeoChat/Change-Agent need a GPU box |
| Impact | 4 | — | clear institutional relevance in the framing |
| PPT quality | 3 | — | six-slide blueprint + story defined; no evidence content |
| Demo quality | 0 | — | no demo path yet |

**Read:** G1 converted "5 candidate repos" into "2 that run here, 2 that need a
Linux GPU, 1 rejected". Foundation is solid; still **no end-to-end prototype**.
Next value: adapters for the two runnable models, then V0. Explain every change here.
