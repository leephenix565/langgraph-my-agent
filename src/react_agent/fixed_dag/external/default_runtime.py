"""Default-runtime external compute helpers."""

from __future__ import annotations

import os
from typing import Any

from react_agent.fixed_dag.external.types import ExternalComputeDemoEntry


def _timeout_from_context(context: Any, entry: ExternalComputeDemoEntry) -> float:
    raw = getattr(context, "external_compute_demo_timeout_seconds", entry.timeout_seconds)
    try:
        timeout = float(raw)
    except (TypeError, ValueError):
        return entry.timeout_seconds
    if timeout <= 0:
        return entry.timeout_seconds
    if (
        timeout == 20.0
        and entry.timeout_seconds != 20.0
        and "EXTERNAL_COMPUTE_DEMO_TIMEOUT_SECONDS" not in os.environ
    ):
        return entry.timeout_seconds
    return timeout


__all__ = []
