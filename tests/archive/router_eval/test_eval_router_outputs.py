import json

import pytest

from ops.regression.router import eval_router_outputs


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
        ],
        "L3": ["a17_traditional_valuation", "a19_risk_identification", "a19_risk_identification"],
        "L4": ["a25_report_center"],
    }


def test_eval_router_outputs_metrics() -> None:
    ok_plan = {
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
                ],
            },
            {
                "layer": "L3",
                "mode": "Star",
                "selected": ["a17_traditional_valuation", "a19_risk_identification"],
            },
            {"layer": "L4", "mode": "Chain", "selected": ["a25_report_center"]},
        ],
        "reason": "ok",
    }
    over_plan = {
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
        "reason": "over",
    }
    records = [
        {"id": "1", "raw_text": json.dumps(ok_plan)},
        {"id": "2", "raw_text": "not json"},
        {"id": "3", "raw_text": json.dumps(over_plan)},
    ]
    metrics = eval_router_outputs.compute_metrics(records, _agent_catalog())
    assert metrics["total"] == 3
    assert metrics["valid_json_rate"] == pytest.approx(2 / 3, rel=1e-6)
    assert metrics["used_default_plan_rate"] == pytest.approx(1 / 3, rel=1e-6)
    assert metrics["l2_trunc_rate"] == pytest.approx(1 / 3, rel=1e-6)
    assert metrics["l2_len_dist"].get("5") == 2
