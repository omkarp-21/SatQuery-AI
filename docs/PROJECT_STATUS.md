# SatQuery — Project Status

> Living status file (see `chatgpt.context.md` §24). Update every significant
> session. No fabricated numbers — "not measured" is the honest value until a real
> run exists. Last updated: **2026-08-31**.

---

## DONE (and how it was verified)

| Item | Verification |
|------|--------------|
| PS 26167 requirements captured | `chatgpt.context.md` §4; mapped in `docs/20_PROTOTYPE_ROADMAP.md` |
| Monorepo structure `apps/` + `packages/` + `external/` | `git ls-files`; ADR-001 in `docs/DECISIONS.md` |
| Claude Code harness: `CLAUDE.md`, 9 rules, 18 skills, 11 subagents | files present under `.claude/`; frontmatter checked |
| Strategy docs `docs/17`–`docs/21` | files present; cross-linked from `CLAUDE.md` |
| `chatgpt.context.md` committed as persistent strategic memory | this session; ADR-003 |
| 6 research repos cloned into `external/research/` at pinned commits | `git -C <repo> rev-parse HEAD` matches `docs/research/model_inventory.md`; gitignored (`!!`) |
| Research inventory + compatibility + env strategy | `docs/research/{model_inventory,repository_compatibility,environment_strategy}.md` |
| Package skeletons (`pyproject.toml`, src layout) + adapter stubs | `python -m py_compile` passes; adapters raise `NotImplementedError` |
| `model_registry.yaml` with capability + routing entries | file present; dotted paths resolve to `satquery_model_adapters.*` |

**Nothing intelligent works yet.** All of the above is structure, process, and inventory.

---

## IN PROGRESS

- V0 vertical slice — *not started*. Next up.
- Candidate model environment validation — planned per `docs/research/environment_strategy.md`.
- Model comparison matrix — skeleton in `docs/research/MODEL_COMPARISON.md`, unfilled.

---

## BLOCKED

| Blocker | Impact | Path forward |
|---------|--------|--------------|
| **ChangeChat has no released weights** + missing `requirements.txt` at pinned commit | EXP-002 / EXP-003 cannot include ChangeChat as a runnable option | proceed with Change-Agent vs ChangeFormer; revisit if weights ship |
| **No confirmed GPU on dev host** (Windows 11) | Cannot run 7B VLMs or CUDA-only stacks (`bitsandbytes`, `deepspeed`, `mmcv 1.x`) natively | decide: WSL2 + Docker + NVIDIA toolkit, or a cloud GPU box; CPU-only for RemoteCLIP / ChangeFormer demo |
| **ChangeFormer pins CUDA 10.2** | Won't run on Ampere+ GPUs as-is | rebuild env on torch ≥1.12 / cu113+ (model code is portable) or CPU |

---

## MISSING (required, not yet built)

- Reproduced model benchmarks (number #2) — none.
- Baseline metrics and SatQuery metrics (number #3) — none.
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

**None measured.** All experiment entries in `docs/19_EXPERIMENT_REGISTRY.md` are
`PLANNED`. Do not populate this section with anything that is not the output of a
real run, tagged with dataset / split / seed / hardware / date and labelled as
paper / reproduction / SatQuery.

| Metric | Value | Dataset | Split | Date | Number type |
|--------|-------|---------|-------|------|-------------|
| — | not measured | — | — | — | — |

---

## RISKS

| Risk | Severity | Mitigation |
|------|----------|------------|
| Environment fragmentation across 5 research models | High | per-model container/venv (`docs/research/environment_strategy.md`); integrate one at a time |
| No GPU on dev host → slow iteration + demo latency | High | secure a GPU path early; keep a CPU-capable fallback demo (RemoteCLIP + ChangeFormer) |
| Adaptation requirement (BigEarthNet) not scoped | High | scope a minimal LoRA/adapter fine-tune on one component before freezing architecture |
| Novelty currently asserted, not measured | High | EXP-004–EXP-007 must produce real deltas before any novelty claim in the PPT |
| ChangeChat unusable → narrows temporal options | Medium | Change-Agent vs ChangeFormer decision via EXP-003 |
| Scope creep vs hackathon time budget | Medium | scope-control checklist (`chatgpt.context.md` §27); cut anything without an eval path |
| Six-slide PPT claims outrunning the prototype | Medium | slide claims gated on `docs/PROJECT_STATUS.md` METRICS + demo path |

---

## NEXT 3 ACTIONS (highest leverage only)

1. **Build V0**: `POST /query` → ingestion + metadata (real CRS/transform/bounds
   extraction) → RemoteCLIP adapter (real checkpoint, zero-shot tag/retrieve) →
   reports. One demo GeoTIFF, offline. Feature-complete per `docs/17`.
2. **Stand up the real eval harness**: `evaluation/scripts/run_suite.py` + one
   metric (unit-tested) + one `evaluation/cases/` entry; move **EXP-001** to
   `RUNNING` with a concrete dataset + baseline model chosen.
3. **Decide the GPU/environment path** and get **one** reproduction number (#2):
   load GeoChat *or* ChangeFormer, run a single real inference, record it.

---

## WIN SCORECARD (0–10 — honest, early baseline)

| Dimension | Score | Why |
|-----------|:----:|-----|
| Problem fit | 4 | requirements understood + documented; nothing built against them |
| Novelty | 2 | contribution areas named; none validated |
| Technical depth | 3 | strong architecture/process docs; no working intelligence |
| Prototype completeness | 1 | skeleton only, no end-to-end path |
| Accuracy | 0 | nothing measured |
| Multimodal (optical–SAR) reasoning | 0 | not started |
| Temporal reasoning | 0 | not started |
| Geospatial integrity | 2 | rules + skill written; no code |
| Evidence / verification | 1 | designed; not built |
| UI / UX | 1 | dir skeleton + design skill |
| Benchmark readiness | 1 | benchmarks identified; none acquired; harness is a stub |
| Feasibility | 5 | plan is realistic; environment fragmentation is the main threat |
| Impact | 4 | clear institutional relevance in the framing |
| PPT quality | 3 | six-slide blueprint + story defined; no evidence content |
| Demo quality | 0 | no demo path yet |

**Read:** strong strategic and organizational foundation; **zero measured
capability.** The single highest-value move is a working V0 plus the first real
measurement. Scores will only rise on evidence — explain every change here.
