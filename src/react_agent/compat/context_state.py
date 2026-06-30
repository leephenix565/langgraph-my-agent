"""Context and State compatibility field metadata.

This module is metadata-only.  It does not import graph, public runtime,
public mapping, providers, endpoint clients, or environment values.
"""

from __future__ import annotations

from dataclasses import fields
from types import MappingProxyType
from typing import Any, Mapping

ACTIVE = "active"
COMPAT = "compat"
LEGACY = "legacy"
MANUAL = "manual"
UNKNOWN = "unknown"

CONTEXT_FIELDS: tuple[str, ...] = (
    "model",
    "router_model",
    "router_openai_base_url",
    "router_openai_api_key",
    "baseline_model",
    "baseline_openai_base_url",
    "baseline_openai_api_key",
    "enable_fair_fusion",
    "baseline_force_search",
    "enable_fair_fusion_source_switch",
    "enable_selected_routing",
    "enable_llm_dimension_router",
    "enable_internal_llm_placeholders",
    "enable_external_compute_demo",
    "enable_llm_report_synthesis",
    "llm_report_synthesis_model",
    "enable_llm_l3_explanation",
    "llm_l3_explanation_model",
    "external_compute_demo_allowlist",
    "external_compute_demo_timeout_seconds",
    "disable_external_compute_default",
    "disable_non_l4_external_compute_default",
    "non_l4_external_compute_optional_canary_allowlist",
    "fixed_dag_as_of",
    "run_id",
    "system_prompt",
    "analyst_profiles",
    "max_search_results",
)

CONTEXT_ACTIVE_FIELDS: tuple[str, ...] = (
    "model",
    "enable_selected_routing",
    "enable_llm_dimension_router",
    "enable_internal_llm_placeholders",
    "enable_external_compute_demo",
    "enable_llm_report_synthesis",
    "llm_report_synthesis_model",
    "enable_llm_l3_explanation",
    "llm_l3_explanation_model",
    "external_compute_demo_allowlist",
    "external_compute_demo_timeout_seconds",
    "disable_external_compute_default",
    "disable_non_l4_external_compute_default",
    "fixed_dag_as_of",
)
CONTEXT_COMPAT_FIELDS: tuple[str, ...] = (
    "baseline_model",
    "baseline_openai_base_url",
    "baseline_openai_api_key",
    "enable_fair_fusion",
    "baseline_force_search",
    "run_id",
    "max_search_results",
)
CONTEXT_LEGACY_FIELDS: tuple[str, ...] = (
    "router_model",
    "router_openai_base_url",
    "router_openai_api_key",
    "enable_fair_fusion_source_switch",
    "system_prompt",
    "analyst_profiles",
)
CONTEXT_MANUAL_FIELDS: tuple[str, ...] = (
    "non_l4_external_compute_optional_canary_allowlist",
)
CONTEXT_COMPAT_BOUNDARY_FIELDS: tuple[str, ...] = tuple(
    name
    for name in CONTEXT_FIELDS
    if name
    in set(CONTEXT_COMPAT_FIELDS) | set(CONTEXT_LEGACY_FIELDS) | set(CONTEXT_MANUAL_FIELDS)
)

CONTEXT_FIELD_CLASSIFICATION: Mapping[str, str] = MappingProxyType(
    {
        **{name: ACTIVE for name in CONTEXT_ACTIVE_FIELDS},
        **{name: COMPAT for name in CONTEXT_COMPAT_FIELDS},
        **{name: LEGACY for name in CONTEXT_LEGACY_FIELDS},
        **{name: MANUAL for name in CONTEXT_MANUAL_FIELDS},
    }
)
CONTEXT_DELETE_CANDIDATE_FIELDS: tuple[str, ...] = ()

INPUT_STATE_FIELDS: tuple[str, ...] = ("messages",)
STATE_FIELDS: tuple[str, ...] = (
    "fixed_dag_plan",
    "data_bundle",
    "entity_relation_bundle",
    "dag_execution",
    "dag_step_results",
    "execution_batches",
    "l2_conclusions",
    "dimension_results",
    "decision_result",
    "report_input_bundle",
    "report_result",
    "workflow_snapshot",
    "final_emit_payload",
    "emitted_bundle",
    "run_id",
    "current_question",
    "thread_summary",
    "stable_findings",
    "is_last_step",
    "analyst_results",
    "ephemeral_results",
    "multi_agent_bundle",
    "mainline_status",
    "mainline_emit_payload",
    "final_answer_source",
    "judge_status",
    "fusion_verdict",
    "writer_status",
    "writer_output",
    "baseline_status",
    "baseline_bundle",
    "plan",
    "fanout_targets",
    "layer_plan",
    "layer_mode",
    "current_layer",
    "layer_done",
    "chain_cursor",
)
STATE_ALL_FIELDS: tuple[str, ...] = INPUT_STATE_FIELDS + STATE_FIELDS

