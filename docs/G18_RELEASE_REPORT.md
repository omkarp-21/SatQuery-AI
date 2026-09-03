# G18 — Release Report

> Final engineering validation of SatQuery AI (SIH 2026, PS 26167). The goal was
> a **reliable release candidate**, not another research prototype. Companion
> docs: `G18_RELEASE_AUDIT.md` (DONE / RELEASE-READY / NEEDS-FIX / KNOWN-LIMITATION
> / BLOCKED), `G18_RELEASE_MANIFEST.md` (reproduce), `G18_LATENCY_PROFILE.md`,
> `docs/sih/CLAIM_MATRIX.md` (allowed / forbidden wording).

## Part 2 — Larger D/E experiment (optical + SAR)

Ran the **full DFC2020 `ROIs0000_validation` (986 patches)** on an **independent
600 train / 386 eval split** (`evaluation/datasets/dfc2020_g17_larger_split.json`).
**The G12 frozen 400/200 split and its numbers are NOT overwritten.**
Report: `evaluation/reports/exp004_run2_g18_larger_*.{json,md}`.

| arm | macro-F1 | accuracy | 95 % CI (bootstrap 2000×) |
|-----|:--------:|:--------:|:-------------------------:|
| CROMA optical-only | **0.8505** | 0.881 | [0.794, 0.896] |
| CROMA joint (optical + SAR) | **0.8247** | 0.881 | [0.757, 0.879] |
| DOFA optical-only | 0.8374 | 0.881 | [0.773, 0.890] |
| DOFA fused (S2 ⊕ S1) | 0.8177 | 0.878 | [0.749, 0.874] |

Per-class F1 is in the JSON (Water ≈ 0.96 everywhere; Shrubland is the weak
class, 0.57–0.76, and is where the arms diverge most).

**Does adding SAR improve the task?**

| comparison | Δ macro-F1 | 95 % CI | CI excludes 0 | McNemar p |
|------------|:----------:|:-------:|:-------------:|:---------:|
| CROMA joint − CROMA optical | **−0.0258** | [−0.0796, +0.0267] | no | 1.0 |
| DOFA fused − DOFA optical | **−0.0197** | [−0.0936, +0.0515] | no | 1.0 |

Runtime / memory: CROMA feature extraction 0.41 s/patch, CPU RSS 1.33 GB; DOFA
0.28 s/patch, 0.99 GB. Probe fit+predict 13.4 s. 0 non-finite feature values.
Failures: 0.

**Comparison with G12 (n = 200):** G12 measured CROMA joint **0.793** vs optical
**0.726** — a **+0.067** delta, already **not significant** (CI [−0.024, +0.153],
p = 0.45). On the larger independent split the point estimate **flipped sign** to
**−0.026** and is still not significant.

**Conclusion (honest, per the brief):** the SAR-improves-the-task result **did
not survive**. The G12 positive delta was within noise. On DFC2020 land-cover
classification with frozen CROMA/DOFA encoders + a linear probe, **adding SAR
provides no measurable downstream benefit** (and a small non-significant decrease
on more data). The **CLAIM_MATRIX §6 claim is withdrawn.** What remains true: the
joint optical+SAR *representation* is integrated and used in the flagship
investigation, and **CROMA ≥ DOFA on the primary metric on both splits** → CROMA
stays the capability-D primary.

## Part 3 — LoRA validation (larger split)

`--lora-weights` is now plumbed through the **actual** `CromaAdapter` +
`scripts/research/croma_infer.py`: the delta is applied as a merged weight update,
**fails loudly if 0 layers match** (never silently frozen), and `provenance`
records `encoder_mode` (`frozen` / `lora_adapted (N layers)`) + the adapter hash.
Tested at the adapter level.

Larger-split re-run (`exp008_adapt.py --tag g18_larger --epochs 3`, CPU, the same
independent 600/386 split; 3 epochs vs G12's 8 for the CPU time budget —
**directional**). Report: `evaluation/reports/exp008_g18_larger_20260903T221800.{json,md}`.
Head: one `nn.Linear`, AdamW, identical epochs across arms. LoRA r=8, α=16,
**42 attention Linear layers** wrapped, **811,008 trainable params**, 3.24 MB
fp32 delta. `torch.cuda.is_available() == False`; CPU RSS peak **1,733 MB**.

