from dataclasses import replace
import inspect

from react_agent import router_provider
from react_agent.router_provider import (
    RouterProviderInvocationOptions,
    RouterProviderPolicy,
    build_default_router_provider_policy,
    build_router_provider_artifact,
    build_router_provider_factory_result,
    router_provider_preflight,
    router_provider_required_env_var_names,
    router_provider_unsafe_scan,
    sanitize_router_provider_artifact,
)


def _authorized_policy(**overrides):
    options = overrides.pop("options", RouterProviderInvocationOptions())
    return RouterProviderPolicy(
        real_provider_authorized=True,
        env_value_access_authorized=True,
        provider_call_authorized=True,
        options=options,
        **overrides,
    )


def test_router_only_provider_factory_source_has_no_live_provider_paths() -> None:
    source = inspect.getsource(router_provider)

    assert "load_chat_model" not in source
    assert "ChatOpenAI" not in source
    assert "init_chat_model" not in source
    assert "os.environ" not in source
    assert "getenv" not in source


def test_default_policy_is_secret_free_and_fail_closed() -> None:
    policy = build_default_router_provider_policy()

    assert policy.real_provider_authorized is False
    assert policy.env_value_access_authorized is False
    assert policy.provider_call_authorized is False
    assert router_provider_required_env_var_names(policy) == (
        "ROUTER_MODEL",
        "ROUTER_OPENAI_BASE_URL",
        "ROUTER_OPENAI_API_KEY",
    )
    result = router_provider_preflight(
        policy,
        selected_routing_enabled=True,
        llm_dimension_router_enabled=True,
    )
    assert result.ready is False
    assert result.reason_code == "real_provider_not_authorized"
    assert "api_key_env_var_name" in result.policy_summary
    assert "api_key_value" not in result.policy_summary


def test_factory_result_never_creates_client_even_when_preflight_ready() -> None:
    result = build_router_provider_factory_result(
        _authorized_policy(),
        selected_routing_enabled=True,
        llm_dimension_router_enabled=True,
    )

    assert result.preflight.ready is True
    assert result.preflight.reason_code == "ready_for_single_call_dry_run"
    assert result.client_available is False
    assert result.client_created is False
    assert result.reason_code == "real_provider_client_creation_deferred_until_m1f"


def test_preflight_requires_selected_routing_and_router_flag() -> None:
    policy = _authorized_policy()

    assert (
        router_provider_preflight(
            policy,
            selected_routing_enabled=False,
            llm_dimension_router_enabled=True,
        ).reason_code
        == "selected_routing_disabled"
    )
    assert (
        router_provider_preflight(
            policy,
            selected_routing_enabled=True,
            llm_dimension_router_enabled=False,
        ).reason_code
        == "llm_dimension_router_disabled"
    )


def test_preflight_authorization_fail_closed_cases() -> None:
    base = _authorized_policy()
    cases = [
        (replace(base, real_provider_authorized=False), "real_provider_not_authorized"),
        (replace(base, env_value_access_authorized=False), "env_value_access_not_authorized"),
        (replace(base, provider_call_authorized=False), "provider_call_not_authorized"),
    ]

    for policy, reason in cases:
        result = router_provider_preflight(
            policy,
            selected_routing_enabled=True,
            llm_dimension_router_enabled=True,
        )
        assert result.ready is False
        assert result.reason_code == reason


def test_preflight_invocation_policy_fail_closed_cases() -> None:
    cases = [
        (
            RouterProviderInvocationOptions(call_cap=2),
            "call_cap_exceeds_limit",
        ),
        (
            RouterProviderInvocationOptions(call_cap=0),
            "call_cap_missing",
        ),
        (
            RouterProviderInvocationOptions(streaming=True),
            "streaming_not_allowed",
        ),
        (
            RouterProviderInvocationOptions(retry_count=1),
            "retry_not_allowed",
        ),
        (
            RouterProviderInvocationOptions(max_tokens=221),
            "max_tokens_exceeds_limit",
        ),
        (
            RouterProviderInvocationOptions(timeout_seconds=8.1),
            "timeout_exceeds_limit",
        ),
        (
            RouterProviderInvocationOptions(raw_response_retention=True),
            "raw_response_retention_not_allowed",
        ),
        (
            RouterProviderInvocationOptions(prompt_retention=True),
            "prompt_retention_not_allowed",
        ),
        (
            RouterProviderInvocationOptions(messages_retention=True),
            "messages_retention_not_allowed",
        ),
        (
            RouterProviderInvocationOptions(artifact_whitelist_enabled=False),
            "artifact_whitelist_disabled",
        ),
    ]

    for options, reason in cases:
        result = router_provider_preflight(
            _authorized_policy(options=options),
            selected_routing_enabled=True,
            llm_dimension_router_enabled=True,
        )
        assert result.ready is False
        assert result.reason_code == reason


