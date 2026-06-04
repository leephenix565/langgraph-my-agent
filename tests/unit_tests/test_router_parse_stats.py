import json

from react_agent import router_parse
from react_agent.fixed_dag_contracts import (
    RESET_RUNTIME_AGENT_IDS,
    validate_fixed_dag_plan,
)


def test_parse_stats_invalid_json_uses_fixed_dag_fallback() -> None:
    plan, stats = router_parse.parse_fixed_dag_plan_with_stats("not json")
    assert plan["schema"] == "fixed_dag_plan_v1"
    assert plan["target_agent_ids"] == list(RESET_RUNTIME_AGENT_IDS)
    assert stats == {
        "schema": "fixed_dag_plan_v1",
        "parse_ok": False,
        "used_fallback": True,
        "fallback_reason": "missing_json",
        "filtered_agents": [],
    }


def test_parse_stats_valid_plan_keeps_plan_id() -> None:
    raw = json.dumps(
        {
            "schema": "fixed_dag_plan_v1",
            "plan_id": "reset-custom",
            "target_agent_ids": ["report_generator", "decision_synthesizer"],
        }
    )
    plan, stats = router_parse.parse_fixed_dag_plan_with_stats(raw)
    assert stats["parse_ok"] is True
    assert stats["used_fallback"] is False
    assert plan["plan_id"] == "reset-custom"
    assert plan["target_agent_ids"] == list(RESET_RUNTIME_AGENT_IDS)
    valid, reason = validate_fixed_dag_plan(plan)
    assert valid, reason


def test_parse_stats_no_first_n_or_layer_count_limits() -> None:
    raw = json.dumps(
        {
            "schema": "fixed_dag_plan_v1",
            "target_agent_ids": list(RESET_RUNTIME_AGENT_IDS),
        }
    )
    plan, stats = router_parse.parse_fixed_dag_plan_with_stats(raw)
    assert stats["parse_ok"] is True
    assert len(plan["target_agent_ids"]) == len(RESET_RUNTIME_AGENT_IDS)
    assert stats["filtered_agents"] == []
