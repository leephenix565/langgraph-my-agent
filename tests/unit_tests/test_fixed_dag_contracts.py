import hashlib
import json

import react_agent.fixed_dag_contracts as fixed_dag_contracts
from react_agent.context import Context
from react_agent.fixed_dag import constants as fixed_dag_constants
from react_agent.fixed_dag import labels as fixed_dag_labels
from react_agent.fixed_dag import safety as fixed_dag_safety
from react_agent.fixed_dag import types as fixed_dag_types
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
    build_agent_task,
    build_agent_tasks_for_plan,
    build_data_bundle,
    build_decision_result,
    build_default_dimension_route_intent,
    build_default_fixed_dag_plan,
    build_default_route_intent,
    build_dimension_results,
    build_entity_relation_bundle,
    build_l2_conclusions,
    build_pending_conclusion,
    build_report_input_bundle,
    build_report_result,
    build_risk_composite,
    build_route_intent,
    build_selected_fixed_dag_plan,
    build_workflow_snapshot_v2,
    compile_selected_fixed_dag_plan,
    normalize_fixed_dag_plan,
    validate_agent_task,
    validate_conclusion_object,
    validate_data_bundle,
    validate_decision_result,
    validate_dimension_composite_result,
    validate_entity_relation_bundle,
    validate_fixed_dag_plan,
    validate_report_input_bundle,
    validate_report_result,
    validate_route_intent,
    validate_selected_fixed_dag_plan,
    validate_workflow_snapshot_v2,
)
from react_agent.fixed_dag_executor import execute_fixed_dag_plan
from react_agent.public_mapping import build_workflow_snapshot


def _canonical_hash(value) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode()).hexdigest()


def _contains_key(value, key: str) -> bool:
    if isinstance(value, dict):
        return key in value or any(_contains_key(item, key) for item in value.values())
    if isinstance(value, list):
        return any(_contains_key(item, key) for item in value)
    return False


def test_fixed_dag_contract_facade_exports_foundational_symbols() -> None:
    assert fixed_dag_contracts.__all__ == sorted(fixed_dag_contracts.__all__)
    for name in (
        "FIXED_DAG_SCHEMA_VERSION",
        "RESET_RUNTIME_AGENT_IDS",
        "DIMENSION_GROUPS",
        "FixedDagPlan",
        "RouteIntent",
        "AGENT_TITLE_LABELS",
        "DIMENSION_TITLE_LABELS",
        "build_default_fixed_dag_plan",
        "compile_selected_fixed_dag_plan",
    ):
        assert name in fixed_dag_contracts.__all__

    assert fixed_dag_contracts.FIXED_DAG_SCHEMA_VERSION is fixed_dag_constants.FIXED_DAG_SCHEMA_VERSION
    assert fixed_dag_contracts.RESET_RUNTIME_AGENT_IDS is fixed_dag_constants.RESET_RUNTIME_AGENT_IDS
    assert fixed_dag_contracts.DIMENSION_GROUPS is fixed_dag_constants.DIMENSION_GROUPS
    assert fixed_dag_contracts.FixedDagPlan is fixed_dag_types.FixedDagPlan
    assert fixed_dag_contracts.RouteIntent is fixed_dag_types.RouteIntent
    assert fixed_dag_contracts.AGENT_TITLE_LABELS is fixed_dag_labels.AGENT_TITLE_LABELS
    assert fixed_dag_contracts._contains_legacy_key is fixed_dag_safety._contains_legacy_key


def test_fixed_dag_foundational_extraction_keeps_canonical_outputs() -> None:
    plan = build_default_fixed_dag_plan("M2B deterministic question", as_of="2026-06-26")
    intent = build_default_route_intent("Should I invest in example company?")
    selected = compile_selected_fixed_dag_plan(
        intent,
        user_text="Should I invest in example company?",
        as_of="2026-06-26",
    )
    execution = execute_fixed_dag_plan(
        plan,
        question="M2B deterministic question",
        as_of="2026-06-26",
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
    ).model_dump(mode="json", by_alias=True)

    assert _canonical_hash(plan) == "52d71147ec4a7cd71933d8f3375905a7d9d22367e470762e594befe0e54048bd"
    assert _canonical_hash(selected) == "8ee97bad6224c9b34bd61b8b75cbff42f5257b3f6bf2dd07039ecab49a465cbf"
    assert _canonical_hash(workflow) == "50048210629b5cef75c7a26bc3f34ecbc3c157a12d9a19e271a6160561c259ee"


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


def test_fixed_dag_plan_has_explicit_dependencies_and_dimensions() -> None:
    plan = build_default_fixed_dag_plan("q", as_of="2026-06-04")
    steps = {step["id"]: step for step in plan["steps"]}

    assert steps["route_planner"]["depends_on"] == []
    assert steps["route_planner"]["dimension"] == "l1"
    assert steps["entity_relation_extractor"]["depends_on"] == ["route_planner"]
    assert steps["financial_data_service"]["depends_on"] == ["route_planner"]
    for agent_id in L2_CONCLUSION_AGENT_IDS:
        assert steps[f"l2:{agent_id}"]["depends_on"] == [
            "financial_data_service",
            "entity_relation_extractor",
        ]
    for dimension, agent_ids in DIMENSION_GROUPS.items():
        assert set(steps[f"dimension:{dimension}"]["depends_on"]) == {
            f"l2:{agent_id}" for agent_id in agent_ids
        }
    assert set(steps["decision_synthesizer"]["depends_on"]) == {
        "dimension:value",
        "dimension:market",
        "dimension:risk",
        "dimension:macro",
    }
    assert steps["report_generator"]["depends_on"] == ["decision_synthesizer"]


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


def _selected_value_risk_steps():
    full = build_default_fixed_dag_plan("selected q", as_of="2026-06-09")
    keep = {
        "route_planner",
        "financial_data_service",
        "entity_relation_extractor",
        "l2:value_traditional_valuation",
        "l2:risk_identification",
        "dimension:value",
        "dimension:risk",
        "decision_synthesizer",
        "report_generator",
    }
    return [
        {
            **step,
            "depends_on": [dep for dep in step.get("depends_on", []) if dep in keep],
            **(
                {
                    "target_ids": [
                        target_id
                        for target_id in step.get("target_ids", [])
                        if target_id in {"value_traditional_valuation", "risk_identification"}
                    ]
                }
                if step.get("target_ids")
                else {}
            ),
        }
        for step in full["steps"]
        if step["id"] in keep
    ]


def _valid_selected_value_risk_intent():
    return build_route_intent(
        task_type="single",
        targets=["示例公司"],
        selected_dimensions=["value", "risk"],
        selected_agents=[
            "route_planner",
            "financial_data_service",
            "entity_relation_extractor",
            "value_traditional_valuation",
            "risk_identification",
            "value_composite",
            "risk_composite",
            "decision_synthesizer",
            "report_generator",
        ],
        task_brief_by_agent={
            "value_traditional_valuation": "整理估值相关线索。",
            "risk_identification": "识别需要保留的风险约束。",
            "report_generator": "输出公开回答。",
        },
        route_confidence=0.82,
        fallback_reason="selected routing can fall back to full DAG if validation fails.",
    )


