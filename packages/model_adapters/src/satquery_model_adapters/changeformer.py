"""ChangeFormer adapter - bi-temporal binary change **mask**.

Upstream: ChangeFormerV6 (`wgcban/ChangeFormer`, MIT). Reproduced + measured in
`docs/research/runtime_validation.md` (IoU 0.83 / F1 0.91 on 7 bundled LEVIR-CD
samples - a sanity check, not a benchmark).

Does NOT do: semantic change classes, captions, VQA, SAR. Those raise
``UnsupportedTaskError`` - never approximated.

Input:  ``AdapterRequest.images == [t1_path, t2_path]`` (RGB, identical dims;
        co-registration is the caller's job - see `satquery_geospatial`).
Output: answer  = {changed_fraction, changed_pixels, total_pixels}
        artifacts = {mask_path, height, width}
        score   = changed_fraction  - **pixel coverage, not a confidence.**

Isolation: runs `scripts/research/changeformer_infer.py` inside `.venvs/changeformer`
via subprocess. This module never imports the research repo.
"""

from __future__ import annotations

import shutil
import tempfile
import time
from pathlib import Path

from ._bridge import bridge_script, run_bridge, sha256, venv_python
from .base import AdapterRequest, NormalizedOutput, RawOutput, SpecialistAdapter
from .errors import AdapterConfigError, AdapterExecutionError, UnsupportedTaskError


class ChangeFormerAdapter(SpecialistAdapter):
    name = "changeformer"
    version = "ChangeFormerV6@afd1b7e"
    source_repo = "https://github.com/wgcban/ChangeFormer"
    license = "MIT"
    capabilities = ("change-detection",)
    modalities = ("optical-bitemporal",)

    def __init__(self, *, checkpoint: str, timeout_s: float = 300.0, **options) -> None:
        super().__init__(checkpoint=checkpoint, timeout_s=timeout_s, **options)
        self.checkpoint_dir = Path(checkpoint)
        self._py = venv_python("changeformer", options.get("venv_python"))
        self._script = bridge_script("changeformer_infer.py", options.get("bridge_script"))

    # --- interface ---

    def validate(self, request: AdapterRequest) -> None:
        task = request.context.get("task", "change-detection")
        if task not in self.capabilities:
            raise UnsupportedTaskError(
                f"changeformer supports {self.capabilities}, not {task!r} - no approximation"
            )
        if len(request.images) != 2:
            raise AdapterExecutionError(f"changeformer needs 2 images (T1, T2); got {len(request.images)}")
        for p in request.images:
            if not Path(p).exists():
                raise AdapterExecutionError(f"input not found: {p}")
        if not (self.checkpoint_dir / "best_ckpt.pt").exists():
            raise AdapterConfigError(f"checkpoint not found: {self.checkpoint_dir / 'best_ckpt.pt'}")

    def execute(self, request: AdapterRequest) -> RawOutput:
        self._artifact_dir = request.context.get("artifact_dir")
        args = [
            "--a", str(request.images[0]),
            "--b", str(request.images[1]),
            "--checkpoint-dir", str(self.checkpoint_dir),
            "--out-mask", self._staged_mask_path(),
        ]
        payload, runtime = run_bridge(self._py, self._script, args, timeout_s=self.timeout_s)
        return RawOutput(data=payload, runtime_s=payload.get("runtime_s", runtime))

    def normalize_output(self, raw: RawOutput, request: AdapterRequest) -> NormalizedOutput:
        d = raw.data
        persisted = None
        staged = getattr(self, "_staged_mask", None)
        if staged and Path(staged).exists():
            persisted = self._persist(staged)
        return NormalizedOutput(
            answer={
                "changed_fraction": d["changed_fraction"],
                "changed_pixels": d["changed_pixels"],
                "total_pixels": d["total_pixels"],
            },
            score=d["changed_fraction"],
            artifacts={"mask_path": persisted, "height": d["height"], "width": d["width"]},
            score_meaning="fraction of pixels flagged changed - NOT a confidence",
        )

    def provenance(self, request, raw, timing):
        prov = super().provenance(request, raw, timing)
        ckpt = self.checkpoint_dir / "best_ckpt.pt"
        prov.update(
            checkpoint_sha256=sha256(ckpt),
            input_digest=sha256(request.images[0])[:16] + ":" + sha256(request.images[1])[:16],
            device="cpu",
            bridge="scripts/research/changeformer_infer.py",
        )
        return prov

    # --- helpers ---

    def _staged_mask_path(self) -> str:
        self._staged = tempfile.NamedTemporaryFile(suffix=".png", delete=False).name
        self._staged_mask = self._staged
        return self._staged

    def _persist(self, src: str) -> str:
        dest_dir = Path(self._artifact_dir) if self._artifact_dir else Path(tempfile.mkdtemp(prefix="satquery_cf_"))
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / f"changeformer_mask_{int(time.time()*1000)}.png"
        shutil.copyfile(src, dest)
        Path(src).unlink(missing_ok=True)
        return str(dest)
