from pathlib import Path

AGENT_IDS = (
    "route_planner",
    "financial_data_service",
    "entity_relation_extractor",
    "value_traditional_valuation",
    "value_ml_valuation",
    "value_meta_valuation",
    "value_financial_analysis",
    "value_research_synthesis",
    "market_stock_technical",
    "market_fund_manager_behavior",
    "market_ipo_investor_behavior",
    "market_capital_flow_chip",
    "risk_crash",
    "risk_financial_fraud",
    "risk_identification",
    "risk_compliance_review",
    "macro_analysis",
    "macro_commodity_pricing",
    "macro_index_valuation",
    "macro_sentiment",
    "macro_industry_hotspot",
    "sentiment_company_radar",
    "value_composite",
    "market_composite",
    "risk_composite",
    "macro_composite",
    "decision_synthesizer",
    "report_generator",
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def test_fixed_dag_architecture_doc_lists_target_agents() -> None:
    assert len(AGENT_IDS) == 28

    path = _repo_root() / "docs" / "ARCHITECTURE_FIXED_DAG.md"
    text = path.read_text(encoding="utf-8")

    missing = [agent_id for agent_id in AGENT_IDS if agent_id not in text]

    assert missing == []
    assert text.count("sentiment_company_radar") == 1


def test_fixed_dag_architecture_doc_excludes_legacy_route_modes() -> None:
    path = _repo_root() / "docs" / "ARCHITECTURE_FIXED_DAG.md"
    text = path.read_text(encoding="utf-8")

    legacy_modes = ("Star", "Chain", "Debate", "Tree")

    assert not any(mode in text for mode in legacy_modes)
