import json

from react_agent.context import Context
from react_agent.fixed_dag_contracts import (
    DIMENSION_GROUPS,
    build_default_dimension_route_intent,
    build_default_fixed_dag_plan,
    build_emitted_bundle,
    build_workflow_snapshot_v2,
    compile_selected_fixed_dag_plan,
)
from react_agent.fixed_dag_executor import execute_fixed_dag_plan
from react_agent.public_mapping import build_assistant_turn, build_workflow_snapshot


def test_public_workflow_fallback_uses_fixed_dag_snapshot_contract() -> None:
    workflow = build_workflow_snapshot(
        {"fixed_dag_plan": build_default_fixed_dag_plan("q")},
        "replay",
    )
    payload = workflow.model_dump(mode="json", by_alias=True)

    assert payload["schema"] == "workflow_snapshot_v2"
    assert payload["finalSource"] == "reset_skeleton"
    assert {item["id"] for item in payload["dimensionGroups"]} == set(DIMENSION_GROUPS)
    assert payload["provenance"]["providerInvoked"] is False
    assert payload["provenance"]["externalInvoked"] is False
    assert payload["provenance"]["selectedRoutingRequested"] is False
    assert payload["provenance"]["selectedRoutingFallback"] is False
    assert payload["provenance"]["selectedDimensions"] == []
    assert payload["provenance"]["providerRouterEnabled"] is False
    assert payload["provenance"]["providerRouterInvoked"] is False
    assert payload["provenance"]["providerRouterSelectedDimensions"] == []
    text = json.dumps(payload)
    assert "layerMode" not in text
    assert "fusionSteps" not in text


