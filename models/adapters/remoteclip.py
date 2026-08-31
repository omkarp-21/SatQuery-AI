"""RemoteCLIP adapter — RS-tuned CLIP for retrieval and embeddings."""

from __future__ import annotations

from .base import AdapterRequest, AdapterResult, ModelAdapter


class RemoteClipAdapter(ModelAdapter):
    name = "remoteclip"
    tasks = ("retrieval", "zero-shot-classification", "embedding")
    modalities = ("optical-single",)

    def load(self) -> None:
        if self._model is not None:
            return
        # TODO: load remoteclip weights from self.checkpoint onto self.device.
        raise NotImplementedError("remoteclip weights not wired yet")

    def predict(self, request: AdapterRequest) -> AdapterResult:
        self.load()
        # TODO: run remoteclip inference.
        raise NotImplementedError("remoteclip inference not implemented")
