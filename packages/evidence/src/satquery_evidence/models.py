"""Evidence + provenance data models (first version).

`EvidenceItem` makes one claim inspectable. **Evidence is not confidence** - there
is no numeric confidence field here, by design (`.claude/rules/ai-models.md`).

`Provenance` standardizes the audit block every specialist result carries.
"""

from __future__ import annotations

import time
import uuid
from typing import Any, Literal

from pydantic import BaseModel, Field

EvidenceType = Literal[
    "change-mask", "embedding", "ranking", "grounding", "metadata", "statistic", "citation"
]
EvidenceStatus = Literal["ok", "degraded", "error"]


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def new_evidence_id(prefix: str = "ev") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


class EvidenceItem(BaseModel):
    """One inspectable piece of support for a claim."""

    evidence_id: str = Field(default_factory=new_evidence_id)
    source_model: str
    task: str
    modality: str
    source_artifact: str | None = Field(default=None, description="path / id of the input(s) or output artifact")
    spatial_region: dict[str, Any] | None = Field(default=None, description="bbox or GeoJSON-like, if known")
    temporal_context: dict[str, Any] | None = Field(default=None, description="e.g. {t1, t2, relation}")
    claim_supported: str = Field(description="the specific claim this item supports")
    evidence_type: EvidenceType
    payload: dict[str, Any] = Field(default_factory=dict, description="the concrete evidence content")
    provenance: dict[str, Any] = Field(default_factory=dict)
    timestamp: str = Field(default_factory=_now)
    status: EvidenceStatus = "ok"


_SECRET_HINTS = ("key", "token", "secret", "password", "credential", "authorization")


def scrub(d: dict[str, Any]) -> dict[str, Any]:
    """Drop keys that look like secrets before persisting a provenance record."""
    out: dict[str, Any] = {}
    for k, v in d.items():
        if any(h in k.lower() for h in _SECRET_HINTS):
            out[k] = "[scrubbed]"
        elif isinstance(v, dict):
            out[k] = scrub(v)
        else:
            out[k] = v
    return out


class Provenance(BaseModel):
    """Standard audit block. Built from an adapter's raw provenance dict + context."""

    model: str
    version: str | None = None
    checkpoint: str | None = None
    checkpoint_sha256: str | None = None
    input_ids: list[str] = Field(default_factory=list)
    task: str | None = None
    parameters: dict[str, Any] = Field(default_factory=dict)
    preprocessing: list[str] = Field(default_factory=list)
    environment: str | None = None
    device: str | None = None
    execution_time_s: float | None = None
    timestamp: str = Field(default_factory=_now)
    status: Literal["ok", "error", "degraded"] = "ok"

    @classmethod
    def from_adapter(
        cls,
        adapter_prov: dict[str, Any],
        *,
        task: str | None = None,
        input_ids: list[str] | None = None,
        preprocessing: list[str] | None = None,
        parameters: dict[str, Any] | None = None,
    ) -> "Provenance":
        p = scrub(adapter_prov)
        return cls(
            model=p.get("model", "unknown"),
            version=p.get("version"),
            checkpoint=p.get("checkpoint"),
            checkpoint_sha256=p.get("checkpoint_sha256"),
            input_ids=input_ids or [],
            task=task,
            parameters=parameters or {},
            preprocessing=preprocessing or [],
            environment=p.get("environment") or p.get("python"),
            device=p.get("device"),
            execution_time_s=p.get("runtime_s"),
        )
