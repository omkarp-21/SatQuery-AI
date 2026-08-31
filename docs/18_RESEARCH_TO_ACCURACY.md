# SATQUERY — Research to Accuracy Strategy

> Status: **Active — binding** · Owner: _TBD_ · Last updated: 2026-08-31
> This is the most important process document in the repo. Read it before any work
> that involves a model, a metric, or an accuracy claim.

## Mission

SatQuery is not merely a software demo and not merely a research exercise.

We are building a **research-backed, working prototype** whose accuracy,
reliability, multimodal reasoning, and geospatial correctness improve through
**controlled experimentation.**

The final system must simultaneously demonstrate:

1. Working prototype
2. Strong task performance
3. Research-backed model choices
4. Measurable accuracy improvements
5. Reliable multimodal / temporal reasoning
6. Explainable evidence
7. Feasible engineering
8. Strong SIH presentation

---

## Core development loop

Every major capability follows this loop:

```
RESEARCH
   ↓
BASELINE            ← never skip this
   ↓
MEASURE
   ↓
IDENTIFY FAILURE
   ↓
HYPOTHESIS
   ↓
EXPERIMENT          ← registered in 19_EXPERIMENT_REGISTRY.md
   ↓
MEASURE AGAIN
   ↓
INTEGRATE
   ↓
REGRESSION TEST
   ↓
DEMO
```

- **Never skip the baseline.**
- **Never claim improvement without measurement.**

---

## The three numbers — never mix them

For any model, there are **three separate numbers**. They live in different
columns, are labelled differently, and are never conflated:

| # | Name | Meaning | Where it is allowed to appear |
|---|------|---------|------------------------------|
| 1 | **Paper result** | What the authors report, under *their* setup, data, and splits. | Quoted with a citation, always attributed: "GeoChat reports X on RSVQA (paper)". |
| 2 | **Our reproduction** | What *we* measure when we run their released code + checkpoint on *their* benchmark, our hardware. | Labelled "reproduction"; expected to differ from #1; the gap is itself a finding. |
| 3 | **SatQuery result** | What the *integrated system* achieves under *our* evaluation (`docs/11_EVALUATION_PLAN.md`, `evaluation/`). | The only number we may call "SatQuery's accuracy". |

Forbidden: *"The paper says model X achieves Y, therefore SatQuery achieves Y."*
This is the single fastest way to lose credibility with the jury. If we only have
#1, we say so explicitly and mark #2 and #3 as "not yet measured".

---

## Prototype + research balance

Prototype development and research are **parallel tracks** (see
[`17_ENGINEERING_STRATEGY.md`](17_ENGINEERING_STRATEGY.md)).

```
Prototype exposes failures  →  Research addresses those failures  →  Improved models return to the prototype
```

The two tracks must continuously exchange information.

---

## Priority order

When choosing what to build next:

1. Mandatory SIH requirement
2. Measurable impact on accuracy / reliability
3. Critical prototype functionality
4. High-value innovation
5. Performance / latency
6. UI polish
7. Nice-to-have features

Do not prioritize visual polish over core model correctness. Do not pursue
research that cannot improve SatQuery.

---

## Accuracy engineering

For **every** AI capability, establish and record:

- baseline model
- dataset
- metric (precise definition)
- evaluation split (+ leakage check)
- hardware
- preprocessing
- inference configuration
- measured result (which of the three numbers it is)
- failure cases (concrete inputs)

Example shape:

```
BASELINE:   GeoChat pretrained (released checkpoint)
EXPERIMENT: remote-sensing adaptation / prompt strategy / fusion
COMPARE:    VQA accuracy, grounding acc@0.5, on our held-out split
DOCUMENT:   Before → After, with n, seed, hardware
```

**Never write invented metrics. Never turn a target into an achieved result.**

---

## Model selection principle

Do **not** choose a model because it is famous.

Choose on the **accuracy-to-engineering-cost ratio for SatQuery**, weighing:

