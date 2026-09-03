# SatQuery — Novelty Argument

> The novelty is **system composition**, not any single model. Each row: the
> common approach, what SatQuery does differently, and the evidence. Facts:
> `docs/G19_SIH_SOURCE_OF_TRUTH.md`.

> Framing rule: we do **not** claim we invented change detection, grounding, or
> optical-SAR encoders. We claim a specific, working *composition* of them under
> a natural-language mission interface with geospatial rigor and verification.

---

## 1. Natural-language geospatial mission

- **Existing approach:** either a GIS analyst hand-builds the workflow, or a
  generic VLM is prompted with an image and no geospatial handling.
- **SatQuery:** a plain-English *mission* is the unit of work; a deterministic
  planner decomposes it into typed steps and picks tools/order; the user names
  no tools and sets no parameters.
- **Evidence:** `POST /investigate`; 100 frozen missions; the frozen flagship
  (`docs/sih/evidence/demos/final/`).

## 2. Specialist orchestration (not one VLM)

- **Existing approach:** one large RS-VLM (7 B+, GPU-bound) tries to cover every
  task; or a fixed script calls tools in a hard-coded order.
- **SatQuery:** a frozen set of small specialists (ChangeFormer, RemoteSAM,
  CROMA/DOFA, TinyRS, RemoteCLIP), each behind a uniform adapter, selected by
  the planner and invoked through the registry — never called directly, never
  substituted silently.
- **Evidence:** `packages/model_adapters/model_registry.yaml`; the deterministic
  router (6 rules, registry-driven); ADR-021 frozen stack.

## 3. Bounded observe / replan execution

- **Existing approach:** open-ended agent loops (no step bound, no closed action
  set) or fully static pipelines (no adaptation at all).
- **SatQuery:** a bounded executor (MAX_STEPS = 8, no recursion) that inspects
  every intermediate result and chooses from a **closed 6-reason replan enum**
  (`NEW_EVIDENCE · TOOL_FAILURE · MISSING_INPUT · INSUFFICIENT_EVIDENCE ·
  VERIFICATION_CONTRADICTION · TASK_COMPLETE`) plus explicit early-stop.
- **Evidence:** CASE A (4 calls) vs CASE B (2 calls, 2 structured replans,
  early-stop) on the *same* mission; exec metrics MAX_STEP_VIOLATION 0.00,
  UNSUPPORTED_ACTION 0.00.

## 4. Geospatial validation in the loop

- **Existing approach:** VLM pipelines ignore CRS/transform; some GIS scripts
  assume co-registration.
- **SatQuery:** every raster carries its CRS/transform/bounds/res/nodata;
  bi-temporal steps assert an identical grid before differencing; malformed or
  misregistered input is rejected with a typed error before any model runs; no
  fabricated coordinate is ever emitted.
- **Evidence:** EXP-007 15/15; `test_g18_failure_matrix.py` 22/22.

## 5. Multimodal / temporal analysis as first-class steps

- **Existing approach:** change and SAR are separate offline tools; a chatbot
  can't do either.
- **SatQuery:** `TEMPORAL_CHANGE`, `EXTRACT_CHANGED_REGIONS`,
  `OPTICAL_SAR_ANALYSIS` are typed plan steps with typed outputs; the joint
  optical+SAR representation is computed but the system is **forbidden** from
  asserting a semantic conclusion from the embedding.
- **Evidence:** flagship CASE A key findings; CLAIM_MATRIX §5 (allowed/forbidden
  wording for SAR).

## 6. Evidence preservation

- **Existing approach:** an answer with no trail; provenance, if any, is ad-hoc.
- **SatQuery:** every stage attaches a `provenance` record (model+version,
  checkpoint hash, input digest, device, timestamp); every result carries a
  typed `EvidenceItem` list; data flows forward only (a later stage never
  mutates an earlier one's output).
- **Evidence:** `.claude/rules/architecture.md` (provenance threaded through
  every stage); the HTML report's audit block.

## 7. Structural verification

- **Existing approach:** trust the model output as-is.
- **SatQuery:** deterministic structural checks per step (box-in-bounds,
  mask-artefact-exists, geospatial-compatibility, modality-supported, …)
  aggregated into a `VerificationResult`; a `cross_check_evidence` step tests
  inter-model agreement (e.g. grounded region ∈ changed region).
- **Evidence:** EXP-005 structural verifier P/R/F1 = 1.00 (n=24 curated);
  flagship CASE A verification SUPPORTED with 6 per-step checks.

## 8. Failure-aware execution

- **Existing approach:** an exception, a 500, or a silent fallback.
- **SatQuery:** a closed set of resolution qualifiers; every fallback is
  surfaced (`AGENT FALLBACK` warning + `resolution.qualifier` + blocking-check
  names in the trace); a failed specialist → listed failure + skipped
  downstream + dropped confidence, never a fabricated value.
- **Evidence:** `docs/research/FAILURE_AWARE_ROUTING.md`;
  `test_g18_failure_matrix.py` 22/22; CASE B's `TOOL_FAILURE` replan.

## 9. Local / resource-aware deployment

- **Existing approach:** cloud API or a multi-GPU server.
- **SatQuery:** runs fully on a laptop CPU; one specialist model resident at a
  time (subprocess per specialist, released before the next); no internet at run
  time.
- **Evidence:** G18 Part 4; `docs/G18_RELEASE_MANIFEST.md` (CPU RSS + cold-load
  latencies); 383 fast tests on the CPU host.

---

## The one-paragraph novelty statement (for a slide / abstract)

> SatQuery's contribution is a **working composition**: a natural-language
> geospatial mission is decomposed by a deterministic planner, cleared by a
> 12-check policy layer, and executed by a bounded agent that observes each
> specialist's result and adapts within a closed action set — over a frozen
> stack of small, CPU-runnable remote-sensing models — with geospatial-metadata
> validation, evidence preservation, structural verification, an evidence-derived
> confidence category, and failure-aware resolution, deployable offline on a
> laptop. No individual model is claimed as novel; the reliable orchestration of
> them under these constraints is.