def test_public_workflow_preserves_execution_batches_and_step_results() -> None:
    plan = build_default_fixed_dag_plan("q", as_of="2026-06-04")
    execution = execute_fixed_dag_plan(
        plan,
        question="q",
        as_of="2026-06-04",
        context=Context(disable_external_compute_default=True),
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

    assert payload["executionBatches"] == execution["execution_batches"]
    assert payload["stepResults"] == execution["step_results"]
    assert payload["stepResults"]["financial_data_service"]["runtime_kind"] == "external_http_candidate"
    assert payload["stepResults"]["financial_data_service"]["implementation_status"] == "external_candidate_disabled"
    assert payload["stepResults"]["financial_data_service"]["invoke_enabled"] is False
    assert payload["stepResults"]["financial_data_service"]["live_verified"] is False
    assert "default_url" not in payload["stepResults"]["financial_data_service"]
    assert "env_var" not in payload["stepResults"]["financial_data_service"]
    assert payload["provenance"]["executionStatus"] == "complete"
    assert payload["provenance"]["fallbackUsed"] is False
    assert payload["completedSteps"] == list(execution["step_results"])


def test_public_workflow_preserves_selected_routing_provenance_safely() -> None:
    intent = build_default_dimension_route_intent("Explain discounted cash flow in simple terms.")
    plan = compile_selected_fixed_dag_plan(intent, user_text="q", as_of="2026-06-04")
    plan["provenance"] = {
        **plan["provenance"],
        "selected_routing_requested": True,
        "selected_routing_fallback": False,
        "route_granularity": "dimension",
        "selected_dimensions": list(plan["selected_dimensions"]),
        "expanded_agent_count": len(plan["target_agent_ids"]),
        "provider_router_enabled": True,
        "provider_router_invoked": True,
        "provider_router_mode": "fake",
        "provider_router_parse_ok": True,
        "provider_router_selected_dimensions": list(plan["selected_dimensions"]),
        "raw_marker": "NEVER_STORE_FAKE_ROUTER_RAW_MARKER",
    }
    execution = execute_fixed_dag_plan(
        plan,
        question="q",
        as_of="2026-06-04",
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
    serialized = json.dumps(payload, ensure_ascii=False)

    provenance = payload["provenance"]
    assert provenance["selectedRoutingRequested"] is True
    assert provenance["selectedRoutingFallback"] is False
    assert provenance["routeGranularity"] == "dimension"
    assert provenance["selectedDimensions"] == ["value"]
    assert provenance["expandedAgentCount"] == len(plan["target_agent_ids"])
    assert provenance["providerRouterEnabled"] is True
    assert provenance["providerRouterInvoked"] is True
    assert provenance["providerRouterMode"] == "fake"
    assert provenance["providerRouterParseOk"] is True
    assert provenance["providerRouterSelectedDimensions"] == ["value"]
    assert "NEVER_STORE_FAKE_ROUTER_RAW_MARKER" not in serialized
    assert "raw_response" not in serialized.lower()
    assert "/v1/agent/invoke" not in serialized
    assert "endpoint" not in serialized.lower()
    assert "secret" not in serialized.lower()
    assert "prompt" not in serialized.lower()


def test_public_assistant_turn_preserves_selected_report_closure() -> None:
    intent = build_default_dimension_route_intent("Explain discounted cash flow in simple terms.")
    plan = compile_selected_fixed_dag_plan(intent, user_text="q", as_of="2026-06-04")
    plan["provenance"] = {
        **plan["provenance"],
        "selected_routing_requested": True,
        "selected_routing_fallback": False,
        "route_granularity": "dimension",
        "selected_dimensions": list(plan["selected_dimensions"]),
        "expanded_agent_count": len(plan["target_agent_ids"]),
    }
    execution = execute_fixed_dag_plan(
        plan,
        question="q",
        as_of="2026-06-04",
        context=Context(
            disable_external_compute_default=True,
            disable_non_l4_external_compute_default=True,
        ),
    )
    turn = build_assistant_turn(
        {
            "final_answer_source": "reset_skeleton",
            "fixed_dag_plan": plan,
            "dag_execution": execution,
            "dag_step_results": execution["step_results"],
            "execution_batches": execution["execution_batches"],
            "l2_conclusions": execution["l2_conclusions"],
            "dimension_results": execution["dimension_results"],
            "decision_result": execution["decision_result"],
            "report_result": execution["report_result"],
            "workflow_snapshot": build_workflow_snapshot_v2(
                plan=plan,
                l2_conclusions=execution["l2_conclusions"],
                dimension_results=execution["dimension_results"],
                decision_result=execution["decision_result"],
                report_result=execution["report_result"],
                dag_execution=execution,
                step_results=execution["step_results"],
                execution_batches=execution["execution_batches"],
                current_stage="report",
            ),
            "emitted_bundle": build_emitted_bundle(execution["report_result"]),
        },
        "replay",
    )
    payload = turn.model_dump(mode="json", by_alias=True)

    assert payload["text"]
    assert payload["answerCard"]["sections"]
    assert payload["workflow"]["currentStage"] == "report"
    assert payload["workflow"]["provenance"]["selectedRoutingRequested"] is True
    assert payload["workflow"]["provenance"]["selectedDimensions"] == ["value"]


def test_public_assistant_turn_preserves_report_sections_and_limitations() -> None:
    turn = build_assistant_turn(
        {
            "final_answer_source": "reset_skeleton",
            "emitted_bundle": {
                "answer": "主回答",
                "confidence": 0.8,
                "sections": [
                    {
                        "id": "value",
                        "title": "价值分析",
                        "content": "估值细节",
                    },
                    {
                        "id": "empty",
                        "title": "空章节",
                        "content": "",
                    },
                ],
                "evidence_cards": [{"title": "估值证据", "note": "PE"}],
                "limitations": ["显式开关路径。"],
            },
        },
        "replay",
    )
    payload = turn.model_dump(mode="json", by_alias=True)

    assert payload["text"] == "主回答"
    assert payload["answerCard"]["sections"] == [
        {"id": "value", "title": "价值分析", "content": "估值细节"}
    ]
    assert payload["answerCard"]["limitations"] == ["显式开关路径。"]
    assert payload["answerCard"]["evidenceCards"][0]["title"] == "估值证据"
