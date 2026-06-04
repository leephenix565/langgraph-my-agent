import subprocess
import sys

import react_agent.graph as graph_module
from react_agent.graph_bootstrap import (
    bootstrap_legacy_agent_runtime,
    build_legacy_node_registry,
)
from react_agent.legacy_agent_registry import AGENT_METADATA, AGENT_TOOLS


def test_fixed_dag_graph_does_not_register_dynamic_agent_nodes() -> None:
    assert not hasattr(graph_module, "_build_agent_node")
    assert not any(name.startswith("agent_") for name in graph_module.builder.nodes)


def test_importing_fixed_dag_graph_does_not_load_legacy_registry() -> None:
    code = """
import sys
import react_agent.graph  # noqa: F401

forbidden = [
    "react_agent.legacy_agent_registry",
    "react_agent.graph_bootstrap",
    "react_agent.default_agents",
    "react_agent.generic_agent",
    "react_agent.external_http_agents",
]
loaded = [name for name in forbidden if name in sys.modules]
if loaded:
    raise SystemExit("loaded legacy modules: " + ",".join(loaded))
"""
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        check=False,
        text=True,
    )
    assert result.returncode == 0, result.stderr or result.stdout


def test_legacy_agent_tool_registry_is_explicit_compatibility_boundary() -> None:
    AGENT_METADATA.clear()
    AGENT_TOOLS.clear()
    bootstrap_legacy_agent_runtime()
    agent_ids, _node_names = build_legacy_node_registry(include_disabled=False)
    assert AGENT_TOOLS
    assert len(agent_ids) == 25
    AGENT_METADATA.clear()
    AGENT_TOOLS.clear()