def test_preflight_pass_ready_criteria_are_bounded() -> None:
    result = router_provider_preflight(
        _authorized_policy(),
        selected_routing_enabled=True,
        llm_dimension_router_enabled=True,
    )

    assert result.ready is True
    assert result.reason_code == "ready_for_single_call_dry_run"
    assert result.policy_summary["call_cap"] == 1
    assert result.policy_summary["timeout_seconds"] == 8.0
    assert result.policy_summary["max_tokens"] == 220
    assert result.policy_summary["retry_count"] == 0
    assert result.policy_summary["streaming"] is False


def test_sanitized_artifact_uses_exact_whitelist_and_forces_no_retention() -> None:
    raw = {
        "phase": "m1f0",
        "provider_router_enabled": True,
        "provider_router_invoked": True,
        "provider_router_mode": "real",
        "provider_router_parse_ok": True,
        "selected_dimensions": ["value", "credit", "risk", "value"],
        "route_confidence": 0.8,
        "fallback_reason_code": "ok",
        "provider_error_code": "",
        "latency_ms": 100,
        "call_count": 1,
        "timeout_seconds": 8.0,
        "max_tokens": 220,
        "retry_count": 0,
        "streaming": False,
        "raw_response_retained": True,
        "prompt_retained": True,
        "messages_retained": True,
        "raw_response": "secret raw text",
        "raw_response_hash": "a" * 64,
        "prompt": "system prompt",
        "messages": ["message"],
        "endpoint": "http://example.invalid",
        "base_url": "https://example.invalid",
        "api_key": "secret",
        "selected_agents": ["value_traditional_valuation"],
        "runtime_bindings": {"route_planner": "x"},
        "dag_steps": [],
    }

    clean = sanitize_router_provider_artifact(raw)

    assert set(clean) <= router_provider.ROUTER_PROVIDER_ARTIFACT_ALLOWED_FIELDS
    assert clean["selected_dimensions"] == ["value", "risk"]
    assert clean["raw_response_retained"] is False
    assert clean["prompt_retained"] is False
    assert clean["messages_retained"] is False
    for forbidden in (
        "raw_response",
        "raw_response_hash",
        "prompt",
        "messages",
        "endpoint",
        "base_url",
        "api_key",
        "selected_agents",
        "runtime_bindings",
        "dag_steps",
    ):
        assert forbidden not in clean


def test_unsafe_scan_catches_forbidden_keys_and_values() -> None:
    metadata = {
        "provider_router_enabled": True,
        "raw_response": "BEGIN PROMPT\nsecret",
        "raw_response_hash": "a" * 64,
        "endpoint": "/v1/agent/invoke",
        "nested": {"api_key": "secret", "traceback": "Traceback"},
        "selected_agents": ["value_traditional_valuation"],
        "runtime_bindings": {"route_planner": "x"},
        "dag_steps": [],
        "chain_of_thought": "hidden",
    }

    scan = router_provider_unsafe_scan(metadata)

    assert scan["pass"] is False
    findings = set(scan["findings"])
    assert "forbidden_key:raw_response" in findings
    assert "forbidden_key:raw_response_hash" in findings
    assert "forbidden_key:endpoint" in findings
    assert "forbidden_key:api_key" in findings
    assert "forbidden_key:traceback" in findings
    assert "forbidden_key:selected_agents" in findings
    assert "forbidden_key:runtime_bindings" in findings
    assert "forbidden_key:dag_steps" in findings
    assert "forbidden_key:chain_of_thought" in findings
    assert "forbidden_value:/v1/agent/invoke" in findings
    assert "forbidden_value:hex_surrogate" in findings


def test_clean_router_provider_artifact_passes_unsafe_scan() -> None:
    clean = build_router_provider_artifact(
        {
            "phase": "m1f0",
            "provider_router_enabled": True,
            "provider_router_invoked": False,
            "provider_router_mode": "preflight",
            "provider_router_parse_ok": False,
            "selected_dimensions": ["macro"],
            "fallback_reason_code": "real_provider_not_authorized",
            "provider_error_code": "",
            "call_count": 0,
            "timeout_seconds": 8.0,
            "max_tokens": 220,
            "retry_count": 0,
            "streaming": False,
        }
    )

    assert clean["unsafe_scan_pass"] is True
    assert router_provider_unsafe_scan(clean)["pass"] is True
    assert clean["raw_response_retained"] is False
    assert clean["prompt_retained"] is False
    assert clean["messages_retained"] is False


def test_build_artifact_marks_source_unsafe_but_omits_forbidden_fields() -> None:
    artifact = build_router_provider_artifact(
        {
            "phase": "m1f0",
            "provider_router_enabled": True,
            "raw_response": "raw_response secret",
            "raw_response_hash": "b" * 64,
            "prompt": "system prompt",
        }
    )

    assert artifact["unsafe_scan_pass"] is False
    assert "raw_response" not in artifact
    assert "raw_response_hash" not in artifact
    assert "prompt" not in artifact
    assert artifact["raw_response_retained"] is False
