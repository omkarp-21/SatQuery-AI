# SatQuery Experiment Registry

> Status: **Active — binding** · Owner: _TBD_ · Last updated: 2026-09-02 (G12)
> Real **integrated, sanity-scale** results now exist for EXP-002 (VQA/grounding,
> G11), EXP-004 Run 2 (DFC2020 optical+SAR probe, G12) and EXP-008 (LoRA
> adaptation, G12) — each labelled sanity-scale, none a full benchmark. EXP-004
> Run 1 is a *synthetic sanity check*; ChangeFormer's IoU 0.83 (n=7) is a
> *reproduction sanity*. Results are filled only from real runs
> (see [`18_RESEARCH_TO_ACCURACY.md`](18_RESEARCH_TO_ACCURACY.md)). Do not invent numbers.
> The canonical set of seven experiments is defined in `chatgpt.context.md` §11.

## Why this file exists

Without a registry, model trials happen off the record and we keep rediscovering
the same things. This file is the scientific history of SatQuery: what we asked,
what we measured, what we decided.

## Rules

- One experiment = one ID (`EXP-NNN`), allocated in order, never reused.
- An experiment must exist **before** the work starts, in status `PLANNED`.
- Every hypothesis in doc 18 (H1–H5) maps to at least one experiment. Some
  experiments are **selection bake-offs** (no hypothesis) — that is fine.
- The **three numbers** stay separate (paper / reproduction / SatQuery). State
  which one each result is.
- Every finished experiment ends with a `DECISION: KEEP | REJECT | INVESTIGATE`.
- Link the experiment from the PR and from the `evaluation/cases/` entry it uses.

## Status lifecycle

`PLANNED → RUNNING → MEASURED → DECIDED` (or `BLOCKED`, with reason).

## Entry schema

```
## EXP-NNN — <short title>
- Status: PLANNED | RUNNING | MEASURED | DECIDED | BLOCKED
- Hypothesis: H# (or "n/a — selection")
- Question: <the one question this answers>
- Owner: <name>              Date: <start> → <end>
- Models / methods: <exact repos, checkpoints, commits, configs>
- Dataset: <source, license, region, sensor>   Split: <train/val/test, leakage check>
- Metric: <precise definition>
- Preprocessing: <steps>      Inference config: <params, seed>
- Hardware: <GPU/CPU, VRAM, batch>
- Baseline: <what, and its measured value — number type: reproduction/SatQuery>
- Result: <measured value — number type>   Δ vs baseline: <with n, seed>
- Failure cases: <concrete inputs where it breaks>
- Notes / threats to validity:
- DECISION: KEEP | REJECT | INVESTIGATE — <one line why>
- Artifacts: evaluation/reports/EXP-NNN/... ; evaluation/cases/... ; PR #
```

---

## EXP-001 — Generic VLM vs RS-adapted VLM

- Status: PLANNED
- Hypothesis: H1
- Question: Does a remote-sensing-adapted VLM outperform a generic VLM on RS VQA
  and visual grounding?
- Models / methods: GeoChat (`external/research/GeoChat`, released checkpoint) vs a
  generic open VLM baseline (TBD — e.g. LLaVA-1.5-7B, same size class).
- Dataset: TBD held-out RS VQA + grounding set (candidates: RSVQA-LR/HR, VRSBench,
  DIOR-RSVG subset). License and region to be recorded.
- Split: held-out test only; check no overlap with GeoChat instruction data.
- Metric: VQA exact-match / accuracy; grounding acc@IoU0.5.
- Baseline: the generic VLM (our reproduction number).
- Result: _not measured_.
- Failure cases: _tbd_.
- DECISION: _pending_.

## EXP-002 — Candidate single-image RS-VLM comparison

- Status: **DONE (G11, 2026-09-02) — A + B both MEASURED + INTEGRATED.**
  `HF_HUB_ENABLE_HF_TRANSFER=1` pulled TinyRS-2B + Qwen2-VL-2B + RemoteSAM weights
  (previously failed 7×); non-gated HF mirrors found for both eval sets.
  **A (VQA):** TinyRS-2B **balanced acc 0.8736** on 40 RSVQA-LR yes/no (CPU,
  p50 4.45 s) → PRIMARY; Qwen2-VL-2B control 0.7033 → FALLBACK. **RSCoVLM-3B does
  not exist** (only 7B released). **B (grounding):** RemoteSAM **acc@IoU0.5 = 0.84
  (21/25)** on frozen DIOR-RSVG (CPU, p50 29 s). Both integrated: `TinyRsAdapter`
  + `RemoteSamAdapter`, `/analyze` `SINGLE_IMAGE_VQA` / `SINGLE_IMAGE_GROUNDING`.
  `docs/research/EXP-002.md` §G11, `EXP-GROUNDING.md`, ADR-020. Reports:
  `evaluation/reports/exp002_vqa_*.json`, `exp_grounding_dior_*.json`.
  Open: larger samples (n=40/25 are sanity-scale) + GPU/4 GB-VRAM verification.
  _Earlier (G5A): BLOCKED on artifact acquisition, 6 download failures (ADR-013)._
