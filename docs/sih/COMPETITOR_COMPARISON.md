# SatQuery — Alternative Approaches Comparison

> A **capability-level** comparison, not a marketing attack. We only mark a cell
> "no" / "manual" where that is a structural property of the approach, not a
> guess about a specific product. Facts: `docs/G19_SIH_SOURCE_OF_TRUTH.md`.

## Approaches compared

- **A · Traditional GIS workflow** — QGIS/ArcGIS/ENVI + an analyst.
- **B · Generic multimodal LLM** — a general chatbot given a satellite image.
- **C · Single remote-sensing VLM** — one large RS-tuned vision-language model
  (GeoChat / TEOChat / SkyEyeGPT class).
- **D · Static specialist pipeline** — a fixed script that always calls the same
  models in the same order.
- **E · SatQuery** — this project.

## Capability matrix

| Dimension | A · GIS | B · Generic VLM | C · Single RS-VLM | D · Static pipeline | E · SatQuery |
|---|---|---|---|---|---|
| Natural-language mission | manual | yes | yes | no (fixed) | **yes** |
| Specialist routing / selection | analyst | none | single model | fixed order | **deterministic planner + policy** |
| Adapts to intermediate results | analyst | no | no | no | **bounded observe / replan** |
| Bi-temporal change as a first-class step | yes (manual) | no | varies | yes | **yes (typed step)** |
| Text-guided object grounding | plugin | weak | varies | yes | **yes (RemoteSAM)** |
| Optical + SAR joint representation | manual | no | rare | possible | **yes (CROMA); no semantic over-claim** |
| Geospatial-metadata validation (CRS/transform/co-reg) | analyst-enforced | no | no | varies | **enforced; rejects malformed input** |
| Evidence trail / provenance | project-dependent | no | no | varies | **typed evidence + provenance on every path** |
| Structural verification of outputs | analyst review | no | no | rare | **per-step structural checks + cross-check** |
| Failure handling | analyst | confident guess | confident guess | exception / silent | **listed failure, skipped downstream, dropped confidence, no fabrication** |
| Confidence semantics | analyst judgement | none / vibes | token probabilities | varies | **evidence-derived category + why (not a number)** |
| Local / offline on a laptop CPU | yes | no (cloud) | no (GPU) | maybe | **yes (verified)** |
| Expertise required of the user | high | low | low | low | **low** |

## How to read it

- **A (GIS)** has the geometry rigor and the specialist tools, but the workflow,
  the routing, the verification and the evidence assembly are all on the human.
  SatQuery keeps A's rigor and automates the rest from language.
- **B (generic VLM)** is easy to use but has no geospatial handling, no
  specialist models, no evidence trail, and answers confidently when it
  shouldn't.
- **C (single RS-VLM)** is the closest "AI" comparison. It's one model for every
  task (weaker per task), typically 7 B+ and GPU-bound, and often licence- or
  reproduction-constrained (see `docs/research/`). SatQuery uses several small
  CPU-runnable specialists behind an orchestrator instead.
- **D (static pipeline)** can chain the same specialists, but it can't decide
  *not* to run a step. SatQuery's CASE A vs CASE B contrast is exactly the
  difference: same mission, different execution because the observations
  differed.

## Honesty notes

- We do **not** claim GIS software "can't" do change detection or grounding — it
  can, manually. The difference is the language interface + automation +
  built-in verification.
- We do **not** claim a specific RS-VLM product lacks a feature it actually has.
  Column C describes the *structural* trade-off of the single-model approach.
- SatQuery's own limitations (sanity-scale eval, GPU unverified, RemoteSAM
  licence, withdrawn SAR claim) are in `README.md` and belong in the same
  conversation.
