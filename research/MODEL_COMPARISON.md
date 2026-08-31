# Model Comparison

Drives `models/model_registry.yaml` and the routing stage.

## Candidates

| Model | Upstream commit | Tasks | Input modality | Strengths | Weaknesses | Verdict |
|-------|-----------------|-------|----------------|-----------|------------|---------|
| GeoChat | _TBD_ | VQA, grounding, region captioning | Optical, single | Conversational, region-level | Not bitemporal | **In** |
| Change-Agent | _TBD_ | Change detection + captioning, multi-turn | Optical, bitemporal | Agentic, explainable | Heavier | **In** |
| ChangeChat | _TBD_ | Change captioning, change VQA | Optical, bitemporal | Instruction-tuned dialogue | Captioning bias | **In** |
| ChangeFormer | _TBD_ | Change detection (masks) | Optical, bitemporal | Precise masks, fast | No language | **In** (mask backend) |
| RemoteCLIP | _TBD_ | Retrieval, zero-shot, embeddings | Optical, single | Fast scene retrieval, embeddings | Coarse | **In** (retrieval/index) |

## Evaluation hooks

Each model gets cases in `evaluation/cases/` and metrics in `evaluation/metrics/`.
Record numbers here once the eval suite runs.

## Open questions

- SAR support — none of the above; do we need a sixth adapter?
- Fusion weighting: static (registry) vs. learned.
