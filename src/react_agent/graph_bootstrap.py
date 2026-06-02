"""Bootstrap helpers for graph agent registration and node registry."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Tuple

from react_agent.agents import (
    AGENT_METADATA,
    AGENT_TOOLS,
    agents_by_layer,
    format_agent_profile,
    load_metadata_from_dir,
    register_agent,
)
from react_agent.default_agents import _build_agent_tool, register_builtin_agents
from react_agent.external_http_agents import register_external_http_agents
from react_agent.generic_agent import build_generic_agent_tool

CONFIG_AGENT_DIR = Path(__file__).resolve().parents[2] / "config" / "agents"


def bootstrap_agent_runtime() -> None:
    """Register config/builtin agents using the existing import-time behavior."""
    enable_builtin = os.environ.get("ENABLE_BUILTIN_AGENTS", "0") == "1"
    config_exists = CONFIG_AGENT_DIR.exists()
    if enable_builtin or not config_exists:
        register_builtin_agents()
    if config_exists:
        load_metadata_from_dir(CONFIG_AGENT_DIR)
    for aid, meta in list(AGENT_METADATA.items()):
        if not getattr(meta, "default_enabled", True):
            AGENT_TOOLS.pop(aid, None)
    for aid, tool in register_external_http_agents(AGENT_METADATA).items():
        if aid not in AGENT_TOOLS:
            AGENT_TOOLS[aid] = tool
    for aid, meta in list(AGENT_METADATA.items()):
        if not getattr(meta, "default_enabled", True):
            continue
        if aid in AGENT_TOOLS:
            continue
        desc = (meta.description or "").strip()
        if desc:
            profile = format_agent_profile(meta)
            if aid == "a01_cio_orchestrator":
                profile = (
                    f"{profile}\n[Router alignment] 严格根据 router_plan_summary 执行任务拆解，"
                    "不得新增/删除 agent，只能解释既定分工、补充验收点与风险门禁。"
                )
            tool = _build_agent_tool(aid, profile, default_allow_search=True)
        else:
            tool = build_generic_agent_tool(aid, meta.description)
        register_agent(meta, tool)


def build_node_registry(include_disabled: bool) -> Tuple[List[str], Dict[str, str]]:
    del include_disabled
    agent_ids_for_nodes: List[str] = [
        aid for aid, meta in AGENT_METADATA.items() if meta.default_enabled
    ]
    agent_node_names: Dict[str, str] = {
        aid: f"agent_{aid}_node" for aid in agent_ids_for_nodes
    }
    return agent_ids_for_nodes, agent_node_names


def _agent_profile_card(meta_id: str) -> Dict[str, Any]:
    meta = AGENT_METADATA[meta_id]
    return {
        "id": meta.id,
        "name": meta.name,
        "business_layer": meta.business_layer or "",
        "business_category": meta.business_category or "",
        "profile_summary": meta.profile_summary or meta.description,
        "when_to_use": meta.when_to_use or "",
        "when_not_to_use": meta.when_not_to_use or "",
        "required_inputs": meta.required_inputs or "",
        "missing_input_policy": meta.missing_input_policy or "",
    }


def build_agent_catalog(layer_order: List[str]) -> Dict[str, List[Dict[str, Any]]]:
    return {
        layer: [_agent_profile_card(agent_id) for agent_id in agents_by_layer(layer)]
        for layer in layer_order
    }