STATE_ACTIVE_FIELDS: tuple[str, ...] = (
    "messages",
    "fixed_dag_plan",
    "data_bundle",
    "entity_relation_bundle",
    "dag_execution",
    "dag_step_results",
    "execution_batches",
    "l2_conclusions",
    "dimension_results",
    "decision_result",
    "report_input_bundle",
    "report_result",
    "workflow_snapshot",
    "final_emit_payload",
    "emitted_bundle",
    "run_id",
    "current_question",
    "thread_summary",
    "stable_findings",
    "is_last_step",
    "multi_agent_bundle",
    "final_answer_source",
)
STATE_COMPAT_FIELDS: tuple[str, ...] = (
    "analyst_results",
    "ephemeral_results",
    "layer_plan",
    "layer_mode",
    "current_layer",
)
STATE_LEGACY_FIELDS: tuple[str, ...] = (
    "mainline_status",
    "mainline_emit_payload",
    "judge_status",
    "fusion_verdict",
    "writer_status",
    "writer_output",
    "plan",
    "fanout_targets",
    "layer_done",
    "chain_cursor",
)
STATE_MANUAL_FIELDS: tuple[str, ...] = (
    "baseline_status",
    "baseline_bundle",
)
STATE_COMPAT_BOUNDARY_FIELDS: tuple[str, ...] = tuple(
    name
    for name in STATE_ALL_FIELDS
    if name in set(STATE_COMPAT_FIELDS) | set(STATE_LEGACY_FIELDS) | set(STATE_MANUAL_FIELDS)
)

STATE_FIELD_CLASSIFICATION: Mapping[str, str] = MappingProxyType(
    {
        **{name: ACTIVE for name in STATE_ACTIVE_FIELDS},
        **{name: COMPAT for name in STATE_COMPAT_FIELDS},
        **{name: LEGACY for name in STATE_LEGACY_FIELDS},
        **{name: MANUAL for name in STATE_MANUAL_FIELDS},
    }
)
STATE_FIELD_OWNER: Mapping[str, str] = MappingProxyType(
    {**{name: "InputState" for name in INPUT_STATE_FIELDS}, **{name: "State" for name in STATE_FIELDS}}
)
STATE_REDUCER_FIELDS: Mapping[str, str] = MappingProxyType(
    {
        "messages": "add_messages",
        "analyst_results": "merge_analyst_results",
        "ephemeral_results": "merge_analyst_results",
    }
)
STATE_DELETE_CANDIDATE_FIELDS: tuple[str, ...] = ()


def classify_context_field(name: str) -> str:
    """Return the M3 classification for a Context field name."""
    return CONTEXT_FIELD_CLASSIFICATION.get(name, UNKNOWN)


def classify_state_field(name: str) -> str:
    """Return the M3 classification for an InputState/State field name."""
    return STATE_FIELD_CLASSIFICATION.get(name, UNKNOWN)


def runtime_context_fields(context_cls: type[Any] | None = None) -> tuple[str, ...]:
    """Return dataclass field names from Context without instantiating it."""
    if context_cls is None:
        from react_agent.context import Context

        context_cls = Context
    return tuple(field.name for field in fields(context_cls))


def runtime_input_state_fields(input_state_cls: type[Any] | None = None) -> tuple[str, ...]:
    """Return InputState annotation names in declaration order."""
    if input_state_cls is None:
        from react_agent.state import InputState

        input_state_cls = InputState
    return tuple(input_state_cls.__annotations__)


def runtime_state_fields(state_cls: type[Any] | None = None) -> tuple[str, ...]:
    """Return State-only annotation names in declaration order."""
    if state_cls is None:
        from react_agent.state import State

        state_cls = State
    return tuple(name for name in state_cls.__annotations__ if name not in INPUT_STATE_FIELDS)


def runtime_all_state_fields(state_cls: type[Any] | None = None) -> tuple[str, ...]:
    """Return InputState + State annotation names in runtime order."""
    if state_cls is None:
        from react_agent.state import State

        state_cls = State
    return tuple(state_cls.__annotations__)


