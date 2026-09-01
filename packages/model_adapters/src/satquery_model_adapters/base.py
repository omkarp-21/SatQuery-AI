"""Standard SpecialistAdapter interface.

Every research model SatQuery uses is reached through a subclass of
:class:`SpecialistAdapter`. Product code never imports research-repo internals —
each adapter's :meth:`execute` shells out to an isolated per-model environment
(`.venvs/<model>` + a bridge script in `scripts/research/`) with an explicit
argument list and a timeout (`.claude/rules/ai-models.md`, `.claude/rules/security.md`).

The template method is :meth:`run`:

    validate -> execute -> normalize_output -> (+ provenance) -> AdapterResult

Each adapter declares, as class attributes, the facts the registry needs:
``name``, ``version``, ``source_repo``, ``license``, ``capabilities`` (tasks),
``modalities``. An adapter never claims a capability the upstream model lacks; an
unsupported request raises a typed error, it is not approximated.
"""

from __future__ import annotations

import abc
import time
from dataclasses import dataclass, field
from typing import Any

from .errors import AdapterExecutionError


@dataclass
class AdapterRequest:
    """Normalized input handed to an adapter."""

    query: str = ""
    images: list[str] = field(default_factory=list)  # file paths
    context: dict[str, Any] = field(default_factory=dict)  # task, modality, params, artifact_dir


@dataclass
class RawOutput:
    """Whatever the model's bridge returned (JSON dict) + timing/meta."""

    data: dict[str, Any]
    runtime_s: float | None = None
    stderr_tail: str = ""


@dataclass
class NormalizedOutput:
    """Adapter output in the shared schema, consumed by fusion / evidence."""

    answer: Any
    score: float | None = None
    artifacts: dict[str, Any] = field(default_factory=dict)
    score_meaning: str = "unspecified"


@dataclass
class AdapterResult:
    """Final result: structured output + provenance + status + timing + model metadata."""

    model: str
    answer: Any
    score: float | None = None
    artifacts: dict[str, Any] = field(default_factory=dict)
    provenance: dict[str, Any] = field(default_factory=dict)
    status: str = "ok"  # ok | degraded | error
    timing_s: float | None = None
    model_meta: dict[str, Any] = field(default_factory=dict)  # name/version/license/caps/modalities


class SpecialistAdapter(abc.ABC):
    """Base class for all specialist adapters."""

    # --- registry facts (override in subclasses) ---
    name: str = "base"
    version: str = "0"
    source_repo: str = ""
    license: str = "unknown"
    capabilities: tuple[str, ...] = ()  # supported tasks
    modalities: tuple[str, ...] = ()

    def __init__(self, *, checkpoint: str, timeout_s: float = 300.0, **options: Any) -> None:
        self.checkpoint = checkpoint
        self.timeout_s = timeout_s
        self.options = options

    # --- the four required methods ---

    @abc.abstractmethod
    def validate(self, request: AdapterRequest) -> None:
        """Raise a typed error if this model cannot serve ``request``. No approximation."""

    @abc.abstractmethod
    def execute(self, request: AdapterRequest) -> RawOutput:
        """Run inference in the isolated env; return the raw per-model output."""

    @abc.abstractmethod
    def normalize_output(self, raw: RawOutput, request: AdapterRequest) -> NormalizedOutput:
        """Map raw output to the shared :class:`NormalizedOutput` schema."""

    def provenance(self, request: AdapterRequest, raw: RawOutput, timing: dict[str, float]) -> dict[str, Any]:
        """Standard provenance block. Subclasses call ``super().provenance(...)`` and extend."""
        return {
            "model": self.name,
            "version": self.version,
            "source_repo": self.source_repo,
            "license": self.license,
            "checkpoint": str(self.checkpoint),
            "capabilities": list(self.capabilities),
            "modalities": list(self.modalities),
            "runtime_s": raw.runtime_s if raw.runtime_s is not None else timing.get("total_s"),
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }

    # --- template method: orchestrator entrypoint ---

    def run(self, request: AdapterRequest) -> AdapterResult:
        self.validate(request)
        t0 = time.time()
        raw = self.execute(request)
        norm = self.normalize_output(raw, request)
        total_s = round(time.time() - t0, 3)
        prov = self.provenance(request, raw, {"total_s": total_s})
        prov.setdefault("score_meaning", norm.score_meaning)
        return AdapterResult(
            model=self.name,
            answer=norm.answer,
            score=norm.score,
            artifacts=norm.artifacts,
            provenance=prov,
            status="ok",
            timing_s=raw.runtime_s if raw.runtime_s is not None else total_s,
            model_meta=self.describe(),
        )

    # backward-compatible alias
    def predict(self, request: AdapterRequest) -> AdapterResult:
        return self.run(request)

    def describe(self) -> dict[str, Any]:
        """Registry-facing description (facts only)."""
        return {
            "name": self.name,
            "version": self.version,
            "source_repo": self.source_repo,
            "license": self.license,
            "capabilities": list(self.capabilities),
            "modalities": list(self.modalities),
        }


# Back-compat alias for not-yet-rewritten stubs (geochat / change_agent / changechat).
ModelAdapter = SpecialistAdapter


def parse_bridge_json(returncode: int, out_json_exists: bool, payload: dict | None, stderr: str) -> dict:
    """Shared helper: turn a bridge subprocess result into a checked dict or raise."""
    if not out_json_exists or payload is None:
        raise AdapterExecutionError(f"bridge produced no output (rc={returncode}): {stderr[-800:]}")
    if not payload.get("ok"):
        raise AdapterExecutionError(f"bridge reported failure: {payload.get('error')}")
    return payload
