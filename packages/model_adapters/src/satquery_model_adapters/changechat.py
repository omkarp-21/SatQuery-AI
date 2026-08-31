"""ChangeChat adapter — instruction-tuned change conversation."""

from __future__ import annotations

from .base import AdapterRequest, AdapterResult, ModelAdapter


class ChangeChatAdapter(ModelAdapter):
    name = "changechat"
    tasks = ("change-captioning", "change-vqa")
    modalities = ("optical-bitemporal",)

    def load(self) -> None:
        if self._model is not None:
            return
        # TODO: load changechat weights from self.checkpoint onto self.device.
        raise NotImplementedError("changechat weights not wired yet")

    def predict(self, request: AdapterRequest) -> AdapterResult:
        self.load()
        # TODO: run changechat inference.
        raise NotImplementedError("changechat inference not implemented")
