# ruff: noqa: D101
"""Provider-free RouteEval helpers for route_intent_v1 selections."""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from react_agent.fixed_dag_contracts import build_default_route_intent


@dataclass(frozen=True)
class RouteEvalCase:
    id: str
    query: str
    gold_task_type: str
    gold_targets: tuple[str, ...]
    gold_dimensions: tuple[str, ...]
    gold_agents: tuple[str, ...]
    gold_needs_clarification: bool
    must_not_agents: tuple[str, ...] = ()
    acceptable_extra_agents: tuple[str, ...] = ()
    notes: str = ""


@dataclass(frozen=True)
class RouteEvalReport:
    case_count: int
    task_type_accuracy: float
    target_exact_or_partial_match: float
    dimension_precision: float
    dimension_recall: float
    dimension_f1: float
    agent_precision: float
    agent_recall: float
    agent_f1: float
    over_selection_count: int
    under_selection_count: int
    clarification_accuracy: float
    fallback_rate: float
    cases: tuple[dict[str, Any], ...]


PlannerFn = Callable[[str], Mapping[str, Any]]


def _as_tuple(raw: Any) -> tuple[str, ...]:
    if not isinstance(raw, list):
        return ()
    return tuple(str(item).strip() for item in raw if str(item).strip())


def _safe_float(numerator: int, denominator: int) -> float:
    if denominator == 0:
        return 1.0
    return numerator / denominator


def _f1(precision: float, recall: float) -> float:
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


def _has_fallback(intent: Mapping[str, Any]) -> bool:
    if bool(intent.get("needs_clarification")):
        return True
    fallback_reason = str(intent.get("fallback_reason") or "").strip()
    provenance = intent.get("provenance")
    provenance_reason = ""
    if isinstance(provenance, Mapping):
        provenance_reason = str(provenance.get("fallback_reason") or "").strip()
    return bool(fallback_reason or provenance_reason)


def _load_route_eval_case(raw: Mapping[str, Any]) -> RouteEvalCase:
    return RouteEvalCase(
        id=str(raw["id"]),
        query=str(raw["query"]),
        gold_task_type=str(raw["gold_task_type"]),
        gold_targets=_as_tuple(raw.get("gold_targets")),
        gold_dimensions=_as_tuple(raw.get("gold_dimensions")),
        gold_agents=_as_tuple(raw.get("gold_agents")),
        gold_needs_clarification=bool(raw.get("gold_needs_clarification", False)),
        must_not_agents=_as_tuple(raw.get("must_not_agents")),
        acceptable_extra_agents=_as_tuple(raw.get("acceptable_extra_agents")),
        notes=str(raw.get("notes") or ""),
    )


def load_route_eval_cases(path: Path) -> list[RouteEvalCase]:
    """Load deterministic JSONL RouteEval cases from a local fixture."""
    cases: list[RouteEvalCase] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        raw = json.loads(stripped)
        if not isinstance(raw, Mapping):
            raise ValueError(f"route_eval_case_not_object:{line_number}")
        cases.append(_load_route_eval_case(raw))
    return cases


def _score_set_selection(
    *,
    predicted: Sequence[str],
    gold: Sequence[str],
    acceptable_extra: Sequence[str] = (),
    must_not: Sequence[str] = (),
) -> dict[str, Any]:
    predicted_set = set(predicted)
    gold_set = set(gold)
    acceptable_extra_set = set(acceptable_extra)
    must_not_set = set(must_not)

    true_positive = len(predicted_set & gold_set)
    false_positive_items = (predicted_set - gold_set - acceptable_extra_set) | (
        predicted_set & must_not_set
    )
    false_negative_items = gold_set - predicted_set
    false_positive = len(false_positive_items)
    false_negative = len(false_negative_items)
    precision = _safe_float(true_positive, true_positive + false_positive)
    recall = _safe_float(true_positive, true_positive + false_negative)
    return {
        "true_positive": true_positive,
        "false_positive": false_positive,
        "false_negative": false_negative,
        "precision": precision,
        "recall": recall,
        "f1": _f1(precision, recall),
        "false_positive_items": sorted(false_positive_items),
        "false_negative_items": sorted(false_negative_items),
    }


def _target_matches(predicted: Sequence[str], gold: Sequence[str]) -> bool:
    if not gold:
        return not predicted
    predicted_set = {item.lower() for item in predicted}
    gold_set = {item.lower() for item in gold}
    return predicted_set == gold_set or bool(predicted_set & gold_set)


