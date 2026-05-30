"""Compatibility facade for valuation agents now handled by generic HTTP wrappers."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Dict

from langchain_core.tools import BaseTool

from react_agent.external_http_agents import (
    EXTERNAL_HTTP_AGENT_CONFIG,
    build_external_http_agent_request,
    build_external_http_tool,
    map_external_http_response_to_agent_output,
    register_external_http_agents,
)


EXTERNAL_VALUATION_AGENT_CONFIG: Dict[str, Dict[str, str]] = {
    agent_id: {
        "external_agent_id": config.external_agent_id,
        "env_var": config.env_var,
        "default_url": config.default_url,
    }
    for agent_id, config in EXTERNAL_HTTP_AGENT_CONFIG.items()
    if agent_id in {"a16_ml_valuation", "a17_traditional_valuation", "a18_meta_valuation"}
}


def external_valuation_agent_ids() -> set[str]:
    """Return the valuation main-system ids bound to generic HTTP wrappers."""
    return set(EXTERNAL_VALUATION_AGENT_CONFIG)


build_external_agent_request = build_external_http_agent_request
map_external_response_to_agent_output = map_external_http_response_to_agent_output
build_external_valuation_tool = build_external_http_tool


def register_external_valuation_agents(metadata_by_id: Mapping[str, Any]) -> Dict[str, BaseTool]:
    """Return valuation wrapper tools using the generic HTTP registration path."""
    wrappers = register_external_http_agents(metadata_by_id)
    return {aid: tool for aid, tool in wrappers.items() if aid in EXTERNAL_VALUATION_AGENT_CONFIG}
