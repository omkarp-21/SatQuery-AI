# SATQUERY — Prototype Roadmap

> Status: **Active** · Owner: _TBD_ · Last updated: 2026-08-31
> Versions are capability milestones, not dates. `main` always runs the demo path
> of the **current** version. A version ships only when its exit criteria are met
> **and** its accuracy claims have measurements (see
> [`18_RESEARCH_TO_ACCURACY.md`](18_RESEARCH_TO_ACCURACY.md),
> [`19_EXPERIMENT_REGISTRY.md`](19_EXPERIMENT_REGISTRY.md)).

```
V0     Upload → validate → answer
  ↓
V0.5   Upload → routing → specialist → answer
  ↓
V1     routing + temporal + grounding + SAR/optical
  ↓
V1.5   evidence + verifier + confidence + provenance
  ↓
V2     benchmarking + optimization + polished UI + demo hardening
```

Each version keeps everything the previous one had (regression tests stay green).

---

## V0 — end-to-end skeleton

**Scope:** one image in, one text answer out. Ingestion → metadata → a single
hard-coded specialist → reports. Minimal UI: upload, ask, see answer + raw trace.

**Exit criteria**
- A real query runs end to end on `data/demo/` offline.
- Metadata stage extracts and carries CRS / transform / bounds / nodata.
- One model adapter (RemoteCLIP — lowest integration risk) loads a real checkpoint
  and returns a real output.
- Errors are typed; the UI shows loading / empty / error states.
- Feature-complete per doc 17 (tests, logging, eval case, docs).

**Research gate:** EXP-001 baseline **started** (generic-VLM number recorded as a
reproduction number). No accuracy claims yet beyond "it runs".

---

## V0.5 — routing to a specialist

**Scope:** add `routing` + `planning` + `registry` + `agents` + `specialists`.
The planner turns the NL query into a deterministic plan; routing picks the
specialist from registry capabilities. Two or more adapters wired (RemoteCLIP +
GeoChat).

**Exit criteria**
- Routing decision is rule-based over registry capabilities; LLM only disambiguates
  intent, validated against a schema (see `agent-orchestration` skill).
- Same query, same inputs → same plan (seeds fixed).
- Unsupported task/modality raises a typed error, surfaced in the trace.
- Plan is stored verbatim for provenance.

**Research gate:** EXP-001 **MEASURED** (H1) — RS-adapted vs generic VLM on our
held-out split, with the before/after in doc 19. Decision recorded. EXP-002
(single-image RS-VLM bake-off) and EXP-006 (LLM vs constrained routing, H2)
**started**.

---

## V1 — full modality coverage

**Scope:** all three modality paths working:
- single-image (VQA / grounding) via GeoChat,
- bi-temporal (change) via the chosen temporal specialist,
- optical–SAR queries with SAR handled as backscatter (dB), never RGB.
Grounding results and change masks appear on the map as inspectable layers
(`map-ui` skill).

**Exit criteria**
- `geospatial` stage: bi-temporal inputs asserted co-registered before differencing;
  reprojection logged; area computed in a projected CRS.
- SAR path rejects optical-only models and vice versa.
- Map shows model outputs as toggleable, traceable layers; SAR and optical visually
  distinct.
- Regression suite covers all three paths.

**Research gate:** EXP-002 (single-image bake-off), EXP-003 (temporal stack
bake-off), EXP-004 (H3, optical+SAR) and EXP-006 (H2, routing) **MEASURED**,
decisions recorded. EXP-007 (H5, geospatial gate) **started**.

---

## V1.5 — trust layer

**Scope:** `evidence` + `verification` + `confidence` + `provenance` fully wired.
Every answer decomposes into `EvidenceItem`s; the verifier cross-checks where it
can; confidence carries its qualifier; the audit record is persisted and
replayable. The UI's evidence panel and execution-trace panel are peers of the map.

**Exit criteria**
- No result path returns without a provenance record; no secrets in it.
- Verifier flags optical↔SAR disagreement rather than averaging it away.
- Confidence values are labelled (probability / margin / heuristic).
- Clicking an evidence item highlights its map geometry and its trace step.

**Research gate:** EXP-005 (H4, verifier detection) and EXP-007 (H5) **MEASURED**,
decisions recorded. Reliability numbers exist as **SatQuery results** (number #3),
clearly separated from paper and reproduction numbers.

---

## V2 — hardening

**Scope:** benchmarking suite, latency/throughput optimization, no-GPU degradation
path, UI polish, demo hardening.

**Exit criteria**
- `docs/13_PERFORMANCE.md` has real p50/p95 per stage group on stated hardware.
- No-GPU path returns a partial answer with lowered confidence and a note — never a
  silent fake.
- `scripts/demo/run_demo.sh` green in CI and on the demo machine; offline; backup
  recording exists.
- `hackathon-jury` pass completed; the three least-ready questions have answers.
- SIH deck maps every claim to a demonstrable capability + a measurement.

**Research gate:** the full evaluation suite (`make eval`) runs with seeds,
hardware, and commit recorded; `docs/11_EVALUATION_PLAN.md` states known
distribution gaps (e.g. untested on unseen ISRO sensors).

---

## Mapping to SIH problem 26167

| Requirement (fill from `docs/02_REQUIREMENTS.md`) | First delivered in |
|--------------------------------------------------|--------------------|
| Natural-language query over imagery | V0 |
| Single / bi-temporal / optical–SAR | V1 |
| Explainable evidence + trace | V1.5 |
| Reliability / verification | V1.5 |
| Performance + robustness | V2 |

_Keep this table in sync with `docs/02_REQUIREMENTS.md`._
