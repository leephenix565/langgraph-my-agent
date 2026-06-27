import copy
import json
import subprocess
import sys
from types import SimpleNamespace

import pytest

from react_agent.context import Context
from react_agent.fixed_dag_contracts import (
    MACRO_AGENT_IDS,
    MARKET_AGENT_IDS,
    RESET_RUNTIME_AGENT_IDS,
    RISK_AGENT_IDS,
    VALUE_AGENT_IDS,
    build_decision_result,
    build_default_fixed_dag_plan,
    build_report_input_bundle,
    build_report_result,
    build_route_intent,
    compile_selected_fixed_dag_plan,
)
from react_agent.fixed_dag_executor import (
    build_dag_step_index,
    build_initial_step_results,
    execute_fixed_dag_plan,
    topological_batches,
    topological_batches_for_selected_plan,
    validate_dag_execution_result,
    validate_dag_steps,
    validate_selected_dag_steps,
    validate_step_result,
)
from react_agent.fixed_dag_external_adapter import (
    map_external_response_to_fixed_dag_object,
)


@pytest.fixture(autouse=True)
def _disable_external_compute_default_for_unit_tests(monkeypatch):
    monkeypatch.setenv("DISABLE_EXTERNAL_COMPUTE_DEFAULT", "1")


def _plan():
    return build_default_fixed_dag_plan("q", as_of="2026-06-04")


def test_executor_execution_package_preserves_old_import_facade() -> None:
    import react_agent.fixed_dag_executor as executor
    from react_agent.fixed_dag.execution import (
        constants,
        runner,
        step_results,
        topology,
        validation,
    )

    assert executor.execute_fixed_dag_plan is runner.execute_fixed_dag_plan
    assert executor.FIXED_DAG_EXECUTION_SCHEMA_VERSION == constants.FIXED_DAG_EXECUTION_SCHEMA_VERSION
    assert executor.FIXED_DAG_STEP_RESULT_SCHEMA_VERSION == constants.FIXED_DAG_STEP_RESULT_SCHEMA_VERSION
    assert executor.LEGAL_STEP_STATUSES == constants.LEGAL_STEP_STATUSES
    assert executor.LEGAL_DIMENSIONS == constants.LEGAL_DIMENSIONS
    assert executor.STAGE_ORDER_INDEX == constants.STAGE_ORDER_INDEX
    assert executor.L2_EVIDENCE_DEPS == constants.L2_EVIDENCE_DEPS
    assert executor.DIMENSION_STEP_IDS == constants.DIMENSION_STEP_IDS
    assert executor.COMPOSITE_DEPENDENCY_GROUPS == constants.COMPOSITE_DEPENDENCY_GROUPS
    assert executor.build_dag_step_index is topology.build_dag_step_index
    assert executor.topological_batches is topology.topological_batches
    assert executor.topological_batches_for_selected_plan is topology.topological_batches_for_selected_plan
    assert executor.validate_dag_steps is validation.validate_dag_steps
    assert executor.validate_selected_dag_steps is validation.validate_selected_dag_steps
    assert executor.validate_dag_execution_result is validation.validate_dag_execution_result
    assert executor.build_step_result is step_results.build_step_result
    assert executor.validate_step_result is step_results.validate_step_result
    assert executor.build_initial_step_results is step_results.build_initial_step_results


def test_execution_leaf_imports_do_not_load_old_executor_or_runner() -> None:
    code = """
import sys
import react_agent.fixed_dag.execution.validation
assert 'react_agent.fixed_dag_executor' not in sys.modules
import react_agent.fixed_dag_contracts
assert 'react_agent.fixed_dag.execution.runner' not in sys.modules
print('import-boundary-ok')
"""
    result = subprocess.run(
        [sys.executable, "-c", code],
        check=True,
        capture_output=True,
        text=True,
    )

    assert result.stdout.strip() == "import-boundary-ok"


def test_executor_validation_rejects_legacy_keys_directly() -> None:
    full_plan = copy.deepcopy(_plan())
    full_plan["layerPlan"] = []
    valid, reason = validate_dag_steps(full_plan)
    assert not valid
    assert reason == "legacy_dispatch_field_present"

    selected_plan = compile_selected_fixed_dag_plan(
        build_route_intent(
            task_type="general",
            selected_dimensions=["value"],
            selected_agents=["value_ml_valuation"],
            fallback_reason="fallback to full DAG",
        ),
        user_text="q",
        as_of="2026-06-09",
    )
    selected_plan["fusionSteps"] = []
    valid, reason = validate_selected_dag_steps(selected_plan)
    assert not valid
    assert reason == "legacy_dispatch_field_present"

    result = execute_fixed_dag_plan(_plan(), question="q", as_of="2026-06-04")
    result["baseline_bundle"] = {}
    valid, reason = validate_dag_execution_result(result)
    assert not valid
    assert reason == "legacy_dispatch_field_present"


def test_build_dag_step_index_preserves_last_nonempty_duplicate_id() -> None:
    plan = {
        "steps": [
            {"id": "", "agent_id": "route_planner"},
            {"id": "duplicate", "agent_id": "route_planner"},
            {"id": "duplicate", "agent_id": "financial_data_service"},
        ]
    }

    index = build_dag_step_index(plan)

    assert "" not in index
    assert index == {"duplicate": {"id": "duplicate", "agent_id": "financial_data_service"}}


def _compute_envelope(agent_id: str, external_agent_id: str, tool_result: dict[str, object]):
    return {
        "schema_version": "external_agent_compute_v0",
        "agent_id": agent_id,
        "external_agent_id": external_agent_id,
        "status": "ok",
        "tool_result": tool_result,
    }


def _agent_conclusion(
    *,
    agent_id: str = "value_ml_valuation",
    external_agent_id: str = "valuation_ml",
    dimension: str = "value",
) -> dict[str, object]:
    role = "gate_member" if dimension == "risk" else "direction"
    payload: dict[str, object] = {
        "schema_version": "agent_conclusion_v1",
        "agent_id": agent_id,
        "external_agent_id": external_agent_id,
        "dimension": dimension,
        "role": role,
        "stance": "demo_positive",
        "confidence": 0.64,
        "status": "ok",
        "evidence": [
            {
                "id": "demo-evidence",
                "fact": "Bounded external compute demo fixture.",
                "source": "unit_test",
                "as_of": "2026-06-04",
                "data_as_of": "2026-06-04",
            }
        ],
        "as_of": "2026-06-04",
        "data_as_of": "2026-06-04",
        "event_flags": [],
    }
    if role == "gate_member":
        payload.pop("stance")
        payload["risk_score"] = 0.22
    return payload


def _risk_conclusion() -> dict[str, object]:
    return {
        "schema_version": "risk_conclusion_v1",
        "agent_id": "risk_composite",
        "external_agent_id": "risk_synthesis",
        "dimension": "risk",
        "role": "gate",
        "target": "600519.SH",
        "gate": "pass",
        "risk_score": 0.31,
        "penalty": 0.1,
        "confidence": 0.73,
        "contributing_agents": ["risk_identification", "risk_compliance_review"],
        "triggered_flags": ["bounded_demo_flag"],
        "red_lines": [],
        "evidence": [
            {
                "id": "risk-demo-evidence",
                "fact": "Risk gate stays below veto level.",
                "source": "unit_test",
                "as_of": "2026-06-04",
                "data_as_of": "2026-06-04",
            }
        ],
        "as_of": "2026-06-04",
        "data_as_of": "2026-06-04",
        "status": "ok",
    }


def _value_dimension_conclusion() -> dict[str, object]:
    return {
        "schema_version": "dimension_conclusion_v1",
        "agent_id": "value_composite",
        "external_agent_id": "composite_valuation",
        "dimension": "value",
        "role": "direction",
        "target": "600519.SH",
        "stance": 0.18,
        "confidence": 0.72,
        "members": [
            {
                "agent_id": "value_traditional_valuation",
                "stance": 0.12,
                "confidence": 0.7,
                "weight": 0.34,
                "status": "ok",
            },
            {
                "agent_id": "value_ml_valuation",
                "stance": 0.2,
                "confidence": 0.72,
                "weight": 0.33,
                "status": "ok",
            },
            {
                "agent_id": "value_meta_valuation",
                "stance": 0.22,
                "confidence": 0.74,
                "weight": 0.33,
                "status": "ok",
            },
            {
                "agent_id": "value_research_synthesis",
                "stance": 0.0,
                "confidence": 0.0,
                "weight": 0.0,
                "status": "pending",
            },
        ],
        "method": "weighted_member_vote",
        "evidence": [
            {
                "id": "value-dimension-evidence",
                "fact": "Value members are mildly positive.",
                "source": "unit_test",
                "as_of": "2026-06-04",
                "data_as_of": "2026-06-04",
            }
        ],
        "as_of": "2026-06-04",
        "data_as_of": "2026-06-04",
        "status": "ok",
    }


