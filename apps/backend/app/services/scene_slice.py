"""Single-image scene vertical slice.

    image path + candidate prompts
      -> input validation (+ GeoTIFF metadata if applicable)
      -> RemoteCLIP adapter (isolated env, subprocess)
      -> zero-shot ranking over the prompts
      -> EvidenceItem (ranking) + standardized Provenance
      -> deterministic structural verification
      -> SceneResult

RemoteCLIP is **not a VQA model**. This slice does retrieval / zero-shot scene
tagging only - it does not satisfy the mandatory single-image VQA requirement.
No confidence value is produced (the score is a softmax over the supplied prompts).
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from satquery_evidence import EvidenceItem, Provenance, VerificationResult, new_evidence_id, verify
from satquery_geospatial import RasterMeta, read_raster_meta
from satquery_model_adapters import AdapterRequest, RemoteClipAdapter

_REPO_ROOT = Path(__file__).resolve().parents[4]
_DEFAULT_CKPT = _REPO_ROOT / "models/cache/remoteclip/RemoteCLIP-ViT-B-32.pt"


class SceneResult(BaseModel):
    ok: bool
    errors: list[str] = []
    image_meta: RasterMeta | None = None
    answer: dict[str, Any] | None = None
    evidence: list[EvidenceItem] = []
    verification: VerificationResult | None = None
    provenance: dict[str, Any] = {}


def run_scene(
    image_path: str | Path,
    prompts: list[str] | str,
    *,
    checkpoint: str | Path | None = None,
    top_k: int = 5,
) -> SceneResult:
    p = Path(image_path)
    errors: list[str] = []
    if not p.exists():
        return SceneResult(ok=False, errors=[f"image not found: {p}"])

    prompt_list = (
        [s.strip() for s in prompts.split(";") if s.strip()]
        if isinstance(prompts, str)
        else [s.strip() for s in prompts if s.strip()]
    )
    if not prompt_list:
        return SceneResult(ok=False, errors=["no candidate prompts supplied"])

    meta: RasterMeta | None = None
    if p.suffix.lower() in (".tif", ".tiff"):
        try:
            meta = read_raster_meta(p)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"raster metadata unreadable: {type(exc).__name__}")

    ckpt = str(checkpoint or os.environ.get("SATQUERY_REMOTECLIP_CKPT") or _DEFAULT_CKPT)
    adapter = RemoteClipAdapter(checkpoint=ckpt)
    result = adapter.run(
        AdapterRequest(
            query=";".join(prompt_list),
            images=[str(p)],
            context={"task": "zero-shot-classification"},
        )
    )

    ranking = result.answer["ranking"][:top_k]
    ev = EvidenceItem(
        evidence_id=new_evidence_id("ev-scene"),
        source_model="remoteclip",
        task="zero-shot-classification",
        modality="optical-single",
        source_artifact=str(p),
        spatial_region=({"bounds": list(meta.bounds), "crs": meta.crs} if meta else None),
        claim_supported=f"the image best matches the label {result.answer['top_label']!r} among the given prompts",
        evidence_type="ranking",
        payload={"top_label": result.answer["top_label"], "ranking": ranking,
                 "score_meaning": result.provenance.get("score_meaning")},
        provenance=result.provenance,
    )

    prov = Provenance.from_adapter(
        result.provenance,
        task="zero-shot-classification",
        input_ids=[str(p)],
        preprocessing=["open-clip-preprocess"],
        parameters={"prompts": prompt_list, "top_k": top_k},
    )

    vr = verify(
        result.answer,
        [ev],
        {
            "input_paths": [str(p)],
            "inputs_exist": {str(p): p.exists()},
            "requested_modality": "optical-single",
            "model_modalities": list(adapter.modalities),
        },
    )

    return SceneResult(
        ok=True,
        errors=errors,
        image_meta=meta,
        answer={"top_label": result.answer["top_label"], "ranking": ranking,
                "score": result.score,
                "score_meaning": "softmax over supplied prompts - not a calibrated confidence"},
        evidence=[ev],
        verification=vr,
        provenance=prov.model_dump(),
    )
