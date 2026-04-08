"""Local shim package to allow src/ layout imports without installation."""

from __future__ import annotations

from importlib import import_module
from pathlib import Path
from typing import Any

_HERE = Path(__file__).resolve().parent
_SRC_PKG = _HERE.parent / "src" / "react_agent"
if _SRC_PKG.exists():
    __path__.append(str(_SRC_PKG))  # type: ignore[name-defined]

__all__ = ["graph", "graph_app"]


def __getattr__(name: str) -> Any:
    if name in {"graph", "graph_app"}:
        module = import_module("react_agent.graph")
        return module if name == "graph" else module.graph
    raise AttributeError(f"module 'react_agent' has no attribute {name!r}")
