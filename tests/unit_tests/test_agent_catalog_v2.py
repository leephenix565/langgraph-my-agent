import json
from pathlib import Path

from react_agent.agents import AGENT_METADATA, AgentMetadata, load_metadata_from_dir


REPO_ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = REPO_ROOT / "config" / "agents"

TARGET_IDS_BY_LAYER = {
    "L1": ["a01_cio_orchestrator"],
    "L2": [
        "a03_macro_industry_research",
        "a04_commodity_hedging",
        "a06_financial_statement_analysis",
        "a07_macro_sentiment",
        "a08_industry_hotspot",
        "a09_company_sentiment_radar",
        "a10_stock_technical_analysis",
        "a12_research_synthesis",
        "a13_fund_manager_behavior",
        "a14_ipo_investor_behavior",
        "a15_entity_relation_extraction",
        "a22_financial_data_service",
    ],
    "L3": [
        "a11_index_technical_analysis",
        "a16_ml_valuation",
        "a17_traditional_valuation",
        "a18_meta_valuation",
        "a19_risk_identification",
        "a20_compliance_review",
        "a23_crash_risk",
        "a24_financial_fraud_risk",
        "a26_composite_valuation",
        "a27_risk_constraint",
        "a28_composite_sentiment",
    ],
    "L4": ["a25_report_center"],
}

DISABLED_NON_EXCEL_FUNCTIONAL_IDS = {
    "a05_annual_report_analysis",
    "a21_portfolio_manager",
}

REMOVED_OLD_IDS = {
    "a02_task_router",
    "a03_macro_policy",
    "a04_industry_layout",
    "a05_product_pricing",
    "a06_financial_reports",
    "a07_financial_modeling",
    "a08_tech_due_diligence",
    "a09_macro_sentiment",
    "a10_industry_sentiment",
    "a11_equity_sentiment",
    "a12_ipo_investor_behavior",
    "a13_index_technical_analysis",
    "a14_single_stock_tech",
    "a15_research_synthesis",
    "a16_fund_manager_behavior",
    "a17_client_profile",
    "a18_primary_secondary_valuation",
    "a19_market_risk",
    "a20_fundamental_risk",
    "a21_reg_compliance",
    "a22_suitability_review",
    "a23_portfolio_opt",
    "a26_sci_tech_valuation",
    "a27_portfolio_backtest",
}


def _load_config_metadata() -> list[dict]:
    return [
        json.loads(path.read_text(encoding="utf-8"))
        for path in sorted(CONFIG_DIR.glob("agent_*.json"))
    ]


def test_agent_catalog_v2_config_shape() -> None:
    metadata = _load_config_metadata()
    ids = [item["id"] for item in metadata]
    enabled = [item for item in metadata if item["default_enabled"] is True]
    disabled = [item for item in metadata if item["default_enabled"] is False]
    assert len(metadata) == 27
    assert len(enabled) == 25
    assert {item["id"] for item in disabled} == DISABLED_NON_EXCEL_FUNCTIONAL_IDS
    assert all(item["version"] == "catalog_v2_sheet2" for item in metadata)
    assert not (set(ids) & REMOVED_OLD_IDS)

    for layer, expected_ids in TARGET_IDS_BY_LAYER.items():
        actual_ids = [
            item["id"] for item in metadata if item["layer"] == layer and item["default_enabled"]
        ]
        assert actual_ids == expected_ids


def test_excel_functional_catalog_excludes_special_runtime_roles() -> None:
    metadata = _load_config_metadata()
    enabled_ids = {item["id"] for item in metadata if item["default_enabled"]}
    special_ids = {"a01_cio_orchestrator", "a25_report_center"}
    assert special_ids <= enabled_ids
    assert "a02_task_router" not in enabled_ids
    assert len(enabled_ids - special_ids) == 23


def test_agent_catalog_v2_required_metadata_fields() -> None:
    required = {
        "id",
        "name",
        "description",
        "capabilities",
        "input_type",
        "latency_level",
        "cost_level",
        "version",
        "layer",
        "team",
        "role_type",
        "default_enabled",
    }
    for item in _load_config_metadata():
        assert set(item) == required
        assert item["name"]
        assert item["description"].startswith("功能：")
        assert "输入：" in item["description"]
        assert "输出：" in item["description"]
        assert item["capabilities"]


def test_load_metadata_from_dir_uses_filename_order(tmp_path) -> None:
    first = {
        "id": "ordered_first",
        "name": "first",
        "description": "first",
        "capabilities": [],
        "input_type": "",
        "latency_level": "",
        "cost_level": "",
        "version": "",
        "layer": "L2",
    }
    second = dict(first, id="ordered_second", name="second")
    (tmp_path / "agent_010.json").write_text(json.dumps(second), encoding="utf-8")
    (tmp_path / "agent_001.json").write_text(json.dumps(first), encoding="utf-8")

    previous = dict(AGENT_METADATA)
    try:
        AGENT_METADATA.clear()
        load_metadata_from_dir(tmp_path)
        assert list(AGENT_METADATA) == ["ordered_first", "ordered_second"]
        assert all(isinstance(meta, AgentMetadata) for meta in AGENT_METADATA.values())
    finally:
        AGENT_METADATA.clear()
        AGENT_METADATA.update(previous)
