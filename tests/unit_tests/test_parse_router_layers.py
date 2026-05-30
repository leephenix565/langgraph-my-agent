import json
import types

from react_agent.context import Context
from react_agent.graph import _default_layer_plan, _parse_router_layers
from react_agent.graph import route_from_manager_summary


def _selected_ids(plan: dict[str, list[str]]) -> set[str]:
    return {agent_id for selected in plan.values() for agent_id in selected}


def test_parse_with_extra_text() -> None:
    raw = 'some text before {"layers":[{"layer":"L1","mode":"Star","selected":["a01"]}]} trailing'
    plan, modes = _parse_router_layers(raw)
    assert "L1" in plan and modes["L1"] in {"Star", "Chain", "Debate", "Tree"}


def test_parse_old_selected_only() -> None:
    raw = '{"selected":["a03_macro_industry_research"]}'
    plan, modes = _parse_router_layers(raw)
    assert plan["L2"]  # old format should populate L2
    assert modes["L2"] == "Star"


def test_parse_current_schema_selecting_a03_only() -> None:
    raw = (
        '{"layers":['
        '{"layer":"L1","mode":"Chain","selected":["a01_cio_orchestrator"]},'
        '{"layer":"L2","mode":"Star","selected":["a03_macro_industry_research"]},'
        '{"layer":"L3","mode":"Star","selected":[]},'
        '{"layer":"L4","mode":"Chain","selected":["a25_report_center"]}'
        ']}'
    )
    plan, modes = _parse_router_layers(raw)
    assert plan["L1"] == ["a01_cio_orchestrator"]
    assert plan["L2"] == ["a03_macro_industry_research"]
    assert plan["L3"] == []
    assert plan["L4"] == ["a25_report_center"]
    assert modes["L2"] == "Star"


def test_parse_mock_macro_only_route_keeps_a03_without_unrelated_externals() -> None:
    raw = (
        '{"layers":['
        '{"layer":"L1","mode":"Chain","selected":["a01_cio_orchestrator"]},'
        '{"layer":"L2","mode":"Star","selected":["a03_macro_industry_research"]},'
        '{"layer":"L3","mode":"Star","selected":[]},'
        '{"layer":"L4","mode":"Chain","selected":["a25_report_center"]}'
        ']}'
    )
    plan, _ = _parse_router_layers(raw)
    selected = _selected_ids(plan)
    assert "a03_macro_industry_research" in selected
    assert not (selected & {"a04_commodity_hedging", "a06_financial_statement_analysis", "a23_crash_risk", "a22_financial_data_service"})


def test_parse_mock_commodity_only_route_keeps_a04_without_unrelated_externals() -> None:
    raw = (
        '{"layers":['
        '{"layer":"L1","mode":"Chain","selected":["a01_cio_orchestrator"]},'
        '{"layer":"L2","mode":"Star","selected":["a04_commodity_hedging"]},'
        '{"layer":"L3","mode":"Star","selected":[]},'
        '{"layer":"L4","mode":"Chain","selected":["a25_report_center"]}'
        ']}'
    )
    plan, _ = _parse_router_layers(raw)
    selected = _selected_ids(plan)
    assert "a04_commodity_hedging" in selected
    assert not (selected & {"a03_macro_industry_research", "a06_financial_statement_analysis", "a23_crash_risk", "a22_financial_data_service"})


def test_parse_mock_financial_only_route_keeps_a06_without_unrelated_externals() -> None:
    raw = (
        '{"layers":['
        '{"layer":"L1","mode":"Chain","selected":["a01_cio_orchestrator"]},'
        '{"layer":"L2","mode":"Star","selected":["a06_financial_statement_analysis"]},'
        '{"layer":"L3","mode":"Star","selected":[]},'
        '{"layer":"L4","mode":"Chain","selected":["a25_report_center"]}'
        ']}'
    )
    plan, _ = _parse_router_layers(raw)
    selected = _selected_ids(plan)
    assert "a06_financial_statement_analysis" in selected
    assert not (selected & {"a04_commodity_hedging", "a23_crash_risk", "a22_financial_data_service"})


def test_parse_mock_crash_risk_only_route_keeps_a23_without_financial_or_data_service() -> None:
    raw = (
        '{"layers":['
        '{"layer":"L1","mode":"Chain","selected":["a01_cio_orchestrator"]},'
        '{"layer":"L2","mode":"Star","selected":["a23_crash_risk"]},'
        '{"layer":"L3","mode":"Star","selected":[]},'
        '{"layer":"L4","mode":"Chain","selected":["a25_report_center"]}'
        ']}'
    )
    plan, _ = _parse_router_layers(raw)
    selected = _selected_ids(plan)
    assert "a23_crash_risk" in selected
    assert not (selected & {"a06_financial_statement_analysis", "a04_commodity_hedging", "a22_financial_data_service"})


