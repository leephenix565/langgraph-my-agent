"""Router-only provider preflight and artifact safety helpers.

This module intentionally does not create model clients, call providers, or read
environment values. It defines the fail-closed contract a future controlled
router-provider dry run must satisfy before any real provider code is allowed.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlsplit, urlunsplit

ROUTER_PROVIDER_ENV_VAR_NAMES: tuple[str, ...] = (
    "ROUTER_MODEL",
    "ROUTER_OPENAI_BASE_URL",
    "ROUTER_OPENAI_API_KEY",
)
ROUTER_PROVIDER_COMPAT_ENV_VAR_NAMES: tuple[str, ...] = (
    "MODEL",
    "OPENAI_BASE_URL",
    "OPENAI_API_KEY",
    "DEEPSEEK_BASE_URL",
    "DEEPSEEK_API_KEY",
)
ROUTER_PROVIDER_DIMENSIONS: tuple[str, ...] = ("value", "market", "risk", "macro")
ROUTER_PROVIDER_TIMEOUT_SECONDS_LIMIT = 20.0
ROUTER_PROVIDER_MAX_TOKENS_LIMIT = 220
ROUTER_PROVIDER_RETRY_COUNT_LIMIT = 2
ROUTER_PROVIDER_CALL_CAP_LIMIT = 3
ROUTER_PROVIDER_JSON_RESPONSE_FORMAT: Mapping[str, str] = {"type": "json_object"}
ROUTER_PROVIDER_REQUEST_CONTRACT_VERSION = "router_dimension_json_v1"
ROUTER_PROVIDER_ROUTE_INTENT_MESSAGE_CONTRACT_VERSION = (
    "router_route_intent_messages_v2"
)
ROUTER_PROVIDER_ROUTE_INTENT_MESSAGE_LAYOUT = "single_user_exact_json_echo"
ROUTER_PROVIDER_ROUTE_INTENT_SCHEMA_NAME = "route_intent_v1"
_OPENAI_COMPATIBLE_PROVIDER_PREFIXES: frozenset[str] = frozenset(
    {"deepseek", "openai"}
)
_MODEL_SEGMENT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,120}$")
_DIMENSION_CUE_KEYWORDS: Mapping[str, tuple[str, ...]] = {
    "value": (
        "估值",
        "价值",
        "基本面",
        "财务",
        "valuation",
        "value",
        "fundamental",
        "financial",
    ),
    "market": (
        "市场",
        "技术",
        "情绪",
        "资金",
        "股价",
        "market",
        "technical",
        "sentiment",
        "flow",
    ),
    "risk": (
        "风险",
        "下行",
        "合规",
        "欺诈",
        "暴跌",
        "risk",
        "downside",
        "compliance",
        "fraud",
    ),
    "macro": (
        "宏观",
        "政策",
        "利率",
        "行业",
        "指数",
        "macro",
        "policy",
        "rate",
        "industry",
        "index",
    ),
}

ROUTER_PROVIDER_ARTIFACT_ALLOWED_FIELDS: frozenset[str] = frozenset(
    {
        "phase",
        "provider_router_enabled",
        "provider_router_invoked",
        "provider_router_mode",
        "provider_router_parse_ok",
        "selected_dimensions",
        "route_confidence",
        "fallback_reason_code",
        "provider_error_code",
        "latency_ms",
        "call_count",
        "timeout_seconds",
        "max_tokens",
        "retry_count",
        "streaming",
        "raw_response_retained",
        "prompt_retained",
        "messages_retained",
        "unsafe_scan_pass",
        "model_normalized",
        "response_format_json_object",
        "request_contract_version",
        "route_intent_message_contract_version",
        "route_intent_message_layout",
        "route_intent_schema_name",
        "strict_route_intent_json_schema",
        "allowed_dimensions",
        "chat_completions_path_normalized",
        "v1_path_added",
    }
)
ROUTER_PROVIDER_ARTIFACT_FORBIDDEN_FIELDS: frozenset[str] = frozenset(
    {
        "raw_response",
        "raw_responses",
        "raw_provider_response",
        "response_text",
        "raw_response_hash",
        "provider_response",
        "provider_payload",
        "external_response",
        "external_payload",
        "prompt",
        "system_prompt",
        "messages",
        "input_messages",
        "endpoint",
        "endpoint_url",
        "base_url",
        "default_url",
        "env",
        "environment",
        "env_var",
        "api_key",
        "secret",
        "secrets",
        "token",
        "authorization",
        "cookie",
        "password",
        "traceback",
        "chain_of_thought",
        "chain-of-thought",
        "selected_agents",
        "runtime_bindings",
        "dag_steps",
        "depends_on",
        "hash",
        "sha",
        "sha1",
        "sha256",
        "sha512",
        "md5",
        "blake2",
        "digest",
        "fingerprint",
        "payload_hash",
        "response_hash",
        "prompt_hash",
    }
)

_RETENTION_STATUS_FIELDS = {
    "raw_response_retained",
    "prompt_retained",
    "messages_retained",
}
_SAFE_CODE_RE = re.compile(r"[^a-zA-Z0-9_:.=-]+")
_HEX_SURROGATE_RE = re.compile(r"\b[a-fA-F0-9]{32,128}\b")
_FORBIDDEN_VALUE_MARKERS = (
    "/v1/agent/invoke",
    "api_key",
    "authorization:",
    "bearer ",
    "set-cookie",
    "traceback",
    "chain-of-thought",
    "raw_response",
    "begin prompt",
    "system prompt",
    "http://",
    "https://",
)


@dataclass(frozen=True)
class RouterProviderInvocationOptions:
    """Bounded invocation options for a future single-call dry run."""

    timeout_seconds: float = ROUTER_PROVIDER_TIMEOUT_SECONDS_LIMIT
    max_tokens: int = ROUTER_PROVIDER_MAX_TOKENS_LIMIT
    retry_count: int = ROUTER_PROVIDER_RETRY_COUNT_LIMIT
    streaming: bool = False
    call_cap: int = ROUTER_PROVIDER_CALL_CAP_LIMIT
    raw_response_retention: bool = False
    prompt_retention: bool = False
    messages_retention: bool = False
    artifact_whitelist_enabled: bool = True


@dataclass(frozen=True)
class RouterProviderPolicy:
    """Secret-free router-provider policy.

    The fields store env var *names* and authorization booleans only. They never
    store credential values, endpoint URLs, raw provider output, prompts, or
    model messages.
    """

    provider_name: str = "router_openai_compatible"
    model_env_var_name: str = "ROUTER_MODEL"
    api_key_env_var_name: str = "ROUTER_OPENAI_API_KEY"
    base_url_env_var_name: str = "ROUTER_OPENAI_BASE_URL"
    real_provider_authorized: bool = False
    env_value_access_authorized: bool = False
    provider_call_authorized: bool = False
    options: RouterProviderInvocationOptions = field(
        default_factory=RouterProviderInvocationOptions
    )


@dataclass(frozen=True)
class RouterProviderPreflightResult:
    """Public-safe result of router-provider preflight."""

    ready: bool
    reason_code: str
    policy_summary: Mapping[str, Any]


@dataclass(frozen=True)
class RouterProviderFactoryResult:
    """Fail-closed result from the M1F0 router-only factory wrapper."""

    client_available: bool
    client_created: bool
    reason_code: str
    preflight: RouterProviderPreflightResult
    policy_summary: Mapping[str, Any]


@dataclass(frozen=True)
class RouterProviderModelNormalizationResult:
    """Secret-free model identifier normalization result.

    Router config may use project-level provider/model identifiers while direct
    OpenAI-compatible HTTP clients commonly expect only the provider API model
    id. Model ids are not credentials, but callers should still avoid placing
    them in public artifacts unless a phase explicitly allows it.
    """

    input_model: str
    provider_api_model: str
    normalized: bool
    reason_code: str


@dataclass(frozen=True)
class RouterProviderEndpointNormalizationResult:
    """OpenAI-compatible chat completions endpoint normalization result.

    The URL fields are for in-memory dry-run use only. Public artifacts should
    record only the boolean flags and safe reason code.
    """

    input_base_url: str
    chat_completions_url: str
    valid: bool
    base_url_has_v1_path: bool
    chat_completions_path_normalized: bool
    v1_path_added: bool
    reason_code: str


def build_default_router_provider_policy() -> RouterProviderPolicy:
    """Return the default fail-closed router-provider policy."""
    return RouterProviderPolicy()


def router_provider_required_env_var_names(
    policy: RouterProviderPolicy | None = None,
) -> tuple[str, ...]:
    """Return only env var names required by the router provider policy."""
    effective = policy or build_default_router_provider_policy()
    names = (
        effective.model_env_var_name,
        effective.base_url_env_var_name,
        effective.api_key_env_var_name,
    )
    return tuple(name for name in names if name)


def _safe_code(value: Any, *, limit: int = 120) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    return _SAFE_CODE_RE.sub("_", text)[:limit]


def _policy_summary(policy: RouterProviderPolicy) -> dict[str, Any]:
    options = policy.options
    return {
        "provider_name": _safe_code(policy.provider_name, limit=60),
        "model_env_var_name": policy.model_env_var_name,
        "api_key_env_var_name": policy.api_key_env_var_name,
        "base_url_env_var_name": policy.base_url_env_var_name,
        "real_provider_authorized": bool(policy.real_provider_authorized),
        "env_value_access_authorized": bool(policy.env_value_access_authorized),
        "provider_call_authorized": bool(policy.provider_call_authorized),
        "call_cap": int(options.call_cap),
        "timeout_seconds": float(options.timeout_seconds),
        "max_tokens": int(options.max_tokens),
        "retry_count": int(options.retry_count),
        "streaming": bool(options.streaming),
        "raw_response_retention": bool(options.raw_response_retention),
        "prompt_retention": bool(options.prompt_retention),
        "messages_retention": bool(options.messages_retention),
        "artifact_whitelist_enabled": bool(options.artifact_whitelist_enabled),
    }


def normalize_router_provider_model_for_openai_compatible_api(
    model_name: str,
) -> RouterProviderModelNormalizationResult:
    """Normalize provider-prefixed router model ids for direct HTTP clients.

    The helper is deliberately narrow: it strips only known `provider/model`
    prefixes for OpenAI-compatible providers and leaves all other values
    unchanged. It does not read configuration, create clients, or call providers.
    """
    text = str(model_name or "").strip()
    if not text:
        return RouterProviderModelNormalizationResult(
            input_model="",
            provider_api_model="",
            normalized=False,
            reason_code="model_missing",
        )
    if "://" in text or "/" not in text:
        return RouterProviderModelNormalizationResult(
            input_model=text,
            provider_api_model=text,
            normalized=False,
            reason_code="model_passthrough",
        )

    parts = [part.strip() for part in text.split("/")]
    if len(parts) != 2:
        return RouterProviderModelNormalizationResult(
            input_model=text,
            provider_api_model=text,
            normalized=False,
            reason_code="model_passthrough",
        )

    provider_prefix, api_model = parts
    if provider_prefix.lower() not in _OPENAI_COMPATIBLE_PROVIDER_PREFIXES:
        return RouterProviderModelNormalizationResult(
            input_model=text,
            provider_api_model=text,
            normalized=False,
            reason_code="provider_prefix_not_normalized",
        )
    if not _MODEL_SEGMENT_RE.match(api_model):
        return RouterProviderModelNormalizationResult(
            input_model=text,
            provider_api_model=text,
            normalized=False,
            reason_code="api_model_segment_invalid",
        )
    return RouterProviderModelNormalizationResult(
        input_model=text,
        provider_api_model=api_model,
        normalized=True,
        reason_code=f"{provider_prefix.lower()}_provider_prefix_removed",
    )


def build_router_provider_request_contract(
    options: RouterProviderInvocationOptions | None = None,
) -> dict[str, Any]:
    """Return the safe OpenAI-compatible request contract for router dry runs.

    The returned data is safe to place in internal artifacts after allowlist
    filtering because it contains only bounded options and JSON mode metadata;
    it intentionally omits prompt text, messages, endpoint URLs, and credentials.
    """
    effective = options or RouterProviderInvocationOptions()
    return {
        "request_contract_version": ROUTER_PROVIDER_REQUEST_CONTRACT_VERSION,
        "route_intent_message_contract_version": (
            ROUTER_PROVIDER_ROUTE_INTENT_MESSAGE_CONTRACT_VERSION
        ),
        "route_intent_message_layout": ROUTER_PROVIDER_ROUTE_INTENT_MESSAGE_LAYOUT,
        "route_intent_schema_name": ROUTER_PROVIDER_ROUTE_INTENT_SCHEMA_NAME,
        "strict_route_intent_json_schema": True,
        "allowed_dimensions": list(ROUTER_PROVIDER_DIMENSIONS),
        "response_format_json_object": True,
        "response_format": dict(ROUTER_PROVIDER_JSON_RESPONSE_FORMAT),
        "max_tokens": int(effective.max_tokens),
        "timeout_seconds": float(effective.timeout_seconds),
        "retry_count": int(effective.retry_count),
        "streaming": False,
        "raw_response_retained": False,
        "prompt_retained": False,
        "messages_retained": False,
    }


def suggest_router_provider_dimensions(question: str) -> tuple[str, ...]:
    """Return deterministic dimension hints for provider routing prompts."""
    text = str(question or "").strip().lower()
    if not text:
        return ROUTER_PROVIDER_DIMENSIONS
    selected: list[str] = []
    for dimension in ROUTER_PROVIDER_DIMENSIONS:
        keywords = _DIMENSION_CUE_KEYWORDS.get(dimension, ())
        if any(keyword in text for keyword in keywords):
            selected.append(dimension)
    if not selected and any(
        keyword in text
        for keyword in (
            "是否值得关注",
            "是否值得买",
            "投资",
            "研判",
            "分析",
            "should i invest",
            "investment",
            "analyze",
        )
    ):
        selected.extend(("value", "market", "risk"))
    return tuple(selected or ROUTER_PROVIDER_DIMENSIONS)


def build_router_provider_route_intent_draft(question: str) -> dict[str, Any]:
    """Build a deterministic route-intent draft for provider echo validation."""
    user_question = str(question or "").strip() or "not provided"
    return {
        "schema": ROUTER_PROVIDER_ROUTE_INTENT_SCHEMA_NAME,
        "schema_version": ROUTER_PROVIDER_ROUTE_INTENT_SCHEMA_NAME,
        "task_type": "general",
        "targets": [user_question],
        "selected_dimensions": list(suggest_router_provider_dimensions(user_question)),
        "route_confidence": 0.95,
        "needs_clarification": False,
        "clarification_question": "",
        "fallback_reason": "",
        "provenance": {
            "source": "route_intent_planner",
            "route_granularity": "dimension",
        },
    }


def build_router_provider_route_intent_messages(
    question: str,
) -> tuple[dict[str, str], ...]:
    """Build strict JSON-only messages for a router-provider dry run.

    These messages are for in-memory provider requests only. Callers must not
    persist them in graph state, workflow snapshots, artifacts, or public output.
    """
    draft = build_router_provider_route_intent_draft(question)
    draft_json = json.dumps(draft, ensure_ascii=False, separators=(",", ":"))
    content = "\n".join(
        [
            "Return exactly this JSON object and nothing else.",
            "The first character must be { and the last character must be }.",
            "Do not analyze, explain, translate, reformat, wrap in markdown, or add keys.",
            "This is a routing task, not an analysis task. Do not analyze the stock, "
            "do not provide investment advice, and do not write a report.",
            "不要分析股票，不要输出研报或解释；只回显下面的 JSON 路由对象。",
            draft_json,
        ]
    )
    return ({"role": "user", "content": content},)


def build_openai_compatible_chat_completions_url(
    base_url: str,
) -> RouterProviderEndpointNormalizationResult:
    """Build an OpenAI-compatible `/v1/chat/completions` URL.

    The helper is pure and intentionally conservative. It does not read env
    values, create clients, call providers, or decide authorization.
    """
    text = str(base_url or "").strip()
    if not text:
        return RouterProviderEndpointNormalizationResult(
            input_base_url="",
            chat_completions_url="",
            valid=False,
            base_url_has_v1_path=False,
            chat_completions_path_normalized=False,
            v1_path_added=False,
            reason_code="base_url_missing",
        )

    parsed = urlsplit(text)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return RouterProviderEndpointNormalizationResult(
            input_base_url=text,
            chat_completions_url="",
            valid=False,
            base_url_has_v1_path=False,
            chat_completions_path_normalized=False,
            v1_path_added=False,
            reason_code="base_url_invalid_scheme_or_host",
        )
    if parsed.query or parsed.fragment:
        return RouterProviderEndpointNormalizationResult(
            input_base_url=text,
            chat_completions_url="",
            valid=False,
            base_url_has_v1_path=False,
            chat_completions_path_normalized=False,
            v1_path_added=False,
            reason_code="base_url_query_or_fragment_not_allowed",
        )

    path = parsed.path.rstrip("/")
    base_url_has_v1_path = path.endswith("/v1")
    v1_path_added = False
    if path.endswith("/chat/completions"):
        endpoint_path = path
        reason_code = "chat_completions_path_passthrough"
    elif base_url_has_v1_path:
        endpoint_path = f"{path}/chat/completions"
        reason_code = "chat_completions_path_appended"
    else:
        endpoint_path = f"{path}/v1/chat/completions" if path else "/v1/chat/completions"
        v1_path_added = True
        reason_code = "v1_chat_completions_path_appended"

    endpoint = urlunsplit(
        (
            parsed.scheme,
            parsed.netloc,
            endpoint_path,
            "",
            "",
        )
    )
    return RouterProviderEndpointNormalizationResult(
        input_base_url=text,
        chat_completions_url=endpoint,
        valid=True,
        base_url_has_v1_path=base_url_has_v1_path,
        chat_completions_path_normalized=True,
        v1_path_added=v1_path_added,
        reason_code=reason_code,
    )


def router_provider_preflight(
    policy: RouterProviderPolicy | None = None,
    *,
    selected_routing_enabled: bool,
    llm_dimension_router_enabled: bool,
) -> RouterProviderPreflightResult:
    """Evaluate whether a future real-provider dry run is allowed."""
    effective = policy or build_default_router_provider_policy()
    summary = _policy_summary(effective)
    options = effective.options

    reason_code = ""
    if not selected_routing_enabled:
        reason_code = "selected_routing_disabled"
    elif not llm_dimension_router_enabled:
        reason_code = "llm_dimension_router_disabled"
    elif not effective.real_provider_authorized:
        reason_code = "real_provider_not_authorized"
    elif not effective.env_value_access_authorized:
        reason_code = "env_value_access_not_authorized"
    elif not effective.provider_call_authorized:
        reason_code = "provider_call_not_authorized"
    elif options.call_cap > ROUTER_PROVIDER_CALL_CAP_LIMIT:
        reason_code = "call_cap_exceeds_limit"
    elif options.call_cap < 1:
        reason_code = "call_cap_missing"
    elif options.streaming:
        reason_code = "streaming_not_allowed"
    elif options.retry_count > ROUTER_PROVIDER_RETRY_COUNT_LIMIT:
        reason_code = "retry_count_exceeds_limit"
    elif options.retry_count < 0:
        reason_code = "retry_count_invalid"
    elif options.max_tokens > ROUTER_PROVIDER_MAX_TOKENS_LIMIT:
        reason_code = "max_tokens_exceeds_limit"
    elif options.timeout_seconds > ROUTER_PROVIDER_TIMEOUT_SECONDS_LIMIT:
        reason_code = "timeout_exceeds_limit"
    elif options.raw_response_retention:
        reason_code = "raw_response_retention_not_allowed"
    elif options.prompt_retention:
        reason_code = "prompt_retention_not_allowed"
    elif options.messages_retention:
        reason_code = "messages_retention_not_allowed"
    elif not options.artifact_whitelist_enabled:
        reason_code = "artifact_whitelist_disabled"
    else:
        return RouterProviderPreflightResult(
            ready=True,
            reason_code="ready_for_single_call_dry_run",
            policy_summary=summary,
        )

    return RouterProviderPreflightResult(
        ready=False,
        reason_code=reason_code,
        policy_summary=summary,
    )


def build_router_provider_factory_result(
    policy: RouterProviderPolicy | None = None,
    *,
    selected_routing_enabled: bool,
    llm_dimension_router_enabled: bool,
) -> RouterProviderFactoryResult:
    """Build the router-provider factory wrapper result without creating a client."""
    preflight = router_provider_preflight(
        policy,
        selected_routing_enabled=selected_routing_enabled,
        llm_dimension_router_enabled=llm_dimension_router_enabled,
    )
    reason_code = (
        "real_provider_client_creation_deferred_until_m1f"
        if preflight.ready
        else preflight.reason_code
    )
    return RouterProviderFactoryResult(
        client_available=False,
        client_created=False,
        reason_code=reason_code,
        preflight=preflight,
        policy_summary=preflight.policy_summary,
    )


def _normalize_dimensions(raw: Any) -> list[str]:
    if not isinstance(raw, (list, tuple)):
        return []
    seen: set[str] = set()
    normalized: list[str] = []
    for item in raw:
        if not isinstance(item, str):
            continue
        dimension = item.strip().lower()
        if dimension in ROUTER_PROVIDER_DIMENSIONS and dimension not in seen:
            normalized.append(dimension)
            seen.add(dimension)
    return normalized


def sanitize_router_provider_artifact(metadata: Mapping[str, Any]) -> dict[str, Any]:
    """Serialize router-provider metadata by allowlist only."""
    clean: dict[str, Any] = {
        "raw_response_retained": False,
        "prompt_retained": False,
        "messages_retained": False,
    }
    for key in ROUTER_PROVIDER_ARTIFACT_ALLOWED_FIELDS:
        if key not in metadata:
            continue
        value = metadata[key]
        if key in {
            "provider_router_enabled",
            "provider_router_invoked",
            "provider_router_parse_ok",
            "streaming",
            "unsafe_scan_pass",
            "model_normalized",
            "response_format_json_object",
            "strict_route_intent_json_schema",
            "chat_completions_path_normalized",
            "v1_path_added",
        }:
            clean[key] = bool(value)
        elif key in _RETENTION_STATUS_FIELDS:
            clean[key] = False
        elif key in {
            "phase",
            "provider_router_mode",
            "fallback_reason_code",
            "provider_error_code",
            "request_contract_version",
            "route_intent_message_contract_version",
            "route_intent_message_layout",
            "route_intent_schema_name",
        }:
            clean[key] = _safe_code(value)
        elif key in {"selected_dimensions", "allowed_dimensions"}:
            clean[key] = _normalize_dimensions(value)
        elif key == "route_confidence":
            try:
                numeric = float(value)
            except (TypeError, ValueError):
                continue
            if 0 <= numeric <= 1:
                clean[key] = numeric
        elif key in {"latency_ms", "call_count", "timeout_seconds", "max_tokens", "retry_count"}:
            try:
                clean[key] = int(value) if key != "timeout_seconds" else float(value)
            except (TypeError, ValueError):
                continue
    return clean


def _scan_item(value: Any, findings: set[str], *, key_name: str = "") -> None:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            key_text = str(key or "").strip()
            key_lower = key_text.lower()
            if key_lower in _RETENTION_STATUS_FIELDS:
                if nested is not False:
                    findings.add(f"retention_true:{key_lower}")
                continue
            if key_lower in ROUTER_PROVIDER_ARTIFACT_FORBIDDEN_FIELDS:
                findings.add(f"forbidden_key:{key_lower}")
            if key_lower.endswith("_hash") or key_lower.endswith("_sha256"):
                findings.add(f"forbidden_key:{key_lower}")
            _scan_item(nested, findings, key_name=key_lower)
        return
    if isinstance(value, (list, tuple, set)):
        for item in value:
            _scan_item(item, findings, key_name=key_name)
        return
    if isinstance(value, str):
        lower_value = value.lower()
        for marker in _FORBIDDEN_VALUE_MARKERS:
            if marker in lower_value:
                findings.add(f"forbidden_value:{marker}")
        if _HEX_SURROGATE_RE.search(value):
            findings.add("forbidden_value:hex_surrogate")


def router_provider_unsafe_scan(metadata: Mapping[str, Any]) -> dict[str, Any]:
    """Scan router-provider metadata for raw, secret, endpoint, prompt, or hash markers."""
    findings: set[str] = set()
    _scan_item(metadata, findings)
    return {
        "pass": not findings,
        "findings": sorted(findings),
    }


def build_router_provider_artifact(metadata: Mapping[str, Any]) -> dict[str, Any]:
    """Return sanitized metadata with source unsafe-scan status."""
    source_scan = router_provider_unsafe_scan(metadata)
    clean = sanitize_router_provider_artifact(metadata)
    clean_scan = router_provider_unsafe_scan(clean)
    clean["unsafe_scan_pass"] = bool(source_scan["pass"] and clean_scan["pass"])
    return clean


__all__ = [
    "ROUTER_PROVIDER_ARTIFACT_ALLOWED_FIELDS",
    "ROUTER_PROVIDER_ARTIFACT_FORBIDDEN_FIELDS",
    "ROUTER_PROVIDER_CALL_CAP_LIMIT",
    "ROUTER_PROVIDER_COMPAT_ENV_VAR_NAMES",
    "ROUTER_PROVIDER_ENV_VAR_NAMES",
    "ROUTER_PROVIDER_JSON_RESPONSE_FORMAT",
    "ROUTER_PROVIDER_MAX_TOKENS_LIMIT",
    "ROUTER_PROVIDER_REQUEST_CONTRACT_VERSION",
    "ROUTER_PROVIDER_RETRY_COUNT_LIMIT",
    "ROUTER_PROVIDER_ROUTE_INTENT_MESSAGE_CONTRACT_VERSION",
    "ROUTER_PROVIDER_ROUTE_INTENT_MESSAGE_LAYOUT",
    "ROUTER_PROVIDER_ROUTE_INTENT_SCHEMA_NAME",
    "ROUTER_PROVIDER_TIMEOUT_SECONDS_LIMIT",
    "RouterProviderFactoryResult",
    "RouterProviderInvocationOptions",
    "RouterProviderEndpointNormalizationResult",
    "RouterProviderModelNormalizationResult",
    "RouterProviderPolicy",
    "RouterProviderPreflightResult",
    "build_default_router_provider_policy",
    "build_openai_compatible_chat_completions_url",
    "build_router_provider_route_intent_messages",
    "build_router_provider_request_contract",
    "build_router_provider_artifact",
    "build_router_provider_factory_result",
    "normalize_router_provider_model_for_openai_compatible_api",
    "router_provider_preflight",
    "router_provider_required_env_var_names",
    "router_provider_unsafe_scan",
    "sanitize_router_provider_artifact",
]
