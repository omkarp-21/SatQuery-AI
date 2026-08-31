"""satquery_geospatial — SatQuery geospatial engine.

Raster/vector I/O, metadata validation, pair co-registration checks. Stands alone
(no internal deps — ADR-001).
"""

__version__ = "0.1.0"

from .errors import (
    GeospatialError,
    MissingCRSError,
    PairNotCoRegisteredError,
    PathNotAllowedError,
    RasterTooLargeError,
    UnreadableRasterError,
)
from .raster import RasterMeta, read_raster_meta
from .validation import (
    Check,
    GeoValidationResult,
    PairCompatibility,
    check_pair_compatibility,
    validate_geotiff,
)

__all__ = [
    "GeospatialError",
    "UnreadableRasterError",
    "RasterTooLargeError",
    "MissingCRSError",
    "PathNotAllowedError",
    "PairNotCoRegisteredError",
    "RasterMeta",
    "read_raster_meta",
    "Check",
    "GeoValidationResult",
    "PairCompatibility",
    "validate_geotiff",
    "check_pair_compatibility",
]
