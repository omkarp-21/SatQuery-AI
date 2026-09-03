# SatQuery AI — SIH Claim Matrix

> Every public claim, its evidence, its N, its status, and the **exact wording
> allowed / forbidden**. Use the allowed wording verbatim in the PPT and pitch.
> Nothing here is fabricated; every number cites a real run.

Status key: **MEASURED** (integrated-system number under our eval) ·
**REPRODUCED** (we ran the upstream code) · **IMPLEMENTED** (works, not
benchmarked) · **NEGATIVE** (measured, did not hold).

---

## 1 · Remote-sensing VQA

| | |
|---|---|
| **Evidence** | TinyRS-2B (primary) / Qwen2-VL-2B (fallback); balanced-accuracy **0.87** on an RSVQA-LR sample, **n = 40**, CPU, via the integrated adapter (`evaluation` reports). |
| **N** | 40 |
| **Status** | MEASURED (sanity-scale) |
| **Allowed** | "Measured prototype VQA capability (bal-acc 0.87, RSVQA-LR n=40, sanity-scale)." · "answers natural-language questions about a single scene." |
| **Forbidden** | "state-of-the-art VQA" · "human-level" · "benchmarked on RSVQA" (it is a 40-item sample, not the benchmark) |

## 2 · Text-guided object grounding

| | |
|---|---|
| **Evidence** | RemoteSAM; acc@IoU0.5 **0.84** (21/25), mean IoU 0.762, 0 no-box, on a DIOR-RSVG sample, **n = 25**, CPU. |
| **N** | 25 |
| **Status** | MEASURED (sanity-scale) · licence caveat |
| **Allowed** | "Measured prototype grounding (acc@IoU0.5 0.84, DIOR-RSVG n=25)." · "locates a described object and returns a box + mask." |
| **Forbidden** | "state-of-the-art segmentation" · any claim that omits the **checkpoint-licence-not-stated** caveat in a distribution context |

## 3 · Bi-temporal change detection

| | |
|---|---|
| **Evidence** | ChangeFormer V6 (LEVIR); IoU **0.83** on a demo pair set (**n = 7**); integrated `/change` + agent `TEMPORAL_CHANGE`. |
| **N** | 7 (demo) |
| **Status** | REPRODUCED + IMPLEMENTED |
| **Allowed** | "Integrated bi-temporal change detection (ChangeFormer, demo IoU ~0.83)." |
| **Forbidden** | "validated change-detection accuracy" (n=7 is a demo, not a validation set) |

## 4 · Semantic / language description of change

| | |
|---|---|
| **Evidence** | ChangeFormer mask → connected components → per-region RemoteCLIP tagging → rule-assembled description. **Not a learned temporal VLM.** |
| **N** | demo only |
| **Status** | IMPLEMENTED — **EXPERIMENTAL** |
| **Allowed** | "an experimental composed baseline that describes changed regions (mask + zero-shot tags), explicitly not a learned change-captioning model." |
| **Forbidden** | "change captioning" · "temporal VLM" · "understands what changed" |

## 5 · Optical + SAR joint representation

| | |
|---|---|
| **Evidence** | CROMA (primary) / DOFA (fallback); produces a joint GAP embedding. **Integrated, representation-level only** — no textual claim is derived from the embedding. |
| **N** | — |
| **Status** | IMPLEMENTED |
| **Allowed** | "computes a joint optical + SAR representation (CROMA); the system never asserts a semantic conclusion from the embedding." |
| **Forbidden** | "SAR confirms construction" · "fuses optical and SAR to detect X" · any sentence where SAR *concludes* something |

## 6 · Does adding SAR improve the downstream task?

| | |
|---|---|
| **Evidence (G12, frozen 400/200 split)** | CROMA joint macro-F1 **0.793** vs optical-only **0.726** (Δ **+0.067**), DFC2020 land-cover, **n_eval = 200**; bootstrap CI crossed 0, McNemar p ≈ 1.0 → **not significant**. |
| **Evidence (G18, larger independent 600/386 split)** | CROMA joint **0.8247** vs optical-only **0.8505** (Δ **−0.026**); CI [−0.080, +0.027], McNemar p = 1.0. DOFA fused **0.8177** vs DOFA optical **0.8374** (Δ −0.020). |
| **N** | 200 (G12) · 386 (G18) |
| **Status** | **NEGATIVE** — the SAR benefit **did not survive** the larger split; the sign of the point estimate flipped and it was never significant. |
| **Allowed** | "On DFC2020 land-cover classification with frozen encoders + a linear probe, adding SAR did **not** measurably improve the downstream task; the small positive delta on the first split was within noise and reversed on a larger independent split." |
| **Forbidden** | "SatQuery benefits from SAR" · "SAR fusion improves accuracy" · "CROMA joint outperforms optical" |

## 7 · Parameter-efficient adaptation (LoRA on frozen CROMA)

