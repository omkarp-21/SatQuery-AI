# Judge Q&A — Top 30

> Prepared answers. Every claim is from `docs/G19_SIH_SOURCE_OF_TRUTH.md` and
> `docs/sih/CLAIM_MATRIX.md`. Keep answers to 2–4 sentences live. Negative-result
> questions have their own doc: `docs/sih/JUDGE_QA_NEGATIVE_RESULTS.md`.

---

**1. What is the problem?**
Satellite imagery is abundant but answering a real question with it needs
specialist GIS tools, model knowledge, and manual chaining. SatQuery turns a
plain-English geospatial mission into a validated, verified multi-step
investigation over single-image, bi-temporal, and optical/SAR imagery.

**2. Why not just use GIS software (QGIS/ArcGIS/ENVI)?**
GIS software is a manual toolbox — the analyst decides every step and checks the
geometry by hand. SatQuery keeps the geometry rigor (CRS/transform/bounds
validation, co-registration checks) but drives the workflow from language and
adds automatic evidence and verification. It complements GIS; it doesn't replace
the GIS engine.

**3. Why not ChatGPT / Gemini with an image?**
A generic multimodal chatbot has no geospatial-metadata handling, no
co-registration check, no specialist change-detection or SAR model, and no
verifiable evidence trail — and it will answer confidently when it shouldn't.
SatQuery routes to purpose-built remote-sensing models and refuses or degrades
visibly when it can't support an answer.

**4. Why not one remote-sensing VLM (GeoChat, TEOChat, SkyEyeGPT)?**
Those are 7 B+ and GPU-bound, several have unclear licences or no working
inference recipe, and one model is weaker at each task than a specialist. Our
model audit (`docs/research/`) covers this. SatQuery orchestrates smaller
specialists that each run on CPU.

**5. Why multiple specialists instead of one model?**
Different questions need different capabilities — scene reading, object
grounding, bi-temporal change, optical+SAR. A specialist per capability is more
accurate and lets each run in a small, CPU-friendly footprint. The cost is
orchestration — which is exactly what SatQuery is.

**6. What is "agentic" here, concretely?**
The executor runs specialists one at a time, **inspects each result**, and picks
the next action from a closed set: continue, structured replan (6 named
reasons), or early-stop — bounded to ≤ 8 calls. CASE A runs 4 specialists; CASE
B sees no change, issues two structured replans, and stops early. That branch is
decided by the real change output, not hard-coded.

**7. Why is the planner deterministic?**
Because we measured the alternative. On 100 frozen missions the rule-based
planner scored plan-validity 0.886 / tool-selection 0.90 at < 0.01 s; the local
LLM planner scored 0.25 / 0.40 and echoed its prompt. The deterministic planner
is reliable, instant, and auditable.

**8. Why did the LLM planner fail?**
The local 2 B model, text-only on CPU, produced structurally-valid plans that
were semantically wrong — it copied the example in its prompt. ~25 % of outputs
were unparseable. We rejected it for production and kept an optional
*intent-only* hybrid where a deterministic synthesiser builds the plan.

**9. How do you prevent hallucination?**
Four layers: (a) the planner can't invent a tool — a 12-check policy rejects
illegal plans; (b) a failed specialist yields a listed failure and skipped
downstream steps, never a fabricated value; (c) every factual claim in a result
is traced to an observed step or evidence item, and a fixed list of
over-claiming phrases is blocked (`test_g18_claim_evidence.py`, 69/69);
(d) structural verification on every step. We say "constrained and verified",
not "hallucination-free".

**10. How do you validate GeoTIFFs?**
`validate_geotiff` checks CRS, affine transform, bounds, GSD, band count, and
NoData; `check_pair_compatibility` asserts two rasters share an identical grid
before any bi-temporal step. EXP-007: 15/15 malformed-pair classes rejected
before a model runs.

**11. How do you handle CRS mismatch?**
It's rejected with a typed error — `VALIDATION_FAILED` — and no inference runs.
Bi-temporal analysis requires co-registration onto an identical grid; we assert
it, we don't silently resample. The failure matrix covers missing CRS,
incompatible CRS, and shape mismatch (22/22).

**12. What happens when a model fails?**
The step is marked failed and listed in `failures[]`; steps that depended on it
are skipped; `warnings[]` is populated; the confidence category drops; the
investigation still returns a structured, partial result. No HTTP 500, no
fabricated output — verified across 22 pathological conditions.

**13. Why RemoteSAM for grounding?**
It was the best open text-guided segmentation model in our audit for
CPU-feasible RS grounding (acc@IoU0.5 0.84 on a DIOR-RSVG sample, n=25). Caveat
we always state: its **checkpoint licence is NOT STATED upstream**, so it's an
**optional** component — the rest of the system works without it.

**14. Why TinyRS for VQA?**
TinyRS-2B is an RS-instruction-tuned Qwen2-VL-2B; it scored balanced accuracy
0.87 on an RSVQA-LR sample (n=40, CPU) versus 0.70 for the generic Qwen2-VL-2B,
which is the fallback. Small enough to run on CPU.

