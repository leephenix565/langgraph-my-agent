"""Public-safety helpers for fixed-DAG contract payloads."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

LEGACY_CONTRACT_KEYS = {
    "mode",
    "layerMode",
    "layer_mode",
    "layerPlan",
    "layer_plan",
    "fusionSteps",
    "fusion_verdict",
    "baseline_bundle",
}
SELECTED_PLAN_FORBIDDEN_KEYS = {
    "runtime_kind",
    "implementation_status",
    "binding_source",
    "legacy_agent_id",
    "external_agent_id",
    "invoke_enabled",
    "live_verified",
    "env_var",
    "default_url",
    "endpoint",
    "provider_response",
    "external_response",
}
SELECTED_PLAN_PUBLIC_UNSAFE_TEXT_TOKENS = (
    "provider",
    "external endpoint",
    "env_var",
    "secret",
    "chain-of-thought",
    "pending_implementation",
    "placeholder",
    "runtime binding",
    "default_url",
    "traceback",
)
LEGACY_DISPATCH_VALUES = {"Star", "Chain", "Debate", "Tree"}
REPORT_BUNDLE_UNSAFE_KEYS = {
    "api_key",
    "secret",
    "token",
    "password",
    "authorization",
    "cookie",
    "set-cookie",
    "traceback",
    "chain-of-thought",
    "raw_provider_response",
    "raw_response",
    "raw_external_json",
    "private",
    "endpoint",
    "base_url",
}


def _contains_legacy_key(value: Any) -> bool:
    if isinstance(value, Mapping):
        return any(
            key in LEGACY_CONTRACT_KEYS or _contains_legacy_key(item)
            for key, item in value.items()
        )
    if isinstance(value, list):
        return any(_contains_legacy_key(item) for item in value)
    return False


def _contains_selected_plan_forbidden_key(value: Any) -> bool:
    if isinstance(value, Mapping):
        return any(
            key in SELECTED_PLAN_FORBIDDEN_KEYS or _contains_selected_plan_forbidden_key(item)
            for key, item in value.items()
        )
    if isinstance(value, list):
        return any(_contains_selected_plan_forbidden_key(item) for item in value)
    return False


def _contains_legacy_dispatch_value(value: Any) -> bool:
    if isinstance(value, Mapping):
        return any(_contains_legacy_dispatch_value(item) for item in value.values())
    if isinstance(value, list):
        return any(_contains_legacy_dispatch_value(item) for item in value)
    return isinstance(value, str) and value.strip() in LEGACY_DISPATCH_VALUES


def _contains_public_unsafe_text(value: str) -> bool:
    lowered = str(value or "").lower()
    return any(token in lowered for token in SELECTED_PLAN_PUBLIC_UNSAFE_TEXT_TOKENS)


def _looks_like_legacy_agent_id(agent_id: str) -> bool:
    return agent_id.startswith("a") and len(agent_id) >= 3 and agent_id[1:3].isdigit()


def _safe_public_text(value: Any, *, limit: int = 180) -> str:
    text = str(value or "").strip()
    text = text.replace("\n", " ").replace("\r", " ")
    if len(text) > limit:
        text = text[: max(limit - 3, 0)].rstrip() + "..."
    lowered = text.lower()
    if any(token in lowered for token in REPORT_BUNDLE_UNSAFE_KEYS):
        return ""
    return text


def _safe_public_float(value: Any, *, default: float = 0.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    if number < 0.0:
        return 0.0
    if number > 1.0:
        return 1.0
    return number


def _safe_public_mapping(value: Any, *, allowed_keys: set[str]) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        return {}
    result: dict[str, Any] = {}
    for key, raw in value.items():
        text_key = str(key)
        if text_key not in allowed_keys:
            continue
        if isinstance(raw, int | float):
            result[text_key] = _safe_public_float(raw)
        else:
            result[text_key] = _safe_public_text(raw, limit=80)
    return result


def _safe_public_detail_value(value: Any, *, depth: int = 0) -> Any:
    if depth > 3:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, int | float):
        return value
    if isinstance(value, str):
        return _safe_public_text(value, limit=240) or None
    if isinstance(value, Mapping):
        result: dict[str, Any] = {}
        for key, raw in list(value.items())[:14]:
            text_key = _safe_public_text(key, limit=80)
            if not text_key or text_key.lower() in REPORT_BUNDLE_UNSAFE_KEYS:
                continue
            bounded = _safe_public_detail_value(raw, depth=depth + 1)
            if bounded not in (None, "", [], {}):
                result[text_key] = bounded
        return result or None
    if isinstance(value, list):
        items: list[Any] = []
        for raw in value[:14]:
            bounded = _safe_public_detail_value(raw, depth=depth + 1)
            if bounded not in (None, "", [], {}):
                items.append(bounded)
        return items or None
    return _safe_public_text(value, limit=160) or None


def _safe_public_detail_mapping(value: Any, *, limit: int = 18) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        return {}
    result: dict[str, Any] = {}
    for key, raw in value.items():
        text_key = _safe_public_text(key, limit=80)
        if not text_key or text_key.lower() in REPORT_BUNDLE_UNSAFE_KEYS:
            continue
        bounded = _safe_public_detail_value(raw)
        if bounded not in (None, "", [], {}):
            result[text_key] = bounded
        if len(result) >= limit:
            break
    return result


def _safe_public_detail_list(value: Any, *, limit: int = 10) -> list[Any]:
    if not isinstance(value, list):
        return []
    result: list[Any] = []
    for raw in value[:limit]:
        bounded = _safe_public_detail_value(raw)
        if bounded not in (None, "", [], {}):
            result.append(bounded)
    return result


def _safe_public_text_list(value: Any, *, limit: int = 6, item_limit: int = 80) -> list[str]:
    if not isinstance(value, list):
        return []
    result: list[str] = []
    for raw in value:
        text = _safe_public_text(raw, limit=item_limit)
        if text and text not in result:
            result.append(text)
        if len(result) >= limit:
            break
    return result


def _contains_unsafe_report_key(value: Any) -> bool:
    if isinstance(value, Mapping):
        for key, item in value.items():
            if str(key).lower() in REPORT_BUNDLE_UNSAFE_KEYS:
                return True
            if _contains_unsafe_report_key(item):
                return True
    if isinstance(value, list):
        return any(_contains_unsafe_report_key(item) for item in value)
    if isinstance(value, str):
        lowered = value.lower()
        return any(token in lowered for token in ("raw_response", "chain-of-thought", "traceback"))
    return False


__all__ = [
    "LEGACY_CONTRACT_KEYS",
    "LEGACY_DISPATCH_VALUES",
    "REPORT_BUNDLE_UNSAFE_KEYS",
    "SELECTED_PLAN_FORBIDDEN_KEYS",
    "SELECTED_PLAN_PUBLIC_UNSAFE_TEXT_TOKENS",
    "_contains_legacy_dispatch_value",
    "_contains_legacy_key",
    "_contains_public_unsafe_text",
    "_contains_selected_plan_forbidden_key",
    "_contains_unsafe_report_key",
    "_looks_like_legacy_agent_id",
    "_safe_public_detail_list",
    "_safe_public_detail_mapping",
    "_safe_public_detail_value",
    "_safe_public_float",
    "_safe_public_mapping",
    "_safe_public_text",
    "_safe_public_text_list",
]
