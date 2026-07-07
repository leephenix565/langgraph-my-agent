"""Opt-in deployment profiles for the fixed-DAG runtime."""

from __future__ import annotations

MIDTERM_SUBSET_PROFILE = "midterm_subset"
DEPLOYMENT_PROFILE_ENV_VAR = "FIXED_DAG_DEPLOYMENT_PROFILE"

MIDTERM_SUBSET_SELECTED_DIMENSIONS: tuple[str, ...] = (
    "value",
    "market",
    "risk",
    "macro",
)

MIDTERM_SUBSET_SELECTED_L2_AGENT_IDS: tuple[str, ...] = (
    "value_traditional_valuation",
    "value_ml_valuation",
    "value_meta_valuation",
    "value_research_synthesis",
    "market_stock_technical",
    "market_capital_flow_chip",
    "macro_analysis",
    "macro_index_valuation",
    "risk_crash",
    "risk_identification",
)

MIDTERM_SUBSET_REQUIRED_DEPENDENCY_AGENT_IDS: tuple[str, ...] = (
    "route_planner",
    "financial_data_service",
    "entity_relation_extractor",
    "value_composite",
    "market_composite",
    "macro_composite",
    "risk_composite",
    "decision_synthesizer",
    "report_generator",
)

MIDTERM_SUBSET_DEFERRED_AGENT_IDS: tuple[str, ...] = (
    "market_ipo_investor_behavior",
    "market_fund_manager_behavior",
    "risk_financial_fraud",
    "risk_compliance_review",
    "sentiment_company_radar",
    "macro_commodity_pricing",
    "macro_sentiment",
    "macro_industry_hotspot",
)


def normalize_deployment_profile(value: object) -> str:
    """Return a known deployment profile id, or empty string for full-DAG default."""
    text = str(value or "").strip().lower()
    if text == MIDTERM_SUBSET_PROFILE:
        return MIDTERM_SUBSET_PROFILE
    return ""


def is_midterm_subset_profile(value: object) -> bool:
    """Whether the opt-in Topic2 midterm subset deployment profile is active."""
    return normalize_deployment_profile(value) == MIDTERM_SUBSET_PROFILE

