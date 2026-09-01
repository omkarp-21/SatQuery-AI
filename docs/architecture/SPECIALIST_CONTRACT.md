# Specialist Adapter Contract

> `packages/model_adapters/src/satquery_model_adapters/base.py`. Every research
> model SatQuery uses is reached through a `SpecialistAdapter` subclass. Product
> code never imports a research repo (`.claude/rules/ai-models.md`).

## Class facts (declared as class attributes)

| Attribute | Meaning |
|-----------|---------|
| `name` | registry key, e.g. `"changeformer"` |
| `version` | upstream tag/commit integrated, e.g. `"ChangeFormerV6@afd1b7e"` |
| `source_repo` | upstream URL |
| `license` | SPDX-ish string |
| `capabilities` | tuple of supported tasks |
| `modalities` | tuple, e.g. `("optical-bitemporal",)` |

These are surfaced by `describe()` and must match `model_registry.yaml`.

## The four methods

```python
def validate(self, request: AdapterRequest) -> None
    # raise a typed error if this model cannot serve the request.
    # UnsupportedTaskError / UnsupportedModalityError / AdapterConfigError /
    # AdapterExecutionError. NEVER approximate an unsupported task.

def execute(self, request: AdapterRequest) -> RawOutput
    # run inference in the isolated env (.venvs/<model>) via a bridge script in
    # scripts/research/, invoked by subprocess with an explicit arg list + timeout.
    # Returns the raw per-model JSON payload + runtime.

def normalize_output(self, raw: RawOutput, request: AdapterRequest) -> NormalizedOutput
    # map the model's idiosyncratic output to the shared schema:
    # answer, score (or None), artifacts, score_meaning.

def provenance(self, request, raw, timing) -> dict
    # call super().provenance(...) then .update(...) with model-specific fields.
```

## Template method (`run`) — the orchestrator entrypoint

```
run(request):
    validate(request)
    raw  = execute(request)
    norm = normalize_output(raw, request)
    prov = provenance(request, raw, timing)
    return AdapterResult(model, answer, score, artifacts, provenance,
                         status, timing_s, model_meta)
```

`predict` is a back-compat alias for `run`.

## Every `AdapterResult` carries

- `model` + `model_meta` (name/version/license/capabilities/modalities)
- `answer` (structured) and `score` (**or `None`** — a score is never a confidence
  unless calibrated; `provenance["score_meaning"]` says what it is)
- `artifacts` (paths to masks/embeddings/…)
- `provenance` (model, version, checkpoint + sha256, input digest, device,
  runtime, bridge, timestamp, `score_meaning`)
- `status` (`ok` | `degraded` | `error`)
- `timing_s`

## Standardized errors (`errors.py`)

`AdapterError` → `UnsupportedTaskError`, `UnsupportedModalityError`,
`AdapterConfigError` (missing venv/checkpoint), `AdapterExecutionError`
(subprocess failed / timed out / bad output). `_bridge.run_bridge()` centralizes
the subprocess + JSON parsing and raises these.

## Isolation rules

- No `import` from `external/research/` anywhere in `apps/` or `packages/`.
- The bridge script (`scripts/research/<model>_infer.py`) runs **inside**
  `.venvs/<model>`; it may import the research repo because it is not product code.
- `.venvs/<model>` python and the bridge path are resolvable via
  `SATQUERY_<MODEL>_VENV_PYTHON` / defaults (`.venvs/<model>/Scripts/python.exe`).

## Adopted adapters (G3)

| Adapter | capabilities | modalities | evidence level |
|---------|--------------|-----------|----------------|
| `ChangeFormerAdapter` | change-detection | optical-bitemporal | INTEGRATED (measured n=7) |
| `RemoteClipAdapter` | zero-shot-classification, retrieval, embedding | optical-single | INTEGRATED (reproduced) |
| `CromaAdapter` | embedding, representation | optical-sar | REPRODUCED |
| `DofaAdapter` | embedding, representation | optical-single, sar-single | REPRODUCED |

Registry loader: `satquery_model_adapters.ADAPTERS` (name → class).
