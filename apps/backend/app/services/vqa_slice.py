"""Single-image VQA vertical slice (G11).

    image path + question
      -> input validation (image opens; GeoTIFF metadata if applicable)
      -> TinyRS adapter (isolated .venvs/tinyrs, subprocess)
      -> normalized answer text (+ yes/no parse when applicable)
      -> EvidenceItem (vqa) + standardized Provenance
      -> deterministic structural verification (inputs exist, modality supported)
      -> VqaResult

TinyRS is a **VQA specialist** (Qwen2-VL-2B base, RS-instruction-tuned). It is
NOT a grounding model — grounding queries go to RemoteSAM
(`SINGLE_IMAGE_GROUNDING`). No confidence value: the answer is greedy-decoded and
no calibrated probability is produced.

Status: TinyRS REPRODUCED + MEASURED (balanced acc 0.87 on 40 RSVQA-LR yes/no,
CPU, 2026-09-02 — sanity-scale, not a full benchmark). See `docs/research/EXP-002.md`.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from satquery_evidence import (
    EvidenceItem,
    Provenance,
    VerificationResult,
    new_evidence_id,
    verify,
)
from satquery_geospatial import RasterMeta, read_raster_meta
from satquery_model_adapters import AdapterRequest, TinyRsAdapter

_REPO_ROOT = Path(__file__).resolve().parents[4]
_DEFAULT_WEIGHTS = _REPO_ROOT / "models/cache/tinyrs/Qwen2-VL-TinyRS"


class VqaResult(BaseModel):
    ok: bool
    errors: list[str] = []
    question: str
    image_meta: RasterMeta | None = None
    answer_text: str | None = None
    yesno: int | None = None  # 1 / 0 / None
    score: float | None = None
    score_meaning: str = (
        "none - the answer is greedy-decoded; no calibrated probability is produced"
    )
    execution_time_s: float | None = None
    evidence: list[EvidenceItem] = []
    verification: VerificationResult | None = None
    provenance: dict[str, Any] = {}


def run_vqa(
    image_path: str | Path,
    question: str,
    *,
    weights: str | Path | None = None,
    arch: str = "qwen2_vl",
    timeout_s: float = 600.0,
) -> VqaResult:
    started = time.time()
    p = Path(image_path)
    if not p.exists():
        return VqaResult(ok=False, question=question, errors=[f"image not found: {p}"])
    if not question or not str(question).strip():
        return VqaResult(ok=False, question=question, errors=["empty question"])
    w = Path(weights or _DEFAULT_WEIGHTS)
    if not (w / "config.json").exists():
        return VqaResult(ok=False, question=question,
                         errors=[f"TinyRS weights not found: {w}"])

    meta: RasterMeta | None = None
    if p.suffix.lower() in (".tif", ".tiff"):
        try:
            meta = read_raster_meta(p)
        except Exception:  # noqa: BLE001
            meta = None

    adapter = TinyRsAdapter(weights=str(w), arch=arch, timeout_s=timeout_s)
    try:
        res = adapter.run(
            AdapterRequest(query=str(question).strip(), images=[str(p)], context={"task": "vqa"})
        )
    except Exception as exc:  # noqa: BLE001 - sanitized
        return VqaResult(ok=False, question=question, image_meta=meta,
                         errors=[f"tinyrs adapter failed: {type(exc).__name__}: {exc}"])

    ans = res.answer or {}
    ev = EvidenceItem(
        evidence_id=new_evidence_id("ev-vqa"),
        source_model="tinyrs", task="vqa", modality="optical-single",
        source_artifact=str(p),
        claim_supported=f"answer to {question!r}: {ans.get('text', '')!r}",
        evidence_type="vqa",
        payload={"question": question, "answer_text": ans.get("text"),
                 "yesno": ans.get("yesno"), "score": None,
                 "score_meaning": "no calibrated probability"},
        provenance=res.provenance,
    )
    vr = verify(
        {"answer": ans.get("text")},
        [ev],
        {"input_paths": [str(p)], "inputs_exist": {str(p): True},
         "requested_modality": "optical-single", "model_modalities": list(adapter.modalities)},
    )

    prov = {
        "layer": "vqa_slice",
        "model": "tinyrs",
        "stages": ["image-open-check", "tinyrs_adapter", "evidence", "verify"],
        "adapter_provenance": res.provenance,
        "standardized": Provenance.from_adapter(
            res.provenance, task="vqa", input_ids=[str(p)],
            preprocessing=["qwen2vl-chat-template"],
        ).model_dump(),
        "orchestration_runtime_s": round(time.time() - started, 3),
        "note": "TinyRS (Qwen2-VL-2B base). VQA only. No confidence value produced.",
    }

    return VqaResult(
        ok=(res.status == "ok" and ans.get("status") == "ok"),
        question=question, image_meta=meta,
        answer_text=ans.get("text"), yesno=ans.get("yesno"),
        score=None, execution_time_s=res.timing_s,
        evidence=[ev], verification=vr, provenance=prov,
    )