def _macro_conclusion() -> dict[str, object]:
    return {
        "schema_version": "macro_conclusion_v1",
        "agent_id": "macro_composite",
        "external_agent_id": "macro_synthesis_service",
        "dimension": "macro",
        "role": "regulator",
        "target": "CN_A_SHARE_MACRO",
        "regime": "neutral_liquidity_watch",
        "dimension_weights": {"value": 0.55, "market": 0.45},
        "risk_sensitivity": 0.6,
        "style_bias": {"quality": 0.7, "defensive": 0.3},
        "regime_detail": {"name": "neutral", "confidence": 0.69},
        "members": {
            "macro_analysis": {
                "confidence": 0.64,
                "status": "ok",
                "summary": "growth stable",
            },
            "macro_commodity_pricing": {
                "confidence": 0.0,
                "status": "pending",
                "weight": 0.0,
                "summary": "not activated",
            },
            "macro_index_valuation": {
                "confidence": 0.65,
                "status": "ok",
                "summary": "index valuation bounded",
            },
            "macro_sentiment": {
                "confidence": 0.0,
                "status": "pending",
                "weight": 0.0,
            },
            "macro_industry_hotspot": {
                "confidence": 0.0,
                "status": "pending",
                "weight": 0.0,
            },
        },
        "warnings": ["macro members pending"],
        "confidence": 0.69,
        "contributing_agents": ["macro_analysis", "macro_index_valuation"],
        "evidence": [
            {
                "id": "macro-evidence-1",
                "fact": "Macro regime supports balanced value and market weights.",
                "source": "unit_test",
                "as_of": "2026-06-04",
                "data_as_of": "2026-06-04",
            }
        ],
        "as_of": "2026-06-04",
        "data_as_of": "2026-06-04",
        "status": "partial",
    }


def _high_quality_report(question: str = "q") -> dict[str, object]:
    section_titles = [
        "核心结论与行动含义",
        "价值维度：估值分歧与安全边际",
        "市场维度：价格、资金与情绪确认度",
        "风险维度：风险门与缺失合规证据",
        "宏观维度：宏观调节器与仓位约束",
    ]
    answer = (
        "研判流程高质量报告：行动含义是研究观察和人工复核。"
        "本报告覆盖 " + "；".join(section_titles) + "。"
        "风险门和宏观调节器都已在正文中说明。"
    )
    return {
        **build_report_result(build_decision_result({}, as_of="2026-06-04"), question=question),
        "title": "外部 L4 默认报告",
        "answer": answer,
        "status": "complete",
        "sections": [
            {
                "id": "core_decision",
                "title": "核心结论与行动含义",
                "content": "行动含义：当前是研究观察，需人工复核风险证据和市场确认。",
            },
            {
                "id": "value_dimension",
                "title": "价值维度：估值分歧与安全边际",
                "content": "价值维度说明估值分歧和安全边际。",
            },
            {
                "id": "market_dimension",
                "title": "市场维度：价格、资金与情绪确认度",
                "content": "市场维度说明价格、资金与情绪确认度。",
            },
            {
                "id": "risk_dimension",
                "title": "风险维度：风险门与缺失合规证据",
                "content": "风险维度说明风险门和缺失合规证据。",
            },
            {
                "id": "macro_dimension",
                "title": "宏观维度：宏观调节器与仓位约束",
                "content": "宏观维度说明宏观调节器和仓位约束。",
            },
        ],
        "evidence_cards": [
            {"title": "价值证据", "note": "估值分歧来自结构化固定 DAG 材料。"},
            {"title": "风险证据", "note": "风险门和合规缺口已保留。"},
        ],
        "limitations": ["仍需人工复核，且不构成正式投资建议。"],
    }


def _data_bundle() -> dict[str, object]:
    return {
        "schema_version": "data_bundle_v1",
        "agent_id": "financial_data_service",
        "external_agent_id": "financial_data_service",
        "status": "ok",
        "target": "600519.SH",
        "as_of": "2026-06-04",
        "data_as_of": "2026-06-04",
        "snapshot_id": "executor-data-snapshot",
        "sources": [
            {"name": "daily_price", "source": "unit_test"},
            {"name": "financial_indicator", "source": "unit_test"},
        ],
        "feature_bundle": {"close": 1520.0, "pe_ttm": 28.4},
        "missing_fields": [],
    }


def _entity_relation_bundle() -> dict[str, object]:
    return {
        "schema_version": "entity_relation_bundle_v1",
        "agent_id": "entity_relation_extractor",
        "external_agent_id": "entity_relation_agent",
        "status": "ok",
        "target": "600519.SH",
        "as_of": "2026-06-04",
        "data_as_of": "2026-06-04",
        "entities": [
            {"id": "stock:600519.SH", "name": "贵州茅台", "type": "company"},
            {"id": "industry:baijiu", "name": "白酒", "type": "industry"},
        ],
        "relations": [
            {
                "source": "stock:600519.SH",
                "target": "industry:baijiu",
                "type": "belongs_to",
            }
        ],
        "sources": [{"name": "unit_relation_extractor"}],
        "notes": ["bounded entity relation fixture"],
    }


class _FakePlaceholderModel:
    def __init__(self) -> None:
        self.prompts: list[str] = []

    def invoke(self, prompt: str):
        self.prompts.append(prompt)
        return SimpleNamespace(
            content=json.dumps(
                {
                    "analysis": "根据 agent_task_v1 做内部占位分析，等待真实外部 agent 接入。",
                    "key_points": ["已读取 L1 证据边界和 required_output_schema。"],
                    "evidence": [{"fact": "当前为内部 LLM 占位，不代表真实外部服务结果。"}],
                    "confidence": 0.22,
                },
                ensure_ascii=False,
            )
        )


def test_default_plan_validates_and_batches_are_stable() -> None:
    plan = _plan()
    valid, reason = validate_dag_steps(plan)
    batches = topological_batches(plan)
    l2_agent_ids = MARKET_AGENT_IDS + VALUE_AGENT_IDS + RISK_AGENT_IDS + MACRO_AGENT_IDS

    assert valid, reason
    assert batches[0] == ["route_planner"]
    assert batches[1] == ["financial_data_service", "entity_relation_extractor"]
    assert set(batches[2]) == {f"l2:{agent_id}" for agent_id in l2_agent_ids}
    assert batches[3] == ["dimension:value", "dimension:market", "dimension:risk", "dimension:macro"]
    assert batches[4] == ["decision_synthesizer"]
    assert batches[5] == ["report_generator"]


def test_selected_value_only_plan_validates_and_batches_are_stable() -> None:
    intent = build_route_intent(
        task_type="general",
        selected_dimensions=["value"],
        selected_agents=["value_ml_valuation"],
        route_confidence=0.7,
        fallback_reason="fallback to full DAG",
    )
    plan = compile_selected_fixed_dag_plan(intent, user_text="q", as_of="2026-06-09")
    valid, reason = validate_selected_dag_steps(plan)
    selected_batches = topological_batches_for_selected_plan(plan)
    full_batches = topological_batches(plan)

    assert valid, reason
    assert selected_batches == [
        ["route_planner"],
        ["financial_data_service", "entity_relation_extractor"],
        ["l2:value_ml_valuation"],
        ["dimension:value"],
        ["report_generator"],
    ]
    assert full_batches == []


def test_selected_investment_plan_validates_decision_and_report_dependencies() -> None:
    intent = build_route_intent(
        task_type="single",
        selected_dimensions=["value", "risk"],
        selected_agents=["value_traditional_valuation", "risk_identification"],
        route_confidence=0.8,
        fallback_reason="fallback to full DAG",
    )
    plan = compile_selected_fixed_dag_plan(intent, user_text="q", as_of="2026-06-09")
    index = build_dag_step_index(plan)
    valid, reason = validate_selected_dag_steps(plan)
    batches = topological_batches_for_selected_plan(plan)

    assert valid, reason
    assert set(index["decision_synthesizer"]["depends_on"]) == {
        "dimension:value",
        "dimension:risk",
    }
    assert index["report_generator"]["depends_on"] == ["decision_synthesizer"]
    assert batches[0] == ["route_planner"]
    assert set(batches[2]) == {
        "l2:value_traditional_valuation",
        "l2:risk_identification",
    }
    assert set(batches[3]) == {"dimension:value", "dimension:risk"}
    assert batches[4] == ["decision_synthesizer"]
    assert batches[5] == ["report_generator"]


def test_selected_dag_validation_rejects_selected_dependency_shape_errors() -> None:
    intent = build_route_intent(
        task_type="single",
        selected_dimensions=["market", "risk"],
        selected_agents=["sentiment_company_radar", "risk_identification"],
        route_confidence=0.7,
        fallback_reason="fallback to full DAG",
    )
    plan = compile_selected_fixed_dag_plan(intent, user_text="q", as_of="2026-06-09")

    risk_reads_sentiment = copy.deepcopy(plan)
    for step in risk_reads_sentiment["steps"]:
        if step["id"] == "dimension:risk":
            step["depends_on"].append("l2:sentiment_company_radar")
            break
    valid, reason = validate_selected_dag_steps(risk_reads_sentiment)
    assert not valid
    assert reason == "risk_reads_sentiment"

    bad_decision = copy.deepcopy(plan)
    for step in bad_decision["steps"]:
        if step["id"] == "decision_synthesizer":
            step["depends_on"] = ["dimension:value"]
            break
    valid, reason = validate_selected_dag_steps(bad_decision)
    assert not valid
    assert reason == "missing_dependency"

    value_only = compile_selected_fixed_dag_plan(
        build_route_intent(
            task_type="general",
            selected_dimensions=["value"],
            selected_agents=["value_ml_valuation"],
            fallback_reason="fallback to full DAG",
        )
    )
    bad_report = copy.deepcopy(value_only)
    for step in bad_report["steps"]:
        if step["id"] == "report_generator":
            step["depends_on"] = ["decision_synthesizer"]
            break
    valid, reason = validate_selected_dag_steps(bad_report)
    assert not valid
    assert reason == "missing_dependency"