- Hypothesis: n/a — selection bake-off
- Question: Among candidate single-image RS-VLMs, which gives the best
  accuracy / latency / integration-cost trade-off for SatQuery's single-image path?
- Models / methods (**revised by the Lightweight Model Replacement Audit,
  2026-09-01 — `docs/research/LIGHTWEIGHT_AUDIT.md`, ADR-011**):
  **PRIMARY = RSCoVLM-3B** (`Qingyun/rscovlm`, Qwen2.5-VL-3B, MIT code / CC-BY-4.0
  data — RS multi-task VQA + grounding + captioning; 4 GB only at 4-bit).
  **FALLBACK = TinyRS-2B** (`aybora/Qwen2-VL-TinyRS`, Apache-2.0; surer 4 GB fit;
  download BLOCKED). **CONTROL = Qwen2-VL-2B-Instruct** (Apache-2.0, generic,
  native bbox grounding — value-of-RS-adaptation baseline). **CEILING = GeoChat**
  (+ **EarthDial-4B**, `akshaydudhane/EarthDial_4B_*`, MIT code+weights, +SAR
  +temporal) on a rented GPU ≥16 GB. **Rejected:** SkyEyeGPT (no inference recipe),
  ISRO-GeoNLI (wrapper, 36 GB), RS-MoE (no weights). RemoteCLIP zero-shot as the
  scene-classification reference.
- Dataset: an **RSVQA-LR** sample for VQA; a **DIOR-RSVG** sample for grounding
  (capability B). Held-out; check overlap with each model's instruction data.
- Metric: VQA accuracy; grounding acc@IoU0.5; measured p50/p95 latency (4-bit CPU
  vs GPU); integration-cost note. **Define a "usable" threshold before running**
  (`EXPERIMENT_DECISION_TREE.md`).
- Baseline: whichever candidate is wired first (its reproduction number).
- Result: _not measured_.
- Notes: compare each model only on tasks it supports; picks the model for **A + B**.
- DECISION: _pending_ — KEEP one local VLM, or trigger the remote-GPU gate.

## EXP-003 — Temporal stack: Change-Agent vs ChangeChat vs ChangeFormer

- Status: PLANNED
- Hypothesis: n/a — selection bake-off (informs H2)
- Question: Which temporal stack gives the best combination of change-mask quality,
  semantic change interpretation, speed, and integration stability?
- Models / methods (G1.6): **Arm 1 (local, first):** ChangeFormer mask → connected
  components → caption each region with the EXP-002 single-image VLM → rule-assemble
  a change description. **Arm 2 (remote ceilings):** Change-Agent `MCI_model.pth`
  (Linux+conda), TEOChat, UniRS — only if Arm 1 underperforms. ChangeChat
  **excluded** (no weights; README now ≥48 GB to train).
- Dataset: LEVIR-CD (mask) + **LEVIR-MCI / LEVIR-CC** (mask + caption) sample.
- Metric: change-mask IoU / F1; change-caption BLEU-4 / CIDEr / METEOR; change-QA
  accuracy where available; p50/p95 latency; stability note.
- Baseline: image-difference + threshold (mask); a rule-only captioner.
- Result: _not measured_.
- Notes: ChangeFormer already MEASURED as the mask worker (IoU 0.83 / n=7).
- DECISION: _pending_ — keep ChangeFormer + a chosen semantic/language layer.

## EXP-004 — Optical-only vs optical + SAR  ⭐ (G1.5, ADR-005)

- Status: **DONE (G12, 2026-09-02)** (`docs/research/EXP-004.md`). Run 1 =
  synthetic sanity. **Run 2 = real DFC2020 probe** — `hf_transfer` +
  non-gated mirror `125oii/dfc2020` pulled the validation split (s1 947 MB +
  s2 633 MB + dfc 6 MB) in ~2.5 min. 400 train / 200 eval, seed 20260902, CPU,
  frozen encoder + `LogisticRegression` probe on dominant-land-cover (8 classes).
  **CROMA joint macro-F1 0.793 vs CROMA optical 0.726 (+0.067, bootstrap 95% CI
  includes 0 → positive but NOT significant at n=200, McNemar p=0.45).** DOFA
  concat-fusion −0.018 (no gain). Reports: `evaluation/reports/exp004_run2_*.json`.
