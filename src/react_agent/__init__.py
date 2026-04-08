"""Router -> Manager -> Analysts LangGraph demo."""

from __future__ import annotations

from importlib import import_module
from typing import Any

__all__ = ["graph", "graph_app"]


def __getattr__(name: str) -> Any:
    if name in {"graph", "graph_app"}:
        module = import_module("react_agent.graph")
        return module if name == "graph" else module.graph
    raise AttributeError(f"module 'react_agent' has no attribute {name!r}")
