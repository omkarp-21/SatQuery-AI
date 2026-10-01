"""POST /investigate — the agentic geospatial investigator (G14).

Mission + 1-3 images -> LLM/rule PLANNER -> typed AgentPlan -> deterministic
POLICY layer -> bounded executor (observe / verify / conditionally replan) ->
evidence-first investigation report.

The planner never bypasses validation and never substitutes a specialist. On
planner failure the request falls back to the deterministic /analyze path.
"""

from __future__ import annotations

import json
import os
import shutil
import time
import uuid
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import HTMLResponse

from satquery_agents.agent import AgentInvestigationResult

from app.services.agent_runner import run_investigation
from app.services.report import investigation_report_html

router = APIRouter(tags=["investigate"])

_REPO_ROOT = Path(__file__).resolve().parents[4]
_DATA_DIR = Path(os.environ.get("SATQUERY_DATA_DIR", _REPO_ROOT / "data")).resolve()
_UPLOAD_ROOT = (_DATA_DIR / "uploads").resolve()
_ALLOWED = {".tif", ".tiff", ".png", ".jpg", ".jpeg", ".npy"}
_MAX_BYTES = 64 * 1024 * 1024
_MAX_FILES = 4


def _safe_name(name: str) -> str:
    base = Path(name or "file").name
    stem = "".join(c for c in Path(base).stem if c.isalnum() or c in ("-", "_"))[:60] or "file"
    suf = Path(base).suffix.lower()
    if suf not in _ALLOWED:
        raise HTTPException(status_code=400, detail={"error": {"code": "unsupported_file_type",
                            "message": f"{suf!r} not supported"}})
    return stem + suf


@router.post("/investigate", response_model=AgentInvestigationResult)
async def investigate(
    query: str = Form(..., min_length=1),
    files: list[UploadFile] = File(...),
    context: str | None = Form(default=None),
) -> AgentInvestigationResult:
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
    req_dir.mkdir(parents=True, exist_ok=True)
    saved: list[str] = []
    for uf in files:
        data = await uf.read()
        if len(data) > _MAX_BYTES:
            shutil.rmtree(req_dir, ignore_errors=True)
            raise HTTPException(status_code=413, detail={"error": {"code": "file_too_large",
                                "message": f"{uf.filename}: too large"}})
        dest = req_dir / _safe_name(uf.filename or "upload")
        dest.write_bytes(data)
        saved.append(str(dest))

    started = time.time()
    try:
        result = run_investigation(query, saved, ctx, artifact_dir=str(req_dir))
    except Exception as exc:  # noqa: BLE001 - sanitized at the boundary
        raise HTTPException(status_code=500, detail={"error": {"code": "agent_error",
                            "message": type(exc).__name__}}) from exc

    # copy the primary change mask into the sandbox so the UI can fetch it
    mask_src = (result.provenance or {}).get("mask_source")
    if not mask_src:
        cand = sorted(req_dir.glob("*mask*.png"))
        mask_src = str(cand[0]) if cand else None
    if mask_src and Path(mask_src).exists():
        try:
            shutil.copyfile(mask_src, req_dir / "mask.png")
        except OSError:
            mask_src = None
    mask_url = f"/artifact?req={req_id}&name=mask.png" if (req_dir / "mask.png").exists() else None
    # Overlay preview: T2 imagery + change-mask tint + grounding box, burned by
    # the backend from executed specialist outputs. The viewer only accepts a
    # PNG/JPEG background — GeoTIFF inputs never qualify — so without this the
    # spatial view falls back to bare SVG polygons. Best-effort: the result
    # stands without it.
    overlay_url = None
    try:
        from app.services.overlay import build_investigation_overlay as _overlay  # noqa: E402

        ordered = list(result.inputs or saved)
        t2_base = ordered[1] if len(ordered) >= 2 else ordered[0]
        gbox, gdims = None, None
        for e in result.evidence or []:
            d = e.model_dump() if hasattr(e, "model_dump") else dict(e)
            if d.get("evidence_type") == "grounding":
                sr, pay = d.get("spatial_region") or {}, d.get("payload") or {}
                gbox = sr.get("bbox_xyxy")
                if gbox is None and sr.get("bbox_pixel"):
                    rmin, cmin, rmax, cmax = sr["bbox_pixel"]  # row-major -> xyxy
                    gbox = [cmin, rmin, cmax, rmax]
                gdims = pay.get("image_dims")
                break
        mask_png = req_dir / "mask.png"
        if mask_png.exists() or gbox:
            ov = _overlay(t2_base, str(mask_png) if mask_png.exists() else None,
                          gbox, gdims, req_dir / "overlay.png")
            if ov:
                overlay_url = f"/artifact?req={req_id}&name=overlay.png"
    except Exception:  # noqa: BLE001
        overlay_url = None
    input_urls = [f"/artifact?req={req_id}&name={Path(s).name}" for s in saved]
    result.provenance["input_files"] = ([overlay_url] + input_urls) if overlay_url else input_urls
    if mask_url:
        result.provenance["mask_url"] = mask_url
    result.timings.setdefault("endpoint_s", round(time.time() - started, 2))
    return result


@router.post("/investigate/report", response_class=HTMLResponse)
async def investigate_report(result: AgentInvestigationResult) -> str:
    """G18 Part 13 — render an executed investigation as a clean, self-contained
    HTML report (print-friendly, no external assets). Post the JSON body returned
    by `POST /investigate`."""
    return investigation_report_html(json.loads(result.model_dump_json()))
