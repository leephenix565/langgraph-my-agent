"""Observability helpers shared by the layered graph runtime."""

from __future__ import annotations

import time
from typing import Any, Dict


def _truncate(text: str, limit: int = 4000) -> str:
    if not isinstance(text, str):
        text = str(text)
    return text if len(text) <= limit else text[: limit - 8] + "...[trunc]"


def _elapsed_ms(started_at: float) -> float:
    return round((time.perf_counter() - started_at) * 1000.0, 3)


def _model_trace_fields(model_spec: str, prefix: str = "model") -> Dict[str, str]:
    spec = str(model_spec or "")
    provider = ""
    name = spec
    if "/" in spec:
        provider, name = spec.split("/", maxsplit=1)
    return {
        f"{prefix}_spec": spec,
        f"{prefix}_provider": provider,
        f"{prefix}_name": name,
    }


def _log_node_latency(logger: Any, node: str, started_at: float, **fields: Any) -> None:
    """Emit lightweight node latency trace without affecting runtime semantics."""
    logger.log_event("node_latency", node=node, elapsed_ms=_elapsed_ms(started_at), **fields)