def test_dimension_dependencies_preserve_sentiment_market_boundary() -> None:
    plan = _plan()
    index = build_dag_step_index(plan)

    assert set(index["dimension:value"]["depends_on"]) == {
        f"l2:{agent_id}" for agent_id in VALUE_AGENT_IDS
    }
    assert set(index["dimension:market"]["depends_on"]) == {
        f"l2:{agent_id}" for agent_id in MARKET_AGENT_IDS
    }
    assert "l2:sentiment_company_radar" in index["dimension:market"]["depends_on"]
    assert set(index["dimension:risk"]["depends_on"]) == {
        f"l2:{agent_id}" for agent_id in RISK_AGENT_IDS
    }
    assert "l2:sentiment_company_radar" not in index["dimension:risk"]["depends_on"]
    assert set(index["dimension:macro"]["depends_on"]) == {
        f"l2:{agent_id}" for agent_id in MACRO_AGENT_IDS
    }
    assert set(index["decision_synthesizer"]["depends_on"]) == {
        "dimension:value",
        "dimension:market",
        "dimension:risk",
        "dimension:macro",
    }
    assert index["report_generator"]["depends_on"] == ["decision_synthesizer"]


def test_dag_validation_rejects_dependency_shape_errors() -> None:
    cases = []

    missing_dep = copy.deepcopy(_plan())
    missing_dep["steps"][3]["depends_on"] = ["missing"]
    cases.append((missing_dep, "missing_dependency"))

    cycle = copy.deepcopy(_plan())
    cycle["steps"][3]["depends_on"] = [cycle["steps"][4]["id"]]
    cycle["steps"][4]["depends_on"] = [cycle["steps"][3]["id"]]
    cases.append((cycle, "cycle_detected"))

    duplicate = copy.deepcopy(_plan())
    duplicate["steps"][1]["id"] = "route_planner"
    cases.append((duplicate, "duplicate_step_id"))

    bad_agent = copy.deepcopy(_plan())
    bad_agent["steps"][3]["agent_id"] = "value_financial_analysis"
    cases.append((bad_agent, "invalid_agent_id"))

    bad_dimension = copy.deepcopy(_plan())
    bad_dimension["steps"][3]["dimension"] = "sentiment_cross_cutting"
    cases.append((bad_dimension, "invalid_dimension"))

    risk_reads_sentiment = copy.deepcopy(_plan())
    for step in risk_reads_sentiment["steps"]:
        if step["id"] == "dimension:risk":
            step["depends_on"].append("l2:sentiment_company_radar")
            break
    cases.append((risk_reads_sentiment, "risk_composite_dependency_mismatch"))

    for plan, expected_reason in cases:
        valid, reason = validate_dag_steps(plan)
        assert not valid
        assert reason == expected_reason


def test_step_result_and_initial_results_validate() -> None:
    initial = build_initial_step_results(_plan())

    assert len(initial) == len(RESET_RUNTIME_AGENT_IDS)
    for result in initial.values():
        valid, reason = validate_step_result(result)
        assert valid, reason
        assert result["status"] == "blocked"
        assert "runtime_kind" in result
        assert "implementation_status" in result
        assert "binding_source" in result
        assert result["invoke_enabled"] in {True, False}
        assert result["live_verified"] in {True, False}


def test_execute_fixed_dag_plan_emits_execution_result_and_public_snapshot() -> None:
    result = execute_fixed_dag_plan(_plan(), question="q", as_of="2026-06-04")
    valid, reason = validate_dag_execution_result(result)

    assert valid, reason
    assert result["schema_version"] == "fixed_dag_execution_v1"
    assert result["status"] == "complete"
    assert result["fallback_used"] is False
    assert len(result["step_results"]) == len(RESET_RUNTIME_AGENT_IDS)
    assert result["execution_batches"][0] == ["route_planner"]
    assert result["workflow_snapshot"]["executionBatches"] == result["execution_batches"]
    assert result["workflow_snapshot"]["stepResults"] == result["step_results"]
    assert set(result["workflow_snapshot"]["completedSteps"]) == set(result["step_results"])
    assert result["report_input_bundle"]["schema"] == "report_input_bundle_v1"
    assert result["report_input_bundle"]["agent_evidence_bundle"]["schema"] == "agent_evidence_bundle_v1"
    assert result["report_input_bundle"]["agent_evidence_bundle"]["l1_evidence"]["data_bundle_status"] == "pending_implementation"
    assert result["agent_task_summaries"]
    assert result["report_input_bundle"]["agent_task_summaries"]
    value_task = result["step_results"]["l2:value_ml_valuation"]["agent_task"]
    assert value_task["required_output_schema"] == "agent_conclusion_v1"
    assert value_task["has_l1_data_bundle"] is True
    assert value_task["has_l1_entity_relation_bundle"] is True
    assert "机器学习企业估值智能体" in value_task["task_instruction"]
    l3_task = result["step_results"]["dimension:value"]["agent_task"]
    assert l3_task["required_output_schema"] == "dimension_conclusion_v1"
    assert "value_ml_valuation" in l3_task["upstream_agent_ids"]
    assert result["step_results"]["route_planner"]["runtime_kind"] == "deterministic_system"
    assert result["step_results"]["route_planner"]["implementation_status"] == "deterministic_skeleton"
    assert result["step_results"]["financial_data_service"]["runtime_kind"] == "external_http_candidate"
    assert result["step_results"]["financial_data_service"]["implementation_status"] == "external_candidate_disabled"
    assert result["step_results"]["financial_data_service"]["invoke_enabled"] is False
    assert result["step_results"]["financial_data_service"]["live_verified"] is False
    assert result["step_results"]["dimension:market"]["runtime_kind"] == "deterministic_composite"
    assert result["step_results"]["dimension:market"]["implementation_status"] == "deterministic_skeleton"
    assert result["step_results"]["l2:sentiment_company_radar"]["runtime_kind"] == "pending_placeholder"
    assert "agent_evidence" in result["step_results"]["l2:value_ml_valuation"]
    assert "evidence_count" in result["step_results"]["l2:value_ml_valuation"]["agent_evidence"]
    assert "detail_notes" in result["step_results"]["l2:value_ml_valuation"]["agent_evidence"]
    assert "composite_evidence" in result["step_results"]["dimension:value"]
    assert "核心结论与行动含义" in result["report_result"]["answer"]
    section_titles = {section["title"] for section in result["report_result"]["sections"]}
    assert "价值维度：估值分歧与安全边际" in section_titles
    assert "市场维度：价格、资金与情绪确认度" in section_titles
    assert "风险维度：风险门与缺失合规证据" in section_titles
    assert "宏观维度：宏观调节器与仓位约束" in section_titles
    assert "sentiment_company_radar" not in result["step_results"]["dimension:risk"]["depends_on"]
    payload = json.dumps(result)
    for forbidden in ("layerMode", "fusionSteps", "layerPlan", "value_financial_analysis"):
        assert forbidden not in payload


def test_execute_fixed_dag_plan_default_context_does_not_load_internal_llm(monkeypatch) -> None:
    def fail_load(_model: str):
        raise AssertionError("internal placeholder provider should stay default-off")

    monkeypatch.setattr("react_agent.fixed_dag_llm_placeholders.load_chat_model", fail_load)
    monkeypatch.setattr("react_agent.fixed_dag_report_synthesizer.load_chat_model", fail_load)

    result = execute_fixed_dag_plan(
        _plan(),
        question="q",
        as_of="2026-06-04",
        context=Context(),
    )

    assert result["provenance"]["internal_llm_placeholders_enabled"] is False
    assert result["provenance"]["internal_llm_placeholder_conclusions"] == 0
    assert {
        item["status"]
        for item in result["l2_conclusions"].values()
    } == {"pending_implementation"}
    assert {
        item["provenance"]["source"]
        for item in result["l2_conclusions"].values()
    } == {"reset_skeleton"}
    assert result["provenance"]["llm_report_synthesis_enabled"] is False
    assert result["provenance"]["provider_invoked"] is False