def _selected_value_only_steps():
    full = build_default_fixed_dag_plan("selected q", as_of="2026-06-09")
    keep = {
        "route_planner",
        "l2:value_traditional_valuation",
        "dimension:value",
        "report_generator",
    }
    return [
        {
            **step,
            "depends_on": [dep for dep in step.get("depends_on", []) if dep in keep],
            **(
                {
                    "target_ids": [
                        target_id
                        for target_id in step.get("target_ids", [])
                        if target_id == "value_traditional_valuation"
                    ]
                }
                if step.get("target_ids")
                else {}
            ),
        }
        for step in full["steps"]
        if step["id"] in keep
    ]


def test_route_intent_validates_selected_dimensions_and_agents() -> None:
    intent = _valid_selected_value_risk_intent()
    valid, reason = validate_route_intent(intent)

    assert valid, reason
    assert intent["schema"] == "route_intent_v1"
    assert intent["selected_dimensions"] == ["value", "risk"]
    assert "report_generator" in intent["selected_agents"]
    assert "decision_synthesizer" in intent["selected_agents"]
    assert "risk" in intent["selected_dimensions"]
    assert intent["route_confidence"] == 0.82
    assert not _contains_key(intent, "layerMode")


def test_default_route_intent_is_provider_free_and_valid() -> None:
    intent = build_default_route_intent("Should I invest in example company?")
    valid, reason = validate_route_intent(intent)

    assert valid, reason
    assert intent["schema"] == "route_intent_v1"
    assert intent["task_type"] == "single"
    assert intent["selected_dimensions"] == ["value", "risk"]
    assert intent["selected_agents"] == ["value_research_synthesis", "risk_identification"]
    assert intent["fallback_reason"] == "fallback to full DAG"
    assert intent["provenance"]["provider_invoked"] is False
    assert intent["provenance"]["external_invoked"] is False


def test_default_route_intent_handles_non_investment_tasks_without_risk() -> None:
    macro = build_default_route_intent("Explain macro inflation and index pressure.")
    sentiment = build_default_route_intent("Summarize public sentiment about example company.")
    general = build_default_route_intent("Explain accounting terminology.")

    assert macro["task_type"] == "macro"
    assert macro["selected_dimensions"] == ["macro"]
    assert macro["selected_agents"] == ["macro_analysis"]
    assert sentiment["task_type"] == "sentiment"
    assert sentiment["selected_dimensions"] == ["market"]
    assert sentiment["selected_agents"] == ["sentiment_company_radar"]
    assert general["task_type"] == "general"
    assert general["selected_dimensions"] == ["value"]
    assert "risk" not in general["selected_dimensions"]


def test_default_dimension_route_intent_is_provider_free_and_dimension_only() -> None:
    intent = build_default_dimension_route_intent("Should I invest in example company?")
    valid, reason = validate_route_intent(intent)

    assert valid, reason
    assert intent["task_type"] == "single"
    assert intent["selected_dimensions"] == ["value", "risk"]
    assert intent["selected_agents"] == []
    assert intent["fallback_reason"] == ""
    assert intent["provenance"]["route_granularity"] == "dimension"
    assert intent["provenance"]["provider_invoked"] is False
    assert intent["provenance"]["external_invoked"] is False


def test_route_intent_allows_dimension_only_with_dimension_provenance() -> None:
    intent = build_route_intent(
        task_type="general",
        targets=["估值方法说明"],
        selected_dimensions=["value"],
        selected_agents=[],
        route_confidence=0.74,
        provenance={"route_granularity": "dimension"},
    )
    valid, reason = validate_route_intent(intent)

    assert valid, reason
    assert intent["selected_dimensions"] == ["value"]
    assert intent["selected_agents"] == []


def test_route_intent_allows_general_value_only_selection() -> None:
    intent = build_route_intent(
        task_type="general",
        targets=["估值方法说明"],
        selected_dimensions=["value"],
        selected_agents=["route_planner", "value_traditional_valuation", "value_composite", "report_generator"],
        route_confidence=0.7,
        fallback_reason="fallback to full DAG",
    )
    valid, reason = validate_route_intent(intent)

    assert valid, reason
    assert intent["selected_dimensions"] == ["value"]
    assert "risk" not in intent["selected_dimensions"]
    assert "decision_synthesizer" not in intent["selected_agents"]


def test_route_intent_rejects_invalid_agents_and_legacy_dispatch() -> None:
    unknown = build_route_intent(
        task_type="general",
        selected_dimensions=["value"],
        selected_agents=["not_a_reset_agent"],
        fallback_reason="fallback to full DAG",
    )
    unknown["selected_agents"] = ["not_a_reset_agent"]
    valid, reason = validate_route_intent(unknown)
    assert not valid
    assert reason == "unknown_selected_agent"

    legacy = build_route_intent(
        task_type="general",
        selected_dimensions=["value"],
        selected_agents=["a16_ml_valuation"],
        fallback_reason="fallback to full DAG",
    )
    legacy["selected_agents"] = ["a16_ml_valuation"]
    valid, reason = validate_route_intent(legacy)
    assert not valid
    assert reason == "legacy_agent_id_present"

    removed = build_route_intent(
        task_type="general",
        selected_dimensions=["value"],
        selected_agents=["value_financial_analysis"],
        fallback_reason="fallback to full DAG",
    )
    removed["selected_agents"] = ["value_financial_analysis"]
    valid, reason = validate_route_intent(removed)
    assert not valid
    assert reason == "removed_agent_present"

    dispatch = _valid_selected_value_risk_intent()
    dispatch["provenance"]["mode"] = "Star"
    valid, reason = validate_route_intent(dispatch)
    assert not valid
    assert reason == "legacy_dispatch_field_present"

    legacy_value = _valid_selected_value_risk_intent()
    legacy_value["fallback_reason"] = "Tree"
    valid, reason = validate_route_intent(legacy_value)
    assert not valid
    assert reason == "legacy_dispatch_value_present"


def test_route_intent_enforces_clarification_and_policy_gates() -> None:
    clarify = build_route_intent(
        task_type="general",
        selected_dimensions=[],
        selected_agents=[],
        route_confidence=0.1,
        needs_clarification=True,
    )
    valid, reason = validate_route_intent(clarify)
    assert not valid
    assert reason == "clarification_question_missing"

    missing_reason = build_route_intent(
        task_type="general",
        selected_dimensions=[],
        selected_agents=[],
    )
    valid, reason = validate_route_intent(missing_reason)
    assert not valid
    assert reason == "fallback_reason_missing"

    missing_risk = build_route_intent(
        task_type="single",
        selected_dimensions=["value"],
        selected_agents=["value_traditional_valuation", "value_composite", "decision_synthesizer", "report_generator"],
        fallback_reason="fallback to full DAG",
    )
    valid, reason = validate_route_intent(missing_risk)
    assert not valid
    assert reason == "risk_dimension_required"

    unsafe_reason = build_route_intent(
        task_type="general",
        selected_dimensions=["value"],
        selected_agents=["route_planner", "value_traditional_valuation", "value_composite", "report_generator"],
        fallback_reason="provider default_url",
    )
    valid, reason = validate_route_intent(unsafe_reason)
    assert not valid
    assert reason == "fallback_reason_not_public_safe"

    unsafe_provenance = build_route_intent(
        task_type="general",
        selected_dimensions=["value"],
        selected_agents=[],
        route_confidence=0.74,
        provenance={
            "route_granularity": "dimension",
            "endpoint": "http://127.0.0.1:10028/v1/agent/compute",
        },
    )
    valid, reason = validate_route_intent(unsafe_provenance)
    assert not valid
    assert reason == "route_intent_unsafe_material_present"


