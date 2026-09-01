"""EvidenceItem + Provenance + deterministic verifier."""

from __future__ import annotations

from satquery_evidence import EvidenceItem, Provenance, new_evidence_id, scrub, verify


def _mask_ev(**over):
    payload = {"mask_path": "/tmp/m.png", "changed_fraction": 0.25}
    payload.update(over.pop("payload", {}))
    return EvidenceItem(
        source_model="changeformer", task="change-detection", modality="optical-bitemporal",
        claim_supported="pixels changed", evidence_type="change-mask", payload=payload, **over,
    )


def test_evidence_item_defaults_and_no_confidence_field():
    ev = _mask_ev()
    assert ev.evidence_id.startswith("ev_")
    assert ev.status == "ok"
    assert "confidence" not in ev.model_dump()  # by design


def test_new_evidence_id_unique():
    assert new_evidence_id() != new_evidence_id()


def test_provenance_from_adapter_scrubs_secrets():
    raw = {"model": "x", "version": "1", "api_key": "sk-SECRET", "device": "cpu",
           "nested": {"auth_token": "abc"}, "runtime_s": 1.2}
    p = Provenance.from_adapter(raw, task="t", input_ids=["a"])
    d = p.model_dump()
    assert d["model"] == "x" and d["execution_time_s"] == 1.2 and d["task"] == "t"
    # scrub() is applied to the raw dict; secret-looking keys are masked
    s = scrub(raw)
    assert s["api_key"] == "[scrubbed]" and s["nested"]["auth_token"] == "[scrubbed]"


def test_verify_supported_when_all_checks_pass():
    vr = verify({"changed_fraction": 0.25}, [_mask_ev()], {"pair_co_registered": True})
    assert vr.status == "SUPPORTED"
    assert {"geospatial_compatibility"} <= {c.name for c in vr.checks}


def test_verify_contradicted_on_bad_range():
    vr = verify({}, [_mask_ev(payload={"changed_fraction": 1.9})], {"pair_co_registered": True})
    assert vr.status == "CONTRADICTED"
    assert any("changed_fraction_range" in c.name and not c.passed for c in vr.checks)


def test_verify_contradicted_when_pair_not_coregistered():
    vr = verify({}, [_mask_ev()], {"pair_co_registered": False})
    assert vr.status == "CONTRADICTED"


def test_verify_insufficient_when_nothing_to_check():
    vr = verify({}, [], {})
    assert vr.status == "INSUFFICIENT_EVIDENCE"


def test_verify_modality_check():
    ev = EvidenceItem(source_model="remoteclip", task="zero-shot-classification",
                      modality="optical-single", claim_supported="c", evidence_type="ranking",
                      payload={"ranking": [["a", 0.9], ["b", 0.1]]})
    vr = verify({}, [ev], {"requested_modality": "sar-single",
                           "model_modalities": ["optical-single"]})
    assert vr.status == "CONTRADICTED"
    assert any(c.name == "modality_supported" and not c.passed for c in vr.checks)


def test_verify_notes_are_explicit_about_scope():
    vr = verify({}, [_mask_ev()], {"pair_co_registered": True})
    assert "not a semantic" in vr.notes.lower()
