import copy
import json

from react_agent.context import Context
from react_agent.fixed_dag_contracts import (
    MACRO_AGENT_IDS,
    MARKET_AGENT_IDS,
    RESET_RUNTIME_AGENT_IDS,
    RISK_AGENT_IDS,
    VALUE_AGENT_IDS,
    build_default_fixed_dag_plan,
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


def _plan():
    return build_default_fixed_dag_plan("q", as_of="2026-06-04")


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
    assert "composite_evidence" in result["step_results"]["dimension:value"]
    assert "报告生成输入摘要" in result["report_result"]["answer"]
    assert "sentiment_company_radar" not in result["step_results"]["dimension:risk"]["depends_on"]
    payload = json.dumps(result)
    for forbidden in ("layerMode", "fusionSteps", "layerPlan", "value_financial_analysis"):
        assert forbidden not in payload


def test_execute_fixed_dag_plan_default_context_does_not_load_internal_llm(monkeypatch) -> None:
    def fail_load(_model: str):
        raise AssertionError("internal placeholder provider should stay default-off")

    monkeypatch.setattr("react_agent.fixed_dag_llm_placeholders.load_chat_model", fail_load)

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
    assert "单体智能体输入" in result["report_result"]["answer"]
    assert "综合智能体输入" in result["report_result"]["answer"]
    assert "外部计算演示摘要" in result["report_result"]["answer"]
    assert "live_verified" not in result["report_result"]["answer"]
    assert "/v1/agent/invoke" not in result["report_result"]["answer"]
    assert "http://127.0.0.1" not in rendered
    assert "raw_response" not in rendered


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
