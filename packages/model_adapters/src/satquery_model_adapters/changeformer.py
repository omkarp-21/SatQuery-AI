"""ChangeFormer adapter — bi-temporal binary change **mask**.

What the upstream model does: given two co-registered RGB rasters (T1, T2), it
predicts a per-pixel binary change mask (ChangeFormerV6, `wgcban/ChangeFormer`,
MIT). Validated in `docs/research/runtime_validation.md` (IoU 0.83 / F1 0.91 on 7
bundled LEVIR-CD samples — a sanity check, not a benchmark).

What it does NOT do: no semantic change classes, no captions, no VQA, no SAR.
Requests for those raise ``UnsupportedTaskError`` — they are never approximated.

Expected input: `AdapterRequest.images == [t1_path, t2_path]` (files readable as
RGB; identical pixel dimensions). Co-registration is the caller's responsibility
(see `satquery_geospatial.check_pair_compatibility`).

Output schema: ``AdapterResult`` with
    answer    = {"changed_fraction": float, "changed_pixels": int, "total_pixels": int}
    artifacts = {"mask_path": str | None, "height": int, "width": int}
    score     = changed_fraction (0..1) — a coverage ratio, **not** a confidence.
    provenance = {model, version, checkpoint_dir, checkpoint_sha256, input_digest,
                  device, runtime_s, bridge, timestamp}

Confidence behaviour: this adapter reports **no calibrated confidence**. `score`
is the fraction of pixels flagged changed. Do not present it as "confidence"
(`.claude/rules/ai-models.md`).

GPU requirements: none — runs CPU (~0.8 s / 256² pair). ~1 GB RAM.

Isolation: inference runs in the `.venvs/changeformer` research env via
`scripts/research/changeformer_infer.py`, invoked by subprocess with an explicit
argument list + timeout. This product module never imports the research repo.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any

from .base import AdapterRequest, AdapterResult, ModelAdapter
from .errors import AdapterConfigError, AdapterExecutionError, UnsupportedTaskError

_REPO_ROOT = Path(__file__).resolve().parents[4]
_DEFAULT_BRIDGE = _REPO_ROOT / "scripts" / "research" / "changeformer_infer.py"
_DEFAULT_VENV_PY = _REPO_ROOT / ".venvs" / "changeformer" / "Scripts" / "python.exe"


def _sha256(path: Path, cap: int = 64 * 1024 * 1024) -> str:
    h = hashlib.sha256()
    read = 0
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
            read += len(chunk)
            if read >= cap:  # cap for very large checkpoints — digest is a fingerprint
                h.update(b"[capped]")
                break
    return h.hexdigest()


class ChangeFormerAdapter(ModelAdapter):
    name = "changeformer"
    version = "ChangeFormerV6@afd1b7e"
    tasks = ("change-detection",)
    modalities = ("optical-bitemporal",)

    def __init__(
        self,
        checkpoint: str,
        device: str = "cpu",
        *,
        venv_python: str | None = None,
        bridge_script: str | None = None,
        timeout_s: float = 300.0,
        **kwargs: Any,
    ) -> None:
        super().__init__(checkpoint=checkpoint, device=device, **kwargs)
        self.checkpoint_dir = Path(checkpoint)
        self.venv_python = Path(
            venv_python or os.environ.get("SATQUERY_CHANGEFORMER_VENV_PYTHON") or _DEFAULT_VENV_PY
        )
        self.bridge_script = Path(bridge_script or os.environ.get("SATQUERY_CHANGEFORMER_BRIDGE") or _DEFAULT_BRIDGE)
        self.timeout_s = timeout_s

    def load(self) -> None:
        """Verify the isolated env + checkpoint are present. Weights load in the subprocess."""
        if not self.venv_python.exists():
            raise AdapterConfigError(f"changeformer venv python not found: {self.venv_python}")
        if not self.bridge_script.exists():
            raise AdapterConfigError(f"bridge script not found: {self.bridge_script}")
        ckpt = self.checkpoint_dir / "best_ckpt.pt"
        if not ckpt.exists():
            raise AdapterConfigError(f"checkpoint not found: {ckpt}")
        self._model = "verified"

    def predict(self, request: AdapterRequest) -> AdapterResult:
        task = request.context.get("task", "change-detection")
        if task not in self.tasks:
            raise UnsupportedTaskError(
                f"changeformer supports {self.tasks}, not {task!r} — no approximation"
            )
        if len(request.images) != 2:
            raise AdapterExecutionError(
                f"changeformer needs exactly 2 images (T1, T2); got {len(request.images)}"
            )
        self.load()
        t1, t2 = (Path(request.images[0]), Path(request.images[1]))
        for p in (t1, t2):
            if not p.exists():
                raise AdapterExecutionError(f"input not found: {p}")

        with tempfile.TemporaryDirectory() as td:
            out_json = Path(td) / "result.json"
            out_mask = Path(td) / "mask.png"
            cmd = [
                str(self.venv_python),
                str(self.bridge_script),
                "--a", str(t1),
                "--b", str(t2),
                "--checkpoint-dir", str(self.checkpoint_dir),
                "--out-json", str(out_json),
                "--out-mask", str(out_mask),
            ]
            t0 = time.time()
            try:
                proc = subprocess.run(
                    cmd, capture_output=True, text=True, timeout=self.timeout_s, check=False
                )
            except subprocess.TimeoutExpired as exc:
                raise AdapterExecutionError(f"changeformer timed out after {self.timeout_s}s") from exc

            if not out_json.exists():
                raise AdapterExecutionError(
                    f"bridge produced no output (rc={proc.returncode}): {proc.stderr[-800:]}"
                )
            data = json.loads(out_json.read_text())
            if not data.get("ok"):
                raise AdapterExecutionError(f"changeformer failed: {data.get('error')}")

            # The temp dir vanishes when this block exits — copy the mask somewhere stable.
            persisted_mask: str | None = None
            if out_mask.exists():
                persisted_mask = _persist_mask(out_mask, request.context.get("artifact_dir"))

            elapsed = round(time.time() - t0, 3)
            ckpt = self.checkpoint_dir / "best_ckpt.pt"
            return AdapterResult(
                model=self.name,
                answer={
                    "changed_fraction": data["changed_fraction"],
                    "changed_pixels": data["changed_pixels"],
                    "total_pixels": data["total_pixels"],
                },
                score=data["changed_fraction"],  # coverage ratio, NOT confidence
                artifacts={
                    "mask_path": persisted_mask,
                    "height": data["height"],
                    "width": data["width"],
                },
                provenance={
                    "model": self.name,
                    "version": self.version,
                    "checkpoint_dir": str(self.checkpoint_dir),
                    "checkpoint_sha256": _sha256(ckpt),
                    "input_digest": _sha256(t1)[:16] + ":" + _sha256(t2)[:16],
                    "device": "cpu",
                    "runtime_s": data.get("runtime_s", elapsed),
                    "bridge": str(self.bridge_script.relative_to(_REPO_ROOT)),
                    "python": str(self.venv_python),
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "score_meaning": "fraction of pixels flagged changed — not a confidence",
                },
            )


def _persist_mask(src: Path, artifact_dir: str | None) -> str:
    """Copy the mask out of the (about-to-vanish) temp dir into a stable location."""
    import shutil

    dest_dir = Path(artifact_dir) if artifact_dir else Path(tempfile.mkdtemp(prefix="satquery_cf_"))
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"changeformer_mask_{int(time.time()*1000)}.png"
    shutil.copyfile(src, dest)
    return str(dest)
