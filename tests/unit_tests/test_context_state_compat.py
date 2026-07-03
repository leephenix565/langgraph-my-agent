from __future__ import annotations

import ast
from dataclasses import MISSING, fields
from pathlib import Path
from typing import Annotated, Dict, get_args, get_origin, get_type_hints

import react_agent.prompts as prompts
from react_agent.agent_types import AgentOutput
from react_agent.compat import context_state as metadata
from react_agent.context import Context
from react_agent.state import InputState, State, merge_analyst_results


def test_context_metadata_groups_cover_dataclass_fields() -> None:
    assert metadata.runtime_context_fields(Context) == metadata.CONTEXT_FIELDS
    assert set(metadata.CONTEXT_ACTIVE_FIELDS).isdisjoint(metadata.CONTEXT_COMPAT_FIELDS)
    assert set(metadata.CONTEXT_ACTIVE_FIELDS).isdisjoint(metadata.CONTEXT_LEGACY_FIELDS)
    assert set(metadata.CONTEXT_ACTIVE_FIELDS).isdisjoint(metadata.CONTEXT_MANUAL_FIELDS)
    assert set(metadata.CONTEXT_COMPAT_FIELDS).isdisjoint(metadata.CONTEXT_LEGACY_FIELDS)
    assert set(metadata.CONTEXT_COMPAT_FIELDS).isdisjoint(metadata.CONTEXT_MANUAL_FIELDS)
    assert set(metadata.CONTEXT_LEGACY_FIELDS).isdisjoint(metadata.CONTEXT_MANUAL_FIELDS)
    assert set(metadata.CONTEXT_FIELD_CLASSIFICATION) == set(metadata.CONTEXT_FIELDS)
    assert metadata.CONTEXT_DELETE_CANDIDATE_FIELDS == ()

    valid, reason = metadata.validate_context_field_classification(Context)
    assert valid, reason
    assert metadata.classify_context_field("enable_selected_routing") == metadata.ACTIVE
    assert metadata.classify_context_field("enable_llm_dimension_router") == metadata.ACTIVE
    assert metadata.classify_context_field("llm_dimension_router_mode") == metadata.ACTIVE
    assert metadata.classify_context_field("baseline_model") == metadata.COMPAT
    assert metadata.classify_context_field("router_model") == metadata.LEGACY
    assert (
        metadata.classify_context_field("non_l4_external_compute_optional_canary_allowlist")
        == metadata.MANUAL
    )
    assert metadata.classify_context_field("not_a_context_field") == metadata.UNKNOWN


