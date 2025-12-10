from react_agent import prompts


def test_router_prompt_format_has_no_extra_placeholders() -> None:
    """Ensure ROUTER_SYSTEM_PROMPT.format only needs system_time."""
    rendered = prompts.ROUTER_SYSTEM_PROMPT.format(system_time="2025-01-01T00:00:00Z")
    assert '"layers"' in rendered
    assert "{system_time}" not in rendered
