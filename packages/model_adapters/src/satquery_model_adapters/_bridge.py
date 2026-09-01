"""Shared subprocess plumbing for adapters that run in an isolated research venv.

Product code. Does NOT import any research repo — it only spawns a bridge script
(in `scripts/research/`) inside `.venvs/<model>/` with an explicit arg list.
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

from .errors import AdapterConfigError, AdapterExecutionError

REPO_ROOT = Path(__file__).resolve().parents[4]


def venv_python(model: str, override: str | None = None) -> Path:
    env = os.environ.get(f"SATQUERY_{model.upper()}_VENV_PYTHON")
    p = Path(override or env or (REPO_ROOT / ".venvs" / model / "Scripts" / "python.exe"))
    return p


def bridge_script(filename: str, override: str | None = None) -> Path:
    return Path(override or (REPO_ROOT / "scripts" / "research" / filename))


def sha256(path: str | Path, cap: int = 64 * 1024 * 1024) -> str:
    h = hashlib.sha256()
    read = 0
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
            read += len(chunk)
            if read >= cap:
                h.update(b"[capped]")
                break
    return h.hexdigest()


def run_bridge(
    py: Path,
    script: Path,
    args: list[str],
    *,
    timeout_s: float,
    writes_json_arg: str = "--out-json",
) -> tuple[dict[str, Any], float]:
    """Spawn ``py script *args --out-json <tmp>`` and return (payload, runtime_s)."""
    if not py.exists():
        raise AdapterConfigError(f"isolated env python not found: {py}")
    if not script.exists():
        raise AdapterConfigError(f"bridge script not found: {script}")

    with tempfile.TemporaryDirectory() as td:
        out_json = Path(td) / "out.json"
        cmd = [str(py), str(script), *args, writes_json_arg, str(out_json)]
        t0 = time.time()
        try:
            proc = subprocess.run(
                cmd, capture_output=True, text=True, timeout=timeout_s, check=False
            )
        except subprocess.TimeoutExpired as exc:
            raise AdapterExecutionError(f"{script.name} timed out after {timeout_s}s") from exc
        runtime = round(time.time() - t0, 3)

        if not out_json.exists():
            raise AdapterExecutionError(
                f"{script.name} produced no JSON (rc={proc.returncode}): {proc.stderr[-800:]}"
            )
        payload = json.loads(out_json.read_text())
        if not payload.get("ok"):
            raise AdapterExecutionError(f"{script.name} failed: {payload.get('error')}")
        # copy any artifact the bridge wrote into the temp dir to a stable place
        return payload, runtime
