"""GeoTIFF ingestion + compatibility validation (the geospatial vertical slice).

Contract:
    ``validate_geotiff(path, ...)`` -> :class:`GeoValidationResult`
        format check, dimensions, CRS, transform, bounds, bands, NoData.
    ``check_pair_compatibility(a, b)`` -> :class:`PairCompatibility`
        whether two rasters sit on an identical grid (required before any
        bi-temporal / paired analysis — `.claude/rules/geospatial.md`).

    side effects: opens files read-only.
    failure modes: typed :class:`~.errors.GeospatialError` subclasses; a *readable*
        raster that merely fails checks returns ``ok=False``, it does not raise.
"""

from __future__ import annotations

import math
from pathlib import Path

from pydantic import BaseModel

from .errors import (
    PathNotAllowedError,
    RasterTooLargeError,
    UnreadableRasterError,
)
from .raster import RasterMeta, read_raster_meta

# Conservative default caps (decompression-bomb guard — `.claude/rules/security.md`).
MAX_PIXELS = 200_000_000  # width * height * bands
MAX_BANDS = 512
TRANSFORM_TOL = 1e-6  # world units, for pair-grid comparison
RES_TOL = 1e-6


class Check(BaseModel):
    name: str
    passed: bool
    detail: str


class GeoValidationResult(BaseModel):
    path: str
    ok: bool
    meta: RasterMeta | None
    checks: list[Check]
    warnings: list[str]

    def failed(self) -> list[Check]:
        return [c for c in self.checks if not c.passed]


class PairCompatibility(BaseModel):
    co_registered: bool
    same_crs: bool
    same_shape: bool
    same_transform: bool
    same_resolution: bool
    mismatches: list[str]


def _resolve(path: str | Path, allowed_base_dir: str | Path | None) -> Path:
    p = Path(path).resolve()
    if allowed_base_dir is not None:
        base = Path(allowed_base_dir).resolve()
        if base not in p.parents and p != base:
            raise PathNotAllowedError(f"{p} is outside the allowed base {base}")
    return p


def validate_geotiff(
    path: str | Path,
    *,
    allowed_base_dir: str | Path | None = None,
    max_pixels: int = MAX_PIXELS,
    max_bands: int = MAX_BANDS,
    require_crs: bool = False,
) -> GeoValidationResult:
    """Validate a single GeoTIFF and return a structured result.

    Raises only for conditions that make the file unusable or unsafe
    (unreadable, path traversal, over the pixel/band budget). Everything else is
    reported as a failing :class:`Check` with ``ok=False``.
    """
    p = _resolve(path, allowed_base_dir)
    checks: list[Check] = []
    warnings: list[str] = []

    if not p.exists():
        raise UnreadableRasterError(f"no such file: {p}")

    meta = read_raster_meta(p)  # raises UnreadableRasterError on non-rasters
    checks.append(Check(name="format_readable", passed=True, detail=f"driver={meta.driver}"))

    # --- bomb guard (raise: unsafe to proceed) ---
    if meta.count > max_bands:
        raise RasterTooLargeError(f"{meta.count} bands exceeds cap {max_bands}")
    if meta.pixel_count > max_pixels:
        raise RasterTooLargeError(
            f"{meta.width}x{meta.height}x{meta.count} = {meta.pixel_count} px exceeds cap {max_pixels}"
        )

    # --- dimensions ---
    dims_ok = meta.width > 0 and meta.height > 0
    checks.append(
        Check(name="dimensions", passed=dims_ok, detail=f"{meta.width}x{meta.height}")
    )

    # --- bands ---
    checks.append(Check(name="bands", passed=meta.count >= 1, detail=f"count={meta.count}"))

    # --- CRS ---
    has_crs = meta.crs is not None
    crs_passed = has_crs or not require_crs
    checks.append(
        Check(
            name="crs_present",
            passed=crs_passed,
            detail=(meta.crs or "MISSING") + ("" if has_crs else " (no CRS tag)"),
        )
    )
    if not has_crs:
        warnings.append("raster has no CRS — cannot reproject or compute area")

    # --- transform ---
    a, b, c, d, e, f = meta.transform
    is_identity = (a, b, c, d, e, f) == (1.0, 0.0, 0.0, 0.0, 1.0, 0.0)
    det = a * e - b * d
    transform_ok = (not is_identity) and abs(det) > 0.0 and math.isfinite(det)
    checks.append(
        Check(
            name="transform_valid",
            passed=transform_ok,
            detail=f"det={det:.3g}" + (" (identity!)" if is_identity else ""),
        )
    )
    if is_identity:
        warnings.append("affine transform is the identity — pixel coords only, not georeferenced")

    # --- bounds ---
    left, bottom, right, top = meta.bounds
    bounds_ok = right > left and top > bottom and all(math.isfinite(v) for v in meta.bounds)
    checks.append(
        Check(name="bounds", passed=bounds_ok, detail=f"({left:.6g},{bottom:.6g},{right:.6g},{top:.6g})")
    )

    # --- NoData (informational; not a failure) ---
    checks.append(
        Check(
            name="nodata",
            passed=True,
            detail=("set: " + repr(meta.nodata)) if meta.nodata is not None else "not set",
        )
    )
    if meta.nodata is None:
        warnings.append("NoData value not set — masking must be handled explicitly downstream")

    ok = all(c.passed for c in checks)
    return GeoValidationResult(path=str(p), ok=ok, meta=meta, checks=checks, warnings=warnings)


def check_pair_compatibility(a: RasterMeta, b: RasterMeta) -> PairCompatibility:
    """Are two rasters on an identical grid? Gate before bi-temporal analysis."""
    mismatches: list[str] = []

    same_crs = (a.crs or "") == (b.crs or "")
    if not same_crs:
        mismatches.append(f"CRS differs: {a.crs!r} vs {b.crs!r}")

    same_shape = (a.width, a.height) == (b.width, b.height)
    if not same_shape:
        mismatches.append(f"shape differs: {a.width}x{a.height} vs {b.width}x{b.height}")

    same_transform = all(abs(x - y) <= TRANSFORM_TOL for x, y in zip(a.transform, b.transform))
    if not same_transform:
        mismatches.append(f"affine transform differs beyond {TRANSFORM_TOL}")

    same_res = all(abs(x - y) <= RES_TOL for x, y in zip(a.res, b.res))
    if not same_res:
        mismatches.append(f"resolution differs: {a.res} vs {b.res}")

    co_registered = same_crs and same_shape and same_transform
    return PairCompatibility(
        co_registered=co_registered,
        same_crs=same_crs,
        same_shape=same_shape,
        same_transform=same_transform,
        same_resolution=same_res,
        mismatches=mismatches,
    )
