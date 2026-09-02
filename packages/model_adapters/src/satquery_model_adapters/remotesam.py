"""RemoteSAM adapter - text-guided grounding + referring segmentation.

Upstream: RemoteSAM (`1e12Leon/RemoteSAM`, ACM MM 2025), Swin-Base + BERT,
checkpoint `RemoteSAMv1.pth` (state_dict: 854 backbone / 197 text_encoder / 56
decoder). **Reproduced** on this host (CPU) - `docs/research/EXP-GROUNDING.md`.
NOT measured on DIOR-RSVG (dataset unacquirable).

**License: NOT STATED.** No LICENSE file in the repo and the HF checkpoint page
has no model card. This adapter records that; adoption for anything beyond a
research prototype needs the authors to state a licence.

Does NOT do: VQA, captioning as a first-class task, SAR, temporal. Those raise
``UnsupportedTaskError`` - never approximated.

Input:  ``AdapterRequest.images == [image_path]`` (1 RGB image) +
        ``context["query"]`` or ``request.query`` (the referring phrase).
Output: answer    = {bbox_xyxy, mask_fg_fraction, image_dims}
        artifacts = {mask_path}
        score     = prob_max  - RemoteSAM's foreground softmax probability,
                    a model score, **NOT a calibrated confidence.**

Isolation: runs `scripts/research/remotesam_infer.py` inside `.venvs/remotesam`
via subprocess. This module never imports the research repo.
"""

from __future__ import annotations

import json
import tempfile
import time
from pathlib import Path

from ._bridge import REPO_ROOT, bridge_script, run_bridge, sha256, venv_python
from .base import AdapterRequest, NormalizedOutput, RawOutput, SpecialistAdapter
from .errors import AdapterConfigError, AdapterExecutionError, UnsupportedTaskError

_GROUNDING_TASKS = ("grounding", "referring-segmentation", "visual-grounding")


class RemoteSamAdapter(SpecialistAdapter):
    name = "remotesam"
    version = "RemoteSAM@ebb7bc2"
    source_repo = "https://github.com/1e12Leon/RemoteSAM"
    license = "NOT STATED (no LICENSE file in repo or on the HF checkpoint)"
    capabilities = ("grounding", "referring-segmentation")
    modalities = ("optical-single",)

    def __init__(
        self,
        *,
        checkpoint: str,
        repo: str | None = None,
        bert_dir: str | None = None,
        hf_home: str | None = None,
        timeout_s: float = 600.0,
        device: str = "cpu",
        **options,
    ) -> None:
        super().__init__(checkpoint=checkpoint, timeout_s=timeout_s, **options)
        self.checkpoint = Path(checkpoint)
        self.repo = Path(repo or (REPO_ROOT / "external" / "research" / "RemoteSAM"))
        self.bert_dir = bert_dir
        self.hf_home = hf_home or str(REPO_ROOT / "models" / "cache" / "hf_home")
        self.device = device
        self._py = venv_python("remotesam", options.get("venv_python"))
        self._script = bridge_script("remotesam_infer.py", options.get("bridge_script"))

    # --- interface ---

    def validate(self, request: AdapterRequest) -> None:
        task = request.context.get("task", "grounding")
        if task not in _GROUNDING_TASKS:
            raise UnsupportedTaskError(
                f"remotesam supports {self.capabilities}, not {task!r} - no approximation "
                "(it is not a VQA or captioning model)"
            )
        if len(request.images) != 1:
            raise AdapterExecutionError(f"remotesam needs exactly 1 image; got {len(request.images)}")
        if not Path(request.images[0]).exists():
            raise AdapterExecutionError(f"input not found: {request.images[0]}")
        phrase = request.context.get("query") or request.query
        if not phrase or not str(phrase).strip():
            raise AdapterExecutionError("remotesam needs a referring phrase (context['query'] or request.query)")
        if not self.checkpoint.exists():
            raise AdapterConfigError(f"checkpoint not found: {self.checkpoint}")
        if not (self.repo / "tasks" / "code" / "model.py").exists():
            raise AdapterConfigError(f"RemoteSAM repo not found at {self.repo}")

    def execute(self, request: AdapterRequest) -> RawOutput:
        phrase = str(request.context.get("query") or request.query).strip()
        self._staged_mask = tempfile.NamedTemporaryFile(suffix=".png", delete=False).name
        jobs = [{"image": str(request.images[0]), "query": phrase, "mask_out": self._staged_mask}]
        jf = tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w", encoding="utf-8")
        json.dump(jobs, jf)
        jf.close()
        args = [
            "--checkpoint", str(self.checkpoint),
            "--repo", str(self.repo),
            "--jobs-json", jf.name,
            "--device", self.device,
            "--hf-home", self.hf_home,
        ]
        if self.bert_dir:
            args += ["--bert-dir", self.bert_dir]
        payload, runtime = run_bridge(self._py, self._script, args, timeout_s=self.timeout_s)
        Path(jf.name).unlink(missing_ok=True)
        return RawOutput(data=payload, runtime_s=payload.get("load_time_s", runtime))

    def normalize_output(self, raw: RawOutput, request: AdapterRequest) -> NormalizedOutput:
        d = raw.data
        res = (d.get("results") or [{}])[0]
        box = res.get("bbox_xyxy")
        mask_path = res.get("mask_path") if res.get("mask_path") and Path(res["mask_path"]).exists() else None
        return NormalizedOutput(
            answer={
                "bbox_xyxy": box,  # [xmin, ymin, xmax, ymax] in original-image pixels, or None
                "mask_fg_fraction": res.get("mask_fg_fraction"),
                "image_dims": res.get("image_dims"),  # [W, H]
                "grounding_status": res.get("status"),  # ok | no_box | error
            },
            score=res.get("prob_max"),
            artifacts={"mask_path": mask_path, "mask_shape": res.get("mask_shape"),
                       "latency_s": res.get("latency_s")},
            score_meaning=(
                "RemoteSAM foreground softmax probability - a raw model score, "
                "NOT a calibrated confidence"
            ),
        )

    def provenance(self, request, raw, timing):
        prov = super().provenance(request, raw, timing)
        prov.update(
            checkpoint_sha256=sha256(self.checkpoint),
            input_digest=sha256(request.images[0])[:16],
            device=self.device,
            bridge="scripts/research/remotesam_infer.py",
            repo_commit="ebb7bc278c7343c29c8c16b035289f78f40f0f72",
            env=raw.data.get("env", {}),
            note="license NOT STATED upstream; score is a raw model probability",
        )
        return prov
