# ChatGPT Context — SatQuery AI / SIH 2026

> Purpose: This file is the persistent strategic memory and evaluation brain for the SatQuery AI project.
> It is designed to be read by Claude Code / Antigravity at the beginning of serious work and maintained throughout development.
>
> Core objective:
> **Win SIH 2026 Problem Statement 26167 (SatQuery AI), while producing a credible, measurable, technically strong prototype.**
>
> Status: **persistent project memory — not disposable documentation.** Keep it in sync with reality.
> Companion living docs: [`docs/PROJECT_STATUS.md`](docs/PROJECT_STATUS.md), [`docs/DECISIONS.md`](docs/DECISIONS.md),
> [`docs/17`–`docs/21`](docs/), [`docs/19_EXPERIMENT_REGISTRY.md`](docs/19_EXPERIMENT_REGISTRY.md).

---

# 0. PROJECT IDENTITY

Project:
**SatQuery AI — Interactive Vision-Language Assistant for Multimodal Remote Sensing Image Analysis Through Text Queries**

SIH: **2026**
Problem Statement: **26167**
Organization: **Indian Space Research Organisation (ISRO)**
Department: **Department of Space**
Category: **Software**
Theme: **Space Technology**

Primary official requirements must always remain the source of truth.

---

# 1. MASTER GOAL

The goal is NOT merely:

- make a chatbot;
- make a dashboard;
- glue together several GitHub repositories;
- produce a visually impressive demo;
- claim novelty without evidence.

The goal is:

> Build the strongest evidence-backed, technically credible, working solution to PS 26167 that is differentiated enough to stand out among hundreds of competing teams.

We optimize for:

**Problem Fit × Novelty × Technical Depth × Accuracy × Reliability × Feasibility × UX × Demonstrability × Impact**

Do not optimize one dimension at the expense of all others.

---

# 2. SIH EVALUATION MINDSET

Historical SIH idea-selection guidance has emphasized:

- novelty;
- complexity;
- clarity and detail;
- feasibility;
- practicability;
- sustainability;
- scale of impact;
- user experience;
- future work potential.

Our current 2026 internal PPT blueprint allocates:

- Problem Understanding: 20%
- Innovation & Novelty: 25%
- Technical Depth: 20%
- Feasibility & Impact: 35%

The blueprint also requires an exact six-slide submission and strongly favors quantified claims, explicit architecture, clear problem-to-feature mapping, and high-authority references.

Treat these as optimization constraints.

---

# 3. WHAT WINNING MEANS

A strong SatQuery proposal should make a reviewer think:

1. This team understands the actual remote-sensing problem.
2. They understand what existing RS-VLMs already do.
3. They identified a meaningful system-level gap.
4. Their architecture is technically coherent.
5. The difficult parts are feasible.
6. They have a working prototype, not only diagrams.
7. Their model choices are evidence-backed.
8. Their improvements are measured.
9. Their system is robust to failure and disagreement.
10. Their solution could plausibly be extended to real institutional workflows.

A polished UI alone is not enough.
A research paper collage alone is not enough.
A GitHub mashup alone is not enough.

---

# 4. OFFICIAL FUNCTIONAL REQUIREMENTS

SatQuery must support:

## Single image
- optical / multispectral image or SAR image;
- visual question answering;
- plus at least one additional task:
  - captioning / scene description OR
  - text-guided region grounding.

## Bi-temporal
- two corresponding observations acquired at different times;
- change understanding;
- change description and/or change-based VQA;
- optional spatial change map where masks/reference data exist.

## Cross-modal
- co-registered optical/multispectral + SAR;
- complementary information extraction;
- joint reasoning over the two observations.

## Agentic orchestration
The system must:
- interpret the query;
- inspect image count/modality/format/metadata;
- select suitable specialist models/tools;
- configure permitted parameters;
- execute the workflow;
- combine textual/spatial outputs;
- estimate confidence;
- return visual evidence;
- expose an auditable execution summary.

## Input formats
- GeoTIFF / TIFF for geospatial imagery;
- PNG/JPEG only where permitted by benchmark inputs.

## Adaptation
At least one visual / vision-language component must be fine-tuned or otherwise adapted using BigEarthNet.txt or another open-source training source.

