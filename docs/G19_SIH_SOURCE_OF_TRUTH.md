# G19 — SIH Source of Truth

> The single reference every SIH-facing artefact (slides, script, Q&A, demo)
> must agree with. If a sentence is not supported here, it does not go on a
> slide or in an answer. Nothing here is new — it is distilled from
> `docs/PROJECT_STATUS.md`, `docs/sih/CLAIM_MATRIX.md`,
> `docs/G18_RELEASE_REPORT.md`, `docs/G18_RELEASE_AUDIT.md`,
> `docs/G18_RELEASE_MANIFEST.md`, `README.md`, `docs/API_CONTRACT.md`, and the
> frozen demo evidence in `docs/sih/evidence/demos/final/`.

Build: commit `aa87c28` (G19) on `docs/lightweight-model-audit`; G18 release
candidate = `d060dce`. Python 3.11, Windows dev host, **CPU-only**
(`torch.cuda.is_available() == False`). `FINAL_TECH_FREEZE = TRUE` (Part 23).

---

## 1. What we CAN claim (with evidence)

| # | Claim | Evidence | N |
|---|-------|----------|---|
| C1 | SatQuery turns a **natural-language geospatial mission** into a validated multi-step investigation across a frozen set of specialist models. | `POST /investigate`; G14–G17; `docs/sih/evidence/demos/final/` | 100 frozen missions (plan), 8 (exec) |
| C2 | The **production planner is deterministic** (`RuleBasedPlanner`). | G17 eval: PLAN_VALIDITY 0.886 / TOOL_SELECTION 0.90 / < 0.01 s | 100 |
| C3 | A **pure local LLM planner was built, measured, and rejected** for production. | G16: semantic plan validity 0.25, tool-selection 0.40, example-echo; exec factual-consistency 0.33 | 15 (plan) |
| C4 | An **LLM-intent hybrid planner is optional** (`SATQUERY_PLANNER=hybrid`); it does not beat the deterministic planner on this hardware. | G17: INTENT_TASK_ACCURACY 0.317; plan validity 0.591 < 0.886 | 100 |
| C5 | Execution is **bounded and observation-driven**: ≤ 8 specialist calls, a closed 6-reason replan enum, explicit early-stop. | G15/G16/G17; exec MAX_STEP_VIOLATION 0.00, UNSUPPORTED_ACTION 0.00 | 8–20 |
| C6 | **CASE A vs CASE B**: the same frozen mission produces a longer or shorter investigation depending on what ChangeFormer actually observes — not a hard-coded branch. | `flagship_caseA_change.json` (4 tool calls) vs `flagship_caseB_nochange.json` (2 tool calls, 2 replans, early-stopped) | 2 |
| C7 | Every raster is **geospatially validated** (CRS / transform / bounds / co-registration); malformed or misregistered input is rejected with a typed error; **no fabricated coordinate** is ever emitted. | EXP-007 15/15; `test_g18_failure_matrix.py` 22/22 | 15 + 22 |
| C8 | Every factual claim in a result **traces to an observed specialist step or an evidence item**; a fixed list of over-claiming phrases is blocked. | `test_g18_claim_evidence.py` 69/69 | ~30 claims + 5 synth |
| C9 | Confidence is an **evidence-derived category** (`HIGH / MEDIUM / LOW / INSUFFICIENT_EVIDENCE`) computed by documented deterministic rules, with an explicit "why" list. | `apps/backend/app/services/trust.py`; `docs/G17_TRUST_LAYER.md`; `test_g18_trust_cases.py` 32/32 across 7 scenario families | 30 |
| C10 | 22 pathological conditions all resolve **without an HTTP 500, a hallucinated result, a fabricated box/coordinate/confidence, or a hidden fallback**. | `test_g18_failure_matrix.py` | 22 |
| C11 | The system runs **fully on CPU on a laptop**; one specialist model is resident at a time (subprocess per specialist). | G18 Part 4; `docs/G18_RELEASE_MANIFEST.md` | — |
| C12 | **383 fast tests pass, 0 failed, 0 regressions**; the slow adapter suite is 9/9. | G18 Part 10 + G19 report-endpoint test | 383 |
| C13 | Specialist quality, **sanity-scale, integrated**: VQA bal-acc **0.87** (RSVQA-LR n=40); grounding acc@IoU0.5 **0.84** (DIOR-RSVG n=25); ChangeFormer change-IoU **≈0.83** (n=7, reproduction). | `EXP-002` §G11, `EXP-GROUNDING`, `EVIDENCE_LEDGER` | 40 / 25 / 7 |
| C14 | **CROMA is the selected optical+SAR representation** for the multimodal path (CROMA ≥ DOFA on the primary metric on **both** DFC2020 splits). | EXP-004 Run 2 (G12) + G18 larger split | 200 + 386 |
| C15 | **LoRA on frozen CROMA** is wired as an optional, provenance-tracked path (`--lora-weights`), verified end-to-end through the real adapter (42/42 layers). On a larger split it lifted the probe macro-F1 **directionally** (+0.09 vs optical), consistent with the first split. | EXP-008 (G12 + G18); `test_repr_adapters.py` | 200 + 386 |

