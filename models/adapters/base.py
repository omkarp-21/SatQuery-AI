"""Shared adapter interface for specialist models.

Every model in ``models/model_registry.yaml`` is reached through a subclass of
:class:`ModelAdapter`. The pipeline never imports a model directly.
"""

from __future__ import annotations

import abc
from dataclasses import dataclass, field
from typing import Any


@dataclass
class AdapterRequest:
    """Normalized input handed to an adapter by the specialists stage."""

    query: str
    images: list[Any] = field(default_factory=list)  # paths, arrays, or STAC items
    context: dict[str, Any] = field(default_factory=dict)


@dataclass
class AdapterResult:
    """Normalized output consumed by the fusion stage."""

    model: str
    answer: Any
    score: float | None = None
    artifacts: dict[str, Any] = field(default_factory=dict)  # masks, boxes, embeddings
    provenance: dict[str, Any] = field(default_factory=dict)


class ModelAdapter(abc.ABC):
    """Base class for all specialist adapters."""

    name: str = "base"
    tasks: tuple[str, ...] = ()
    modalities: tuple[str, ...] = ()

    def __init__(self, checkpoint: str, device: str = "cuda", **kwargs: Any) -> None:
        self.checkpoint = checkpoint
        self.device = device
        self.options = kwargs
        self._model: Any | None = None

    @abc.abstractmethod
    def load(self) -> None:
        """Lazily load weights onto ``self.device``."""

    @abc.abstractmethod
    def predict(self, request: AdapterRequest) -> AdapterResult:
        """Run inference and return a normalized result."""

    def capabilities(self) -> dict[str, Any]:
        return {"name": self.name, "tasks": self.tasks, "modalities": self.modalities}
