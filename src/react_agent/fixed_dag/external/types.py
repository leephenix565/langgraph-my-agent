"""Types for fixed-DAG external compute boundaries."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ExternalComputeDemoEntry:
    """Demo/default endpoint metadata for one fixed-DAG compute candidate."""

    agent_id: str
    base_url: str
    compute_path: str
    expected_payload: str
    dimension: str
    external_agent_id: str
    default_target: str = "600519.SH"
    timeout_seconds: float = 20.0


Transport = Callable[
    [ExternalComputeDemoEntry, Mapping[str, Any], float],
    Mapping[str, Any],
]


__all__ = ["ExternalComputeDemoEntry", "Transport"]
