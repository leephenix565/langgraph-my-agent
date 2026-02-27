"""Define the state structures for the multi-agent graph."""

from __future__ import annotations

from typing import Dict, List, Sequence

from langchain_core.messages import AnyMessage
from langgraph.graph import add_messages
from typing_extensions import Annotated, TypedDict

from react_agent.agents import AgentOutput


def merge_analyst_results(a: Dict[str, AgentOutput], b: Dict[str, AgentOutput]) -> Dict[str, AgentOutput]:
    """Merge analyst_results from parallel branches; allow explicit reset."""
    # If a branch requests reset, drop previous results for a fresh turn.
    if "__reset__" in b:
        return {}

    merged = dict(a)
    merged.update(b)
    merged.pop("__reset__", None)
    return merged


class InputState(TypedDict):
    """External inputs to the graph."""

    messages: Annotated[Sequence[AnyMessage], add_messages]


class State(InputState, total=False):
    """Internal state shared by Router -> Manager -> Agents."""

    plan: List[str]
    analyst_results: Annotated[Dict[str, AgentOutput], merge_analyst_results]
    run_id: str
    is_last_step: bool
    current_question: str
    fanout_targets: List[str]
    layer_plan: Dict[str, List[str]]
    layer_mode: Dict[str, str]
    current_layer: str
    layer_done: Dict[str, bool]
    chain_cursor: int
    thread_summary: str
