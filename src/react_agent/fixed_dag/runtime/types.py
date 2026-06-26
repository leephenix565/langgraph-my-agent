# ruff: noqa: D101
"""Typed runtime binding contracts."""

from __future__ import annotations

from typing import Any, NotRequired, TypedDict


class FixedDagRuntimeBinding(TypedDict):
    agent_id: str
    runtime_kind: str
    implementation_status: str
    invoke_enabled_by_default: bool
    live_verified: bool
    legacy_agent_id: str
    external_agent_id: str
    env_var: str
    default_url: str
    input_contract: str
    output_contract: str
    notes: str
    routes_to: list[str]


class FixedDagRuntimeBindings(TypedDict):
    schema_version: str
    catalog_schema_version: str
    catalog_source: str
    total_count: int
    default_external_invoke_enabled: bool
    bindings: list[FixedDagRuntimeBinding]
    provenance: NotRequired[dict[str, Any]]


__all__ = ["FixedDagRuntimeBinding", "FixedDagRuntimeBindings"]