**15. Why ChangeFormer for change detection?**
A well-established bi-temporal change model with a working checkpoint; we
reproduced change-IoU ≈ 0.83 on a bundled LEVIR-CD demo set (n=7 — a
reproduction number, not a benchmark). It's integrated into `/change` and the
agent's `TEMPORAL_CHANGE` step.

**16. Why CROMA for optical+SAR?**
In a three-arm bake-off on DFC2020, CROMA's joint representation gave a better
downstream probe than DOFA's late-concat fusion on the primary metric on **both**
splits. It's a native joint radar-optical cross-encoder, MIT-licensed, runs on
CPU.

**17. What does SAR actually contribute?**
At the representation level, a joint optical+SAR embedding that the flagship
computes. At the *task* level — on DFC2020 land-cover with a frozen encoder +
linear probe — **we did not measure a benefit**; the first split's +0.067 was
within noise and reversed on a larger split, so we withdrew that claim. We don't
overstate the embedding.

**18. What is your evidence?**
Per result: a typed `EvidenceItem` list (change-mask, grounding box/mask,
ranking, joint representation), structural `VerificationResult`, `provenance`
(model+version, checkpoint hash, input digest, device, timestamp), a confidence
category with reasons, and an EPSG:4326 GeoJSON of spatial findings — all in the
one-click HTML report.

**19. What are your limitations?**
Sanity-scale evaluation (no significance established); GPU/4 GB fit UNVERIFIED
(CPU-only host); RemoteSAM licence NOT STATED (optional component); the
SAR-benefit claim was withdrawn; the pure LLM planner is rejected; semantic
*description* of change is an experimental composed baseline, not a learned VLM;
confidence is a category, never a number. All listed in `README.md` and
`PROJECT_STATUS.md`.

**20. Can it run locally?**
Yes — entirely. FastAPI backend + a self-contained UI (no build step), each
specialist in its own venv, checkpoints on disk. No internet at run time.

**21. Does it fit 4 GB VRAM?**
Unverified — no CUDA machine on hand, so we make no VRAM claim. CPU-only is the
verified, demoed path; one model resident at a time.

**22. How fast is it?**
The deterministic planner plans in < 0.01 s. A cold 4-specialist flagship
investigation is ~93 s, of which ~90 % is loading checkpoints from disk; CASE B
(no change) is ~17 s; the secondary grounding demo is ~65 s cold, seconds warm.
On a GPU or a warm system the same runs are seconds.

**23. Is it real-time?**
No, and we don't claim it. It's a laptop CPU prototype; latency isn't optimised
against a real-time budget.

**24. What happens without a GPU?**
That *is* the shipped configuration. Everything runs on CPU; the only cost is
cold-start model loading.

**25. What is novel?**
Not the individual models — the **system composition**: a natural-language
geospatial mission → deterministic planning → policy → bounded observe/replan
execution over specialists → geospatial validation → evidence → structural
verification → failure-aware, resource-aware local deployment. Details in
`docs/sih/NOVELTY_ARGUMENT.md`.

**26. What is research vs product?**
Product: the unified `/analyze` + `/investigate` pipeline, the agent runtime, the
frozen specialist stack, geospatial validation, evidence/verification, the UI and
report. Research: the model audit, the D/E optical-SAR experiments, the LoRA
adaptation probe, the planner-architecture evaluation. The three-numbers rule
(paper / our reproduction / integrated result) keeps them separate.

**27. How is confidence determined?**
`trust.py` applies documented deterministic rules to the specialists' structured
results and the verification aggregate, producing a **category**
(HIGH/MEDIUM/LOW/INSUFFICIENT_EVIDENCE) plus a "why" list. Hard rules (e.g.
contradiction, primary specialist failed, no evidence) force INSUFFICIENT.
Validated against 30 frozen cases across 7 scenario families. It is **not** a
probability and the internal score is never surfaced.

**28. Is it fully autonomous?**
No. The deterministic system is the execution guard; the LLM never controls
execution. We call it **bounded agentic execution** — policy-constrained,
evidence-backed orchestration.

**29. What happens if evidence conflicts?**
Verification can return CONTRADICTED, which triggers a
`VERIFICATION_CONTRADICTION` replan or withholds the answer, and the confidence
hard-rule forces INSUFFICIENT_EVIDENCE. The cross-check step
(`cross_check_evidence`) explicitly tests whether, e.g., a grounded region lies
inside a changed region and reports the ratio.

**30. How would you scale this commercially / for government?**
The architecture already isolates each specialist behind an adapter and runs
resource-bounded, so the near-term path is: larger evaluation datasets, a GPU
deployment profile, a stronger intent model, broader modality coverage, and
domain-specific specialist sets (disaster response, infrastructure monitoring,
agriculture). Roadmap: `docs/sih/PRODUCT_ROADMAP.md`. We don't claim operational
readiness beyond a prototype.
