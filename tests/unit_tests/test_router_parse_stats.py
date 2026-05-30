import json

from react_agent import router_parse

EXTERNAL_WRAPPER_IDS = {
    "a03_macro_industry_research",
    "a04_commodity_hedging",
    "a06_financial_statement_analysis",
    "a10_stock_technical_analysis",
    "a11_index_technical_analysis",
    "a12_research_synthesis",
    "a14_ipo_investor_behavior",
    "a16_ml_valuation",
    "a17_traditional_valuation",
    "a18_meta_valuation",
    "a22_financial_data_service",
    "a23_crash_risk",
    "a26_composite_valuation",
}

DISABLED_AGENT_IDS = {"a05_annual_report_analysis", "a21_portfolio_manager"}


def _agent_catalog():
    return {
        "L1": ["a01_cio_orchestrator"],
        "L2": [
            "a03_macro_industry_research",
            "a04_commodity_hedging",
            "a05_annual_report_analysis",
            "a06_financial_statement_analysis",
            "a06_financial_statement_analysis",
            "a08_industry_hotspot",
            "a10_stock_technical_analysis",
            "a12_research_synthesis",
            "a14_ipo_investor_behavior",
            "a22_financial_data_service",
        ],
        "L3": [
            "a11_index_technical_analysis",
            "a16_ml_valuation",
            "a17_traditional_valuation",
            "a18_meta_valuation",
            "a19_risk_identification",
            "a19_risk_identification",
            "a21_portfolio_manager",
            "a23_crash_risk",
            "a26_composite_valuation",
        ],
        "L4": ["a25_report_center"],
    }


def _flatten(plan):
    return [aid for layer in router_parse.LAYER_ORDER for aid in plan.get(layer, [])]


def test_parse_stats_invalid_json_uses_default() -> None:
    plan, modes, stats = router_parse.parse_router_layers_with_stats("not json", _agent_catalog())
    default_plan, _ = router_parse.default_layer_plan(_agent_catalog())
    assert plan == default_plan
    assert stats["parse_ok"] is False
    assert stats["used_default_plan"] is True
    assert stats["fallback_reason"] == "parse_failed"
    assert stats["l2_truncated"] == 0
    assert stats["filtered_agents"] == 0


def test_default_layer_plan_on_parse_failure_selects_only_special_roles() -> None:
    plan, _modes, stats = router_parse.parse_router_layers_with_stats("not json", _agent_catalog())
    assert _flatten(plan) == ["a01_cio_orchestrator", "a25_report_center"]
    assert plan["L2"] == []
    assert plan["L3"] == []
    assert stats["parse_ok"] is False
    assert stats["used_default_plan"] is True


def test_default_layer_plan_does_not_select_external_wrappers() -> None:
    plan, _modes = router_parse.default_layer_plan(_agent_catalog())
    assert not (set(_flatten(plan)) & EXTERNAL_WRAPPER_IDS)


def test_default_layer_plan_does_not_select_disabled_agents() -> None:
    plan, _modes = router_parse.default_layer_plan(_agent_catalog())
    assert not (set(_flatten(plan)) & DISABLED_AGENT_IDS)


def test_valid_parse_still_preserves_selected_functional_agents() -> None:
    raw = {
        "layers": [
            {"layer": "L1", "mode": "Chain", "selected": ["a01_cio_orchestrator"]},
            {
                "layer": "L2",
                "mode": "Star",
                "selected": ["a03_macro_industry_research", "a04_commodity_hedging"],
            },
            {"layer": "L3", "mode": "Star", "selected": ["a17_traditional_valuation"]},
            {"layer": "L4", "mode": "Chain", "selected": ["a25_report_center"]},
        ]
    }
    plan, _modes, stats = router_parse.parse_router_layers_with_stats(
        json.dumps(raw), _agent_catalog()
    )
    assert stats["parse_ok"] is True
    assert stats["used_default_plan"] is False
    assert plan["L2"] == ["a03_macro_industry_research", "a04_commodity_hedging"]
    assert plan["L3"] == ["a17_traditional_valuation"]


def test_default_layer_plan_does_not_restore_a02_task_router() -> None:
    catalog = dict(_agent_catalog())
    catalog["L1"] = ["a01_cio_orchestrator", "a02_task_router"]
    plan, _modes = router_parse.default_layer_plan(catalog)
    assert "a02_task_router" not in _flatten(plan)


def test_parse_stats_l2_truncated() -> None:
    raw = {
        "layers": [
            {"layer": "L1", "mode": "Chain", "selected": ["a01_cio_orchestrator"]},
            {
                "layer": "L2",
                "mode": "Star",
                "selected": [
                    "a03_macro_industry_research",
                    "a04_commodity_hedging",
                    "a05_annual_report_analysis",
                    "a06_financial_statement_analysis",
                    "a06_financial_statement_analysis",
                    "a08_industry_hotspot",
                ],
            },
            {
                "layer": "L3",
                "mode": "Star",
                "selected": ["a17_traditional_valuation", "a19_risk_identification"],
            },
            {"layer": "L4", "mode": "Chain", "selected": ["a25_report_center"]},
        ],
        "reason": "test",
    }
    plan, modes, stats = router_parse.parse_router_layers_with_stats(
        json.dumps(raw), _agent_catalog()
    )
    assert stats["parse_ok"] is True
    assert stats["used_default_plan"] is False
    assert stats["l2_truncated"] == 1
    assert len(plan["L2"]) == 5


def test_parse_stats_filtered_invalid_agents() -> None:
    raw = {
        "layers": [
            {"layer": "L1", "mode": "Chain", "selected": ["a01_cio_orchestrator"]},
            {
                "layer": "L2",
                "mode": "Star",
                "selected": ["a03_macro_industry_research", "a19_risk_identification", "bad_id"],
            },
            {
                "layer": "L3",
                "mode": "Star",
                "selected": ["a17_traditional_valuation"],
            },
            {"layer": "L4", "mode": "Chain", "selected": ["a25_report_center"]},
        ],
        "reason": "test",
    }
    plan, modes, stats = router_parse.parse_router_layers_with_stats(
        json.dumps(raw), _agent_catalog()
    )
    assert stats["parse_ok"] is True
    assert stats["used_default_plan"] is False
    assert stats["filtered_agents"] == 2
    assert plan["L2"] == ["a03_macro_industry_research"]
