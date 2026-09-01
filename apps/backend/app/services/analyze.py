"""Unified deterministic analysis layer.

    request (query + images + context)
      -> input validation (GeoTIFF + pair compatibility, safeguards preserved)
      -> deterministic query interpretation (keywords -> intent; NO LLM)
      -> deterministic routing (satquery_core.routing)
      -> specialist execution (scene / change / composed-semantic / joint-repr)
      -> evidence aggregation + verification + provenance aggregation
      -> AnalyzeResult (+ observable routing info)

No unrestricted LLM planning. No confidence value. The multimodal path is
representation-level only (not full optical-SAR reasoning). Single-image VQA has
no specialist and the router says so (NO_VQA_SPECIALIST) - it is never silently
routed to RemoteCLIP.
"""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from satquery_core.routing import RoutingRequest, route
from satquery_evidence import EvidenceItem, VerificationResult
from satquery_geospatial import check_pair_compatibility, read_raster_meta, validate_geotiff

from app.services.failure_aware import ResolutionInfo, derive_resolution
from app.services.multimodal_slice import run_joint_representation
from app.services.scene_slice import run_scene
from app.services.semantic_change_baseline import run_composed_semantic_change
from app.services.temporal_slice import run_change_fallback, run_change_slice

_REPO_ROOT = Path(__file__).resolve().parents[4]
_CF_CKPT = _REPO_ROOT / ("models/cache/changeformer/CD_ChangeFormerV6_LEVIR_b16_lr0.0001_adamw"
                         "_train_test_200_linear_ce_multi_train_True_multi_infer_False_shuffle_AB_False_embed_dim_256")

_CHANGE_KW = ("change", "changed", "difference", "before and after", "bi-temporal", "bitemporal")
_SEMANTIC_KW = ("describe", "what kind", "what type", "semantic", "explain the change", "characteri")
_SCENE_KW = ("scene", "what is this", "classify", "retrieve", "find similar", "land cover", "tag", "identify the")
_VQA_KW = ("how many", "count", "is there", "are there", "where is", "locate", "point to", "?")
_SAR_KW = ("sar", "radar", "sentinel-1", "backscatter", "vv", "vh")


class QueryInterpretation(BaseModel):
    intent: str
    notes: list[str]


def interpret_query(query: str) -> QueryInterpretation:
    """Deterministic keyword -> intent. Order: semantic-change > change > scene > vqa."""
    q = (query or "").strip().lower()
    notes: list[str] = []
    if not q:
        return QueryInterpretation(intent="unknown", notes=["empty query"])
    if any(k in q for k in _SEMANTIC_KW) and any(k in q for k in _CHANGE_KW):
        notes.append("matched semantic-change keywords")
        return QueryInterpretation(intent="semantic-change", notes=notes)
    if any(k in q for k in _CHANGE_KW):
        return QueryInterpretation(intent="change", notes=["matched change keywords"])
    if any(k in q for k in _SCENE_KW):
        return QueryInterpretation(intent="scene", notes=["matched scene/retrieval keywords"])
    if any(k in q for k in _VQA_KW):
        return QueryInterpretation(intent="vqa", notes=["matched VQA-style keywords"])
    return QueryInterpretation(intent="unknown", notes=["no keyword match"])


class RoutingInfo(BaseModel):
    selected_task: str
    selected_specialists: list[str]
    routing_code: str
    routing_rule: str
    required_inputs: list[str]
    execution_order: list[str]
    status: str


class AnalyzeResult(BaseModel):
    ok: bool
    query: str
    interpretation: QueryInterpretation
    routing: RoutingInfo
    metadata_valid: bool
    validation_errors: list[str] = []
    result: dict[str, Any] | None = None  # the sub-service's structured output
    evidence: list[EvidenceItem] = []
    verification: VerificationResult | None = None
    resolution: ResolutionInfo | None = None  # failure-aware post-execution qualifier (G8)
    provenance: dict[str, Any] = {}
    errors: list[str] = []


def _modalities_from(paths: list[Path], context: dict[str, Any]) -> list[str]:
    if context.get("modalities"):
        return [m.lower() for m in context["modalities"]]
    mods: set[str] = set()
    for p in paths:
        if p.suffix.lower() in (".tif", ".tiff"):
            try:
                bc = read_raster_meta(p).count
                mods.add("sar" if bc == 2 else "optical")
            except Exception:  # noqa: BLE001
                mods.add("optical")
        else:
            mods.add("optical")
    return sorted(mods)


