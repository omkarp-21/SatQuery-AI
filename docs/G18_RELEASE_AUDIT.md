# G18 — Release Audit

> Final engineering audit of SatQuery AI (SIH 2026, PS 26167) before SIH
> presentation prep. Every row is one of: **DONE** · **RELEASE-READY** ·
> **NEEDS-FIX** · **KNOWN-LIMITATION** · **BLOCKED**. No functionality is
> duplicated; G18 only validates, hardens, and packages what G10–G17 built.

Audited: G10–G17 reports, `PROJECT_STATUS.md`, `README.md`, `API_CONTRACT.md`,
`docs/DECISIONS.md` (ADR-021), `packages/model_adapters/model_registry.yaml`,
`docs/research/EVIDENCE_LEDGER.md`, `evaluation/agent/reports/*`,
`evaluation/reports/*`, `docs/sih/evidence/*`.

## Production architecture (official, unless new evidence overturns it)

```
USER MISSION
  -> DETERMINISTIC INTENT / PLANNER   (RuleBasedPlanner = default; G17 decision)
  -> POLICY / SAFETY                   (12-check policy + G16 plan-intent cross-check)
  -> SPECIALIST EXECUTION              (bounded, <= 8 tool calls, one model resident at a time)
  -> OBSERVATION
  -> ADAPTIVE RULE / POLICY DECISION   (continue / structured-replan / early-stop)
  -> EVIDENCE + VERIFICATION
  -> TRUST / CONFIDENCE CATEGORY       (HIGH/MEDIUM/LOW/INSUFFICIENT_EVIDENCE; NOT a probability)
  -> GEO-SPATIAL RESULT               (spatial findings + EPSG:4326 GeoJSON)

optional:  LLM INTENT EXTRACTION -> typed Intent -> deterministic PlanSynthesizer
           (SATQUERY_PLANNER=hybrid; if it fails, deterministic interpretation continues)
```

## Core product

| item | status | note |
|------|--------|------|
| `POST /analyze` + `/analyze/upload` + `GET /` UI + `NormalizedResponse` | **RELEASE-READY** | G13; one flat schema for all 6 specialist paths; vanilla-JS UI, no build |
| `POST /investigate` — agentic investigation | **RELEASE-READY** | G14→G17; plan → policy → observe/replan executor → evidence-first report + trust category |
| Deterministic router (6 rules, registry-driven, no LLM) | **RELEASE-READY** | the execution guard; `ROUTING_SPEC.md` |
| Failure-aware resolution (`derive_resolution`, 6 qualifiers) | **RELEASE-READY** | + G16 `PLANNER_UNAVAILABLE` / `PLAN_REJECTED` / `PLAN_INTENT_MISMATCH` |
| Provenance on every code path | **RELEASE-READY** | model+version, input digest, device, timestamp; scrubbed of secrets |
| No confidence *number* anywhere; category only | **RELEASE-READY** | G17 trust layer is a documented deterministic rule set, explicitly not calibrated |

## Agent / planner

| item | status | note |
|------|--------|------|
| **Architecture A — RuleBasedPlanner** = production default | **RELEASE-READY** | G17: PLAN_VALIDITY 0.886 / TOOL_SELECTION 0.90 / <0.01 s on 100 frozen missions |
| **Architecture B — pure local LLM planner** | **KNOWN-LIMITATION (rejected)** | G16: semantic plan validity 0.25, example-echo; exec factual-consistency 0.33. Opt-in `SATQUERY_PLANNER=llm`, behind repair + cross-check + fallback. **Not** the default. Finding preserved. |
| **Architecture C — hybrid (LLM intent + deterministic synthesis)** | **RELEASE-READY (optional)** | G17: INTENT_TASK_ACCURACY 0.317; ties A only on the INVESTIGATION family. `SATQUERY_PLANNER=hybrid`. Enhancement, not default. |
| 12-check policy layer + G16 plan-intent cross-check | **RELEASE-READY** | no forbidden/illegal tool reached execution in any G15/G16/G17 run (plan **and** exec) |
| Bounded executor (≤ 8 calls, no recursion), structured replanning (6 reasons), explicit early-stop | **RELEASE-READY** | G15/G16; exec MAX_STEP_VIOLATION 0.00 |
| Visible deterministic fallback (never silent) | **RELEASE-READY** | `AGENT FALLBACK` warning + `resolution.qualifier` + blocking-check names in the trace |
| Trust / confidence category + claim-level evidence | **RELEASE-READY** | `trust.py`; `docs/G17_TRUST_LAYER.md`; validated against a frozen 30-case set (G18 Part 7) |

## Specialists (frozen stack — ADR-021)

| capability | model | status | measured |
|-----------|-------|--------|----------|
| A · VQA | TinyRS-2B (primary), Qwen2-VL-2B (fallback) | **RELEASE-READY** | bal-acc 0.87, RSVQA-LR n=40 (sanity-scale). CPU ~27 s cold. |
| B · Grounding | RemoteSAM | **RELEASE-READY** + **KNOWN-LIMITATION (licence)** | acc@IoU0.5 0.84, DIOR-RSVG n=25. CPU ~29 s cold. **LICENSE NOT STATED** — see Part 6. |
| C · Temporal change | ChangeFormer | **RELEASE-READY** | IoU 0.83, n=7 demo. CPU ~8 s. |
| C · Semantic change | ChangeFormer + RemoteCLIP composed baseline | **KNOWN-LIMITATION** | **EXPERIMENTAL** — not a learned temporal VLM; labelled as such everywhere. |
| D · Optical+SAR | CROMA (primary), DOFA (fallback) | **RELEASE-READY** | representation only, no textual claim. See Part 2 — **SAR does not improve downstream land-cover classification on the larger split**. |
| E · RS adaptation | LoRA on frozen CROMA | **KNOWN-LIMITATION** | prod default stays **frozen CROMA**; `--lora-weights` opt-in, plumbed + tested through `CromaAdapter` (42/42 layers). G18 larger split: LoRA +0.09 macro-F1 vs optical (direction replicates G12) but **no significance test**. See Part 3. |
| Scene / retrieval | RemoteCLIP | **RELEASE-READY** | zero-shot; CPU ~6 s. |