---

# 5. CURRENT WORKING THESIS

Working thesis:

> Task-specific remote-sensing specialists coordinated by a geospatially aware planner and checked through evidence/verification can produce more reliable, auditable and useful answers than a single monolithic VLM.

This is a HYPOTHESIS until experiments support it.

Never present a hypothesis as an established fact.

---

# 6. OUR PROPOSED DIFFERENTIATION

Existing research models are building blocks, not our novelty.

Potential SatQuery contribution:

## A. Geospatial integrity layer
- native raster ingestion;
- CRS validation;
- band metadata;
- GSD/resolution where available;
- bounds;
- affine transform;
- NoData handling;
- pair compatibility checks;
- registration/alignment checks;
- explicit record of transformations.

## B. Agentic planner
- infer task;
- inspect input;
- determine eligible tools;
- generate a constrained execution plan;
- route to specialists;
- avoid arbitrary/random tool use.

## C. Evidence engine
Each important answer should be traceable to:
- input image(s);
- model/tool;
- region/mask;
- temporal relation;
- modality;
- relevant intermediate outputs.

## D. Verification layer
When feasible, verify important claims using independent evidence:
- temporal mask;
- spatial grounding;
- optical evidence;
- SAR evidence;
- metadata consistency;
- cross-model agreement.

## E. Confidence / uncertainty
Do not invent confidence numbers.
Confidence must have an explicitly defined source or calibration method.

Model disagreement should be treated as useful information:
- agreement -> stronger support;
- partial agreement -> caution;
- disagreement -> lower confidence / re-route / ask for confirmation.

## F. Audit / provenance
For every execution, preserve:
- query;
- input IDs;
- metadata summary;
- selected task;
- selected models;
- key parameters;
- timestamps;
- latency;
- outputs/artifacts;
- verification status;
- confidence method;
- final answer.

---

# 7. IMPORTANT ENGINEERING PRINCIPLE

Do not build every component from scratch.

Use proven open-source research implementations where useful.

The preferred pattern is:

```
Research repository
    ->
isolated environment/service
    ->
SatQuery adapter
    ->
standard internal interface
    ->
planner / verifier / evidence engine
```

Research repositories should remain isolated and should not become our application architecture.

---

# 8. CURRENT RESEARCH COMPONENT CANDIDATES

Initial candidate pool:

- GeoChat -> single-image RS-VLM / grounding / VQA-related capabilities
- Change-Agent -> bi-temporal change interpretation
- ChangeChat -> conversational change analysis
- ChangeFormer -> pixel-level change detection baseline
- RemoteCLIP -> RS-specific vision-language representation / auxiliary component
- BigEarthNet.txt -> adaptation/training resource
- VRSBench -> single-image evaluation
- RSVQA -> VQA evaluation
- CDVQA -> change-based VQA evaluation

Important:
These are candidates, NOT automatically final dependencies.

Every candidate must be evaluated on:
- task coverage;
- accuracy;
- input compatibility;
- output quality;
- latency;
- GPU/RAM requirements;
- dependency complexity;
- reproducibility;
- license;
- integration cost;
- usefulness for the final demo.

Keep the best capability-to-engineering-cost ratio.

---

# 9. MODEL STRATEGY

Use the smallest / simplest model that meets quality requirements.

Do not choose a model because:
- it is famous;
- the paper is impressive;
- it is the newest;
- it has the largest parameter count.

Choose based on evidence.

Each model candidate gets a record containing:

- model name;
- repository;
- paper;
- license;
- checkpoint source;
- supported tasks;
- supported modalities;
- input format;
- output format;
- expected hardware;
- environment requirements;
- benchmark results;
- our reproduced results;
- strengths;
- weaknesses;
- integration effort;
- final decision.

---

# 10. RESEARCH -> ACCURACY LOOP

This is one of the highest-priority operating principles.

Every meaningful AI feature should follow:

```
RESEARCH
    ->
BASELINE
    ->
MEASURE
    ->
FAILURE ANALYSIS
    ->
HYPOTHESIS
    ->
EXPERIMENT
    ->
MEASURE AGAIN
    ->
INTEGRATE
    ->
REGRESSION TEST
    ->
DEMO
```

