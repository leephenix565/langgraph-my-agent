#!/usr/bin/env python
"""Network-free Router advisory A/B dry-run harness.

This tool does not call an LLM and does not modify runtime Router behavior. It
parses supplied or deterministic-stub Router outputs with the existing parser so
RP-3A can measure parser stability and selected-agent deltas before any runtime
advisory implementation exists.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

JsonDict = dict[str, Any]
JsonMapping = Mapping[str, Any]
LAYER_ORDER = ("L1", "L2", "L3", "L4")
SCHEMA_VERSION = "router_advisory_ab_run_v0"
SUMMARY_SCHEMA_VERSION = "router_advisory_ab_summary_v0"
PREDICTION_SCHEMA_VERSION = "router_advisory_prediction_v0"
NETWORK_FREE_MODE = "network-free"
SIDE_METADATA_FIELDS = (
    "model_name",
    "model_spec",
    "prompt_chars",
    "token_count",
    "latency_ms",
    "prompt_hash",
    "catalog_hash",
    "parse_latency_ms",
)
PREDICTION_METADATA_FIELDS = (
    "advisory_source",
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
)
NUMERIC_SIDE_METADATA_FIELDS = {
    "prompt_chars",
    "token_count",
    "latency_ms",
    "parse_latency_ms",
}


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
from react_agent import prompts, router_parse  # noqa: E402
from react_agent.agents import (  # noqa: E402
    AGENT_METADATA,
    agents_by_layer,
    load_metadata_from_dir,
)


def question_hash(question: str) -> str:
    """Return a stable question hash without storing extra raw artifacts."""
    return "sha256:" + hashlib.sha256(question.encode("utf-8")).hexdigest()


def question_preview(question: str, *, limit: int = 160) -> str:
    """Return a compact question preview for local artifacts."""
    text = question.strip()
    return text if len(text) <= limit else text[: limit - 8] + "...[trunc]"


def load_agent_catalog() -> dict[str, list[str]]:
    """Load the formal Router catalog from tracked agent metadata only."""
    AGENT_METADATA.clear()
    load_metadata_from_dir(REPO_ROOT / "config" / "agents")
    return {layer: agents_by_layer(layer) for layer in LAYER_ORDER}


def selected_agents(layer_plan: Mapping[str, Sequence[str]]) -> list[str]:
    """Flatten selected agents in stable Router layer order."""
    selected: list[str] = []
    for layer in LAYER_ORDER:
        for agent_id in layer_plan.get(layer, []):
            if agent_id not in selected:
                selected.append(str(agent_id))
    return selected


def selected_jaccard(left: Sequence[str], right: Sequence[str]) -> float:
    """Return Jaccard similarity for selected agent id sets."""
    left_set = set(left)
    right_set = set(right)
    if not left_set and not right_set:
        return 1.0
    union = left_set | right_set
    return len(left_set & right_set) / len(union) if union else 0.0


def recall(selected: Sequence[str], expected: Sequence[str]) -> float:
    """Return expected-agent recall for one selected-agent list."""
    expected_set = set(expected)
    if not expected_set:
        return 0.0
    return len(set(selected) & expected_set) / len(expected_set)


def critical_miss(selected: Sequence[str], critical_agents: Sequence[str]) -> bool:
    """Return whether any critical agent is absent from selected agents."""
    selected_set = set(selected)
    return any(agent_id not in selected_set for agent_id in critical_agents)


def negative_selection_count(
    selected: Sequence[str],
    should_not_include_agents: Sequence[str],
) -> int:
    """Return how many negative-label agents are selected."""
    return len(set(selected) & set(should_not_include_agents))


def build_router_raw_from_layers(
    expected_layers: Mapping[str, Any],
    *,
    reason: str,
) -> str:
    """Build deterministic Router JSON from label expected_layers."""
    layers: list[JsonDict] = []
    for layer in LAYER_ORDER:
        raw_ids = expected_layers.get(layer, [])
        selected = [str(agent_id) for agent_id in raw_ids] if isinstance(raw_ids, list) else []
        layers.append(
            {
                "layer": layer,
                "mode": router_parse.DEFAULT_MODES.get(layer, "Star"),
                "selected": selected,
            }
        )
    return json.dumps({"layers": layers, "reason": reason}, ensure_ascii=False)


def default_raw_for_expected_layers(
    expected_layers: Mapping[str, Any],
    *,
    side: str,
) -> str:
    """Return deterministic Router JSON from supplied expected layer labels."""
    return build_router_raw_from_layers(
        expected_layers,
        reason=f"network-free {side} stub from accepted label expected_layers",
    )


def default_raw_for_case(case: LabelCase, *, side: str) -> str:
    """Return a deterministic network-free Router output stub for one case."""
    return default_raw_for_expected_layers(
        {"L2": list(case.must_include_agents or case.expected_agents), "L3": []},
        side=side,
    )


def _coerce_raw(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, Mapping) or isinstance(value, list):
        return json.dumps(value, ensure_ascii=False)
    return ""


def _optional_str(value: Any) -> str | None:
    return value if isinstance(value, str) and value.strip() else None


def _optional_number(value: Any) -> int | float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        return value
    if isinstance(value, str) and value.strip():
        try:
            number = float(value.strip())
        except ValueError:
            return None
        return int(number) if number.is_integer() else number
    return None


def _side_metadata(payload: Mapping[str, Any] | None) -> JsonDict:
    """Return whitelisted side metadata without prompt body fields."""
    payload = payload or {}
    metadata: JsonDict = {}
    for field in SIDE_METADATA_FIELDS:
        value = payload.get(field)
        if field in NUMERIC_SIDE_METADATA_FIELDS:
            metadata[field] = _optional_number(value)
        else:
            metadata[field] = _optional_str(value)
    return metadata


def _prediction_side(
    payload: Mapping[str, Any],
    *,
    side: str,
    legacy_raw_key: str,
) -> JsonDict:
    side_payload = payload.get(side)
    if isinstance(side_payload, Mapping):
        raw = _coerce_raw(side_payload.get("raw", ""))
        return {"raw": raw, **_side_metadata(side_payload)}
    return {
        "raw": _coerce_raw(payload.get(legacy_raw_key, "")),
        **_side_metadata(None),
    }


def normalize_prediction_payload(payload: Mapping[str, Any] | None) -> JsonDict:
    """Normalize legacy or enriched prediction payloads to side objects."""
    payload = payload or {}
    schema_version = payload.get("schema_version")
    nested_metadata = payload.get("metadata")
    metadata: JsonDict = dict(nested_metadata) if isinstance(nested_metadata, Mapping) else {}
    metadata.update(
        {
            field: payload.get(field)
            for field in PREDICTION_METADATA_FIELDS
            if field in payload
        },
    )
    return {
        "schema_version": schema_version if isinstance(schema_version, str) else None,
        "metadata": metadata,
        "baseline": _prediction_side(
            payload,
            side="baseline",
            legacy_raw_key="baseline_raw",
        ),
        "advisory": _prediction_side(
            payload,
            side="advisory",
            legacy_raw_key="advisory_raw",
        ),
    }


def load_prediction_artifact(path: Path | None) -> dict[str, JsonDict]:
    """Load optional JSONL predictions keyed by id/case_id."""
    if path is None:
        return {}
    predictions: dict[str, JsonDict] = {}
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        text = line.strip()
        if not text:
            continue
        payload = json.loads(text)
        if not isinstance(payload, Mapping):
            raise ValueError(f"Prediction line {line_no} is not an object")
        case_id = payload.get("case_id") or payload.get("id")
        if not isinstance(case_id, str) or not case_id.strip():
            raise ValueError(f"Prediction line {line_no} missing case_id/id")
        predictions[case_id] = normalize_prediction_payload(payload)
    return predictions


def load_expected_layers_by_case(path: Path) -> dict[str, Mapping[str, Any]]:
    """Load optional expected_layers from raw label JSONL by case id."""
    expected_layers_by_case: dict[str, Mapping[str, Any]] = {}
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        text = line.strip()
        if not text:
            continue
        payload = json.loads(text)
        if not isinstance(payload, Mapping):
            raise ValueError(f"Dataset line {line_no} is not an object")
        case_id = payload.get("id")
        expected_layers = payload.get("expected_layers")
        if isinstance(case_id, str) and isinstance(expected_layers, Mapping):
            expected_layers_by_case[case_id] = expected_layers
    return expected_layers_by_case


def render_baseline_prompt(agent_catalog: Mapping[str, Sequence[str]]) -> str:
    """Render the current Router prompt locally without mutating runtime code."""
    catalog = {layer: list(agent_catalog.get(layer, [])) for layer in LAYER_ORDER}
    return prompts.ROUTER_SYSTEM_PROMPT.format(
        system_time="offline-network-free",
        agent_catalog=json.dumps(catalog, ensure_ascii=False),
    )


def render_advisory_prompt(
    baseline_prompt: str,
    case: LabelCase,
    *,
    agent_catalog: Mapping[str, Sequence[str]] | None = None,
    expected_layers: Mapping[str, Any] | None = None,
    max_agents: int = 8,
) -> str:
    """Render a compact non-runtime advisory prompt for char-delta estimates."""
    layer_lookup = _agent_layer_lookup(
        agent_catalog=agent_catalog,
        expected_layers=expected_layers,
    )
    advisory = {
        "mode": "offline_network_free_label_stub",
        "non_binding": True,
        "must_include_agents_by_layer": _agents_by_layer(
            case.must_include_agents or case.expected_agents,
            layer_lookup=layer_lookup,
            max_agents=max_agents,
        ),
        "critical_agents_by_layer": _agents_by_layer(
            case.critical_agents,
            layer_lookup=layer_lookup,
            max_agents=max_agents,
        ),
        "nice_to_have_agents_by_layer": _agents_by_layer(
            case.nice_to_have_agents,
            layer_lookup=layer_lookup,
            max_agents=max_agents,
        ),
        "instruction": (
            "Only select each advisory agent in the layer where it is listed. "
            "Do not move L3 agents into L2 or L2 agents into L3. "
            "If uncertain, omit rather than selecting the agent in the wrong layer. "
            "Return only the existing Router JSON schema."
        ),
    }
    block = "\n\nRoute prior advisory, non-binding (offline dry-run stub):\n"
    block += json.dumps(advisory, ensure_ascii=False, sort_keys=True)
    return baseline_prompt + block


def _agent_layer_lookup(
    *,
    agent_catalog: Mapping[str, Sequence[str]] | None,
    expected_layers: Mapping[str, Any] | None,
) -> dict[str, str]:
    """Return agent->layer lookup, preferring label expected layer hints."""
    lookup: dict[str, str] = {}
    for layer in LAYER_ORDER:
        raw_ids = expected_layers.get(layer, []) if isinstance(expected_layers, Mapping) else []
        if isinstance(raw_ids, Sequence) and not isinstance(raw_ids, str):
            for agent_id in raw_ids:
                if isinstance(agent_id, str) and agent_id.strip():
                    lookup[agent_id.strip()] = layer
    catalog = agent_catalog or {}
    for layer in LAYER_ORDER:
        raw_ids = catalog.get(layer, [])
        for agent_id in raw_ids:
            normalized = str(agent_id).strip()
            if normalized:
                lookup.setdefault(normalized, layer)
    return lookup


def _agents_by_layer(
    agent_ids: Sequence[str],
    *,
    layer_lookup: Mapping[str, str],
    max_agents: int,
) -> JsonDict:
    """Group advisory agent ids by their valid Router layer."""
    groups: dict[str, list[str]] = {layer: [] for layer in LAYER_ORDER}
    unlayered: list[str] = []
    for agent_id in dict.fromkeys(str(agent_id).strip() for agent_id in agent_ids):
        if not agent_id:
            continue
        layer = layer_lookup.get(agent_id)
        if layer in groups:
            groups[layer].append(agent_id)
        else:
            unlayered.append(agent_id)
        if sum(len(ids) for ids in groups.values()) + len(unlayered) >= max_agents:
            break
    result: JsonDict = {layer: ids for layer, ids in groups.items() if ids}
    if unlayered:
        result["unlayered"] = unlayered
    return result


def parse_side(
    raw: str,
    agent_catalog: Mapping[str, list[str]],
    *,
    metadata: Mapping[str, Any] | None = None,
) -> JsonDict:
    """Parse one raw Router output and return artifact fields."""
    plan, modes, stats = router_parse.parse_router_layers_with_stats(
        raw,
        agent_catalog=dict(agent_catalog),
    )
    selected = selected_agents(plan)
    return {
        "raw": raw,
        "parse_stats": stats,
        "layer_plan": plan,
        "layer_mode": modes,
        "selected_agents": selected,
        **_side_metadata(metadata),
    }


def _numeric_delta(
    advisory_value: Any,
    baseline_value: Any,
) -> int | float | None:
    advisory_number = _optional_number(advisory_value)
    baseline_number = _optional_number(baseline_value)
    if advisory_number is None or baseline_number is None:
        return None
    return advisory_number - baseline_number


def compare_parsed_outputs(
    *,
    case: LabelCase,
    baseline: JsonMapping,
    advisory: JsonMapping,
    baseline_prompt_chars: int,
    advisory_prompt_chars: int,
    advisory_applied: bool = True,
) -> JsonDict:
    """Compare parsed Router outputs for one case."""
    if not advisory_applied:
        return {
            "parse_ok_delta": 0,
            "used_default_plan_delta": 0,
            "filtered_agents_delta": 0,
            "l2_truncated_delta": 0,
            "selected_jaccard": 1.0,
            "must_include_recall_delta": 0.0,
            "critical_agent_miss_delta": 0,
            "negative_selection_delta": 0,
            "prompt_char_delta": 0,
            "token_count_delta": 0,
            "latency_ms_delta": 0,
            "advisory_applied": False,
            "advisory_comparison_mode": "noop_no_advisory",
        }
    baseline_selected = [str(agent_id) for agent_id in baseline.get("selected_agents", [])]
    advisory_selected = [str(agent_id) for agent_id in advisory.get("selected_agents", [])]
    baseline_stats = baseline.get("parse_stats", {})
    advisory_stats = advisory.get("parse_stats", {})
    baseline_stats = baseline_stats if isinstance(baseline_stats, Mapping) else {}
    advisory_stats = advisory_stats if isinstance(advisory_stats, Mapping) else {}
    must_include = case.must_include_agents or case.expected_agents
    prompt_char_delta = _numeric_delta(
        advisory.get("prompt_chars"),
        baseline.get("prompt_chars"),
    )

    return {
        "parse_ok_delta": int(bool(advisory_stats.get("parse_ok", False)))
        - int(bool(baseline_stats.get("parse_ok", False))),
        "used_default_plan_delta": int(bool(advisory_stats.get("used_default_plan", False)))
        - int(bool(baseline_stats.get("used_default_plan", False))),
        "filtered_agents_delta": int(advisory_stats.get("filtered_agents", 0) or 0)
        - int(baseline_stats.get("filtered_agents", 0) or 0),
        "l2_truncated_delta": int(advisory_stats.get("l2_truncated", 0) or 0)
        - int(baseline_stats.get("l2_truncated", 0) or 0),
        "selected_jaccard": selected_jaccard(baseline_selected, advisory_selected),
        "must_include_recall_delta": recall(advisory_selected, must_include)
        - recall(baseline_selected, must_include),
        "critical_agent_miss_delta": int(critical_miss(advisory_selected, case.critical_agents))
        - int(critical_miss(baseline_selected, case.critical_agents)),
        "negative_selection_delta": negative_selection_count(
            advisory_selected,
            case.should_not_include_agents,
        )
        - negative_selection_count(baseline_selected, case.should_not_include_agents),
        "prompt_char_delta": (
            prompt_char_delta
            if prompt_char_delta is not None
            else advisory_prompt_chars - baseline_prompt_chars
        ),
        "token_count_delta": _numeric_delta(
            advisory.get("token_count"),
            baseline.get("token_count"),
        ),
        "latency_ms_delta": _numeric_delta(
            advisory.get("latency_ms"),
            baseline.get("latency_ms"),
        ),
        "advisory_applied": True,
        "advisory_comparison_mode": "applied",
    }


def build_case_record(
    case: LabelCase,
    *,
    agent_catalog: Mapping[str, list[str]],
    prediction: Mapping[str, Any] | None = None,
    expected_layers: Mapping[str, Any] | None = None,
    mode: str = NETWORK_FREE_MODE,
) -> JsonDict:
    """Build one network-free A/B artifact record."""
    baseline_prompt = render_baseline_prompt(agent_catalog)
    advisory_prompt = render_advisory_prompt(
        baseline_prompt,
        case,
        agent_catalog=agent_catalog,
        expected_layers=expected_layers,
    )
    fallback_layers = expected_layers or {
        "L2": list(case.must_include_agents or case.expected_agents),
        "L3": [],
    }
    prediction = normalize_prediction_payload(prediction)
    prediction_metadata = prediction.get("metadata", {})
    prediction_metadata = prediction_metadata if isinstance(prediction_metadata, Mapping) else {}
    advisory_applied = bool(prediction_metadata.get("advisory_applied", True))
    if not advisory_applied:
        advisory_prompt = baseline_prompt
    baseline_prediction = prediction["baseline"]
    advisory_prediction = prediction["advisory"]
    baseline_raw = baseline_prediction.get("raw") or default_raw_for_expected_layers(
        fallback_layers,
        side="baseline",
    )
    advisory_raw = advisory_prediction.get("raw") or default_raw_for_expected_layers(
        fallback_layers,
        side="advisory",
    )
    baseline = parse_side(str(baseline_raw), agent_catalog, metadata=baseline_prediction)
    advisory = parse_side(str(advisory_raw), agent_catalog, metadata=advisory_prediction)
    comparison = compare_parsed_outputs(
        case=case,
        baseline=baseline,
        advisory=advisory,
        baseline_prompt_chars=len(baseline_prompt),
        advisory_prompt_chars=len(advisory_prompt),
        advisory_applied=advisory_applied,
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "mode": mode,
        "case_id": case.case_id,
        "question_hash": question_hash(case.question),
        "question_preview": question_preview(case.question),
        "label_source": case.label_source,
        "quality_conclusion_allowed": case.quality_conclusion_allowed,
        "baseline_prompt_chars": len(baseline_prompt),
        "advisory_prompt_chars": len(advisory_prompt),
        **prediction_metadata,
        "baseline": baseline,
        "advisory": advisory,
        "comparison": comparison,
        "prediction_schema_version": prediction.get("schema_version"),
    }


def _number_list(comparisons: Sequence[JsonMapping], field: str) -> list[float]:
    values: list[float] = []
    for comparison in comparisons:
        value = _optional_number(comparison.get(field))
        if value is not None:
            values.append(float(value))
    return values


def _average(values: Sequence[float]) -> float | None:
    return sum(values) / len(values) if values else None


def _percentile(values: Sequence[float], percentile: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    rank = round((percentile / 100) * (len(ordered) - 1))
    return ordered[int(rank)]


def _complete_side_metadata_count(records: Sequence[JsonMapping], field: str) -> int:
    count = 0
    for record in records:
        baseline = record.get("baseline", {})
        advisory = record.get("advisory", {})
        if not isinstance(baseline, Mapping) or not isinstance(advisory, Mapping):
            continue
        if baseline.get(field) is not None and advisory.get(field) is not None:
            count += 1
    return count


def build_summary(records: Sequence[JsonMapping], *, dataset: Path) -> JsonDict:
    """Build a compact A/B run summary."""
    case_count = len(records)
    comparisons = [
        record.get("comparison", {})
        for record in records
        if isinstance(record.get("comparison"), Mapping)
    ]
    parse_ok_regressions = sum(
        1 for comparison in comparisons if int(comparison.get("parse_ok_delta", 0) or 0) < 0
    )
    default_plan_regressions = sum(
        1
        for comparison in comparisons
        if int(comparison.get("used_default_plan_delta", 0) or 0) > 0
    )
    critical_miss_regressions = sum(
        1
        for comparison in comparisons
        if int(comparison.get("critical_agent_miss_delta", 0) or 0) > 0
    )
    avg_selected_jaccard = (
        sum(float(comparison.get("selected_jaccard", 0.0) or 0.0) for comparison in comparisons)
        / case_count
        if case_count
        else 0.0
    )
    prompt_char_deltas = _number_list(comparisons, "prompt_char_delta")
    token_count_deltas = _number_list(comparisons, "token_count_delta")
    latency_ms_deltas = _number_list(comparisons, "latency_ms_delta")
    advisory_applied_count = sum(1 for record in records if bool(record.get("advisory_applied", True)))
    advisory_noop_count = sum(1 for record in records if record.get("advisory_applied") is False)
    advisory_missing_count = sum(
        1
        for record in records
        if str(record.get("advisory_status", "") or "").endswith("_missing")
        or str(record.get("advisory_source", "") or "").endswith("_missing")
    )
    return {
        "schema_version": SUMMARY_SCHEMA_VERSION,
        "mode": NETWORK_FREE_MODE,
        "dataset": str(dataset),
        "case_count": case_count,
        "parse_ok_regressions": parse_ok_regressions,
        "default_plan_regressions": default_plan_regressions,
        "critical_miss_regressions": critical_miss_regressions,
        "avg_selected_jaccard": avg_selected_jaccard,
        "avg_prompt_char_delta": _average(prompt_char_deltas),
        "avg_token_count_delta": _average(token_count_deltas),
        "avg_latency_ms_delta": _average(latency_ms_deltas),
        "latency_ms_delta_p50": _percentile(latency_ms_deltas, 50),
        "latency_ms_delta_p90": _percentile(latency_ms_deltas, 90),
        "latency_ms_delta_p95": _percentile(latency_ms_deltas, 95),
        "prediction_records_with_complete_prompt_char_metadata": _complete_side_metadata_count(
            records,
            "prompt_chars",
        ),
        "prediction_records_with_complete_token_metadata": _complete_side_metadata_count(
            records,
            "token_count",
        ),
        "prediction_records_with_complete_latency_metadata": _complete_side_metadata_count(
            records,
            "latency_ms",
        ),
        "advisory_applied_count": advisory_applied_count,
        "advisory_noop_count": advisory_noop_count,
        "advisory_missing_count": advisory_missing_count,
        "routing_quality_promotion_evidence": False,
    }


def write_jsonl(records: Sequence[JsonMapping], path: Path) -> None:
    """Write JSONL records."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as fh:
        for record in records:
            fh.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")