## 2. What we CANNOT claim

| Forbidden claim | Why | Say instead |
|-----------------|-----|-------------|
| "SAR improves the downstream task" / "SAR fusion improves accuracy" / "CROMA joint outperforms optical" | G12 +0.067 was within noise; on the larger independent split it **reversed** to −0.026, never significant. **Claim withdrawn.** | "CROMA is the selected optical+SAR representation; the larger validation did **not** support the earlier SAR-benefit claim — and we withdrew it." |
| "LoRA significantly improves accuracy" / "SatQuery uses an adapted CROMA" | 3-epoch CPU run, no bootstrap/paired test, under-trained frozen baselines; production default is the frozen encoder. | "LoRA adaptation is an optional path; its larger-split gain is directional, not significance-tested." |
| "state-of-the-art" / "benchmark result" | Every eval is sanity-scale (n = tens–hundreds), not a benchmark. | "measured, sanity-scale, integrated-system result (n = …)." |
| "fully autonomous" / "the AI decides everything" / "autonomous agent" | The deterministic system is the execution guard; the LLM never controls execution. | "bounded agentic execution" / "policy-constrained, evidence-backed orchestration." |
| "real-time" | Latency is not optimised or measured against a real-time budget; a cold flagship run is ~90 s. | "runs on a laptop in ~90 s cold / seconds warm." |
| "hallucination-free" / "no hallucinations" | Unprovable; we constrain and verify, we do not guarantee. | "every claim is traced to an observation and structurally verified; over-claiming phrases are blocked." |
| "runs in 4 GB VRAM" / any VRAM number | No CUDA build on the dev host → **GPU FIT = UNVERIFIED**. | "runs fully on CPU; the 4 GB-GPU fit is unverified." |
| "calibrated confidence" / "X % confident" / any confidence number | `trust.py` produces a category from deterministic rules, not a probability. | "an evidence-derived confidence **category** with an explicit why." |
| "change captioning" / "temporal VLM" / "understands what changed" | Semantic-change description is a composed baseline (mask → components → zero-shot tags), not a learned model. | "an experimental composed baseline that describes changed regions." |
| "benchmarked on RSVQA / DIOR-RSVG" | Those are 25–40 item samples, not the benchmarks. | "on an RSVQA-LR / DIOR-RSVG **sample** (n = …)." |

## 3. Exact metrics allowed (copy verbatim; always with N)

