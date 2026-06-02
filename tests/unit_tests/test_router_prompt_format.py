from react_agent import prompts


def _render_router_prompt() -> str:
    return prompts.ROUTER_SYSTEM_PROMPT.format(
        system_time="2025-01-01T00:00:00Z",
        agent_catalog="{}",
    )


def test_router_prompt_format_has_no_extra_placeholders() -> None:
    """Ensure ROUTER_SYSTEM_PROMPT.format only needs system_time and agent_catalog."""
    rendered = _render_router_prompt()
    assert '"layers"' in rendered
    assert "{system_time}" not in rendered


def test_router_prompt_contains_single_intent_minimum_sufficient_guidance() -> None:
    rendered = _render_router_prompt()
    assert "minimum sufficient agents" in rendered
    assert "single-intent question" in rendered
    assert "exactly one primary functional agent" in rendered
    assert "primary functional agent may live in L2 or L3" in rendered
    assert "selecting only a01_cio_orchestrator and/or a25_report_center is not sufficient" in rendered


def test_router_prompt_contains_explicit_exclusion_guidance() -> None:
    rendered = _render_router_prompt()
    assert "Respect explicit exclusions" in rendered
    assert "do not call" in rendered
    assert "不要调用" in rendered
    assert "do not select those agents" in rendered


def test_router_prompt_contains_a22_data_service_caution() -> None:
    rendered = _render_router_prompt()
    assert "a22_financial_data_service" in rendered
    assert "general analysis questions" in rendered
    assert "raw data retrieval" in rendered
    assert "database/API query" in rendered


def test_router_prompt_does_not_encourage_broad_l2_selection() -> None:
    rendered = _render_router_prompt()
    assert "L2 usually 2-5" not in rendered
    assert "usually 2-5" not in rendered
    assert "first 5" not in rendered
    assert "first five" not in rendered


def test_router_prompt_contains_single_intent_domain_routing_guide() -> None:
    rendered = _render_router_prompt()
    assert "Single-intent routing guide" in rendered
    assert "a03_macro_industry_research" in rendered
    assert "a04_commodity_hedging" in rendered
    assert "a06_financial_statement_analysis" in rendered
    assert "a23_crash_risk" in rendered
    assert "商品定价" in rendered
    assert "财务报表" in rendered
    assert "股价崩盘风险" in rendered


def test_router_prompt_limits_a04_to_pricing_influence_boundary() -> None:
    rendered = _render_router_prompt()
    old_display_name = "大宗商品价格分析" + "与套期保值智能体"
    assert old_display_name not in rendered
    assert "Commodity boundary rule" in rendered
    assert "商品定价影响力" in rendered
    assert "期货市场影响力" in rendered
    assert "境内外定价关系" in rendered
    assert "非实时走势预测" in rendered
    assert "非交易建议" in rendered
    assert "非投资预测" in rendered
    assert "do not use a04 as the sole prediction tool" in rendered


def test_router_prompt_keeps_crash_risk_from_auto_financial_analysis() -> None:
    rendered = _render_router_prompt()
    assert "Risk subtype rule" in rendered
    assert "do not leave the functional selection empty" in rendered
    assert "Exclusions of financial statements" in rendered
    assert "apply to a06_financial_statement_analysis, not to a23_crash_risk" in rendered
    assert "Do not add a06 merely because crash-risk models may use financial variables" in rendered
    assert "select a06 only when the user explicitly requests financial statements" in rendered
    assert 'L2 selected ["a23_crash_risk"]' in rendered
    assert "financial, market, and governance variables are used for crash-risk analysis" in rendered
