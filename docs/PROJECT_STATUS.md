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
| **G1.6 model tournament** — 15-repo pool validated; CROMA + DOFA reproduced | `docs/research/MODEL_TOURNAMENT.md` + `EXPERIMENT_DECISION_TREE.md` (ADR-006). **REPRODUCED (CPU):** CROMA (joint SAR+optical, 194 M, MIT), DOFA (S1+S2 encoder, 111 M, MIT) → gap D now **REPRODUCED** (was NONE). **RE-VERIFIED REJECT:** ChangeChat (no weights, ≥48 GB to train), **RS-MoE** (no weights/inference). **TEST FURTHER local:** TinyRS, RSCoVLM-3B. **Remote-GPU only:** GeoChat, GeoGround, TEOChat, UniRS, LRS-VQA. `SARLANG-1M` = SAR-language dataset (not a model). No remote GPU yet — not justified. |
| Strategy docs `docs/17`–`docs/21` | files present; cross-linked from `CLAUDE.md` |
| `chatgpt.context.md` committed as persistent strategic memory | this session; ADR-003 |
| 6 research repos cloned into `external/research/` at pinned commits | `git -C <repo> rev-parse HEAD` matches `docs/research/model_inventory.md`; gitignored (`!!`) |
| Research inventory + compatibility + env strategy | `docs/research/{model_inventory,repository_compatibility,environment_strategy}.md` |
| Package skeletons (`pyproject.toml`, src layout) + adapter stubs | `python -m py_compile` passes; adapters raise `NotImplementedError` |
| `model_registry.yaml` with capability + routing entries | file present; dotted paths resolve to `satquery_model_adapters.*` |

**Nothing intelligent works yet.** All of the above is structure, process, and inventory.

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

1. **Run EXP-004** — 3-arm probe (optical-only / CROMA `joint_GAP` / DOFA S1⊕S2) on
   a small reBEN (BigEarthNet v2) subset, linear head. **MEASURES** gap D, gives
   H3 its first number, and its head IS EXP-008 (gap E). **Local, no infra spend.**
2. **Run EXP-002** — TinyRS vs RSCoVLM-3B on an RSVQA-LR + DIOR-RSVG sample
   (4-bit / CPU). Picks the local single-image model for gaps A + B, or triggers
   the remote-GPU gate. **Local.**
3. **Wrap the 4 reproduced models as adapters** (`remoteclip`, `changeformer`,
   `croma`, `dofa`) with the smoke tests already proven; populate
   `model_registry.yaml` with measured facts. Prereq for V0 + EXP-006.

Remote GPU: **still not justified.** Provision one Linux box ≥16 GB only after
EXP-002/004/008, and only if the local VQA candidates measurably underperform.

---

## WIN SCORECARD (0–10 — honest)

| Dimension | Score | Δ (since G1) | Why |
|-----------|:----:|:--:|-----|
| Problem fit | 4 | — | requirements mapped (A–H); nothing built against them |
| Novelty | 2 | — | contribution areas named; none measured |
| Technical depth | 5 | +1 | 4 research models reproduced on CPU incl. two optical–SAR encoders; 15-repo pool validated; decision tree written |
| Prototype completeness | 1 | — | still no end-to-end path (no adapter) |
| Accuracy | 1 | — | one reproduction (ChangeFormer IoU 0.83, n=7); CROMA/DOFA reproduced but not scored |
| Multimodal (optical–SAR) reasoning | 2 | +2 | CROMA + DOFA **reproduced** (S1+S2 embeddings) — gap D moved NONE → REPRODUCED; not yet measured |
| Temporal reasoning | 2 | — | ChangeFormer mask runs (n=7); language side still unbuilt |
| Geospatial integrity | 2 | — | rules + skill; no code |
| Evidence / verification | 1 | — | designed; not built |
| UI / UX | 1 | — | skeleton + design skill |
| Benchmark readiness | 2 | — | 4 venvs + tournament docs; real benchmarks still not acquired |
| Feasibility | 7 | +1 | 4-model local stack (RemoteCLIP, ChangeFormer, CROMA, DOFA) proven CPU-only, no source edits; remote GPU still not needed |
| Impact | 4 | — | clear institutional relevance |
| PPT quality | 3 | — | blueprint + story; no evidence content |
| Demo quality | 0 | — | no demo path |

**Read:** G1.6 turned a 15-repo candidate pool into a decision: **4 models
reproduced locally** (RemoteCLIP, ChangeFormer, CROMA, DOFA — all MIT/Apache, all
CPU), **2 REJECTED for missing weights** (ChangeChat, RS-MoE), the rest are
remote-GPU or local-untested. Gap D moved from NONE to REPRODUCED. Still **no
end-to-end prototype and no measured task number for D/E**. Next value: EXP-004 +
EXP-002 (both local), then adapters, then V0.
