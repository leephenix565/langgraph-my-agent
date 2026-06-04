import json

from react_agent.fixed_dag_contracts import (
    DIMENSION_GROUPS,
    FIXED_DAG_STAGE_ORDER,
    L2_CONCLUSION_AGENT_IDS,
    RESET_RUNTIME_AGENT_IDS,
    SENTIMENT_COMPANY_RADAR_OUTPUT_ROUTES,
    build_deterministic_fixed_dag_plan,
    build_l2_conclusions,
    build_workflow_snapshot_v2,
)


def _contains_key(value, key: str) -> bool:
    if isinstance(value, dict):
        return key in value or any(_contains_key(item, key) for item in value.values())
    if isinstance(value, list):
        return any(_contains_key(item, key) for item in value)
    return False


def test_fixed_dag_plan_has_six_stages_and_all_targets() -> None:
    plan = build_deterministic_fixed_dag_plan("q")
    assert [stage["id"] for stage in plan["stages"]] == list(FIXED_DAG_STAGE_ORDER)
    assert plan["target_agent_ids"] == list(RESET_RUNTIME_AGENT_IDS)
    assert len(plan["target_agent_ids"]) == 27
    l2_targets = [
        agent_id
        for agent_id in plan["target_agent_ids"]
        if agent_id in L2_CONCLUSION_AGENT_IDS
    ]
    assert len(l2_targets) == 18
    assert "financial_metrics_analyzer" not in plan["target_agent_ids"]
    assert not _contains_key(plan, "mode")


def test_sentiment_company_radar_routes_only_to_market_composite() -> None:
    conclusions = build_l2_conclusions()
    radar = conclusions["sentiment_company_radar"]
    assert radar["output_routes"] == list(SENTIMENT_COMPANY_RADAR_OUTPUT_ROUTES)
    assert radar["output_routes"] == ["market_composite"]
    assert list(conclusions).count("sentiment_company_radar") == 1
    assert "sentiment_company_radar" in DIMENSION_GROUPS["market"]
    assert "sentiment_company_radar" not in DIMENSION_GROUPS["risk"]


def test_workflow_snapshot_v2_has_no_legacy_public_fields() -> None:
    plan = build_deterministic_fixed_dag_plan("q")
    snapshot = build_workflow_snapshot_v2(
        plan=plan,
        current_stage="report",
        completed_steps=[step["id"] for step in plan["steps"]],
    )
    payload = json.dumps(snapshot)
    assert snapshot["schema"] == "workflow_snapshot_v2"
    assert snapshot["finalSource"] == "reset_skeleton"
    assert snapshot["provenance"]["providerInvoked"] is False
    assert snapshot["provenance"]["externalInvoked"] is False
    for field in ("layerMode", "fusionSteps", "layerPlan"):
        assert field not in payload
    assert set(DIMENSION_GROUPS) == {item["id"] for item in snapshot["dimensionGroups"]}
