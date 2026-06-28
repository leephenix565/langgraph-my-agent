"""Router-only provider preflight and artifact safety helpers.

This module intentionally does not create model clients, call providers, or read
environment values. It defines the fail-closed contract a future controlled
router-provider dry run must satisfy before any real provider code is allowed.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

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
ROUTER_PROVIDER_TIMEOUT_SECONDS_LIMIT = 8.0
ROUTER_PROVIDER_MAX_TOKENS_LIMIT = 220
ROUTER_PROVIDER_CALL_CAP_LIMIT = 1

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
    retry_count: int = 0
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
    elif options.retry_count > 0:
        reason_code = "retry_not_allowed"
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
        }:
            clean[key] = bool(value)
        elif key in _RETENTION_STATUS_FIELDS:
            clean[key] = False
        elif key in {"phase", "provider_router_mode", "fallback_reason_code", "provider_error_code"}:
            clean[key] = _safe_code(value)
        elif key == "selected_dimensions":
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
    "ROUTER_PROVIDER_MAX_TOKENS_LIMIT",
    "ROUTER_PROVIDER_TIMEOUT_SECONDS_LIMIT",
    "RouterProviderFactoryResult",
    "RouterProviderInvocationOptions",
    "RouterProviderPolicy",
    "RouterProviderPreflightResult",
    "build_default_router_provider_policy",
    "build_router_provider_artifact",
    "build_router_provider_factory_result",
    "router_provider_preflight",
    "router_provider_required_env_var_names",
    "router_provider_unsafe_scan",
    "sanitize_router_provider_artifact",
]