def write_json(payload: JsonMapping, path: Path) -> None:
    """Write one JSON artifact."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        description="Run network-free Router advisory A/B parser dry-run.",
    )
    parser.add_argument("--dataset", required=True, help="route_eval_label_v0 JSONL path.")
    parser.add_argument(
        "--out-dir",
        default=str(REPO_ROOT / "ops" / "regression" / "route_prior" / "out"),
        help="Output directory.",
    )
    parser.add_argument("--max-items", type=int, default=None, help="Optional max case count.")
    parser.add_argument(
        "--mode",
        choices=[NETWORK_FREE_MODE],
        default=NETWORK_FREE_MODE,
        help="Only network-free mode is implemented in RP-3A-1.",
    )
    parser.add_argument(
        "--predictions",
        default="",
        help=(
            "Optional JSONL with id/case_id plus legacy baseline_raw/advisory_raw "
            "or enriched baseline/advisory side metadata."
        ),
    )
    parser.add_argument(
        "--output-jsonl",
        default="router_advisory_ab_runs.jsonl",
        help="Output A/B JSONL artifact name.",
    )
    parser.add_argument(
        "--summary-json",
        default="router_advisory_ab_summary.json",
        help="Output A/B summary JSON name.",
    )
    return parser.parse_args()


def run(args: argparse.Namespace) -> int:
    """Run the network-free A/B dry-run."""
    dataset = Path(args.dataset)
    out_dir = Path(args.out_dir)
    cases = load_label_cases(dataset)
    if isinstance(args.max_items, int) and args.max_items >= 0:
        cases = cases[: args.max_items]
    predictions = load_prediction_artifact(
        Path(args.predictions) if str(args.predictions or "").strip() else None
    )
    expected_layers_by_case = load_expected_layers_by_case(dataset)
    agent_catalog = load_agent_catalog()
    records = [
        build_case_record(
            case,
            agent_catalog=agent_catalog,
            prediction=predictions.get(case.case_id),
            expected_layers=expected_layers_by_case.get(case.case_id),
            mode=str(args.mode),
        )
        for case in cases
    ]
    out_jsonl = out_dir / str(args.output_jsonl)
    summary_json = out_dir / str(args.summary_json)
    write_jsonl(records, out_jsonl)
    summary = build_summary(records, dataset=dataset)
    write_json(summary, summary_json)
    sys.stdout.write(f"case_count: {summary['case_count']}\n")
    sys.stdout.write(f"parse_ok_regressions: {summary['parse_ok_regressions']}\n")
    sys.stdout.write(f"default_plan_regressions: {summary['default_plan_regressions']}\n")
    sys.stdout.write(f"critical_miss_regressions: {summary['critical_miss_regressions']}\n")
    sys.stdout.write(f"runs: {out_jsonl}\n")
    sys.stdout.write(f"summary: {summary_json}\n")
    return 0


def main() -> int:
    """CLI entry point."""
    return run(parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
