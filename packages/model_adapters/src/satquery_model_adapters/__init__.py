"""satquery_model_adapters — standard SpecialistAdapter interface + implementations.

Product code. Adapters run inference in isolated per-model envs (`.venvs/<model>`)
via subprocess; no research-repo internals are imported here.
"""

__version__ = "0.1.0"

from .base import (
    AdapterRequest,
    AdapterResult,
    ModelAdapter,  # back-compat alias for SpecialistAdapter
    NormalizedOutput,
    RawOutput,
    SpecialistAdapter,
)
from .changeformer import ChangeFormerAdapter
from .croma import CromaAdapter
from .dofa import DofaAdapter
from .errors import (
    AdapterConfigError,
    AdapterError,
    AdapterExecutionError,
    UnsupportedModalityError,
    UnsupportedTaskError,
)
from .remoteclip import RemoteClipAdapter
from .remotesam import RemoteSamAdapter
from .tinyrs import TinyRsAdapter

#: name -> adapter class, for the registry loader.
ADAPTERS: dict[str, type[SpecialistAdapter]] = {
    ChangeFormerAdapter.name: ChangeFormerAdapter,
    RemoteClipAdapter.name: RemoteClipAdapter,
    CromaAdapter.name: CromaAdapter,
    DofaAdapter.name: DofaAdapter,
    RemoteSamAdapter.name: RemoteSamAdapter,
    TinyRsAdapter.name: TinyRsAdapter,
}

__all__ = [
    "AdapterRequest",
    "AdapterResult",
    "NormalizedOutput",
    "RawOutput",
    "SpecialistAdapter",
    "ModelAdapter",
    "ChangeFormerAdapter",
    "RemoteClipAdapter",
    "CromaAdapter",
    "DofaAdapter",
    "RemoteSamAdapter",
    "TinyRsAdapter",
    "ADAPTERS",
    "AdapterError",
    "AdapterConfigError",
    "AdapterExecutionError",
    "UnsupportedTaskError",
    "UnsupportedModalityError",
]
