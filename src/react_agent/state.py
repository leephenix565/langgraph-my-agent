"""State structures for the fixed-DAG reset graph."""

from __future__ import annotations

from typing import Any, Dict, List, Sequence

from langchain_core.messages import AnyMessage
from langgraph.graph import add_messages
from typing_extensions import Annotated, TypedDict

from react_agent.agent_types import AgentOutput


def merge_analyst_results(
    a: Dict[str, AgentOutput], b: Dict[str, AgentOutput]
) -> Dict[str, AgentOutput]:
    """Merge result pools from parallel branches; allow explicit reset."""
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
    """Internal state shared by the Phase R3 fixed DAG executor skeleton."""

    fixed_dag_plan: Dict[str, Any]
    data_bundle: Dict[str, Any]
    entity_relation_bundle: Dict[str, Any]
    dag_execution: Dict[str, Any]
    _execution_plan: Dict[str, Any]
    _batches: List[List[str]]
    _step_results: Dict[str, Any]
    _fallback_used: bool
    _fallback_reason: str
    dag_step_results: Dict[str, Any]
    execution_batches: List[List[str]]
    l2_conclusions: Dict[str, Any]
    dimension_results: Dict[str, Any]
    decision_result: Dict[str, Any]
    report_input_bundle: Dict[str, Any]
    report_result: Dict[str, Any]
    workflow_snapshot: Dict[str, Any]
    final_emit_payload: Dict[str, Any]
    emitted_bundle: Dict[str, Any]
    run_id: str
    current_question: str
    thread_summary: str
    stable_findings: List[Dict[str, Any]]
    is_last_step: bool

    # Compatibility pools retained for non-reset helper tests and external
    # wrapper infrastructure.  The active fixed-DAG graph does not project or
    # write legacy layer/mode/fusion fields.
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
    baseline_status: str
    baseline_bundle: Dict[str, Any]
    plan: List[str]
    fanout_targets: List[str]
    layer_plan: Dict[str, List[str]]
    layer_mode: Dict[str, str]
    current_layer: str
    layer_done: Dict[str, bool]
    chain_cursor: int