- Hypothesis: H3
- Question: For suitable queries (built-up / informal-settlement classification),
  does a **joint optical+SAR** representation improve the result vs optical-only?
- Models / methods (G1.6 — both encoders **REPRODUCED** on CPU): 3 arms, same
  linear-probe head, same split, same budget —
  (1) **optical-only** (CROMA `optical_GAP` or RemoteCLIP image features);
  (2) **CROMA** `joint_GAP` (native joint radar-optical);
  (3) **DOFA** S1⊕S2 features concatenated (downstream fusion).
  All run on the 4 GB laptop / CPU — no GPU box.
- Dataset: a **fixed, recorded subset** of reBEN / BigEarthNet v2 (Zenodo
  `10891137`) — paired Sentinel-1 (VV/VH, dB) + Sentinel-2 (12-band), held-out
  split, leakage-checked. **Subset only** (a few k patches), not the full 549 k.
- Preprocessing: CROMA's channel norm; S1 in dB; 120×120 tiling; record CRS/GSD.
- Metric: per-class F1 / mAP for built-up + 2–3 other classes; **explicitly report
  where SAR hurt**. p50 latency of the joint encoder.
- Baseline: optical-only head (its reproduction number).
- Result: _not measured_.
- Notes: also produces the adaptation evidence for requirement E — the probe head
  IS a bounded BigEarthNet adaptation (see EXP-008, shares this pipeline).
- DECISION (G12): **KEEP CROMA** for the optical–SAR path (won the bake-off on
  downstream macro-F1, 0.793 vs 0.708; the only arm where SAR helped). DOFA =
  challenger/fallback. **H3 = INVESTIGATE → lean KEEP** — SAR helps CROMA
  (+0.067) but not significantly at n=200; a larger eval split is the honest next
  step before a strong claim.
- **G18 ADDENDUM (2026-09-03) — the larger split was run; the SAR benefit did NOT
  survive.** Full DFC2020 `ROIs0000_validation` (986 patches), independent
  600/386 split `evaluation/datasets/dfc2020_g17_larger_split.json` (**G12 400/200
  split untouched**), same frozen-encoder + probe method + bootstrap + McNemar.
  **CROMA optical-only macro-F1 0.8505 vs joint 0.8247 (Δ −0.0258; 95% CI
  [−0.0796, +0.0267]; McNemar p = 1.0).** DOFA fused 0.8177 vs optical 0.8374.
  The point estimate **flipped sign** and was never significant. **H3 verdict →
  the "SAR improves the downstream task" claim is WITHDRAWN**
  (`docs/sih/CLAIM_MATRIX.md` §6, `docs/G18_RELEASE_REPORT.md` Part 2). CROMA
  still ≥ DOFA on the primary metric on both splits → **CROMA stays D primary**;
  the joint *representation* remains integrated (no textual claim derived from
  it). Reports: `evaluation/reports/exp004_run2_g18_larger_*` (gitignored).

## EXP-008 — RS adaptation probe on DFC2020 (requirement E)

- Status: **DONE (G12, 2026-09-02)** (`docs/research/EXP-008.md`). Ran on the
  EXP-004 Run 2 winner (**CROMA**), the same frozen DFC2020 split (400/200, seed
  20260902), CPU. 3 arms, one shared torch linear head, 6 epochs each.
- Hypothesis: n/a — mandatory-capability evidence (PS §Adaptation)
- Question: Does a bounded PEFT adaptation (LoRA) of a frozen RS encoder
  measurably improve the downstream task vs the frozen encoder, and is it
  *sufficient* (no full fine-tune)?
- Method: LoRA r=8 α=16 on CROMA attention Linear layers (42 wrapped, **811 k
  trainable params = 0.4 % of the backbone; 3.24 MB adapter**) + linear head vs
  frozen encoder + linear head vs optical-only + linear head.
- Result: **macro-F1 — optical-only 0.656 · frozen fused 0.643 · LoRA-adapted
  0.704.** Adapted − frozen = **+0.061** (clears the pre-registered +0.03
  threshold). Not significance-tested (n_eval 200). Inference cost unchanged.
- DECISION (G12): **ADOPT LoRA as the E adaptation method** (rule met; no
  deployment blocker). Production default stays the **frozen** encoder until a
  larger-split, bootstrapped re-run confirms the gain. Additive opt-in load path,
  not an architecture change.
