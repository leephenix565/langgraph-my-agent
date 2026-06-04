import copy
import json

from react_agent.fixed_dag_contracts import (
    MACRO_AGENT_IDS,
    MARKET_AGENT_IDS,
    RESET_RUNTIME_AGENT_IDS,
    RISK_AGENT_IDS,
    VALUE_AGENT_IDS,
    build_default_fixed_dag_plan,
)
from react_agent.fixed_dag_executor import (
    build_dag_step_index,
    build_initial_step_results,
    execute_fixed_dag_plan,
    topological_batches,
    validate_dag_execution_result,
    validate_dag_steps,
    validate_step_result,
)


def _plan():
    return build_default_fixed_dag_plan("q", as_of="2026-06-04")


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
    payload = json.dumps(result)
    for forbidden in ("layerMode", "fusionSteps", "layerPlan", "value_financial_analysis"):
        assert forbidden not in payload


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