def test_report_input_bundle_explains_thin_external_agent_evidence() -> None:
    payload = _agent_conclusion()
    payload["evidence"] = []
    payload["raw_output"] = {"model_score": 0.51, "feature_count": 8}
    payload["quality"] = {"coverage": "thin", "sample_size": 1}
    mapped = map_external_response_to_fixed_dag_object(
        _compute_envelope("value_ml_valuation", "valuation_ml", payload)
    )

    bundle = build_report_input_bundle(
        question="请分析 600519.SH",
        l2_conclusions={"value_ml_valuation": mapped},
        dimension_results={},
        decision_result={
            "decision": "hold",
            "score": 0.0,
            "confidence": 0.1,
            "status": "partial",
        },
    )
    report = build_report_result(
        {
            "decision": "hold",
            "score": 0.0,
            "confidence": 0.1,
            "status": "partial",
        },
        question="请分析 600519.SH",
        report_input_bundle=bundle,
    )
    item = bundle["l2_agent_summaries"][0]
    evidence_bundle = bundle["agent_evidence_bundle"]
    evidence_detail = evidence_bundle["l2_agent_outputs"][0]
    rendered = json.dumps(report, ensure_ascii=False)

    assert item["evidence_count"] == 0
    assert "readable_evidence_count=0" in item["detail_notes"]
    assert any("raw_output_keys=model_score,feature_count" == note for note in item["detail_notes"])
    assert evidence_bundle["schema"] == "agent_evidence_bundle_v1"
    assert evidence_bundle["quality_summary"]["l2_without_readable_evidence"] == 1
    assert evidence_detail["provenance_notes"]["raw_output_keys"] == ["model_score", "feature_count"]
    assert evidence_detail["provenance_notes"]["quality_keys"] == ["coverage", "sample_size"]
    assert "证据质量" in rendered
    assert "未展开无可读证据的 L2" in rendered
    assert "raw_output_keys=model_score,feature_count" not in rendered


def test_report_input_bundle_carries_first_batch_report_material() -> None:
    payload = _agent_conclusion()
    valuation_bridge = {
        "current_market_value": 18000.0,
        "fair_value_center_mv": 21000.0,
        "undervalued_ratio": 0.1667,
    }
    model_vote_table = [
        {"model": "xgb", "trend": "涨", "calibrated_probability": 0.62},
        {"model": "catboost", "trend": "跌", "calibrated_probability": 0.47},
    ]
    rubric_score_table = [
        {"name_cn": "风险揭示", "score": 38.0, "weight": 0.12},
    ]
    research_points = [
        {
            "claim": "估值显著低于合理价值中枢。",
            "support": "合理市值中枢 21000 亿元，当前市值 18000 亿元。",
            "interpretation": "折价幅度已经超过轻微偏离区间。",
            "decision_implication": "估值端可作为较重要的正向输入。",
            "caveat": "仍需复核同行估值和盈利敏感性。",
        }
    ]
    payload["raw_output"] = {
        "valuation_bridge": valuation_bridge,
        "research_points": research_points,
        "drivers": [
            {"name": "valuation_bridge", "value": valuation_bridge},
            {"name": "model_vote_table", "value": model_vote_table},
            {"name": "rubric_score_table", "value": rubric_score_table},
        ],
        "endpoint": "http://example.invalid/v1/agent/invoke",
    }
    payload["quality"] = {
        "dimension_coverage": 1.0,
        "missing_components": [],
        "corpus_notice": "本地演示/合成公告语料。",
        "raw_response": "traceback",
    }
    mapped = map_external_response_to_fixed_dag_object(
        _compute_envelope("value_ml_valuation", "valuation_ml", payload)
    )

    bundle = build_report_input_bundle(
        question="请分析 600519.SH",
        l2_conclusions={"value_ml_valuation": mapped},
        dimension_results={},
        decision_result={
            "decision": "hold",
            "score": 0.0,
            "confidence": 0.1,
            "status": "partial",
        },
    )
    evidence_detail = bundle["agent_evidence_bundle"]["l2_agent_outputs"][0]
    rendered = json.dumps(bundle, ensure_ascii=False)

    assert evidence_detail["domain_metrics"]["valuation_bridge"] == valuation_bridge
    assert evidence_detail["drivers"] == [
        {"name": "valuation_bridge", "value": valuation_bridge},
        {"name": "model_vote_table", "value": model_vote_table},
        {"name": "rubric_score_table", "value": rubric_score_table},
    ]
    assert evidence_detail["research_points"] == research_points
    assert evidence_detail["data_quality"]["dimension_coverage"] == 1.0
    assert evidence_detail["data_quality"]["corpus_notice"] == "本地演示/合成公告语料。"
    fallback = build_report_result(
        {
            "decision": "hold",
            "score": 0.0,
            "confidence": 0.1,
            "status": "partial",
        },
        question="请分析 600519.SH",
        report_input_bundle=bundle,
    )
    assert "研究判断：判断：估值显著低于合理价值中枢。" in fallback["answer"]
    assert "依据：合理市值中枢 21000 亿元，当前市值 18000 亿元。" in fallback["answer"]
    assert "raw_response" not in rendered
    assert "/v1/agent/invoke" not in rendered


def test_external_compute_demo_default_off_makes_no_bridge_calls(monkeypatch) -> None:
    import react_agent.fixed_dag_external_compute_bridge as bridge

    def fail_invoke(*_args, **_kwargs):
        raise AssertionError("external compute bridge should stay default-off")

    monkeypatch.setattr(bridge, "invoke_external_compute", fail_invoke)

    result = execute_fixed_dag_plan(
        _plan(),
        question="q",
        as_of="2026-06-04",
        context=Context(external_compute_demo_allowlist=("value_ml_valuation",)),
    )

    assert result["provenance"]["external_compute_demo_enabled"] is False
    assert result["provenance"]["external_compute_demo_called_agents"] == []
    assert result["provenance"]["external_invoked"] is False
    assert result["l2_conclusions"]["value_ml_valuation"]["status"] == "pending_implementation"


def test_external_compute_default_overlays_l4_without_demo_flag(monkeypatch) -> None:
    import react_agent.fixed_dag_external_compute_bridge as bridge

    monkeypatch.delenv("DISABLE_EXTERNAL_COMPUTE_DEFAULT", raising=False)
    called = []

    def fake_invoke(entry, **kwargs):
        called.append((entry.agent_id, kwargs.get("demo")))
        if entry.agent_id == "decision_synthesizer":
            mapped = map_external_response_to_fixed_dag_object(
                _compute_envelope(
                    "decision_synthesizer",
                    "l4_decision_synthesizer",
                    {
                        **build_decision_result({}, as_of="2026-06-04"),
                        "decision": "manual_review",
                        "status": "partial",
                    },
                )
            )
        elif entry.agent_id == "report_generator":
            assert kwargs["report_input_bundle"]["schema"] == "report_input_bundle_v1"
            mapped = map_external_response_to_fixed_dag_object(
                _compute_envelope(
                    "report_generator",
                    "l4_report_generator",
                    _high_quality_report(),
                )
            )
        else:
            raise AssertionError(f"unexpected runtime default agent {entry.agent_id}")
        return {
            "agent_id": entry.agent_id,
            "status": "pass",
            "mapped": mapped,
            "failure_code": "",
            "warning": "",
        }

    monkeypatch.setattr(bridge, "invoke_external_compute", fake_invoke)
    monkeypatch.setattr(
        "react_agent.fixed_dag_report_synthesizer.load_chat_model",
        lambda _model: (_ for _ in ()).throw(
            AssertionError("mapped L4 report must suppress internal LLM report synthesis")
        ),
    )

    result = execute_fixed_dag_plan(
        _plan(),
        question="q",
        as_of="2026-06-04",
        context=Context(enable_llm_report_synthesis=True),
    )
    valid, reason = validate_dag_execution_result(result)

    assert valid, reason
    assert called == [
        ("decision_synthesizer", False),
        ("report_generator", False),
    ]
    assert result["provenance"]["external_compute_demo_enabled"] is False
    assert result["provenance"]["external_compute_default_enabled"] is True
    assert result["provenance"]["external_compute_default_mapped_agents"] == [
        "decision_synthesizer",
        "report_generator",
    ]
    assert result["provenance"]["external_invoked"] is False
    assert result["provenance"]["provider_invoked"] is False
    assert result["provenance"]["llm_report_synthesis_attempted"] is False
    assert result["provenance"]["llm_report_synthesis_used"] is False
    assert result["decision_result"]["decision"] == "manual_review"
    assert result["report_result"]["title"] == "外部 L4 默认报告"
    assert result["report_result"]["answer"] == _high_quality_report()["answer"]
    assert result["step_results"]["decision_synthesizer"]["status"] == "complete"
    assert result["step_results"]["report_generator"]["status"] == "complete"
    assert "external_compute_default_runtime_binding" in result["step_results"]["report_generator"]["warnings"]


def _run_demo_report_generator(monkeypatch, report_tool_result: dict[str, object]) -> dict:
    import react_agent.fixed_dag_external_compute_bridge as bridge

    def fake_invoke(entry, **_kwargs):
        if entry.agent_id == "value_ml_valuation":
            tool_result = _agent_conclusion()
        elif entry.agent_id == "report_generator":
            tool_result = report_tool_result
        else:
            raise AssertionError(f"unexpected demo agent {entry.agent_id}")
        mapped = map_external_response_to_fixed_dag_object(
            _compute_envelope(entry.agent_id, entry.external_agent_id, tool_result)
        )
        return {
            "agent_id": entry.agent_id,
            "status": "pass",
            "mapped": mapped,
            "failure_code": "",
            "warning": "",
        }

    monkeypatch.setattr(bridge, "invoke_external_compute", fake_invoke)
    return execute_fixed_dag_plan(
        _plan(),
        question="请分析 600519.SH",
        as_of="2026-06-04",
        context=Context(
            enable_external_compute_demo=True,
            external_compute_demo_allowlist=("value_ml_valuation", "report_generator"),
        ),
    )