- **VQA** — "balanced accuracy **0.87** on an RSVQA-LR sample, **n = 40**, CPU, via the integrated adapter (TinyRS-2B primary, Qwen2-VL-2B fallback)."
- **Grounding** — "acc@IoU0.5 **0.84** (21/25), mean IoU 0.762, 0 no-box, on a DIOR-RSVG sample, **n = 25**, CPU (RemoteSAM)."
- **Change detection** — "ChangeFormer, change-IoU **≈ 0.83** on a bundled LEVIR-CD demo set, **n = 7** — a *reproduction* number, not a SatQuery benchmark."
- **Optical+SAR probe (D)** — "DFC2020 land-cover, frozen encoder + linear probe: CROMA optical-only **0.8505** vs joint **0.8247** on the G18 larger split (n = 386); the SAR benefit did **not** survive. G12 n = 200: joint 0.793 vs optical 0.726 (+0.067, not significant)."
- **LoRA (E)** — "G18 larger split, 3 CPU epochs: LoRA-adapted joint **0.6686** vs frozen fused **0.5422** vs optical-only frozen **0.5772**; +0.09 vs optical, direction replicates G12 (+0.061, n = 200), **no significance test**."
- **Planner eval** — "RuleBasedPlanner (production default): PLAN_VALIDITY **0.886**, TOOL_SELECTION **0.90**, latency **< 0.01 s**, on **100** frozen missions. Execution sample (N = 8): mission-completion / factual-consistency / evidence-preservation / verification-preservation all **1.00**; UNSUPPORTED_ACTION_RATE **0.00**."
- **Agent leverage** — "on multi-step missions the agent runs **≈ 2.25×** the deterministic baseline's specialist calls" (G17; small N — state it).
- **Trust layer** — "validated against **30** frozen cases across **7** scenario families; category matches the written policy in 32/32 tests."
- **Geospatial safeguards** — "EXP-007 **15/15** malformed-pair classes rejected before any model runs; G18 failure matrix **22/22** pathological inputs → structured resolution, no 500, no fabricated coordinate."
- **Tests** — "**383 fast tests pass, 0 failed, 0 regressions**; slow adapter suite **9/9**."
- **Flagship latency** — "CASE A ≈ **93 s** cold (ChangeFormer 16 s + RemoteSAM 62 s + CROMA 14 s; ≈ 90 % is model loading). CASE B ≈ **17 s**. Secondary grounding ≈ **65 s** cold / seconds warm."

Numbers **not** to put on a slide as a positive: any SAR-benefit delta; any VRAM figure; any confidence percentage; any "significant"/"p < …" claim.

## 4. Exact wording for the limitations

Use these sentences as-is:

1. "Evaluation is **sanity-scale** (n = tens to hundreds), not a full benchmark; every number carries its N and a significance caveat."
2. "On DFC2020 land-cover classification, **adding SAR did not measurably improve the downstream task** — the first split's small positive delta was within noise and reversed on a larger independent split, so we **withdrew that claim**."
3. "The **4 GB-GPU fit is UNVERIFIED** — there is no CUDA build on the development host, so no VRAM number is claimed. The CPU path is the shipped path and is fully functional."
4. "The **RemoteSAM checkpoint licence is NOT STATED** upstream (repo, model card and paper are silent). RemoteSAM is packaged as an **optional** component; every other capability works without it."
5. "The **pure local LLM planner is rejected for production**; the hybrid LLM-intent planner is **optional** and does not beat the deterministic planner on this hardware."
6. "Confidence is an **evidence-derived category, never a probability or a number**."
7. "Semantic *description* of change is an **experimental composed baseline**, not a learned temporal vision-language model."

## 5. Flagship demo facts (frozen — `docs/sih/evidence/demos/final/`)

**Mission (frozen, both cases):** *"Investigate this area. Identify significant
changes between the two observations, locate the affected structures, compare
optical and SAR evidence, and provide a verified summary."*
**Planner:** `rule_based` (production default). **Inputs:** 4 tiles in
`data/demo/investigation/` (2 optical observations + 1 SAR + 1 no-change optical).

| | CASE A — significant change | CASE B — minimal / no change |
|---|---|---|
| plan (9 tasks) | `VALIDATE_INPUT → TEMPORAL_CHANGE → EXTRACT_CHANGED_REGIONS → GROUND_OBJECT → OPTICAL_SAR_ANALYSIS → CROSS_CHECK_EVIDENCE → VERIFY → SUMMARIZE → FINALIZE` | identical plan |
| tool calls | **4** | **2** |
| replans | none | **`NEW_EVIDENCE`** (changed_fraction ≈ 0 → skip region/ground/SAR) + **`TOOL_FAILURE`** (no region on the unchanged scene) |
| early_stopped | `false` | `true` — completion_reason "no significant temporal change detected" |
| conclusion | "~25.3% of the scene changed, 6 changed region(s) isolated, 1 structure region(s) located, optical+SAR representation computed. Verification: SUPPORTED." | "1 step(s) failed. Verification: SUPPORTED." (no fabricated change) |
| key findings | change ≈ 25.3% (~0.41 ha); 6 changed regions; grounded structure box `[17,16,241,239]`; joint repr dim 768 (representation-level only); cross-check 1/1 grounded region inside a changed region | "No significant change: changed fraction ~0.00% (below the 1% threshold)"; "Grounding: no matching region … (returned explicitly, not fabricated)"; "Optical+SAR analysis was not performed — no distinct SAR input" |
| verification | SUPPORTED (6 per-step checks SUPPORTED) | SUPPORTED (aggregate of SUPPORTED, SUPPORTED, INSUFFICIENT_EVIDENCE) |
| confidence | **HIGH** — "All planned specialist steps completed; 3 evidence items; SUPPORTED; 6 grounded regions; cross-check all inside; optical+SAR representation-level only" | **MEDIUM** — "A required modality (SAR) was missing — optical+SAR was not performed" |
| models used | ChangeFormer, RemoteSAM, CROMA | ChangeFormer |
| total time | **92.99 s** (validate 0.03 · temporal 16.03 · regions 0.02 · grounding 62.33 · optical+SAR 14.16) | **16.83 s** (validate 0.02 · temporal 16.71 · regions 0.01) |