Do not skip the baseline.

Do not claim an improvement without measuring it.

Do not use paper-reported numbers as if they were our numbers.

Distinguish:

- Paper result
- Our reproduction
- Our SatQuery integrated result

---

# 11. INITIAL EXPERIMENTS

## EXP-001
Generic VLM vs remote-sensing-adapted VLM on relevant single-image tasks.

Question:
Does remote-sensing adaptation improve the actual task?

## EXP-002
Compare candidate single-image RS-VLMs.

Question:
Which candidate gives the best accuracy / latency / integration trade-off?

## EXP-003
Change-Agent vs ChangeChat vs ChangeFormer-based pipeline.

Question:
Which temporal stack gives the best combination of:
- change mask quality;
- semantic change interpretation;
- speed;
- integration stability?

## EXP-004
Optical-only vs optical + SAR.

Question:
For suitable tasks, does multimodal evidence improve the result?

## EXP-005
Unverified model answer vs verified answer.

Question:
Can the verifier detect unsupported/contradictory outputs?

## EXP-006
LLM-only routing vs constrained deterministic/agentic routing.

Question:
Does the structured router improve correct tool selection and reduce invalid execution?

## EXP-007
Geospatial validation ON vs OFF.

Question:
Does metadata/compatibility validation measurably reduce invalid analyses?

Experiments may be replaced or expanded as evidence develops.
The living registry is [`docs/19_EXPERIMENT_REGISTRY.md`](docs/19_EXPERIMENT_REGISTRY.md).

---

# 12. PROTOTYPE STRATEGY

Research and prototype development are PARALLEL tracks.

Prototype gives us:
- working end-to-end flow;
- real failure cases;
- UI proof;
- demo proof;
- integration feedback.

Research gives us:
- model choice;
- accuracy improvements;
- failure analysis;
- evidence for novelty;
- benchmark credibility.

The loop is:

```
Prototype
  ->
find failure
  ->
research
  ->
experiment
  ->
improve
  ->
integrate
  ->
prototype improves
```

Never allow the project to become:
- 100% research with no usable system;
- OR 100% demo polish with weak intelligence.

---

# 13. PROTOTYPE GATES

## V0
Upload -> validate -> one specialist -> answer

## V0.5
Upload -> query understanding -> routing -> specialist -> answer

## V1
Single-image tasks + temporal change + grounding + optical/SAR path

## V1.5
Evidence + verification + confidence + provenance

## V2
Benchmarks + performance optimization + polished UX + final demo hardening

Do not skip a gate unless the team explicitly records why.
Detailed exit criteria: [`docs/20_PROTOTYPE_ROADMAP.md`](docs/20_PROTOTYPE_ROADMAP.md).

---

# 14. "KILLER DEMO" PRINCIPLE

The demo should make the difficult technology visible.

A strong example:

Query:
"Has built-up area increased between these dates? Use SAR as supporting evidence."

Expected visible flow:

```
Query understood
    ->
T1/T2 validated
    ->
change specialist selected
    ->
change map generated
    ->
spatial evidence extracted
    ->
SAR evidence checked
    ->
evidence fused
    ->
confidence produced using defined method
    ->
answer + map + evidence + execution trace
```

The demo should not simply show:
"Here is our dashboard."

---

# 15. USER EXPERIENCE

Target interface:

## Screen A: ASK
- upload image(s);
- select/auto-detect modality;
- natural-language query;
- clear system status.

## Screen B: INVESTIGATE
- answer;
- confidence;
- before/after comparison;
- map;
- masks/bounding boxes;
- optical/SAR evidence;
- relevant statistics.

## Screen C: TRACE
- task selected;
- tools/models executed;
- important parameters;
- latency;
- evidence;
- validation events;
- warnings;
- provenance.

UI is not decoration.
The visual evidence is part of the product.

---

# 16. RESEARCH CREDIBILITY RULES

Never:
- fabricate benchmark results;
- fabricate latency;
- fabricate accuracy;
- call a target an achieved result;
- call a hypothesis a fact;
- claim global novelty without a defensible literature review;
- claim "ISRO currently takes X hours/days" without a credible source;
- claim a generic VLM always fails at a specific task without evidence.

