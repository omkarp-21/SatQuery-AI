"""GeoChat adapter — conversational VQA and visual grounding on single RS images."""

from __future__ import annotations

from .base import AdapterRequest, AdapterResult, ModelAdapter


class GeoChatAdapter(ModelAdapter):
    name = "geochat"
    tasks = ("vqa", "grounding", "region-captioning")
    modalities = ("optical-single",)

    def load(self) -> None:
        if self._model is not None:
            return
        # TODO: load geochat weights from self.checkpoint onto self.device.
        raise NotImplementedError("geochat weights not wired yet")

    def predict(self, request: AdapterRequest) -> AdapterResult:
        self.load()
        # TODO: run geochat inference.
        raise NotImplementedError("geochat inference not implemented")
