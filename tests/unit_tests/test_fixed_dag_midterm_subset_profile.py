import json
from pathlib import Path

import pytest
from pydantic import ValidationError

import react_agent.graph as graph_module
from react_agent.context import Context
from react_agent.fixed_dag.deploy_profiles import (
    DEPLOYMENT_PROFILE_ENV_VAR,
    MIDTERM_SUBSET_DEFERRED_AGENT_IDS,
    MIDTERM_SUBSET_PROFILE,
    MIDTERM_SUBSET_REQUIRED_DEPENDENCY_AGENT_IDS,
    MIDTERM_SUBSET_SELECTED_DIMENSIONS,
    MIDTERM_SUBSET_SELECTED_L2_AGENT_IDS,
)
from react_agent.fixed_dag_contracts import (
    FIXED_DAG_SCHEMA_VERSION,
    RESET_RUNTIME_AGENT_IDS,
    SELECTED_FIXED_DAG_SCHEMA_VERSION,
)
from react_agent.fixed_dag_executor import (
    execute_fixed_dag_plan,
    validate_selected_dag_steps,
)
from react_agent.public_contracts import PublicRoutingRequest
from react_agent.public_mapping import build_workflow_snapshot


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _profile_plan(question: str = "分析 600519.SH 的中期研判范围。") -> dict[str, object]:
    return graph_module._route_plan_for_context(  # noqa: SLF001
        question,
        Context(fixed_dag_deployment_profile=MIDTERM_SUBSET_PROFILE),
    )


def test_midterm_subset_profile_is_default_off(monkeypatch) -> None:
    monkeypatch.delenv(DEPLOYMENT_PROFILE_ENV_VAR, raising=False)

    plan = graph_module._route_plan_for_context("q", Context())  # noqa: SLF001

    assert plan["schema"] == FIXED_DAG_SCHEMA_VERSION
    assert plan["target_agent_ids"] == list(RESET_RUNTIME_AGENT_IDS)
    provenance = plan["provenance"]
    assert provenance["provider_invoked"] is False
    assert provenance["external_invoked"] is False
    assert "deployment_profile" not in provenance


def test_midterm_subset_profile_env_compiles_selected_agent_plan(monkeypatch) -> None:
    monkeypatch.setenv(DEPLOYMENT_PROFILE_ENV_VAR, MIDTERM_SUBSET_PROFILE)

    context = Context()
    plan = graph_module._route_plan_for_context("q", context)  # noqa: SLF001

    assert context.fixed_dag_deployment_profile == MIDTERM_SUBSET_PROFILE
    assert plan["schema"] == SELECTED_FIXED_DAG_SCHEMA_VERSION
    assert plan["selected_dimensions"] == list(MIDTERM_SUBSET_SELECTED_DIMENSIONS)
    assert set(plan["target_agent_ids"]) == set(MIDTERM_SUBSET_SELECTED_L2_AGENT_IDS) | set(
        MIDTERM_SUBSET_REQUIRED_DEPENDENCY_AGENT_IDS
    )
    assert set(MIDTERM_SUBSET_DEFERRED_AGENT_IDS).isdisjoint(plan["target_agent_ids"])
    assert "market_ipo_investor_behavior" in plan["omitted_agents"]
    assert "entity_relation_extractor" in plan["target_agent_ids"]
    assert plan["dimension_groups"]["value"] == [
        "value_traditional_valuation",
        "value_ml_valuation",
        "value_meta_valuation",
        "value_research_synthesis",
    ]
    assert plan["dimension_groups"]["market"] == [
        "market_stock_technical",
        "market_capital_flow_chip",
    ]
    assert plan["provenance"]["deployment_profile"] == MIDTERM_SUBSET_PROFILE
    assert plan["provenance"]["route_granularity"] == "agent_profile"
    valid, reason = validate_selected_dag_steps(plan)
    assert valid, reason


