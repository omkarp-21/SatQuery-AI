"""Constrained deterministic router (first version - NOT an LLM agent).

Given a typed :class:`RoutingRequest` (intent + image count + modalities +
metadata validity + available capabilities), return a :class:`RoutingDecision`
naming the specialist(s), a machine ``code``, the required preprocessing, and the
execution order.

No LLM, no hidden fallbacks. If nothing matches, the decision says so with a code
the caller can explain. Routing reads model capabilities from the registry YAML
(data, not a code import) so it never hardcodes model names beyond the mapping
table here, which is itself derived from registered capabilities.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field

_DEFAULT_REGISTRY = (
    Path(__file__).resolve().parents[5]
    / "packages" / "model_adapters" / "model_registry.yaml"
)

RoutingCode = Literal[
    "TEMPORAL",
    "MULTIMODAL_REPR",
    "SINGLE_IMAGE_SCENE",
    "SINGLE_IMAGE_GROUNDING",
    "SINGLE_IMAGE_VQA",
    "NO_VQA_SPECIALIST",
    "VALIDATION_FAILED",
    "NO_MATCH",
]

SCENE_INTENTS = {"scene", "scene-description", "retrieval", "classify", "classification",
                 "zero-shot", "tag", "tagging", "what-is-this-scene"}
# grounding = "point me at the region the phrase refers to" -> RemoteSAM specialist
GROUNDING_INTENTS = {"grounding", "grounding-query", "refer", "referring", "referring-segmentation",
                     "locate", "where-is", "point-to", "find-the", "segment"}
# VQA = an open-ended question about the image -> no integrated specialist yet
VQA_INTENTS = {"vqa", "question", "count", "describe-object", "how-many", "is-there"}
CHANGE_INTENTS = {"change", "change-detection", "what-changed", "bitemporal"}


class RoutingRequest(BaseModel):
    query_intent: str = Field(description="normalized intent keyword")
    image_count: int = Field(ge=0)
    modalities: list[str] = Field(default_factory=list, description="e.g. ['optical'], ['optical','sar']")
    metadata_valid: bool = True
    available_capabilities: list[str] | None = Field(
        default=None, description="override; else read from the registry"
    )


class RoutingDecision(BaseModel):
    specialists: list[str]
    code: RoutingCode
    reason: str
    required_preprocessing: list[str] = Field(default_factory=list)
    execution_order: list[str] = Field(default_factory=list)


def _registry_caps(registry_path: str | Path | None) -> dict[str, list[str]]:
    p = Path(registry_path) if registry_path else _DEFAULT_REGISTRY
    if not p.exists():
        return {}
    data: dict[str, Any] = yaml.safe_load(p.read_text()) or {}
    return {name: list(m.get("capabilities", [])) for name, m in (data.get("models") or {}).items()}


def route(req: RoutingRequest, *, registry_path: str | Path | None = None) -> RoutingDecision:
    caps = {c for caps_list in _registry_caps(registry_path).values() for c in caps_list}
    if req.available_capabilities is not None:
        caps = set(req.available_capabilities)

    intent = req.query_intent.strip().lower().replace(" ", "-").replace("_", "-")

    # 1. metadata gate
    if not req.metadata_valid:
        return RoutingDecision(
            specialists=[], code="VALIDATION_FAILED",
            reason="input metadata / geospatial validation failed - nothing is routed",
        )

    has_sar = "sar" in [m.lower() for m in req.modalities]
    has_optical = any(m.lower() in ("optical", "multispectral", "rgb") for m in req.modalities)

    # 2. bi-temporal change - a change intent wins even if SAR is also supplied
    #    (SAR then serves as supporting evidence, not the primary route).
    if req.image_count == 2 and intent in CHANGE_INTENTS and "change-detection" in caps:
        return RoutingDecision(
            specialists=["changeformer"], code="TEMPORAL",
            reason="two images + a change intent -> the bi-temporal change specialist",
            required_preprocessing=["geotiff-validate", "pair-co-registration-assert"],
            execution_order=["changeformer"],
        )

    # 3. paired optical + SAR (non-change intent) -> joint representation
    if req.image_count == 2 and has_sar and has_optical:
        for m in ("croma", "dofa"):
            if m in _registry_caps(registry_path):
                return RoutingDecision(
                    specialists=[m], code="MULTIMODAL_REPR",
                    reason="paired optical + SAR -> joint representation encoder "
                           "(representation-level; NOT full optical-SAR reasoning yet)",
                    required_preprocessing=["geotiff-validate", "s1-db-scale", "s2-12band-select",
                                            "channel-normalize", "resample-120"],
                    execution_order=[m],
                )

    # 4. single image scene / retrieval / zero-shot
    if req.image_count == 1 and (intent in SCENE_INTENTS):
        if {"zero-shot-classification", "retrieval"} & caps:
            return RoutingDecision(
                specialists=["remoteclip"], code="SINGLE_IMAGE_SCENE",
                reason="one image + a scene/retrieval intent -> the RS embedding specialist",
                required_preprocessing=["image-open-check"],
                execution_order=["remoteclip"],
            )

    # 4b. single image + a grounding intent -> the grounding specialist (RemoteSAM)
    if req.image_count == 1 and intent in GROUNDING_INTENTS and "grounding" in caps:
        return RoutingDecision(
            specialists=["remotesam"], code="SINGLE_IMAGE_GROUNDING",
            reason="one image + a grounding intent -> the RS grounding specialist "
                   "(text -> box + mask; RemoteSAM). NOT a VQA model.",
            required_preprocessing=["image-open-check"],
            execution_order=["remotesam"],
        )

    # 5. single image + a VQA intent -> the VQA specialist (TinyRS)
    if req.image_count == 1 and intent in VQA_INTENTS:
        if "vqa" in caps:
            return RoutingDecision(
                specialists=["tinyrs"], code="SINGLE_IMAGE_VQA",
                reason="one image + a VQA intent -> the RS VQA specialist (TinyRS, "
                       "Qwen2-VL-2B base). NOT a grounding model - grounding is RemoteSAM.",
                required_preprocessing=["image-open-check"],
                execution_order=["tinyrs"],
            )
        return RoutingDecision(
            specialists=[], code="NO_VQA_SPECIALIST",
            reason="single-image VQA has NO integrated specialist in the registry. "
                   "Do not route RemoteCLIP or RemoteSAM as a VQA model.",
        )

    return RoutingDecision(
        specialists=[], code="NO_MATCH",
        reason=f"no rule matched (intent={intent!r}, images={req.image_count}, modalities={req.modalities})",
    )
