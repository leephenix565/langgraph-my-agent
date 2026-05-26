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
        "a05_annual_report_analysis",
        "a06_financial_statement_analysis",
        "a07_macro_sentiment",
        "a08_industry_hotspot",
        "a09_company_sentiment_radar",
        "a10_stock_technical_analysis",
        "a11_index_technical_analysis",
        "a12_research_synthesis",
        "a13_fund_manager_behavior",
        "a14_ipo_investor_behavior",
        "a15_entity_relation_extraction",
    ],
    "L3": [
        "a16_ml_valuation",
        "a17_traditional_valuation",
        "a18_meta_valuation",
        "a19_risk_identification",
        "a20_compliance_review",
        "a21_portfolio_manager",
    ],
    "L4": ["a25_report_center"],
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
    assert len(metadata) == 21
    assert all(item["default_enabled"] is True for item in metadata)
    assert all(item["version"] == "catalog_v2_sheet2" for item in metadata)
    assert not (set(ids) & REMOVED_OLD_IDS)

    for layer, expected_ids in TARGET_IDS_BY_LAYER.items():
        actual_ids = [item["id"] for item in metadata if item["layer"] == layer]
        assert actual_ids == expected_ids


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
