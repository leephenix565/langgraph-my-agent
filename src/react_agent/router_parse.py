"""Router parsing helpers shared by runtime and offline evaluation."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Tuple

LAYER_ORDER: List[str] = ["L1", "L2", "L3", "L4"]
DEFAULT_MODES: Dict[str, str] = {"L1": "Chain", "L2": "Star", "L3": "Star", "L4": "Chain"}
LEGACY_LAYER_MAP: Dict[str, str] = {"L4": "L3", "L5": "L4"}
SPECIAL_FALLBACK_BY_LAYER: Dict[str, List[str]] = {
    "L1": ["a01_cio_orchestrator"],
    "L4": ["a25_report_center"],
}


def normalize_mode(mode: Any) -> str:
    """Return a single valid mode (Star/Chain/Debate/Tree) with light tolerance."""
    allowed = {"star", "chain", "debate", "tree"}
    if not mode:
        return "Star"
    raw = str(mode).strip()
    for sep in [",", ";", "|", "/"]:
        if sep in raw:
            raw = raw.split(sep)[0]
            break
    raw = raw.strip().split()[0]
    token = raw.lower()
    if token in allowed:
        return token.title()
    return "Star"


def extract_json_str(text: str) -> Optional[str]:
    """Best-effort extract a JSON object string; return None if not parseable."""
    try:
        json.loads(text)
        return text
    except Exception:
        pass

    first = text.find("{")
    last = text.rfind("}")
    if first == -1 or last == -1 or last <= first:
        return None
    candidate = text[first : last + 1]
    try:
        json.loads(candidate)
        return candidate
    except Exception:
        return None


def _normalize_agent_catalog(agent_catalog: Dict[str, Any]) -> Dict[str, List[str]]:
    """Return a layer -> agent ids catalog from layer maps or metadata maps."""
    normalized: Dict[str, List[str]] = {layer: [] for layer in LAYER_ORDER}
    if any(layer in agent_catalog for layer in LAYER_ORDER):
        for layer in LAYER_ORDER:
            raw_ids = agent_catalog.get(layer, [])
            if isinstance(raw_ids, list):
                normalized[layer] = [aid for aid in raw_ids if isinstance(aid, str)]
        return normalized

    for fallback_id, meta in agent_catalog.items():
        if not isinstance(fallback_id, str):
            continue
        if isinstance(meta, dict):
            layer = str(meta.get("layer", "") or "").upper()
            enabled = bool(meta.get("default_enabled", True))
            agent_id = str(meta.get("id", fallback_id) or "")
        else:
            layer = str(getattr(meta, "layer", "") or "").upper()
            enabled = bool(getattr(meta, "default_enabled", True))
            agent_id = str(getattr(meta, "id", fallback_id) or "")
        if enabled and layer in normalized and agent_id:
            normalized[layer].append(agent_id)
    return normalized


def default_layer_plan(
    agent_catalog: Dict[str, Any],
) -> Tuple[Dict[str, List[str]], Dict[str, str]]:
    """Fail closed on Router parse failure: special management/report roles only."""
    normalized_catalog = _normalize_agent_catalog(agent_catalog)
    plan: Dict[str, List[str]] = {}
    modes: Dict[str, str] = {}
    for layer in LAYER_ORDER:
        modes[layer] = DEFAULT_MODES.get(layer, "Star")
        allowed_ids = set(normalized_catalog.get(layer, []))
        plan[layer] = [
            agent_id
            for agent_id in SPECIAL_FALLBACK_BY_LAYER.get(layer, [])
            if agent_id in allowed_ids
        ]
    return plan, modes


def parse_router_layers_with_stats(
    raw: str,
    agent_catalog: Optional[Dict[str, List[str]]] = None,
) -> Tuple[Dict[str, List[str]], Dict[str, str], Dict[str, Any]]:
    """Parse router JSON into layer_plan/layer_mode with parse stats."""
    agent_catalog = _normalize_agent_catalog(agent_catalog or {})
    default_plan, default_modes = default_layer_plan(agent_catalog)
    stats: Dict[str, Any] = {
        "parse_ok": False,
        "used_default_plan": False,
        "fallback_reason": None,
        "l2_truncated": 0,
        "filtered_agents": 0,
    }

    json_str = extract_json_str(raw or "")
    if not json_str:
        stats["used_default_plan"] = True
        stats["fallback_reason"] = "parse_failed"
        return default_plan, default_modes, stats
    try:
        parsed = json.loads(json_str)
    except Exception:
        stats["used_default_plan"] = True
        stats["fallback_reason"] = "parse_failed"
        return default_plan, default_modes, stats

    if not isinstance(parsed, dict):
        stats["used_default_plan"] = True
        stats["fallback_reason"] = "parse_failed"
        return default_plan, default_modes, stats

    allowed_by_layer = {
        layer: set(agent_catalog.get(layer, [])) for layer in LAYER_ORDER
    }

    if "layers" not in parsed and "selected" in parsed:
        plan, modes = default_layer_plan(agent_catalog)
        selected_raw = parsed.get("selected", [])
        selected: List[str] = []
        if isinstance(selected_raw, list):
            for aid in selected_raw:
                if not isinstance(aid, str):
                    stats["filtered_agents"] += 1
                    continue
                if aid in allowed_by_layer.get("L2", set()):
                    selected.append(aid)
                else:
                    stats["filtered_agents"] += 1
        if selected_raw and not selected:
            selected = plan.get("L2", [])
        if len(selected) > 5:
            stats["l2_truncated"] += len(selected) - 5
            selected = selected[:5]
        plan["L2"] = selected or plan.get("L2", [])
        modes["L2"] = "Star"
        stats["parse_ok"] = True
        return plan, modes, stats

    layers_raw = parsed.get("layers")
    if not isinstance(layers_raw, list):
        stats["used_default_plan"] = True
        stats["fallback_reason"] = "parse_failed"
        return default_plan, default_modes, stats

    legacy_mode = any(
        isinstance(entry, dict)
        and isinstance(entry.get("layer"), str)
        and entry.get("layer").strip() == "L5"
        for entry in layers_raw
    )

    layer_plan: Dict[str, List[str]] = {}
    layer_mode: Dict[str, str] = {}
    for layer_entry in layers_raw:
        if not isinstance(layer_entry, dict):
            continue
        layer = layer_entry.get("layer")
        if isinstance(layer, str):
            layer = layer.strip()
            if legacy_mode:
                layer = LEGACY_LAYER_MAP.get(layer, layer)
        if not layer or layer not in LAYER_ORDER:
            continue
        mode = normalize_mode(layer_entry.get("mode"))
        selected_raw = layer_entry.get("selected", []) or []
        selected: List[str] = []
        if isinstance(selected_raw, list):
            for aid in selected_raw:
                if not isinstance(aid, str):
                    stats["filtered_agents"] += 1
                    continue
                if aid in allowed_by_layer.get(layer, set()):
                    selected.append(aid)
                else:
                    stats["filtered_agents"] += 1
        if selected_raw and not selected:
            selected = default_plan.get(layer, [])
        if layer == "L2" and len(selected) > 5:
            stats["l2_truncated"] += len(selected) - 5
            selected = selected[:5]
        layer_plan[layer] = selected
        layer_mode[layer] = mode

    for layer in LAYER_ORDER:
        layer_plan.setdefault(layer, default_plan.get(layer, []))
        layer_mode.setdefault(layer, default_modes.get(layer, "Star"))

    stats["parse_ok"] = True
    return layer_plan, layer_mode, stats


def parse_router_layers(
    raw: str,
    agent_catalog: Optional[Dict[str, List[str]]] = None,
) -> Tuple[Dict[str, List[str]], Dict[str, str]]:
    plan, modes, _stats = parse_router_layers_with_stats(raw, agent_catalog)
    return plan, modes
