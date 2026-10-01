"""TinyRS adapter — single-image RS visual question answering.

Upstream: TinyRS (`aybora/TinyRS`, base Qwen2-VL-2B, code Apache-2.0). Reproduced
+ measured 2026-09-02: balanced accuracy **0.87** on 40 RSVQA-LR yes/no questions
(CPU, `.venvs/tinyrs`) — a sanity-scale sample, not a full benchmark
(`docs/research/EXP-002.md`).

Does NOT do: grounding (that is RemoteSAM's job — see `remotesam.py`), captioning
as a first-class task, SAR, temporal. `context["task"]` other than `vqa` /
`question` raises ``UnsupportedTaskError`` — never approximated.

Input:  ``AdapterRequest.images == [image_path]`` (1 RGB image) +
        ``context["question"]`` or ``request.query``.
Output: answer  = {"text": <model answer>, "yesno": 0|1|None}
        score   = None  — the model is greedy-decoded; no calibrated probability.

Isolation: runs `scripts/research/qwen2vl_vqa_infer.py` inside `.venvs/tinyrs`
via subprocess. This module never imports the research repo / model weights.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from ._bridge import bridge_script, run_bridge, sha256, venv_python
from .base import AdapterRequest, NormalizedOutput, RawOutput, SpecialistAdapter
from .errors import AdapterConfigError, AdapterExecutionError, UnsupportedTaskError

_VQA_TASKS = ("vqa", "question", "visual-question-answering")


def _yesno(s: str) -> int | None:
    s = s.strip().lower()
    if s.startswith("yes") or s in ("true", "1"):
        return 1
    if s.startswith("no") or s in ("false", "0"):
        return 0
    return None


class TinyRsAdapter(SpecialistAdapter):
    name = "tinyrs"
    version = "TinyRS@Qwen2-VL-2B"
    source_repo = "https://github.com/aybora/TinyRS"
    license = "Apache-2.0 (code); weights inherit Qwen2-VL-2B terms"
    capabilities = ("vqa",)
    modalities = ("optical-single",)

    def __init__(self, *, weights: str, arch: str = "qwen2_vl",
                 max_new_tokens: int = 24, timeout_s: float = 600.0, **options) -> None:
        super().__init__(checkpoint=weights, timeout_s=timeout_s, **options)
        self.weights = Path(weights)
        self.arch = arch
        self.max_new_tokens = max_new_tokens
        self._py = venv_python("tinyrs", options.get("venv_python"))
        self._script = bridge_script("qwen2vl_vqa_infer.py", options.get("bridge_script"))

    # --- interface ---

    def validate(self, request: AdapterRequest) -> None:
        task = request.context.get("task", "vqa")
        if task not in _VQA_TASKS:
            raise UnsupportedTaskError(
                f"tinyrs supports {self.capabilities} (VQA only), not {task!r} - no approximation. "
                "For grounding use the RemoteSAM specialist."
            )
        if len(request.images) != 1:
            raise AdapterExecutionError(f"tinyrs needs exactly 1 image; got {len(request.images)}")
        if not Path(request.images[0]).exists():
            raise AdapterExecutionError(f"input not found: {request.images[0]}")
        q = request.context.get("question") or request.query
        if not q or not str(q).strip():
            raise AdapterExecutionError("tinyrs needs a question (context['question'] or request.query)")
        if not (self.weights / "config.json").exists():
            raise AdapterConfigError(f"weights not found: {self.weights / 'config.json'}")

    def execute(self, request: AdapterRequest) -> RawOutput:
        q = str(request.context.get("question") or request.query).strip()
        jobs = [{"image": str(request.images[0]), "question": q}]
        jf = tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w", encoding="utf-8")
        json.dump(jobs, jf)
        jf.close()
        args = [
            "--weights", str(self.weights),
            "--jobs-json", jf.name,
            "--arch", self.arch,
            "--max-new-tokens", str(self.max_new_tokens),
        ]
        payload, runtime = run_bridge(self._py, self._script, args, timeout_s=self.timeout_s)
        Path(jf.name).unlink(missing_ok=True)
        return RawOutput(data=payload, runtime_s=payload.get("load_time_s", runtime))

    def normalize_output(self, raw: RawOutput, request: AdapterRequest) -> NormalizedOutput:
        res = (raw.data.get("results") or [{}])[0]
        text = res.get("answer", "")
        return NormalizedOutput(
            answer={"text": text, "yesno": _yesno(text), "status": res.get("status")},
            score=None,
            artifacts={"latency_s": res.get("latency_s")},
            score_meaning="none - the answer is greedy-decoded; no calibrated probability is produced",
        )

    def provenance(self, request, raw, timing):
        prov = super().provenance(request, raw, timing)
        cfg = self.weights / "config.json"
        prov.update(
            checkpoint_sha256=sha256(cfg) if cfg.exists() else None,
            input_digest=sha256(request.images[0])[:16],
            device="cpu",
            bridge="scripts/research/qwen2vl_vqa_infer.py",
            env=raw.data.get("env", {}),
            note="TinyRS (Qwen2-VL-2B base). VQA only - grounding is RemoteSAM. No confidence.",
        )
        return prov
