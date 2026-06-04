"""Shared agent input/output typing with no legacy registry imports."""

from __future__ import annotations

from typing import Any, Dict, List

from typing_extensions import TypedDict


class AgentInput(Dict[str, Any]):
    """Lightweight dict-compatible AgentInput schema."""

    question: str
    subtask: str
    shared_context: Dict[str, Any]
    history: List[Dict[str, Any]]
    tools_config: Dict[str, Any]


class AgentOutput(TypedDict, total=False):
    """Dict-shaped Agent output surface used by runtime and Studio schema export.

    Runtime callers still pass and consume plain dict objects. This type surface
    only narrows the commonly-used keys so Pydantic / LangGraph can emit a JSON
    schema for Studio without changing the graph's dict-style behavior.
    """

    analysis: str
    key_points: List[str]
    evidence: List[str]
    confidence: float
    parse_ok: bool
    contract: Dict[str, Any] | str


__all__ = ["AgentInput", "AgentOutput"]