def test_report_enrichment_gate_enriches_pending_external_l4_report(monkeypatch) -> None:
    pending_report = build_report_result(
        build_decision_result({}, as_of="2026-06-04"),
        question="请分析 600519.SH",
    )

    result = _run_demo_report_generator(monkeypatch, pending_report)
    valid, reason = validate_dag_execution_result(result)

    assert valid, reason
    assert result["report_result"]["status"] == "complete"
    assert result["report_result"]["title"] == "固定 DAG 研判报告"
    assert "核心结论与行动含义" in result["report_result"]["answer"]
    assert "价值维度：估值分歧与安全边际" in result["report_result"]["answer"]
    assert "风险维度：风险门与缺失合规证据" in result["report_result"]["answer"]
    assert "行动含义" in result["report_result"]["sections"][0]["content"]


def test_report_enrichment_gate_does_not_overwrite_rich_external_l4_report(monkeypatch) -> None:
    rich_report = _high_quality_report("请分析 600519.SH")

    result = _run_demo_report_generator(monkeypatch, rich_report)

    assert result["report_result"]["title"] == rich_report["title"]
    assert result["report_result"]["answer"] == rich_report["answer"]
    assert result["report_result"]["status"] == "complete"


def test_report_enrichment_gate_keeps_original_when_enrichment_invalid(monkeypatch) -> None:
    import react_agent.fixed_dag.report_quality_renderer as renderer

    pending_report = build_report_result(
        build_decision_result({}, as_of="2026-06-04"),
        question="请分析 600519.SH",
    )

    def fail_builder(**_kwargs):
        raise ValueError("invalid enrichment")

    monkeypatch.setattr(renderer, "build_enriched_report_result_from_bundle", fail_builder)
    result = _run_demo_report_generator(monkeypatch, pending_report)

    assert result["report_result"]["status"] == "pending_implementation"
    assert result["report_result"]["title"] == pending_report["title"]


def test_report_enrichment_gate_keeps_original_when_enrichment_unsafe(monkeypatch) -> None:
    import react_agent.fixed_dag.report_quality_renderer as renderer

    pending_report = build_report_result(
        build_decision_result({}, as_of="2026-06-04"),
        question="请分析 600519.SH",
    )
    unsafe_report = {
        **_high_quality_report("请分析 600519.SH"),
        "answer": _high_quality_report("请分析 600519.SH")["answer"] + " raw_response",
    }

    monkeypatch.setattr(
        renderer,
        "build_enriched_report_result_from_bundle",
        lambda **_kwargs: unsafe_report,
    )
    result = _run_demo_report_generator(monkeypatch, pending_report)

    assert result["report_result"]["status"] == "pending_implementation"
    assert result["report_result"]["title"] == pending_report["title"]


def test_production_non_l4_default_overlays_required_set(monkeypatch) -> None:
    import react_agent.fixed_dag_production_external_compute as production

    monkeypatch.delenv("DISABLE_NON_L4_EXTERNAL_COMPUTE_DEFAULT", raising=False)
    called = []

    def fake_invoke(entry, **kwargs):
        called.append((entry.agent_id, kwargs.get("demo")))
        if entry.agent_id == "value_composite":
            assert kwargs["upstream_outputs"]["value_traditional_valuation"]["agent_id"] == (
                "value_traditional_valuation"
            )
            tool_result = _value_dimension_conclusion()
        elif entry.agent_id == "macro_composite":
            tool_result = _macro_conclusion()
        else:
            tool_result = _agent_conclusion(
                agent_id=entry.agent_id,
                external_agent_id=entry.external_agent_id,
                dimension=entry.dimension,
            )
        mapped = map_external_response_to_fixed_dag_object(
            _compute_envelope(entry.agent_id, entry.external_agent_id, tool_result)
        )
        return {
            "agent_id": entry.agent_id,
            "status": "pass",
            "mapped": mapped,
            "failure_code": "",
            "warning": "",
        }

    monkeypatch.setattr(production, "invoke_external_compute", fake_invoke)

    result = execute_fixed_dag_plan(
        _plan(),
        question="请分析 600519.SH",
        as_of="2026-06-04",
        context=Context(),
    )
    valid, reason = validate_dag_execution_result(result)

    assert valid, reason
    assert result["provenance"]["production_external_compute_enabled"] is True
    assert result["provenance"]["production_external_compute_called_agents"] == [
        "value_traditional_valuation",
        "value_ml_valuation",
        "value_meta_valuation",
        "market_ipo_investor_behavior",
        "market_capital_flow_chip",
        "risk_crash",
        "macro_analysis",
        "macro_index_valuation",
        "value_composite",
        "macro_composite",
    ]
    assert result["provenance"]["production_external_compute_mapped_agents"] == (
        result["provenance"]["production_external_compute_called_agents"]
    )
    assert result["provenance"]["production_external_compute_failed_agents"] == []
    assert result["provenance"]["external_compute_demo_called_agents"] == []
    assert result["provenance"]["external_invoked"] is False
    assert all(demo is False for _agent_id, demo in called)
    assert result["l2_conclusions"]["value_traditional_valuation"]["status"] == "complete"
    assert result["dimension_results"]["value"]["agent_id"] == "value_composite"
    assert result["dimension_results"]["macro"]["agent_id"] == "macro_composite"
    assert (
        result["report_input_bundle"]["l2_agent_summaries"][0]["source"]
        == "production_external_compute"
    )
    sources_by_agent = {
        item["agent_id"]: item["source"]
        for item in result["report_input_bundle"]["l3_composite_summaries"]
    }
    assert sources_by_agent["value_composite"] == "production_external_compute"
    assert sources_by_agent["macro_composite"] == "production_external_compute"
    assert "production_external_compute" in result["step_results"]["dimension:value"]["warnings"]


def test_production_non_l4_is_suppressed_by_demo(monkeypatch) -> None:
    import react_agent.fixed_dag_external_compute_bridge as bridge
    import react_agent.fixed_dag_production_external_compute as production

    monkeypatch.delenv("DISABLE_NON_L4_EXTERNAL_COMPUTE_DEFAULT", raising=False)

    def fail_production(*_args, **_kwargs):
        raise AssertionError("production non-L4 should be suppressed by demo mode")

    def fake_demo(entry, **_kwargs):
        mapped = map_external_response_to_fixed_dag_object(
            _compute_envelope(
                "value_ml_valuation",
                "valuation_ml",
                _agent_conclusion(),
            )
        )
        return {
            "agent_id": entry.agent_id,
            "status": "pass",
            "mapped": mapped,
            "failure_code": "",
            "warning": "",
        }

    monkeypatch.setattr(production, "invoke_external_compute", fail_production)
    monkeypatch.setattr(bridge, "invoke_external_compute", fake_demo)

    result = execute_fixed_dag_plan(
        _plan(),
        question="q",
        as_of="2026-06-04",
        context=Context(
            enable_external_compute_demo=True,
            external_compute_demo_allowlist=("value_ml_valuation",),
        ),
    )

    assert result["provenance"]["external_compute_demo_called_agents"] == [
        "value_ml_valuation"
    ]
    assert result["provenance"]["production_external_compute_called_agents"] == []
    assert result["provenance"]["production_external_compute_demo_suppressed"] is True


def test_production_non_l4_rollback_disables_only_non_l4(monkeypatch) -> None:
    import react_agent.fixed_dag_external_compute_bridge as bridge
    import react_agent.fixed_dag_production_external_compute as production

    monkeypatch.delenv("DISABLE_NON_L4_EXTERNAL_COMPUTE_DEFAULT", raising=False)
    monkeypatch.delenv("DISABLE_EXTERNAL_COMPUTE_DEFAULT", raising=False)

    def fail_production(*_args, **_kwargs):
        raise AssertionError("rollback should disable production non-L4 calls")

    def fake_l4(entry, **kwargs):
        if entry.agent_id == "decision_synthesizer":
            mapped = map_external_response_to_fixed_dag_object(
                _compute_envelope(
                    "decision_synthesizer",
                    "l4_decision_synthesizer",
                    build_decision_result({}, as_of="2026-06-04"),
                )
            )
        elif entry.agent_id == "report_generator":
            assert kwargs["report_input_bundle"]["schema"] == "report_input_bundle_v1"
            mapped = map_external_response_to_fixed_dag_object(
                _compute_envelope(
                    "report_generator",
                    "l4_report_generator",
                    build_report_result(
                        build_decision_result({}, as_of="2026-06-04"),
                        question="q",
                    ),
                )
            )
        else:
            raise AssertionError(f"unexpected L4 agent {entry.agent_id}")
        return {
            "agent_id": entry.agent_id,
            "status": "pass",
            "mapped": mapped,
            "failure_code": "",
            "warning": "",
        }

    monkeypatch.setattr(production, "invoke_external_compute", fail_production)
    monkeypatch.setattr(bridge, "invoke_external_compute", fake_l4)

    result = execute_fixed_dag_plan(
        _plan(),
        question="q",
        as_of="2026-06-04",
        context=Context(disable_non_l4_external_compute_default=True),
    )

    assert result["provenance"]["production_external_compute_called_agents"] == []
    assert result["provenance"]["production_external_compute_rollback_disabled"] is True
    assert result["provenance"]["external_compute_default_enabled"] is True
    assert result["provenance"]["external_compute_default_mapped_agents"] == [
        "decision_synthesizer",
        "report_generator",
    ]