## Geospatial

| item | status | note |
|------|--------|------|
| CRS / transform / bounds / res / nodata preserved through every stage | **RELEASE-READY** | `packages/geospatial`; EXP-007 15/15 safeguard cases |
| Bi-temporal co-registration asserted before differencing | **RELEASE-READY** | misregistered pair → policy `7_geospatial` reject → visible fallback |
| Pixel→area only with pixel size + CRS units; GeoJSON EPSG:4326 (logged) | **RELEASE-READY** | |
| Ungeoreferenced demo tiles (identity transform) carve-out | **KNOWN-LIMITATION** | DFC2020 validation patches have georeferencing stripped; the G13 geo carve-out handles this and emits `geo_warnings` |

## Evaluation & evidence

| item | status | note |
|------|--------|------|
| Agent eval — 100 frozen missions, 3 arms, every metric with N | **DONE** | `evaluation/agent/reports/G17_HYBRID_EVALUATION.{md,json}` |
| The three-numbers rule (paper / reproduction / SatQuery) | **RELEASE-READY** | enforced in docs; only integrated-system numbers called "SatQuery result" |
| Larger DFC2020 D/E validation (986 patches, independent split) | **DONE** | Part 2 — G12 400/200 split **untouched**; result reported honestly (SAR benefit does not survive) |
| Claim-level evidence audit (≥ 30 claims) | **DONE** | Part 8 — `test_g18_claim_evidence.py` |
| Failure matrix (22 conditions) | **DONE** | Part 9 — `test_g18_failure_matrix.py`; no 500, no fabrication, structured resolution |
| Full regression | **DONE** | Part 10 — fast + slow + demos; exact counts recorded |

## Deployment

| item | status | note |
|------|--------|------|
| CPU path fully functional | **RELEASE-READY** | every specialist + the agent run CPU-only on the dev host |
| **4 GB GPU fit** | **KNOWN-LIMITATION** | `torch.cuda.is_available() == False` on the dev host → **GPU FIT = UNVERIFIED**. No numerical VRAM claim. Model sizes are within 4 GB on paper; not measured. |
| One model resident at a time (subprocess-per-specialist) | **RELEASE-READY** | the executor never holds two specialist models simultaneously; Part 5 |
| `models/checkpoints/**`, `data/raw|processed/**`, `.env` never committed | **RELEASE-READY** | `.gitignore` verified |

## Docs / reproducibility

| item | status |
|------|--------|
| `README.md` runnable; `QUICKSTART.md` 5-minute path | **DONE** (Part 14) |
| `docs/G18_RELEASE_MANIFEST.md` (commit, versions, checkpoints, split IDs, demo commands) | **DONE** (Part 15) |
| `docs/sih/CLAIM_MATRIX.md` (claim / evidence / N / allowed / forbidden wording) | **DONE** (Part 18) |
| `PROJECT_STATUS.md` GREEN/YELLOW/RED | **DONE** (Part 16) |

## NEEDS-FIX found and resolved in G18

| finding | fix |
|---------|-----|
| `exp004_run2_probe.py` / `exp008_adapt.py` crash writing the `.md` under a cp1252 console (`Δ`) | `encoding="utf-8"` on both `write_text` calls |
| the two scripts hard-coded `split_file` → a G18 larger-split run would mis-label its output as the G12 split | added `--tag` + `--split-file`; G18 outputs are `exp004_run2_g18_larger_*` / `exp008_g18_larger_*` |
| `run_g17_larger_de.sh` had `set -euo pipefail` so the probe `.md` crash aborted the LoRA step | scripts fixed; LoRA step re-run standalone |
| `croma_infer.py` `--lora-weights` expected `{name: (A,B,scaling)}` but `exp008_adapt.py` persists `{lora_r, lora_alpha, targets, state_dict:{f"{mod}.a", f"{mod}.b"}}` → an end-to-end LoRA load would fail "0 layers matched" | `croma_infer.py` now parses the real `exp008_adapt.py` format (groups `.a`/`.b` by module, `scaling = alpha/r`); verified through `CromaAdapter` — 42/42 layers, `test_croma_lora_adapter_loads_and_changes_representation` |

## BLOCKED

| item | why | mitigation |
|------|-----|-----------|
| GPU measurement of every specialist | no CUDA build / no GPU access on the dev host | documented as **UNVERIFIED**; CPU path is the shipped path; measurement is a follow-up when hardware is available |
| RemoteSAM checkpoint licence | upstream repo + HF card + paper are all silent | **LICENSE NOT STATED** kept; RemoteSAM is packaged as an **optional** component (Part 6); the rest of the product works without it (VQA can answer "where" questions with a caveat; grounding degrades to "not available") |