def evaluate_route_intents(
    cases: Sequence[RouteEvalCase],
    planner_fn: PlannerFn = build_default_route_intent,
) -> RouteEvalReport:
    """Evaluate provider-free planner output against route_intent_v1 gold cases."""
    task_matches = 0
    target_matches = 0
    clarification_matches = 0
    fallback_count = 0
    over_selection_count = 0
    under_selection_count = 0
    dim_tp = dim_fp = dim_fn = 0
    agent_tp = agent_fp = agent_fn = 0
    case_results: list[dict[str, Any]] = []

    for case in cases:
        intent = dict(planner_fn(case.query))
        predicted_dimensions = _as_tuple(intent.get("selected_dimensions"))
        predicted_agents = _as_tuple(intent.get("selected_agents"))
        predicted_targets = _as_tuple(intent.get("targets"))
        task_match = intent.get("task_type") == case.gold_task_type
        target_match = _target_matches(predicted_targets, case.gold_targets)
        clarification_match = (
            bool(intent.get("needs_clarification")) == case.gold_needs_clarification
        )
        fallback_used = _has_fallback(intent)
        dimension_score = _score_set_selection(
            predicted=predicted_dimensions,
            gold=case.gold_dimensions,
        )
        agent_score = _score_set_selection(
            predicted=predicted_agents,
            gold=case.gold_agents,
            acceptable_extra=case.acceptable_extra_agents,
            must_not=case.must_not_agents,
        )

        task_matches += int(task_match)
        target_matches += int(target_match)
        clarification_matches += int(clarification_match)
        fallback_count += int(fallback_used)
        dim_tp += int(dimension_score["true_positive"])
        dim_fp += int(dimension_score["false_positive"])
        dim_fn += int(dimension_score["false_negative"])
        agent_tp += int(agent_score["true_positive"])
        agent_fp += int(agent_score["false_positive"])
        agent_fn += int(agent_score["false_negative"])
        over_selection_count += int(dimension_score["false_positive"]) + int(
            agent_score["false_positive"]
        )
        under_selection_count += int(dimension_score["false_negative"]) + int(
            agent_score["false_negative"]
        )
        case_results.append(
            {
                "id": case.id,
                "task_type_match": task_match,
                "target_match": target_match,
                "clarification_match": clarification_match,
                "fallback_used": fallback_used,
                "dimension": dimension_score,
                "agent": agent_score,
            }
        )

    case_count = len(cases)
    dimension_precision = _safe_float(dim_tp, dim_tp + dim_fp)
    dimension_recall = _safe_float(dim_tp, dim_tp + dim_fn)
    agent_precision = _safe_float(agent_tp, agent_tp + agent_fp)
    agent_recall = _safe_float(agent_tp, agent_tp + agent_fn)
    return RouteEvalReport(
        case_count=case_count,
        task_type_accuracy=_safe_float(task_matches, case_count),
        target_exact_or_partial_match=_safe_float(target_matches, case_count),
        dimension_precision=dimension_precision,
        dimension_recall=dimension_recall,
        dimension_f1=_f1(dimension_precision, dimension_recall),
        agent_precision=agent_precision,
        agent_recall=agent_recall,
        agent_f1=_f1(agent_precision, agent_recall),
        over_selection_count=over_selection_count,
        under_selection_count=under_selection_count,
        clarification_accuracy=_safe_float(clarification_matches, case_count),
        fallback_rate=_safe_float(fallback_count, case_count),
        cases=tuple(case_results),
    )


def route_eval_report_to_dict(report: RouteEvalReport) -> dict[str, Any]:
    """Convert a RouteEval report to a stable JSON-serializable mapping."""
    return {
        "case_count": report.case_count,
        "task_type_accuracy": report.task_type_accuracy,
        "target_exact_or_partial_match": report.target_exact_or_partial_match,
        "dimension_precision": report.dimension_precision,
        "dimension_recall": report.dimension_recall,
        "dimension_f1": report.dimension_f1,
        "agent_precision": report.agent_precision,
        "agent_recall": report.agent_recall,
        "agent_f1": report.agent_f1,
        "over_selection_count": report.over_selection_count,
        "under_selection_count": report.under_selection_count,
        "clarification_accuracy": report.clarification_accuracy,
        "fallback_rate": report.fallback_rate,
        "cases": list(report.cases),
    }


__all__ = [
    "RouteEvalCase",
    "RouteEvalReport",
    "evaluate_route_intents",
    "load_route_eval_cases",
    "route_eval_report_to_dict",
]