Use language carefully:
- "our experiments show..."
- "our evaluation target is..."
- "our literature review identifies..."
- "the system is designed to..."
- "we hypothesize..."

---

# 17. PAST SIH / JURY LESSONS TO INTERNALIZE

Historical SIH guidance places weight on novelty, complexity, clarity/detail, feasibility, practicability, sustainability, scale of impact, user experience and future progression.

Past winner examples show that winning concepts do NOT have to be impossibly complicated:
- a language translator for government websites;
- a VR CBRN disaster-response training system;
- a community water-problem mapping system;
- AI-powered legal documentation / legal-awareness assistants;
- blockchain-based legal records.

The lesson is not that any one technology wins.

The lesson is:

> A strong SIH entry connects a real problem to a clear, practical solution with enough technical depth, demonstrable value and future potential.

Do not confuse "more technologies" with "more innovation."

---

# 18. JURY PERSONA

Assume reviewers may include combinations of:
- government/domain experts;
- technical evaluators;
- ML/software engineers;
- senior technology leaders;
- product/UI/UX reviewers.

Therefore the project must survive multiple lenses:

## Domain lens
Does this actually solve the stated problem?

## ML lens
Are the models appropriate? Are claims measured?

## Systems lens
Can these components actually work together?

## Geospatial lens
Are CRS, bands, registration and spatial outputs trustworthy?

## Product lens
Can a real person use this?

## Jury lens
What is genuinely new? Why this solution?

## Feasibility lens
Can this be built and extended realistically?

---

# 19. SIX-SLIDE PPT STRATEGY

The current internal blueprint uses exactly six slides.

## Slide 1
Problem + metadata + sharp value proposition

## Slide 2
Proposed solution + problem fit + innovation
Include a visual:
Problem Trigger -> Core IP / Algorithm -> Impact Outcome

## Slide 3
Technical Approach & Stack
Include an end-to-end architecture flowchart

## Slide 4
Feasibility & Risk Matrix
Challenge -> risk -> engineering mitigation

## Slide 5
Impact & Benefits Metrics
Use quantified metrics only.
Until measured, mark numbers as TARGETS.

## Slide 6
Research & References
Use a small number of high-authority citations.
Maintain a much larger internal research repository.

Do not exceed six slides.

---

# 20. SIX-SLIDE STORY

The story should be:

```
PROBLEM
  ->
existing approaches are fragmented
  ->
GAP
  ->
no coherent evidence-aware execution layer
  ->
SATQUERY
  ->
plan + validate + route + analyze + verify + explain + audit
  ->
PROOF
  ->
research + benchmark + measurable improvement
  ->
IMPACT
  ->
usable, scalable geospatial intelligence interface
```

Every slide should advance this story.

---

# 21. DEVELOPMENT FILE STRUCTURE

Recommended high-level structure (see ADR-001 in `docs/DECISIONS.md` for the
implemented version):

```
SATQUERY/
├── apps/
│   ├── backend/
│   └── frontend/
├── packages/
│   ├── core/
│   ├── geospatial/
│   ├── agents/
│   ├── evidence/
│   └── model_adapters/
├── external/
│   └── research/
│       ├── awesome-rs-vlms/
│       ├── GeoChat/
│       ├── Change-Agent/
│       ├── ChangeChat/
│       ├── ChangeFormer/
│       └── RemoteCLIP/
├── models/
│   ├── checkpoints/
│   └── cache/
├── data/
│   ├── raw/
│   ├── processed/
│   ├── demo/
│   └── manifests/
├── evaluation/
│   ├── datasets/
│   ├── metrics/
│   ├── cases/
│   └── reports/
├── docs/
│   ├── research/
│   ├── architecture/     (numbered docs 00–21 + DECISIONS.md live directly in docs/)
│   └── experiments/      (implemented as docs/19_EXPERIMENT_REGISTRY.md)
├── scripts/
├── infrastructure/
└── .claude/
```

Research repositories must remain isolated under `external/research/`.
Do not mix their source tree into SatQuery application code.

---

# 22. CLAUDE CODE OPERATING PRINCIPLES

Before implementing a major feature, Claude should:

