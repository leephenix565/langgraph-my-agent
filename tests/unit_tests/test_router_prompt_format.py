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
