import json

from react_agent.fixed_dag_contracts import (
    FIXED_DAG_SCHEMA_VERSION,
    RESET_RUNTIME_AGENT_IDS,
    build_deterministic_fixed_dag_plan,
    validate_fixed_dag_plan,
    validate_route_intent,
)
from react_agent.router_parse import (
    normalize_route_intent,
    parse_dimension_route_intent_json,
    parse_fixed_dag_plan_with_stats,
    parse_route_intent_json,
)


def test_parse_with_extra_text_preserves_plan_id() -> None:
    raw = 'text before {"schema":"fixed_dag_plan_v1","plan_id":"custom","target_agent_ids":["route_planner"]} trailing'
    plan, stats = parse_fixed_dag_plan_with_stats(raw, user_text="q")
    assert stats["parse_ok"] is True
    assert stats["used_fallback"] is False
    assert plan["plan_id"] == "custom"
    assert plan["schema"] == FIXED_DAG_SCHEMA_VERSION
    assert plan["schema_version"] == FIXED_DAG_SCHEMA_VERSION
    assert plan["target"] == list(RESET_RUNTIME_AGENT_IDS)
    assert plan["dag_steps"] == plan["steps"]
    valid, reason = validate_fixed_dag_plan(plan)
    assert valid, reason


def test_parse_invalid_json_falls_back_to_deterministic_plan() -> None:
    plan, stats = parse_fixed_dag_plan_with_stats("not json", user_text="q")
    assert plan == build_deterministic_fixed_dag_plan("q")
    assert stats["parse_ok"] is False
    assert stats["used_fallback"] is True
    assert stats["fallback_reason"] == "missing_json"


def test_parse_filters_unknown_agents_and_restores_full_reset_targets() -> None:
    raw = json.dumps(
        {
            "schema": "fixed_dag_plan_v1",
            "plan_id": "filtered",
            "target_agent_ids": ["route_planner", "bad_id"],
        }
    )
    plan, stats = parse_fixed_dag_plan_with_stats(raw)
    assert stats["parse_ok"] is True
    assert "bad_id" in stats["filtered_agents"]
    assert "route_planner" not in stats["filtered_agents"]
    assert "route_planner" in plan["target_agent_ids"]
    assert plan["target_agent_ids"] == list(RESET_RUNTIME_AGENT_IDS)
    valid, reason = validate_fixed_dag_plan(plan)
    assert valid, reason


def test_fixed_dag_plan_has_no_mode_or_layer_dispatch_fields() -> None:
    plan, stats = parse_fixed_dag_plan_with_stats(
        json.dumps({"schema": "fixed_dag_plan_v1", "target_agent_ids": []})
    )
    assert stats["parse_ok"] is True
    text = json.dumps(plan)
    forbidden = ("layer_plan", "layer_mode", "current_layer", "fusion_verdict")
    for field in forbidden:
        assert field not in text


def _valid_route_intent_payload() -> dict:
    return {
        "schema": "route_intent_v1",
        "schema_version": "route_intent_v1",
        "task_type": "single",
        "targets": ["example company"],
        "selected_dimensions": ["value", "risk"],
        "selected_agents": ["value_research_synthesis", "risk_identification"],
        "task_brief_by_agent": {
            "value_research_synthesis": "Summarize value signals.",
            "risk_identification": "Identify risk gates.",
        },
        "route_confidence": 0.74,
        "needs_clarification": False,
        "clarification_question": "",
        "fallback_reason": "fallback to full DAG",
        "provenance": {"source": "unit_fixture"},
    }


def test_parse_route_intent_json_parses_valid_intent() -> None:
    intent, stats = parse_route_intent_json(
        f"before {json.dumps(_valid_route_intent_payload())} after",
        question="Should I evaluate example company?",
    )
    valid, reason = validate_route_intent(intent)

    assert valid, reason
    assert stats["parse_ok"] is True
    assert stats["used_fallback"] is False
    assert intent["schema"] == "route_intent_v1"
    assert intent["task_type"] == "single"
    assert intent["selected_dimensions"] == ["value", "risk"]
    assert intent["selected_agents"] == ["value_research_synthesis", "risk_identification"]
    assert intent["task_brief_by_agent"]["risk_identification"] == "Identify risk gates."
    assert intent["provenance"]["provider_invoked"] is False
    assert intent["provenance"]["external_invoked"] is False