def test_midterm_subset_profile_public_workflow_omits_deferred_agents() -> None:
    plan = _profile_plan()
    execution = execute_fixed_dag_plan(
        plan,
        question="q",
        as_of="2026-06-05",
        context=Context(
            disable_external_compute_default=True,
            disable_non_l4_external_compute_default=True,
        ),
    )

    workflow = build_workflow_snapshot(
        {
            "fixed_dag_plan": plan,
            "dag_execution": execution,
            "dag_step_results": execution["step_results"],
            "execution_batches": execution["execution_batches"],
            "l2_conclusions": execution["l2_conclusions"],
            "dimension_results": execution["dimension_results"],
            "decision_result": execution["decision_result"],
            "report_result": execution["report_result"],
        },
        "replay",
    )
    payload = workflow.model_dump(mode="json", by_alias=True)
    active_agent_ids = {
        step["agentId"]
        for step in payload["dagSteps"]
        if isinstance(step.get("agentId"), str)
    }

    assert set(MIDTERM_SUBSET_DEFERRED_AGENT_IDS).isdisjoint(active_agent_ids)
    assert payload["provenance"]["selectedRoutingRequested"] is True
    assert payload["provenance"]["selectedRoutingFallback"] is False
    assert payload["provenance"]["routeGranularity"] == "agent_profile"
    assert payload["provenance"]["selectedDimensions"] == list(
        MIDTERM_SUBSET_SELECTED_DIMENSIONS
    )
    assert payload["provenance"]["expandedAgentCount"] == len(plan["target_agent_ids"])


def test_midterm_subset_profile_graph_runtime_uses_selected_plan(monkeypatch) -> None:
    def fail_load_model(*args, **kwargs):
        raise AssertionError("provider should not be called")

    def fail_external_client(*args, **kwargs):
        raise AssertionError("external HTTP should not be called")

    monkeypatch.setattr("react_agent.default_agents.load_chat_model", fail_load_model)
    monkeypatch.setattr(
        "react_agent.external_http_agents.httpx.AsyncClient",
        fail_external_client,
    )

    result = graph_module.graph.invoke(
        {"messages": [("user", "分析 600519.SH 的中期研判范围。")]},
        context=Context(
            fixed_dag_deployment_profile=MIDTERM_SUBSET_PROFILE,
            disable_external_compute_default=True,
            disable_non_l4_external_compute_default=True,
        ),
    )

    plan = result["fixed_dag_plan"]
    assert plan["schema"] == SELECTED_FIXED_DAG_SCHEMA_VERSION
    assert plan["provenance"]["deployment_profile"] == MIDTERM_SUBSET_PROFILE
    assert set(MIDTERM_SUBSET_DEFERRED_AGENT_IDS).isdisjoint(plan["target_agent_ids"])
    assert set(MIDTERM_SUBSET_DEFERRED_AGENT_IDS).isdisjoint(result["dag_step_results"])
    assert result["report_result"]["schema"] == "report_result_v1"
    assert result["final_answer_source"] == "reset_skeleton"


def test_public_routing_request_does_not_accept_arbitrary_agent_ids() -> None:
    with pytest.raises(ValidationError):
        PublicRoutingRequest(
            mode="selected",
            selected_agents=["market_ipo_investor_behavior"],
        )


def test_midterm_profile_does_not_change_source_controlled_runtime_configs() -> None:
    root = _repo_root()
    catalog = json.loads((root / "config/fixed_dag/agent_catalog.json").read_text())
    bindings = json.loads((root / "config/fixed_dag/runtime_bindings.json").read_text())
    non_l4_policy = json.loads(
        (root / "config/fixed_dag/non_l4_external_compute_policy.json").read_text()
    )

    assert len(catalog["agents"]) == 27
    assert bindings["default_external_invoke_enabled"] is False
    assert non_l4_policy["max_concurrency_by_stage"]["l2"] == 20
