import inspect
import json
from dataclasses import replace

from react_agent import router_provider
from react_agent.fixed_dag_contracts import (
    DIMENSION_GROUPS,
    compile_selected_fixed_dag_plan,
    validate_selected_fixed_dag_plan,
)
from react_agent.router_parse import parse_dimension_route_intent_json
from react_agent.router_provider import (
    ROUTER_PROVIDER_ROUTE_INTENT_MESSAGE_CONTRACT_VERSION,
    ROUTER_PROVIDER_ROUTE_INTENT_MESSAGE_LAYOUT,
    ROUTER_PROVIDER_ROUTE_INTENT_SCHEMA_NAME,
    RouterProviderInvocationOptions,
    RouterProviderPolicy,
    build_default_router_provider_policy,
    build_openai_compatible_chat_completions_url,
    build_router_provider_artifact,
    build_router_provider_factory_result,
    build_router_provider_request_contract,
    build_router_provider_route_intent_draft,
    build_router_provider_route_intent_messages,
    normalize_router_provider_model_for_openai_compatible_api,
    router_provider_preflight,
    router_provider_required_env_var_names,
    router_provider_unsafe_scan,
    sanitize_router_provider_artifact,
    suggest_router_provider_dimensions,
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


def test_openai_compatible_model_normalization_strips_known_provider_prefix() -> None:
    result = normalize_router_provider_model_for_openai_compatible_api(
        "deepseek/deepseek-chat"
    )

    assert result.provider_api_model == "deepseek-chat"
    assert result.normalized is True
    assert result.reason_code == "deepseek_provider_prefix_removed"


def test_model_normalization_keeps_api_model_ids_and_unknown_prefixes() -> None:
    plain = normalize_router_provider_model_for_openai_compatible_api("deepseek-chat")
    unknown = normalize_router_provider_model_for_openai_compatible_api(
        "vendor/custom-model"
    )
    url_like = normalize_router_provider_model_for_openai_compatible_api(
        "https://example.invalid/model"
    )

    assert plain.provider_api_model == "deepseek-chat"
    assert plain.normalized is False
    assert plain.reason_code == "model_passthrough"
    assert unknown.provider_api_model == "vendor/custom-model"
    assert unknown.normalized is False
    assert unknown.reason_code == "provider_prefix_not_normalized"
    assert url_like.provider_api_model == "https://example.invalid/model"
    assert url_like.normalized is False
    assert url_like.reason_code == "model_passthrough"


def test_router_provider_request_contract_uses_json_mode_without_sensitive_fields() -> None:
    contract = build_router_provider_request_contract()

    assert contract["request_contract_version"] == "router_dimension_json_v1"
    assert (
        contract["route_intent_message_contract_version"]
        == ROUTER_PROVIDER_ROUTE_INTENT_MESSAGE_CONTRACT_VERSION
    )
    assert contract["route_intent_message_layout"] == ROUTER_PROVIDER_ROUTE_INTENT_MESSAGE_LAYOUT
    assert contract["route_intent_schema_name"] == ROUTER_PROVIDER_ROUTE_INTENT_SCHEMA_NAME
    assert contract["strict_route_intent_json_schema"] is True
    assert contract["allowed_dimensions"] == ["value", "market", "risk", "macro"]
    assert contract["response_format_json_object"] is True
    assert contract["response_format"] == {"type": "json_object"}
    assert contract["max_tokens"] == 220
    assert contract["timeout_seconds"] == 8.0
    assert contract["retry_count"] == 0
    assert contract["streaming"] is False
    assert contract["raw_response_retained"] is False
    assert contract["prompt_retained"] is False
    assert contract["messages_retained"] is False
    for forbidden in (
        "prompt",
        "messages",
        "endpoint",
        "base_url",
        "api_key",
        "raw_response",
        "raw_response_hash",
    ):
        assert forbidden not in contract


def test_router_provider_route_intent_messages_are_strict_json_contract() -> None:
    messages = build_router_provider_route_intent_messages(
        "请从估值、市场、风险和宏观角度分析贵州茅台 600519.SH 当前是否值得关注。"
    )

    assert [message["role"] for message in messages] == ["user"]
    joined = "\n".join(message["content"] for message in messages)
    assert "Return exactly this JSON object and nothing else." in joined
    assert "first character must be {" in joined
    assert "last character must be }" in joined
    assert "route_intent_v1" in joined
    assert '"task_type":"general"' in joined
    assert (
        '"selected_dimensions":["value","market","risk","macro"]'
        in joined
    )
    assert "markdown" in joined
    assert "api_key" not in joined.lower()
    assert "bearer" not in joined.lower()


def test_router_provider_route_intent_draft_parses_for_explicit_dimensions() -> None:
    draft = build_router_provider_route_intent_draft(
        "请从估值、市场、风险和宏观角度分析贵州茅台 600519.SH 当前是否值得关注。"
    )
    intent, stats = parse_dimension_route_intent_json(
        json.dumps(draft, ensure_ascii=False),
        question="请从估值、市场、风险和宏观角度分析贵州茅台。",
    )

    assert draft["task_type"] == "general"
    assert "selected_agents" not in draft
    assert stats["parse_ok"] is True
    assert stats["used_fallback"] is False
    assert intent["selected_dimensions"] == ["value", "market", "risk", "macro"]
    assert intent["route_confidence"] == 0.95


def test_router_provider_focused_dimension_drafts_compile_without_risk() -> None:
    cases = (
        (
            "请只从估值角度判断贵州茅台是否被高估。",
            ["value"],
            "value_composite",
        ),
        (
            "请只从价格走势、资金流和市场情绪角度分析贵州茅台。",
            ["market"],
            "market_composite",
        ),
    )

    for question, expected_dimensions, composite_id in cases:
        draft = build_router_provider_route_intent_draft(question)
        intent, stats = parse_dimension_route_intent_json(
            json.dumps(draft, ensure_ascii=False),
            question=question,
        )
        plan = compile_selected_fixed_dag_plan(
            intent,
            user_text=question,
            as_of="2026-06-28",
        )
        valid, reason = validate_selected_fixed_dag_plan(plan)

        assert draft["task_type"] == "general"
        assert "selected_agents" not in draft
        assert stats["parse_ok"] is True
        assert intent["selected_dimensions"] == expected_dimensions
        assert valid, reason
        assert plan["selected_dimensions"] == expected_dimensions
        assert plan["dimension_groups"][expected_dimensions[0]] == list(
            DIMENSION_GROUPS[expected_dimensions[0]]
        )
        assert composite_id in plan["target_agent_ids"]
        assert "decision_synthesizer" in plan["target_agent_ids"]
        assert "report_generator" in plan["target_agent_ids"]
        assert "risk_identification" not in plan["target_agent_ids"]


def test_router_provider_dimension_hint_detects_explicit_dimensions() -> None:
    assert suggest_router_provider_dimensions(
        "请从估值、市场、风险和宏观角度分析贵州茅台。"
    ) == ("value", "market", "risk", "macro")
    assert suggest_router_provider_dimensions("只看风险和宏观环境。") == (
        "risk",
        "macro",
    )


def test_router_provider_route_intent_messages_are_not_artifact_safe_if_retained() -> None:
    messages = build_router_provider_route_intent_messages("route the request")

    clean = build_router_provider_artifact(
        {
            "phase": "m1f7",
            "provider_router_invoked": True,
            "provider_router_parse_ok": True,
            "messages": messages,
            "prompt_retained": True,
            "messages_retained": True,
            "raw_response_retained": True,
        }
    )

    assert "messages" not in clean
    assert clean["prompt_retained"] is False
    assert clean["messages_retained"] is False
    assert clean["raw_response_retained"] is False
    assert clean["unsafe_scan_pass"] is False


def test_openai_compatible_chat_completions_url_appends_v1_when_missing() -> None:
    result = build_openai_compatible_chat_completions_url("https://provider.example/api")

    assert result.valid is True
    assert result.chat_completions_url == "https://provider.example/api/v1/chat/completions"
    assert result.base_url_has_v1_path is False
    assert result.chat_completions_path_normalized is True
    assert result.v1_path_added is True
    assert result.reason_code == "v1_chat_completions_path_appended"


def test_openai_compatible_chat_completions_url_uses_existing_v1_path() -> None:
    result = build_openai_compatible_chat_completions_url("https://provider.example/v1/")

    assert result.valid is True
    assert result.chat_completions_url == "https://provider.example/v1/chat/completions"
    assert result.base_url_has_v1_path is True
    assert result.chat_completions_path_normalized is True
    assert result.v1_path_added is False
    assert result.reason_code == "chat_completions_path_appended"


def test_openai_compatible_chat_completions_url_preserves_full_endpoint_path() -> None:
    result = build_openai_compatible_chat_completions_url(
        "https://provider.example/v1/chat/completions"
    )

    assert result.valid is True
    assert result.chat_completions_url == "https://provider.example/v1/chat/completions"
    assert result.chat_completions_path_normalized is True
    assert result.v1_path_added is False
    assert result.reason_code == "chat_completions_path_passthrough"


def test_openai_compatible_chat_completions_url_rejects_unsafe_shapes() -> None:
    missing = build_openai_compatible_chat_completions_url("")
    scheme = build_openai_compatible_chat_completions_url("file:///tmp/provider")
    query = build_openai_compatible_chat_completions_url(
        "https://provider.example/v1?secret=value"
    )

    assert missing.valid is False
    assert missing.reason_code == "base_url_missing"
    assert scheme.valid is False
    assert scheme.reason_code == "base_url_invalid_scheme_or_host"
    assert query.valid is False
    assert query.reason_code == "base_url_query_or_fragment_not_allowed"


def test_router_provider_contract_metadata_is_artifact_safe() -> None:
    clean = build_router_provider_artifact(
        {
            "phase": "m1f3",
            "provider_router_enabled": True,
            "provider_router_invoked": True,
            "provider_router_mode": "real_dry_run",
            "provider_router_parse_ok": True,
            "selected_dimensions": ["value", "market", "risk", "macro"],
            "fallback_reason_code": "",
            "provider_error_code": "",
            "call_count": 1,
            "timeout_seconds": 8.0,
            "max_tokens": 220,
            "retry_count": 0,
            "streaming": False,
            "model_normalized": True,
            "request_contract_version": "router_dimension_json_v1",
            "route_intent_message_contract_version": "router_route_intent_messages_v2",
            "route_intent_message_layout": "single_user_exact_json_echo",
            "route_intent_schema_name": "route_intent_v1",
            "strict_route_intent_json_schema": True,
            "allowed_dimensions": ["value", "market", "risk", "macro"],
            "response_format_json_object": True,
            "chat_completions_path_normalized": True,
            "v1_path_added": True,
            "raw_response_retained": False,
            "prompt_retained": False,
            "messages_retained": False,
        }
    )

    assert clean["unsafe_scan_pass"] is True
    assert clean["model_normalized"] is True
    assert clean["request_contract_version"] == "router_dimension_json_v1"
    assert clean["route_intent_message_contract_version"] == (
        "router_route_intent_messages_v2"
    )
    assert clean["route_intent_message_layout"] == "single_user_exact_json_echo"
    assert clean["route_intent_schema_name"] == "route_intent_v1"
    assert clean["strict_route_intent_json_schema"] is True
    assert clean["allowed_dimensions"] == ["value", "market", "risk", "macro"]
    assert clean["response_format_json_object"] is True
    assert clean["chat_completions_path_normalized"] is True
    assert clean["v1_path_added"] is True
    assert router_provider_unsafe_scan(clean)["pass"] is True


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