def test_route_intent_preserves_sentiment_market_boundary() -> None:
    intent = build_route_intent(
        task_type="sentiment",
        selected_dimensions=["risk"],
        selected_agents=["sentiment_company_radar", "report_generator"],
        fallback_reason="fallback to full DAG",
    )
    intent["selected_agents"] = ["sentiment_company_radar", "report_generator"]
    valid, reason = validate_route_intent(intent)

    assert not valid
    assert reason == "agent_dimension_mismatch"


def test_selected_fixed_dag_plan_allows_general_value_only_subset() -> None:
    intent = build_route_intent(
        task_type="general",
        targets=["估值方法说明"],
        selected_dimensions=["value"],
        selected_agents=["route_planner", "value_traditional_valuation", "value_composite", "report_generator"],
        route_confidence=0.7,
        fallback_reason="fallback to full DAG",
    )
    plan = build_selected_fixed_dag_plan(
        route_intent=intent,
        user_text="selected q",
        selected_steps=_selected_value_only_steps(),
        fallback_reason="fallback to full DAG",
    )
    valid, reason = validate_selected_fixed_dag_plan(plan)

    assert valid, reason
    assert len(plan["steps"]) < len(RESET_RUNTIME_AGENT_IDS)
    assert plan["selected_dimensions"] == ["value"]
    assert set(plan["omitted_dimensions"]) == {"market", "risk", "macro"}
    assert "risk_identification" in plan["omitted_agents"]
    assert "macro_analysis" in plan["omitted_agents"]


def test_compile_selected_fixed_dag_plan_builds_value_only_dependency_closure() -> None:
    intent = build_route_intent(
        task_type="general",
        targets=["valuation method"],
        selected_dimensions=["value"],
        selected_agents=["value_ml_valuation"],
        route_confidence=0.7,
        fallback_reason="fallback to full DAG",
    )
    plan = compile_selected_fixed_dag_plan(
        intent,
        user_text="explain valuation method",
        as_of="2026-06-09",
    )
    steps = {step["id"]: step for step in plan["steps"]}
    selected_valid, selected_reason = validate_selected_fixed_dag_plan(plan)
    full_valid, full_reason = validate_fixed_dag_plan(plan)

    assert selected_valid, selected_reason
    assert not full_valid
    assert full_reason == "invalid_schema"
    assert list(steps) == [
        "route_planner",
        "financial_data_service",
        "entity_relation_extractor",
        "l2:value_ml_valuation",
        "dimension:value",
        "report_generator",
    ]
    assert steps["financial_data_service"]["depends_on"] == ["route_planner"]
    assert steps["entity_relation_extractor"]["depends_on"] == ["route_planner"]
    assert steps["l2:value_ml_valuation"]["depends_on"] == [
        "financial_data_service",
        "entity_relation_extractor",
    ]
    assert steps["dimension:value"]["target_ids"] == ["value_ml_valuation"]
    assert steps["dimension:value"]["depends_on"] == ["l2:value_ml_valuation"]
    assert steps["report_generator"]["depends_on"] == ["dimension:value"]
    assert "decision_synthesizer" not in plan["target_agent_ids"]
    assert set(plan["omitted_dimensions"]) == {"market", "risk", "macro"}
    assert len(plan["steps"]) < len(RESET_RUNTIME_AGENT_IDS)
    assert plan["provenance"]["source"] == "deterministic_selected_dag_compiler"
    assert not _contains_key(plan, "layerMode")
    assert not _contains_key(plan, "fusionSteps")


def test_compile_selected_fixed_dag_plan_expands_dimension_only_value_intent() -> None:
    intent = build_route_intent(
        task_type="general",
        targets=["valuation method"],
        selected_dimensions=["value"],
        selected_agents=[],
        route_confidence=0.74,
        provenance={"route_granularity": "dimension"},
    )
    plan = compile_selected_fixed_dag_plan(
        intent,
        user_text="explain valuation method",
        as_of="2026-06-09",
    )
    steps = {step["id"]: step for step in plan["steps"]}
    selected_valid, selected_reason = validate_selected_fixed_dag_plan(plan)

    assert selected_valid, selected_reason
    assert plan["provenance"]["route_granularity"] == "dimension"
    assert plan["provenance"]["expanded_from_selected_dimensions"] is True
    assert plan["dimension_groups"]["value"] == list(DIMENSION_GROUPS["value"])
    assert set(plan["selected_dimensions"]) == {"value"}
    assert all(agent_id in plan["target_agent_ids"] for agent_id in DIMENSION_GROUPS["value"])
    assert "value_composite" in plan["target_agent_ids"]
    assert "decision_synthesizer" in plan["target_agent_ids"]
    assert "report_generator" in plan["target_agent_ids"]
    assert steps["dimension:value"]["target_ids"] == list(DIMENSION_GROUPS["value"])
    assert steps["dimension:value"]["depends_on"] == [
        f"l2:{agent_id}" for agent_id in DIMENSION_GROUPS["value"]
    ]
    assert steps["decision_synthesizer"]["depends_on"] == ["dimension:value"]
    assert steps["report_generator"]["depends_on"] == ["decision_synthesizer"]
    assert set(plan["omitted_dimensions"]) == {"market", "risk", "macro"}


def test_compile_selected_fixed_dag_plan_expands_dimension_only_risk_macro_intent() -> None:
    intent = build_route_intent(
        task_type="general",
        targets=["risk and macro"],
        selected_dimensions=["risk", "macro"],
        selected_agents=[],
        route_confidence=0.82,
        provenance={"route_granularity": "dimension"},
    )
    plan = compile_selected_fixed_dag_plan(intent, user_text="risk and macro")
    steps = {step["id"]: step for step in plan["steps"]}
    selected_valid, selected_reason = validate_selected_fixed_dag_plan(plan)

    assert selected_valid, selected_reason
    assert plan["dimension_groups"]["risk"] == list(DIMENSION_GROUPS["risk"])
    assert plan["dimension_groups"]["macro"] == list(DIMENSION_GROUPS["macro"])
    assert all(agent_id in plan["target_agent_ids"] for agent_id in DIMENSION_GROUPS["risk"])
    assert all(agent_id in plan["target_agent_ids"] for agent_id in DIMENSION_GROUPS["macro"])
    assert "risk_composite" in plan["target_agent_ids"]
    assert "macro_composite" in plan["target_agent_ids"]
    assert "decision_synthesizer" in plan["target_agent_ids"]
    assert set(steps["decision_synthesizer"]["depends_on"]) == {
        "dimension:risk",
        "dimension:macro",
    }
    assert steps["report_generator"]["depends_on"] == ["decision_synthesizer"]
    assert set(plan["omitted_dimensions"]) == {"value", "market"}


