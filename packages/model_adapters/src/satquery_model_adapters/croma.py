"""CROMA adapter - joint radar-optical representation (embeddings only).

Upstream: `antofuller/CROMA` (MIT, NeurIPS 2023). Reproduced in
`docs/research/runtime_validation.md`. Produces GAP feature vectors; a downstream
head (linear probe / retrieval) is the caller's job. No language, no task output.

Input:  `AdapterRequest.images` = [s1_npy, s2_npy] - S1 (2, H, W), S2 (12, H, W)
        numpy arrays saved to disk. Or `context={"random": 1}` for a smoke.
Output: answer = {joint_gap, optical_gap, sar_gap, dim}; no score.
Modality: **optical-sar** (paired). Rejects a single-modality request.
"""

from __future__ import annotations

from pathlib import Path

from ._bridge import bridge_script, run_bridge, sha256, venv_python
from .base import AdapterRequest, NormalizedOutput, RawOutput, SpecialistAdapter
from .errors import AdapterExecutionError, UnsupportedModalityError, UnsupportedTaskError

_TASKS = ("embedding", "representation")


class CromaAdapter(SpecialistAdapter):
    name = "croma"
    version = "CROMA_base@59505a6"
    source_repo = "https://github.com/antofuller/CROMA"
    license = "MIT"
    capabilities = _TASKS
    modalities = ("optical-sar",)

    def __init__(self, *, checkpoint: str, timeout_s: float = 240.0, size: str = "base",
                 resolution: int = 120, lora_weights: str | None = None, **opts) -> None:
        super().__init__(checkpoint=checkpoint, timeout_s=timeout_s, **opts)
        self.size = size
        self.resolution = resolution
        # G17 (EXP-008): OPTIONAL frozen-encoder LoRA delta. Production default is
        # None = frozen CROMA. Only pass this once a larger-split validation
        # supports adaptation (see docs/G17_HYBRID_AGENT_REPORT.md Part 19/20).
        self.lora_weights = str(lora_weights) if lora_weights else None
        self._py = venv_python("croma", opts.get("venv_python"))
        self._script = bridge_script("croma_infer.py", opts.get("bridge_script"))

    def validate(self, request: AdapterRequest) -> None:
        task = request.context.get("task", "embedding")
        if task not in self.capabilities:
            raise UnsupportedTaskError(f"croma supports {self.capabilities}, not {task!r}")
        if request.context.get("random"):
            return
        if len(request.images) != 2:
            raise UnsupportedModalityError(
                "croma needs a paired [s1_npy, s2_npy]; it does not accept a single modality"
            )
        for p in request.images:
            if not Path(p).exists():
                raise AdapterExecutionError(f"input not found: {p}")

    def execute(self, request: AdapterRequest) -> RawOutput:
        args = ["--checkpoint", str(self.checkpoint), "--size", self.size,
                "--resolution", str(self.resolution)]
        if self.lora_weights:
            if not Path(self.lora_weights).exists():
                raise AdapterExecutionError(f"lora weights not found: {self.lora_weights}")
            args += ["--lora-weights", self.lora_weights]
        if request.context.get("random"):
            args += ["--random", "1"]
        else:
            args += ["--s1-npy", str(request.images[0]), "--s2-npy", str(request.images[1])]
        payload, runtime = run_bridge(self._py, self._script, args, timeout_s=self.timeout_s)
        return RawOutput(data=payload, runtime_s=payload.get("runtime_s", runtime))

    def normalize_output(self, raw: RawOutput, request: AdapterRequest) -> NormalizedOutput:
        d = raw.data
        return NormalizedOutput(
            answer={"joint_gap": d["joint_gap"], "optical_gap": d["optical_gap"],
                    "sar_gap": d["sar_gap"], "dim": d["dim"]},
            score=None,
            artifacts={"n_patches": d["n_patches"]},
            score_meaning="n/a - CROMA returns representations, not scores",
        )

    def provenance(self, request, raw, timing):
        prov = super().provenance(request, raw, timing)
        prov.update(checkpoint_sha256=sha256(self.checkpoint), device="cpu",
                    size=self.size, resolution=self.resolution,
                    bridge="scripts/research/croma_infer.py",
                    lora_weights=self.lora_weights,
                    lora_weights_sha256=sha256(self.lora_weights) if self.lora_weights else None,
                    encoder_mode="lora_adapted" if self.lora_weights else "frozen")
        return prov
