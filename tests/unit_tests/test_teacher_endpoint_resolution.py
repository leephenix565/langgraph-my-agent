from tools.generate_a01_teacher_contracts import _resolve_endpoint


def test_resolve_endpoint_base_url_root() -> None:
    host, path, scheme = _resolve_endpoint("https://api.deepseek.com")
    assert scheme == "https"
    assert host == "api.deepseek.com"
    assert path == "/chat/completions"


def test_resolve_endpoint_base_url_v1() -> None:
    host, path, scheme = _resolve_endpoint("https://api.deepseek.com/v1")
    assert scheme == "https"
    assert host == "api.deepseek.com"
    assert path == "/chat/completions"


def test_resolve_endpoint_base_url_root_trailing_slash() -> None:
    host, path, scheme = _resolve_endpoint("https://api.deepseek.com/")
    assert scheme == "https"
    assert host == "api.deepseek.com"
    assert path == "/chat/completions"


def test_resolve_endpoint_base_url_no_scheme() -> None:
    host, path, scheme = _resolve_endpoint("api.deepseek.com")
    assert scheme == "https"
    assert host == "api.deepseek.com"
    assert path == "/chat/completions"