def test_production_non_l4_selected_plan_calls_only_selected_agents(monkeypatch) -> None:
    import react_agent.fixed_dag_production_external_compute as production

    monkeypatch.delenv("DISABLE_NON_L4_EXTERNAL_COMPUTE_DEFAULT", raising=False)
    intent = build_route_intent(
        task_type="general",
        selected_dimensions=["value"],
        selected_agents=["value_ml_valuation"],
        route_confidence=0.7,
        fallback_reason="fallback to full DAG",
    )
    plan = compile_selected_fixed_dag_plan(intent, user_text="q", as_of="2026-06-09")

    def fake_invoke(entry, **kwargs):
        if entry.agent_id == "value_composite":
            assert set(kwargs["upstream_outputs"]) == {"value_ml_valuation"}
            tool_result = {
                **_value_dimension_conclusion(),
                "members": [
                    {
                        "agent_id": "value_ml_valuation",
                        "stance": 0.2,
                        "confidence": 0.72,
                        "weight": 1.0,
                        "status": "ok",
                    }
                ],
            }
        else:
            tool_result = _agent_conclusion(
                agent_id=entry.agent_id,
                external_agent_id=entry.external_agent_id,
                dimension=entry.dimension,
            )
        mapped = map_external_response_to_fixed_dag_object(
            _compute_envelope(entry.agent_id, entry.external_agent_id, tool_result)
        )
        return {
            "agent_id": entry.agent_id,
            "status": "pass",
            "mapped": mapped,
            "failure_code": "",
            "warning": "",
        }

    monkeypatch.setattr(production, "invoke_external_compute", fake_invoke)

    result = execute_fixed_dag_plan(
        plan,
        question="q",
        as_of="2026-06-04",
        context=Context(),
    )

    assert result["provenance"]["production_external_compute_called_agents"] == [
        "value_ml_valuation",
        "value_composite",
    ]
    assert set(result["l2_conclusions"]) == {"value_ml_valuation"}
    assert set(result["dimension_results"]) == {"value"}


def test_production_non_l4_required_failure_falls_back(monkeypatch) -> None:
    import react_agent.fixed_dag_production_external_compute as production

    monkeypatch.delenv("DISABLE_NON_L4_EXTERNAL_COMPUTE_DEFAULT", raising=False)

    def fake_invoke(entry, **_kwargs):
        if entry.agent_id == "value_ml_valuation":
            return {
                "agent_id": entry.agent_id,
                "status": "failed",
                "mapped": None,
                "failure_code": "timeout",
                "warning": "external_compute_failed:timeout",
            }
        if entry.agent_id == "value_composite":
            tool_result = _value_dimension_conclusion()
        elif entry.agent_id == "macro_composite":
            tool_result = _macro_conclusion()
        else:
            tool_result = _agent_conclusion(
                agent_id=entry.agent_id,
                external_agent_id=entry.external_agent_id,
                dimension=entry.dimension,
            )
        mapped = map_external_response_to_fixed_dag_object(
            _compute_envelope(entry.agent_id, entry.external_agent_id, tool_result)
        )
        return {
            "agent_id": entry.agent_id,
            "status": "pass",
            "mapped": mapped,
            "failure_code": "",
            "warning": "",
        }

    monkeypatch.setattr(production, "invoke_external_compute", fake_invoke)

    result = execute_fixed_dag_plan(
        _plan(),
        question="q",
        as_of="2026-06-04",
        context=Context(),
    )

    assert result["status"] == "degraded"
    assert result["l2_conclusions"]["value_ml_valuation"]["status"] == "pending_implementation"
    assert result["provenance"]["production_external_compute_required_failures"] == [
        "value_ml_valuation"
    ]
    assert "production_external_compute_failed:value_ml_valuation:timeout" in (
        result["step_results"]["l2:value_ml_valuation"]["warnings"]
    )


def test_external_compute_demo_overlays_l2_and_l3_results(monkeypatch) -> None:
    import react_agent.fixed_dag_external_compute_bridge as bridge

    def fake_invoke(entry, **_kwargs):
        if entry.agent_id == "value_ml_valuation":
            mapped = map_external_response_to_fixed_dag_object(
                _compute_envelope(
                    "value_ml_valuation",
                    "valuation_ml",
                    _agent_conclusion(),
                )
            )
        elif entry.agent_id == "risk_composite":
            mapped = map_external_response_to_fixed_dag_object(
                _compute_envelope(
                    "risk_composite",
                    "risk_synthesis",
                    _risk_conclusion(),
                )
            )
        else:
            raise AssertionError(f"unexpected demo agent {entry.agent_id}")
        return {
            "agent_id": entry.agent_id,
            "status": "pass",
            "mapped": mapped,
            "failure_code": "",
            "warning": "",
        }

    monkeypatch.setattr(bridge, "invoke_external_compute", fake_invoke)

    result = execute_fixed_dag_plan(
        _plan(),
        question="请分析 600519.SH",
        as_of="2026-06-04",
        context=Context(
            enable_external_compute_demo=True,
            external_compute_demo_allowlist=("value_ml_valuation", "risk_composite"),
        ),
    )
    valid, reason = validate_dag_execution_result(result)
    rendered = json.dumps(result, ensure_ascii=False).lower()

    assert valid, reason
    assert result["provenance"]["external_invoked"] is False
    assert result["provenance"]["external_compute_demo_enabled"] is True
    assert result["provenance"]["external_compute_demo_called_agents"] == [
        "value_ml_valuation",
        "risk_composite",
    ]
    assert result["provenance"]["external_compute_demo_mapped_agents"] == [
        "value_ml_valuation",
        "risk_composite",
    ]
    assert result["l2_conclusions"]["value_ml_valuation"]["status"] == "complete"
    assert result["l2_conclusions"]["value_ml_valuation"]["stance"] == "demo_positive"
    assert result["dimension_results"]["risk"]["gate"] == "pass"
    assert result["step_results"]["l2:value_ml_valuation"]["status"] == "complete"
    assert result["step_results"]["dimension:risk"]["status"] == "complete"
    assert result["step_results"]["l2:value_ml_valuation"]["agent_evidence"]["stance"] == "demo_positive"
    assert result["step_results"]["dimension:risk"]["composite_evidence"]["gate"] == "pass"
    assert result["report_input_bundle"]["risk_gate"]["gate"] == "pass"
    assert "核心结论与行动含义" in result["report_result"]["answer"]
    assert "风险维度：风险门与缺失合规证据" in result["report_result"]["answer"]
    assert result["report_input_bundle"]["l2_agent_summaries"]
    assert result["report_input_bundle"]["l3_composite_summaries"]
    assert any(
        item["agent_id"] == "value_ml_valuation"
        for item in result["report_input_bundle"]["l2_agent_summaries"]
    )
    assert "live_verified" not in result["report_result"]["answer"]
    assert "/v1/agent/invoke" not in result["report_result"]["answer"]
    assert "http://127.0.0.1" not in rendered
    assert "raw_response" not in rendered


def test_external_compute_demo_overlays_l1_before_l2_tasks(monkeypatch) -> None:
    import react_agent.fixed_dag_external_compute_bridge as bridge

    called = []

    def fake_invoke(entry, **_kwargs):
        called.append(entry.agent_id)
        if entry.agent_id == "financial_data_service":
            mapped = map_external_response_to_fixed_dag_object(
                _compute_envelope(
                    "financial_data_service",
                    "financial_data_service",
                    _data_bundle(),
                )
            )
        elif entry.agent_id == "entity_relation_extractor":
            mapped = map_external_response_to_fixed_dag_object(
                _compute_envelope(
                    "entity_relation_extractor",
                    "entity_relation_agent",
                    _entity_relation_bundle(),
                )
            )
        elif entry.agent_id == "macro_commodity_pricing":
            mapped = map_external_response_to_fixed_dag_object(
                _compute_envelope(
                    "macro_commodity_pricing",
                    "price_influence_agent",
                    _agent_conclusion(
                        agent_id="macro_commodity_pricing",
                        external_agent_id="price_influence_agent",
                        dimension="macro",
                    ),
                )
            )
        elif entry.agent_id == "macro_index_valuation":
            mapped = map_external_response_to_fixed_dag_object(
                _compute_envelope(
                    "macro_index_valuation",
                    "valuation_index",
                    _agent_conclusion(
                        agent_id="macro_index_valuation",
                        external_agent_id="valuation_index",
                        dimension="macro",
                    ),
                )
            )
        else:
            raise AssertionError(f"unexpected demo agent {entry.agent_id}")
        return {
            "agent_id": entry.agent_id,
            "status": "pass",
            "mapped": mapped,
            "failure_code": "",
            "warning": "",
        }

    monkeypatch.setattr(bridge, "invoke_external_compute", fake_invoke)

    result = execute_fixed_dag_plan(
        _plan(),
        question="请从宏观和估值角度分析贵州茅台 600519.SH",
        as_of="2026-06-04",
        context=Context(
            enable_external_compute_demo=True,
            external_compute_demo_allowlist=(
                "financial_data_service",
                "entity_relation_extractor",
                "macro_commodity_pricing",
                "macro_index_valuation",
            ),
        ),
    )
    valid, reason = validate_dag_execution_result(result)
    data_evidence = result["step_results"]["financial_data_service"]["agent_evidence"]
    entity_evidence = result["step_results"]["entity_relation_extractor"]["agent_evidence"]
    macro_task = result["step_results"]["l2:macro_commodity_pricing"]["agent_task"]
    l1_evidence = result["report_input_bundle"]["agent_evidence_bundle"]["l1_evidence"]
    rendered = json.dumps(result, ensure_ascii=False).lower()

    assert valid, reason
    assert called == [
        "financial_data_service",
        "entity_relation_extractor",
        "macro_commodity_pricing",
        "macro_index_valuation",
    ]
    assert result["data_bundle"]["status"] == "complete"
    assert result["entity_relation_bundle"]["status"] == "complete"
    assert data_evidence["status"] == "complete"
    assert data_evidence["sources_count"] == 2
    assert entity_evidence["status"] == "complete"
    assert entity_evidence["entities_count"] == 2
    assert macro_task["has_l1_data_bundle"] is True
    assert macro_task["has_l1_entity_relation_bundle"] is True
    assert result["l2_conclusions"]["macro_commodity_pricing"]["status"] == "complete"
    assert result["l2_conclusions"]["macro_index_valuation"]["status"] == "complete"
    assert l1_evidence["data_bundle_status"] == "complete"
    assert l1_evidence["entity_relation_status"] == "complete"
    assert result["provenance"]["external_compute_demo_mapped_agents"] == [
        "financial_data_service",
        "entity_relation_extractor",
        "macro_commodity_pricing",
        "macro_index_valuation",
    ]
    assert "raw_response" not in rendered
    assert "/v1/agent/invoke" not in rendered