| | |
|---|---|
| **Evidence (G12, EXP-008, 400/200, 8 epochs)** | LoRA-adapted joint macro-F1 **0.704** vs frozen joint **0.643** (Δ **+0.061**); trainable params small; no deployment blocker. |
| **Evidence (G18, larger 600/386 split, 3 CPU epochs)** | `exp008_g18_larger_20260903T221800` — LoRA-adapted joint macro-F1 **0.6686** vs frozen fused **0.5422** (Δ **+0.126**) vs optical-only frozen **0.5772** (Δ **+0.091**); 811,008 trainable params, 3.24 MB fp32 delta, 42 layers, CPU RSS 1,733 MB. **No bootstrap CI / no paired test in this run**; the frozen arms are under-trained 3-epoch linear heads (not comparable to the Part 2 converged probe). `--lora-weights` tested through the real `CromaAdapter` (42/42 layers, provenance-tracked). |
| **N** | 200 (G12) · 386 (G18) |
| **Status** | IMPLEMENTED — LoRA lift replicates G12's direction but is **directional only** (no significance). **Production default stays FROZEN CROMA**; LoRA is `--lora-weights` opt-in. |
| **Allowed** | "LoRA adaptation of the frozen CROMA encoder is wired as an optional, provenance-tracked path (`--lora-weights`); on a larger split it lifted the probe macro-F1 directionally (+0.09 vs optical), consistent with the first split, but was not significance-tested. The production default is the frozen encoder." |
| **Forbidden** | "SatQuery uses an adapted CROMA" · "LoRA improves SatQuery" (not the default) · "LoRA significantly improves accuracy" (no test) |

## 8 · Agentic geospatial investigation

| | |
|---|---|
| **Evidence** | G14–G17: real-model multi-step execution — plan → 12-check policy → bounded observe/replan executor → evidence + verification. G17 100-mission eval: RuleBasedPlanner PLAN_VALIDITY **0.886** / TOOL_SELECTION **0.90**; exec (N=8) MISSION_COMPLETION / FACTUAL_CONSISTENCY / EVIDENCE / VERIFICATION all **1.00**, UNSUPPORTED_ACTION **0.00**; on multi-step missions the agent runs **2.25×** the baseline's specialists. |
| **N** | 100 (plan) · 8 (exec) |
| **Status** | MEASURED |
| **Allowed** | "bounded agentic geospatial investigation" · "decomposes a mission into validated specialist actions and adapts execution to intermediate observations" · "policy-constrained, evidence-backed orchestration." |
| **Forbidden** | "fully autonomous intelligence" · "the AI decides everything" · "autonomous agent" (the deterministic system is the execution guard) |

## 9 · The planner architecture decision

| | |
|---|---|
| **Evidence** | G16: pure local LLM planner (Qwen2-VL-2B) — semantic plan validity **0.25**, tool-selection **0.40**, example-echo, exec factual-consistency **0.33** → **rejected**. G17: hybrid (LLM intent + deterministic synthesis) — intent task-accuracy **0.317**, plan validity **0.591** < the deterministic **0.886** → **optional enhancement**, not default. |
| **N** | 15 (B) · 100 (A, C) |
| **Status** | MEASURED |
| **Allowed** | "the production planner is deterministic; a pure local LLM planner was built and **measured to be unreliable** (rejected); an LLM-intent hybrid is optional." · "the LLM never controls execution." |
| **Forbidden** | "LLM-powered planning" · "AI plans the investigation" (as a description of the default) |

## 10 · Trust / confidence

| | |
|---|---|
| **Evidence** | `trust.py` — an evidence-derived **category** (HIGH/MEDIUM/LOW/INSUFFICIENT_EVIDENCE) from documented deterministic rules; validated against 30 frozen cases (`test_g18_trust_cases.py`), 7 scenario families. |
| **N** | 30 |
| **Status** | IMPLEMENTED + rule-validated |
| **Allowed** | "an evidence-derived confidence **category** with an explicit 'why', computed by deterministic rules from the specialists' results and the verification aggregate." |
| **Forbidden** | "confidence score" · "calibrated confidence" · "X % confident" · any number |

## 11 · Geospatial correctness

| | |
|---|---|
| **Evidence** | EXP-007: **15/15** safeguard cases pass (CRS/transform/shape mismatch, missing CRS, invalid raster, decompression-bomb guard, path traversal, NoData). G18 failure matrix: **22/22** pathological inputs → structured resolution, no 500, no fabricated coordinates. |
| **N** | 15 + 22 |
| **Status** | MEASURED |
| **Allowed** | "preserves CRS, transform and bounds through every stage; rejects misregistered or malformed input with a typed error; never emits a fabricated coordinate." |
| **Forbidden** | "handles any imagery" (it rejects, by design) |

## 12 · Deployment

| | |
|---|---|
| **Evidence** | Every specialist + the agent run **CPU-only** on the dev host. `torch.cuda.is_available() == False` → GPU not measured. |
| **N** | — |
| **Status** | CPU **VERIFIED** · GPU **UNVERIFIED** |
| **Allowed** | "runs fully on CPU on a laptop; the 4 GB-GPU fit is **unverified** (no CUDA build on the dev host)." |
| **Forbidden** | "runs in 4 GB VRAM" · "real-time" (not measured) · any VRAM number |

---

## Global wording rules

- Never: "state-of-the-art", "fully autonomous", "hallucination-free", "real-time"
  (unmeasured), "calibrated confidence", "statistically significant" (unless a
  test established it — none has), "benchmark result" (our evals are sanity-scale).
- Always attribute: *paper result* vs *our reproduction* vs *SatQuery result* —
  only the third may be called "SatQuery's accuracy".
- Every accuracy number carries its **N** and its **significance caveat**.