def runtime_state_reducers(state_cls: type[Any] | None = None) -> Mapping[str, str]:
    """Return reducer metadata for fields that intentionally have reducers."""
    if state_cls is None:
        from react_agent.state import State

        state_cls = State
    annotation_names = set(state_cls.__annotations__)
    return MappingProxyType(
        {name: reducer for name, reducer in STATE_REDUCER_FIELDS.items() if name in annotation_names}
    )


def _disjoint(*groups: tuple[str, ...]) -> bool:
    seen: set[str] = set()
    for group in groups:
        group_set = set(group)
        if seen & group_set:
            return False
        seen.update(group_set)
    return True


def validate_context_field_classification(
    context_cls: type[Any] | None = None,
) -> tuple[bool, str]:
    """Validate Context metadata against the live dataclass field surface."""
    live_fields = runtime_context_fields(context_cls)
    if live_fields != CONTEXT_FIELDS:
        return False, "context_field_order_mismatch"
    if not _disjoint(
        CONTEXT_ACTIVE_FIELDS,
        CONTEXT_COMPAT_FIELDS,
        CONTEXT_LEGACY_FIELDS,
        CONTEXT_MANUAL_FIELDS,
    ):
        return False, "context_groups_not_disjoint"
    if set(CONTEXT_FIELD_CLASSIFICATION) != set(CONTEXT_FIELDS):
        return False, "context_classification_field_set_mismatch"
    if CONTEXT_DELETE_CANDIDATE_FIELDS:
        return False, "context_delete_candidates_present"
    return True, "ok"


def validate_state_field_classification(
    state_cls: type[Any] | None = None,
    input_state_cls: type[Any] | None = None,
) -> tuple[bool, str]:
    """Validate InputState/State metadata against the live TypedDict surface."""
    live_input_fields = runtime_input_state_fields(input_state_cls)
    live_all_fields = runtime_all_state_fields(state_cls)
    live_state_fields = tuple(name for name in live_all_fields if name not in live_input_fields)
    if live_input_fields != INPUT_STATE_FIELDS:
        return False, "input_state_field_order_mismatch"
    if live_state_fields != STATE_FIELDS:
        return False, "state_field_order_mismatch"
    if live_all_fields != STATE_ALL_FIELDS:
        return False, "state_all_field_order_mismatch"
    if not _disjoint(
        STATE_ACTIVE_FIELDS,
        STATE_COMPAT_FIELDS,
        STATE_LEGACY_FIELDS,
        STATE_MANUAL_FIELDS,
    ):
        return False, "state_groups_not_disjoint"
    if set(STATE_FIELD_CLASSIFICATION) != set(STATE_ALL_FIELDS):
        return False, "state_classification_field_set_mismatch"
    if STATE_DELETE_CANDIDATE_FIELDS:
        return False, "state_delete_candidates_present"
    return True, "ok"


__all__ = [
    "ACTIVE",
    "COMPAT",
    "CONTEXT_ACTIVE_FIELDS",
    "CONTEXT_COMPAT_BOUNDARY_FIELDS",
    "CONTEXT_COMPAT_FIELDS",
    "CONTEXT_DELETE_CANDIDATE_FIELDS",
    "CONTEXT_FIELD_CLASSIFICATION",
    "CONTEXT_FIELDS",
    "CONTEXT_LEGACY_FIELDS",
    "CONTEXT_MANUAL_FIELDS",
    "INPUT_STATE_FIELDS",
    "LEGACY",
    "MANUAL",
    "STATE_ACTIVE_FIELDS",
    "STATE_ALL_FIELDS",
    "STATE_COMPAT_BOUNDARY_FIELDS",
    "STATE_COMPAT_FIELDS",
    "STATE_DELETE_CANDIDATE_FIELDS",
    "STATE_FIELD_CLASSIFICATION",
    "STATE_FIELD_OWNER",
    "STATE_FIELDS",
    "STATE_LEGACY_FIELDS",
    "STATE_MANUAL_FIELDS",
    "STATE_REDUCER_FIELDS",
    "UNKNOWN",
    "classify_context_field",
    "classify_state_field",
    "runtime_all_state_fields",
    "runtime_context_fields",
    "runtime_input_state_fields",
    "runtime_state_fields",
    "runtime_state_reducers",
    "validate_context_field_classification",
    "validate_state_field_classification",
]
