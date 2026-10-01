# G18 Part 5 — Multi-step latency profile

> Measure before optimizing. This profiles the **INVESTIGATION workflow** end to
> end, not individual models. Individual-model latency is not touched — the
> bottleneck is cold model *loading*, not inference, and it cannot be safely
> removed inside the 4 GB single-model-resident constraint.

## Measured breakdown — flagship investigation, real models, CPU, cold

Source: `docs/sih/evidence/demos/g17_hybrid_flagship_caseA.json` (9-step plan,
4 specialists). `timings` block + `execution_trace` deltas.

| phase | time | note |
|-------|-----:|------|
| planning (**hybrid** path) | **~127 s** | LLM intent extraction: model load (~90 s) + generate (~35 s). Then it fell back to the rule intent anyway. |
| planning (**RuleBasedPlanner** = production default) | **~0.01 s** | no model — this is the shipped path |
| `validate_geospatial_input` | 0.04 s | one raster-meta read of 4 tiles |
| `run_temporal_change` (ChangeFormer) | 17.5 s | ~90 % cold model load |
| `extract_changed_regions` | 0.03 s | pure numpy (scipy connected components) |
| `run_grounding` (RemoteSAM) | **71.6 s** | ~90 % cold model load — the largest specialist cost |
| `run_optical_sar` (CROMA) | 13.5 s | ~90 % cold model load |
| `cross_check` / `verify` / `summarize` / `finalize` | ~0 s each | deterministic, in-process |
| serialization (`model_dump_json`) | < 0.1 s | large arrays trimmed in the capture script |
| **total (rule planner)** | **~103 s** | 4 real specialists, cold |
| **total (hybrid planner)** | **~230 s** | + the LLM-intent overhead |

DFC2020 feature-extraction reference (Part 2 run): CROMA 0.41 s/patch, DOFA
0.28 s/patch, CPU RSS 1.3 GB / 1.0 GB.

## What was looked for (Part 5 checklist)

| candidate waste | found? | action |
|-----------------|:------:|--------|
| unnecessary repeated model loading | **partly** | each specialist is a fresh subprocess (one model resident at a time — required by the 4 GB budget). The load cost is inherent; not a bug. |
| unnecessary tool calls | **no** | G17 exec `UNNECESSARY_TOOL_CALL_RATE = 0.00` (N=8); the executor prunes on observation (`NEW_EVIDENCE` skip, `MISSING_INPUT` skip) |
| duplicate validation | **no** | `_preflight_geo` reads raster meta once (~10 ms/tile); the `validate_geospatial_input` step reads it again but the whole step is 0.04 s. Not worth a cache. |
| duplicate image decoding | inherent | each specialist subprocess decodes its own input; a shared decode cache would need shared memory the 4 GB budget forbids |
| duplicate artifact creation | **no** | one per-request sandbox dir; masks copied once |
| infinite loops | **no** | bounded executor, `MAX_STEPS = 8`, `MAX_STEP_VIOLATION_RATE = 0.00` |

## Applied optimizations (safe, measured-justified)

1. **`LlmIntentExtractor` default timeout 120 s → 90 s.** An intent classification
   that cannot answer in 90 s is unusable interactively; the caller falls back to
   the deterministic keyword extractor. This caps the *hybrid* path's
   planning-latency tail. The production (rule) path is unaffected (0.01 s).
2. The executor already **releases each specialist subprocess before the next**
   (`subprocess.run` blocks to completion) — verified, no change needed.

## Not done (deliberately)

- **No persistent specialist processes / model caching.** That would keep
  multiple models resident and could violate the 4 GB target. Not done without a
  measured VRAM budget (GPU FIT = **UNVERIFIED**).
- **No per-request raster-meta cache.** The redundant reads total ~40 ms; below
  the threshold where optimization is warranted.
- **No individual-model optimization.** The models are frozen (ADR-021) and the
  cost is loading, not inference.

## Takeaway

The **production path (RuleBasedPlanner) plans in ~0.01 s**; a cold 4-specialist
investigation is **~100 s**, ~90 % of which is model loading that cannot be
safely removed at 4 GB. On a warm system (models already loaded once) or a GPU
host, the same investigation would be seconds of inference. The **hybrid** path
adds ~90–130 s of one-time LLM-intent overhead and is an opt-in enhancement, not
the default.
