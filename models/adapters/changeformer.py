"""ChangeFormer adapter — transformer-based change masks."""

from __future__ import annotations

from .base import AdapterRequest, AdapterResult, ModelAdapter


class ChangeFormerAdapter(ModelAdapter):
    name = "changeformer"
    tasks = ("change-detection",)
    modalities = ("optical-bitemporal",)

    def load(self) -> None:
        if self._model is not None:
            return
        # TODO: load changeformer weights from self.checkpoint onto self.device.
        raise NotImplementedError("changeformer weights not wired yet")

    def predict(self, request: AdapterRequest) -> AdapterResult:
        self.load()
        # TODO: run changeformer inference.
        raise NotImplementedError("changeformer inference not implemented")