**Secondary demo (frozen — `secondary_grounding.json`):** query *"Where is the
largest ship?"* → `SINGLE_IMAGE_GROUNDING` (RemoteSAM), box
`[211, 427, 634, 512]` in an 800×800 image, foreground softmax 0.999 (**not** a
confidence), verification SUPPORTED (structural checks only), latency **65.33 s**
cold. Warning surfaced: "RemoteSAM upstream licence is NOT STATED — treat
grounding output as prototype-only."

**The CASE B path is genuinely data-driven:** the executor read
`changed_fraction ≈ 0.0000` from the real ChangeFormer output and pruned steps
s3–s5 via a structured `NEW_EVIDENCE` replan. There is no `if case=="B"` in the
code.

## 6. Architecture facts

```
USER MISSION (natural language + 1–4 rasters)
  → INTENT / PLANNER      RuleBasedPlanner (default) → typed AgentPlan (Pydantic)
                          optional: LLM → typed Intent → deterministic PlanSynthesizer  (SATQUERY_PLANNER=hybrid)
  → POLICY / SAFETY       12-check deterministic policy.validate_plan
                          + G16 plan-intent cross-check (LLM plans only)
  → SPECIALIST EXECUTION  bounded executor, MAX_STEPS = 8, one model resident at a time
                          tools: run_vqa · run_grounding · run_temporal_change ·
                          extract_changed_regions · run_semantic_change · run_optical_sar ·
                          cross_check_evidence · validate_geospatial_input · verify · summarize · finalize
  → OBSERVATION           each step result is inspected
  → ADAPTIVE DECISION     continue / structured-replan (NEW_EVIDENCE · TOOL_FAILURE ·
                          MISSING_INPUT · INSUFFICIENT_EVIDENCE · VERIFICATION_CONTRADICTION ·
                          TASK_COMPLETE) / early-stop
  → EVIDENCE              typed EvidenceItem list, provenance on every path
  → VERIFICATION          structural / deterministic checks → aggregate status
  → TRUST / CONFIDENCE    assess_confidence → category + reasons  (NOT a probability)
  → GEO-SPATIAL RESULT    spatial findings + EPSG:4326 GeoJSON + HTML report (POST /investigate/report)
```

- **Frozen model stack (ADR-021):** A VQA = TinyRS-2B / Qwen2-VL-2B fallback ·
  B Grounding = RemoteSAM (licence NOT STATED) · C Temporal = ChangeFormer ·
  C Semantic-change = ChangeFormer + RemoteCLIP **composed baseline
  (EXPERIMENTAL)** · D Optical+SAR = CROMA / DOFA fallback · E adaptation = LoRA
  on frozen CROMA (**prod default = frozen**) · Scene = RemoteCLIP.
- **Three planner architectures (G17 decision):** A pure deterministic
  (PRODUCTION DEFAULT) · B pure local LLM (REJECTED, G16) · C LLM-intent hybrid
  (OPTIONAL).
- **Package split:** `packages/{core,geospatial,agents,evidence,model_adapters}`
  (src layout) + `apps/{backend,frontend}` + `external/research/` (read-only,
  gitignored, never imported).
- **Endpoints:** `POST /analyze`, `POST /analyze/upload`, `POST /investigate`,
  `POST /investigate/report` (HTML, G18), `POST /change`, `POST /scene`,
  `GET /artifact`, `GET /health`, `GET /` (self-contained UI, no build step).
- **The deterministic router is the execution guard**, not replaced by any
  planner. Data flows forward only; a later stage never mutates an earlier
  stage's output.

## 7. G19 rule

No new factual claims without evidence in this document. If a judge answer or a
slide needs a fact not listed here, either find its evidence and add a row, or
do not say it.