def test_external_compute_overlays_task_aware_llm_placeholders(monkeypatch) -> None:
    import react_agent.fixed_dag_external_compute_bridge as bridge

    fake_model = _FakePlaceholderModel()
    monkeypatch.setattr(
        "react_agent.fixed_dag_llm_placeholders.load_chat_model",
        lambda _model: fake_model,
    )

    def fake_invoke(entry, **_kwargs):
        assert entry.agent_id == "value_ml_valuation"
        mapped = map_external_response_to_fixed_dag_object(
            _compute_envelope(
                "value_ml_valuation",
                "valuation_ml",
                _agent_conclusion(),
            )
        )
        return {
            "agent_id": entry.agent_id,
            "status": "pass",
            "mapped": mapped,
            "failure_code": "",
            "warning": "",
        }

    monkeypatch.setattr(bridge, "invoke_external_compute", fake_invoke)

    result = execute_fixed_dag_plan(
        _plan(),
        question="请从估值、市场、风险和宏观角度分析贵州茅台 600519.SH",
        as_of="2026-06-04",
        context=Context(
            enable_internal_llm_placeholders=True,
            enable_external_compute_demo=True,
            external_compute_demo_allowlist=("value_ml_valuation",),
        ),
    )
    valid, reason = validate_dag_execution_result(result)
    rendered = json.dumps(result, ensure_ascii=False).lower()

    assert valid, reason
    assert fake_model.prompts
    assert any("agent_task_schema: agent_task_v1" in prompt for prompt in fake_model.prompts)
    assert result["l2_conclusions"]["value_ml_valuation"]["status"] == "complete"
    assert result["l2_conclusions"]["value_ml_valuation"]["provenance"].get("runtime_path") != (
        "internal_llm_placeholder"
    )
    placeholder = result["l2_conclusions"]["market_fund_manager_behavior"]
    assert placeholder["status"] == "partial"
    assert placeholder["provenance"]["runtime_path"] == "internal_llm_placeholder"
    assert placeholder["provenance"]["required_output_schema"] == "agent_conclusion_v1"
    market_task = result["step_results"]["l2:market_fund_manager_behavior"]["agent_task"]
    assert market_task["required_output_schema"] == "agent_conclusion_v1"
    assert market_task["has_l1_data_bundle"] is True
    assert result["step_results"]["dimension:market"]["agent_task"]["upstream_agent_ids"]
    assert result["provenance"]["external_compute_demo_mapped_agents"] == ["value_ml_valuation"]
    assert result["provenance"]["internal_llm_placeholder_conclusions"] > 0
    assert "核心结论与行动含义" in result["report_result"]["answer"]
    assert "agent_task_v1" in json.dumps(result["report_input_bundle"], ensure_ascii=False)
    assert "raw_response" not in rendered
    assert "/v1/agent/invoke" not in rendered


def test_llm_report_synthesis_reads_external_agent_evidence(monkeypatch) -> None:
    import react_agent.fixed_dag_external_compute_bridge as bridge

    class FakeReportModel:
        def __init__(self) -> None:
            self.prompts: list[str] = []

        def invoke(self, prompt: str):
            self.prompts.append(prompt)
            return json.dumps(
                {
                    "title": "贵州茅台固定 DAG 研判报告",
                    "answer": (
                        "估值维度由机器学习企业估值给出 demo_positive 信号；"
                        "风险综合为 pass。综合研判：当前可进入关注池，但需要等待更多确认。"
                    ),
                    "sections": [
                        {
                            "id": "final_view",
                            "title": "最终研判",
                            "content": "大模型已读取单体智能体和综合智能体输入后整理报告。",
                        }
                    ],
                    "evidence_cards": [
                        {
                            "title": "参与输入",
                            "note": "包含 L2 机器学习企业估值和 L3 风险综合。",
                        }
                    ],
                    "limitations": ["显式开关下的大模型报告综合，不代表默认生产调用。"],
                },
                ensure_ascii=False,
            )

    fake_model = FakeReportModel()

    def fake_invoke(entry, **_kwargs):
        if entry.agent_id == "value_ml_valuation":
            mapped = map_external_response_to_fixed_dag_object(
                _compute_envelope(
                    "value_ml_valuation",
                    "valuation_ml",
                    _agent_conclusion(),
                )
            )
        elif entry.agent_id == "risk_composite":
            mapped = map_external_response_to_fixed_dag_object(
                _compute_envelope(
                    "risk_composite",
                    "risk_synthesis",
                    _risk_conclusion(),
                )
            )
        else:
            raise AssertionError(f"unexpected demo agent {entry.agent_id}")
        return {
            "agent_id": entry.agent_id,
            "status": "pass",
            "mapped": mapped,
            "failure_code": "",
            "warning": "",
        }

    monkeypatch.setattr(bridge, "invoke_external_compute", fake_invoke)
    monkeypatch.setattr(
        "react_agent.fixed_dag_report_synthesizer.load_chat_model",
        lambda _model: fake_model,
    )

    result = execute_fixed_dag_plan(
        _plan(),
        question="请分析 600519.SH",
        as_of="2026-06-04",
        context=Context(
            model="test/report-model",
            enable_external_compute_demo=True,
            external_compute_demo_allowlist=("value_ml_valuation", "risk_composite"),
            enable_llm_report_synthesis=True,
        ),
    )
    valid, reason = validate_dag_execution_result(result)
    rendered = json.dumps(result, ensure_ascii=False).lower()

    assert valid, reason
    assert fake_model.prompts
    assert "value_ml_valuation" in fake_model.prompts[0]
    assert "risk_gate" in fake_model.prompts[0]
    assert result["provenance"]["provider_invoked"] is True
    assert result["provenance"]["llm_report_synthesis_used"] is True
    assert result["workflow_snapshot"]["provenance"]["providerInvoked"] is True
    assert "综合研判：当前可进入关注池" in result["report_result"]["answer"]
    assert "报告生成输入摘要" not in result["report_result"]["answer"]
    assert "raw_response" not in rendered
    assert "/v1/agent/invoke" not in rendered