def test_compile_selected_fixed_dag_plan_builds_investment_plan_with_risk_and_decision() -> None:
    intent = build_route_intent(
        task_type="single",
        targets=["example company"],
        selected_dimensions=["value", "risk"],
        selected_agents=["value_traditional_valuation", "risk_identification"],
        route_confidence=0.78,
        fallback_reason="fallback to full DAG",
    )
    plan = compile_selected_fixed_dag_plan(
        intent,
        user_text="evaluate example company",
        as_of="2026-06-09",
    )
    steps = {step["id"]: step for step in plan["steps"]}
    selected_valid, selected_reason = validate_selected_fixed_dag_plan(plan)

    assert selected_valid, selected_reason
    assert set(plan["selected_dimensions"]) == {"value", "risk"}
    assert set(plan["dimension_groups"]) == {"value", "risk"}
    assert plan["dimension_groups"]["value"] == ["value_traditional_valuation"]
    assert plan["dimension_groups"]["risk"] == ["risk_identification"]
    assert steps["dimension:value"]["depends_on"] == ["l2:value_traditional_valuation"]
    assert steps["dimension:risk"]["depends_on"] == ["l2:risk_identification"]
    assert set(steps["decision_synthesizer"]["depends_on"]) == {
        "dimension:value",
        "dimension:risk",
    }
    assert steps["report_generator"]["depends_on"] == ["decision_synthesizer"]
    assert "market_composite" not in plan["target_agent_ids"]
    assert "macro_composite" not in plan["target_agent_ids"]


def test_compile_selected_fixed_dag_plan_rejects_invalid_or_incomplete_intent() -> None:
    missing_risk = build_route_intent(
        task_type="single",
        targets=["example company"],
        selected_dimensions=["value"],
        selected_agents=["value_traditional_valuation"],
        fallback_reason="fallback to full DAG",
    )
    try:
        compile_selected_fixed_dag_plan(missing_risk)
    except ValueError as exc:
        assert str(exc) == "invalid_route_intent:risk_dimension_required"
    else:
        raise AssertionError("expected invalid investment intent to fail")

    missing_dimensions = build_route_intent(
        task_type="general",
        selected_dimensions=[],
        selected_agents=[],
        fallback_reason="fallback to full DAG",
    )
    try:
        compile_selected_fixed_dag_plan(missing_dimensions)
    except ValueError as exc:
        assert str(exc) == "selected_dimensions_missing"
    else:
        raise AssertionError("expected missing selected dimensions to fail")

    dimension_only_with_non_l2_agent = build_route_intent(
        task_type="general",
        selected_dimensions=["value"],
        selected_agents=["value_composite"],
        fallback_reason="fallback to full DAG",
    )
    plan = compile_selected_fixed_dag_plan(dimension_only_with_non_l2_agent)
    assert plan["dimension_groups"]["value"] == list(DIMENSION_GROUPS["value"])


def test_selected_fixed_dag_plan_validates_subset_and_omissions() -> None:
    intent = _valid_selected_value_risk_intent()
    plan = build_selected_fixed_dag_plan(
        route_intent=intent,
        user_text="selected q",
        as_of="2026-06-09",
        selected_steps=_selected_value_risk_steps(),
        fallback_reason="fallback to full DAG",
    )
    selected_valid, selected_reason = validate_selected_fixed_dag_plan(plan)
    full_valid, full_reason = validate_fixed_dag_plan(plan)

    assert selected_valid, selected_reason
    assert not full_valid
    assert full_reason == "invalid_schema"
    assert plan["schema"] == "selected_fixed_dag_plan_v1"
    assert len(plan["steps"]) < len(RESET_RUNTIME_AGENT_IDS)
    assert set(plan["selected_dimensions"]) == {"value", "risk"}
    assert set(plan["omitted_dimensions"]) == {"market", "macro"}
    assert "market_stock_technical" in plan["omitted_agents"]
    assert "macro_analysis" in plan["omitted_agents"]
    assert "report_generator" in plan["target_agent_ids"]
    assert "decision_synthesizer" in plan["target_agent_ids"]
    assert plan["fallback_to"] == "full_dag"
    assert plan["fallback_reason"] == "fallback to full DAG"
    assert not _contains_key(plan, "layerMode")
    assert not _contains_key(plan, "fusionSteps")


def test_selected_fixed_dag_plan_rejects_runtime_fields_and_bad_omissions() -> None:
    intent = _valid_selected_value_risk_intent()
    plan = build_selected_fixed_dag_plan(
        route_intent=intent,
        user_text="selected q",
        selected_steps=_selected_value_risk_steps(),
        fallback_reason="fallback to full DAG",
    )
    plan["steps"][0]["runtime_kind"] = "external_http_candidate"
    valid, reason = validate_selected_fixed_dag_plan(plan)
    assert not valid
    assert reason == "runtime_binding_field_present"

    plan = build_selected_fixed_dag_plan(
        route_intent=intent,
        user_text="selected q",
        selected_steps=_selected_value_risk_steps(),
        fallback_reason="fallback to full DAG",
    )
    plan["omitted_dimensions"] = ["market"]
    valid, reason = validate_selected_fixed_dag_plan(plan)
    assert not valid
    assert reason == "omitted_dimensions_mismatch"

    plan = build_selected_fixed_dag_plan(
        route_intent=intent,
        user_text="selected q",
        selected_steps=_selected_value_risk_steps(),
        fallback_reason="provider default_url",
    )
    valid, reason = validate_selected_fixed_dag_plan(plan)
    assert not valid
    assert reason == "fallback_reason_not_public_safe"


def test_selected_fixed_dag_plan_rejects_sentiment_to_risk_dependency() -> None:
    intent = build_route_intent(
        task_type="single",
        targets=["示例公司"],
        selected_dimensions=["market", "risk"],
        selected_agents=[
            "route_planner",
            "financial_data_service",
            "entity_relation_extractor",
            "sentiment_company_radar",
            "risk_identification",
            "market_composite",
            "risk_composite",
            "decision_synthesizer",
            "report_generator",
        ],
        route_confidence=0.7,
        fallback_reason="fallback to full DAG",
    )
    full = build_default_fixed_dag_plan("selected q")
    keep = {
        "route_planner",
        "financial_data_service",
        "entity_relation_extractor",
        "l2:sentiment_company_radar",
        "l2:risk_identification",
        "dimension:market",
        "dimension:risk",
        "decision_synthesizer",
        "report_generator",
    }
    steps = []
    for step in full["steps"]:
        if step["id"] not in keep:
            continue
        item = {**step, "depends_on": [dep for dep in step.get("depends_on", []) if dep in keep]}
        if item["id"] == "dimension:risk":
            item["depends_on"].append("l2:sentiment_company_radar")
        if item.get("target_ids"):
            item["target_ids"] = [
                target for target in item["target_ids"] if target in {"sentiment_company_radar", "risk_identification"}
            ]
        steps.append(item)
    plan = build_selected_fixed_dag_plan(
        route_intent=intent,
        selected_steps=steps,
        fallback_reason="fallback to full DAG",
    )
    valid, reason = validate_selected_fixed_dag_plan(plan)

    assert not valid
    assert reason == "risk_reads_sentiment"


