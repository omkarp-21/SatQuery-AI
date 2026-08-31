# Model Architecture

> Status: **Draft outline** · Owner: _TBD_ · Last updated: 2026-09-01
> Full per-repo detail: `docs/research/model_inventory.md`. Selection is decided by
> experiments in `docs/19_EXPERIMENT_REGISTRY.md`, not by reputation.

## Purpose

Record which specialist models cover which tasks, and the criteria by which one is
chosen over another.

## Candidate specialists (none final until measured)

| Candidate | Intended role | Modality |
|-----------|---------------|----------|
| GeoChat | single-image VQA / grounding / scene | optical, single |
| Change-Agent | bi-temporal change detection + captioning | optical, bi-temporal |
| ChangeChat | conversational change analysis (⚠ weights unreleased) | optical, bi-temporal |
| ChangeFormer | pixel-level change mask baseline | optical, bi-temporal |
| RemoteCLIP | scene retrieval / zero-shot / embeddings | optical, single |

## Selection criteria (the accuracy-to-engineering-cost ratio, `docs/18`)

```
accuracy + generalization + input compatibility + output quality
        + latency + GPU/RAM requirements + dependency complexity
        + reproducibility + license + integration effort
```

Use the smallest / simplest model that meets the quality bar. Never pick a model
because it is famous, new, or large.

## Every candidate carries a record

repository · paper · license · checkpoint source · supported tasks · supported
modalities · input format · output schema · expected hardware · environment
requirements · paper result · **our reproduction** · **SatQuery result** ·
strengths · weaknesses · integration effort · **final decision**.

(The three-numbers separation is mandatory — `docs/18`, `.claude/rules/documentation.md`.)

## Open questions

- How much fine-tuning is genuinely required for the BigEarthNet adaptation requirement.
- Best grounding model (GeoChat vs alternatives from `awesome-rs-vlms`).
- Whether a SAR-specific model/adapter is needed (none of the current five handle SAR).
