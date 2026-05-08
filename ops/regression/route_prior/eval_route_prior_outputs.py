#!/usr/bin/env python
"""Aggregate offline route-prior run outputs into metrics."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, cast

JsonDict = dict[str, Any]
JsonMapping = Mapping[str, Any]


METRICS_META = {
    "phase": "RP-2A",
    "scope": "offline_eval_tooling",
    "schema_version": "route_prior_metrics_v2",
    "legacy_rp1b_compatible": True,
    "runtime_semantics_changed": False,
    "formal_router_changed": False,
    "public_surface_changed": False,
    "labels_warning": "draft labels are not final quality evidence",
}
DEEPSEEK_TEACHER_LABEL_SOURCE = "deepseek_teacher_v1"
DEEPSEEK_TEACHER_LABELS_WARNING = (
    "DeepSeek teacher labels are model-generated proxy labels, not human/manual gold labels"
)
QUALITY_LABEL_SOURCES = {"manual", "manual_gold"}
NON_QUALITY_LABEL_SOURCES = {"draft_for_human_review", DEEPSEEK_TEACHER_LABEL_SOURCE}
COST_VALUES = {
    "low": 1.0,
    "normal": 2.0,
    "medium": 2.0,
    "high": 3.0,
    "unknown": 2.0,
    "": 2.0,
}

CONSERVATIVE_PRUNING_POLICIES = {
    "keep_top_12": 12,
    "keep_top_14": 14,
    "keep_top_16": 16,
    "keep_top_18": 18,
    "keep_top_14_plus_wildcard": 14,
    "keep_top_16_plus_wildcard": 16,
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


def _as_str_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str) and item]


def _as_mapping_list(value: object) -> list[JsonMapping]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, Mapping)]


def _rate(values: Sequence[bool]) -> float:
    if not values:
        return 0.0
    return sum(1 for item in values if item) / len(values)


def _avg(values: Sequence[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


def _nullable_avg(values: Sequence[float]) -> float | None:
    if not values:
        return None
    return _avg(values)


def _labels_mapping(record: JsonMapping) -> JsonMapping:
    labels = record.get("labels")
    if isinstance(labels, Mapping):
        return labels
    return {}


def must_include_agents(record: JsonMapping) -> list[str]:
    """Return RP-2A must-include labels, falling back to legacy expected_agents."""
    labels = _labels_mapping(record)
    explicit = _as_str_list(labels.get("must_include_agents"))
    if explicit:
        return explicit
    explicit = _as_str_list(record.get("must_include_agents"))
    if explicit:
        return explicit
    return _as_str_list(record.get("expected_agents"))


def critical_agents(record: JsonMapping) -> list[str]:
    """Return critical-agent labels when present."""
    labels = _labels_mapping(record)
    explicit = _as_str_list(labels.get("critical_agents"))
    if explicit:
        return explicit
    return _as_str_list(record.get("critical_agents"))


def nice_to_have_agents(record: JsonMapping) -> list[str]:
    """Return nice-to-have labels when present."""
    labels = _labels_mapping(record)
    explicit = _as_str_list(labels.get("nice_to_have_agents"))
    if explicit:
        return explicit
    return _as_str_list(record.get("nice_to_have_agents"))


def should_not_include_agents(record: JsonMapping) -> list[str]:
    """Return negative route labels when present."""
    labels = _labels_mapping(record)
    explicit = _as_str_list(labels.get("should_not_include_agents"))
    if explicit:
        return explicit
    return _as_str_list(record.get("should_not_include_agents"))


def _record_quality_conclusion_allowed(record: JsonMapping) -> bool:
    source = str(record.get("label_source", "") or "")
    if source in NON_QUALITY_LABEL_SOURCES:
        return False
    raw = record.get("quality_conclusion_allowed")
    if isinstance(raw, bool):
        return raw and source in QUALITY_LABEL_SOURCES
    return source in QUALITY_LABEL_SOURCES


def _score_value(raw: object) -> float:
    try:
        score = float(raw or 0.0)
    except (TypeError, ValueError):
        score = 0.0
    return max(0.0, min(1.0, score))


def _route_score_items(record: JsonMapping) -> list[JsonMapping]:
    items = _as_mapping_list(record.get("route_scores_all_light"))
    if items:
        return items
    return _as_mapping_list(record.get("route_scores_top10"))


def _precision(selected: Sequence[str], expected: Sequence[str]) -> float:
    selected_set = set(selected)
    if not selected_set:
        return 0.0
    return len(selected_set.intersection(expected)) / len(selected_set)


def _f1(precision: float, recall: float) -> float:
    if precision + recall <= 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


def _agent_cost_levels() -> dict[str, str]:
    from react_agent.agents import (  # type: ignore[import-not-found]
        AGENT_METADATA,
        load_metadata_from_dir,
    )

    if not AGENT_METADATA:
        load_metadata_from_dir(REPO_ROOT / "config" / "agents")
    return {
        agent_id: str(getattr(meta, "cost_level", "") or "").strip().lower()
        for agent_id, meta in AGENT_METADATA.items()
    }


def _cost_value(agent_id: str, agent_costs: Mapping[str, str]) -> float:
    cost_level = str(agent_costs.get(agent_id, "") or "").strip().lower()
    return COST_VALUES.get(cost_level, COST_VALUES["unknown"])


def _shortlist_cost(record: JsonMapping, agent_costs: Mapping[str, str]) -> float:
    return sum(_cost_value(agent_id, agent_costs) for agent_id in _as_str_list(record.get("awake_agents")))


def _calibration_metrics(records: Sequence[JsonMapping]) -> JsonDict:
    pairs: list[tuple[float, int]] = []
    for record in records:
        positives = set(must_include_agents(record))
        negatives = set(should_not_include_agents(record))
        for item in _route_score_items(record):
            agent_id = item.get("agent_id")
            if not isinstance(agent_id, str) or not agent_id:
                continue
            if agent_id in positives:
                label = 1
            elif agent_id in negatives:
                label = 0
            else:
                continue
            pairs.append((_score_value(item.get("semantic_similarity_score")), label))

    if not pairs:
        return {
            "ECE": None,
            "Brier": None,
            "calibration_pair_count": 0,
            "calibration_bin_count": 0,
        }

    brier = _avg([(score - label) ** 2 for score, label in pairs])
    bin_count = 10
    ece = 0.0
    total = len(pairs)
    for bin_index in range(bin_count):
        lower = bin_index / bin_count
        upper = (bin_index + 1) / bin_count
        bucket = [
            (score, label)
            for score, label in pairs
            if (score >= lower and (score < upper or bin_index == bin_count - 1))
        ]
        if not bucket:
            continue
        avg_score = _avg([score for score, _label in bucket])
        accuracy = _avg([float(label) for _score, label in bucket])
        ece += (len(bucket) / total) * abs(avg_score - accuracy)
    return {
        "ECE": ece,
        "Brier": brier,
        "calibration_pair_count": total,
        "calibration_bin_count": bin_count,
    }


def load_run_records(path: Path) -> list[JsonDict]:
    """Load route-prior run records from JSONL."""
    records: list[JsonDict] = []
    with path.open("r", encoding="utf-8") as fh:
        for line_no, line in enumerate(fh, start=1):
            text = line.strip()
            if not text:
                continue
            obj = json.loads(text)
            if not isinstance(obj, dict):
                raise ValueError(f"JSONL line {line_no} is not an object")
            records.append(cast(JsonDict, obj))
    return records


def top_ranked_ids(record: JsonMapping) -> list[str]:
    """Return ranked agent ids from an RP-1B run record."""
    explicit = _as_str_list(record.get("top_ranked_ids"))
    if explicit:
        return explicit
    ranked: list[str] = []
    for item in _as_mapping_list(record.get("route_scores_top10")):
        agent_id = item.get("agent_id")
        if isinstance(agent_id, str) and agent_id:
            ranked.append(agent_id)
    return ranked


def full_ranked_agent_ids(record: JsonMapping) -> list[str]:
    """Return full ranked agent ids when the run record includes them."""
    explicit = _as_str_list(record.get("route_scores_all_agent_ids"))
    if explicit:
        return explicit
    ranked: list[str] = []
    for item in _as_mapping_list(record.get("route_scores_all_light")):
        agent_id = item.get("agent_id")
        if isinstance(agent_id, str) and agent_id:
            ranked.append(agent_id)
    if ranked:
        return ranked
    return top_ranked_ids(record)


def topk_hit(record: JsonMapping, k: int) -> bool:
    """Return whether any expected agent appears in the top-k ranked ids."""
    expected = set(must_include_agents(record))
    if not expected:
        return False
    return bool(expected.intersection(top_ranked_ids(record)[:k]))


def expected_recall(selected: Sequence[str], expected: Sequence[str]) -> float:
    """Compute selected-agent recall against expected agent ids."""
    expected_set = set(expected)
    if not expected_set:
        return 0.0
    return len(expected_set.intersection(selected)) / len(expected_set)


def jaccard(left: Sequence[str], right: Sequence[str]) -> float:
    """Compute Jaccard overlap for two agent id sequences."""
    left_set = set(left)
    right_set = set(right)
    union = left_set | right_set
    if not union:
        return 0.0
    return len(left_set & right_set) / len(union)


def _filtered_records(
    records: Sequence[JsonMapping],
    *,
    include_draft_labels: bool,
    require_manual_labels: bool,
) -> list[JsonMapping]:
    filtered: list[JsonMapping] = []
    for record in records:
        source = str(record.get("label_source", "") or "")
        if require_manual_labels and source not in QUALITY_LABEL_SOURCES:
            continue
        if not include_draft_labels and source == "draft_for_human_review":
            continue
        filtered.append(record)
    return filtered


def collect_false_negatives(records: Sequence[JsonMapping]) -> list[JsonDict]:
    """Collect cases whose expected agents are missing from awake_agents."""
    examples: list[JsonDict] = []
    for record in records:
        expected = must_include_agents(record)
        awake = _as_str_list(record.get("awake_agents"))
        missing = [agent_id for agent_id in expected if agent_id not in awake]
        if not missing:
            continue
        examples.append(
            {
                "id": str(record.get("id", "") or ""),
                "question": str(record.get("question", "") or ""),
                "expected_agents": expected,
                "must_include_agents": expected,
                "missing_expected_agents": missing,
                "awake_agents": awake,
                "top_ranked_ids": top_ranked_ids(record),
                "confidence_band": str(record.get("confidence_band", "") or ""),
                "low_confidence_fallback": bool(record.get("low_confidence_fallback", False)),
                "retrieval_reason": str(record.get("retrieval_reason", "") or ""),
                "reason_codes": _as_str_list(record.get("reason_codes")),
                "label_source": str(record.get("label_source", "") or ""),
            }
        )
    return examples


def false_negative_agent_count(examples: Sequence[JsonMapping]) -> int:
    """Return the number of missing expected-agent labels across false-negative cases."""
    return sum(len(_as_str_list(example.get("missing_expected_agents"))) for example in examples)


def conservative_pruned_agents(record: JsonMapping, *, keep_top_k: int) -> tuple[list[str], bool]:
    """Simulate conservative pruning for one record without changing runtime behavior."""
    awake_agents = _as_str_list(record.get("awake_agents"))
    if bool(record.get("low_confidence_fallback", False)):
        return awake_agents, False

    ranked_ids = full_ranked_agent_ids(record)
    selected: list[str] = []
    for agent_id in ranked_ids[:keep_top_k]:
        if agent_id not in selected:
            selected.append(agent_id)
    for wildcard_id in _as_str_list(record.get("wildcard_agents")):
        if wildcard_id in ranked_ids and wildcard_id not in selected:
            selected.append(wildcard_id)
    return selected, True


def collect_conservative_false_negatives(
    records: Sequence[JsonMapping],
    *,
    keep_top_k: int,
) -> list[JsonDict]:
    """Collect false negatives under one conservative pruning policy."""
    examples: list[JsonDict] = []
    for record in records:
        pruned_agents, pruning_applied = conservative_pruned_agents(record, keep_top_k=keep_top_k)
        expected = must_include_agents(record)
        missing = [agent_id for agent_id in expected if agent_id not in pruned_agents]
        if not missing:
            continue
        examples.append(
            {
                "id": str(record.get("id", "") or ""),
                "question": str(record.get("question", "") or ""),
                "expected_agents": expected,
                "must_include_agents": expected,
                "missing_expected_agents": missing,
                "pruned_agents": pruned_agents,
                "top_ranked_ids": full_ranked_agent_ids(record),
                "confidence_band": str(record.get("confidence_band", "") or ""),
                "low_confidence_fallback": bool(record.get("low_confidence_fallback", False)),
                "pruning_applied": pruning_applied,
                "retrieval_reason": str(record.get("retrieval_reason", "") or ""),
                "label_source": str(record.get("label_source", "") or ""),
            }
        )
    return examples


def aggregate_conservative_pruning(records: Sequence[JsonMapping]) -> JsonDict:
    """Aggregate offline conservative-pruning simulation metrics."""
    policy_metrics: JsonDict = {}
    case_count = len(records)
    for policy_name, keep_top_k in CONSERVATIVE_PRUNING_POLICIES.items():
        pool_sizes: list[float] = []
        pool_ratios: list[float] = []
        recall_values: list[float] = []
        full_covered_values: list[bool] = []
        dropped_counts: list[float] = []
        pruning_applied_count = 0

        for record in records:
            pruned_agents, pruning_applied = conservative_pruned_agents(
                record,
                keep_top_k=keep_top_k,
            )
            if pruning_applied:
                pruning_applied_count += 1
            ordinary_pool_size = int(record.get("ordinary_pool_size", 0) or 0)
            if ordinary_pool_size <= 0:
                ordinary_pool_size = len(full_ranked_agent_ids(record)) or len(pruned_agents)
            pool_size = len(pruned_agents)
            pool_sizes.append(float(pool_size))
            if ordinary_pool_size > 0:
                pool_ratios.append(pool_size / ordinary_pool_size)
                dropped_counts.append(float(max(ordinary_pool_size - pool_size, 0)))
            recall_value = expected_recall(
                pruned_agents,
                must_include_agents(record),
            )
            recall_values.append(recall_value)
            full_covered_values.append(recall_value == 1.0)

        false_negatives = collect_conservative_false_negatives(records, keep_top_k=keep_top_k)
        false_negative_case_count = len(false_negatives)
        policy_metrics[policy_name] = {
            "case_count": case_count,
            "pruning_applied_count": pruning_applied_count,
            "avg_pool_size": _avg(pool_sizes),
            "avg_pool_ratio": _avg(pool_ratios),
            "shortlist_recall": _avg(recall_values),
            "full_expected_covered_rate": _rate(full_covered_values),
            "false_negative_count": false_negative_case_count,
            "false_negative_case_count": false_negative_case_count,
            "false_negative_agent_count": false_negative_agent_count(false_negatives),
            "false_negative_examples": false_negatives,
            "dropped_agent_count_avg": _avg(dropped_counts),
        }
    return policy_metrics


def _formal_router_overlap(records: Sequence[JsonMapping]) -> JsonDict | None:
    observed: list[JsonMapping] = [
        record for record in records if isinstance(record.get("formal_router_selected"), list)
    ]
    if not observed:
        return None
    jaccard_values: list[float] = []
    overlap_counts: list[float] = []
    for record in observed:
        awake = _as_str_list(record.get("awake_agents"))
        selected = _as_str_list(record.get("formal_router_selected"))
        jaccard_values.append(jaccard(awake, selected))
        overlap_counts.append(float(len(set(awake).intersection(selected))))
    return {
        "case_count": len(observed),
        "avg_jaccard": _avg(jaccard_values),
        "avg_overlap_count": _avg(overlap_counts),
    }


def aggregate_metrics(
    records: Sequence[JsonMapping],
    *,
    include_draft_labels: bool = True,
    require_manual_labels: bool = False,
    agent_costs: Mapping[str, str] | None = None,
    _include_label_source_groups: bool = True,
) -> JsonDict:
    """Aggregate route-prior validation metrics with legacy RP-1B compatibility."""
    evaluated = _filtered_records(
        records,
        include_draft_labels=include_draft_labels,
        require_manual_labels=require_manual_labels,
    )
    case_count = len(evaluated)
    label_sources = Counter(str(record.get("label_source", "") or "") for record in evaluated)
    manual_count = sum(label_sources.get(source, 0) for source in QUALITY_LABEL_SOURCES)
    deepseek_teacher_count = label_sources.get(DEEPSEEK_TEACHER_LABEL_SOURCE, 0)
    quality_label_count = sum(1 for record in evaluated if _record_quality_conclusion_allowed(record))
    quality_conclusion_allowed = quality_label_count > 0
    proxy_quality_conclusion_only = quality_label_count == 0 and deepseek_teacher_count > 0

    shortlist_sizes = [float(len(_as_str_list(record.get("awake_agents")))) for record in evaluated]
    shortlist_ratios: list[float] = []
    for record in evaluated:
        ordinary_pool_size = int(record.get("ordinary_pool_size", 0) or 0)
        shortlist_size = len(_as_str_list(record.get("awake_agents")))
        if ordinary_pool_size > 0:
            shortlist_ratios.append(shortlist_size / ordinary_pool_size)

    top1_recalls = [
        expected_recall(top_ranked_ids(record)[:1], must_include_agents(record))
        for record in evaluated
    ]
    top3_recalls = [
        expected_recall(top_ranked_ids(record)[:3], must_include_agents(record))
        for record in evaluated
    ]
    top5_recalls = [
        expected_recall(
            top_ranked_ids(record)[:5],
            must_include_agents(record),
        )
        for record in evaluated
    ]
    shortlist_recalls = [
        expected_recall(
            _as_str_list(record.get("awake_agents")),
            must_include_agents(record),
        )
        for record in evaluated
    ]
    effective_shortlist_recalls = [
        0.0 if bool(record.get("low_confidence_fallback", False)) else recall_value
        for record, recall_value in zip(evaluated, shortlist_recalls, strict=False)
    ]
    precision_values = [
        _precision(_as_str_list(record.get("awake_agents")), must_include_agents(record))
        for record in evaluated
    ]
    f1_values = [
        _f1(precision, recall)
        for precision, recall in zip(precision_values, shortlist_recalls, strict=False)
    ]
    jaccard_values = [
        jaccard(_as_str_list(record.get("awake_agents")), must_include_agents(record))
        for record in evaluated
    ]
    full_expected_covered = [
        expected_recall(
            _as_str_list(record.get("awake_agents")),
            must_include_agents(record),
        )
        == 1.0
        for record in evaluated
    ]
    critical_labeled = [record for record in evaluated if critical_agents(record)]
    critical_misses = [
        any(agent_id not in _as_str_list(record.get("awake_agents")) for agent_id in critical_agents(record))
        for record in critical_labeled
    ]
    nice_labeled = [record for record in evaluated if nice_to_have_agents(record)]
    nice_recalls = [
        expected_recall(
            _as_str_list(record.get("awake_agents")),
            nice_to_have_agents(record),
        )
        for record in nice_labeled
    ]
    negative_labeled = [record for record in evaluated if should_not_include_agents(record)]
    negative_rates = [
        len(
            set(_as_str_list(record.get("awake_agents"))).intersection(
                should_not_include_agents(record)
            )
        )
        / len(should_not_include_agents(record))
        for record in negative_labeled
    ]
    high_confidence_records = [
        record
        for record in evaluated
        if str(record.get("confidence_band", "") or "") == "high"
    ]
    high_confidence_wrong = [
        (
            any(
                agent_id not in _as_str_list(record.get("awake_agents"))
                for agent_id in critical_agents(record)
            )
            or expected_recall(
                _as_str_list(record.get("awake_agents")),
                must_include_agents(record),
            )
            < 1.0
        )
        for record in high_confidence_records
    ]

    if agent_costs is not None:
        resolved_agent_costs = dict(agent_costs)
    else:
        try:
            resolved_agent_costs = _agent_cost_levels()
        except Exception:
            resolved_agent_costs = {}
    cost_values = [_shortlist_cost(record, resolved_agent_costs) for record in evaluated]
    recall_per_cost_values = [
        recall_value / cost if cost > 0 else 0.0
        for recall_value, cost in zip(shortlist_recalls, cost_values, strict=False)
    ]
    calibration = _calibration_metrics(evaluated)

    wildcard_retained: list[bool] = []
    for record in evaluated:
        wildcards = _as_str_list(record.get("wildcard_agents"))
        if not wildcards:
            continue
        awake = set(_as_str_list(record.get("awake_agents")))
        wildcard_retained.append(bool(awake.intersection(wildcards)))

    false_negatives = collect_false_negatives(evaluated)
    false_negative_case_count = len(false_negatives)
    invalid_expected_agents = [
        {
            "id": str(record.get("id", "") or ""),
            "invalid_expected_agents": _as_str_list(record.get("invalid_expected_agents")),
        }
        for record in evaluated
        if _as_str_list(record.get("invalid_expected_agents"))
    ]
    metrics = {
        "meta": {
            **METRICS_META,
            "quality_conclusion_allowed": quality_conclusion_allowed,
            "proxy_quality_conclusion_only": proxy_quality_conclusion_only,
            "proxy_label_only": proxy_quality_conclusion_only,
            "deepseek_teacher_label_count": deepseek_teacher_count,
            "teacher_labels_warning": (
                DEEPSEEK_TEACHER_LABELS_WARNING if deepseek_teacher_count else ""
            ),
            "evaluated_case_count": case_count,
            "manual_label_count": manual_count,
            "quality_label_count": quality_label_count,
            "cost_metadata_available": bool(resolved_agent_costs),
        },
        "quality_conclusion_allowed": quality_conclusion_allowed,
        "proxy_quality_conclusion_only": proxy_quality_conclusion_only,
        "proxy_label_only": proxy_quality_conclusion_only,
        "case_count": case_count,
        "label_source_counts": dict(sorted(label_sources.items())),
        "enabled_rate": _rate([bool(record.get("enabled", False)) for record in evaluated]),
        "retrieval_reason_counts": dict(
            sorted(Counter(str(record.get("retrieval_reason", "") or "") for record in evaluated).items())
        ),
        "confidence_band_counts": dict(
            sorted(Counter(str(record.get("confidence_band", "") or "") for record in evaluated).items())
        ),
        "low_confidence_fallback_rate": _rate(
            [bool(record.get("low_confidence_fallback", False)) for record in evaluated]
        ),
        "avg_shortlist_size": _avg(shortlist_sizes),
        "avg_shortlist_ratio": _avg(shortlist_ratios),
        "top1_match_rate": _rate([topk_hit(record, 1) for record in evaluated]),
        "top3_match_rate": _rate([topk_hit(record, 3) for record in evaluated]),
        "top5_match_rate": _rate([topk_hit(record, 5) for record in evaluated]),
        "expected_agent_recall@1": _avg(top1_recalls),
        "expected_agent_recall@3": _avg(top3_recalls),
        "expected_agent_recall@5": _avg(top5_recalls),
        "expected_agent_recall_at_top1": _avg(top1_recalls),
        "expected_agent_recall_at_top3": _avg(top3_recalls),
        "expected_agent_recall_at_top5": _avg(top5_recalls),
        "shortlist_recall": _avg(shortlist_recalls),
        "safe_shortlist_recall": _avg(shortlist_recalls),
        "effective_shortlist_recall": _avg(effective_shortlist_recalls),
        "critical_agent_labeled_case_count": len(critical_labeled),
        "critical_agent_miss_rate": _nullable_avg(
            [1.0 if item else 0.0 for item in critical_misses]
        ),
        "precision_at_shortlist": _avg(precision_values),
        "f1_at_shortlist": _avg(f1_values),
        "jaccard_at_shortlist": _avg(jaccard_values),
        "nice_to_have_labeled_case_count": len(nice_labeled),
        "nice_to_have_recall": _nullable_avg(nice_recalls),
        "negative_labeled_case_count": len(negative_labeled),
        "negative_selection_rate": _nullable_avg(negative_rates),
        "avg_cost": _avg(cost_values),
        "recall_per_cost": _avg(recall_per_cost_values),
        "high_confidence_case_count": len(high_confidence_records),
        "high_confidence_wrong_rate": _nullable_avg(
            [1.0 if item else 0.0 for item in high_confidence_wrong]
        ),
        "ECE": calibration["ECE"],
        "Brier": calibration["Brier"],
        "calibration_pair_count": calibration["calibration_pair_count"],
        "calibration_bin_count": calibration["calibration_bin_count"],
        "full_expected_covered_rate": _rate(full_expected_covered),
        "wildcard_retention_rate": _rate(wildcard_retained) if wildcard_retained else None,
        "formal_router_overlap_observation": _formal_router_overlap(evaluated),
        "false_negative_count": false_negative_case_count,
        "false_negative_case_count": false_negative_case_count,
        "false_negative_agent_count": false_negative_agent_count(false_negatives),
        "false_negative_examples": false_negatives,
        "invalid_expected_agent_count": len(invalid_expected_agents),
        "invalid_expected_agents": invalid_expected_agents,
        "conservative_pruning": aggregate_conservative_pruning(evaluated),
    }
    if _include_label_source_groups:
        metrics["label_source_grouped_metrics"] = {
            source: aggregate_metrics(
                [record for record in evaluated if str(record.get("label_source", "") or "") == source],
                include_draft_labels=True,
                require_manual_labels=False,
                agent_costs=resolved_agent_costs,
                _include_label_source_groups=False,
            )
            for source in sorted(label_sources)
        }
    return metrics


def write_json(payload: JsonMapping, path: Path) -> None:
    """Write a JSON payload to disk with stable formatting."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Evaluate RP-1B route-prior run outputs.")
    parser.add_argument("--runs", required=True, help="Path to route_prior_runs.jsonl.")
    parser.add_argument(
        "--out",
        default=str(REPO_ROOT / "ops" / "regression" / "route_prior" / "out" / "route_prior_metrics.json"),
        help="Output metrics JSON path.",
    )
    parser.add_argument(
        "--false-negatives-out",
        default=str(
            REPO_ROOT
            / "ops"
            / "regression"
            / "route_prior"
            / "out"
            / "route_prior_false_negatives.json"
        ),
        help="Output false-negative examples JSON path.",
    )
    parser.add_argument(
        "--require-manual-labels",
        action="store_true",
        help="Evaluate only manual or manual_gold records.",
    )
    parser.add_argument(
        "--include-draft-labels",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Include draft_for_human_review records in metrics.",
    )
    return parser.parse_args()


def main() -> int:
    """Run the route-prior metrics aggregation CLI."""
    args = parse_args()
    records = load_run_records(Path(args.runs))
    metrics = aggregate_metrics(
        records,
        include_draft_labels=bool(args.include_draft_labels),
        require_manual_labels=bool(args.require_manual_labels),
    )
    false_negatives = {
        "meta": metrics["meta"],
        "false_negative_count": metrics["false_negative_count"],
        "false_negative_case_count": metrics["false_negative_case_count"],
        "false_negative_agent_count": metrics["false_negative_agent_count"],
        "false_negative_examples": metrics["false_negative_examples"],
    }
    out_path = Path(args.out)
    false_negatives_path = Path(args.false_negatives_out)
    write_json(metrics, out_path)
    write_json(cast(JsonMapping, false_negatives), false_negatives_path)
    sys.stdout.write(f"case_count: {metrics['case_count']}\n")
    sys.stdout.write(f"shortlist_recall: {float(metrics['shortlist_recall']):.4f}\n")
    sys.stdout.write(f"false_negative_count: {metrics['false_negative_count']}\n")
    sys.stdout.write(f"out: {out_path}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
