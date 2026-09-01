"""DOFA adapter - multi-sensor (incl. SAR) representation via one wavelength-
conditioned encoder. Upstream: `zhu-xlab/DOFA` (MIT). Reproduced in
`docs/research/runtime_validation.md`.

Encodes ONE modality per call (S1 2ch or S2 12ch). Fusion (S2 ⊕ S1) is a
downstream design choice - call twice and concatenate. No language, no task head.

Input:  `AdapterRequest.images` = [x_npy]  (C, H, W);  `context["modality"]` in
        {"s1", "s2"}. Or `context={"random": 1}` for a smoke.
Output: answer = {feature, dim, modality}; no score.
"""

from __future__ import annotations

from pathlib import Path

from ._bridge import bridge_script, run_bridge, sha256, venv_python
from .base import AdapterRequest, NormalizedOutput, RawOutput, SpecialistAdapter
from .errors import AdapterExecutionError, UnsupportedModalityError, UnsupportedTaskError

_TASKS = ("embedding", "representation")


class DofaAdapter(SpecialistAdapter):
    name = "dofa"
    version = "DOFA_ViT_base_e100@0cfb7e1"
    source_repo = "https://github.com/zhu-xlab/DOFA"
    license = "MIT"
    capabilities = _TASKS
    modalities = ("optical-single", "sar-single")

    def __init__(self, *, checkpoint: str, timeout_s: float = 180.0, **opts) -> None:
        super().__init__(checkpoint=checkpoint, timeout_s=timeout_s, **opts)
        self._py = venv_python("dofa", opts.get("venv_python"))
        self._script = bridge_script("dofa_infer.py", opts.get("bridge_script"))

    def validate(self, request: AdapterRequest) -> None:
        task = request.context.get("task", "embedding")
        if task not in self.capabilities:
            raise UnsupportedTaskError(f"dofa supports {self.capabilities}, not {task!r}")
        mod = request.context.get("modality")
        if mod not in ("s1", "s2"):
            raise UnsupportedModalityError("dofa needs context['modality'] == 's1' or 's2'")
        if request.context.get("random"):
            return
        if len(request.images) != 1 or not Path(request.images[0]).exists():
            raise AdapterExecutionError("dofa needs one existing [x_npy] path")

    def execute(self, request: AdapterRequest) -> RawOutput:
        mod = request.context["modality"]
        args = ["--checkpoint", str(self.checkpoint), "--modality", mod]
        if request.context.get("random"):
            args += ["--random", "1"]
        else:
            args += ["--x-npy", str(request.images[0])]
        payload, runtime = run_bridge(self._py, self._script, args, timeout_s=self.timeout_s)
        return RawOutput(data=payload, runtime_s=payload.get("runtime_s", runtime))

    def normalize_output(self, raw: RawOutput, request: AdapterRequest) -> NormalizedOutput:
        d = raw.data
        return NormalizedOutput(
            answer={"feature": d["feature"], "dim": d["dim"], "modality": d["modality"]},
            score=None,
            artifacts={},
            score_meaning="n/a - DOFA returns a representation, not a score",
        )

    def provenance(self, request, raw, timing):
        prov = super().provenance(request, raw, timing)
        prov.update(checkpoint_sha256=sha256(self.checkpoint), device="cpu",
                    modality=request.context.get("modality"),
                    bridge="scripts/research/dofa_infer.py")
        return prov
