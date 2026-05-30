"""Bootstrap helpers for graph agent registration and node registry."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, List, Tuple

from react_agent.agents import (
    AGENT_METADATA,
    AGENT_TOOLS,
    agents_by_layer,
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
            if aid == "a01_cio_orchestrator":
                desc = (
                    f"{desc}\n[Router alignment] 严格根据 router_plan_summary 执行任务拆解，"
                    "不得新增/删除 agent，只能解释既定分工、补充验收点与风险门禁。"
                )
            tool = _build_agent_tool(aid, desc, default_allow_search=True)
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


def build_agent_catalog(layer_order: List[str]) -> Dict[str, List[str]]:
    return {layer: agents_by_layer(layer) for layer in layer_order}
