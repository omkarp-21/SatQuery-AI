"""G13 product surface — one coherent end-to-end SatQuery MVP.

    GET  /                 -> the local single-page UI (static HTML, no build step)
    POST /analyze/upload   -> multipart: 1-2 image/GeoTIFF files + query -> NormalizedResponse
    GET  /artifact         -> serve a mask/overlay PNG produced by a request (sandboxed)

`/analyze/upload` is the primary product entry point. It saves uploads into a
per-request sandbox under ``data/uploads/<id>/``, runs the existing deterministic
`run_analyze` (validation -> interpret -> route -> specialist -> evidence ->
verify -> resolution), then flattens the result with `normalize()`. Nothing
bypasses GeoTIFF validation, CRS/transform checks, evidence, verification, or
failure resolution.
"""

from __future__ import annotations

import json
import os
import shutil
import time
import uuid
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, HTMLResponse

from app.services.analyze import run_analyze
from app.services.normalize import NormalizedResponse, normalize

router = APIRouter(tags=["product"])

_REPO_ROOT = Path(__file__).resolve().parents[4]
_DATA_DIR = Path(os.environ.get("SATQUERY_DATA_DIR", _REPO_ROOT / "data")).resolve()
_UPLOAD_ROOT = (_DATA_DIR / "uploads").resolve()
_STATIC = (Path(__file__).resolve().parents[1] / "static").resolve()

_ALLOWED_SUFFIX = {".tif", ".tiff", ".png", ".jpg", ".jpeg", ".npy"}
_MAX_BYTES = 64 * 1024 * 1024  # 64 MB per file — bounded, rejects decompression bombs early
_MAX_FILES = 2


@router.get("/", response_class=HTMLResponse, include_in_schema=False)
def ui() -> HTMLResponse:
    idx = _STATIC / "index.html"
    if not idx.exists():
        raise HTTPException(status_code=404, detail={"error": {"code": "ui_missing",
                            "message": "static UI not built into this deployment"}})
    return HTMLResponse(idx.read_text(encoding="utf-8"))


def _safe_name(name: str) -> str:
    base = Path(name or "file").name
    stem = "".join(c for c in Path(base).stem if c.isalnum() or c in ("-", "_"))[:60] or "file"
    suf = Path(base).suffix.lower()
    if suf not in _ALLOWED_SUFFIX:
        raise HTTPException(status_code=400, detail={"error": {"code": "unsupported_file_type",
                            "message": f"file type {suf!r} not supported; use {sorted(_ALLOWED_SUFFIX)}"}})
    return stem + suf


@router.post("/analyze/upload", response_model=NormalizedResponse)
async def analyze_upload(
    query: str = Form(..., min_length=1),
    files: list[UploadFile] = File(...),
    context: str | None = Form(default=None, description="optional JSON: {modalities, prompts, question}"),
) -> NormalizedResponse:
    if not files or len(files) > _MAX_FILES:
        raise HTTPException(status_code=400, detail={"error": {"code": "bad_file_count",
                            "message": f"upload 1-{_MAX_FILES} files"}})
    try:
        ctx = json.loads(context) if context else {}
        if not isinstance(ctx, dict):
            raise ValueError
    except ValueError:
        raise HTTPException(status_code=400, detail={"error": {"code": "bad_context",
                            "message": "context must be a JSON object"}}) from None

    req_id = uuid.uuid4().hex[:12]
    req_dir = (_UPLOAD_ROOT / req_id).resolve()
    if _UPLOAD_ROOT not in req_dir.parents:  # defensive
        raise HTTPException(status_code=400, detail={"error": {"code": "path_error", "message": "bad sandbox"}})
    req_dir.mkdir(parents=True, exist_ok=True)

    saved: list[str] = []
    for uf in files:
        data = await uf.read()
        if len(data) > _MAX_BYTES:
            shutil.rmtree(req_dir, ignore_errors=True)
            raise HTTPException(status_code=413, detail={"error": {"code": "file_too_large",
                                "message": f"{uf.filename}: exceeds {_MAX_BYTES // (1024 * 1024)} MB"}})
        dest = req_dir / _safe_name(uf.filename or "upload")
        dest.write_bytes(data)
        saved.append(str(dest))

    started = time.time()
    try:
        res = run_analyze(query, saved, ctx, artifact_dir=str(req_dir))
    except Exception as exc:  # noqa: BLE001 - sanitized at the boundary
        raise HTTPException(status_code=500, detail={"error": {"code": "pipeline_error",
                            "message": type(exc).__name__}}) from exc
    latency = round(time.time() - started, 3)

    resp = normalize(res, latency_s=latency)

    # copy any produced mask into this request's sandbox and rewrite the URL so the
    # UI can fetch it regardless of where the slice wrote it.
    payload = res.result or {}
    mask_src = payload.get("mask_path")
    if resp.mask_url and mask_src and Path(mask_src).exists():
        try:
            shutil.copyfile(mask_src, req_dir / "mask.png")
            resp.mask_url = f"/artifact?req={req_id}&name=mask.png"
        except OSError:
            resp.mask_url = None
    else:
        resp.mask_url = None

    # echo the input image URL(s) for preview
    resp.provenance = resp.provenance or {}
    resp.provenance["input_files"] = [f"/artifact?req={req_id}&name={Path(s).name}" for s in saved]
    return resp


@router.get("/artifact", include_in_schema=False)
def artifact(req: str = Query(..., pattern=r"^[a-f0-9]{6,32}$"),
             name: str = Query(..., min_length=1, max_length=80)) -> FileResponse:
    safe = Path(name).name
    target = (_UPLOAD_ROOT / req / safe).resolve()
    if _UPLOAD_ROOT not in target.parents or not target.exists() or not target.is_file():
        raise HTTPException(status_code=404, detail={"error": {"code": "not_found",
                            "message": "artifact not found"}})
    return FileResponse(target)
