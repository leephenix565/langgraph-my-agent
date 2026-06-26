# ruff: noqa: D103
"""Runtime binding annotations for fixed-DAG step results."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from react_agent.fixed_dag.runtime.bindings import binding_by_agent_id
from react_agent.fixed_dag.runtime.constants import FIXED_DAG_RUNTIME_BINDINGS_SOURCE


def annotate_step_result_with_binding(
    step_result: Mapping[str, Any],
    bindings: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    result = dict(step_result)
    binding = binding_by_agent_id(str(result.get("agent_id") or ""), bindings)
    result.update(
        {
            "runtime_kind": binding["runtime_kind"],
            "implementation_status": binding["implementation_status"],
            "binding_source": FIXED_DAG_RUNTIME_BINDINGS_SOURCE,
            "legacy_agent_id": binding["legacy_agent_id"],
            "external_agent_id": binding["external_agent_id"],
            "invoke_enabled": binding["invoke_enabled_by_default"],
            "live_verified": binding["live_verified"],
        }
    )
    return result


__all__ = ["annotate_step_result_with_binding"]