def test_parse_dimension_route_intent_json_accepts_dimensions_only() -> None:
    payload = {
        "schema": "route_intent_v1",
        "schema_version": "route_intent_v1",
        "task_type": "general",
        "targets": ["example company"],
        "selected_dimensions": ["value"],
        "route_confidence": 0.74,
        "needs_clarification": False,
        "clarification_question": "",
        "fallback_reason": "",
        "provenance": {"source": "unit_fixture"},
    }
    intent, stats = parse_dimension_route_intent_json(json.dumps(payload))
    valid, reason = validate_route_intent(intent)

    assert valid, reason
    assert stats["parse_ok"] is True
    assert stats["used_fallback"] is False
    assert stats["route_granularity"] == "dimension"
    assert stats["selected_dimensions"] == ["value"]
    assert intent["selected_dimensions"] == ["value"]
    assert intent["selected_agents"] == []
    assert intent["provenance"]["route_granularity"] == "dimension"
    assert intent["provenance"]["provider_invoked"] is False
    assert intent["provenance"]["external_invoked"] is False


def test_parse_dimension_route_intent_json_preserves_single_risk_policy() -> None:
    payload = {
        "schema": "route_intent_v1",
        "schema_version": "route_intent_v1",
        "task_type": "single",
        "targets": ["example company"],
        "selected_dimensions": ["value"],
        "route_confidence": 0.74,
        "needs_clarification": False,
        "clarification_question": "",
        "fallback_reason": "",
        "provenance": {"source": "unit_fixture"},
    }
    intent, stats = parse_dimension_route_intent_json(json.dumps(payload))

    assert stats["parse_ok"] is False
    assert stats["used_fallback"] is True
    assert stats["fallback_reason"] == "validation_error:risk_dimension_required"
    assert stats["selected_dimensions"] == ["value"]
    assert intent["needs_clarification"] is True


def test_parse_dimension_route_intent_json_accepts_risk_macro_dimensions() -> None:
    payload = {
        "schema": "route_intent_v1",
        "schema_version": "route_intent_v1",
        "task_type": "general",
        "targets": ["example company"],
        "selected_dimensions": ["risk", "macro"],
        "route_confidence": 0.86,
        "needs_clarification": False,
        "clarification_question": "",
        "fallback_reason": "",
        "provenance": {"source": "unit_fixture"},
    }
    intent, stats = parse_dimension_route_intent_json(json.dumps(payload))

    assert stats["parse_ok"] is True
    assert stats["used_fallback"] is False
    assert intent["selected_dimensions"] == ["risk", "macro"]
    assert intent["selected_agents"] == []


def test_parse_dimension_route_intent_json_falls_back_for_invalid_dimension_shape() -> None:
    for dimensions, reason in (
        (["value", "unknown"], "unknown_selected_dimension"),
        ([], "selected_dimensions_missing"),
    ):
        payload = {
            "schema": "route_intent_v1",
            "schema_version": "route_intent_v1",
            "task_type": "general",
            "targets": [],
            "selected_dimensions": dimensions,
            "route_confidence": 0.8,
            "needs_clarification": False,
            "clarification_question": "",
            "fallback_reason": "",
            "provenance": {"source": "unit_fixture"},
        }
        intent, stats = parse_dimension_route_intent_json(json.dumps(payload))

        assert stats["parse_ok"] is False
        assert stats["used_fallback"] is True
        assert stats["fallback_reason"] == reason
        assert intent["needs_clarification"] is True


def test_parse_dimension_route_intent_json_falls_back_for_low_confidence_or_clarification() -> None:
    for confidence, needs_clarification, reason in (
        (0.2, False, "low_route_confidence"),
        (0.9, True, "route_intent_needs_clarification"),
    ):
        payload = {
            "schema": "route_intent_v1",
            "schema_version": "route_intent_v1",
            "task_type": "general",
            "targets": [],
            "selected_dimensions": ["value"],
            "route_confidence": confidence,
            "needs_clarification": needs_clarification,
            "clarification_question": "Which target?" if needs_clarification else "",
            "fallback_reason": "",
            "provenance": {"source": "unit_fixture"},
        }
        intent, stats = parse_dimension_route_intent_json(json.dumps(payload))

        assert stats["parse_ok"] is False
        assert stats["used_fallback"] is True
        assert stats["fallback_reason"] == reason
        assert intent["needs_clarification"] is True


def test_parse_dimension_route_intent_json_blocks_agent_level_selection() -> None:
    payload = {
        "schema": "route_intent_v1",
        "schema_version": "route_intent_v1",
        "task_type": "general",
        "targets": [],
        "selected_dimensions": ["value"],
        "selected_agents": ["value_research_synthesis"],
        "route_confidence": 0.8,
        "needs_clarification": False,
        "clarification_question": "",
        "fallback_reason": "",
        "provenance": {"source": "unit_fixture"},
    }
    intent, stats = parse_dimension_route_intent_json(json.dumps(payload))

    assert stats["parse_ok"] is False
    assert stats["used_fallback"] is True
    assert stats["fallback_reason"] == "agent_level_route_not_allowed_in_dimension_mode"
    assert stats["agent_level_selection_blocked"] is True
    assert intent["needs_clarification"] is True