def test_l1_bundles_are_deterministic_and_keep_as_of_boundary() -> None:
    plan = build_default_fixed_dag_plan("question", as_of="2026-06-04")
    data_bundle = build_data_bundle(plan)
    entity_bundle = build_entity_relation_bundle(plan)

    for bundle in (data_bundle, entity_bundle):
        assert bundle["status"] == "pending_implementation"
        assert bundle["as_of"] == "2026-06-04"
        assert bundle["data_as_of"] <= bundle["as_of"]
        assert "本地固定流程模式" in " ".join(bundle["notes"])
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
    market_members = {
        item["agent_id"]
        for item in results["market"]["provenance"]["member_weight_summary"]
    }

    assert set(results) == set(DIMENSION_GROUPS)
    assert "sentiment_company_radar" in market_members
    assert "sentiment_company_radar" not in results["market"]["contributing_agents"]
    assert "sentiment_company_radar" not in results["risk"]["contributing_agents"]
    assert {"gate", "veto", "penalty", "risk_score"} <= set(results["risk"])
    assert {"regime", "dimension_weights", "risk_sensitivity"} <= set(results["macro"])
    assert set(results["macro"]["dimension_weights"]) == {"value", "market"}
    for item in results.values():
        valid, reason = validate_dimension_composite_result(item)
        assert valid, reason


def test_dimension_composite_validator_accepts_selected_subset_contributors() -> None:
    item = {
        "schema": "dimension_composite_result_v1",
        "schema_version": "dimension_composite_result_v1",
        "agent_id": "value_composite",
        "dimension": "value",
        "stance": "0.12",
        "confidence": 0.7,
        "status": "complete",
        "contributing_agents": ["value_ml_valuation", "value_research_synthesis"],
        "evidence_refs": ["bounded-evidence"],
        "as_of": "2026-06-05",
        "data_as_of": "2026-06-05",
        "vote_type": "weighted_member_vote",
        "provenance": {
            "source": "fixed_dag_external_adapter",
            "provider_invoked": False,
            "external_invoked": False,
        },
    }

    valid, reason = validate_dimension_composite_result(item)

    assert valid, reason


def test_macro_composite_validator_rejects_legacy_four_weight_shape() -> None:
    results = build_dimension_results({}, as_of="2026-06-04")
    macro = dict(results["macro"])
    macro["dimension_weights"] = {
        "value": 0.35,
        "market": 0.25,
        "risk": 0.25,
        "macro": 0.15,
    }

    valid, reason = validate_dimension_composite_result(macro)

    assert not valid
    assert reason == "dimension_weights_keys_mismatch"


def test_risk_composite_ignores_sentiment_even_if_present_in_input() -> None:
    conclusions = build_l2_conclusions(
        build_default_fixed_dag_plan("q", as_of="2026-06-04")
    )
    risk = build_risk_composite(conclusions, as_of="2026-06-04")

    assert risk["contributing_agents"] == []
    assert "sentiment_company_radar" not in risk["contributing_agents"]


def test_l3_composites_project_partial_research_material_from_available_l2() -> None:
    conclusions = build_l2_conclusions(
        build_default_fixed_dag_plan("请分析 600519.SH", as_of="2026-06-04")
    )
    conclusions["value_traditional_valuation"].update(
        {
            "status": "complete",
            "stance": "1",
            "confidence": 0.8,
            "evidence": [
                {
                    "id": "value-real",
                    "fact": "传统估值给出正向估值线索。",
                    "source": "unit_test",
                }
            ],
            "provenance": {
                **conclusions["value_traditional_valuation"]["provenance"],
                "research_points": [
                    {
                        "claim": "估值显著低于合理价值中枢。",
                        "support": "PE 法给出正向估值线索。",
                    }
                ],
            },
        }
    )
    conclusions["market_stock_technical"].update(
        {
            "status": "complete",
            "stance": "0.54",
            "confidence": 0.54,
            "evidence": [
                {
                    "id": "market-real",
                    "fact": "三模型投票偏上涨。",
                    "source": "unit_test",
                }
            ],
        }
    )
    conclusions["risk_compliance_review"].update(
        {
            "status": "complete",
            "stance": "risk_gate_member",
            "confidence": 0.75,
            "evidence": [
                {
                    "id": "risk-real",
                    "fact": "合规评分未触发风险否决。",
                    "source": "unit_test",
                }
            ],
            "provenance": {
                **conclusions["risk_compliance_review"]["provenance"],
                "risk_score": 0.18,
                "domain_metrics": {
                    "model_vintage_boundary": {
                        "feature_data_anti_lookahead_passed": True,
                        "production_model_trained_through_feature_year": 2024,
                        "as_of_market_feature_year": 2023,
                        "model_vintage_caveat": True,
                        "interpretation": "特征按 as_of 截断；这是历史 as_of 使用当前生产模型版本的 caveat。",
                    }
                },
                "data_quality": {
                    "warnings": [
                        "模型版本边界:历史 as_of 使用当前生产模型版本,不表示输入特征晚于 as_of。"
                    ]
                },
            },
        }
    )

    results = build_dimension_results(conclusions, as_of="2026-06-04")
    value = results["value"]
    market = results["market"]
    risk = results["risk"]
    macro = results["macro"]
    value_provenance = value["provenance"]
    risk_provenance = risk["provenance"]

    assert value["status"] == "partial"
    assert value["stance"] == "positive"
    assert value["confidence"] == 0.2
    assert value["evidence_refs"]
    assert value_provenance["domain_metrics"]["coverage"] == 0.25
    assert value_provenance["domain_metrics"]["weighted_stance_score"] == 1.0
    assert value_provenance["research_points"][0]["caveat"].endswith("真实 evidence。")
    assert any(
        item["agent_id"] == "value_traditional_valuation" and item["weight"] == 1.0
        for item in value_provenance["member_weight_summary"]
    )
    assert market["status"] == "partial"
    assert market["stance"] == "positive"
    assert risk["status"] == "partial"
    assert risk["gate"] == "pass"
    assert risk["risk_score"] == 0.18
    assert risk["veto"] is False
    assert "sentiment_company_radar" not in risk["contributing_agents"]
    assert risk_provenance["domain_metrics"]["risk_member_count"] == 1
    assert risk_provenance["data_quality"]["coverage"] == 0.25
    boundary_driver = next(
        item for item in risk_provenance["drivers"] if item["name"] == "member_boundary_summary"
    )
    assert boundary_driver["value"][0]["agent_id"] == "risk_compliance_review"
    assert "模型版本边界" in boundary_driver["value"][0]["caveats"][0]
    assert risk_provenance["data_quality"]["member_boundary_summary"] == boundary_driver["value"]
    assert any(
        point["claim"] == "风险门通过不等于成员边界消失。"
        for point in risk_provenance["research_points"]
    )
    assert macro["status"] == "pending_implementation"
    assert macro["regime"] == "not_evaluated"
    assert macro["dimension_weights"] == {"value": 0.5, "market": 0.5}

    decision = build_decision_result(results, as_of="2026-06-04")
    bundle = build_report_input_bundle(
        question="请分析 600519.SH",
        l2_conclusions=conclusions,
        dimension_results=results,
        decision_result=decision,
    )
    report = build_report_result(
        decision,
        question="请分析 600519.SH",
        report_input_bundle=bundle,
    )
    rendered = json.dumps({"bundle": bundle, "report": report}, ensure_ascii=False)

    assert "综合智能体输入" in report["answer"]
    assert "研究判断：判断：价值综合当前为 partial" in report["answer"]
    assert "风险综合当前为 partial，风险门为 pass" in rendered
    assert "raw_response" not in rendered


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
    assert "研判流程" in joined
    assert "分析框架" in report["evidence_cards"][0]["title"]
    assert "高级连接状态可在设置诊断中查看" in joined
    assert "provider verified" not in joined.lower()


