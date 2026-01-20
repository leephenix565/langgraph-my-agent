import json

from react_agent import router_parse


def _agent_catalog():
    return {
        "L1": ["a01_cio_orchestrator"],
        "L2": [
            "a03_macro_policy",
            "a04_industry_layout",
            "a05_product_pricing",
            "a06_financial_reports",
            "a07_financial_modeling",
            "a08_tech_due_diligence",
        ],
        "L3": ["a18_primary_secondary_valuation", "a19_market_risk", "a20_fundamental_risk"],
        "L4": ["a25_report_center"],
    }


def test_parse_stats_invalid_json_uses_default() -> None:
    plan, modes, stats = router_parse.parse_router_layers_with_stats("not json", _agent_catalog())
    default_plan, _ = router_parse.default_layer_plan(_agent_catalog())
    assert plan == default_plan
    assert stats["parse_ok"] is False
    assert stats["used_default_plan"] is True
    assert stats["l2_truncated"] == 0
    assert stats["filtered_agents"] == 0


def test_parse_stats_l2_truncated() -> None:
    raw = {
        "layers": [
            {"layer": "L1", "mode": "Chain", "selected": ["a01_cio_orchestrator"]},
            {
                "layer": "L2",
                "mode": "Star",
                "selected": [
                    "a03_macro_policy",
                    "a04_industry_layout",
                    "a05_product_pricing",
                    "a06_financial_reports",
                    "a07_financial_modeling",
                    "a08_tech_due_diligence",
                ],
            },
            {
                "layer": "L3",
                "mode": "Star",
                "selected": ["a18_primary_secondary_valuation", "a19_market_risk"],
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
                "selected": ["a03_macro_policy", "a19_market_risk", "bad_id"],
            },
            {
                "layer": "L3",
                "mode": "Star",
                "selected": ["a18_primary_secondary_valuation"],
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
    assert plan["L2"] == ["a03_macro_policy"]
