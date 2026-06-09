# ruff: noqa: D103
"""Parser for the Phase R3 fixed DAG planner response."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from typing import Any, cast

from react_agent.fixed_dag_contracts import (
    DIMENSION_GROUPS,
    FIXED_DAG_SCHEMA_VERSION,
    RESET_RUNTIME_AGENT_IDS,
    ROUTE_INTENT_SCHEMA_VERSION,
    ROUTE_TASK_TYPES,
    DimensionName,
    RouteIntent,
    RouteTaskType,
    build_default_fixed_dag_plan,
    build_route_intent,
    normalize_fixed_dag_plan,
    validate_fixed_dag_plan,
    validate_route_intent,
)

_JSON_BLOCK_RE = re.compile(r"\{.*\}", re.DOTALL)
_ROUTE_INTENT_FORBIDDEN_KEYS = {
    "mode",
    "layerMode",
    "layer_mode",
    "layerPlan",
    "layer_plan",
    "fusionSteps",
    "fusion_steps",
    "dag_steps",
    "dagSteps",
    "depends_on",
    "target_agent_ids",
    "runtime_bindings",
    "provider_response",
    "external_response",
}
_LEGACY_ROUTE_VALUES = {"Star", "Chain", "Debate", "Tree"}
_REMOVED_AGENT_IDS = {"value_financial_analysis"}


def extract_json_str(raw: str) -> str | None:
    """Extract the first JSON object from a provider-style response."""
    if not raw:
        return None
    candidate = raw.strip()
    if candidate.startswith("{") and candidate.endswith("}"):
        return candidate
    match = _JSON_BLOCK_RE.search(candidate)
    if match:
        return match.group(0)
    return None


def _normalize_agent_ids(raw_ids: Any) -> tuple[list[str], list[str]]:
    if not isinstance(raw_ids, list):
        return list(RESET_RUNTIME_AGENT_IDS), []
    known = set(RESET_RUNTIME_AGENT_IDS)
    filtered: list[str] = []
    seen: set[str] = set()
    for value in raw_ids:
        if not isinstance(value, str):
            filtered.append(str(value))
            continue
        agent_id = value.strip()
        if agent_id in known and agent_id not in seen:
            seen.add(agent_id)
        else:
            filtered.append(agent_id)
    return list(RESET_RUNTIME_AGENT_IDS), filtered


def _looks_like_legacy_agent_id(agent_id: str) -> bool:
    return agent_id.startswith("a") and len(agent_id) >= 3 and agent_id[1:3].isdigit()


def _contains_route_intent_forbidden_key(value: Any) -> bool:
    if isinstance(value, Mapping):
        return any(
            key in _ROUTE_INTENT_FORBIDDEN_KEYS
            or _contains_route_intent_forbidden_key(item)
            for key, item in value.items()
        )
    if isinstance(value, list):
        return any(_contains_route_intent_forbidden_key(item) for item in value)
    return False


def _contains_legacy_route_value(value: Any) -> bool:
    if isinstance(value, Mapping):
        return any(_contains_legacy_route_value(item) for item in value.values())
    if isinstance(value, list):
        return any(_contains_legacy_route_value(item) for item in value)
    return isinstance(value, str) and value.strip() in _LEGACY_ROUTE_VALUES


def _fallback_route_intent(reason: str) -> RouteIntent:
    return build_route_intent(
        task_type="general",
        selected_dimensions=[],
        selected_agents=[],
        route_confidence=0.0,
        needs_clarification=True,
        clarification_question="Please clarify the routing target before selected planning.",
        fallback_reason="planner_parse_failed",
        provenance={
            "source": "route_intent_parser",
            "normalizer": "r8_3_route_intent_normalizer",
            "fallback_reason": reason,
            "provider_invoked": False,
            "external_invoked": False,
        },
    )


def _normalize_route_dimensions(raw_dimensions: Any) -> tuple[list[DimensionName], list[str]]:
    if not isinstance(raw_dimensions, list):
        return [], []
    selected: list[DimensionName] = []
    filtered: list[str] = []
    seen: set[str] = set()
    for value in raw_dimensions:
        dimension = str(value or "").strip()
        if dimension in DIMENSION_GROUPS and dimension not in seen:
            selected.append(cast(DimensionName, dimension))
            seen.add(dimension)
        elif dimension:
            filtered.append(dimension)
    return selected, filtered


def _normalize_route_agents(raw_agents: Any) -> tuple[list[str], list[str], str]:
    if not isinstance(raw_agents, list):
        return [], [], ""
    known = set(RESET_RUNTIME_AGENT_IDS)
    selected: list[str] = []
    filtered: list[str] = []
    seen: set[str] = set()
    for value in raw_agents:
        agent_id = str(value or "").strip()
        if not agent_id:
            continue
        if agent_id in _REMOVED_AGENT_IDS:
            return [], [agent_id], "removed_agent_present"
        if _looks_like_legacy_agent_id(agent_id):
            return [], [agent_id], "legacy_agent_id_present"
        if agent_id not in known:
            filtered.append(agent_id)
            continue
        if agent_id not in seen:
            selected.append(agent_id)
            seen.add(agent_id)
    return selected, filtered, ""


def _normalize_route_intent_with_stats(
    raw: Mapping[str, Any],
    *,
    question: str = "",
) -> tuple[RouteIntent, dict[str, Any]]:
    if _contains_route_intent_forbidden_key(raw):
        return _fallback_route_intent("forbidden_route_intent_field_present"), {
            "schema": ROUTE_INTENT_SCHEMA_VERSION,
            "parse_ok": False,
            "used_fallback": True,
            "fallback_reason": "forbidden_route_intent_field_present",
            "filtered_agents": [],
            "filtered_dimensions": [],
        }
    if _contains_legacy_route_value(raw):
        return _fallback_route_intent("legacy_route_value_present"), {
            "schema": ROUTE_INTENT_SCHEMA_VERSION,
            "parse_ok": False,
            "used_fallback": True,
            "fallback_reason": "legacy_route_value_present",
            "filtered_agents": [],
            "filtered_dimensions": [],
        }
    schema = raw.get("schema", ROUTE_INTENT_SCHEMA_VERSION)
    schema_version = raw.get("schema_version", ROUTE_INTENT_SCHEMA_VERSION)
    if schema != ROUTE_INTENT_SCHEMA_VERSION or schema_version != ROUTE_INTENT_SCHEMA_VERSION:
        return _fallback_route_intent("invalid_schema"), {
            "schema": ROUTE_INTENT_SCHEMA_VERSION,
            "parse_ok": False,
            "used_fallback": True,
            "fallback_reason": "invalid_schema",
            "filtered_agents": [],
            "filtered_dimensions": [],
        }
    task_type = str(raw.get("task_type") or "general").strip()
    if task_type not in ROUTE_TASK_TYPES:
        return _fallback_route_intent("invalid_task_type"), {
            "schema": ROUTE_INTENT_SCHEMA_VERSION,
            "parse_ok": False,
            "used_fallback": True,
            "fallback_reason": "invalid_task_type",
            "filtered_agents": [],
            "filtered_dimensions": [],
        }
    try:
        confidence = float(raw.get("route_confidence", 0.0))
    except (TypeError, ValueError):
        return _fallback_route_intent("invalid_route_confidence"), {
            "schema": ROUTE_INTENT_SCHEMA_VERSION,
            "parse_ok": False,
            "used_fallback": True,
            "fallback_reason": "invalid_route_confidence",
            "filtered_agents": [],
            "filtered_dimensions": [],
        }
    confidence = max(0.0, min(1.0, confidence))
    selected_dimensions, filtered_dimensions = _normalize_route_dimensions(
        raw.get("selected_dimensions")
    )
    selected_agents, filtered_agents, agent_error = _normalize_route_agents(
        raw.get("selected_agents")
    )
    if agent_error:
        return _fallback_route_intent(agent_error), {
            "schema": ROUTE_INTENT_SCHEMA_VERSION,
            "parse_ok": False,
            "used_fallback": True,
            "fallback_reason": agent_error,
            "filtered_agents": filtered_agents,
            "filtered_dimensions": filtered_dimensions,
        }
    if filtered_agents and not selected_agents:
        return _fallback_route_intent("unknown_selected_agent"), {
            "schema": ROUTE_INTENT_SCHEMA_VERSION,
            "parse_ok": False,
            "used_fallback": True,
            "fallback_reason": "unknown_selected_agent",
            "filtered_agents": filtered_agents,
            "filtered_dimensions": filtered_dimensions,
        }
    briefs = raw.get("task_brief_by_agent")
    if not isinstance(briefs, Mapping):
        briefs = {}
    provenance = raw.get("provenance")
    if not isinstance(provenance, Mapping):
        provenance = {}
    targets = raw.get("targets")
    if not isinstance(targets, list):
        targets = [question] if question else []
    intent = build_route_intent(
        task_type=cast(RouteTaskType, task_type),
        targets=[str(item).strip() for item in targets if str(item).strip()],
        selected_dimensions=selected_dimensions,
        selected_agents=selected_agents,
        task_brief_by_agent={
            str(agent_id): str(brief)
            for agent_id, brief in briefs.items()
        },
        route_confidence=confidence,
        needs_clarification=bool(raw.get("needs_clarification", False)),
        clarification_question=str(raw.get("clarification_question") or "").strip(),
        fallback_reason=str(raw.get("fallback_reason") or "").strip(),
        provenance={
            **dict(provenance),
            "source": "normalized_route_intent",
            "normalizer": "r8_3_route_intent_normalizer",
            "provider_invoked": False,
            "external_invoked": False,
        },
    )
    valid, reason = validate_route_intent(intent)
    if not valid:
        return _fallback_route_intent(f"validation_error:{reason}"), {
            "schema": ROUTE_INTENT_SCHEMA_VERSION,
            "parse_ok": False,
            "used_fallback": True,
            "fallback_reason": f"validation_error:{reason}",
            "filtered_agents": filtered_agents,
            "filtered_dimensions": filtered_dimensions,
        }
    return intent, {
        "schema": ROUTE_INTENT_SCHEMA_VERSION,
        "parse_ok": True,
        "used_fallback": False,
        "fallback_reason": None,
        "filtered_agents": filtered_agents,
        "filtered_dimensions": filtered_dimensions,
    }


def normalize_route_intent(
    raw: Mapping[str, Any],
    *,
    question: str = "",
) -> RouteIntent:
    """Normalize a planner object into route_intent_v1 or a safe fallback."""
    intent, _stats = _normalize_route_intent_with_stats(raw, question=question)
    return intent


def parse_route_intent_json(
    raw: str,
    *,
    question: str = "",
) -> tuple[RouteIntent, dict[str, Any]]:
    """Parse provider-style JSON into route_intent_v1 without executing it."""
    extracted = extract_json_str(raw)
    if not extracted:
        return _fallback_route_intent("missing_json"), {
            "schema": ROUTE_INTENT_SCHEMA_VERSION,
            "parse_ok": False,
            "used_fallback": True,
            "fallback_reason": "missing_json",
            "filtered_agents": [],
            "filtered_dimensions": [],
        }

    try:
        parsed = json.loads(extracted)
    except json.JSONDecodeError as exc:
        return _fallback_route_intent(f"json_decode_error:{exc.msg}"), {
            "schema": ROUTE_INTENT_SCHEMA_VERSION,
            "parse_ok": False,
            "used_fallback": True,
            "fallback_reason": f"json_decode_error:{exc.msg}",
            "filtered_agents": [],
            "filtered_dimensions": [],
        }

    if not isinstance(parsed, Mapping):
        return _fallback_route_intent("not_object"), {
            "schema": ROUTE_INTENT_SCHEMA_VERSION,
            "parse_ok": False,
            "used_fallback": True,
            "fallback_reason": "not_object",
            "filtered_agents": [],
            "filtered_dimensions": [],
        }
    return _normalize_route_intent_with_stats(parsed, question=question)


def parse_route_intent(raw: str, *, question: str = "") -> RouteIntent:
    intent, _stats = parse_route_intent_json(raw, question=question)
    return intent


def parse_fixed_dag_plan_with_stats(
    raw: str,
    *,
    user_text: str = "",
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Parse a fixed DAG plan and fail-soft to the deterministic reset plan."""
    fallback = build_default_fixed_dag_plan(user_text)
    extracted = extract_json_str(raw)
    if not extracted:
        return fallback, {
            "schema": FIXED_DAG_SCHEMA_VERSION,
            "parse_ok": False,
            "used_fallback": True,
            "fallback_reason": "missing_json",
            "filtered_agents": [],
        }

    try:
        parsed = json.loads(extracted)
    except json.JSONDecodeError as exc:
        return fallback, {
            "schema": FIXED_DAG_SCHEMA_VERSION,
            "parse_ok": False,
            "used_fallback": True,
            "fallback_reason": f"json_decode_error:{exc.msg}",
            "filtered_agents": [],
        }

    if not isinstance(parsed, Mapping):
        return fallback, {
            "schema": FIXED_DAG_SCHEMA_VERSION,
            "parse_ok": False,
            "used_fallback": True,
            "fallback_reason": "not_object",
            "filtered_agents": [],
        }

    if parsed.get("schema") != FIXED_DAG_SCHEMA_VERSION:
        return fallback, {
            "schema": FIXED_DAG_SCHEMA_VERSION,
            "parse_ok": False,
            "used_fallback": True,
            "fallback_reason": "invalid_schema",
            "filtered_agents": [],
        }

    target_agent_ids, filtered_agents = _normalize_agent_ids(
        parsed.get("target_agent_ids")
    )
    plan = normalize_fixed_dag_plan(
        {
            **parsed,
            "user_text": user_text,
            "target_agent_ids": target_agent_ids,
            "target": target_agent_ids,
        }
    )
    plan["target_agent_ids"] = target_agent_ids
    plan["target"] = target_agent_ids
    plan["provenance"] = {
        **fallback["provenance"],
        "source": "parsed_fixed_dag_plan",
        "parser_filtered_agents": filtered_agents,
    }
    valid, reason = validate_fixed_dag_plan(plan)
    if not valid:
        return fallback, {
            "schema": FIXED_DAG_SCHEMA_VERSION,
            "parse_ok": False,
            "used_fallback": True,
            "fallback_reason": f"validation_error:{reason}",
            "filtered_agents": filtered_agents,
        }
    return plan, {
        "schema": FIXED_DAG_SCHEMA_VERSION,
        "parse_ok": True,
        "used_fallback": False,
        "fallback_reason": None,
        "filtered_agents": filtered_agents,
    }


def parse_fixed_dag_plan(raw: str, *, user_text: str = "") -> dict[str, Any]:
    plan, _stats = parse_fixed_dag_plan_with_stats(raw, user_text=user_text)
    return plan
