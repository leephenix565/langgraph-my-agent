"""Define the state structures for the multi-agent graph."""

from __future__ import annotations

from typing import Dict, List, Sequence

from langchain_core.messages import AnyMessage
from langgraph.graph import add_messages
from typing_extensions import Annotated, TypedDict

from react_agent.agents import AgentOutput


def merge_analyst_results(a: Dict[str, AgentOutput], b: Dict[str, AgentOutput]) -> Dict[str, AgentOutput]:
    """Merge analyst_results from parallel branches; later branch wins on conflicts."""
    merged = dict(a)
    merged.update(b)
    return merged


class InputState(TypedDict):
    """External inputs to the graph."""

    messages: Annotated[Sequence[AnyMessage], add_messages]


class State(InputState, total=False):
    """Internal state shared by Router -> Manager -> Agents."""

    plan: List[str]
    analyst_results: Annotated[Dict[str, AgentOutput], merge_analyst_results]
    is_last_step: bool