def test_valid_parse_does_not_truncate_multiple_l2_agents() -> None:
    l2_agents = [
        "a17_traditional_valuation",
        "a16_ml_valuation",
        "a18_meta_valuation",
        "a11_index_technical_analysis",
        "a04_commodity_hedging",
        "a06_financial_statement_analysis",
        "a12_research_synthesis",
        "a23_crash_risk",
    ]
    raw = json.dumps(
        {
            "layers": [
                {"layer": "L1", "mode": "Chain", "selected": ["a01_cio_orchestrator"]},
                {"layer": "L2", "mode": "Star", "selected": l2_agents},
                {"layer": "L3", "mode": "Star", "selected": []},
                {"layer": "L4", "mode": "Chain", "selected": ["a25_report_center"]},
            ]
        }
    )
    plan, _ = _parse_router_layers(raw)
    assert plan["L2"] == l2_agents


def test_parse_with_joined_mode() -> None:
    raw = '{"layers":[{"layer":"L1","mode":"Star,Chain,Debate,Tree","selected":["a01"]}]}'
    plan, modes = _parse_router_layers(raw)
    assert modes["L1"] in {"Star", "Chain", "Debate", "Tree"}


def test_parse_invalid_json_fallback() -> None:
    raw = "not json at all"
    plan, modes = _parse_router_layers(raw)
    assert set(plan.keys()) == {"L1", "L2", "L3", "L4"}


def test_parse_invalid_ids_fall_back_to_default_layer_plan() -> None:
    raw = '{"layers":[{"layer":"L3","mode":"Star","selected":["Sentiment_Analyst"]}]}'
    default_plan, _ = _default_layer_plan()
    plan, _ = _parse_router_layers(raw)
    assert plan["L3"] == default_plan["L3"]  # fallback when selection is invalid but non-empty


def test_parse_explicit_empty_layer_keeps_empty() -> None:
    raw = '{"layers":[{"layer":"L3","mode":"Star","selected":[]}]}'
    plan, _ = _parse_router_layers(raw)
    assert plan["L3"] == []  # explicit empty should remain empty


def test_parse_legacy_layer_mapping() -> None:
    raw = '{"layers":[{"layer":"L4","mode":"Star","selected":[]},{"layer":"L5","mode":"Chain","selected":[]}]}'
    plan, modes = _parse_router_layers(raw)
    assert set(plan.keys()) == {"L1", "L2", "L3", "L4"}
    assert plan["L3"] == []
    assert plan["L4"] == []
    assert modes["L3"] == "Star"
    assert modes["L4"] == "Chain"


def test_route_star_first_time_goes_broadcast() -> None:
    state = {
        "current_layer": "L2",
        "plan": ["a03_macro_industry_research"],
        "layer_plan": {"L2": ["a03_macro_industry_research"]},
        "layer_mode": {"L2": "Star"},
        "analyst_results": {},
        "fanout_targets": [],
    }
    assert route_from_manager_summary(state) == "manager_broadcast"


def test_route_star_after_fanout_goes_noop() -> None:
    state = {
        "current_layer": "L2",
        "plan": ["a03_macro_industry_research"],
        "layer_plan": {"L2": ["a03_macro_industry_research"]},
        "layer_mode": {"L2": "Star"},
        "analyst_results": {},
        "fanout_targets": ["a03_macro_industry_research"],
    }
    assert route_from_manager_summary(state) == "noop"


def test_manager_summary_advance_clears_fanout_targets() -> None:
    # Simulate finishing L1 and advancing to L2; fanout_targets should reset.
    layer_plan = {"L1": ["a01"], "L2": ["a03"], "L3": [], "L4": []}
    state = {
        "layer_plan": layer_plan,
        "layer_mode": {"L1": "Chain", "L2": "Star", "L3": "Star", "L4": "Chain"},
        "current_layer": "L1",
        "plan": ["a01"],
        "analyst_results": {"a01": {}},
        "fanout_targets": ["a01"],
        "messages": [],
    }

    import anyio
    from react_agent.graph import manager_summary

    runtime = types.SimpleNamespace(context=Context())
    res = anyio.run(manager_summary, state, runtime)  # type: ignore[arg-type]
    assert res["current_layer"] == "L2"
    assert res.get("fanout_targets") == []


def test_route_star_first_time_after_advance_goes_broadcast() -> None:
    state = {
        "current_layer": "L2",
        "plan": ["a03_macro_industry_research"],
        "layer_plan": {"L2": ["a03_macro_industry_research"]},
        "layer_mode": {"L2": "Star"},
        "analyst_results": {},
        "fanout_targets": [],
    }
    assert route_from_manager_summary(state) == "manager_broadcast"
