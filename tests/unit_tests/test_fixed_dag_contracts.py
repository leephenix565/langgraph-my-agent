import json

from react_agent.fixed_dag_contracts import (
    DIMENSION_GROUPS,
    FIXED_DAG_STAGE_ORDER,
    L1_AGENT_IDS,
    L2_CONCLUSION_AGENT_IDS,
    L3_COMPOSITE_AGENT_IDS,
    L4_AGENT_IDS,
    MACRO_AGENT_IDS,
    MARKET_AGENT_IDS,
    RESET_RUNTIME_AGENT_IDS,
    RISK_AGENT_IDS,
    SENTIMENT_COMPANY_RADAR_OUTPUT_ROUTES,
    VALUE_AGENT_IDS,
    build_data_bundle,
    build_decision_result,
    build_default_fixed_dag_plan,
    build_dimension_results,
    build_entity_relation_bundle,
    build_l2_conclusions,
    build_pending_conclusion,
    build_report_result,
    build_risk_composite,
    build_workflow_snapshot_v2,
    normalize_fixed_dag_plan,
    validate_conclusion_object,
    validate_data_bundle,
    validate_decision_result,
    validate_dimension_composite_result,
    validate_entity_relation_bundle,
    validate_fixed_dag_plan,
    validate_report_result,
    validate_workflow_snapshot_v2,
)


def _contains_key(value, key: str) -> bool:
    if isinstance(value, dict):
        return key in value or any(_contains_key(item, key) for item in value.values())
    if isinstance(value, list):
        return any(_contains_key(item, key) for item in value)
    return False


def test_roster_constants_are_v4_feedback_aligned() -> None:
    assert len(RESET_RUNTIME_AGENT_IDS) == 27
    assert len(L1_AGENT_IDS) == 3
    assert len(L2_CONCLUSION_AGENT_IDS) == 18
    assert len(L3_COMPOSITE_AGENT_IDS) == 4
    assert len(L4_AGENT_IDS) == 2
    assert len(VALUE_AGENT_IDS) == 4
    assert len(MARKET_AGENT_IDS) == 5
    assert len(RISK_AGENT_IDS) == 4
    assert len(MACRO_AGENT_IDS) == 5
    assert "value_financial_analysis" not in RESET_RUNTIME_AGENT_IDS
    assert "financial_metrics_analyzer" not in RESET_RUNTIME_AGENT_IDS
    assert "sentiment_company_radar" in MARKET_AGENT_IDS
    assert "sentiment_company_radar" not in RISK_AGENT_IDS
    assert SENTIMENT_COMPANY_RADAR_OUTPUT_ROUTES == ("market_composite",)


def test_fixed_dag_plan_normalizes_and_validates() -> None:
    plan = build_default_fixed_dag_plan("q", as_of="2026-06-04")
    valid, reason = validate_fixed_dag_plan(plan)

    assert valid, reason
    assert [stage["id"] for stage in plan["stages"]] == list(FIXED_DAG_STAGE_ORDER)
    assert plan["target_agent_ids"] == list(RESET_RUNTIME_AGENT_IDS)
    assert plan["target"] == list(RESET_RUNTIME_AGENT_IDS)
    assert len(plan["dag_steps"]) == len(RESET_RUNTIME_AGENT_IDS)
    assert not _contains_key(plan, "mode")
    assert not _contains_key(plan, "layerMode")


def test_normalize_fixed_dag_plan_fail_soft_restores_deterministic_shape() -> None:
    normalized = normalize_fixed_dag_plan(
        {
            "schema": "wrong",
            "plan_id": "custom",
            "target_agent_ids": ["bad_id"],
            "mode": "Star",
        }
    )
    valid, reason = validate_fixed_dag_plan(normalized)

    assert valid, reason
    assert normalized["plan_id"] == "custom"
    assert normalized["target_agent_ids"] == list(RESET_RUNTIME_AGENT_IDS)
    assert not _contains_key(normalized, "mode")


def test_l1_bundles_are_deterministic_and_keep_as_of_boundary() -> None:
    plan = build_default_fixed_dag_plan("question", as_of="2026-06-04")
    data_bundle = build_data_bundle(plan)
    entity_bundle = build_entity_relation_bundle(plan)

    for bundle in (data_bundle, entity_bundle):
        assert bundle["status"] == "pending_implementation"
        assert bundle["as_of"] == "2026-06-04"
        assert bundle["data_as_of"] <= bundle["as_of"]
        assert "no provider" in " ".join(bundle["notes"]).lower()
    valid, reason = validate_data_bundle(data_bundle)
    assert valid, reason
    valid, reason = validate_entity_relation_bundle(entity_bundle)
    assert valid, reason


