"""POST /change - the first real SatQuery API surface.

    {t1_path, t2_path} -> GeoTIFF validation -> compatibility gate ->
    ChangeFormer adapter -> mask -> changed fraction / area / bbox / centroid ->
    provenance -> JSON (ChangeSliceResult)

No agent, no LLM, no confidence value. Paths are resolved against an allow-listed
base directory (`SATQUERY_DATA_DIR`, default the repo `data/`).
"""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.temporal_slice import ChangeSliceResult, run_change_slice

router = APIRouter(tags=["change"])

_REPO_ROOT = Path(__file__).resolve().parents[4]
_DATA_DIR = Path(os.environ.get("SATQUERY_DATA_DIR", _REPO_ROOT / "data")).resolve()
_CKPT_DIR = Path(
    os.environ.get(
        "SATQUERY_CHANGEFORMER_CKPT_DIR",
        _REPO_ROOT
        / "models/cache/changeformer/CD_ChangeFormerV6_LEVIR_b16_lr0.0001_adamw_train_test_200_linear_ce_multi_train_True_multi_infer_False_shuffle_AB_False_embed_dim_256",
    )
)


class ChangeRequest(BaseModel):
    t1_path: str = Field(description="path to the T1 GeoTIFF, under the data dir")
    t2_path: str = Field(description="path to the T2 GeoTIFF, under the data dir")
    strict: bool = Field(default=True, description="block analysis if the pair is not co-registered")


def _resolve_under_data(p: str) -> Path:
    rp = (Path(p) if Path(p).is_absolute() else _DATA_DIR / p).resolve()
    if _DATA_DIR not in rp.parents and rp != _DATA_DIR:
        raise HTTPException(status_code=400, detail={"error": {"code": "path_not_allowed",
                            "message": "input path is outside the allowed data directory"}})
    if not rp.exists():
        raise HTTPException(status_code=404, detail={"error": {"code": "not_found",
                            "message": f"no such file: {p}"}})
    return rp


@router.post("/change", response_model=ChangeSliceResult)
def post_change(req: ChangeRequest) -> ChangeSliceResult:
    t1 = _resolve_under_data(req.t1_path)
    t2 = _resolve_under_data(req.t2_path)
    if not (_CKPT_DIR / "best_ckpt.pt").exists():
        raise HTTPException(status_code=503, detail={"error": {"code": "model_unavailable",
                            "message": "ChangeFormer checkpoint not present on this host"}})
    try:
        result = run_change_slice(t1, t2, checkpoint_dir=_CKPT_DIR, strict=req.strict)
    except Exception as exc:  # noqa: BLE001 - sanitized at the boundary
        raise HTTPException(status_code=500, detail={"error": {"code": "pipeline_error",
                            "message": type(exc).__name__}}) from exc
    return result