1. Read the relevant project documents.
2. Identify the SIH requirement addressed.
3. Search existing research/components.
4. Decide whether reuse is appropriate.
5. Define a baseline where applicable.
6. Define a success metric.
7. Implement the smallest useful experiment.
8. Measure the result.
9. Record the decision.
10. Integrate only after the evidence supports it.

When uncertain:
- inspect;
- test;
- measure;
- document.

Do not invent.

Full version: [`docs/21_CLAUDE_WORKING_PRINCIPLES.md`](docs/21_CLAUDE_WORKING_PRINCIPLES.md).

---

# 23. DEFINITION OF DONE

A FEATURE is not complete until:

- implemented;
- tests exist;
- error paths exist;
- logging exists;
- relevant evaluation case exists;
- observable through UI/API where relevant;
- documentation is updated;
- demo path is functional.

A RESEARCH ITEM is not complete until:

- source identified;
- method understood;
- implementation tested;
- baseline measured;
- limitation documented;
- experiment completed where relevant;
- decision recorded;
- citation recorded.

---

# 24. PROJECT STATUS SYSTEM

Maintain a single project status file:

`docs/PROJECT_STATUS.md`

It must always contain:

## DONE
What works and how it was verified.

## IN PROGRESS
What is actively being built.

## BLOCKED
What prevents progress and why.

## MISSING
Required capabilities not yet implemented.

## RESEARCH NEEDED
Open research/model questions.

## METRICS
All measured metrics with dataset, split and date.

## RISKS
Technical and submission risks.

## NEXT 3 ACTIONS
Only the next three highest-value actions.

## WIN SCORECARD
Rate 0-10:
- problem fit
- novelty
- technical depth
- prototype completeness
- accuracy
- multimodal reasoning
- temporal reasoning
- geospatial integrity
- evidence/verification
- UI/UX
- benchmark readiness
- feasibility
- impact
- PPT quality
- demo quality

Always explain why the score changed.

---

# 25. DECISION LOG

Maintain:

`docs/DECISIONS.md`

For each major decision record:

- date;
- decision;
- alternatives;
- evidence;
- reason;
- trade-off;
- consequence.

This prevents circular discussions.

---

# 26. RED-TEAM QUESTIONS

Before calling a feature "innovative," ask:

- Who already does this?
- Is this actually novel or merely integrated?
- Can an existing RS-VLM already do this?
- What exactly is ours?
- Can we measure the improvement?
- Is the improvement statistically / experimentally credible?
- What happens when models disagree?
- What if metadata is wrong?
- What if optical and SAR disagree?
- What if images are misregistered?
- What if the query is ambiguous?
- What if inference fails?
- What is the fallback?
- What is the latency?
- What hardware is needed?
- Could the jury reproduce the demo?

---

# 27. SCOPE CONTROL

Every proposed feature must answer:

1. Which SIH requirement does it satisfy?
2. What user value does it add?
3. What measurable improvement does it create?
4. Does it improve the demo?
5. What is the engineering cost?
6. Can it be validated?
7. What will we have to delay to build it?

If it cannot justify itself, CUT IT.

Do not build:
- blockchain just for buzzwords;
- unnecessary microservices;
- unnecessary agents;
- giant models when smaller models work;
- features with no evaluation path;
- UI animations that hide weak functionality.

---

# 28. OPEN-MINDEDNESS RULE

This architecture is a starting hypothesis, not a religion.

If experiments show:
- GeoChat is inferior to another model -> replace it.
- ChangeChat is easier and more reliable than Change-Agent -> use ChangeChat.
- An external model can already perform a component better -> reuse it.
- Our verifier is not useful -> redesign it.
- A simpler router is more reliable than an LLM planner -> simplify.
- A proposed innovation does not improve measurements -> abandon it.
- New research appears that materially changes the best approach -> investigate it.

The goal is not to defend our first architecture.

The goal is to continuously converge on the strongest solution.

---

# 29. PERFORMANCE PRINCIPLE

Optimize in this order:

1. Correctness
2. Reliability
3. Required benchmark performance
4. Inference stability
5. Latency
6. Cost
7. UI polish

Do not sacrifice correctness for demo speed without explicitly documenting the trade-off.

---

