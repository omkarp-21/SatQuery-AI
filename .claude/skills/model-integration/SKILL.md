---
name: model-integration
description: How to wrap an arbitrary research repository into a SatQuery SpecialistAdapter — validate_input, execute, normalize_output, confidence, provenance — plus registry registration, checkpoint handling, and smoke testing. Invoke when adding or updating a model (GeoChat, Change-Agent, ChangeChat, ChangeFormer, RemoteCLIP, or new).
---

# Model Integration

Enforces `.claude/rules/ai-models.md`. Turns a messy research repo into a
predictable component.

## The adapter shape

```python
class SpecialistAdapter(ModelAdapter):
    name = "..."          # matches models/model_registry.yaml key
    version = "..."       # upstream tag/commit you integrated
    tasks = (...)
    modalities = (...)    # e.g. ("optical-bitemporal",) — SAR is its own tag

    def validate_input(self, request: AdapterRequest) -> None:
        """Raise a typed error if this model cannot serve this request.
        Check: task supported, modality supported, band count, image size,
        number of timepoints, dtype/range. Reject SAR into an optical model."""

    def execute(self, request: AdapterRequest) -> RawOutput:
        """Run inference. Load lazily (self.load()). Prefer a vendored minimal
        inference path or a subprocess call into research/repos/<repo>/ with an
        explicit arg list + timeout. Never import research code into product."""

    def normalize_output(self, raw: RawOutput) -> AdapterResult:
        """Map the repo's idiosyncratic output to the shared schema:
        answer, artifacts (mask/boxes/embedding/caption), score."""

    def confidence(self, raw: RawOutput) -> Confidence:
        """Return a value AND its meaning. If it's a softmax prob, say so.
        If it's a margin or a heuristic, label it. Never dress a logit as a probability."""

    def provenance(self, request, raw) -> dict:
        """model name+version, checkpoint sha256, input digest, device,
        library versions, timestamp, upstream repo+commit, license."""
```

## Integration steps

1. **Read the repo.** Find the exact inference entrypoint, input preprocessing,
   checkpoint format, and license. Note the upstream commit hash in
   `research/MODEL_COMPARISON.md`.
2. **Vendor or submodule** into `research/repos/<name>/` (read-only).
3. **Pin the checkpoint**: downloader in `scripts/download_models/`, expected
   sha256 recorded, target `models/checkpoints/<name>/`.
4. **Write the adapter** in `models/adapters/<name>.py` implementing all five methods.
5. **Register** in `models/model_registry.yaml` with every required field.
6. **Smoke test** in `backend/tests/` (`@pytest.mark.slow`/`gpu`): load checkpoint,
   run one real inference on a tiny fixture, assert the output schema.
7. **Document** in the adapter docstring: what it does, what it does NOT do,
   expected input, output schema, confidence meaning, GPU/VRAM needs.

## Isolation rules

- No `import` from `research/repos/` in `backend/` or `models/adapters/`
  (subprocess or a small vendored function only).
- Orchestration (planning/agents) never imports `torch` or a model — it goes
  through the registry.
- An adapter that can't fulfil a request raises `UnsupportedTaskError` /
  `UnsupportedModalityError` — it does not approximate or fall back silently.

## CPU / no-GPU

Every adapter declares `gpu_required` and VRAM. If no GPU is available, the
adapter raises a clear error the planner can route around — the system degrades
explicitly, never pretends.
