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
        "L1": ["a01_cio_orchestrator", "a22_financial_data_service"],
        "L2": [
            "a03_macro_industry_research",
            "a04_commodity_hedging",
            "a06_financial_statement_analysis",
            "a08_industry_hotspot",
            "a11_index_technical_analysis",
            "a10_stock_technical_analysis",
            "a12_research_synthesis",
            "a14_ipo_investor_behavior",
            "a16_ml_valuation",
            "a17_traditional_valuation",
            "a18_meta_valuation",
            "a19_risk_identification",
            "a23_crash_risk",
        ],
        "L3": ["a26_composite_valuation", "a27_risk_constraint", "a28_composite_sentiment"],
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
                "selected": [
                    "a03_macro_industry_research",
                    "a04_commodity_hedging",
                    "a17_traditional_valuation",
                ],
            },
            {"layer": "L3", "mode": "Star", "selected": ["a26_composite_valuation"]},
            {"layer": "L4", "mode": "Chain", "selected": ["a25_report_center"]},
        ]
    }
    plan, _modes, stats = router_parse.parse_router_layers_with_stats(
        json.dumps(raw), _agent_catalog()
    )
    assert stats["parse_ok"] is True
    assert stats["used_default_plan"] is False
    assert plan["L2"] == [
        "a03_macro_industry_research",
        "a04_commodity_hedging",
        "a17_traditional_valuation",
    ]
    assert plan["L3"] == ["a26_composite_valuation"]


def test_detailed_profile_catalog_is_normalized_to_allowed_ids() -> None:
    catalog = {
        "L1": [{"id": "a01_cio_orchestrator", "name": "问题解析与协同编排智能体"}],
        "L2": [
            {
                "id": "a17_traditional_valuation",
                "name": "传统企业估值智能体",
                "when_to_use": "传统估值",
                "when_not_to_use": "指数估值",
            }
        ],
        "L3": [],
        "L4": [{"id": "a25_report_center", "name": "报告生成智能体"}],
    }
    raw = {
        "layers": [
            {"layer": "L1", "mode": "Chain", "selected": ["a01_cio_orchestrator"]},
            {"layer": "L2", "mode": "Star", "selected": ["a17_traditional_valuation"]},
            {"layer": "L3", "mode": "Star", "selected": ["a26_composite_valuation"]},
            {"layer": "L4", "mode": "Chain", "selected": ["a25_report_center"]},
        ]
    }
    plan, _modes, stats = router_parse.parse_router_layers_with_stats(
        json.dumps(raw), catalog
    )
    assert stats["parse_ok"] is True
    assert stats["filtered_agents"] == 1
    assert plan["L2"] == ["a17_traditional_valuation"]
    assert plan["L3"] == []


def test_default_layer_plan_does_not_restore_a02_task_router() -> None:
    catalog = dict(_agent_catalog())
    catalog["L1"] = ["a01_cio_orchestrator", "a02_task_router"]
    plan, _modes = router_parse.default_layer_plan(catalog)
    assert "a02_task_router" not in _flatten(plan)


def test_parse_stats_does_not_truncate_valid_l2_selection() -> None:
    raw = {
        "layers": [
            {"layer": "L1", "mode": "Chain", "selected": ["a01_cio_orchestrator"]},
            {
                "layer": "L2",
                "mode": "Star",
                "selected": [
                    "a03_macro_industry_research",
                    "a04_commodity_hedging",
                    "a06_financial_statement_analysis",
                    "a08_industry_hotspot",
                    "a11_index_technical_analysis",
                    "a16_ml_valuation",
                ],
            },
            {
                "layer": "L3",
                "mode": "Star",
                "selected": ["a26_composite_valuation", "a27_risk_constraint"],
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
    assert stats["l2_truncated"] == 0
    assert plan["L2"] == [
        "a03_macro_industry_research",
        "a04_commodity_hedging",
        "a06_financial_statement_analysis",
        "a08_industry_hotspot",
        "a11_index_technical_analysis",
        "a16_ml_valuation",
    ]


def test_parse_stats_filtered_invalid_agents() -> None:
    raw = {
        "layers": [
            {"layer": "L1", "mode": "Chain", "selected": ["a01_cio_orchestrator"]},
            {
                "layer": "L2",
                "mode": "Star",
                "selected": ["a03_macro_industry_research", "a26_composite_valuation", "bad_id"],
            },
            {
                "layer": "L3",
                "mode": "Star",
                "selected": ["a27_risk_constraint"],
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