def test_pending_conclusion_validates_and_event_flags_are_optional() -> None:
    item = build_pending_conclusion(
        "sentiment_company_radar",
        "market",
        as_of="2026-06-04",
        reason="test",
    )
    valid, reason = validate_conclusion_object(item)

    assert valid, reason
    assert item["event_flags"] == []
    assert item["output_routes"] == ["market_composite"]
    item.pop("event_flags")
    valid, reason = validate_conclusion_object(item)
    assert valid, reason


def test_l2_conclusions_validate_all_agents_once() -> None:
    conclusions = build_l2_conclusions(
        build_default_fixed_dag_plan("q", as_of="2026-06-04")
    )

    assert list(conclusions) == list(L2_CONCLUSION_AGENT_IDS)
    assert len(conclusions) == 18
    for item in conclusions.values():
        valid, reason = validate_conclusion_object(item)
        assert valid, reason


def test_dimension_composites_validate_and_preserve_sentiment_boundary() -> None:
    conclusions = build_l2_conclusions(
        build_default_fixed_dag_plan("q", as_of="2026-06-04")
    )
    results = build_dimension_results(conclusions, as_of="2026-06-04")

    assert set(results) == set(DIMENSION_GROUPS)
    assert "sentiment_company_radar" in results["market"]["contributing_agents"]
    assert "sentiment_company_radar" not in results["risk"]["contributing_agents"]
    assert {"gate", "veto", "penalty", "risk_score"} <= set(results["risk"])
    assert {"regime", "dimension_weights", "risk_sensitivity"} <= set(results["macro"])
    for item in results.values():
        valid, reason = validate_dimension_composite_result(item)
        assert valid, reason


def test_risk_composite_ignores_sentiment_even_if_present_in_input() -> None:
    conclusions = build_l2_conclusions(
        build_default_fixed_dag_plan("q", as_of="2026-06-04")
    )
    risk = build_risk_composite(conclusions, as_of="2026-06-04")

    assert risk["contributing_agents"] == list(RISK_AGENT_IDS)
    assert "sentiment_company_radar" not in risk["contributing_agents"]


def test_decision_result_validates_and_risk_veto_is_conservative() -> None:
    results = build_dimension_results({}, as_of="2026-06-04")
    results["risk"]["veto"] = True
    decision = build_decision_result(results, as_of="2026-06-04")
    valid, reason = validate_decision_result(decision)

    assert valid, reason
    assert -1.0 <= decision["score"] <= 1.0
    assert decision["decision"] == "conservative_pending"
    assert len(decision["reasoning_trace"]) >= 3


def test_report_result_validates_and_has_reset_limitations() -> None:
    decision = build_decision_result({}, as_of="2026-06-04")
    report = build_report_result(decision, question="q")
    valid, reason = validate_report_result(report)

    assert valid, reason
    assert report["evidence_cards"]
    joined = "\n".join([report["answer"], *report["limitations"]])
    assert "No provider" in joined
    assert "external /v1/agent/invoke" in joined
    assert "not implemented" in joined


def test_workflow_snapshot_v2_has_no_legacy_public_fields() -> None:
    plan = build_default_fixed_dag_plan("q")
    conclusions = build_l2_conclusions(plan)
    dimensions = build_dimension_results(conclusions)
    decision = build_decision_result(dimensions)
    report = build_report_result(decision, question="q")
    snapshot = build_workflow_snapshot_v2(
        plan=plan,
        l2_conclusions=conclusions,
        dimension_results=dimensions,
        decision_result=decision,
        report_result=report,
    )
    valid, reason = validate_workflow_snapshot_v2(snapshot)
    payload = json.dumps(snapshot)

    assert valid, reason
    assert snapshot["schema"] == "workflow_snapshot_v2"
    assert snapshot["finalSource"] == "reset_skeleton"
    assert snapshot["provenance"]["providerInvoked"] is False
    assert snapshot["provenance"]["externalInvoked"] is False
    for field in ("layerMode", "fusionSteps", "layerPlan"):
        assert field not in payload
    assert set(DIMENSION_GROUPS) == {item["id"] for item in snapshot["dimensionGroups"]}
