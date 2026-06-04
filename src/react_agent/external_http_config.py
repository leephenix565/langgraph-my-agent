"""Configuration-only metadata for retained external HTTP wrapper candidates."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ExternalHTTPAgentConfig:
    """Runtime config for one table-driven external HTTP agent."""

    agent_id: str
    external_agent_id: str
    env_var: str
    default_url: str


EXTERNAL_HTTP_AGENT_CONFIG: dict[str, ExternalHTTPAgentConfig] = {
    "a03_macro_industry_research": ExternalHTTPAgentConfig(
        agent_id="a03_macro_industry_research",
        external_agent_id="macro_analysis",
        env_var="MACRO_ANALYSIS_AGENT_URL",
        default_url="http://222.73.85.26:10014/v1/agent/invoke",
    ),
    "a04_commodity_hedging": ExternalHTTPAgentConfig(
        agent_id="a04_commodity_hedging",
        external_agent_id="price_influence_agent",
        env_var="COMMODITY_PRICING_AGENT_URL",
        default_url="http://222.73.85.26:10004/v1/agent/invoke",
    ),
    "a06_financial_statement_analysis": ExternalHTTPAgentConfig(
        agent_id="a06_financial_statement_analysis",
        external_agent_id="financial_report_agent",
        env_var="ENTERPRISE_FINANCIAL_ANALYSIS_AGENT_URL",
        default_url="http://222.73.85.26:10005/v1/agent/invoke",
    ),
    "a10_stock_technical_analysis": ExternalHTTPAgentConfig(
        agent_id="a10_stock_technical_analysis",
        external_agent_id="technical_stock",
        env_var="STOCK_TECHNICAL_ANALYSIS_AGENT_URL",
        default_url="http://222.73.85.26:10009/v1/agent/invoke",
    ),
    "a11_index_technical_analysis": ExternalHTTPAgentConfig(
        agent_id="a11_index_technical_analysis",
        external_agent_id="valuation_index",
        env_var="INDEX_VALUATION_AGENT_URL",
        default_url="http://222.73.85.26:10003/v1/agent/invoke",
    ),
    "a12_research_synthesis": ExternalHTTPAgentConfig(
        agent_id="a12_research_synthesis",
        external_agent_id="analyst_research",
        env_var="RESEARCH_SYNTHESIS_AGENT_URL",
        default_url="http://222.73.85.26:10006/v1/agent/invoke",
    ),
    "a14_ipo_investor_behavior": ExternalHTTPAgentConfig(
        agent_id="a14_ipo_investor_behavior",
        external_agent_id="ipo_investor_behavior",
        env_var="IPO_INVESTOR_BEHAVIOR_AGENT_URL",
        default_url="http://222.73.85.26:10008/v1/agent/invoke",
    ),
    "a16_ml_valuation": ExternalHTTPAgentConfig(
        agent_id="a16_ml_valuation",
        external_agent_id="valuation_ml",
        env_var="VALUATION_ML_AGENT_URL",
        default_url="http://222.73.85.26:10001/v1/agent/invoke",
    ),
    "a17_traditional_valuation": ExternalHTTPAgentConfig(
        agent_id="a17_traditional_valuation",
        external_agent_id="valuation_traditional",
        env_var="VALUATION_TRADITIONAL_AGENT_URL",
        default_url="http://222.73.85.26:10000/v1/agent/invoke",
    ),
    "a18_meta_valuation": ExternalHTTPAgentConfig(
        agent_id="a18_meta_valuation",
        external_agent_id="valuation_meta",
        env_var="VALUATION_META_AGENT_URL",
        default_url="http://222.73.85.26:10002/v1/agent/invoke",
    ),
    "a22_financial_data_service": ExternalHTTPAgentConfig(
        agent_id="a22_financial_data_service",
        external_agent_id="financial_data_service",
        env_var="FINANCIAL_DATA_AGENT_URL",
        default_url="http://222.73.85.26:11000/v1/agent/invoke",
    ),
    "a23_crash_risk": ExternalHTTPAgentConfig(
        agent_id="a23_crash_risk",
        external_agent_id="crash_risk",
        env_var="CRASH_RISK_AGENT_URL",
        default_url="http://222.73.85.26:10012/v1/agent/invoke",
    ),
    "a26_composite_valuation": ExternalHTTPAgentConfig(
        agent_id="a26_composite_valuation",
        external_agent_id="composite_valuation",
        env_var="COMPOSITE_VALUATION_AGENT_URL",
        default_url="http://222.73.85.26:10015/v1/agent/invoke",
    ),
}


def external_http_agent_ids() -> set[str]:
    """Return main-system ids configured for external HTTP wrappers."""
    return set(EXTERNAL_HTTP_AGENT_CONFIG)


__all__ = [
    "EXTERNAL_HTTP_AGENT_CONFIG",
    "ExternalHTTPAgentConfig",
    "external_http_agent_ids",
]
