from react_agent.graph import _normalize_mode


def test_normalize_mode_single_ok() -> None:
    assert _normalize_mode("Star") == "Star"
    assert _normalize_mode("chain") == "Chain"


def test_normalize_mode_joined_string() -> None:
    # Comma-joined should pick the first valid token and not raise.
    assert _normalize_mode("Star,Chain,Debate,Tree") == "Star"
    # Space or semicolon separated also tolerated.
    assert _normalize_mode("Debate Tree") == "Debate"
    assert _normalize_mode("Tree;Star") == "Tree"


def test_normalize_mode_invalid_fallback() -> None:
    assert _normalize_mode("invalid") == "Star"
    assert _normalize_mode("") == "Star"
