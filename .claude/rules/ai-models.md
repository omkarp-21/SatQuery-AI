# AI Model Rules

Every model adapter must define:

- name
- version
- source repository
- license
- checkpoint
- supported modalities
- supported tasks
- expected input
- output schema
- confidence behavior
- GPU requirements

Model code must remain isolated from orchestration logic.

## Additional constraints

- These fields are declared in `models/model_registry.yaml` and enforced by the
  adapter base class. Routing reads only the registry — never hardcoded model names.
- An adapter never claims a capability the upstream model does not have. If a task
  is unsupported, the adapter raises `UnsupportedTaskError`, it does not approximate.
- SAR is a distinct modality. An optical-only model is never handed SAR input, and
  the adapter rejects it rather than treating it as RGB.
- Every adapter output includes a `provenance` block (model name+version, checkpoint
  hash, input digest, device, timestamp) and a `confidence` value whose meaning is
  documented (probability? margin? heuristic? — say which).
- Confidence that is not a calibrated probability must be labeled as such. Never
  present a raw logit or an ad-hoc score as "confidence: 0.9" without qualification.
- Checkpoints live in `models/checkpoints/` (gitignored) with a downloader script.
  The expected file hash is recorded so a wrong/partial checkpoint fails fast.
- No model is integrated before its adapter has a smoke test that loads it and runs
  one real inference. "Test before integrating."
- Research repo code stays in `research/repos/`. The adapter may shell out to it or
  vendor a minimal inference path, but product code does not import from it.