# 30. SECURITY / PRIVACY

Remote-sensing data may be sensitive.

The system should:
- minimize unnecessary transmission;
- validate uploaded files;
- avoid arbitrary code execution from input;
- restrict model/tool parameters;
- log important processing steps;
- protect secrets;
- separate user data from application code;
- avoid storing data longer than necessary in deployment;
- clearly distinguish demo data from sensitive operational data.

Do not make unsupported security claims.

---

# 31. FINAL DEMO PRINCIPLE

The strongest demo is evidence-first.

Example sequence:

1. Upload T1 optical
2. Upload T2 optical
3. Upload corresponding SAR if applicable
4. Ask one hard question
5. Show query interpretation
6. Show validation
7. Show model/tool routing
8. Show specialist outputs
9. Show verification
10. Show fused answer
11. Show spatial evidence
12. Open audit trace

The jury should see:
**problem -> intelligence -> proof -> result**

not:
**dashboard -> buttons -> claims**

---

# 32. CURRENT UNKNOWNS THAT MUST BE RESOLVED

Before architecture is frozen, establish:

- exact public benchmark packaging;
- exact BigEarthNet.txt access/training format;
- available model checkpoints;
- license compatibility;
- GPU environment;
- actual performance of candidate models;
- exact input/output contracts;
- achievable inference latency;
- how confidence will be derived;
- best approach for optical-SAR fusion;
- best temporal model;
- best grounding model;
- how much fine-tuning is genuinely needed.

Never fill these gaps with assumptions.

---

# 33. CURRENT PROJECT STATE

Update this section frequently. The authoritative live view is
[`docs/PROJECT_STATUS.md`](docs/PROJECT_STATUS.md).

## Completed
- PS 26167 understood.
- Initial architecture concept created.
- Research catalogue identified.
- Candidate repositories identified.
- Six-slide PPT blueprint established.
- Research-to-accuracy operating philosophy established.
- Multi-device / isolated-model-service architecture considered.
- Monorepo scaffold + Claude Code harness (rules/skills/agents) built (ADR-001).
- 6 research repos cloned + inventoried under `external/research/` (ADR-002).
- Strategy docs `docs/17`–`docs/21` written.

## In Progress
- Clone/inventory research repositories. (done — inventory in `docs/research/`)
- Validate candidate model environments.
- Build model comparison matrix.
- Build experiment registry. (seeded — `docs/19_EXPERIMENT_REGISTRY.md`)
- Build project-status system. (created — `docs/PROJECT_STATUS.md`)
- Build initial MVP architecture. (V0 not yet started)

## Missing
- Reproduced model benchmarks.
- Actual baseline metrics.
- Actual SatQuery metrics.
- Fine-tuning/adaptation proof.
- Optical-SAR experiment.
- Temporal experiment.
- Verification experiment.
- End-to-end prototype.
- Final PPT evidence.
- Adversarial testing.

---

# 34. WINNING OPERATING RHYTHM

Every work session should end with:

### What changed?
Code / research / metrics / design

### What did we learn?
Especially failures.

### What did we prove?
Measured facts only.

### What remains weak?
Identify honestly.

### What is the highest-leverage next step?
Pick one.

Avoid endless feature accumulation.

---

# 35. FINAL NORTH STAR

SatQuery should ultimately feel like:

**QUERY -> PLAN -> VALIDATE -> ROUTE -> ANALYZE -> VERIFY -> FUSE -> EXPLAIN -> AUDIT**

Not:

**QUERY -> LLM -> ANSWER**

Our biggest advantage should be:
**coherent system engineering around specialized remote-sensing intelligence.**

The winning project is not the project with the most repositories.

It is the project with the strongest combination of:
**research evidence + measurable performance + reliable architecture + memorable demo + credible impact.**

---

# 36. SOURCE REFERENCES

Maintain authoritative references in the research repository.

At minimum:
- Official SIH problem statement / portal materials
- SIH evaluation guidance
- relevant RS-VLM papers
- relevant change-detection / change-VQA papers
- dataset papers
- repository licenses / documentation
- benchmark documentation

When a claim is important enough for the PPT, make sure there is a source or an experimental result behind it.

END OF CONTEXT
