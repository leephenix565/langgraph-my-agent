import json

from react_agent.fixed_dag_contracts import (
    DIMENSION_GROUPS,
    build_default_fixed_dag_plan,
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
    text = json.dumps(payload)
    assert "layerMode" not in text
    assert "fusionSteps" not in text


def test_public_workflow_preserves_execution_batches_and_step_results() -> None:
    plan = build_default_fixed_dag_plan("q", as_of="2026-06-04")
    execution = execute_fixed_dag_plan(plan, question="q", as_of="2026-06-04")
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
