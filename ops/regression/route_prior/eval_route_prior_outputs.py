#!/usr/bin/env python
"""Aggregate RP-1B offline route-prior run outputs into metrics."""

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
    "phase": "RP-1B",
    "scope": "offline_shadow_validation",
    "runtime_semantics_changed": False,
    "formal_router_changed": False,
    "public_surface_changed": False,
    "labels_warning": "draft labels are not final quality evidence",
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
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


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


def load_run_records(path: Path) -> list[JsonDict]:
    """Load RP-1B route-prior run records from JSONL."""
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
    expected = set(_as_str_list(record.get("expected_agents")))
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
        if require_manual_labels and source != "manual":
            continue
        if not include_draft_labels and source == "draft_for_human_review":
            continue
        filtered.append(record)
    return filtered


def collect_false_negatives(records: Sequence[JsonMapping]) -> list[JsonDict]:
    """Collect cases whose expected agents are missing from awake_agents."""
    examples: list[JsonDict] = []
    for record in records:
        expected = _as_str_list(record.get("expected_agents"))
        awake = _as_str_list(record.get("awake_agents"))
        missing = [agent_id for agent_id in expected if agent_id not in awake]
        if not missing:
            continue
        examples.append(
            {
                "id": str(record.get("id", "") or ""),
                "question": str(record.get("question", "") or ""),
                "expected_agents": expected,
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
        expected = _as_str_list(record.get("expected_agents"))
        missing = [agent_id for agent_id in expected if agent_id not in pruned_agents]
        if not missing:
            continue
        examples.append(
            {
                "id": str(record.get("id", "") or ""),
                "question": str(record.get("question", "") or ""),
                "expected_agents": expected,
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
                _as_str_list(record.get("expected_agents")),
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
) -> JsonDict:
    """Aggregate RP-1B route-prior validation metrics."""
    evaluated = _filtered_records(
        records,
        include_draft_labels=include_draft_labels,
        require_manual_labels=require_manual_labels,
    )
    case_count = len(evaluated)
    label_sources = Counter(str(record.get("label_source", "") or "") for record in evaluated)
    manual_count = label_sources.get("manual", 0)
    quality_conclusion_allowed = manual_count > 0

    shortlist_sizes = [float(len(_as_str_list(record.get("awake_agents")))) for record in evaluated]
    shortlist_ratios: list[float] = []
    for record in evaluated:
        ordinary_pool_size = int(record.get("ordinary_pool_size", 0) or 0)
        shortlist_size = len(_as_str_list(record.get("awake_agents")))
        if ordinary_pool_size > 0:
            shortlist_ratios.append(shortlist_size / ordinary_pool_size)

    top5_recalls = [
        expected_recall(
            top_ranked_ids(record)[:5],
            _as_str_list(record.get("expected_agents")),
        )
        for record in evaluated
    ]
    shortlist_recalls = [
        expected_recall(
            _as_str_list(record.get("awake_agents")),
            _as_str_list(record.get("expected_agents")),
        )
        for record in evaluated
    ]
    full_expected_covered = [
        expected_recall(
            _as_str_list(record.get("awake_agents")),
            _as_str_list(record.get("expected_agents")),
        )
        == 1.0
        for record in evaluated
    ]
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
            "evaluated_case_count": case_count,
            "manual_label_count": manual_count,
        },
        "quality_conclusion_allowed": quality_conclusion_allowed,
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
        "expected_agent_recall_at_top5": _avg(top5_recalls),
        "shortlist_recall": _avg(shortlist_recalls),
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
        help="Evaluate only label_source=manual records.",
    )
    parser.add_argument(
        "--include-draft-labels",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Include draft_for_human_review records in metrics.",
    )
    return parser.parse_args()


def main() -> int:
    """Run the RP-1B metrics aggregation CLI."""
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
