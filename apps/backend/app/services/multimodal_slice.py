"""Optical + SAR joint-representation vertical contract (INTERNAL - no public endpoint).

    optical + SAR (+ context)
      -> input validation
      -> CROMA or DOFA adapter (isolated env, subprocess)
      -> normalized joint / per-modality representation
      -> EvidenceItem (embedding) + standardized Provenance + timing
      -> deterministic structural verification
      -> JointReprResult

**Representation-level integration.** EXP-004 Run 2 (G12) measured the task-level
benefit on real DFC2020: frozen CROMA `joint_GAP` -> linear probe = macro-F1
0.793 vs optical-only 0.726 (+0.067) - **positive but not significant at n=200**
(bootstrap CI includes 0). CROMA is the optical-SAR primary (beat DOFA 0.708).
Still **no `/fusion` endpoint**: the SAR benefit is real but under-powered, so a
production fusion task waits for a larger eval split to confirm significance.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel

from satquery_evidence import EvidenceItem, Provenance, VerificationResult, new_evidence_id, verify
from satquery_model_adapters import AdapterRequest, CromaAdapter, DofaAdapter

_REPO_ROOT = Path(__file__).resolve().parents[4]
_CKPT = {
    "croma": _REPO_ROOT / "models/cache/croma/CROMA_base.pt",
    "dofa": _REPO_ROOT / "models/cache/dofa/DOFA_ViT_base_e100.pth",
}


class JointReprResult(BaseModel):
    ok: bool
    errors: list[str] = []
    model: str
    modality: str = "optical-sar"
    representation: dict[str, Any] = {}  # e.g. {"joint_gap": [...], "dim": 768}
    evidence: list[EvidenceItem] = []
    verification: VerificationResult | None = None
    provenance: dict[str, Any] = {}
    execution_time_s: float | None = None
    note: str = (
        "representation-level only - NOT full optical-SAR reasoning; task benefit is EXP-004 Run 2"
    )


def run_joint_representation(
    optical_npy: str | Path | None,
    sar_npy: str | Path | None,
    *,
    model: Literal["croma", "dofa"] = "croma",
    checkpoint: str | Path | None = None,
    smoke_random: bool = False,
) -> JointReprResult:
    ckpt = str(checkpoint or os.environ.get(f"SATQUERY_{model.upper()}_CKPT") or _CKPT[model])
    errors: list[str] = []

    if not smoke_random:
        for tag, pth in (("optical", optical_npy), ("sar", sar_npy)):
            if pth is None or not Path(pth).exists():
                return JointReprResult(ok=False, model=model, errors=[f"{tag} input not found: {pth}"])

    if model == "croma":
        # CROMA adapter reads images as [s1_npy, s2_npy] -> [sar, optical]
        adapter: Any = CromaAdapter(checkpoint=ckpt)
        req = AdapterRequest(
            images=([] if smoke_random else [str(sar_npy), str(optical_npy)]),
            context={"task": "embedding", **({"random": 1} if smoke_random else {})},
        )
    else:
        adapter = DofaAdapter(checkpoint=ckpt)
        req = AdapterRequest(
            images=([] if smoke_random else [str(optical_npy)]),
            context={"task": "embedding", "modality": "s2", **({"random": 1} if smoke_random else {})},
        )

    result = adapter.run(req)

    if model == "croma":
        rep = {"joint_gap": result.answer["joint_gap"], "optical_gap": result.answer["optical_gap"],
               "sar_gap": result.answer["sar_gap"], "dim": result.answer["dim"]}
        payload = {"dim": result.answer["dim"], "has_joint": True}
    else:
        rep = {"feature": result.answer["feature"], "dim": result.answer["dim"],
               "modality": result.answer["modality"]}
        payload = {"dim": result.answer["dim"], "has_joint": False}

    ev = EvidenceItem(
        evidence_id=new_evidence_id("ev-mm"),
        source_model=model,
        task="joint-representation",
        modality="optical-sar",
        source_artifact=(None if smoke_random else f"{optical_npy} + {sar_npy}"),
        claim_supported="a joint optical-SAR representation was produced for downstream probing",
        evidence_type="embedding",
        payload=payload,
        provenance=result.provenance,
    )
    prov = Provenance.from_adapter(
        result.provenance, task="joint-representation",
        input_ids=([] if smoke_random else [str(optical_npy), str(sar_npy)]),
        preprocessing=["channel-normalize"] + (["resample-120"] if model == "croma" else []),
    )
    vr = verify(result.answer, [ev], {
        "requested_modality": "optical-sar" if model == "croma" else "optical-single",
        "model_modalities": list(adapter.modalities),
    })

    return JointReprResult(
        ok=True, model=model, errors=errors, representation=rep,
        evidence=[ev], verification=vr, provenance=prov.model_dump(),
        execution_time_s=result.provenance.get("runtime_s"),
    )
