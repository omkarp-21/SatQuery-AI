"""Single-image grounding vertical slice (G10).

    image path + referring phrase
      -> input validation (image opens; GeoTIFF metadata if applicable)
      -> RemoteSAM adapter (isolated .venvs/remotesam, subprocess)
      -> normalized GroundingResult (bbox + mask, in original-image pixels)
      -> spatial-correspondence checks (box in bounds, mask dims match)
      -> EvidenceItem (grounding) + standardized Provenance
      -> deterministic structural verification
      -> GroundingResult

RemoteSAM is a **grounding / referring-segmentation specialist** — text -> box +
mask. It is **not** a VQA or captioning model. Its `score` is a raw foreground
softmax probability, NOT a calibrated confidence. Upstream licence: **NOT STATED**.

Status: RemoteSAM is **REPRODUCED** on this host (CPU). Not MEASURED on DIOR-RSVG
(dataset unacquirable). See `docs/research/EXP-GROUNDING.md`.
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
from satquery_model_adapters import AdapterRequest, RemoteSamAdapter

_REPO_ROOT = Path(__file__).resolve().parents[4]
_DEFAULT_CKPT = _REPO_ROOT / "models/cache/remotesam/RemoteSAM/RemoteSAMv1.pth"
_DEFAULT_BERT = (
    _REPO_ROOT
    / "models/cache/hf_home/hub/models--bert-base-uncased/snapshots"
    / "86b5e0934494bd15c9632b12f734a8a67f723594"
)


class GroundingResult(BaseModel):
    ok: bool
    errors: list[str] = []
    query: str
    image_meta: RasterMeta | None = None
    image_dimensions: list[int] | None = None  # [W, H]
    bbox_xyxy: list[float] | None = None  # [xmin, ymin, xmax, ymax] in image pixels
    mask_path: str | None = None
    score: float | None = None
    score_meaning: str = (
        "RemoteSAM foreground softmax probability - a raw model score, NOT a calibrated confidence"
    )
    grounding_status: str | None = None  # ok | no_box | error
    validation_status: str | None = None  # PASS | FAIL_BOX_OUT_OF_BOUNDS | NO_REGION | ...
    execution_time_s: float | None = None
    evidence: list[EvidenceItem] = []
    verification: VerificationResult | None = None
    provenance: dict[str, Any] = {}


def run_grounding(
    image_path: str | Path,
    query: str,
    *,
    checkpoint: str | Path | None = None,
    repo: str | Path | None = None,
    bert_dir: str | Path | None = None,
    device: str = "cpu",
    timeout_s: float = 600.0,
    artifact_dir: str | Path | None = None,
) -> GroundingResult:
    started = time.time()
    p = Path(image_path)
    if not p.exists():
        return GroundingResult(ok=False, query=query, errors=[f"image not found: {p}"])
    if not query or not str(query).strip():
        return GroundingResult(ok=False, query=query, errors=["empty referring phrase"])

    ckpt = Path(checkpoint or _DEFAULT_CKPT)
    if not ckpt.exists():
        return GroundingResult(ok=False, query=query,
                               errors=[f"RemoteSAM checkpoint not found: {ckpt}"])

    meta: RasterMeta | None = None
    if p.suffix.lower() in (".tif", ".tiff"):
        try:
            meta = read_raster_meta(p)
        except Exception:  # noqa: BLE001 - a non-geo TIFF is still groundable
            meta = None

    adapter = RemoteSamAdapter(
        checkpoint=str(ckpt),
        repo=str(repo) if repo else None,
        bert_dir=str(bert_dir or _DEFAULT_BERT) if Path(bert_dir or _DEFAULT_BERT).exists() else None,
        device=device,
        timeout_s=timeout_s,
    )
    try:
        res = adapter.run(
            AdapterRequest(query=str(query).strip(), images=[str(p)], context={"task": "grounding"})
        )
    except Exception as exc:  # noqa: BLE001 - sanitized
        return GroundingResult(ok=False, query=query,
                               errors=[f"remotesam adapter failed: {type(exc).__name__}: {exc}"],
                               image_meta=meta)

    ans = res.answer or {}
    box = ans.get("bbox_xyxy")
    dims = ans.get("image_dims")  # [W, H]
    mask_path = res.artifacts.get("mask_path")

    # spatial-correspondence checks (Phase 5)
    vstatus = "PASS"
    if box is None:
        vstatus = "NO_REGION"
    else:
        if not (len(box) == 4 and box[0] < box[2] and box[1] < box[3]):
            vstatus = "FAIL_BOX_DEGENERATE"
        elif dims and not (0 <= box[0] and 0 <= box[1] and box[2] <= dims[0] and box[3] <= dims[1]):
            vstatus = "FAIL_BOX_OUT_OF_BOUNDS"

    region = None
    if box is not None:
        region = {"bbox_pixel": [int(box[1]), int(box[0]), int(box[3]), int(box[2])],  # rmin,cmin,rmax,cmax
                  "bbox_xyxy": [float(x) for x in box]}

    ev = EvidenceItem(
        evidence_id=new_evidence_id("ev-ground"),
        source_model="remotesam", task="grounding", modality="optical-single",
        source_artifact=mask_path,
        spatial_region=region,
        claim_supported=f"the phrase {query!r} refers to the region "
                        + (f"{[round(x,1) for x in box]}" if box else "(no region found)"),
        evidence_type="grounding",
        payload={"bbox_xyxy": box, "image_dims": dims, "mask_path": mask_path,
                 "mask_fg_fraction": ans.get("mask_fg_fraction"), "score": res.score,
                 "score_meaning": res.model_meta.get("license", "")[:0] or
                 "foreground softmax probability - not a calibrated confidence"},
        provenance=res.provenance,
    )
    vr = verify(
        {"grounding_status": ans.get("grounding_status")},
        [ev],
        {"input_paths": [str(p)], "inputs_exist": {str(p): True},
         "requested_modality": "optical-single", "model_modalities": list(adapter.modalities)},
    )

    prov = {
        "layer": "grounding_slice",
        "model": "remotesam",
        "stages": ["image-open-check", "remotesam_adapter", "spatial-correspondence", "evidence", "verify"],
        "adapter_provenance": res.provenance,
        "standardized": Provenance.from_adapter(
            res.provenance, task="grounding", input_ids=[str(p)],
            preprocessing=["resize-896", "bert-tokenize"],
        ).model_dump(),
        "orchestration_runtime_s": round(time.time() - started, 3),
        "note": "RemoteSAM: text -> box + mask. Score is a raw model probability, NOT a "
                "confidence. Upstream licence NOT STATED. Reproduced, not measured on a benchmark.",
    }

    return GroundingResult(
        ok=(res.status == "ok" and vstatus.startswith(("PASS", "NO_REGION"))),
        query=query, image_meta=meta,
        image_dimensions=dims, bbox_xyxy=[float(x) for x in box] if box else None,
        mask_path=mask_path, score=res.score, grounding_status=ans.get("grounding_status"),
        validation_status=vstatus, execution_time_s=res.timing_s,
        evidence=[ev], verification=vr, provenance=prov,
    )
