import json

from react_agent import prompts
from react_agent.graph import _build_agent_catalog


def _render_router_prompt(agent_catalog: object | None = None) -> str:
    catalog = "{}" if agent_catalog is None else json.dumps(agent_catalog, ensure_ascii=False)
    return prompts.ROUTER_SYSTEM_PROMPT.format(
        system_time="2025-01-01T00:00:00Z",
        agent_catalog=catalog,
    )


def _catalog_cards_by_id() -> dict[str, dict]:
    cards: dict[str, dict] = {}
    for layer_cards in _build_agent_catalog().values():
        for card in layer_cards:
            cards[card["id"]] = card
    return cards


def test_router_prompt_format_has_no_extra_placeholders() -> None:
    """Ensure ROUTER_SYSTEM_PROMPT.format only needs system_time and agent_catalog."""
    rendered = _render_router_prompt()
    assert '"layers"' in rendered
    assert "{system_time}" not in rendered
    assert "{agent_catalog}" not in rendered


def test_router_prompt_is_profile_driven() -> None:
    rendered = _render_router_prompt()
    assert "Available agent profile catalog by layer" in rendered
    assert "Every selected agent must have clear support from its profile card" in rendered
    assert "Read each agent card fields" in rendered
    assert "profile_summary" in rendered
    assert "when_to_use" in rendered
    assert "when_not_to_use" in rendered
    assert "required_inputs" in rendered
    assert "missing_input_policy" in rendered
    assert "Choose based on the profile" in rendered
    assert "not on historical names" in rendered


def test_router_prompt_contains_profile_exclusion_and_missing_input_guidance() -> None:
    rendered = _render_router_prompt()
    assert "Select an agent only when its when_to_use clearly matches" in rendered
    assert "covered by an agent's when_not_to_use, do not select that agent" in rendered
    assert "If required_inputs are missing" in rendered
    assert "prefer a clarification / parsing / orchestration-capable layer" in rendered
    assert "Do not choose agents merely to fill a layer or target count" in rendered


def test_router_prompt_contains_explicit_exclusion_guidance() -> None:
    rendered = _render_router_prompt()
    assert "Respect explicit exclusions" in rendered
    assert "do not call" in rendered
    assert "不要调用" in rendered
    assert "do not select those agents" in rendered


def test_router_prompt_does_not_restore_broad_or_fixed_mapping_logic() -> None:
    rendered = _render_router_prompt(_build_agent_catalog())
    forbidden = [
        "L2 usually 2-5",
        "usually 2-5",
        "first 5",
        "first five",
        "Single-intent routing guide",
        "Commodity boundary rule",
        "Risk subtype rule",
        'L2 selected ["a23_crash_risk"]',
        "Macro cycle / macro regime",
        "Commodity pricing influence / futures market influence",
        "Enterprise financial statements / financial health",
        "Stock crash risk / downside crash",
        "a02_task_router",
    ]
    for text in forbidden:
        assert text not in rendered


def test_router_catalog_cards_include_profile_fields() -> None:
    rendered = _render_router_prompt(_build_agent_catalog())
    assert '"when_to_use"' in rendered
    assert '"when_not_to_use"' in rendered
    assert '"required_inputs"' in rendered
    assert '"missing_input_policy"' in rendered


def test_mock_acceptance_catalog_supports_maotai_multi_agent_analysis() -> None:
    cards = _catalog_cards_by_id()
    for agent_id in [
        "a10_stock_technical_analysis",
        "a17_traditional_valuation",
        "a16_ml_valuation",
        "a12_research_synthesis",
    ]:
        card = cards[agent_id]
        assert card["when_to_use"]
        assert card["when_not_to_use"]
        assert card["required_inputs"]
    assert "个股" in cards["a10_stock_technical_analysis"]["when_to_use"]
    assert "传统估值" in cards["a17_traditional_valuation"]["when_to_use"]
    assert "机器学习" in cards["a16_ml_valuation"]["when_to_use"]
    assert "研报观点" in cards["a12_research_synthesis"]["when_to_use"]


def test_mock_acceptance_catalog_separates_index_and_enterprise_valuation() -> None:
    cards = _catalog_cards_by_id()
    a11 = cards["a11_index_technical_analysis"]
    assert "指数" in a11["when_to_use"]
    assert "估值百分位" in a11["when_to_use"]
    assert "市场情绪" in a11["profile_summary"]

    for agent_id in [
        "a16_ml_valuation",
        "a17_traditional_valuation",
        "a18_meta_valuation",
    ]:
        assert "股票指数估值" in cards[agent_id]["when_not_to_use"]
        assert "市场情绪" in cards[agent_id]["when_not_to_use"]


def test_mock_acceptance_catalog_separates_valuation_methods() -> None:
    cards = _catalog_cards_by_id()
    assert "DCF" in cards["a17_traditional_valuation"]["when_to_use"]
    assert "传统估值" in cards["a16_ml_valuation"]["when_not_to_use"]
    assert "传统 DCF" in cards["a18_meta_valuation"]["when_not_to_use"]


def test_mock_acceptance_catalog_has_company_sentiment_boundary() -> None:
    cards = _catalog_cards_by_id()
    sentiment = cards["a09_company_sentiment_radar"]
    assert "企业舆情" in sentiment["name"]
    assert "舆情分析" in sentiment["when_to_use"]
    assert "估值" not in sentiment["when_to_use"]
    assert "技术" not in sentiment["when_to_use"]
