# ruff: noqa: D103
"""Load and query fixed-DAG runtime binding metadata."""

from __future__ import annotations

import json
from collections import Counter
from collections.abc import Mapping
from pathlib import Path
from typing import Any, cast

from react_agent.fixed_dag.runtime.constants import FIXED_DAG_RUNTIME_BINDINGS_PATH
from react_agent.fixed_dag.runtime.types import (
    FixedDagRuntimeBinding,
    FixedDagRuntimeBindings,
)
from react_agent.fixed_dag.runtime.validation import validate_fixed_dag_runtime_bindings


def load_fixed_dag_runtime_bindings(path: Path | None = None) -> FixedDagRuntimeBindings:
    bindings_path = path or FIXED_DAG_RUNTIME_BINDINGS_PATH
    return cast(
        FixedDagRuntimeBindings,
        json.loads(bindings_path.read_text(encoding="utf-8")),
    )


def _validated_runtime_bindings(
    bindings: Mapping[str, Any] | None = None,
) -> FixedDagRuntimeBindings:
    loaded = load_fixed_dag_runtime_bindings() if bindings is None else bindings
    valid, reason = validate_fixed_dag_runtime_bindings(loaded)
    if not valid:
        raise ValueError(f"Invalid fixed DAG runtime bindings: {reason}")
    return cast(FixedDagRuntimeBindings, loaded)


def fixed_dag_runtime_bindings(
    bindings: Mapping[str, Any] | None = None,
) -> list[FixedDagRuntimeBinding]:
    return list(_validated_runtime_bindings(bindings)["bindings"])


def fixed_dag_runtime_binding_ids(
    bindings: Mapping[str, Any] | None = None,
) -> tuple[str, ...]:
    return tuple(binding["agent_id"] for binding in fixed_dag_runtime_bindings(bindings))


def binding_by_agent_id(
    agent_id: str,
    bindings: Mapping[str, Any] | None = None,
) -> FixedDagRuntimeBinding:
    for binding in fixed_dag_runtime_bindings(bindings):
        if binding["agent_id"] == agent_id:
            return binding
    raise KeyError(f"unknown fixed DAG runtime binding: {agent_id}")


def external_candidate_bindings(
    bindings: Mapping[str, Any] | None = None,
) -> tuple[FixedDagRuntimeBinding, ...]:
    return tuple(
        binding
        for binding in fixed_dag_runtime_bindings(bindings)
        if binding["runtime_kind"] == "external_http_candidate"
    )


def external_compute_default_bindings(
    bindings: Mapping[str, Any] | None = None,
) -> tuple[FixedDagRuntimeBinding, ...]:
    return tuple(
        binding
        for binding in fixed_dag_runtime_bindings(bindings)
        if binding["runtime_kind"] == "external_compute_default"
    )


def external_compute_default_agent_ids(
    bindings: Mapping[str, Any] | None = None,
) -> tuple[str, ...]:
    return tuple(binding["agent_id"] for binding in external_compute_default_bindings(bindings))


def runtime_binding_summary(bindings: Mapping[str, Any] | None = None) -> dict[str, Any]:
    items = fixed_dag_runtime_bindings(bindings)
    return {
        "total_count": len(items),
        "runtime_kind_counts": dict(Counter(item["runtime_kind"] for item in items)),
        "implementation_status_counts": dict(
            Counter(item["implementation_status"] for item in items)
        ),
        "external_candidate_count": sum(
            item["runtime_kind"] == "external_http_candidate" for item in items
        ),
        "external_compute_default_count": sum(
            item["runtime_kind"] == "external_compute_default" for item in items
        ),
        "live_verified_count": sum(item["live_verified"] for item in items),
        "invoke_enabled_count": sum(item["invoke_enabled_by_default"] for item in items),
    }


__all__ = [
    "binding_by_agent_id",
    "external_candidate_bindings",
    "external_compute_default_agent_ids",
    "external_compute_default_bindings",
    "fixed_dag_runtime_binding_ids",
    "fixed_dag_runtime_bindings",
    "load_fixed_dag_runtime_bindings",
    "runtime_binding_summary",
]
