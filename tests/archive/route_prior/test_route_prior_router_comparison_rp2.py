from __future__ import annotations

import copy

from react_agent.route_reliability import compare_route_prior_to_router


def _shadow() -> dict[str, object]:
    return {
        "schema_version": "route_reliability_shadow_v0",
        "algorithm": "rarp_v0",
        "shadow_only": True,
        "confidence_band": "high",
        "cards": [
            {"agent_id": "a03_macro_industry_research", "priority": "strong"},
            {"agent_id": "a11_rates_fx", "priority": "strong"},
            {"agent_id": "a09_sector_bank", "priority": "candidate"},
            {"agent_id": "a21_portfolio_manager", "priority": "deprioritized"},
            {"agent_id": "a20_compliance_review", "priority": "hidden"},
        ],
        "groups": {
            "strongly_recommended": ["a03_macro_industry_research", "a11_rates_fx"],
            "candidate": ["a09_sector_bank"],
            "wildcard": [],
            "deprioritized": ["a21_portfolio_manager"],
        },
    }


def test_compare_route_prior_to_router_detects_omitted_and_deprioritized() -> None:
    layer_plan = {
        "L1": ["a01_cio_orchestrator"],
        "L2": ["a03_macro_industry_research"],
        "L3": ["a21_portfolio_manager", "a20_compliance_review"],
        "L4": ["a25_report_center"],
    }

    comparison = compare_route_prior_to_router(_shadow(), layer_plan)

    assert comparison["schema_version"] == "route_prior_router_comparison_v0"
    assert comparison["prior_confidence_band"] == "high"
    assert comparison["router_overlap"] == 0.4
    assert comparison["prior_only_agents"] == ["a11_rates_fx", "a09_sector_bank"]
    assert comparison["router_only_agents"] == ["a20_compliance_review"]
    assert comparison["omitted_strong_recommended"] == ["a11_rates_fx"]
    assert comparison["selected_deprioritized"] == ["a21_portfolio_manager"]
    assert comparison["disagreement_band"] == "high"
    assert "overlap:low" in comparison["reason_codes"]
    assert "omitted_strong_recommended:1" in comparison["reason_codes"]
    assert "selected_deprioritized:1" in comparison["reason_codes"]


def test_compare_route_prior_to_router_does_not_mutate_inputs() -> None:
    shadow = _shadow()
    layer_plan = {
        "L2": ["a03_macro_industry_research", "a09_sector_bank"],
        "L3": ["a21_portfolio_manager"],
    }
    shadow_before = copy.deepcopy(shadow)
    plan_before = copy.deepcopy(layer_plan)

    compare_route_prior_to_router(shadow, layer_plan)

    assert shadow == shadow_before
    assert layer_plan == plan_before


def test_compare_route_prior_to_router_handles_missing_inputs() -> None:
    comparison = compare_route_prior_to_router(None, None)

    assert comparison == {
        "schema_version": "route_prior_router_comparison_v0",
        "prior_confidence_band": "",
        "router_overlap": 0.0,
        "prior_only_agents": [],
        "router_only_agents": [],
        "omitted_strong_recommended": [],
        "selected_deprioritized": [],
        "disagreement_band": "low",
        "reason_codes": ["overlap:none"],
    }