def test_parse_route_intent_json_filters_unknown_agent_when_valid_agents_remain() -> None:
    payload = _valid_route_intent_payload()
    payload["selected_agents"] = [
        "value_research_synthesis",
        "risk_identification",
        "not_a_reset_agent",
    ]

    intent, stats = parse_route_intent_json(json.dumps(payload))
    valid, reason = validate_route_intent(intent)

    assert valid, reason
    assert stats["parse_ok"] is True
    assert stats["filtered_agents"] == ["not_a_reset_agent"]
    assert intent["selected_agents"] == ["value_research_synthesis", "risk_identification"]


def test_parse_route_intent_json_falls_back_for_legacy_or_executable_fields() -> None:
    for field, value in (
        ("layerMode", "mode"),
        ("fusionSteps", []),
        ("dag_steps", []),
        ("depends_on", ["route_planner"]),
        ("endpoint", "http://127.0.0.1:10028/v1/agent/compute"),
        ("env", {"ROUTER_TOKEN": "redacted"}),
        ("secrets", ["redacted"]),
        ("raw_response", {"body": "redacted"}),
        ("chain_of_thought", "redacted"),
    ):
        payload = _valid_route_intent_payload()
        payload[field] = value
        intent, stats = parse_route_intent_json(json.dumps(payload))

        assert stats["parse_ok"] is False
        assert stats["used_fallback"] is True
        assert stats["fallback_reason"] == "forbidden_route_intent_field_present"
        assert intent["needs_clarification"] is True
        assert intent["fallback_reason"] == "planner_parse_failed"


def test_parse_route_intent_json_falls_back_for_legacy_mode_values() -> None:
    payload = _valid_route_intent_payload()
    payload["provenance"]["route_mode"] = "Star"
    intent, stats = parse_route_intent_json(json.dumps(payload))

    assert stats["parse_ok"] is False
    assert stats["fallback_reason"] == "legacy_route_value_present"
    assert intent["needs_clarification"] is True


def test_parse_route_intent_json_falls_back_for_nested_unsafe_fields() -> None:
    payload = _valid_route_intent_payload()
    payload["provenance"]["endpoint"] = "http://127.0.0.1:10028/v1/agent/compute"
    intent, stats = parse_route_intent_json(json.dumps(payload))

    assert stats["parse_ok"] is False
    assert stats["fallback_reason"] == "forbidden_route_intent_field_present"
    assert intent["needs_clarification"] is True


def test_parse_route_intent_json_falls_back_for_removed_or_legacy_agents() -> None:
    for agent_id, reason in (
        ("a16_ml_valuation", "legacy_agent_id_present"),
        ("value_financial_analysis", "removed_agent_present"),
        ("not_a_reset_agent", "unknown_selected_agent"),
    ):
        payload = _valid_route_intent_payload()
        payload["selected_agents"] = [agent_id]
        intent, stats = parse_route_intent_json(json.dumps(payload))

        assert stats["parse_ok"] is False
        assert stats["fallback_reason"] == reason
        assert stats["filtered_agents"] == [agent_id]
        assert intent["needs_clarification"] is True


def test_parse_route_intent_json_enforces_sentiment_market_only() -> None:
    payload = {
        **_valid_route_intent_payload(),
        "task_type": "sentiment",
        "selected_dimensions": ["risk"],
        "selected_agents": ["sentiment_company_radar"],
        "task_brief_by_agent": {
            "sentiment_company_radar": "Summarize sentiment signals."
        },
    }
    intent, stats = parse_route_intent_json(json.dumps(payload))

    assert stats["parse_ok"] is False
    assert stats["fallback_reason"] == "validation_error:agent_dimension_mismatch"
    assert intent["needs_clarification"] is True


def test_parse_route_intent_json_enforces_investment_risk_policy() -> None:
    payload = {
        **_valid_route_intent_payload(),
        "selected_dimensions": ["value"],
        "selected_agents": ["value_research_synthesis"],
        "task_brief_by_agent": {
            "value_research_synthesis": "Summarize value signals."
        },
    }
    intent, stats = parse_route_intent_json(json.dumps(payload))

    assert stats["parse_ok"] is False
    assert stats["fallback_reason"] == "validation_error:risk_dimension_required"
    assert intent["needs_clarification"] is True


def test_normalize_route_intent_returns_safe_fallback_for_bad_shape() -> None:
    intent = normalize_route_intent(
        {
            "schema": "route_intent_v1",
            "task_type": "general",
            "selected_dimensions": ["value"],
            "selected_agents": ["not_a_reset_agent"],
            "fallback_reason": "fallback to full DAG",
        }
    )

    assert intent["schema"] == "route_intent_v1"
    assert intent["needs_clarification"] is True
    assert intent["provenance"]["provider_invoked"] is False
    assert intent["provenance"]["external_invoked"] is False