def test_llm_l3_explanation_enriches_l3_without_overriding_fusion(monkeypatch) -> None:
    import react_agent.fixed_dag_external_compute_bridge as bridge

    class FakeL3ExplanationModel:
        def __init__(self) -> None:
            self.prompts: list[str] = []

        def invoke(self, prompt: str):
            self.prompts.append(prompt)
            return json.dumps(
                {
                    "dimensions": [
                        {
                            "dimension": "value",
                            "research_points": [
                                {
                                    "claim": "价值综合只读取到机器学习估值，覆盖不足但方向偏正。",
                                    "support": "value_ml_valuation 提供 demo_positive 信号，其余价值成员仍缺失。",
                                    "interpretation": "该解释只能说明当前可用成员贡献，不能替代完整价值维。",
                                    "decision_implication": "最终报告应把价值维写成 partial 支持，而不是强结论。",
                                    "caveat": "LLM 解释层不改变 deterministic L3 stance、confidence 或权重。",
                                }
                            ],
                            "notes": ["language-only explanation"],
                        }
                    ]
                },
                ensure_ascii=False,
            )

    fake_model = FakeL3ExplanationModel()

    def fake_invoke(entry, **_kwargs):
        if entry.agent_id != "value_ml_valuation":
            raise AssertionError(f"unexpected demo agent {entry.agent_id}")
        mapped = map_external_response_to_fixed_dag_object(
            _compute_envelope(
                "value_ml_valuation",
                "valuation_ml",
                _agent_conclusion(),
            )
        )
        return {
            "agent_id": entry.agent_id,
            "status": "pass",
            "mapped": mapped,
            "failure_code": "",
            "warning": "",
        }

    monkeypatch.setattr(bridge, "invoke_external_compute", fake_invoke)
    monkeypatch.setattr(
        "react_agent.fixed_dag_l3_explanation_synthesizer.load_chat_model",
        lambda _model: fake_model,
    )

    result = execute_fixed_dag_plan(
        _plan(),
        question="请分析 600519.SH",
        as_of="2026-06-04",
        context=Context(
            model="test/l3-model",
            enable_external_compute_demo=True,
            external_compute_demo_allowlist=("value_ml_valuation",),
            enable_llm_l3_explanation=True,
        ),
    )
    valid, reason = validate_dag_execution_result(result)
    rendered = json.dumps(result, ensure_ascii=False).lower()
    value = result["dimension_results"]["value"]
    l3_outputs = result["report_input_bundle"]["agent_evidence_bundle"]["l3_composite_outputs"]
    value_detail = next(item for item in l3_outputs if item["dimension"] == "value")

    assert valid, reason
    assert fake_model.prompts
    assert result["provenance"]["provider_invoked"] is True
    assert result["provenance"]["llm_l3_explanation_used"] is True
    assert result["provenance"]["llm_report_synthesis_used"] is False
    assert value["status"] == "partial"
    assert value["provenance"]["llm_explanation"]["language_only"] is True
    assert value["provenance"]["llm_explanation"]["fusion_fields_overridden"] is False
    assert value["provenance"]["research_points"][0]["claim"].startswith("价值综合只读取到")
    assert value_detail["research_points"][0]["claim"].startswith("价值综合只读取到")
    assert "raw_response" not in rendered
    assert "/v1/agent/invoke" not in rendered


def test_llm_report_synthesis_failure_keeps_template_report(monkeypatch) -> None:
    class BadReportModel:
        def invoke(self, _prompt: str):
            return "not json raw_response secret traceback"

    monkeypatch.setattr(
        "react_agent.fixed_dag_report_synthesizer.load_chat_model",
        lambda _model: BadReportModel(),
    )

    result = execute_fixed_dag_plan(
        _plan(),
        question="q",
        as_of="2026-06-04",
        context=Context(model="test/report-model", enable_llm_report_synthesis=True),
    )
    valid, reason = validate_dag_execution_result(result)
    rendered = json.dumps(result, ensure_ascii=False).lower()

    assert valid, reason
    assert result["provenance"]["provider_invoked"] is True
    assert result["provenance"]["llm_report_synthesis_used"] is False
    assert result["provenance"]["llm_report_synthesis_attempted"] is True
    assert "报告生成输入摘要" in result["report_result"]["answer"]
    assert "raw_response" not in rendered
    assert "secret" not in rendered


def test_llm_report_missing_credential_records_safe_provider_diagnostic(monkeypatch) -> None:
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("DEEPSEEK_BASE_URL", raising=False)
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)

    def fail_load(_model: str):
        raise AssertionError("provider should not load without known credentials")

    monkeypatch.setattr("react_agent.fixed_dag_report_synthesizer.load_chat_model", fail_load)

    result = execute_fixed_dag_plan(
        _plan(),
        question="q",
        as_of="2026-06-04",
        context=Context(
            enable_llm_report_synthesis=True,
            llm_report_synthesis_model="deepseek/deepseek-chat",
        ),
    )
    valid, reason = validate_dag_execution_result(result)
    rendered = json.dumps(result, ensure_ascii=False).lower()
    provider_config = result["provenance"]["llm_report_synthesis_provider_config"]

    assert valid, reason
    assert result["provenance"]["provider_invoked"] is False
    assert result["provenance"]["llm_report_synthesis_used"] is False
    assert result["provenance"]["llm_report_synthesis_attempted"] is True
    assert (
        result["provenance"]["llm_report_synthesis_fallback_reason"]
        == "provider_configuration_missing:missing_credential"
    )
    assert provider_config["provider"] == "deepseek"
    assert provider_config["credential_status"] == "missing"
    assert provider_config["preflight_status"] == "missing_credential"
    assert "api_key" not in rendered
    assert "secret" not in rendered


def test_external_compute_demo_failure_falls_back_to_placeholder(monkeypatch) -> None:
    import react_agent.fixed_dag_external_compute_bridge as bridge

    def fake_invoke(entry, **_kwargs):
        return {
            "agent_id": entry.agent_id,
            "status": "failed",
            "mapped": None,
            "failure_code": "timeout",
            "warning": "external_compute_demo_failed:timeout",
        }

    monkeypatch.setattr(bridge, "invoke_external_compute", fake_invoke)

    result = execute_fixed_dag_plan(
        _plan(),
        question="q",
        as_of="2026-06-04",
        context=Context(
            enable_external_compute_demo=True,
            external_compute_demo_allowlist=("value_ml_valuation",),
        ),
    )
    valid, reason = validate_dag_execution_result(result)

    assert valid, reason
    assert result["provenance"]["external_compute_demo_failed_agents"] == [
        "value_ml_valuation"
    ]
    assert result["l2_conclusions"]["value_ml_valuation"]["status"] == "pending_implementation"
    assert "external_compute_demo_failed:timeout" in result["step_results"]["l2:value_ml_valuation"]["warnings"]
    assert "外部计算演示摘要" not in result["report_result"]["answer"]


def test_execute_selected_fixed_dag_plan_emits_selected_execution_subset() -> None:
    intent = build_route_intent(
        task_type="general",
        selected_dimensions=["value"],
        selected_agents=["value_ml_valuation"],
        route_confidence=0.7,
        fallback_reason="fallback to full DAG",
    )
    plan = compile_selected_fixed_dag_plan(intent, user_text="q", as_of="2026-06-09")

    result = execute_fixed_dag_plan(plan, question="q", as_of="2026-06-09")
    valid, reason = validate_dag_execution_result(result)

    assert valid, reason
    assert result["status"] == "complete"
    assert result["fallback_used"] is False
    assert result["execution_batches"] == topological_batches_for_selected_plan(plan)
    assert set(result["step_results"]) == {step["id"] for step in plan["steps"]}
    assert len(result["step_results"]) < len(RESET_RUNTIME_AGENT_IDS)
    assert set(result["l2_conclusions"]) == {"value_ml_valuation"}
    assert set(result["dimension_results"]) == {"value"}
    assert result["step_results"]["financial_data_service"]["runtime_kind"] == "external_http_candidate"
    assert result["step_results"]["financial_data_service"]["invoke_enabled"] is False
    assert result["step_results"]["entity_relation_extractor"]["runtime_kind"] == "pending_placeholder"
    assert result["step_results"]["l2:value_ml_valuation"]["runtime_kind"] == "external_http_candidate"
    assert result["step_results"]["l2:value_ml_valuation"]["live_verified"] is False
    assert "decision_synthesizer" not in result["step_results"]
    assert {item["id"] for item in result["workflow_snapshot"]["dimensionGroups"]} == {"value"}
    assert len(result["workflow_snapshot"]["dagSteps"]) == len(plan["steps"])
    assert set(result["workflow_snapshot"]["completedSteps"]) == set(result["step_results"])


def test_external_compute_demo_with_selected_plan_calls_only_selected_agents(monkeypatch) -> None:
    import react_agent.fixed_dag_external_compute_bridge as bridge

    intent = build_route_intent(
        task_type="general",
        selected_dimensions=["value"],
        selected_agents=["value_ml_valuation"],
        route_confidence=0.7,
        fallback_reason="fallback to full DAG",
    )
    plan = compile_selected_fixed_dag_plan(intent, user_text="q", as_of="2026-06-09")
    called = []

    def fake_invoke(entry, **_kwargs):
        called.append(entry.agent_id)
        mapped = map_external_response_to_fixed_dag_object(
            _compute_envelope(
                "value_ml_valuation",
                "valuation_ml",
                _agent_conclusion(),
            )
        )
        return {
            "agent_id": entry.agent_id,
            "status": "pass",
            "mapped": mapped,
            "failure_code": "",
            "warning": "",
        }

    monkeypatch.setattr(bridge, "invoke_external_compute", fake_invoke)

    result = execute_fixed_dag_plan(
        plan,
        question="q",
        as_of="2026-06-04",
        context=Context(
            enable_external_compute_demo=True,
            external_compute_demo_allowlist=(
                "value_ml_valuation",
                "value_meta_valuation",
            ),
        ),
    )

    assert called == ["value_ml_valuation"]
    assert result["provenance"]["external_compute_demo_called_agents"] == ["value_ml_valuation"]
    assert set(result["l2_conclusions"]) == {"value_ml_valuation"}
    assert set(result["dimension_results"]) == {"value"}


def test_invalid_plan_falls_back_to_deterministic_default_without_raising() -> None:
    bad = copy.deepcopy(_plan())
    bad["steps"][0]["agent_id"] = "bad_agent"

    result = execute_fixed_dag_plan(bad, question="q", as_of="2026-06-04")
    valid, reason = validate_dag_execution_result(result)

    assert valid, reason
    assert result["status"] == "degraded"
    assert result["fallback_used"] is True
    assert result["fallback_reason"] == "invalid_agent_id"
    assert result["workflow_snapshot"]["provenance"]["fallbackUsed"] is True