- **G18 ADDENDUM (2026-09-03) — larger-split re-run + adapter persisted + plumbing
  verified.** Same 986-patch independent 600/386 split, 3 CPU epochs (vs G12's 8,
  for time budget). **LoRA-adapted joint macro-F1 0.6686 vs frozen fused 0.5422
  (+0.1264) vs optical-only frozen 0.5772 (+0.0914); frozen fused − optical
  −0.0350.** 811 k params / 3.24 MB delta / 42 layers / CPU RSS 1.73 GB. The LoRA
  lift over frozen **replicates G12's direction and is larger here**, BUT: no
  bootstrap CI / no paired test in this run, and the frozen arms are 3-epoch
  AdamW linear heads (under-trained — the fully-converged Part-2 probe scored
  ~0.85 on the same frozen features), so Part-2 and Part-3 absolute numbers are
  **not comparable**; only the within-Part-3 arm deltas are. Adapter persisted
  `models/checkpoints/exp008_croma_lora.pt`; `--lora-weights` verified end-to-end
  through the real `CromaAdapter` (`test_croma_lora_adapter_loads_and_changes_representation`
  — 42/42 wrapped Linears matched, joint embedding measurably shifted, provenance
  `encoder_mode` + adapter sha256 recorded). **Decision unchanged: production
  default stays FROZEN CROMA** (a directional 3-epoch CPU run with no significance
  test is not grounds to flip a production default; the G18 D finding removes the
  task-benefit objective anyway). LoRA stays opt-in. Reports:
  `evaluation/reports/exp008_g18_larger_*` (gitignored).

## EXP-005 — Structural verifier detection

- Status: **RUN — structural part done (2026-09-01, G6). `docs/research/EXP-005.md`.**
- Hypothesis: H4
- Question: Does `verify()` detect structural defects, and what does it miss?
- Method: 24-case curated corpus (CLEAN 6 / STRUCTURAL 8 / SEMANTIC 6 /
  INSUFFICIENT 4) exercising every rule in `verifier.py`.
  `evaluation/scripts/exp005_verifier_detection.py` + 3 lock tests.
- Result: **structural-defect detection precision / recall / F1 = 1.00**
  (TP 8, FP 0, TN 12, FN 0; 4 INSUFFICIENT correct). **Semantic-defect miss rate
  = 1.00** (0/6 structurally-clean-but-wrong cases flagged) — by design.
- **EXP-005b (G7): model-independent semantic verifier built + measured.**
  `verify_semantic()` — 6 checks (claim↔number, claim↔label, temporal direction,
  region geometry, whole-scene region, area arithmetic). Curated n=34 corpus →
  **P/R/F1 = 1.00** for internal-incoherence detection (TP 10/FP 0/TN 14/FN 0);
  **BEYOND_SCOPE residual miss rate 1.00** (label-correctness needs a second
  model). INTEGRATED into `COMPOSED_SEMANTIC_CHANGE_BASELINE`.
  `evaluation/scripts/exp005b_semantic_verifier.py` + 9 lock tests.
- DECISION: structural verifier = **VALIDATED (structural)**; semantic verifier =
  **MEASURED + INTEGRATED (experimental, model-independent subset)**. Remaining:
  `independent_model_agreement` + `optical_sar_agreement` (EXP-002 / EXP-C2).
  Confidence: EXP-C1/C2 specified in `CONFIDENCE_PLAN.md`, blocked on a scored model.
- Caveat: both corpora are n≈30, author-curated → prove the checks fire on their
  target defect classes, **not** a real-world coverage rate. Grow with real
  `/analyze` failures before quoting outside `EXP-005.md`.

## EXP-006 — LLM-only routing vs constrained deterministic/agentic routing

- Status: **RUN (G14, 2026-09-02)** — `docs/research/EXP-006_AGENTIC_PLANNER.md`.
  The agentic geospatial investigator: PLANNER (LlmPlanner local Qwen2-VL-2B
  text-only / RuleBasedPlanner default) → typed `AgentPlan` → 12-check POLICY
  layer → bounded executor (≤ 8 specialist calls; observe / verify / conditionally
  replan) → evidence-first synthesis. The deterministic router is **not**
  replaced — it stays the execution guard; `run_analyze` is the fallback.
- Hypothesis: H2
- Question: Does a constrained planner + deterministic policy guard produce
  correct multi-step specialist plans without replacing the router, and add
  functional value over single-shot `/analyze` on multi-step missions?
- Method: `packages/agents/src/satquery_agents/agent/` (schemas, registry, policy,
  planner, prompts, memory, verifier) + `apps/backend/app/services/agent_runner.py`
  + `POST /investigate`. Task ontology (12 closed tasks), tool registry (12 closed
  tools with metadata). `evaluation/agent/` — 30 frozen missions (6 categories),
  `run_agent_eval.py` (plan phase all 30 + exec phase bounded sample + agent-vs-
  baseline).