def test_report_input_bundle_projects_l2_and_l3_public_summaries() -> None:
    plan = build_default_fixed_dag_plan("请分析 600519.SH", as_of="2026-06-04")
    conclusions = build_l2_conclusions(plan)
    value = conclusions["value_ml_valuation"]
    value["status"] = "complete"
    value["stance"] = "demo_positive"
    value["confidence"] = 0.66
    value["evidence"] = [
        {
            "id": "value-demo",
            "fact": "估值模型给出偏积极信号。",
            "source": "unit_test",
            "raw_response": "must_not_leak",
        }
    ]
    dimensions = build_dimension_results(conclusions, as_of="2026-06-04")
    dimensions["value"].setdefault("provenance", {})["member_weight_summary"] = [
        {
            "agent_id": "value_ml_valuation",
            "weight": 0.7,
            "stance": 0.2,
            "confidence": 0.66,
            "status": "ok",
        },
        {
            "agent_id": "value_research_synthesis",
            "weight": 0.3,
            "stance": 0.0,
            "confidence": 0.3,
            "status": "partial",
        },
    ]
    dimensions["risk"]["gate"] = "manual_review"
    dimensions["risk"]["veto"] = False
    decision = build_decision_result(dimensions, as_of="2026-06-04")
    bundle = build_report_input_bundle(
        question="请分析 600519.SH",
        l2_conclusions=conclusions,
        dimension_results=dimensions,
        decision_result=decision,
    )
    valid, reason = validate_report_input_bundle(bundle)
    report = build_report_result(
        decision,
        question="请分析 600519.SH",
        report_input_bundle=bundle,
    )
    rendered = json.dumps({"bundle": bundle, "report": report}, ensure_ascii=False)

    assert valid, reason
    assert bundle["schema"] == "report_input_bundle_v1"
    assert any(
        item["agent_id"] == "value_ml_valuation"
        for item in bundle["l2_agent_summaries"]
    )
    assert any(
        item["dimension"] == "risk" and item["gate"] == "manual_review"
        for item in bundle["l3_composite_summaries"]
    )
    assert "单体智能体输入" in report["answer"]
    assert "综合智能体输入" in report["answer"]
    assert "机器学习企业估值" in report["answer"]
    assert "未展开无可读证据的 L2" in report["answer"]
    assert "传统企业估值 输出 not_evaluated 信号" not in report["answer"]
    assert "主要成员：机器学习企业估值" in report["answer"]
    assert "L3 输出" in report["answer"]
    assert "raw_response" not in rendered
    assert "must_not_leak" not in rendered


def test_report_projection_does_not_name_pending_l3_members_as_main_contributors() -> None:
    plan = build_default_fixed_dag_plan("请分析 600519.SH", as_of="2026-06-04")
    conclusions = build_l2_conclusions(plan)
    dimensions = build_dimension_results(conclusions, as_of="2026-06-04")
    dimensions["market"].setdefault("provenance", {})["member_weight_summary"] = [
        {
            "agent_id": "market_stock_technical",
            "weight": 1.0,
            "stance": -0.2,
            "confidence": 0.6,
            "status": "complete",
        },
        {
            "agent_id": "sentiment_company_radar",
            "weight": 0.0,
            "stance": 0.0,
            "confidence": 0.0,
            "status": "pending_implementation",
        },
        {
            "agent_id": "market_fund_manager_behavior",
            "weight": 0.0,
            "stance": 0.0,
            "confidence": 0.0,
            "status": "pending_implementation",
        },
    ]
    dimensions["market"]["contributing_agents"] = ["market_stock_technical"]
    decision = build_decision_result(dimensions, as_of="2026-06-04")
    bundle = build_report_input_bundle(
        question="请分析 600519.SH",
        l2_conclusions=conclusions,
        dimension_results=dimensions,
        decision_result=decision,
    )
    report = build_report_result(
        decision,
        question="请分析 600519.SH",
        report_input_bundle=bundle,
    )
    l3_section = next(
        section
        for section in report["sections"]
        if section["id"] == "l3_composite_evidence"
    )

    assert "主要成员：个股技术分析" in l3_section["content"]
    assert "主要成员：企业舆情雷达" not in l3_section["content"]
    assert "主要成员：基金经理行为" not in l3_section["content"]


def test_deterministic_l3_contributing_agents_are_real_contributors_only() -> None:
    plan = build_default_fixed_dag_plan("请分析 600519.SH", as_of="2026-06-04")
    conclusions = build_l2_conclusions(plan)
    conclusions["market_stock_technical"].update(
        {
            "status": "complete",
            "stance": "negative",
            "confidence": 0.6,
            "evidence": [
                {
                    "id": "technical-evidence",
                    "fact": "技术面偏弱。",
                    "source": "unit_test",
                }
            ],
        }
    )
    conclusions["market_fund_manager_behavior"].update(
        {
            "status": "partial",
            "stance": "positive",
            "confidence": 0.32,
            "summary": "LLM 不可用/解析失败(compute_no_llm_deterministic_fallback)，使用确定性替身兜底输出",
            "evidence": [
                {
                    "id": "fund-fallback",
                    "fact": "fallback evidence must not be promoted.",
                    "source": "market_fund_manager_behavior",
                }
            ],
            "provenance": {
                **conclusions["market_fund_manager_behavior"]["provenance"],
                "raw_output_keys": ["degraded", "fallback", "fallback_reason"],
            },
        }
    )

    dimensions = build_dimension_results(conclusions, as_of="2026-06-04")
    valid, reason = validate_dimension_composite_result(dimensions["market"])

    assert valid, reason
    assert dimensions["market"]["contributing_agents"] == ["market_stock_technical"]
    assert "market_fund_manager_behavior" not in dimensions["market"]["contributing_agents"]
    assert all(
        "基金经理行为" not in evidence_ref
        for evidence_ref in dimensions["market"]["evidence_refs"]
    )


def test_deterministic_l3_pending_without_real_contributors_remains_valid() -> None:
    plan = build_default_fixed_dag_plan("请分析 600519.SH", as_of="2026-06-04")
    conclusions = build_l2_conclusions(plan)

    dimensions = build_dimension_results(conclusions, as_of="2026-06-04")
    valid, reason = validate_dimension_composite_result(dimensions["market"])

    assert valid, reason
    assert dimensions["market"]["status"] == "pending_implementation"
    assert dimensions["market"]["contributing_agents"] == []


