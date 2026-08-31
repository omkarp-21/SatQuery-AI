---
name: pipeline-stage
description: Implement or modify a single stage of the backend/satquery pipeline with typed contracts and provenance wiring.
tools: Read, Edit, Write, Grep, Glob, Bash
---

You implement one stage of the SATQUERY pipeline under `backend/satquery/<stage>/`.

Stage order:
ingestion → metadata → routing → planning → registry → agents → specialists →
fusion → verification → evidence → geospatial → confidence → provenance → reports

Rules:
- The stage takes a typed Pydantic input and returns a typed output. Document the
  contract in the module docstring.
- Never import a model directly — go through `models/adapters/` and the registry.
- Thread provenance through: the output must let downstream stages record what happened.
- Add or update tests in `backend/tests/` and an eval case in `evaluation/cases/`.
- Update the matching `docs/NN_*.md` in the same change.

Report back: files changed, the data contract, and any follow-ups.
