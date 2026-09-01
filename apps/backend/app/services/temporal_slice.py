"""Temporal vertical slice — a real end-to-end backend path.

    T1 / T2 GeoTIFF paths
      -> geospatial validation (format, dims, CRS, transform, bounds, bands, NoData)
      -> pair-compatibility (co-registration) check
      -> ChangeFormer adapter (isolated research env, via subprocess)
      -> change mask
      -> simple spatial statistics (changed area, bbox in native + lon/lat)
      -> structured ChangeSliceResult (+ provenance)

This is orchestration (lives in `apps/backend/app/services/`, not in `packages/`).
It does NOT build the full agent, invent confidence, or claim any SIH requirement
is met — it produces evidence.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import numpy as np
import rasterio
from pydantic import BaseModel
from pyproj import Transformer

from satquery_evidence import EvidenceItem, Provenance, VerificationResult, new_evidence_id, verify
from satquery_geospatial import (
    PairCompatibility,
    RasterMeta,
    check_pair_compatibility,
    validate_geotiff,
)
from satquery_model_adapters.base import AdapterRequest
from satquery_model_adapters.changeformer import ChangeFormerAdapter


class ChangeStats(BaseModel):
    changed_pixels: int
    total_pixels: int
    changed_fraction: float
    changed_area_m2: float | None = None
    changed_area_ha: float | None = None
    change_bbox_native: tuple[float, float, float, float] | None = None
    change_bbox_lonlat: tuple[float, float, float, float] | None = None
    change_centroid_lonlat: tuple[float, float] | None = None


class ChangeSliceResult(BaseModel):
    ok: bool
    errors: list[str]
    t1_meta: RasterMeta | None
    t2_meta: RasterMeta | None
    t1_valid: bool | None = None
    t2_valid: bool | None = None
    validation_warnings: list[str] = []
    pair: PairCompatibility | None = None
    stats: ChangeStats | None = None
    mask_path: str | None = None
    evidence: list[EvidenceItem] = []
    verification: VerificationResult | None = None
    provenance: dict[str, Any] = {}


def _mask_bbox_native(mask: np.ndarray, transform6: tuple[float, ...]) -> tuple[float, float, float, float] | None:
    rows = np.any(mask > 127, axis=1)
    cols = np.any(mask > 127, axis=0)
    if not rows.any():
        return None
    rmin, rmax = np.where(rows)[0][[0, -1]]
    cmin, cmax = np.where(cols)[0][[0, -1]]
    a, b, c, d, e, f = transform6  # x = a*col + b*row + c ; y = d*col + e*row + f
    xs = [a * cc + b * rr + c for cc in (cmin, cmax + 1) for rr in (rmin, rmax + 1)]
    ys = [d * cc + e * rr + f for cc in (cmin, cmax + 1) for rr in (rmin, rmax + 1)]
    return (min(xs), min(ys), max(xs), max(ys))


def run_change_slice(
    t1_path: str | Path,
    t2_path: str | Path,
    *,
    checkpoint_dir: str | Path,
    artifact_dir: str | Path | None = None,
    strict: bool = True,
) -> ChangeSliceResult:
    """Run the full T1/T2 -> validated -> ChangeFormer -> stats path."""
    errors: list[str] = []
    started = time.time()

    v1 = validate_geotiff(t1_path)
    v2 = validate_geotiff(t2_path)
    warnings = list(v1.warnings) + list(v2.warnings)
    if not v1.ok:
        errors.append(f"T1 failed validation: {[c.name for c in v1.failed()]}")
    if not v2.ok:
        errors.append(f"T2 failed validation: {[c.name for c in v2.failed()]}")

    m1, m2 = v1.meta, v2.meta
    if m1 is None or m2 is None:
        return ChangeSliceResult(ok=False, errors=errors or ["unreadable raster"], t1_meta=m1, t2_meta=m2)

    pair = check_pair_compatibility(m1, m2)
    if not pair.co_registered:
        errors.append(f"T1/T2 not co-registered: {pair.mismatches}")

    if strict and errors:
        return ChangeSliceResult(
            ok=False, errors=errors, t1_meta=m1, t2_meta=m2,
            t1_valid=v1.ok, t2_valid=v2.ok, validation_warnings=warnings, pair=pair,
        )

    adapter = ChangeFormerAdapter(checkpoint=str(checkpoint_dir), device="cpu")
    result = adapter.predict(
        AdapterRequest(
            query="detect bi-temporal change",
            images=[str(t1_path), str(t2_path)],
            context={"task": "change-detection", "modality": "optical-bitemporal",
                     "artifact_dir": str(artifact_dir) if artifact_dir else None},
        )
    )

    changed_px = int(result.answer["changed_pixels"])
    total_px = int(result.answer["total_pixels"])
    stats = ChangeStats(
        changed_pixels=changed_px,
        total_pixels=total_px,
        changed_fraction=float(result.answer["changed_fraction"]),
    )

    # --- area (only if the grid is projected with linear metres) ---
    if m1.is_projected and (m1.linear_units or "").lower().startswith(("met", "m")):
        px_area = m1.res[0] * m1.res[1]
        stats.changed_area_m2 = round(changed_px * px_area, 2)
        stats.changed_area_ha = round(stats.changed_area_m2 / 10_000.0, 4)

    # --- change bbox in native CRS + lon/lat ---
    mask_path = result.artifacts.get("mask_path")
    if mask_path and Path(mask_path).exists():
        with rasterio.open(mask_path) as ds:
            mask = ds.read(1)
        bbox = _mask_bbox_native(mask, m1.transform)
        if bbox is not None:
            stats.change_bbox_native = tuple(round(float(v), 4) for v in bbox)  # type: ignore[assignment]
            if m1.crs_epsg:
                tr = Transformer.from_crs(f"EPSG:{m1.crs_epsg}", "EPSG:4326", always_xy=True)
                lon0, lat0 = tr.transform(bbox[0], bbox[1])
                lon1, lat1 = tr.transform(bbox[2], bbox[3])
                stats.change_bbox_lonlat = (round(min(lon0, lon1), 6), round(min(lat0, lat1), 6),
                                            round(max(lon0, lon1), 6), round(max(lat0, lat1), 6))
                cx, cy = tr.transform((bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2)
                stats.change_centroid_lonlat = (round(cx, 6), round(cy, 6))

    # --- structured evidence + deterministic verification ---
    ev = EvidenceItem(
        evidence_id=new_evidence_id("ev-change"),
        source_model="changeformer",
        task="change-detection",
        modality="optical-bitemporal",
        source_artifact=mask_path,
        spatial_region=({"bbox_lonlat": list(stats.change_bbox_lonlat)}
                        if stats.change_bbox_lonlat else None),
        temporal_context={"t1": m1.path, "t2": m2.path, "relation": "T1 before T2"},
        claim_supported=f"~{stats.changed_fraction:.1%} of pixels changed between T1 and T2",
        evidence_type="change-mask",
        payload={"mask_path": mask_path, "changed_fraction": stats.changed_fraction,
                 "changed_area_ha": stats.changed_area_ha},
        provenance=result.provenance,
    )
    vr = verify(
        {"changed_fraction": stats.changed_fraction},
        [ev],
        {
            "input_paths": [m1.path, m2.path],
            "inputs_exist": {m1.path: True, m2.path: True},
            "requested_modality": "optical-bitemporal",
            "model_modalities": ["optical-bitemporal"],
            "pair_co_registered": pair.co_registered,
        },
    )

    std_prov = Provenance.from_adapter(
        result.provenance, task="change-detection",
        input_ids=[m1.path, m2.path],
        preprocessing=["geotiff-validate", "pair-co-registration-assert", "to_tensor+normalize[0.5]"],
    ).model_dump()
    provenance = {
        "slice": "temporal_vertical_slice",
        "stages": ["validate_geotiff", "check_pair_compatibility", "changeformer_adapter",
                   "spatial_stats", "evidence", "verify"],
        "standardized": std_prov,
        "t1": {"path": m1.path, "crs": m1.crs, "shape": [m1.height, m1.width]},
        "t2": {"path": m2.path, "crs": m2.crs, "shape": [m2.height, m2.width]},
        "co_registered": pair.co_registered,
        "adapter_provenance": result.provenance,
        "orchestration_runtime_s": round(time.time() - started, 3),
        "score_meaning": (
            "stats.changed_fraction is pixel coverage, not a confidence; "
            "this slice produces no confidence value"
        ),
    }

    return ChangeSliceResult(
        ok=True,
        errors=errors,  # non-fatal notes when strict=False
        t1_meta=m1,
        t2_meta=m2,
        t1_valid=v1.ok,
        t2_valid=v2.ok,
        validation_warnings=warnings,
        pair=pair,
        stats=stats,
        mask_path=mask_path,
        evidence=[ev],
        verification=vr,
        provenance=provenance,
    )
