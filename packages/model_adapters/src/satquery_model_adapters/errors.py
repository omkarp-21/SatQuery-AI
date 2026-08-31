"""Typed errors raised by specialist adapters."""

from __future__ import annotations


class AdapterError(Exception):
    code = "adapter_error"


class UnsupportedTaskError(AdapterError):
    """The upstream model does not support the requested task. Never approximated."""

    code = "unsupported_task"


class UnsupportedModalityError(AdapterError):
    """Wrong modality for this model (e.g. SAR handed to an optical-only model)."""

    code = "unsupported_modality"


class AdapterConfigError(AdapterError):
    """Adapter is missing a required path / env var (venv python, checkpoint, ...)."""

    code = "adapter_config"


class AdapterExecutionError(AdapterError):
    """The underlying inference process failed, timed out, or returned garbage."""

    code = "adapter_execution"
