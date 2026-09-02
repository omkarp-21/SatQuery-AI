"""Bounded structured agent memory (G14).

Stores only references and small facts — never raw images or embedding vectors.
The executor writes to it after every step; the finalizer reads from it to build
the report. Nothing here is fed verbatim into a prompt.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


def _is_big(v: Any) -> bool:
    """True for values too large to keep in bounded memory (arrays, long lists/strings)."""
    if isinstance(v, (list, tuple)):
        return len(v) > 64
    if isinstance(v, str):
        return len(v) > 4000
    if isinstance(v, dict):
        return len(v) > 64
    return False


class RegionRef(BaseModel):
    region_id: int
    bbox_pixel: list[int]
    bbox_lonlat: list[float] | None = None
    area_ha: float | None = None
    label: str | None = None
    source_step: str


class AgentMemory(BaseModel):
    goal: str = ""
    image_ids: list[str] = Field(default_factory=list)
    image_paths: dict[str, str] = Field(default_factory=dict)  # id -> path
    crs: str | None = None
    geospatial_available: bool = False
    pair_co_registered: bool | None = None

    # per-step outputs kept by reference (the full dict lives in `results`)
    results: dict[str, dict[str, Any]] = Field(default_factory=dict)  # step_id -> normalized payload
    regions: list[RegionRef] = Field(default_factory=list)
    masks: dict[str, str] = Field(default_factory=dict)   # step_id -> mask path
    labels: dict[str, list[Any]] = Field(default_factory=dict)  # step_id -> ranking
    numeric: dict[str, float] = Field(default_factory=dict)  # e.g. changed_fraction

    evidence: list[dict[str, Any]] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    verification_statuses: list[str] = Field(default_factory=list)
    failures: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    models_used: list[str] = Field(default_factory=list)

    def note_model(self, name: str | None) -> None:
        if name and name not in self.models_used:
            self.models_used.append(name)

    def add_evidence(self, items: list[dict[str, Any]]) -> None:
        for it in items or []:
            self.evidence.append(it)
            eid = it.get("evidence_id")
            if eid and eid not in self.evidence_ids:
                self.evidence_ids.append(eid)

    def record_result(self, step_id: str, payload: dict[str, Any]) -> None:
        # keep a trimmed copy — drop anything large / array-ish
        trimmed = {
            k: v for k, v in payload.items()
            if k not in ("representation", "evidence") and not _is_big(v)
        }
        self.results[step_id] = trimmed
