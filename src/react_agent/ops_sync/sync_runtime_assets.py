# ruff: noqa: D101, D103
"""Explicit runtime asset allowlist for sync source selection."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

from react_agent.ops_sync.sync_contracts import CONFIG_OPS_DIR, read_json

RUNTIME_ASSET_MANIFEST_PATH = CONFIG_OPS_DIR / "agent_runtime_asset_manifest.json"


@lru_cache(maxsize=1)
def load_runtime_asset_manifest(path: str = str(RUNTIME_ASSET_MANIFEST_PATH)) -> dict[str, Any]:
    manifest_path = Path(path)
    if not manifest_path.exists():
        return {"schema_version": "agent_runtime_asset_manifest_v1", "assets": []}
    data = read_json(manifest_path)
    if not isinstance(data, dict):
        return {"schema_version": "agent_runtime_asset_manifest_v1", "assets": []}
    return data


@lru_cache(maxsize=1)
def runtime_asset_keys(path: str = str(RUNTIME_ASSET_MANIFEST_PATH)) -> frozenset[tuple[str, str]]:
    manifest = load_runtime_asset_manifest(path)
    keys: set[tuple[str, str]] = set()
    for row in manifest.get("assets") or []:
        if not isinstance(row, dict):
            continue
        if row.get("publish_to_sandbox") is not True:
            continue
        agent_id = str(row.get("agent_id") or "")
        relative_path = str(row.get("relative_path") or "").replace("\\", "/")
        if agent_id and relative_path:
            keys.add((agent_id, relative_path))
    return frozenset(keys)


def is_explicit_runtime_asset(agent_id: str, relative_path: str) -> bool:
    return (agent_id, relative_path.replace("\\", "/")) in runtime_asset_keys()
