import json

from react_agent.fixed_dag_contracts import (
    FIXED_DAG_SCHEMA_VERSION,
    RESET_RUNTIME_AGENT_IDS,
    build_deterministic_fixed_dag_plan,
)
from react_agent.router_parse import parse_fixed_dag_plan_with_stats


def test_parse_with_extra_text_preserves_plan_id() -> None:
    raw = 'text before {"schema":"fixed_dag_plan_v1","plan_id":"custom","target_agent_ids":["route_planner"]} trailing'
    plan, stats = parse_fixed_dag_plan_with_stats(raw, user_text="q")
    assert stats["parse_ok"] is True
    assert stats["used_fallback"] is False
    assert plan["plan_id"] == "custom"
    assert plan["schema"] == FIXED_DAG_SCHEMA_VERSION


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
            "target_agent_ids": ["route_planner", "bad_id", "route_planner"],
        }
    )
    plan, stats = parse_fixed_dag_plan_with_stats(raw)
    assert stats["parse_ok"] is True
    assert "bad_id" in stats["filtered_agents"]
    assert "route_planner" in stats["filtered_agents"]
    assert "route_planner" not in plan["target_agent_ids"]
    assert plan["target_agent_ids"] == list(RESET_RUNTIME_AGENT_IDS)


def test_fixed_dag_plan_has_no_mode_or_layer_dispatch_fields() -> None:
    plan, stats = parse_fixed_dag_plan_with_stats(
        json.dumps({"schema": "fixed_dag_plan_v1", "target_agent_ids": []})
    )
    assert stats["parse_ok"] is True
    text = json.dumps(plan)
    forbidden = ("layer_plan", "layer_mode", "current_layer", "fusion_verdict")
    for field in forbidden:
        assert field not in text
