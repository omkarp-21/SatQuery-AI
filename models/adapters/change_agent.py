"""Change-Agent adapter — agentic bitemporal change analysis."""

from __future__ import annotations

from .base import AdapterRequest, AdapterResult, ModelAdapter


class ChangeAgentAdapter(ModelAdapter):
    name = "change_agent"
    tasks = ("change-detection", "change-captioning", "multi-turn")
    modalities = ("optical-bitemporal",)

    def load(self) -> None:
        if self._model is not None:
            return
        # TODO: load change_agent weights from self.checkpoint onto self.device.
        raise NotImplementedError("change_agent weights not wired yet")

    def predict(self, request: AdapterRequest) -> AdapterResult:
        self.load()
        # TODO: run change_agent inference.
        raise NotImplementedError("change_agent inference not implemented")
