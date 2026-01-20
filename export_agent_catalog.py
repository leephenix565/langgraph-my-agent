#!/usr/bin/env python
"""Export enabled agent_catalog snapshot from config/agents JSON files."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple


ALLOWED_LAYERS: Tuple[str, ...] = ("L1", "L2", "L3", "L4")
REQUIRED_FIELDS = {
    "id": str,
    "name": str,
    "layer": str,
    "team": str,
    "description": str,
    "default_enabled": bool,
}


def _read_json(path: Path) -> Dict[str, Any]:
    try:
        raw = path.read_text(encoding="utf-8")
    except Exception as exc:
        raise ValueError(f"Failed to read {path}: {exc}") from exc
    try:
        data = json.loads(raw)
    except Exception as exc:
        raise ValueError(f"Invalid JSON in {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object in {path}")
    return data


def _validate_agent(data: Dict[str, Any], path: Path) -> Dict[str, Any]:
    minimal: Dict[str, Any] = {}
    for field, expected_type in REQUIRED_FIELDS.items():
        if field not in data:
            raise ValueError(f"Missing field '{field}' in {path}")
        value = data[field]
        if not isinstance(value, expected_type):
            raise ValueError(
                f"Invalid type for field '{field}' in {path}: "
                f"expected {expected_type.__name__}, got {type(value).__name__}"
            )
        minimal[field] = value

    layer_norm = minimal["layer"].upper()
    if layer_norm not in ALLOWED_LAYERS:
        raise ValueError(
            f"Invalid layer '{minimal['layer']}' in {path}; expected one of {ALLOWED_LAYERS}"
        )
    minimal["layer"] = layer_norm
    return minimal


def _load_agents(agents_dir: Path) -> List[Dict[str, Any]]:
    if not agents_dir.exists():
        raise ValueError(f"Agents dir not found: {agents_dir}")

    files = sorted(agents_dir.glob("agent_*.json"), key=lambda p: p.name)
    if not files:
        raise ValueError(f"No agent_*.json files found in {agents_dir}")

    agents: List[Dict[str, Any]] = []
    id_to_files: Dict[str, List[str]] = {}

    for path in files:
        data = _read_json(path)
        minimal = _validate_agent(data, path)
        agents.append(minimal)
        id_to_files.setdefault(minimal["id"], []).append(str(path))

    duplicates = {aid: paths for aid, paths in id_to_files.items() if len(paths) > 1}
    if duplicates:
        parts = []
        for aid, paths in sorted(duplicates.items()):
            parts.append(f"{aid}: {', '.join(paths)}")
        msg = "Duplicate id(s) found: " + "; ".join(parts)
        raise ValueError(msg)

    return agents


def _desc_1l(text: str) -> str:
    compact = re.sub(r"\s+", " ", text).strip()
    if len(compact) > 140:
        compact = compact[:137] + "..."
    return compact


def _group_by_layer(agents: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    layers: Dict[str, List[Dict[str, Any]]] = {k: [] for k in ALLOWED_LAYERS}
    for agent in agents:
        layers[agent["layer"]].append(agent)
    for layer in ALLOWED_LAYERS:
        layers[layer].sort(key=lambda a: a["id"])
    return layers


def _canonical_hash(enabled_agents: List[Dict[str, Any]]) -> str:
    canonical_agents = sorted(enabled_agents, key=lambda a: a["id"])
    canonical_str = json.dumps(
        canonical_agents,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical_str.encode("utf-8")).hexdigest()[:12]


def _write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_latest(out_dir: Path, catalog_id: str) -> Path:
    latest_path = out_dir / "LATEST"
    latest_path.write_text(f"{catalog_id}\n", encoding="utf-8")
    return latest_path


def _check_latest(latest_path: Path, catalog_id: str) -> None:
    if not latest_path.exists():
        raise ValueError(f"LATEST missing: {latest_path}")
    content = latest_path.read_text(encoding="utf-8").strip()
    if content != catalog_id:
        raise ValueError(f"LATEST mismatch: {content} != {catalog_id}")


def _self_check(snapshot_path: Path, prompt_path: Path) -> None:
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    prompt = json.loads(prompt_path.read_text(encoding="utf-8"))

    snap_id = snapshot.get("catalog_id")
    prompt_id = prompt.get("catalog_id")
    if snap_id != prompt_id:
        raise ValueError(f"catalog_id mismatch: {snap_id} vs {prompt_id}")

    def _check_layers(obj: Dict[str, Any], label: str) -> Dict[str, List[Dict[str, Any]]]:
        layers = obj.get("layers")
        if not isinstance(layers, dict):
            raise ValueError(f"{label}: layers must be a dict")
        if set(layers.keys()) != set(ALLOWED_LAYERS):
            raise ValueError(f"{label}: layers keys must be {ALLOWED_LAYERS}")
        for layer in ALLOWED_LAYERS:
            if not isinstance(layers[layer], list):
                raise ValueError(f"{label}: layers[{layer}] must be a list")
        return layers

    snap_layers = _check_layers(snapshot, "snapshot")
    prompt_layers = _check_layers(prompt, "prompt")

    for layer in ALLOWED_LAYERS:
        snap_items = snap_layers[layer]
        snap_ids = []
        for item in snap_items:
            if not isinstance(item, dict):
                raise ValueError(f"snapshot: items in {layer} must be objects")
            if item.get("default_enabled") is not True:
                raise ValueError(f"snapshot: default_enabled must be true in {layer}")
            if not isinstance(item.get("id"), str):
                raise ValueError(f"snapshot: id must be string in {layer}")
            snap_ids.append(item["id"])
        if snap_ids != sorted(snap_ids):
            raise ValueError(f"snapshot: ids not sorted in {layer}")

        prompt_items = prompt_layers[layer]
        prompt_ids = []
        for item in prompt_items:
            if not isinstance(item, dict):
                raise ValueError(f"prompt: items in {layer} must be objects")
            for key in ("id", "name", "desc_1l"):
                if key not in item or not isinstance(item[key], str):
                    raise ValueError(f"prompt: {key} must be string in {layer}")
            desc = item["desc_1l"]
            if "\n" in desc or "\r" in desc:
                raise ValueError(f"prompt: desc_1l contains newline in {layer}")
            if len(desc) > 140:
                raise ValueError(f"prompt: desc_1l longer than 140 chars in {layer}")
            prompt_ids.append(item["id"])
        if prompt_ids != sorted(prompt_ids):
            raise ValueError(f"prompt: ids not sorted in {layer}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Export enabled agent catalog snapshot.")
    parser.add_argument("--agents-dir", default="config/agents", help="Directory containing agent_*.json")
    parser.add_argument("--out-dir", default="data/catalogs", help="Output directory for catalog JSON files")
    parser.add_argument("--date", default=None, help="Date override (YYYYMMDD)")
    parser.add_argument("--self-check", action="store_true", help="Validate output after writing")
    args = parser.parse_args()

    agents_dir = Path(args.agents_dir)
    out_dir = Path(args.out_dir)

    agents = _load_agents(agents_dir)
    enabled_agents = [a for a in agents if a["default_enabled"] is True]

    layers = _group_by_layer(enabled_agents)
    hash12 = _canonical_hash(enabled_agents)
    date_str = args.date or datetime.now().strftime("%Y%m%d")
    catalog_id = f"{date_str}_{hash12}"

    out_dir.mkdir(parents=True, exist_ok=True)

    snapshot_path = out_dir / f"catalog_{catalog_id}.json"
    prompt_path = out_dir / f"catalog_{catalog_id}_prompt.json"

    snapshot_payload = {
        "catalog_id": catalog_id,
        "generated_at": datetime.now().isoformat(),
        "source_dir": str(agents_dir),
        "layers": layers,
    }

    prompt_layers: Dict[str, List[Dict[str, str]]] = {k: [] for k in ALLOWED_LAYERS}
    for layer in ALLOWED_LAYERS:
        for agent in layers[layer]:
            prompt_layers[layer].append(
                {
                    "id": agent["id"],
                    "name": agent["name"],
                    "desc_1l": _desc_1l(agent["description"]),
                }
            )
        prompt_layers[layer].sort(key=lambda a: a["id"])

    prompt_payload = {
        "catalog_id": catalog_id,
        "layers": prompt_layers,
    }

    _write_json(snapshot_path, snapshot_payload)
    _write_json(prompt_path, prompt_payload)

    latest_path = _write_latest(out_dir, catalog_id)

    if args.self_check:
        _self_check(snapshot_path, prompt_path)
        _check_latest(latest_path, catalog_id)

    total_enabled = len(enabled_agents)
    counts = {layer: len(layers[layer]) for layer in ALLOWED_LAYERS}
    print(f"catalog_id: {catalog_id}")
    print(
        "enabled_total: {total} (L1={L1}, L2={L2}, L3={L3}, L4={L4})".format(
            total=total_enabled, **counts
        )
    )
    print(f"snapshot_path: {snapshot_path} (abs: {snapshot_path.resolve()})")
    print(f"prompt_path: {prompt_path} (abs: {prompt_path.resolve()})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
