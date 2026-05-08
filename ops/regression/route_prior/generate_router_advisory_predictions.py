#!/usr/bin/env python
"""Generate optional Router advisory prediction artifacts.

This tool is offline/ops-only. It does not modify runtime Router behavior, does
not change the Router prompt constant, and does not persist full prompt bodies.
Dry-run mode is network-free and writes deterministic valid Router JSON so the
RP-3A A/B replay harness can validate artifact wiring without provider access.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import sys
import time
from collections.abc import Mapping, Sequence
from contextlib import contextmanager
from pathlib import Path
from typing import Any

JsonDict = dict[str, Any]
JsonMapping = Mapping[str, Any]
DRY_RUN_MODE = "dry-run"
LIVE_MODE = "live"
LABEL_STUB_SOURCE = "label_stub"
PROVIDED_ARTIFACT_SOURCE = "provided_artifact"
RARP_SHADOW_SOURCE = "rarp_shadow"
PROVIDED_ARTIFACT_MISSING_SUFFIX = "_missing"
NOOP_STATUS = "noop_no_advisory"
WILDCARD_ONLY_NOOP_STATUS = "noop_wildcard_only"
WEAK_NON_WILDCARD_FALLBACK = "weak_non_wildcard_fallback"
WEAK_FALLBACK_MAX_AGENTS = 5
ADVISORY_SOURCE_CHOICES = (
    LABEL_STUB_SOURCE,
    PROVIDED_ARTIFACT_SOURCE,
    RARP_SHADOW_SOURCE,
)
DEFAULT_MODEL_ENV_KEYS = (
    "ROUTER_MODEL",
    "REACT_AGENT_ROUTER_MODEL",
    "REACT_AGENT_MODEL",
    "MODEL",
)


def _find_repo_root(start: Path) -> Path:
    for candidate in (start, *start.parents):
        if (candidate / "pyproject.toml").exists():
            return candidate
    raise RuntimeError(f"Could not locate repo root from {start}")


REPO_ROOT = _find_repo_root(Path(__file__).resolve().parent)
SRC_DIR = REPO_ROOT / "src"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from ops.regression.route_prior.run_route_prior_eval import (  # noqa: E402
    LabelCase,
    load_label_cases,
)
from ops.regression.route_prior.run_router_advisory_ab import (  # noqa: E402
    PREDICTION_SCHEMA_VERSION,
    default_raw_for_expected_layers,
    load_agent_catalog,
    load_expected_layers_by_case,
    question_hash,
    render_advisory_prompt,
    render_baseline_prompt,
    write_json,
    write_jsonl,
)
from react_agent.utils import get_message_text, load_chat_model  # noqa: E402


def stable_hash(value: str) -> str:
    """Return a stable sha256 hash string."""
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


def stable_file_hash(path: Path | None) -> str | None:
    """Return a stable sha256 hash for an optional local artifact."""
    if path is None or not path.exists():
        return None
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def catalog_hash(agent_catalog: Mapping[str, Sequence[str]]) -> str:
    """Return a stable hash for the formal Router catalog."""
    payload = json.dumps(
        {layer: list(agent_catalog.get(layer, [])) for layer in sorted(agent_catalog)},
        ensure_ascii=False,
        sort_keys=True,
    )
    return stable_hash(payload)


def prompt_text(system_prompt: str, question: str) -> str:
    """Serialize the offline prompt representation without persisting it."""
    return json.dumps(
        [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": question},
        ],
        ensure_ascii=False,
        sort_keys=True,
    )


def prompt_messages(system_prompt: str, question: str) -> list[dict[str, str]]:
    """Return chat messages for the Router model call."""
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": question},
    ]


def side_metadata(
    *,
    raw: str,
    model_spec: str,
    prompt_payload: str,
    catalog_hash_value: str,
    latency_ms: float | None,
    token_count: int | None,
) -> JsonDict:
    """Build one enriched prediction side without prompt body fields."""
    model_name = model_spec.split("/", maxsplit=1)[-1] if model_spec else None
    return {
        "raw": raw,
        "model_name": model_name,
        "model_spec": model_spec or None,
        "prompt_chars": len(prompt_payload),
        "token_count": token_count,
        "latency_ms": latency_ms,
        "prompt_hash": stable_hash(prompt_payload),
        "catalog_hash": catalog_hash_value,
    }


def _as_mapping(value: Any) -> JsonMapping:
    return value if isinstance(value, Mapping) else {}


def _as_str_list(value: Any) -> list[str]:
    if not isinstance(value, Sequence) or isinstance(value, str):
        return []
    result: list[str] = []
    seen: set[str] = set()
    for item in value:
        normalized = str(item).strip()
        if normalized and normalized not in seen:
            result.append(normalized)
            seen.add(normalized)
    return result


def _ordered_unique(values: Sequence[Any]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        normalized = str(value).strip()
        if normalized and normalized not in seen:
            result.append(normalized)
            seen.add(normalized)
    return result


def _agent_layer_lookup(agent_catalog: Mapping[str, Sequence[str]]) -> dict[str, str]:
    lookup: dict[str, str] = {}
    for layer, agent_ids in agent_catalog.items():
        for agent_id in agent_ids:
            normalized = str(agent_id).strip()
            if normalized:
                lookup[normalized] = str(layer)
    return lookup


def _group_agents_by_layer(
    agent_ids: Sequence[str],
    *,
    agent_catalog: Mapping[str, Sequence[str]],
) -> JsonDict:
    lookup = _agent_layer_lookup(agent_catalog)
    groups: dict[str, list[str]] = {layer: [] for layer in ("L1", "L2", "L3", "L4")}
    unlayered: list[str] = []
    for agent_id in _ordered_unique(agent_ids):
        layer = lookup.get(agent_id)
        if layer in groups:
            groups[layer].append(agent_id)
        else:
            unlayered.append(agent_id)
    result: JsonDict = {layer: ids for layer, ids in groups.items() if ids}
    if unlayered:
        result["unlayered"] = unlayered
    return result


def _extract_route_reliability_shadow(record: JsonMapping) -> JsonMapping:
    """Extract RP-2B/RP-2C route reliability shadow from known artifact shapes."""
    candidates: list[Any] = [
        record.get("route_reliability"),
        record.get("route_reliability_shadow"),
        record.get("route_reliability_shadow_v0"),
        record.get("payload"),
        record.get("data"),
        record,
    ]
    for candidate in candidates:
        mapping = _as_mapping(candidate)
        if not mapping:
            continue
        schema = str(mapping.get("schema_version") or "")
        if schema == "route_reliability_shadow_v0":
            return mapping
        if "cards" in mapping and "groups" in mapping:
            return mapping
    return {}


def load_advisory_artifact(path: Path | None) -> dict[str, JsonDict]:
    """Load optional RP-2 route-prior/reliability artifacts keyed by case id."""
    if path is None or not path.exists():
        return {}
    records: dict[str, JsonDict] = {}
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        text = line.strip()
        if not text:
            continue
        payload = json.loads(text)
        if not isinstance(payload, Mapping):
            raise ValueError(f"Advisory artifact line {line_no} is not an object")
        case_id = payload.get("id") or payload.get("case_id")
        if isinstance(case_id, str) and case_id.strip():
            records[case_id.strip()] = dict(payload)
    return records


def _shadow_cards(shadow: JsonMapping) -> list[JsonMapping]:
    cards = shadow.get("cards")
    if not isinstance(cards, list):
        return []
    return [card for card in cards if isinstance(card, Mapping)]


def _shadow_groups(shadow: JsonMapping) -> JsonMapping:
    return _as_mapping(shadow.get("groups"))


def _group_ids(groups: JsonMapping, key: str) -> list[str]:
    return _as_str_list(groups.get(key))


def _card_agent_id(card: JsonMapping) -> str:
    return str(card.get("agent_id", "") or "").strip()


def _wildcard_agent_ids(shadow: JsonMapping) -> list[str]:
    groups = _shadow_groups(shadow)
    wildcard_ids = _group_ids(groups, "wildcard")
    if wildcard_ids:
        return wildcard_ids
    return _ordered_unique(
        _card_agent_id(card)
        for card in _shadow_cards(shadow)
        if bool(card.get("wildcard_flag", False))
    )


def _ranked_agent_ids(record: JsonMapping, shadow: JsonMapping) -> list[str]:
    ranked_ids = _as_str_list(record.get("top_ranked_ids"))
    if ranked_ids:
        return ranked_ids
    for key in ("route_scores_top10", "route_scores_all_light"):
        scores = record.get(key)
        if isinstance(scores, list):
            ids = _ordered_unique(
                item.get("agent_id")
                for item in scores
                if isinstance(item, Mapping)
            )
            if ids:
                return ids
    return _ordered_unique(_card_agent_id(card) for card in _shadow_cards(shadow))


def _top_non_wildcard_agent_ids(
    record: JsonMapping,
    shadow: JsonMapping,
    *,
    max_agents: int = WEAK_FALLBACK_MAX_AGENTS,
) -> list[str]:
    cards_by_id = {
        _card_agent_id(card): card
        for card in _shadow_cards(shadow)
        if _card_agent_id(card)
    }
    selected: list[str] = []
    for agent_id in _ranked_agent_ids(record, shadow):
        card = cards_by_id.get(agent_id)
        if not card or bool(card.get("wildcard_flag", False)):
            continue
        selected.append(agent_id)
        if len(selected) >= max_agents:
            break
    return _ordered_unique(selected)


def _artifact_advisory_selection(
    record: JsonMapping,
    shadow: JsonMapping,
    *,
    max_agents: int = 8,
) -> JsonDict:
    groups = _shadow_groups(shadow)
    priority_ids = _ordered_unique(
        _group_ids(groups, "strongly_recommended") + _group_ids(groups, "candidate")
    )
    wildcard_ids = _wildcard_agent_ids(shadow)
    if priority_ids:
        return {
            "agent_ids": priority_ids[:max_agents],
            "secondary_agent_ids": [agent_id for agent_id in wildcard_ids if agent_id not in priority_ids],
            "selection_reason": "priority_groups",
            "advisory_status_suffix": "applied",
            "advisory_applied": True,
        }

    fallback_ids = _top_non_wildcard_agent_ids(record, shadow, max_agents=WEAK_FALLBACK_MAX_AGENTS)
    if fallback_ids:
        return {
            "agent_ids": fallback_ids[:max_agents],
            "secondary_agent_ids": [agent_id for agent_id in wildcard_ids if agent_id not in fallback_ids],
            "selection_reason": WEAK_NON_WILDCARD_FALLBACK,
            "advisory_status_suffix": WEAK_NON_WILDCARD_FALLBACK,
            "advisory_applied": True,
        }

    if wildcard_ids:
        return {
            "agent_ids": [],
            "secondary_agent_ids": wildcard_ids[:max_agents],
            "selection_reason": WILDCARD_ONLY_NOOP_STATUS,
            "advisory_status_suffix": WILDCARD_ONLY_NOOP_STATUS,
            "advisory_applied": False,
        }

    return {
        "agent_ids": [],
        "secondary_agent_ids": [],
        "selection_reason": "reliability_cards_empty",
        "advisory_status_suffix": "missing",
        "advisory_applied": False,
    }


def _reason_codes_by_agent(shadow: JsonMapping, agent_ids: Sequence[str]) -> JsonDict:
    selected = set(agent_ids)
    reason_codes: JsonDict = {}
    for card in _shadow_cards(shadow):
        agent_id = str(card.get("agent_id", "") or "").strip()
        if not agent_id or agent_id not in selected:
            continue
        reason_codes[agent_id] = _as_str_list(card.get("reason_codes"))
    return reason_codes


def build_provided_advisory_context(
    *,
    case_id: str,
    requested_source: str,
    artifact_path: Path | None,
    artifact_hash_value: str | None,
    records: Mapping[str, JsonMapping],
    agent_catalog: Mapping[str, Sequence[str]],
) -> JsonDict:
    """Build safe prompt metadata from a provided RP-2 reliability artifact."""
    artifact_path_text = str(artifact_path) if artifact_path is not None else None
    base: JsonDict = {
        "advisory_source": f"{requested_source}{PROVIDED_ARTIFACT_MISSING_SUFFIX}",
        "advisory_status": f"{requested_source}_missing",
        "advisory_applied": False,
        "advisory_noop_reason": NOOP_STATUS,
        "advisory_artifact_path": artifact_path_text,
        "advisory_artifact_hash": artifact_hash_value,
        "advisory_case_found": False,
        "advisory_confidence_band": "",
        "advisory_low_confidence_fallback": None,
        "advisory_agent_ids": [],
        "advisory_reason_codes": {},
        "advisory_retrieval_enabled": None,
        "advisory_retrieval_reason": "",
        "advisory_missing_reason": "artifact_not_configured" if artifact_path is None else "case_not_found",
        "groups_by_layer": {},
        "secondary_groups_by_layer": {},
        "advisory_secondary_agent_ids": [],
        "advisory_selection_reason": "",
    }
    record = records.get(case_id)
    if not record:
        return base

    shadow = _extract_route_reliability_shadow(record)
    base["advisory_case_found"] = True
    base["advisory_retrieval_enabled"] = record.get("enabled")
    base["advisory_retrieval_reason"] = str(record.get("retrieval_reason", "") or "")
    if not shadow:
        base["advisory_missing_reason"] = "route_reliability_missing"
        return base

    confidence_band = str(shadow.get("confidence_band", "") or record.get("confidence_band", "") or "")
    low_confidence_fallback = bool(
        shadow.get("low_confidence_fallback", record.get("low_confidence_fallback", False))
    )
    base["advisory_confidence_band"] = confidence_band
    base["advisory_low_confidence_fallback"] = low_confidence_fallback
    if record.get("enabled") is False:
        base["advisory_source"] = f"{requested_source}_disabled"
        base["advisory_status"] = f"{requested_source}_disabled"
        base["advisory_missing_reason"] = "retrieval_disabled"
        return base
    if low_confidence_fallback or confidence_band == "low":
        base["advisory_source"] = f"{requested_source}_low_confidence"
        base["advisory_status"] = f"{requested_source}_low_confidence"
        base["advisory_missing_reason"] = (
            "low_confidence_fallback" if low_confidence_fallback else "low_confidence"
        )
        return base
    selection = _artifact_advisory_selection(record, shadow)
    agent_ids = _as_str_list(selection.get("agent_ids"))
    secondary_agent_ids = _as_str_list(selection.get("secondary_agent_ids"))
    base.update(
        {
            "advisory_agent_ids": agent_ids,
            "advisory_reason_codes": _reason_codes_by_agent(shadow, agent_ids),
            "groups_by_layer": _group_agents_by_layer(agent_ids, agent_catalog=agent_catalog),
            "advisory_secondary_agent_ids": secondary_agent_ids,
            "secondary_groups_by_layer": _group_agents_by_layer(
                secondary_agent_ids,
                agent_catalog=agent_catalog,
            ),
            "advisory_selection_reason": str(selection.get("selection_reason", "") or ""),
        }
    )
    if not agent_ids:
        if secondary_agent_ids:
            base["advisory_source"] = f"{requested_source}_wildcard_only"
            base["advisory_status"] = WILDCARD_ONLY_NOOP_STATUS
            base["advisory_noop_reason"] = WILDCARD_ONLY_NOOP_STATUS
            base["advisory_missing_reason"] = "wildcard_only"
        else:
            base["advisory_missing_reason"] = "reliability_cards_empty"
        return base
    base["advisory_source"] = requested_source
    status_suffix = str(selection.get("advisory_status_suffix", "applied") or "applied")
    base["advisory_status"] = f"{requested_source}_{status_suffix}"
    base["advisory_applied"] = True
    base["advisory_noop_reason"] = ""
    base["advisory_missing_reason"] = ""
    return base


def label_stub_metadata() -> JsonDict:
    """Return neutral metadata for the label-derived smoke advisory."""
    return {
        "advisory_artifact_path": None,
        "advisory_artifact_hash": None,
        "advisory_applied": True,
        "advisory_status": "label_stub_applied",
        "advisory_noop_reason": "",
        "advisory_case_found": None,
        "advisory_confidence_band": None,
        "advisory_low_confidence_fallback": None,
        "advisory_agent_ids": [],
        "advisory_reason_codes": {},
        "advisory_retrieval_enabled": None,
        "advisory_retrieval_reason": "",
        "advisory_missing_reason": "",
    }


def render_provided_advisory_prompt(
    baseline_prompt: str,
    *,
    context: JsonMapping,
) -> str:
    """Render a compact non-runtime advisory block from RP-2 artifacts only."""
    if not bool(context.get("advisory_applied", False)):
        return baseline_prompt
    advisory = {
        "mode": "offline_provided_artifact_rarp_shadow",
        "non_binding": True,
        "advisory_source": context.get("advisory_source"),
        "case_found": bool(context.get("advisory_case_found", False)),
        "confidence_band": context.get("advisory_confidence_band") or "",
        "low_confidence_fallback": context.get("advisory_low_confidence_fallback"),
        "advisory_agents_by_layer": context.get("groups_by_layer") or {},
        "secondary_agents_by_layer": context.get("secondary_groups_by_layer") or {},
        "selection_reason": context.get("advisory_selection_reason") or "",
        "reason_codes_by_agent": context.get("advisory_reason_codes") or {},
        "missing_reason": context.get("advisory_missing_reason") or "",
        "instruction": (
            "Use this provided route-prior advisory as a non-binding prior only. "
            "Treat weak fallback candidates as tentative domain recall hints, not mandatory selections. "
            "Secondary agents are context only and must not be the sole basis for selection. "
            "Only select each advisory agent in the layer where it is listed. "
            "Do not move L3 agents into L2 or L2 agents into L3. "
            "If no advisory agent is listed, rely on the full catalog and your best judgment. "
            "Return only the existing Router JSON schema."
        ),
    }
    block = "\n\nRoute prior advisory, non-binding (provided artifact):\n"
    block += json.dumps(advisory, ensure_ascii=False, sort_keys=True)
    return baseline_prompt + block


def render_prompt_for_source(
    *,
    baseline_prompt: str,
    case: LabelCase,
    agent_catalog: Mapping[str, Sequence[str]],
    expected_layers: Mapping[str, Any] | None,
    advisory_source: str,
    advisory_context: JsonMapping | None,
) -> str:
    """Render the advisory prompt for a selected offline source."""
    if advisory_source == LABEL_STUB_SOURCE:
        return render_advisory_prompt(
            baseline_prompt,
            case,
            agent_catalog=agent_catalog,
            expected_layers=expected_layers,
        )
    return render_provided_advisory_prompt(
        baseline_prompt,
        context=_as_mapping(advisory_context),
    )


def expected_layers_for_case(
    case: LabelCase,
    expected_layers: Mapping[str, Any] | None,
) -> Mapping[str, Any]:
    """Return expected layers or a label-derived fallback for smoke artifacts."""
    if isinstance(expected_layers, Mapping):
        return expected_layers
    return {"L2": list(case.must_include_agents or case.expected_agents), "L3": []}


def build_dry_run_prediction(
    case: LabelCase,
    *,
    agent_catalog: Mapping[str, Sequence[str]],
    expected_layers: Mapping[str, Any] | None,
    model_spec: str,
    advisory_source: str,
    advisory_context: JsonMapping | None = None,
) -> JsonDict:
    """Build one deterministic network-free prediction record."""
    baseline_prompt = render_baseline_prompt(agent_catalog)
    advisory_prompt = render_prompt_for_source(
        baseline_prompt=baseline_prompt,
        case=case,
        agent_catalog=agent_catalog,
        expected_layers=expected_layers,
        advisory_source=advisory_source,
        advisory_context=advisory_context,
    )
    layers = expected_layers_for_case(case, expected_layers)
    catalog_hash_value = catalog_hash(agent_catalog)
    baseline_payload = prompt_text(baseline_prompt, case.question)
    advisory_payload = prompt_text(advisory_prompt, case.question)
    advisory_metadata = label_stub_metadata() if advisory_source == LABEL_STUB_SOURCE else dict(advisory_context or {})
    advisory_applied = bool(advisory_metadata.get("advisory_applied", True))
    baseline_side = side_metadata(
        raw=default_raw_for_expected_layers(layers, side="baseline"),
        model_spec=model_spec,
        prompt_payload=baseline_payload,
        catalog_hash_value=catalog_hash_value,
        latency_ms=0.0,
        token_count=None,
    )
    advisory_side = (
        side_metadata(
            raw=default_raw_for_expected_layers(layers, side="advisory"),
            model_spec=model_spec,
            prompt_payload=advisory_payload,
            catalog_hash_value=catalog_hash_value,
            latency_ms=0.0,
            token_count=None,
        )
        if advisory_applied
        else dict(baseline_side)
    )
    return {
        "schema_version": PREDICTION_SCHEMA_VERSION,
        "id": case.case_id,
        "question_hash": question_hash(case.question),
        "advisory_source": advisory_metadata.get("advisory_source", advisory_source),
        **{
            key: advisory_metadata.get(key)
            for key in (
                "advisory_artifact_path",
                "advisory_artifact_hash",
                "advisory_applied",
                "advisory_status",
                "advisory_noop_reason",
                "advisory_case_found",
                "advisory_confidence_band",
                "advisory_low_confidence_fallback",
                "advisory_agent_ids",
                "advisory_reason_codes",
                "advisory_retrieval_enabled",
                "advisory_retrieval_reason",
                "advisory_missing_reason",
                "advisory_secondary_agent_ids",
                "advisory_selection_reason",
            )
        },
        "baseline": baseline_side,
        "advisory": advisory_side,
    }


def _token_count_from_response(response: Any) -> int | None:
    """Extract total token count from common LangChain response metadata shapes."""
    usage_metadata = getattr(response, "usage_metadata", None)
    if isinstance(usage_metadata, Mapping):
        total = usage_metadata.get("total_tokens")
        if isinstance(total, int):
            return total
        input_tokens = usage_metadata.get("input_tokens")
        output_tokens = usage_metadata.get("output_tokens")
        if isinstance(input_tokens, int) and isinstance(output_tokens, int):
            return input_tokens + output_tokens
    response_metadata = getattr(response, "response_metadata", None)
    if isinstance(response_metadata, Mapping):
        token_usage = response_metadata.get("token_usage") or response_metadata.get("usage")
        if isinstance(token_usage, Mapping):
            total = token_usage.get("total_tokens") or token_usage.get("total")
            if isinstance(total, int):
                return total
    return None


@contextmanager
def temporary_openai_env(base_url: str, api_key_value: str | None):
    """Temporarily set OpenAI-compatible env vars for one optional-live call."""
    previous: dict[str, tuple[bool, str | None]] = {}
    updates: dict[str, str] = {}
    if base_url:
        updates["OPENAI_BASE_URL"] = base_url
    if api_key_value:
        updates["OPENAI_API_KEY"] = api_key_value
    for key, value in updates.items():
        previous[key] = (key in os.environ, os.environ.get(key))
        os.environ[key] = value
    try:
        yield
    finally:
        for key, (had_value, old_value) in previous.items():
            if had_value and old_value is not None:
                os.environ[key] = old_value
            else:
                os.environ.pop(key, None)


async def invoke_router_side(
    *,
    model_spec: str,
    system_prompt: str,
    question: str,
    base_url: str,
    api_key_value: str | None,
) -> tuple[str, float, int | None]:
    """Invoke one Router side and return raw text, latency, and tokens."""
    messages = prompt_messages(system_prompt, question)
    started_at = time.perf_counter()
    with temporary_openai_env(base_url, api_key_value):
        model = load_chat_model(model_spec)
        response = await model.ainvoke(messages)
    latency_ms = (time.perf_counter() - started_at) * 1000
    return get_message_text(response), latency_ms, _token_count_from_response(response)


async def build_live_prediction(
    case: LabelCase,
    *,
    agent_catalog: Mapping[str, Sequence[str]],
    expected_layers: Mapping[str, Any] | None,
    model_spec: str,
    base_url: str,
    api_key_value: str | None,
    advisory_source: str,
    advisory_context: JsonMapping | None = None,
) -> JsonDict:
    """Build one optional-live prediction record."""
    baseline_prompt = render_baseline_prompt(agent_catalog)
    advisory_prompt = render_prompt_for_source(
        baseline_prompt=baseline_prompt,
        case=case,
        agent_catalog=agent_catalog,
        expected_layers=expected_layers,
        advisory_source=advisory_source,
        advisory_context=advisory_context,
    )
    catalog_hash_value = catalog_hash(agent_catalog)
    baseline_payload = prompt_text(baseline_prompt, case.question)
    advisory_payload = prompt_text(advisory_prompt, case.question)
    baseline_raw, baseline_latency, baseline_tokens = await invoke_router_side(
        model_spec=model_spec,
        system_prompt=baseline_prompt,
        question=case.question,
        base_url=base_url,
        api_key_value=api_key_value,
    )
    advisory_metadata = advisory_context or label_stub_metadata()
    advisory_applied = bool(advisory_metadata.get("advisory_applied", True))
    if advisory_applied:
        advisory_raw, advisory_latency, advisory_tokens = await invoke_router_side(
            model_spec=model_spec,
            system_prompt=advisory_prompt,
            question=case.question,
            base_url=base_url,
            api_key_value=api_key_value,
        )
    else:
        advisory_raw = baseline_raw
        advisory_latency = baseline_latency
        advisory_tokens = baseline_tokens
    return {
        "schema_version": PREDICTION_SCHEMA_VERSION,
        "id": case.case_id,
        "question_hash": question_hash(case.question),
        "advisory_source": advisory_metadata.get("advisory_source", advisory_source),
        **{
            key: advisory_metadata.get(key)
            for key in (
                "advisory_artifact_path",
                "advisory_artifact_hash",
                "advisory_applied",
                "advisory_status",
                "advisory_noop_reason",
                "advisory_case_found",
                "advisory_confidence_band",
                "advisory_low_confidence_fallback",
                "advisory_agent_ids",
                "advisory_reason_codes",
                "advisory_retrieval_enabled",
                "advisory_retrieval_reason",
                "advisory_missing_reason",
                "advisory_secondary_agent_ids",
                "advisory_selection_reason",
            )
        },
        "baseline": side_metadata(
            raw=baseline_raw,
            model_spec=model_spec,
            prompt_payload=baseline_payload,
            catalog_hash_value=catalog_hash_value,
            latency_ms=baseline_latency,
            token_count=baseline_tokens,
        ),
        "advisory": side_metadata(
            raw=advisory_raw,
            model_spec=model_spec,
            prompt_payload=advisory_payload,
            catalog_hash_value=catalog_hash_value,
            latency_ms=advisory_latency,
            token_count=advisory_tokens,
        ),
    }


def _numbers(records: Sequence[JsonMapping], field: str) -> list[float]:
    values: list[float] = []
    for record in records:
        baseline = record.get("baseline", {})
        advisory = record.get("advisory", {})
        if not isinstance(baseline, Mapping) or not isinstance(advisory, Mapping):
            continue
        for side in (baseline, advisory):
            value = side.get(field)
            if isinstance(value, int | float) and not isinstance(value, bool):
                values.append(float(value))
    return values


def _percentile(values: Sequence[float], percentile: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    rank = round((percentile / 100) * (len(ordered) - 1))
    return ordered[int(rank)]


def token_metadata_complete_count(records: Sequence[JsonMapping]) -> int:
    """Count records with token metadata for both Router sides."""
    count = 0
    for record in records:
        baseline = record.get("baseline", {})
        advisory = record.get("advisory", {})
        if not isinstance(baseline, Mapping) or not isinstance(advisory, Mapping):
            continue
        if baseline.get("token_count") is not None and advisory.get("token_count") is not None:
            count += 1
    return count


def build_summary(
    *,
    status: str,
    mode: str,
    dataset: Path,
    out: Path,
    records: Sequence[JsonMapping],
    case_count: int,
    skipped_count: int,
    model_spec: str,
    missing_env_reason: str | None = None,
    error_message: str | None = None,
) -> JsonDict:
    """Build the prediction-generator summary artifact."""
    latencies = _numbers(records, "latency_ms")
    advisory_source_counts: dict[str, int] = {}
    advisory_applied_count = 0
    advisory_noop_count = 0
    advisory_missing_count = 0
    for record in records:
        source = record.get("advisory_source")
        key = source if isinstance(source, str) and source else "unknown"
        advisory_source_counts[key] = advisory_source_counts.get(key, 0) + 1
        if bool(record.get("advisory_applied", False)):
            advisory_applied_count += 1
        else:
            advisory_noop_count += 1
        advisory_status_value = str(record.get("advisory_status", "") or "")
        if advisory_status_value.endswith("_missing") or key.endswith("_missing"):
            advisory_missing_count += 1
    return {
        "schema_version": "router_advisory_predictions_summary_v0",
        "status": status,
        "mode": mode,
        "dataset": str(dataset),
        "out": str(out),
        "case_count": case_count,
        "generated_count": len(records),
        "skipped_count": skipped_count,
        "model_spec": model_spec or None,
        "missing_env_reason": missing_env_reason,
        "error_message": error_message,
        "latency_ms_p50": _percentile(latencies, 50),
        "latency_ms_p90": _percentile(latencies, 90),
        "latency_ms_p95": _percentile(latencies, 95),
        "token_metadata_complete_count": token_metadata_complete_count(records),
        "advisory_source_counts": advisory_source_counts,
        "advisory_applied_count": advisory_applied_count,
        "advisory_noop_count": advisory_noop_count,
        "advisory_missing_count": advisory_missing_count,
        "routing_quality_promotion_evidence": False,
    }


def resolve_model_spec(cli_model: str) -> str:
    """Resolve model from CLI or supported Router model envs."""
    if cli_model.strip():
        return cli_model.strip()
    for key in DEFAULT_MODEL_ENV_KEYS:
        value = os.environ.get(key, "").strip()
        if value:
            return value
    return ""


def infer_api_key_env(model_spec: str, cli_api_key_env: str) -> str:
    """Resolve API key env name for optional-live preflight."""
    value = cli_api_key_env.strip()
    if value:
        return value
    provider = model_spec.split("/", maxsplit=1)[0] if "/" in model_spec else ""
    return f"{provider.upper()}_API_KEY" if provider else ""


def live_missing_env_reason(model_spec: str, api_key_env: str) -> str | None:
    """Return a skip reason when optional-live prerequisites are absent."""
    if not model_spec:
        return "missing model; pass --model or set ROUTER_MODEL/REACT_AGENT_ROUTER_MODEL"
    if api_key_env.lower() == "none":
        return None
    if not api_key_env:
        return "missing api key env name; pass --api-key-env or use provider/model"
    if not os.environ.get(api_key_env, "").strip():
        return f"missing env {api_key_env}"
    return None


def write_empty_jsonl(path: Path) -> None:
    """Create an empty JSONL artifact."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        description="Generate Router advisory prediction artifacts for offline A/B replay.",
    )
    parser.add_argument("--dataset", required=True, help="route_eval_label_v0 JSONL path.")
    parser.add_argument(
        "--out",
        default=str(REPO_ROOT / "ops" / "regression" / "route_prior" / "out" / "router_advisory_predictions.jsonl"),
        help="Output prediction JSONL artifact path.",
    )
    parser.add_argument(
        "--summary-out",
        default=str(
            REPO_ROOT
            / "ops"
            / "regression"
            / "route_prior"
            / "out"
            / "router_advisory_predictions_summary.json"
        ),
        help="Output prediction summary JSON path.",
    )
    parser.add_argument("--max-items", type=int, default=None, help="Optional max case count.")
    parser.add_argument(
        "--mode",
        choices=[DRY_RUN_MODE, LIVE_MODE],
        default=DRY_RUN_MODE,
        help="dry-run is network-free; live explicitly calls the configured Router model.",
    )
    parser.add_argument("--model", default="", help="Model spec in provider/model format.")
    parser.add_argument("--base-url", default="", help="Optional OpenAI-compatible base URL.")
    parser.add_argument(
        "--api-key-env",
        default="",
        help="Optional API key env var name. Use 'none' to skip key preflight.",
    )
    parser.add_argument(
        "--advisory-source",
        choices=ADVISORY_SOURCE_CHOICES,
        default=LABEL_STUB_SOURCE,
        help="Source tag for the local advisory block.",
    )
    parser.add_argument(
        "--advisory-artifact",
        default="",
        help="Optional RP-2 route-prior/reliability JSONL artifact for provided_artifact/rarp_shadow sources.",
    )
    return parser.parse_args()


