"""RemoteCLIP adapter - RS image/text embeddings, zero-shot scene classification,
retrieval scoring. Upstream: `ChenDelong1999/RemoteCLIP` (Apache-2.0). Reproduced
in `docs/research/runtime_validation.md`.

This is **not a VQA model**. `capabilities` are retrieval / zero-shot-classification
/ embedding only. A VQA request raises ``UnsupportedTaskError``.

Input:  `AdapterRequest.query` = ';'-separated candidate labels/captions;
        `AdapterRequest.images` = [one RGB image path].
Output: answer = {top_label, ranking:[(label, prob)...]}; score = top prob
        (a softmax over the *given* prompts - a relative score, not a calibrated
        probability of correctness).
"""

from __future__ import annotations

from pathlib import Path

from ._bridge import bridge_script, run_bridge, sha256, venv_python
from .base import AdapterRequest, NormalizedOutput, RawOutput, SpecialistAdapter
from .errors import AdapterExecutionError, UnsupportedTaskError

_SUPPORTED = ("zero-shot-classification", "retrieval", "embedding")


class RemoteClipAdapter(SpecialistAdapter):
    name = "remoteclip"
    version = "RemoteCLIP-ViT-B-32@a6a4787"
    source_repo = "https://github.com/ChenDelong1999/RemoteCLIP"
    license = "Apache-2.0"
    capabilities = _SUPPORTED
    modalities = ("optical-single",)

    def __init__(self, *, checkpoint: str, timeout_s: float = 180.0, model_name: str = "ViT-B-32", **opts) -> None:
        super().__init__(checkpoint=checkpoint, timeout_s=timeout_s, **opts)
        self.model_name = model_name
        self._py = venv_python("remoteclip", opts.get("venv_python"))
        self._script = bridge_script("remoteclip_infer.py", opts.get("bridge_script"))

    def validate(self, request: AdapterRequest) -> None:
        task = request.context.get("task", "zero-shot-classification")
        if task not in self.capabilities:
            raise UnsupportedTaskError(
                f"remoteclip supports {self.capabilities}, not {task!r} (it is NOT a VQA model)"
            )
        if len(request.images) != 1:
            raise AdapterExecutionError(f"remoteclip needs exactly 1 image; got {len(request.images)}")
        if not Path(request.images[0]).exists():
            raise AdapterExecutionError(f"input not found: {request.images[0]}")
        if not [p.strip() for p in request.query.split(";") if p.strip()]:
            raise AdapterExecutionError("remoteclip needs ';'-separated candidate labels in request.query")

    def execute(self, request: AdapterRequest) -> RawOutput:
        args = [
            "--image", str(request.images[0]),
            "--prompts", request.query,
            "--checkpoint", str(self.checkpoint),
            "--model-name", self.model_name,
        ]
        payload, runtime = run_bridge(self._py, self._script, args, timeout_s=self.timeout_s)
        return RawOutput(data=payload, runtime_s=payload.get("runtime_s", runtime))

    def normalize_output(self, raw: RawOutput, request: AdapterRequest) -> NormalizedOutput:
        d = raw.data
        ranking = sorted(zip(d["prompts"], d["probs"]), key=lambda t: -t[1])
        return NormalizedOutput(
            answer={"top_label": d["top_prompt"], "ranking": [[l, p] for l, p in ranking]},
            score=float(d["probs"][d["top_index"]]),
            artifacts={"image_embed_dim": d["image_embed_dim"]},
            score_meaning="softmax over the supplied prompts - a relative score, not calibrated P(correct)",
        )

    def provenance(self, request, raw, timing):
        prov = super().provenance(request, raw, timing)
        prov.update(
            checkpoint_sha256=sha256(self.checkpoint),
            input_digest=sha256(request.images[0])[:16],
            device="cpu",
            model_name=self.model_name,
            bridge="scripts/research/remoteclip_infer.py",
        )
        return prov