| arm | macro-F1 | accuracy | train s | infer s/patch |
|-----|:--------:|:--------:|:-------:|:-------------:|
| 1 · optical-only frozen | **0.5772** | 0.749 | 240 | 0.412 |
| 2 · CROMA fused frozen | **0.5422** | 0.785 | 244 | 0.404 |
| 3 · CROMA fused **LoRA** | **0.6686** | 0.819 | 2129 | 0.423 |

Deltas (macro-F1): LoRA − frozen fused **+0.1264**; LoRA − optical-only
**+0.0914**; frozen fused − optical-only **−0.0350**.

**Reading it honestly:** the LoRA lift over the *frozen fused* arm (+0.126)
replicates G12's direction (+0.061) and is larger here. **But** three confounds
keep this directional, not decisive: (a) only 3 CPU epochs; (b) **no bootstrap
CI / no paired test** in this script; (c) the frozen arms are 3-epoch AdamW
linear heads and are under-trained — the Part 2 fully-converged sklearn probe
scored ~0.85 on the same frozen features, so Part 2 and Part 3 absolute numbers
are **not comparable**; only the within-Part-3 arm deltas are. The frozen
fused − optical delta being **−0.035** is consistent with Part 2's finding that
SAR adds nothing to the *frozen* representation.

`--lora-weights` was tested end-to-end through the **actual `CromaAdapter`**
(`test_croma_lora_adapter_loads_and_changes_representation`, slow): the persisted
delta loads, matches **42/42** wrapped Linears (never "0 layers → silently
frozen"), measurably shifts the joint embedding (max component Δ ≈ 8.2), and
`provenance.encoder_mode` / `lora_weights_sha256` record it.

Adapter persisted at `models/checkpoints/exp008_croma_lora.pt` (3,271,915 bytes).

**Decision: the production default stays FROZEN CROMA.** Per the brief ("do not
automatically make LoRA default; only switch if the larger experiment supports
it"), a 3-epoch CPU run with no significance test and under-trained baselines is
not a sufficient basis to flip a production default — and the G18 D/E finding
(no SAR *task* benefit at all) removes the objective that adapting the joint
encoder would serve. LoRA remains an **opt-in** path (`--lora-weights`), fully
plumbed, provenance-tracked, and tested. Not a release blocker.

## Part 4 — Model deployment audit

`torch.cuda.is_available() == False` on the dev host (`torch 2.13.0+cpu`). **No
GPU measurement was taken and none is estimated.**

**GPU FIT = UNVERIFIED.**

CPU path — **VERIFIED WORKING** for every specialist and the agent:

| model | CPU cold-load + inference | CPU RSS (observed) | failure behaviour |
|-------|:------------------------:|:------------------:|-------------------|
| TinyRS-2B (VQA) | ~27 s | ~6 GB | missing weights → typed `run_vqa` failure → `NO_VQA_SPECIALIST` |
| RemoteSAM (grounding) | ~70 s | ~6–8 GB | no box → explicit "no region", never a fabricated box |
| ChangeFormer (temporal) | ~17 s | ~1.5 GB | corrupt raster → `VALIDATION_FAILED`, no 500 |
| CROMA (optical+SAR) | ~13 s | ~1.3 GB | no 2-band SAR → never called, `MISSING_INPUT` replan |
| DOFA (fallback) | ~0.28 s/patch | ~1.0 GB | — |
| RemoteCLIP (scene) | ~6 s | ~1.5 GB | — |
| Qwen2-VL-2B (rejected planner / hybrid intent) | ~35–100 s | ~3 GB (bf16) | any failure → deterministic fallback, visible |

One model resident at a time (subprocess per specialist, released before the
next). ~90 % of specialist latency is model *loading*, not inference — on a warm
system or a GPU the same investigation is seconds.

## Part 5 — Multi-step latency

See `docs/G18_LATENCY_PROFILE.md`. Production (RuleBasedPlanner) plans in
**~0.01 s**; a cold 4-specialist investigation is **~100 s**, ~90 % model load.
No redundant validation, no duplicate tool calls, no unnecessary work found (G17
`UNNECESSARY_TOOL_CALL_RATE = 0.00`, `MAX_STEP_VIOLATION_RATE = 0.00`). Applied:
`LlmIntentExtractor` default timeout 120 s → 90 s (caps the *hybrid* path tail;
production path unaffected). Not done (deliberately): persistent model caching
(would risk the 4 GB budget — GPU UNVERIFIED).

## Part 6 — RemoteSAM licence

Re-checked 2026-09-03: **no LICENSE file** in `github.com/1e12Leon/RemoteSAM`,
**no model card** on the HF checkpoint, and the ACM MM 2025 paper does not state a
weights licence. `model_registry.yaml` records this re-check and that an upstream
issue asking for clarification is the next step.

**Release note:** *"RemoteSAM checkpoint licensing requires upstream
clarification."* RemoteSAM is packaged as an **optional component**: the product
runs without it — grounding degrades to "grounding specialist not available"
(a typed, surfaced result), and every other capability (VQA, change, optical+SAR,
scene, the agent) is unaffected. RemoteSAM is **not** silently removed from the
docs; the caveat travels with it.

## Part 7 — Trust / confidence validation

30 frozen cases (`evaluation/agent/trust_cases.json`) across 7 families (strong /
partial / contradictory / missing evidence, failed specialist, invalid geometry,
ambiguous request). `test_g18_trust_cases.py` asserts the category matches the
written policy. **32/32 pass.** G18 added **conservative caps** (documented in
`docs/G17_TRUST_LAYER.md`): verification ≠ SUPPORTED → LOW; an INCOHERENT step →
LOW; a failed specialist → MEDIUM; < 2 specialists & no cross-check → MEDIUM;
ambiguity caps. Net effect: **HIGH is reached only by a multi-specialist,
SUPPORTED, unambiguous investigation** with no failed/withheld step. Single-step
and bare 2-image results cap at MEDIUM. The internal `score` is never surfaced;
the UI shows the category + a "why" list.

## Part 8 — Claim-level evidence

`test_g18_claim_evidence.py` audits **all 15 captured demo responses** (G13–G17)
— **> 30 individual `key_findings` / answer claims** — plus 5 constructed
synthesis scenarios. Every templated factual claim traces to a matching evidence
item **or** an observed step of the right task; **no forbidden phrasing**
("SAR confirms", "fully autonomous", "N % confident", …) appears; an optical+SAR
line is always "representation-level only"; an INCOHERENT step's claim is
withheld. **69/69 pass.**

## Part 9 — Failure matrix

`test_g18_failure_matrix.py` — **22 pathological conditions** (invalid / corrupt
GeoTIFF, missing / incompatible CRS, shape mismatch, missing 2nd image, missing
SAR, unsupported / ambiguous query, object absent, grounding / temporal / CROMA
failure, planner failure, LLM timeout, malformed LLM intent / plan, policy
rejection, evidence contradiction, insufficient evidence, artifact missing,
invalid GeoJSON). For every one: **no uncaught exception**, **no hallucinated
result**, **no fabricated coordinate**, **no fabricated confidence number**, **no
hidden fallback** (every fallback is in `warnings` + `resolution`), **no infinite
loop** (bounded executor), **structured resolution returned**. **22/22 pass.**

## Part 10 — Full regression

| suite | result |
|-------|--------|
| fast (`-m "not slow and not gpu and not integration"`) | **382 passed, 38 deselected, 0 failed** (249 pre-G18 + 132 G18 test files + 1 CROMA-LoRA plumbing contract test) |
| slow / model tests | marked `@pytest.mark.slow`; skip when a checkpoint/venv is absent. `test_repr_adapters.py` (incl. the new `test_croma_lora_adapter_loads_and_changes_representation`): **9 passed**. |
| investigation demos | `run_final_demo.py` — flagship CASE A + CASE B + secondary all OK (see Part 11/12); frozen under `docs/sih/evidence/demos/final/` |
| G13 model demo captures | unchanged (5/5 real) |

**0 regressions.** The final fast run was executed while the LoRA training still
held CPU, so its wall clock (≈ 4 h) is not representative — an isolated fast run
is ~13 min; every test passed either way.

## Part 11 — Flagship demo (frozen)

Mission (frozen): *"Investigate this area. Identify significant changes between
the two observations, locate the affected structures, compare optical and SAR
evidence, and provide a verified summary."* Production planner (RuleBasedPlanner).
Captured to `docs/sih/evidence/demos/final/`.

| | CASE A — significant change | CASE B — minimal / no change |
|---|---|---|
| planner | `rule_based` | `rule_based` |
| plan | `VALIDATE → TEMPORAL_CHANGE → EXTRACT_CHANGED_REGIONS → GROUND_OBJECT → OPTICAL_SAR_ANALYSIS → CROSS_CHECK → VERIFY → SUMMARIZE → FINALIZE` | identical |
| tool calls | **4** | **2** |
| replans | — | **`NEW_EVIDENCE`** (change ≈ 0 → skip region/ground/SAR) + `TOOL_FAILURE` (grounding found nothing on the unchanged scene) |
| early_stopped | False | **True** |
| conclusion | "~25.3 % of the scene changed, 6 changed region(s) isolated, 1 structure region(s) located, optical+SAR representation computed. Verification: SUPPORTED." | "1 step(s) failed. Verification: SUPPORTED." (no fabricated change) |
| verification / confidence | SUPPORTED / **HIGH** | SUPPORTED / **MEDIUM** (capped: a specialist step failed) |
| latency (cold) | **93 s** | **17 s** |

**The different execution paths emerge from the real ChangeFormer output** — CASE
B is not hard-coded; the executor observed `changed_fraction ≈ 0` and pruned.

## Part 12 — Secondary demo

*"Where is the largest ship?"* on `data/demo/grounding/scene.jpg` →
`SINGLE_IMAGE_GROUNDING` (RemoteSAM), box `[211, 427, 634, 512]`, verification
SUPPORTED, ~65 s cold (~5 s warm). `docs/sih/evidence/demos/final/secondary_grounding.json`.

## Part 13 — Report export

`POST /investigate/report` returns a **self-contained HTML** report (Mission ·
Understood as · Inputs · Plan & execution · Replans · Key findings · Spatial
findings · Evidence · Verification · Confidence category + why · Models used ·
Warnings · Execution time · raw provenance). CLI:
`scripts/demo/mission_report.py <investigation.json>`. Print-friendly, no external
assets, HTML-escaped. `test_g18_report_export.py` (9 tests).

## Part 14 — Run experience

`QUICKSTART.md` — clone → install → launch → demo in ~5 min, with the 10 required
sections. `README.md` gains a 10-point release table + a "Known limitations" box.

## Part 15 — Release manifest

`docs/G18_RELEASE_MANIFEST.md` — commit, Python 3.11.0, OS, every checkpoint id +
bytes + upstream commit, dataset + split ids, test counts, API endpoints,
hardware status, caveats, and copy-paste reproduce commands.

## Part 16 — Project status

`PROJECT_STATUS.md` now leads with a **GREEN / YELLOW / RED** table. All core
areas GREEN; YELLOW items: SAR task-benefit (negative), LoRA (frozen default),
pure LLM planner (rejected), hybrid planner (optional), semantic-change language
(experimental), 4 GB GPU (unverified), RemoteSAM licence (not stated). **No RED.**

---

## Part 17 — Release gate

| gate | status | basis |
|------|:------:|-------|
| CORE PRODUCT WORKS | ✅ | `/analyze` + `/investigate` + UI, 381 fast tests |
| AGENT WORKS | ✅ | G17 exec N=8: completion / factual / evidence / verification 1.00; UNSUPPORTED_ACTION 0.00 |
| SPECIALISTS WORK | ✅ | all 6 run CPU-only, real models, integrated + provenanced |
| GEO VALIDATION WORKS | ✅ | EXP-007 15/15 + failure matrix 22/22; no fabricated coordinate |
| EVIDENCE WORKS | ✅ | claim-level audit — every claim traces to an observation; 69/69 |
| TRUST LAYER WORKS | ✅ | 30 frozen cases / 7 families, rules validated; category only, never a number |
| DEMO WORKS | ✅ | frozen CASE A / CASE B + secondary captured with real models; paths emerge from observations |
| TESTS PASS | ✅ | **382 fast pass, 0 failed, 0 regressions**; slow adapter suite 9/9 |

**Blockers checked — none present:**

| block-for | present? |
|-----------|:--------:|
| data corruption | no — CRS/transform/bounds preserved; EXP-007 + failure matrix |
| false geospatial output | no — no fabricated coordinate in any of the 22 failure cases or the demos |
| hidden failures | no — every fallback is surfaced (`AGENT FALLBACK` warning + `resolution.qualifier`) |
| unsafe planner execution | no — 0 forbidden/illegal tool calls reached execution in any G15/G16/G17 run |
| reproducibility failure | no — `G18_RELEASE_MANIFEST.md` + `run_final_demo.py` reproduce the demo |
| unresolved critical dependency | no — RemoteSAM (licence) is **optional**; the product runs without it |

Non-blocking (Part 17 explicitly): the larger-split LoRA experiment is
CPU-bound / statistically inconclusive — **does not block release**.

### RELEASE CANDIDATE = **YES**

SatQuery AI is a reliable release candidate for SIH presentation preparation. The
core product, the agent, the specialists, geospatial validation, evidence,
verification, the trust layer, and the frozen demo all work and are tested; there
is no data-corruption, false-geo-output, hidden-failure, unsafe-planner, or
reproducibility blocker.

---

## Part 18 — Claim matrix

`docs/sih/CLAIM_MATRIX.md` — 12 claims with evidence, N, status, and **exact
allowed / forbidden wording**. Notable: the **"SAR improves the task" claim is
withdrawn**; "agentic investigation" is allowed as *"bounded agentic geospatial
investigation"* and forbidden as *"fully autonomous intelligence"*.

---

## Final answers

**1 · Is SatQuery demo-ready?** **Yes.** The frozen flagship (CASE A / CASE B) and
the secondary grounding demo run end-to-end with real models; CASE B's shorter
path is decided by the actual ChangeFormer output, not hard-coded; the UI shows
the plan, evidence, verification, and a confidence category with a "why". 93 s /
17 s / 65 s cold on a laptop CPU (seconds on a warm system).

**2 · Is SatQuery SIH-release-ready?** **Yes, as a release candidate** — with the
limitations kept visible: sanity-scale evaluation (no significance established),
GPU fit UNVERIFIED, RemoteSAM licence NOT STATED (optional component), the SAR
task-benefit withdrawn, the pure LLM planner rejected. None of these is a
correctness or safety blocker.

**3 · Single biggest remaining risk:** **on-stage latency on a cold machine.** A
first flagship run is ~90 s because every specialist model loads from disk. Fix:
warm the models once before the demo (run `scripts/demo/run_final_demo.py` on the
demo machine beforehand); then a live run is seconds. Secondary risk: judges
asking for the RemoteSAM licence — the honest answer is prepared (Part 6).

**4 · What should NOT be worked on anymore:**
- Searching for new specialist models, or trying to make Qwen2-VL-2B the planner.
- Redesigning the agent architecture (it is measured and works).
- Chasing statistical significance on the D/E experiment — it is inconclusive and
  that is the reported result.
- UI rewrites, export styling, new AI features, any feature that does not improve
  usefulness / reliability / explainability / demo impact / scientific evidence.

**5 · What must be done immediately before the final PPT / pitch:**
1. **Warm the demo machine** — run the frozen demo set once so the live run is fast.
2. Lock the pitch wording to `docs/sih/CLAIM_MATRIX.md` (allowed column only).
3. Have the RemoteSAM-licence answer and the "SAR benefit withdrawn" answer ready
   — both are strengths (they show measurement discipline), not weaknesses to hide.
4. Rehearse the CASE A → CASE B contrast: *"same mission, the system chose a
   shorter path because the data showed no change."* That is the demo.
5. Finish (or explicitly defer) the larger-split LoRA row — it is not a blocker.
