from react_agent import prompts


def test_analyst_prompt_format_safe() -> None:
    rendered = prompts.ANALYST_SYSTEM_PROMPT.format(profile="TEST_PROFILE")
    assert "TEST_PROFILE" in rendered
    # JSON field names should be present literally.
    for field in ["\"analysis\"", "\"key_points\"", "\"evidence\"", "\"confidence\""]:
        assert field in rendered
    # {profile} should be substituted.
    assert "{profile}" not in rendered