def test_report_input_bundle_projects_financial_fraud_and_macro_report_material() -> None:
    plan = build_default_fixed_dag_plan("请分析 600519.SH", as_of="2026-06-04")
    conclusions = build_l2_conclusions(plan)
    conclusions["risk_financial_fraud"].update(
        {
            "status": "complete",
            "confidence": 0.73,
            "risk_score": 0.25,
            "evidence": [
                {
                    "fact": "财务造假风险分数为 25/100，闸门 action=pass。",
                    "source": "financial_fraud_risk_gate",
                    "data_as_of": "2024-12-31",
                }
            ],
            "provenance": {
                **conclusions["risk_financial_fraud"]["provenance"],
                "domain_metrics": {
                    "fraud_risk_bridge": {"risk_score": 25, "gate_action": "pass"},
                    "model_context": {"model_available": True, "threshold": 0.5},
                    "feature_diagnostics": {"financial_report_period": "2024"},
                },
                "drivers": [
                    {"name": "fraud_risk_bridge", "value": {"risk_score": 25}},
                    {"name": "risk_gate_rule", "value": {"selected_action": "pass"}},
                ],
                "research_points": [
                    {
                        "claim": "财务造假风险闸门为 pass。",
                        "support": "风险分数 25/100，模型和本地特征均可用。",
                    }
                ],
                "data_quality": {
                    "financial_report_period": "2024",
                    "annual_feature_available_after": "2025-04-30",
                },
            },
        }
    )
    conclusions["macro_analysis"].update(
        {
            "status": "complete",
            "stance": "0.6",
            "confidence": 0.8,
            "evidence": [
                {
                    "fact": "宏观周期=宽货币·宽信用 / 复苏，stance=0.6。",
                    "source": "macro_regime_bridge",
                    "data_as_of": "2024-12-31",
                }
            ],
            "provenance": {
                **conclusions["macro_analysis"]["provenance"],
                "domain_metrics": {
                    "macro_regime_bridge": {"quadrant_label": "宽货币·宽信用", "stance": 0.6},
                    "macro_signal_table": {"growth": {"signal": "up"}},
                    "sector_rotation_summary": {"available": True, "industry_recommend": ["电子"]},
                },
                "drivers": [
                    {"name": "macro_regime_bridge", "value": {"stance": 0.6}},
                    {"name": "macro_signal_table", "value": {"growth": {"signal": "up"}}},
                ],
                "research_points": [
                    {
                        "claim": "宏观周期判断为宽货币·宽信用 / 复苏。",
                        "support": "stance=0.6，行业推荐包含电子。",
                    }
                ],
                "data_quality": {
                    "knowledge_version": "2026-05-27",
                    "release_dates": {"growth": "2024-12-01"},
                },
            },
        }
    )

    dimensions = build_dimension_results(conclusions, as_of="2026-06-04")
    decision = build_decision_result(dimensions, as_of="2026-06-04")
    bundle = build_report_input_bundle(
        question="请分析 600519.SH",
        l2_conclusions=conclusions,
        dimension_results=dimensions,
        decision_result=decision,
    )
    valid, reason = validate_report_input_bundle(bundle)
    report = build_report_result(
        decision,
        question="请分析 600519.SH",
        report_input_bundle=bundle,
    )
    l2_outputs = {
        item["agent_id"]: item
        for item in bundle["agent_evidence_bundle"]["l2_agent_outputs"]
    }
    rendered = json.dumps({"bundle": bundle, "report": report}, ensure_ascii=False)

    assert valid, reason
    assert l2_outputs["risk_financial_fraud"]["domain_metrics"]["fraud_risk_bridge"]["risk_score"] == 25
    assert l2_outputs["risk_financial_fraud"]["research_points"][0]["claim"] == "财务造假风险闸门为 pass。"
    assert l2_outputs["macro_analysis"]["domain_metrics"]["sector_rotation_summary"]["industry_recommend"] == ["电子"]
    assert l2_outputs["macro_analysis"]["research_points"][0]["claim"].startswith("宏观周期判断")
    assert "财务造假风险闸门为 pass" in report["answer"]
    assert "宏观周期判断为宽货币·宽信用 / 复苏" in report["answer"]
    assert "raw_response" not in rendered


def test_report_input_bundle_quality_summary_counts_l3_partial_outputs() -> None:
    plan = build_default_fixed_dag_plan("请分析 600519.SH", as_of="2026-06-04")
    conclusions = build_l2_conclusions(plan)
    dimensions = build_dimension_results(conclusions, as_of="2026-06-04")
    for result in dimensions.values():
        result["status"] = "partial"
    decision = build_decision_result(dimensions, as_of="2026-06-04")
    bundle = build_report_input_bundle(
        question="请分析 600519.SH",
        l2_conclusions=conclusions,
        dimension_results=dimensions,
        decision_result=decision,
    )
    report = build_report_result(
        decision,
        question="请分析 600519.SH",
        report_input_bundle=bundle,
    )
    quality = bundle["agent_evidence_bundle"]["quality_summary"]

    assert quality["l3_total"] == 4
    assert quality["l3_complete"] == 0
    assert quality["l3_partial"] == 4
    assert quality["l3_error"] == 0
    assert quality["l3_available"] == 4
    assert "L3 输出 4/4，complete 0，partial 4，error 0" in report["answer"]


def test_report_input_bundle_records_selected_scope_and_dimension_coverage() -> None:
    plan = build_default_fixed_dag_plan("请分析 600519.SH", as_of="2026-06-04")
    conclusions = build_l2_conclusions(plan)
    dimensions = build_dimension_results(conclusions, as_of="2026-06-04")
    decision = build_decision_result(dimensions, as_of="2026-06-04")
    bundle = build_report_input_bundle(
        question="请分析 600519.SH",
        l2_conclusions=conclusions,
        dimension_results=dimensions,
        decision_result=decision,
        selected_dimensions=["value", "risk"],
    )
    valid, reason = validate_report_input_bundle(bundle)
    evidence_bundle = bundle["agent_evidence_bundle"]

    assert valid, reason
    assert bundle["routing_context"]["routing_mode"] == "selected"
    assert bundle["routing_context"]["selected_dimensions"] == ["value", "risk"]
    assert bundle["routing_context"]["unselected_dimensions"] == ["market", "macro"]
    assert evidence_bundle["selected_scope"] == bundle["routing_context"]
    assert evidence_bundle["coverage_by_dimension"]["value"]["selected"] is True
    assert evidence_bundle["coverage_by_dimension"]["market"]["selected"] is False
    assert evidence_bundle["quality_summary"]["selected_dimension_count"] == 2
    assert evidence_bundle["quality_summary"]["unselected_dimension_count"] == 2