- Result (plan phase, 30 missions, rule planner, CPU): **plan validity 0.967,
  tool-selection accuracy 1.00, task-order correctness 1.00**, avg 2.4 specialist
  steps/plan, failed-plan rate 0.033 (adv-5 misregistered pair correctly
  rejected). Exec phase + baseline comparison: see `EXP-006_AGENTIC_PLANNER.md` /
  `evaluation/agent/reports/latest.json`.
- DECISION (G14): **KEEP** — the agent produces valid multi-step plans, never
  runs a forbidden tool, preserves evidence/verification/provenance, and on
  multi-step missions runs multiple required specialists where the deterministic
  baseline routes to one. SatQuery's differentiating feature.

## EXP-007 — Geospatial validation ON vs OFF

- Status: PLANNED
- Hypothesis: H5
- Question: Does the geospatial integrity layer (CRS check, co-registration
  assertion, GSD check, NoData handling) measurably reduce invalid analyses and
  spatial-reasoning failures?
- Models / methods: `packages/geospatial` validation gate on vs off, feeding the
  EXP-003 / EXP-004 pipelines.
- Dataset: a stress set of deliberately mismatched pairs (different CRS, sub-pixel
  and gross offset, different GSD, missing NoData) mixed with valid pairs.
- Metric: fraction of invalid pairs correctly rejected; downstream change-metric
  error with vs without the gate; count of fake "change" from misregistration.
- Baseline: gate disabled.
- Result: _not measured_.
- DECISION: _pending_.

---

## Index

| ID | Focus | Hypothesis | Status | Decision |
|----|-------|-----------|--------|----------|
| EXP-001 | generic vs RS-adapted VLM | H1 | PLANNED (blocked on GPU box) | — |
| EXP-002 | single-image VLM A/B gate — VQA + grounding | selection | **DONE (G11)** — TinyRS-2B VQA bal-acc 0.87 (PRIMARY) / Qwen2-VL-2B 0.70 (fallback); RemoteSAM grounding acc@IoU0.5 0.84; RSCoVLM-3B does not exist. ADR-020 | KEEP TinyRS-2B + RemoteSAM |
| EXP-003 | temporal-language — composed baseline vs remote VLMs (a); crop strategy (b) | selection (→H2) | **EXP-003b RUN** (crop strategy: agreement 4/6, `expanded` provisional); EXP-003a BLOCKED (remote) | `EXP-003.md` |
| **EXP-004** | **optical vs optical+SAR — CROMA vs DOFA** | **H3** | **DONE (G12 + G18)** — G12 n=200: CROMA joint 0.793 vs optical 0.726 (+0.067, n.s.). **G18 n=386 larger split: joint 0.8247 vs optical 0.8505 (Δ −0.026, n.s.) — SAR benefit did NOT survive** | **KEEP CROMA** (D primary; CROMA ≥ DOFA both splits); **H3 → "SAR improves the task" claim WITHDRAWN** |
| EXP-005 | verifier detection — structural (a) + model-independent semantic (b) | H4 | **RUN** — 005a structural P/R/F1 = 1.00 (n=24); 005b semantic P/R/F1 = 1.00 (n=34), INTEGRATED; label-correctness gap remains | `EXP-005.md` |
| EXP-006 | agentic planner + policy guard vs single-shot routing | H2 | **DONE (G14)** — plan validity 0.967, tool-selection 1.00, task-order 1.00 (30 frozen missions); agent runs multiple required specialists on multi-step missions where the baseline routes to one | **KEEP** — the differentiating feature |
| EXP-007 | geospatial safeguard stress test | H5 | **RUN — 15/15 pass** (`EXP-007.md`) | KEEP the gate |
| EXP-008 | RS adaptation probe (req. E) | n/a | **DONE (G12 + G18)** — G12 8ep: 0.643→0.704 (+0.061). G18 larger split, 3 CPU ep: LoRA 0.6686 vs frozen fused 0.5422 (+0.126) vs optical 0.5772 (+0.091); direction replicates, no significance test | **LoRA is the E method**; prod default stays **frozen CROMA**; `--lora-weights` opt-in, adapter persisted + verified through `CromaAdapter` |

Hypothesis coverage: H1→EXP-001, H2→EXP-006 (informed by EXP-003), H3→EXP-004,
H4→EXP-005, H5→EXP-007. Mandatory-capability coverage without a hypothesis:
req. E → EXP-008.
