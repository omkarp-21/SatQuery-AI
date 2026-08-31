"""Typed errors for the geospatial engine.

`GeospatialError` is the package-local base. `packages/core` re-exports a common
`SatQueryError` hierarchy; geospatial stays dependency-free (ADR-001) so it keeps
its own base and callers can catch either.
"""

from __future__ import annotations


class GeospatialError(Exception):
    """Base for every geospatial failure. Carries a machine code + message."""

    code: str = "geospatial_error"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class UnreadableRasterError(GeospatialError):
    """The file could not be opened as a raster (bad format, truncated, missing)."""

    code = "unreadable_raster"


class RasterTooLargeError(GeospatialError):
    """Raster exceeds the configured pixel/band budget (decompression-bomb guard)."""

    code = "raster_too_large"


class MissingCRSError(GeospatialError):
    """Raster has no coordinate reference system and one is required for this op."""

    code = "missing_crs"


class PathNotAllowedError(GeospatialError):
    """Resolved path escapes the allow-listed base directory."""

    code = "path_not_allowed"


class PairNotCoRegisteredError(GeospatialError):
    """Two rasters are not on an identical grid; paired analysis is unsafe."""

    code = "pair_not_co_registered"