def run_analyze(
    query: str,
    image_paths: list[str | Path],
    context: dict[str, Any] | None = None,
) -> AnalyzeResult:
    ctx = context or {}
    started = time.time()
    paths = [Path(p) for p in image_paths]
    interp = interpret_query(query)

    # --- input validation (safeguards preserved) ---
    val_errors: list[str] = []
    for p in paths:
        if not p.exists():
            val_errors.append(f"input not found: {p}")
        elif p.suffix.lower() in (".tif", ".tiff"):
            v = validate_geotiff(p)
            if not v.ok:
                val_errors.append(f"{p.name}: validation failed ({[c.name for c in v.failed()]})")
    pair_ok = None
    if len(paths) == 2 and not val_errors:
        try:
            pair = check_pair_compatibility(read_raster_meta(paths[0]), read_raster_meta(paths[1]))
            pair_ok = pair.co_registered
            if not pair.co_registered:
                val_errors.append(f"pair not co-registered: {pair.mismatches}")
        except Exception as exc:  # noqa: BLE001
            val_errors.append(f"pair check error: {type(exc).__name__}")
    metadata_valid = not val_errors

    modalities = _modalities_from(paths, ctx) if not val_errors else []
    rr = RoutingRequest(
        query_intent=("semantic-change" if interp.intent == "semantic-change" else interp.intent),
        image_count=len(paths),
        modalities=modalities,
        metadata_valid=metadata_valid,
    )
    # a semantic-change intent still routes TEMPORAL (change-detection is the substrate)
    routing_intent = "change" if interp.intent == "semantic-change" else interp.intent
    decision = route(RoutingRequest(query_intent=routing_intent, image_count=len(paths),
                                    modalities=modalities, metadata_valid=metadata_valid))

    info = RoutingInfo(
        selected_task=interp.intent,
        selected_specialists=decision.specialists,
        routing_code=decision.code,
        routing_rule=decision.reason,
        required_inputs=decision.required_preprocessing,
        execution_order=decision.execution_order,
        status=("blocked" if decision.code in ("VALIDATION_FAILED", "NO_VQA_SPECIALIST", "NO_MATCH")
                else "routed"),
    )

    base = dict(ok=False, query=query, interpretation=interp, routing=info,
                metadata_valid=metadata_valid, validation_errors=val_errors)

    if decision.code == "VALIDATION_FAILED":
        return AnalyzeResult(**base, errors=val_errors or ["metadata validation failed"])
    if decision.code == "NO_VQA_SPECIALIST":
        return AnalyzeResult(**base, errors=[decision.reason])
    if decision.code == "NO_MATCH":
        return AnalyzeResult(**base, errors=[decision.reason])

    # --- dispatch ---
    sem_vr = None
    fallback_used: str | None = None
    try:
        if decision.code == "SINGLE_IMAGE_SCENE":
            prompts = ctx.get("prompts") or ["urban area", "farmland", "forest", "water body",
                                             "bare land", "industrial area"]
            sub = run_scene(paths[0], prompts)
            payload, ev, vr, prov = sub.model_dump(), sub.evidence, sub.verification, sub.provenance
        elif decision.code == "TEMPORAL" and interp.intent == "semantic-change":
            sub = run_composed_semantic_change(paths[0], paths[1], checkpoint_dir=_CF_CKPT)
            payload, ev, vr, prov = sub.model_dump(), sub.evidence, sub.verification, sub.provenance
            sem_vr = sub.semantic_verification
        elif decision.code == "TEMPORAL":
            sub = run_change_slice(paths[0], paths[1], checkpoint_dir=_CF_CKPT, strict=True)
            # failure-aware single-step fallback: the pair is already co-registered
            # here (mis-registration is caught earlier as VALIDATION_FAILED), so any
            # failure of run_change_slice means the ChangeFormer env is unavailable.
            if not sub.ok:
                fb = run_change_fallback(paths[0], paths[1])
                if fb.ok:
                    sub, fallback_used = fb, "image_difference_fallback"
            payload, ev, vr, prov = sub.model_dump(), sub.evidence, sub.verification, sub.provenance
        elif decision.code == "MULTIMODAL_REPR":
            opt = next((p for p in paths if p.suffix.lower() in (".npy",)), paths[0])
            sar = paths[1] if len(paths) > 1 else paths[0]
            model = decision.specialists[0] if decision.specialists else "croma"
            sub = run_joint_representation(opt, sar, model=model)  # representation-level
            payload, ev, vr, prov = sub.model_dump(), sub.evidence, sub.verification, sub.provenance
        else:
            return AnalyzeResult(**base, errors=[f"unhandled routing code {decision.code}"])
    except Exception as exc:  # noqa: BLE001 - sanitized
        return AnalyzeResult(**base, errors=[f"specialist execution failed: {type(exc).__name__}"])

    resolution = derive_resolution(
        sub_ok=bool(payload.get("ok", True)), verification=vr,
        semantic_verification=sem_vr, fallback_used=fallback_used,
    )

    agg_prov = {
        "layer": "analyze",
        "interpretation": interp.model_dump(),
        "routing": info.model_dump(),
        "pair_co_registered": pair_ok,
        "resolution": resolution.model_dump(),
        "sub_service_provenance": prov,
        "orchestration_runtime_s": round(time.time() - started, 3),
        "note": ("multimodal path is representation-level only; VQA has no specialist; "
                 "no confidence value is produced; `resolution` is a deterministic "
                 "failure-aware qualifier, not a confidence"),
    }
    return AnalyzeResult(
        ok=bool(payload.get("ok", True)),
        query=query, interpretation=interp, routing=info,
        metadata_valid=metadata_valid, validation_errors=val_errors,
        result=payload, evidence=list(ev), verification=vr, resolution=resolution,
        provenance=agg_prov,
        errors=list(payload.get("errors", []) or []),
    )