def test_context_dataclass_surface_is_stable() -> None:
    fs = list(fields(Context))
    assert [field.name for field in fs] == list(metadata.CONTEXT_FIELDS)
    assert [
        (
            field.name,
            "<factory>" if field.default_factory is not MISSING else field.default,
            field.metadata["description"],
        )
        for field in fs
    ] == [
        ("model", "deepseek/deepseek-v4-flash", "Underlying chat model (provider/model)."),
        (
            "router_model",
            "",
            "Optional override for the Router model (provider/model). "
            "If empty, the Router uses `model`.",
        ),
        (
            "router_openai_base_url",
            "",
            "Optional OpenAI-compatible base URL for Router-only calls. "
            "If empty, Router uses global OPENAI_BASE_URL.",
        ),
        (
            "router_openai_api_key",
            "",
            "Optional OpenAI API key for Router-only calls. "
            "If empty, Router uses global OPENAI_API_KEY.",
        ),
        (
            "baseline_model",
            "",
            "Optional override for the baseline sidecar model (provider/model). "
            "If empty, baseline sidecar uses `model`.",
        ),
        (
            "baseline_openai_base_url",
            "",
            "Optional OpenAI-compatible base URL for baseline-sidecar calls. "
            "If empty, baseline sidecar uses the global provider/env path.",
        ),
        (
            "baseline_openai_api_key",
            "",
            "Optional OpenAI API key for baseline-sidecar calls. "
            "If empty, baseline sidecar uses the global provider/env path.",
        ),
        ("enable_fair_fusion", False, "Enable the isolated baseline sidecar shadow scaffold."),
        (
            "baseline_force_search",
            True,
            "Request force-search behavior in baseline sidecar metadata. "
            "FF-2A records the request but does not hard-bind provider-native search.",
        ),
        (
            "enable_fair_fusion_source_switch",
            False,
            "Enable final source switching across mainline/baseline/fused emit paths. "
            "Defaults off so the visible answer stays on the mainline path.",
        ),
        (
            "enable_selected_routing",
            False,
            "Enable provider-free selected fixed DAG routing. "
            "Defaults off so the active graph keeps the full DAG path.",
        ),
        (
            "enable_llm_dimension_router",
            False,
            "Enable the internal LLM dimension router seam. "
            "This is gated behind selected routing; real provider calls also require "
            "`llm_dimension_router_mode=real` and provider credentials.",
        ),
        (
            "llm_dimension_router_mode",
            "",
            "Optional LLM dimension router mode. Empty keeps the fake seam; "
            "`real` allows an explicitly enabled router to use the OpenAI-compatible "
            "router provider path.",
        ),
        (
            "enable_internal_llm_placeholders",
            False,
            "Enable default-off internal LLM placeholders for fixed-DAG L2 slots. "
            "Provider failures fall back to deterministic placeholders.",
        ),
        (
            "enable_external_compute_demo",
            False,
            "Enable the default-off fixed-DAG external compute demo bridge. "
            "The bridge only calls explicitly allowlisted production /v1/agent/compute endpoints.",
        ),
        (
            "enable_llm_report_synthesis",
            False,
            "Enable default-off LLM synthesis of the final fixed-DAG report from "
            "the public-safe report_input_bundle_v1.",
        ),
        (
            "llm_report_synthesis_model",
            "",
            "Optional override model for LLM report synthesis. "
            "If empty, report synthesis uses `model`.",
        ),
        (
            "enable_llm_l3_explanation",
            False,
            "Enable default-off LLM explanation of fixed-DAG L3 composites. "
            "This may add public-safe research_points but must not override fusion fields.",
        ),
        (
            "llm_l3_explanation_model",
            "",
            "Optional override model for LLM L3 explanation. "
            "If empty, L3 explanation uses `model`.",
        ),
        (
            "external_compute_demo_allowlist",
            (),
            "Fixed-DAG agent ids allowed for external compute demo calls. "
            "Empty by default, so enabling the bridge alone makes no HTTP calls.",
        ),
        ("external_compute_demo_timeout_seconds", 20.0, "Per-agent timeout for external compute demo calls."),
        (
            "disable_external_compute_default",
            False,
            "Disable runtime-binding external compute defaults for tests or rollback.",
        ),
        (
            "disable_non_l4_external_compute_default",
            False,
            "Disable production non-L4 external compute defaults for tests or rollback. "
            "This does not disable L4 external compute defaults.",
        ),
        (
            "non_l4_external_compute_optional_canary_allowlist",
            (),
            "Temporary canary-only optional non-L4 agent ids. Empty in normal production "
            "requests; source-controlled policy decides final default enablement.",
        ),
        (
            "fixed_dag_as_of",
            "",
            "Optional fixed-DAG planning as_of date. Empty keeps the default reset value.",
        ),
        ("run_id", "", "Optional run identifier for tracing/logging."),
        (
            "system_prompt",
            prompts.MANAGER_SYSTEM_PROMPT,
            "Top-level system prompt for the Manager agent. "
            "Router/Analyst prompts are sourced from prompts.py.",
        ),
        ("analyst_profiles", "<factory>", "Per-analyst system prompts keyed by analyst id."),
        (
            "max_search_results",
            10,
            "The maximum number of search results to return for each search query.",
        ),
    ]
    analyst_profiles_field = next(field for field in fs if field.name == "analyst_profiles")
    assert analyst_profiles_field.default_factory() == prompts.ANALYST_PROFILES
    assert analyst_profiles_field.default_factory() is not prompts.ANALYST_PROFILES

    hints = get_type_hints(Context, include_extras=True)
    assert get_origin(hints["model"]) is Annotated
    assert get_args(hints["model"]) == (str, {"__template_metadata__": {"kind": "llm"}})


def test_state_metadata_groups_cover_typeddict_fields() -> None:
    assert metadata.runtime_input_state_fields(InputState) == metadata.INPUT_STATE_FIELDS
    assert metadata.runtime_state_fields(State) == metadata.STATE_FIELDS
    assert metadata.runtime_all_state_fields(State) == metadata.STATE_ALL_FIELDS
    assert set(metadata.STATE_ACTIVE_FIELDS).isdisjoint(metadata.STATE_COMPAT_FIELDS)
    assert set(metadata.STATE_ACTIVE_FIELDS).isdisjoint(metadata.STATE_LEGACY_FIELDS)
    assert set(metadata.STATE_ACTIVE_FIELDS).isdisjoint(metadata.STATE_MANUAL_FIELDS)
    assert set(metadata.STATE_COMPAT_FIELDS).isdisjoint(metadata.STATE_LEGACY_FIELDS)
    assert set(metadata.STATE_COMPAT_FIELDS).isdisjoint(metadata.STATE_MANUAL_FIELDS)
    assert set(metadata.STATE_LEGACY_FIELDS).isdisjoint(metadata.STATE_MANUAL_FIELDS)
    assert set(metadata.STATE_FIELD_CLASSIFICATION) == set(metadata.STATE_ALL_FIELDS)
    assert metadata.STATE_DELETE_CANDIDATE_FIELDS == ()

    valid, reason = metadata.validate_state_field_classification(State, InputState)
    assert valid, reason
    assert metadata.classify_state_field("fixed_dag_plan") == metadata.ACTIVE
    assert metadata.classify_state_field("analyst_results") == metadata.COMPAT
    assert metadata.classify_state_field("fusion_verdict") == metadata.LEGACY
    assert metadata.classify_state_field("baseline_bundle") == metadata.MANUAL
    assert metadata.classify_state_field("not_a_state_field") == metadata.UNKNOWN


