import types

import pytest

from react_agent.external_http_agents import EXTERNAL_HTTP_AGENT_CONFIG
from react_agent.generic_agent import build_generic_agent_tool
from react_agent.graph_bootstrap import (
    bootstrap_legacy_agent_runtime,
    build_legacy_node_registry,
)
from react_agent.legacy_agent_registry import (
    AGENT_METADATA,
    AGENT_TOOLS,
    AgentMetadata,
    register_agent,
)

P0_EXTERNAL_AGENT_IDS = {
    "a16_ml_valuation": "valuation_ml",
    "a17_traditional_valuation": "valuation_traditional",
    "a18_meta_valuation": "valuation_meta",
}

P1A_EXTERNAL_AGENT_IDS = {
    "a22_financial_data_service": "financial_data_service",
    "a03_macro_industry_research": "macro_analysis",
    "a04_commodity_hedging": "price_influence_agent",
    "a06_financial_statement_analysis": "financial_report_agent",
    "a10_stock_technical_analysis": "technical_stock",
    "a11_index_technical_analysis": "valuation_index",
    "a12_research_synthesis": "analyst_research",
    "a14_ipo_investor_behavior": "ipo_investor_behavior",
    "a23_crash_risk": "crash_risk",
    "a26_composite_valuation": "composite_valuation",
}

HELD_OR_FUTURE_AGENT_IDS = [
    "a27_risk_constraint",
    "a13_fund_manager_behavior",
    "a19_risk_identification",
    "a20_compliance_review",
    "a24_financial_fraud_risk",
    "a15_entity_relation_extraction",
    "a07_macro_sentiment",
    "a08_industry_hotspot",
    "a09_company_sentiment_radar",
    "a28_composite_sentiment",
]

DISABLED_RETAINED_METADATA_IDS = [
    "a05_annual_report_analysis",
    "a21_portfolio_manager",
]


@pytest.fixture(autouse=True)
def legacy_registry_boundary():
    AGENT_METADATA.clear()
    AGENT_TOOLS.clear()
    bootstrap_legacy_agent_runtime()
    yield
    AGENT_METADATA.clear()
    AGENT_TOOLS.clear()


def test_config_agents_default_to_llm_tools(monkeypatch) -> None:
    """Config agents should register with LLM tools (non-stub) when description exists."""

    class FakeModel:
        tool_calls = []

        async def ainvoke(self, msgs):
            return types.SimpleNamespace(content='{"analysis":"ok","key_points":[],"evidence":[],"confidence":0.7}')

        def bind_tools(self, tool_list):
            return self

    # Monkeypatch to avoid real LLM calls.
    monkeypatch.setattr("react_agent.default_agents.load_chat_model", lambda name: FakeModel())
    monkeypatch.setattr("react_agent.utils.load_chat_model", lambda name: FakeModel())

    tool = AGENT_TOOLS.get("a07_macro_sentiment")
    assert tool is not None
    assert not getattr(tool, "is_stub", False)
    assert not getattr(tool, "is_external_http_wrapper", False)
    assert not getattr(tool, "is_external_valuation_wrapper", False)


def test_external_http_agents_are_not_default_llm_tools() -> None:
    expected = {**P0_EXTERNAL_AGENT_IDS, **P1A_EXTERNAL_AGENT_IDS}
    assert set(EXTERNAL_HTTP_AGENT_CONFIG) == set(expected)
    for agent_id, external_agent_id in expected.items():
        tool = AGENT_TOOLS.get(agent_id)
        assert tool is not None
        assert getattr(tool, "is_external_http_wrapper", False)
        assert getattr(tool, "external_agent_id", "") == external_agent_id
        assert not getattr(tool, "is_stub", False)
        if agent_id in P0_EXTERNAL_AGENT_IDS:
            assert getattr(tool, "is_external_valuation_wrapper", False)
        else:
            assert not getattr(tool, "is_external_valuation_wrapper", False)


def test_p0_valuation_agents_remain_generic_http_wrappers() -> None:
    for agent_id, external_agent_id in P0_EXTERNAL_AGENT_IDS.items():
        tool = AGENT_TOOLS.get(agent_id)
        assert tool is not None
        assert getattr(tool, "is_external_http_wrapper", False)
        assert getattr(tool, "is_external_valuation_wrapper", False)
        assert getattr(tool, "external_agent_id", "") == external_agent_id


def test_p1a_agents_register_as_generic_http_wrappers() -> None:
    for agent_id, external_agent_id in P1A_EXTERNAL_AGENT_IDS.items():
        tool = AGENT_TOOLS.get(agent_id)
        assert tool is not None
        assert getattr(tool, "is_external_http_wrapper", False)
        assert not getattr(tool, "is_external_valuation_wrapper", False)
        assert getattr(tool, "external_agent_id", "") == external_agent_id


def test_held_or_future_agents_still_use_default_llm_tools() -> None:
    for agent_id in HELD_OR_FUTURE_AGENT_IDS:
        tool = AGENT_TOOLS.get(agent_id)
        assert tool is not None
        assert not getattr(tool, "is_external_http_wrapper", False)
        assert not getattr(tool, "is_external_valuation_wrapper", False)
        assert not getattr(tool, "is_stub", False)
        assert getattr(tool, "is_llm_search_placeholder", False)
        assert getattr(tool, "runtime_path", "") == "INTERNAL_LLM_SEARCH_PLACEHOLDER"


def test_disabled_retained_metadata_is_not_callable() -> None:
    _agent_ids, node_names = build_legacy_node_registry(include_disabled=False)
    for agent_id in DISABLED_RETAINED_METADATA_IDS:
        assert agent_id in AGENT_METADATA
        assert AGENT_METADATA[agent_id].default_enabled is False
        assert agent_id not in AGENT_TOOLS
        assert agent_id not in node_names


def test_special_and_removed_agents_are_not_generic_external_wrappers() -> None:
    assert "a02_task_router" not in AGENT_METADATA
    assert "a02_task_router" not in AGENT_TOOLS
    for agent_id in ["a01_cio_orchestrator", "a25_report_center"]:
        tool = AGENT_TOOLS.get(agent_id)
        assert tool is not None
        assert not getattr(tool, "is_external_http_wrapper", False)


def test_stub_fallback_when_description_missing(monkeypatch) -> None:
    """If description is empty, fallback to stub."""
    previous_metadata = dict(AGENT_METADATA)
    previous_tools = dict(AGENT_TOOLS)
    try:
        # Register a temp agent with empty description.
        meta = AgentMetadata(
            id="tmp_no_desc",
            name="tmp",
            description="",
            capabilities=[],
            input_type="",
            latency_level="",
            cost_level="",
            version="",
            layer="L2",
        )
        tool = build_generic_agent_tool(meta.id, meta.description)
        register_agent(meta, tool)
        assert getattr(AGENT_TOOLS[meta.id], "is_stub", False)
    finally:
        AGENT_METADATA.clear()
        AGENT_METADATA.update(previous_metadata)
        AGENT_TOOLS.clear()
        AGENT_TOOLS.update(previous_tools)