def test_agent_task_v1_carries_l1_and_l2_upstream_context_safely() -> None:
    plan = build_default_fixed_dag_plan("请分析 600519.SH", as_of="2026-06-04")
    data_bundle = build_data_bundle(plan)
    entity_bundle = build_entity_relation_bundle(plan)
    conclusions = build_l2_conclusions(plan)
    conclusions["value_ml_valuation"]["status"] = "complete"
    conclusions["value_ml_valuation"]["stance"] = "slightly_positive"
    conclusions["value_ml_valuation"]["evidence"] = [
        {
            "fact": "ML 估值给出偏正面信号。",
            "source": "unit_test",
            "data_as_of": "2026-06-04",
        }
    ]
    conclusions["value_ml_valuation"]["provenance"] = {
        **conclusions["value_ml_valuation"]["provenance"],
        "domain_metrics": {
            "valuation_bridge": {"fair_value_center": 1650.0, "upside_pct": 18.0},
        },
        "drivers": [
            {"name": "valuation_bridge", "value": {"fair_value_center": 1650.0}},
        ],
        "research_points": [
            {
                "claim": "ML 估值与研报目标价方向一致。",
                "support": "合理价值中枢高于当前价格。",
            }
        ],
        "data_quality": {
            "financial_report_period": "20240930",
        },
    }
    dimensions = build_dimension_results(conclusions, as_of="2026-06-04")

    l2_task = build_agent_task(
        "value_ml_valuation",
        question="请分析 600519.SH",
        as_of="2026-06-04",
        data_bundle={**data_bundle, "raw_response": "must_not_leak"},
        entity_relation_bundle=entity_bundle,
    )
    l3_task = build_agent_task(
        "value_composite",
        question="请分析 600519.SH",
        as_of="2026-06-04",
        data_bundle=data_bundle,
        entity_relation_bundle=entity_bundle,
        l2_conclusions=conclusions,
        dimension_results=dimensions,
    )

    valid_l2, reason_l2 = validate_agent_task(l2_task)
    valid_l3, reason_l3 = validate_agent_task(l3_task)
    rendered = json.dumps({"l2": l2_task, "l3": l3_task}, ensure_ascii=False)

    assert valid_l2, reason_l2
    assert valid_l3, reason_l3
    assert l2_task["required_output_schema"] == "agent_conclusion_v1"
    assert l2_task["data_bundle"]["schema"] == "data_bundle_v1"
    assert l2_task["entity_relation_bundle"]["schema"] == "entity_relation_bundle_v1"
    assert "机器学习企业估值智能体" in l2_task["task_instruction"]
    assert l3_task["required_output_schema"] == "dimension_conclusion_v1"
    assert "value_ml_valuation" in l3_task["upstream_results"]
    ml_upstream = l3_task["upstream_results"]["value_ml_valuation"]
    assert ml_upstream["evidence_items"][0]["fact"] == "ML 估值给出偏正面信号。"
    assert ml_upstream["domain_metrics"]["valuation_bridge"]["fair_value_center"] == 1650.0
    assert ml_upstream["drivers"][0]["name"] == "valuation_bridge"
    assert ml_upstream["research_points"][0]["claim"] == "ML 估值与研报目标价方向一致。"
    assert ml_upstream["data_quality"]["financial_report_period"] == "20240930"
    assert "raw_response" not in rendered
    assert "must_not_leak" not in rendered


def test_report_input_bundle_includes_agent_task_summaries() -> None:
    plan = build_default_fixed_dag_plan("请分析 600519.SH", as_of="2026-06-04")
    data_bundle = build_data_bundle(plan)
    entity_bundle = build_entity_relation_bundle(plan)
    conclusions = build_l2_conclusions(plan)
    dimensions = build_dimension_results(conclusions, as_of="2026-06-04")
    decision = build_decision_result(dimensions, as_of="2026-06-04")
    tasks = build_agent_tasks_for_plan(
        plan,
        question="请分析 600519.SH",
        as_of="2026-06-04",
        data_bundle=data_bundle,
        entity_relation_bundle=entity_bundle,
        l2_conclusions=conclusions,
        dimension_results=dimensions,
        decision_result=decision,
    )
    bundle = build_report_input_bundle(
        question="请分析 600519.SH",
        l2_conclusions=conclusions,
        dimension_results=dimensions,
        decision_result=decision,
        agent_tasks=tasks,
    )
    report = build_report_result(
        decision,
        question="请分析 600519.SH",
        report_input_bundle=bundle,
    )
    rendered = json.dumps(report, ensure_ascii=False)

    assert bundle["agent_task_summaries"]
    assert any(
        item["agent_id"] == "value_ml_valuation"
        and item["has_l1_data_bundle"]
        and item["has_l1_entity_relation_bundle"]
        for item in bundle["agent_task_summaries"]
    )
    assert "智能体任务编排" in rendered
    assert "agent_task_v1" in rendered
    assert "本轮生成 agent_task_v1" in rendered
    assert "你是机器学习企业估值智能体" not in rendered


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


def test_workflow_snapshot_v2_uses_execution_results_when_available() -> None:
    plan = build_default_fixed_dag_plan("q")
    step_results = {
        "route_planner": {
            "schema_version": "fixed_dag_step_result_v1",
            "step_id": "route_planner",
            "agent_id": "route_planner",
            "stage": "planning",
            "dimension": "l1",
            "status": "complete",
            "depends_on": [],
            "output_ref": "fixed_dag_plan",
            "summary": "done",
            "warnings": [],
        },
        "entity_relation_extractor": {
            "schema_version": "fixed_dag_step_result_v1",
            "step_id": "entity_relation_extractor",
            "agent_id": "entity_relation_extractor",
            "stage": "evidence",
            "dimension": "l1",
            "status": "blocked",
            "depends_on": ["route_planner"],
            "output_ref": "",
            "summary": "blocked",
            "warnings": [],
        },
        "financial_data_service": {
            "schema_version": "fixed_dag_step_result_v1",
            "step_id": "financial_data_service",
            "agent_id": "financial_data_service",
            "stage": "evidence",
            "dimension": "l1",
            "status": "pending_implementation",
            "depends_on": ["route_planner"],
            "output_ref": "data_bundle",
            "summary": "pending",
            "warnings": [],
        },
    }
    snapshot = build_workflow_snapshot_v2(
        plan=plan,
        step_results=step_results,
        execution_batches=[["route_planner"], ["financial_data_service", "entity_relation_extractor"]],
        dag_execution={
            "status": "degraded",
            "fallback_used": True,
            "limitations": ["fallback test"],
        },
        current_stage="evidence",
    )
    statuses = {step["id"]: step["status"] for step in snapshot["dagSteps"]}
    valid, reason = validate_workflow_snapshot_v2(snapshot)

    assert valid, reason
    assert statuses["route_planner"] == "complete"
    assert statuses["entity_relation_extractor"] == "blocked"
    assert statuses["financial_data_service"] == "pending_implementation"
    assert snapshot["completedSteps"] == ["route_planner", "financial_data_service"]
    assert snapshot["executionBatches"] == [
        ["route_planner"],
        ["financial_data_service", "entity_relation_extractor"],
    ]
    assert snapshot["stepResults"] == step_results
    assert snapshot["provenance"]["executionStatus"] == "degraded"
    assert snapshot["provenance"]["fallbackUsed"] is True
    assert snapshot["provenance"]["limitations"] == ["fallback test"]


def test_workflow_snapshot_v2_preserves_selected_plan_shape() -> None:
    intent = build_route_intent(
        task_type="general",
        selected_dimensions=["value"],
        selected_agents=["value_ml_valuation"],
        route_confidence=0.7,
        fallback_reason="fallback to full DAG",
    )
    plan = compile_selected_fixed_dag_plan(intent, user_text="q", as_of="2026-06-09")
    snapshot = build_workflow_snapshot_v2(
        plan=plan,
        completed_steps=["route_planner", "financial_data_service"],
        current_stage="evidence",
    )
    valid, reason = validate_workflow_snapshot_v2(snapshot)

    assert valid, reason
    assert snapshot["planId"] == plan["plan_id"]
    assert len(snapshot["dagSteps"]) == len(plan["steps"])
    assert {item["id"] for item in snapshot["dimensionGroups"]} == {"value"}
    assert snapshot["completedSteps"] == ["route_planner", "financial_data_service"]
