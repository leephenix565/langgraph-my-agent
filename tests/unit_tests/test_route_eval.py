import json
from pathlib import Path

from react_agent.fixed_dag_contracts import (
    build_default_route_intent,
    build_route_intent,
)
from react_agent.route_eval import (
    RouteEvalCase,
    evaluate_route_intents,
    load_route_eval_cases,
    route_eval_report_to_dict,
)

FIXTURE_PATH = Path(__file__).resolve().parents[1] / "fixtures" / "route_eval_gold.jsonl"


def test_load_route_eval_fixture() -> None:
    cases = load_route_eval_cases(FIXTURE_PATH)

    assert len(cases) == 12
    assert cases[0].id == "route-001"
    assert cases[0].gold_task_type == "single"
    assert "risk" in cases[0].gold_dimensions
    assert "sentiment_company_radar" in cases[9].must_not_agents


def test_route_eval_scores_perfect_handcrafted_prediction() -> None:
    cases = [
        RouteEvalCase(
            id="perfect",
            query="Should I invest in ExampleCo?",
            gold_task_type="single",
            gold_targets=("ExampleCo",),
            gold_dimensions=("value", "risk"),
            gold_agents=("value_research_synthesis", "risk_identification"),
            gold_needs_clarification=False,
        )
    ]

    def planner(_: str):
        return build_route_intent(
            task_type="single",
            targets=["ExampleCo"],
            selected_dimensions=["value", "risk"],
            selected_agents=["value_research_synthesis", "risk_identification"],
            route_confidence=0.9,
            fallback_reason="fallback to full DAG",
        )

    report = evaluate_route_intents(cases, planner)

    assert report.task_type_accuracy == 1.0
    assert report.target_exact_or_partial_match == 1.0
    assert report.dimension_f1 == 1.0
    assert report.agent_f1 == 1.0
    assert report.over_selection_count == 0
    assert report.under_selection_count == 0
    assert route_eval_report_to_dict(report)["case_count"] == 1


def test_route_eval_counts_false_positive_and_false_negative_behavior() -> None:
    cases = [
        RouteEvalCase(
            id="mixed",
            query="Should I invest in ExampleCo?",
            gold_task_type="single",
            gold_targets=("ExampleCo",),
            gold_dimensions=("value", "risk"),
            gold_agents=("value_research_synthesis", "risk_identification"),
            gold_needs_clarification=False,
        )
    ]

    def planner(_: str):
        return build_route_intent(
            task_type="single",
            targets=["ExampleCo"],
            selected_dimensions=["value", "risk", "macro"],
            selected_agents=[
                "value_research_synthesis",
                "risk_identification",
                "macro_analysis",
            ],
            route_confidence=0.8,
            fallback_reason="fallback to full DAG",
        )

    report = evaluate_route_intents(cases, planner)

    assert report.dimension_precision == 2 / 3
    assert report.dimension_recall == 1.0
    assert report.agent_precision == 2 / 3
    assert report.agent_recall == 1.0
    assert report.over_selection_count == 2
    assert report.under_selection_count == 0


def test_acceptable_extra_agents_are_not_false_positive() -> None:
    cases = [
        RouteEvalCase(
            id="extra-ok",
            query="Screen stocks.",
            gold_task_type="screen",
            gold_targets=(),
            gold_dimensions=("value", "risk"),
            gold_agents=("value_research_synthesis", "risk_identification"),
            gold_needs_clarification=False,
            acceptable_extra_agents=("market_stock_technical",),
        )
    ]

    def planner(_: str):
        return build_route_intent(
            task_type="screen",
            selected_dimensions=["value", "risk"],
            selected_agents=[
                "value_research_synthesis",
                "risk_identification",
                "market_stock_technical",
            ],
            route_confidence=0.8,
            fallback_reason="fallback to full DAG",
        )

    report = evaluate_route_intents(cases, planner)

    assert report.agent_precision == 1.0
    assert report.over_selection_count == 0


