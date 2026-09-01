"""POST /analyze - the unified deterministic SatQuery analysis endpoint.

query + images -> interpret -> validate -> route -> specialist -> aggregate
evidence/verification/provenance -> structured response with observable routing.

No LLM planning. No confidence. Multimodal path is representation-level.
"""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.analyze import AnalyzeResult, run_analyze

router = APIRouter(tags=["analyze"])

_REPO_ROOT = Path(__file__).resolve().parents[4]
_DATA_DIR = Path(os.environ.get("SATQUERY_DATA_DIR", _REPO_ROOT / "data")).resolve()
_EXTRA = [(_REPO_ROOT / "external/research/RemoteCLIP/assets").resolve()]


class AnalyzeRequest(BaseModel):
    query: str = Field(min_length=1, description="natural-language query")
    images: list[str] = Field(default_factory=list, description="0-2 image paths under the data dir")
    context: dict = Field(default_factory=dict, description="optional {modalities, prompts, ...}")


def _resolve(p: str) -> Path:
    allowed = [_DATA_DIR, *_EXTRA]
    cands = [Path(p).resolve()] if Path(p).is_absolute() else [(b / p).resolve() for b in allowed]
    for rp in cands:
        if any(b == rp or b in rp.parents for b in allowed) and rp.exists():
            return rp
    for rp in cands:
        if not any(b == rp or b in rp.parents for b in allowed):
            raise HTTPException(status_code=400, detail={"error": {"code": "path_not_allowed",
                                "message": "image path outside allowed directories"}})
    raise HTTPException(status_code=404, detail={"error": {"code": "not_found",
                        "message": f"no such file: {p}"}})


@router.post("/analyze", response_model=AnalyzeResult)
def post_analyze(req: AnalyzeRequest) -> AnalyzeResult:
    if len(req.images) > 2:
        raise HTTPException(status_code=400, detail={"error": {"code": "too_many_images",
                            "message": "at most 2 images are supported"}})
    paths = [str(_resolve(p)) for p in req.images]
    try:
        return run_analyze(req.query, paths, req.context)
    except Exception as exc:  # noqa: BLE001 - sanitized at boundary
        raise HTTPException(status_code=500, detail={"error": {"code": "pipeline_error",
                            "message": type(exc).__name__}}) from exc
