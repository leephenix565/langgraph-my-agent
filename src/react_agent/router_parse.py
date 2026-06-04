# ruff: noqa: D103
"""Parser for the Phase R1-B fixed DAG planner response."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from typing import Any

from react_agent.fixed_dag_contracts import (
    FIXED_DAG_SCHEMA_VERSION,
    RESET_RUNTIME_AGENT_IDS,
    build_deterministic_fixed_dag_plan,
)

_JSON_BLOCK_RE = re.compile(r"\{.*\}", re.DOTALL)


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


def parse_fixed_dag_plan_with_stats(
    raw: str,
    *,
    user_text: str = "",
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Parse a fixed DAG plan and fail-soft to the deterministic reset plan."""
    fallback = build_deterministic_fixed_dag_plan(user_text)
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

    target_agent_ids, filtered_agents = _normalize_agent_ids(
        parsed.get("target_agent_ids")
    )
    plan = dict(fallback)
    if isinstance(parsed.get("plan_id"), str) and parsed["plan_id"].strip():
        plan["plan_id"] = parsed["plan_id"].strip()
    plan["target_agent_ids"] = target_agent_ids
    plan["provenance"] = {
        **fallback["provenance"],
        "source": "parsed_fixed_dag_plan",
        "parser_filtered_agents": filtered_agents,
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
