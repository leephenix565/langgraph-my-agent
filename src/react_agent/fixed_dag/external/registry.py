"""Built-in fixed-DAG external compute demo registry."""

from __future__ import annotations

import os

from react_agent.fixed_dag.external.constants import COMPUTE_PATH
from react_agent.fixed_dag.external.types import ExternalComputeDemoEntry
from react_agent.fixed_dag_contracts import (
    DECISION_RESULT_SCHEMA_VERSION,
    REPORT_RESULT_SCHEMA_VERSION,
)


def _demo_base_url(agent_id: str, default: str) -> str:
    env_name = f"EXTERNAL_COMPUTE_DEMO_URL_{agent_id.upper()}"
    return str(os.getenv(env_name, default) or default).strip().rstrip("/")


DEMO_COMPUTE_SERVICE_REGISTRY: dict[str, ExternalComputeDemoEntry] = {
    "financial_data_service": ExternalComputeDemoEntry(
        agent_id="financial_data_service",
        base_url=_demo_base_url("financial_data_service", "http://127.0.0.1:11000"),
        compute_path=COMPUTE_PATH,
        expected_payload="data_bundle_v1",
        dimension="l1",
        external_agent_id="financial_data_service",
    ),
    "entity_relation_extractor": ExternalComputeDemoEntry(
        agent_id="entity_relation_extractor",
        base_url=_demo_base_url("entity_relation_extractor", "http://127.0.0.1:10017"),
        compute_path=COMPUTE_PATH,
        expected_payload="entity_relation_bundle_v1",
        dimension="l1",
        external_agent_id="entity_relation_agent",
    ),
    "value_traditional_valuation": ExternalComputeDemoEntry(
        agent_id="value_traditional_valuation",
        base_url=_demo_base_url("value_traditional_valuation", "http://127.0.0.1:10000"),
        compute_path=COMPUTE_PATH,
        expected_payload="agent_conclusion_v1",
        dimension="value",
        external_agent_id="valuation_traditional",
    ),
    "value_ml_valuation": ExternalComputeDemoEntry(
        agent_id="value_ml_valuation",
        base_url=_demo_base_url("value_ml_valuation", "http://127.0.0.1:10001"),
        compute_path=COMPUTE_PATH,
        expected_payload="agent_conclusion_v1",
        dimension="value",
        external_agent_id="valuation_ml",
    ),
    "value_meta_valuation": ExternalComputeDemoEntry(
        agent_id="value_meta_valuation",
        base_url=_demo_base_url("value_meta_valuation", "http://127.0.0.1:10002"),
        compute_path=COMPUTE_PATH,
        expected_payload="agent_conclusion_v1",
        dimension="value",
        external_agent_id="valuation_meta",
    ),
    "value_research_synthesis": ExternalComputeDemoEntry(
        agent_id="value_research_synthesis",
        base_url=_demo_base_url("value_research_synthesis", "http://127.0.0.1:10006"),
        compute_path=COMPUTE_PATH,
        expected_payload="agent_conclusion_v1",
        dimension="value",
        external_agent_id="analyst_research",
    ),
    "market_stock_technical": ExternalComputeDemoEntry(
        agent_id="market_stock_technical",
        base_url=_demo_base_url("market_stock_technical", "http://127.0.0.1:10009"),
        compute_path=COMPUTE_PATH,
        expected_payload="agent_conclusion_v1",
        dimension="market",
        external_agent_id="technical_stock",
    ),
    "market_fund_manager_behavior": ExternalComputeDemoEntry(
        agent_id="market_fund_manager_behavior",
        base_url=_demo_base_url("market_fund_manager_behavior", "http://127.0.0.1:8503"),
        compute_path=COMPUTE_PATH,
        expected_payload="agent_conclusion_v1",
        dimension="market",
        external_agent_id="fund_manager_behavior",
    ),
    "market_capital_flow_chip": ExternalComputeDemoEntry(
        agent_id="market_capital_flow_chip",
        base_url=_demo_base_url("market_capital_flow_chip", "http://127.0.0.1:10022"),
        compute_path=COMPUTE_PATH,
        expected_payload="agent_conclusion_v1",
        dimension="market",
        external_agent_id="money_flow",
    ),
    "sentiment_company_radar": ExternalComputeDemoEntry(
        agent_id="sentiment_company_radar",
        base_url=_demo_base_url("sentiment_company_radar", "http://127.0.0.1:10020"),
        compute_path=COMPUTE_PATH,
        expected_payload="agent_conclusion_v1",
        dimension="market",
        external_agent_id="company_radar_agent",
    ),
    "market_ipo_investor_behavior": ExternalComputeDemoEntry(
        agent_id="market_ipo_investor_behavior",
        base_url=_demo_base_url("market_ipo_investor_behavior", "http://127.0.0.1:10008"),
        compute_path=COMPUTE_PATH,
        expected_payload="agent_conclusion_v1",
        dimension="market",
        external_agent_id="ipo_investor_behavior",
    ),
    "risk_identification": ExternalComputeDemoEntry(
        agent_id="risk_identification",
        base_url=_demo_base_url("risk_identification", "http://127.0.0.1:10010"),
        compute_path=COMPUTE_PATH,
        expected_payload="agent_conclusion_v1",
        dimension="risk",
        external_agent_id="market_risk_reasoning",
    ),
    "risk_compliance_review": ExternalComputeDemoEntry(
        agent_id="risk_compliance_review",
        base_url=_demo_base_url("risk_compliance_review", "http://127.0.0.1:10011"),
        compute_path=COMPUTE_PATH,
        expected_payload="agent_conclusion_v1",
        dimension="risk",
        external_agent_id="announcement_compliance",
    ),
    "risk_financial_fraud": ExternalComputeDemoEntry(
        agent_id="risk_financial_fraud",
        base_url=_demo_base_url("risk_financial_fraud", "http://127.0.0.1:10013"),
        compute_path=COMPUTE_PATH,
        expected_payload="agent_conclusion_v1",
        dimension="risk",
        external_agent_id="financial_fraud_agent",
    ),
    "risk_crash": ExternalComputeDemoEntry(
        agent_id="risk_crash",
        base_url=_demo_base_url("risk_crash", "http://127.0.0.1:10012"),
        compute_path=COMPUTE_PATH,
        expected_payload="agent_conclusion_v1",
        dimension="risk",
        external_agent_id="crash_risk",
    ),
    "macro_analysis": ExternalComputeDemoEntry(
        agent_id="macro_analysis",
        base_url=_demo_base_url("macro_analysis", "http://127.0.0.1:10014"),
        compute_path=COMPUTE_PATH,
        expected_payload="agent_conclusion_v1",
        dimension="macro",
        external_agent_id="macro_analysis",
        default_target="CN_A_SHARE_MACRO",
    ),
    "macro_commodity_pricing": ExternalComputeDemoEntry(
        agent_id="macro_commodity_pricing",
        base_url=_demo_base_url("macro_commodity_pricing", "http://127.0.0.1:10004"),
        compute_path=COMPUTE_PATH,
        expected_payload="agent_conclusion_v1",
        dimension="macro",
        external_agent_id="price_influence_agent",
        default_target="CU",
    ),
    "macro_index_valuation": ExternalComputeDemoEntry(
        agent_id="macro_index_valuation",
        base_url=_demo_base_url("macro_index_valuation", "http://127.0.0.1:10003"),
        compute_path=COMPUTE_PATH,
        expected_payload="agent_conclusion_v1",
        dimension="macro",
        external_agent_id="valuation_index",
        default_target="沪深300",
    ),
    "macro_sentiment": ExternalComputeDemoEntry(
        agent_id="macro_sentiment",
        base_url=_demo_base_url("macro_sentiment", "http://127.0.0.1:10018"),
        compute_path=COMPUTE_PATH,
        expected_payload="agent_conclusion_v1",
        dimension="macro",
        external_agent_id="macro_sentiment",
        default_target="CN_A_SHARE_MACRO",
    ),
    "macro_industry_hotspot": ExternalComputeDemoEntry(
        agent_id="macro_industry_hotspot",
        base_url=_demo_base_url("macro_industry_hotspot", "http://127.0.0.1:10019"),
        compute_path=COMPUTE_PATH,
        expected_payload="agent_conclusion_v1",
        dimension="macro",
        external_agent_id="macro_industry_hotspot",
        default_target="CN_A_SHARE_MACRO",
    ),
    "value_composite": ExternalComputeDemoEntry(
        agent_id="value_composite",
        base_url=_demo_base_url("value_composite", "http://127.0.0.1:10015"),
        compute_path=COMPUTE_PATH,
        expected_payload="dimension_conclusion_v1",
        dimension="value",
        external_agent_id="composite_valuation",
    ),
    "market_composite": ExternalComputeDemoEntry(
        agent_id="market_composite",
        base_url=_demo_base_url("market_composite", "http://127.0.0.1:10023"),
        compute_path=COMPUTE_PATH,
        expected_payload="dimension_conclusion_v1",
        dimension="market",
        external_agent_id="market_composite",
    ),
    "risk_composite": ExternalComputeDemoEntry(
        agent_id="risk_composite",
        base_url=_demo_base_url("risk_composite", "http://127.0.0.1:10016"),
        compute_path=COMPUTE_PATH,
        expected_payload="risk_conclusion_v1",
        dimension="risk",
        external_agent_id="risk_synthesis",
    ),
    "macro_composite": ExternalComputeDemoEntry(
        agent_id="macro_composite",
        base_url=_demo_base_url("macro_composite", "http://127.0.0.1:10024"),
        compute_path=COMPUTE_PATH,
        expected_payload="macro_conclusion_v1",
        dimension="macro",
        external_agent_id="macro_synthesis_service",
        default_target="CN_A_SHARE_MACRO",
    ),
    "decision_synthesizer": ExternalComputeDemoEntry(
        agent_id="decision_synthesizer",
        base_url=_demo_base_url("decision_synthesizer", "http://127.0.0.1:10025"),
        compute_path=COMPUTE_PATH,
        expected_payload=DECISION_RESULT_SCHEMA_VERSION,
        dimension="l4",
        external_agent_id="l4_decision_synthesizer",
    ),
    "report_generator": ExternalComputeDemoEntry(
        agent_id="report_generator",
        base_url=_demo_base_url("report_generator", "http://127.0.0.1:10026"),
        compute_path=COMPUTE_PATH,
        expected_payload=REPORT_RESULT_SCHEMA_VERSION,
        dimension="l4",
        external_agent_id="l4_report_generator",
        timeout_seconds=120.0,
    ),
}


__all__ = ["DEMO_COMPUTE_SERVICE_REGISTRY"]
