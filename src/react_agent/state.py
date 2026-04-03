"""Define the state structures for the multi-agent graph."""

from __future__ import annotations

from typing import Any, Dict, List, Sequence

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
    ephemeral_results: Annotated[Dict[str, AgentOutput], merge_analyst_results]
    multi_agent_bundle: Dict[str, Any]
    mainline_status: str
    mainline_emit_payload: Dict[str, Any]
    final_answer_source: str
    judge_status: str
    fusion_verdict: Dict[str, Any]
    writer_status: str
    writer_output: Dict[str, Any]
    final_emit_payload: Dict[str, Any]
    emitted_bundle: Dict[str, Any]
    baseline_status: str
    baseline_bundle: Dict[str, Any]
    stable_findings: List[Dict[str, Any]]
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
