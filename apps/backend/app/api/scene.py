"""POST /scene - single-image scene / retrieval slice (RemoteCLIP).

NOT a VQA endpoint. Returns a zero-shot ranking + evidence + provenance +
structural verification. No confidence value.
"""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.scene_slice import SceneResult, run_scene

router = APIRouter(tags=["scene"])

_REPO_ROOT = Path(__file__).resolve().parents[4]
_DATA_DIR = Path(os.environ.get("SATQUERY_DATA_DIR", _REPO_ROOT / "data")).resolve()
_EXTRA_DIRS = [
    (_REPO_ROOT / "external/research/RemoteCLIP/assets").resolve(),  # demo images
]
_CKPT = Path(os.environ.get("SATQUERY_REMOTECLIP_CKPT",
                            _REPO_ROOT / "models/cache/remoteclip/RemoteCLIP-ViT-B-32.pt"))


class SceneRequest(BaseModel):
    image_path: str = Field(description="path to the image, under the data dir (or a demo asset)")
    prompts: list[str] = Field(min_length=1, description="candidate scene labels / captions")
    top_k: int = Field(default=5, ge=1, le=50)


def _resolve(p: str) -> Path:
    allowed = [_DATA_DIR, *_EXTRA_DIRS]
    if Path(p).is_absolute():
        candidates = [Path(p).resolve()]
    else:
        candidates = [(base / p).resolve() for base in allowed]
    for rp in candidates:
        if any(base == rp or base in rp.parents for base in allowed) and rp.exists():
            return rp
    # distinguish "outside allowed" from "not found"
    for rp in candidates:
        if not any(base == rp or base in rp.parents for base in allowed):
            raise HTTPException(status_code=400, detail={"error": {"code": "path_not_allowed",
                                "message": "image path is outside the allowed directories"}})
    raise HTTPException(status_code=404, detail={"error": {"code": "not_found",
                        "message": f"no such file: {p}"}})


@router.post("/scene", response_model=SceneResult)
def post_scene(req: SceneRequest) -> SceneResult:
    img = _resolve(req.image_path)
    if not _CKPT.exists():
        raise HTTPException(status_code=503, detail={"error": {"code": "model_unavailable",
                            "message": "RemoteCLIP checkpoint not present on this host"}})
    try:
        return run_scene(img, req.prompts, checkpoint=_CKPT, top_k=req.top_k)
    except Exception as exc:  # noqa: BLE001 - sanitized at the boundary
        raise HTTPException(status_code=500, detail={"error": {"code": "pipeline_error",
                            "message": type(exc).__name__}}) from exc