async def run_async(args: argparse.Namespace) -> int:
    """Run prediction generation."""
    dataset = Path(args.dataset)
    out = Path(args.out)
    summary_out = Path(args.summary_out)
    cases = load_label_cases(dataset)
    if isinstance(args.max_items, int) and args.max_items >= 0:
        cases = cases[: args.max_items]
    expected_layers_by_case = load_expected_layers_by_case(dataset)
    agent_catalog = load_agent_catalog()
    model_spec = resolve_model_spec(str(args.model))
    requested_advisory_source = str(args.advisory_source)
    advisory_artifact_path = (
        Path(args.advisory_artifact)
        if requested_advisory_source != LABEL_STUB_SOURCE and str(args.advisory_artifact or "").strip()
        else None
    )
    advisory_artifact_hash = stable_file_hash(advisory_artifact_path)
    advisory_artifact_records = (
        load_advisory_artifact(advisory_artifact_path)
        if requested_advisory_source != LABEL_STUB_SOURCE
        else {}
    )

    def context_for(case: LabelCase) -> JsonDict | None:
        if requested_advisory_source == LABEL_STUB_SOURCE:
            return None
        return build_provided_advisory_context(
            case_id=case.case_id,
            requested_source=requested_advisory_source,
            artifact_path=advisory_artifact_path,
            artifact_hash_value=advisory_artifact_hash,
            records=advisory_artifact_records,
            agent_catalog=agent_catalog,
        )

    if args.mode == LIVE_MODE:
        api_key_env = infer_api_key_env(model_spec, str(args.api_key_env))
        missing_reason = live_missing_env_reason(model_spec, api_key_env)
        if missing_reason:
            write_empty_jsonl(out)
            summary = build_summary(
                status="skipped",
                mode=str(args.mode),
                dataset=dataset,
                out=out,
                records=[],
                case_count=len(cases),
                skipped_count=len(cases),
                model_spec=model_spec,
                missing_env_reason=missing_reason,
            )
            write_json(summary, summary_out)
            sys.stdout.write(f"status: {summary['status']}\n")
            sys.stdout.write(f"missing_env_reason: {missing_reason}\n")
            sys.stdout.write(f"summary: {summary_out}\n")
            return 0
        api_key_value = None if api_key_env.lower() == "none" else os.environ.get(api_key_env)
        try:
            records = [
                await build_live_prediction(
                    case,
                    agent_catalog=agent_catalog,
                    expected_layers=expected_layers_by_case.get(case.case_id),
                    model_spec=model_spec,
                    base_url=str(args.base_url or ""),
                    api_key_value=api_key_value,
                    advisory_source=requested_advisory_source,
                    advisory_context=context_for(case),
                )
                for case in cases
            ]
        except Exception as exc:
            write_empty_jsonl(out)
            summary = build_summary(
                status="error",
                mode=str(args.mode),
                dataset=dataset,
                out=out,
                records=[],
                case_count=len(cases),
                skipped_count=len(cases),
                model_spec=model_spec,
                error_message=str(exc),
            )
            write_json(summary, summary_out)
            sys.stderr.write(f"status: {summary['status']}\n")
            sys.stderr.write(f"error_message: {exc}\n")
            sys.stderr.write(f"summary: {summary_out}\n")
            return 1
    else:
        dry_model_spec = model_spec or "dry-run/router-stub"
        records = [
            build_dry_run_prediction(
                case,
                agent_catalog=agent_catalog,
                expected_layers=expected_layers_by_case.get(case.case_id),
                model_spec=dry_model_spec,
                advisory_source=requested_advisory_source,
                advisory_context=context_for(case),
            )
            for case in cases
        ]

    write_jsonl(records, out)
    summary = build_summary(
        status="ready",
        mode=str(args.mode),
        dataset=dataset,
        out=out,
        records=records,
        case_count=len(cases),
        skipped_count=0,
        model_spec=model_spec or ("dry-run/router-stub" if args.mode == DRY_RUN_MODE else ""),
    )
    write_json(summary, summary_out)
    sys.stdout.write(f"status: {summary['status']}\n")
    sys.stdout.write(f"case_count: {summary['case_count']}\n")
    sys.stdout.write(f"generated_count: {summary['generated_count']}\n")
    sys.stdout.write(f"predictions: {out}\n")
    sys.stdout.write(f"summary: {summary_out}\n")
    sys.stdout.write("routing_quality_promotion_evidence: False\n")
    return 0


def run(args: argparse.Namespace) -> int:
    """Run the async generator from synchronous callers."""
    return asyncio.run(run_async(args))


def main() -> int:
    """CLI entry point."""
    return run(parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
