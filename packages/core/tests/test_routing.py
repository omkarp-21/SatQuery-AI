"""Deterministic router - decision tests. No LLM, no network."""

from __future__ import annotations

import pytest

from satquery_core.routing import RoutingRequest, route

CAPS = ["change-detection", "zero-shot-classification", "retrieval", "embedding"]


def _r(**kw):
    kw.setdefault("available_capabilities", CAPS)
    return route(RoutingRequest(**kw))


def test_temporal_two_images_change_intent():
    d = _r(query_intent="change", image_count=2, modalities=["optical"])
    assert d.code == "TEMPORAL" and d.specialists == ["changeformer"]
    assert "pair-co-registration-assert" in d.required_preprocessing


def test_change_intent_wins_even_with_sar():
    d = _r(query_intent="what changed", image_count=2, modalities=["optical", "sar"])
    assert d.code == "TEMPORAL" and d.specialists == ["changeformer"]


def test_optical_sar_non_change_routes_multimodal():
    # registry-backed (no override) so croma/dofa are visible
    d = route(RoutingRequest(query_intent="classify", image_count=2, modalities=["optical", "sar"]))
    assert d.code == "MULTIMODAL_REPR"
    assert d.specialists and d.specialists[0] in ("croma", "dofa")
    assert "representation-level" in d.reason.lower()


def test_single_image_scene_routes_remoteclip():
    d = _r(query_intent="scene", image_count=1, modalities=["optical"])
    assert d.code == "SINGLE_IMAGE_SCENE" and d.specialists == ["remoteclip"]


def test_single_image_vqa_has_no_specialist():
    d = _r(query_intent="vqa", image_count=1, modalities=["optical"])
    assert d.code == "NO_VQA_SPECIALIST" and d.specialists == []
    assert "EXP-002" in d.reason


def test_invalid_metadata_blocks_routing():
    d = _r(query_intent="change", image_count=2, modalities=["optical"], metadata_valid=False)
    assert d.code == "VALIDATION_FAILED" and d.specialists == []


def test_no_match_is_explicit():
    d = _r(query_intent="teleport", image_count=7, modalities=["optical"])
    assert d.code == "NO_MATCH" and d.specialists == []


def test_decision_is_serializable():
    d = _r(query_intent="scene", image_count=1, modalities=["optical"])
    assert set(d.model_dump()) == {"specialists", "code", "reason",
                                   "required_preprocessing", "execution_order"}