def test_must_not_agents_are_counted_as_false_positive() -> None:
    cases = [
        RouteEvalCase(
            id="must-not",
            query="Sentiment scan only.",
            gold_task_type="sentiment",
            gold_targets=(),
            gold_dimensions=("market",),
            gold_agents=("sentiment_company_radar",),
            gold_needs_clarification=False,
            must_not_agents=("risk_identification",),
        )
    ]

    def planner(_: str):
        return build_route_intent(
            task_type="sentiment",
            selected_dimensions=["market", "risk"],
            selected_agents=["sentiment_company_radar", "risk_identification"],
            route_confidence=0.7,
            fallback_reason="fallback to full DAG",
        )

    report = evaluate_route_intents(cases, planner)

    assert report.agent_precision == 0.5
    assert report.over_selection_count == 2
    assert report.cases[0]["agent"]["false_positive_items"] == ["risk_identification"]


def test_deterministic_planner_can_be_evaluated_provider_free() -> None:
    cases = load_route_eval_cases(FIXTURE_PATH)
    report = evaluate_route_intents(cases, build_default_route_intent)
    payload = route_eval_report_to_dict(report)
    rendered = json.dumps(payload, ensure_ascii=False)

    assert report.case_count == 12
    assert 0.0 <= report.task_type_accuracy <= 1.0
    assert 0.0 <= report.dimension_f1 <= 1.0
    assert 0.0 <= report.agent_f1 <= 1.0
    assert "Star" not in rendered
    assert "Chain" not in rendered
    assert "Debate" not in rendered
    assert "Tree" not in rendered


def test_route_eval_does_not_evaluate_legacy_mode_fields() -> None:
    case = RouteEvalCase(
        id="legacy-ignored",
        query="Should I invest in ExampleCo?",
        gold_task_type="single",
        gold_targets=(),
        gold_dimensions=("value", "risk"),
        gold_agents=("value_research_synthesis", "risk_identification"),
        gold_needs_clarification=False,
    )

    def planner(_: str):
        intent = build_route_intent(
            task_type="single",
            selected_dimensions=["value", "risk"],
            selected_agents=["value_research_synthesis", "risk_identification"],
            route_confidence=0.8,
            fallback_reason="fallback to full DAG",
        )
        return {**intent, "mode": "Star", "layerMode": "Chain"}

    report = evaluate_route_intents([case], planner)
    payload = route_eval_report_to_dict(report)

    assert "mode_accuracy" not in payload
    assert "layerMode" not in json.dumps(payload)
    assert report.agent_f1 == 1.0


def test_sentiment_to_risk_mistake_is_penalized() -> None:
    case = RouteEvalCase(
        id="sentiment-risk",
        query="Sentiment scan.",
        gold_task_type="sentiment",
        gold_targets=(),
        gold_dimensions=("market",),
        gold_agents=("sentiment_company_radar",),
        gold_needs_clarification=False,
        must_not_agents=("risk_identification",),
    )

    def planner(_: str):
        return build_route_intent(
            task_type="sentiment",
            selected_dimensions=["risk"],
            selected_agents=["risk_identification"],
            route_confidence=0.6,
            fallback_reason="fallback to full DAG",
        )

    report = evaluate_route_intents([case], planner)

    assert report.dimension_recall == 0.0
    assert report.agent_recall == 0.0
    assert report.over_selection_count == 2
    assert report.under_selection_count == 2


def test_unclear_query_clarification_accuracy() -> None:
    case = RouteEvalCase(
        id="unclear",
        query="This thing?",
        gold_task_type="general",
        gold_targets=(),
        gold_dimensions=(),
        gold_agents=(),
        gold_needs_clarification=True,
    )

    def planner(_: str):
        return build_route_intent(
            needs_clarification=True,
            clarification_question="Please clarify the routing target before selected planning.",
            fallback_reason="planner_parse_failed",
        )

    report = evaluate_route_intents([case], planner)

    assert report.clarification_accuracy == 1.0
    assert report.fallback_rate == 1.0