```
accuracy + generalization + input compatibility + output quality
        + latency + GPU requirements + integration complexity
        + license + reproducibility
```

The best model is the one that gives the best accuracy-to-engineering-cost ratio
for *our* problem, on *our* data.

---

## Research repositories as specialist engines

External repos (`external/research/`) are treated as **specialist engines**, not
code to rewrite.

```
Research repo → Model adapter → Standard SatQuery interface → Planner / verifier / evidence engine
```

Do not rewrite academic code unnecessarily. Build adapters
(`packages/model_adapters/`, see the `model-integration` skill). Keep the research
repos read-only and isolated (`docs/research/`).

---

## Research hypotheses

We explicitly test hypotheses. Each **must** have a registered experiment
(`19_EXPERIMENT_REGISTRY.md`).

| ID | Hypothesis | Experiment |
|----|-----------|------------|
| **H1** | Remote-sensing-adapted VLMs outperform generic VLMs on RS tasks. | EXP-001 |
| **H2** | Task-specific specialist routing improves reliability over a single monolithic VLM. | EXP-006 (informed by EXP-003) |
| **H3** | Optical + SAR evidence improves reliability for suitable queries vs optical-only reasoning. | EXP-004 |
| **H4** | A verification layer can detect unsupported or contradictory model outputs. | EXP-005 |
| **H5** | Geospatial validation reduces invalid paired-image execution and spatial-reasoning failures. | EXP-007 |

Selection bake-offs (no hypothesis): EXP-002 (single-image RS-VLM comparison),
EXP-003 (temporal stack comparison). Full set of seven: `chatgpt.context.md` §11.

---

## Failure-driven development

When a model fails, **do not immediately replace it.** First **classify** the
failure:

- perception failure
- modality failure (e.g. SAR handled as RGB)
- temporal reasoning failure
- grounding failure
- geospatial failure
- query interpretation failure
- hallucination
- confidence calibration failure
- routing failure
- preprocessing failure

Then decide the *correct* remedy:

- better preprocessing
- a different specialist
- fine-tuning
- prompt adaptation
- fusion
- a verifier
- a routing change
- a fallback model
- dataset augmentation

Record the classification and remedy in the experiment entry.

---

## Novelty rule

Novelty comes from **what SatQuery contributes**, not from which models it calls.

Using GeoChat / ChangeChat / Change-Agent / ChangeFormer / RemoteCLIP / LangGraph
is **not** our novelty.

Our contribution may come from:

- multimodal task orchestration
- evidence-aware model selection
- cross-model verification
- a geospatial integrity layer
- confidence fusion
- a provenance / audit framework
- intelligent fallback / rerouting
- **measurable** reliability improvements

Any novelty claim must be supported by literature review **and** experimentation.

---

## Demonstration rule

The prototype must visibly prove the research.

- **Bad demo:** "Here is our dashboard."
- **Good demo:** query → planner → specialist selection → model execution →
  evidence → verification → result → trace.

Show **measured outputs**, not claims, wherever possible.

---

## SIH strategy (see also `docs/16_SIH_JUDGING_STRATEGY.md`)

The submission must communicate:

```
PROBLEM → EXISTING LIMITATIONS → RESEARCH GAP → SATQUERY CONTRIBUTION
        → TECHNICAL IMPLEMENTATION → EXPERIMENTAL VALIDATION → IMPACT
```

The deck must never describe functionality the prototype cannot credibly
demonstrate. Conversely, useful prototype capabilities should be backed by
research evidence wherever possible.

---

## Definition of Research Complete

A research item is complete only when: source identified · method understood ·
implementation tested · baseline measured · limitation documented · experiment
conducted where relevant · decision recorded · citation recorded.

## Definition of Feature Complete

Implemented · tested · integrated · observable in UI/API · error handling ·
logging · evaluation case exists · documentation updated.

---

## Golden principle

> **Do not build features for the sake of features.**
>
> research-backed capability → measurable improvement → integrated functionality
> → demonstrable value.