def test_inputstate_and_state_annotations_are_stable() -> None:
    assert list(InputState.__annotations__) == list(metadata.INPUT_STATE_FIELDS)
    assert (
        InputState.__annotations__["messages"].__forward_arg__
        == "Annotated[Sequence[AnyMessage], add_messages]"
    )
    assert InputState.__total__ is True
    assert InputState.__required_keys__ == frozenset({"messages"})
    assert InputState.__optional_keys__ == frozenset()

    assert list(State.__annotations__) == list(metadata.STATE_ALL_FIELDS)
    assert (
        State.__annotations__["analyst_results"].__forward_arg__
        == "Annotated[Dict[str, AgentOutput], merge_analyst_results]"
    )
    assert (
        State.__annotations__["ephemeral_results"].__forward_arg__
        == "Annotated[Dict[str, AgentOutput], merge_analyst_results]"
    )
    assert State.__total__ is False
    assert State.__required_keys__ == frozenset({"messages"})
    assert State.__optional_keys__ == frozenset(set(State.__annotations__) - {"messages"})


def test_state_reducers_are_stable() -> None:
    hints = get_type_hints(State, include_extras=True)

    analyst_base, analyst_reducer = get_args(hints["analyst_results"])
    ephemeral_base, ephemeral_reducer = get_args(hints["ephemeral_results"])

    assert get_origin(hints["analyst_results"]) is Annotated
    assert get_origin(hints["ephemeral_results"]) is Annotated
    assert analyst_base == Dict[str, AgentOutput]
    assert ephemeral_base == Dict[str, AgentOutput]
    assert analyst_reducer is merge_analyst_results
    assert ephemeral_reducer is merge_analyst_results
    assert metadata.runtime_state_reducers(State) == metadata.STATE_REDUCER_FIELDS


def test_merge_analyst_results_behavior_is_stable() -> None:
    left = {"alpha": {"analysis": "old"}}
    right = {"beta": {"analysis": "new"}}
    merged = merge_analyst_results(left, right)
    assert merged == {"alpha": {"analysis": "old"}, "beta": {"analysis": "new"}}
    assert left == {"alpha": {"analysis": "old"}}
    assert right == {"beta": {"analysis": "new"}}

    assert merge_analyst_results(
        {"same": {"analysis": "old"}},
        {"same": {"analysis": "new"}},
    ) == {"same": {"analysis": "new"}}

    assert merge_analyst_results(
        {"__reset__": {"analysis": "sentinel"}, "alpha": {"analysis": "old"}},
        {"beta": {"analysis": "new"}},
    ) == {"alpha": {"analysis": "old"}, "beta": {"analysis": "new"}}

    assert merge_analyst_results(
        {"alpha": {"analysis": "old"}},
        {"__reset__": {"analysis": "sentinel"}, "beta": {"analysis": "new"}},
    ) == {}


def test_compat_metadata_imports_do_not_touch_graph_or_public_modules() -> None:
    root = Path(__file__).resolve().parents[2]
    forbidden_modules = {
        "react_agent.graph",
        "react_agent.public_api",
        "react_agent.public_contracts",
        "react_agent.public_mapping",
        "react_agent.public_runtime",
    }
    source = (root / "src/react_agent/compat/context_state.py").read_text()
    tree = ast.parse(source)
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)

    assert forbidden_modules.isdisjoint(imported)

    for rel_path in (
        "src/react_agent/graph.py",
        "src/react_agent/public_api.py",
        "src/react_agent/public_contracts.py",
        "src/react_agent/public_mapping.py",
        "src/react_agent/public_runtime.py",
    ):
        module_source = (root / rel_path).read_text()
        assert "react_agent.compat" not in module_source
