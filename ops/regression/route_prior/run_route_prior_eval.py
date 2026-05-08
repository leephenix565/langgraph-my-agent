#!/usr/bin/env python
"""Run offline route-prior validation against labeled questions."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast

import httpx

JsonDict = dict[str, Any]
JsonMapping = Mapping[str, Any]
QUALITY_LABEL_SOURCES = {"manual", "manual_gold"}
NON_QUALITY_LABEL_SOURCES = {"draft_for_human_review", "deepseek_teacher_v1"}
COST_VALUES = {
    "low": 1.0,
    "normal": 2.0,
    "medium": 2.0,
    "high": 3.0,
    "unknown": 2.0,
    "": 2.0,
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

@dataclass(frozen=True)
class LabelCase:
    """Represent one labeled route-prior validation case."""

    case_id: str
    question: str
    expected_agents: list[str]
    tags: list[str]
    label_source: str
    formal_router_selected: list[str] | None = None
    notes: str = ""
    schema_version: str = "rp1b_legacy"
    must_include_agents: list[str] = field(default_factory=list)
    critical_agents: list[str] = field(default_factory=list)
    nice_to_have_agents: list[str] = field(default_factory=list)
    should_not_include_agents: list[str] = field(default_factory=list)
    quality_conclusion_allowed: bool = False
    task_type: str = ""
    difficulty: str = ""
    risk_level: str = ""


def _as_str_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    out: list[str] = []
    seen: set[str] = set()
    for item in value:
        if not isinstance(item, str):
            continue
        normalized = item.strip()
        if not normalized or normalized in seen:
            continue
        out.append(normalized)
        seen.add(normalized)
    return out


def _required_str(payload: JsonMapping, key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Label case missing required string field: {key}")
    return value.strip()


def _optional_str(payload: JsonMapping, key: str) -> str:
    value = payload.get(key)
    return value.strip() if isinstance(value, str) and value.strip() else ""


def _quality_conclusion_allowed(label_source: str, raw_value: object) -> bool:
    requested = raw_value if isinstance(raw_value, bool) else None
    if label_source in NON_QUALITY_LABEL_SOURCES:
        if requested is True:
            raise ValueError(
                f"label_source={label_source!r} cannot set quality_conclusion_allowed=true"
            )
        return False
    if label_source in QUALITY_LABEL_SOURCES:
        if label_source == "manual_gold" and requested is False:
            raise ValueError("manual_gold requires quality_conclusion_allowed=true")
        return True if requested is None else bool(requested)
    if requested is True:
        raise ValueError(
            "quality_conclusion_allowed=true requires label_source manual or manual_gold"
        )
    return False


def _validate_label_sets(
    *,
    must_include_agents: Sequence[str],
    critical_agents: Sequence[str],
    should_not_include_agents: Sequence[str],
) -> None:
    must = set(must_include_agents)
    critical = set(critical_agents)
    negative = set(should_not_include_agents)
    if not critical.issubset(must):
        missing = sorted(critical - must)
        raise ValueError(
            "critical_agents must be a subset of must_include_agents: "
            + ", ".join(missing)
        )
    overlap = sorted(must & negative)
    if overlap:
        raise ValueError(
            "must_include_agents and should_not_include_agents overlap: "
            + ", ".join(overlap)
        )


def label_case_from_record(payload: JsonMapping) -> LabelCase:
    """Build a LabelCase from one JSON object."""
    label_source = _required_str(payload, "label_source")
    schema_version = _optional_str(payload, "schema_version") or "rp1b_legacy"
    legacy_expected_agents = _as_str_list(payload.get("expected_agents"))
    must_include_agents = _as_str_list(payload.get("must_include_agents"))
    if not must_include_agents:
        must_include_agents = legacy_expected_agents
    if not must_include_agents:
        raise ValueError(
            "Label case must include must_include_agents or legacy expected_agents"
        )
    critical_agents = _as_str_list(payload.get("critical_agents"))
    nice_to_have_agents = _as_str_list(payload.get("nice_to_have_agents"))
    should_not_include_agents = _as_str_list(payload.get("should_not_include_agents"))
    _validate_label_sets(
        must_include_agents=must_include_agents,
        critical_agents=critical_agents,
        should_not_include_agents=should_not_include_agents,
    )
    quality_conclusion_allowed = _quality_conclusion_allowed(
        label_source, payload.get("quality_conclusion_allowed")
    )
    formal_router_selected: list[str] | None = None
    if "formal_router_selected" in payload:
        formal_router_selected = _as_str_list(payload.get("formal_router_selected"))
    notes = payload.get("notes")
    return LabelCase(
        case_id=_required_str(payload, "id"),
        question=_required_str(payload, "question"),
        expected_agents=list(must_include_agents),
        tags=_as_str_list(payload.get("tags")),
        label_source=label_source,
        formal_router_selected=formal_router_selected,
        notes=notes if isinstance(notes, str) else "",
        schema_version=schema_version,
        must_include_agents=list(must_include_agents),
        critical_agents=critical_agents,
        nice_to_have_agents=nice_to_have_agents,
        should_not_include_agents=should_not_include_agents,
        quality_conclusion_allowed=quality_conclusion_allowed,
        task_type=_optional_str(payload, "task_type"),
        difficulty=_optional_str(payload, "difficulty"),
        risk_level=_optional_str(payload, "risk_level"),
    )


def load_label_cases(path: Path) -> list[LabelCase]:
    """Load labeled route-prior cases from JSONL."""
    cases: list[LabelCase] = []
    with path.open("r", encoding="utf-8") as fh:
        for line_no, line in enumerate(fh, start=1):
            text = line.strip()
            if not text:
                continue
            obj = json.loads(text)
            if not isinstance(obj, dict):
                raise ValueError(f"Dataset line {line_no} is not an object")
            try:
                cases.append(label_case_from_record(cast(JsonMapping, obj)))
            except ValueError as exc:
                raise ValueError(f"Dataset line {line_no}: {exc}") from exc
    return cases


def validate_label_case(case: LabelCase, known_agent_ids: set[str]) -> list[str]:
    """Return label agent ids that are not present in known metadata."""
    invalid: list[str] = []
    seen: set[str] = set()
    for agent_id in (
        list(case.expected_agents)
        + list(case.critical_agents)
        + list(case.nice_to_have_agents)
        + list(case.should_not_include_agents)
    ):
        if agent_id in known_agent_ids or agent_id in seen:
            continue
        invalid.append(agent_id)
        seen.add(agent_id)
    return invalid


async def prewarm_embedding_endpoint(
    profiles: Sequence[Any],
    *,
    timeout: float,
) -> JsonDict:
    """Prewarm the configured embedding endpoint with ordinary profile texts."""
    from react_agent.route_prior_embeddings import (  # type: ignore[import-not-found]
        resolve_embedding_backend_config,
    )

    config = resolve_embedding_backend_config()
    if not config.enabled:
        return {
            "enabled": False,
            "reason": config.reason,
            "profile_count": len(profiles),
            "embedding_count": 0,
            "embedding_dim": 0,
        }
    payload = {
        "model": config.model,
        "input": [profile.profile_text for profile in profiles],
    }
    headers = {
        "Authorization": f"Bearer {config.api_key}",
        "Content-Type": "application/json",
    }
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(f"{config.base_url}/embeddings", headers=headers, json=payload)
        response.raise_for_status()
        body = response.json()
    raw_items = body.get("data")
    if not isinstance(raw_items, list):
        raise ValueError("embedding prewarm response missing data list")
    embedding_dim = 0
    if raw_items:
        first = raw_items[0]
        if isinstance(first, Mapping):
            embedding = first.get("embedding")
            if isinstance(embedding, list):
                embedding_dim = len(embedding)
    return {
        "enabled": True,
        "reason": "ok",
        "profile_count": len(profiles),
        "embedding_count": len(raw_items),
        "embedding_dim": embedding_dim,
    }


def _score_light(route_scores: object, *, limit: int | None = None) -> list[JsonDict]:
    if not isinstance(route_scores, list):
        return []
    items: list[JsonDict] = []
    selected_scores = route_scores[:limit] if limit is not None else route_scores
    for raw_item in selected_scores:
        if not isinstance(raw_item, Mapping):
            continue
        items.append(
            {
                "agent_id": str(raw_item.get("agent_id", "") or ""),
                "semantic_similarity_score": float(
                    raw_item.get("semantic_similarity_score", 0.0) or 0.0
                ),
                "cost_tiebreak_score": float(raw_item.get("cost_tiebreak_score", 0.0) or 0.0),
                "wildcard_flag": bool(raw_item.get("wildcard_flag", False)),
                "confidence_band": str(raw_item.get("confidence_band", "") or ""),
            }
        )
    return items


def _score_all_light(route_scores: object) -> list[JsonDict]:
    if not isinstance(route_scores, list):
        return []
    items: list[JsonDict] = []
    for raw_item in route_scores:
        if not isinstance(raw_item, Mapping):
            continue
        items.append(
            {
                "agent_id": str(raw_item.get("agent_id", "") or ""),
                "semantic_similarity_score": round(
                    float(raw_item.get("semantic_similarity_score", 0.0) or 0.0),
                    6,
                ),
                "wildcard_flag": bool(raw_item.get("wildcard_flag", False)),
                "confidence_band": str(raw_item.get("confidence_band", "") or ""),
            }
        )
    return items


def _shadow_confidence_band(shadow: JsonMapping) -> str:
    routing_hint = shadow.get("routing_hint")
    if isinstance(routing_hint, Mapping):
        confidence_band = routing_hint.get("confidence_band")
        if isinstance(confidence_band, str):
            return confidence_band
    route_semantics = shadow.get("route_semantics")
    if isinstance(route_semantics, Mapping):
        confidence_band = route_semantics.get("similarity_confidence_band")
        if isinstance(confidence_band, str):
            return confidence_band
    return ""


def _shadow_reason_codes(shadow: JsonMapping) -> list[str]:
    routing_hint = shadow.get("routing_hint")
    if isinstance(routing_hint, Mapping):
        reason_codes = routing_hint.get("reason_codes")
        return _as_str_list(reason_codes)
    return []


def _question_hash(question: str) -> str:
    return "sha256:" + hashlib.sha256(question.encode("utf-8")).hexdigest()


def _question_preview(question: str, *, limit: int = 160) -> str:
    text = question.strip()
    return text if len(text) <= limit else text[: limit - 8] + "...[trunc]"


def _cost_value_for_agent(agent_id: str, metadata_by_id: Mapping[str, Any]) -> float:
    meta = metadata_by_id.get(agent_id)
    cost_level = str(getattr(meta, "cost_level", "") or "").strip().lower()
    return COST_VALUES.get(cost_level, COST_VALUES["unknown"])


def _recall(selected: Sequence[str], expected: Sequence[str]) -> float:
    expected_set = set(expected)
    if not expected_set:
        return 0.0
    return len(expected_set.intersection(selected)) / len(expected_set)


def _case_metrics(
    case: LabelCase,
    *,
    awake_agents: Sequence[str],
    top_ranked_ids: Sequence[str],
    low_confidence_fallback: bool,
    metadata_by_id: Mapping[str, Any],
) -> JsonDict:
    must_include = case.must_include_agents or case.expected_agents
    safe_recall = _recall(awake_agents, must_include)
    effective_recall = 0.0 if low_confidence_fallback else safe_recall
    critical_miss = any(agent_id not in awake_agents for agent_id in case.critical_agents)
    negative_total = len(case.should_not_include_agents)
    negative_selected = len(set(awake_agents).intersection(case.should_not_include_agents))
    shortlist_cost = sum(_cost_value_for_agent(agent_id, metadata_by_id) for agent_id in awake_agents)
    return {
        "recall_at_5": _recall(top_ranked_ids[:5], must_include),
        "safe_shortlist_recall": safe_recall,
        "effective_shortlist_recall": effective_recall,
        "critical_miss": critical_miss,
        "negative_selection_rate": (
            negative_selected / negative_total if negative_total else 0.0
        ),
        "shortlist_cost": shortlist_cost,
    }


async def run_case(
    case: LabelCase,
    metadata_by_id: Mapping[str, Any],
    *,
    invalid_expected_agents: list[str],
    rarp_scoring_enabled: bool = False,
    profile_cards: Mapping[str, Any] | None = None,
    reliability_table: Mapping[str, Any] | None = None,
) -> JsonDict:
    """Run one labeled case through the RP-1A shadow helper."""
    from react_agent import route_prior

    try:
        shadow = await route_prior.compute_route_prior_shadow(case.question, metadata_by_id)
        route_scores_top10 = _score_light(shadow.get("route_scores"), limit=10)
        route_scores_all_light = _score_all_light(shadow.get("route_scores"))
        top_ranked_ids = [
            str(item.get("agent_id", "") or "") for item in route_scores_top10 if item.get("agent_id")
        ]
        record: JsonDict = {
            "schema_version": "route_prior_run_v2",
            "id": case.case_id,
            "question_hash": _question_hash(case.question),
            "question_preview": _question_preview(case.question),
            "question": case.question,
            "expected_agents": case.expected_agents,
            "must_include_agents": case.must_include_agents or case.expected_agents,
            "critical_agents": case.critical_agents,
            "nice_to_have_agents": case.nice_to_have_agents,
            "should_not_include_agents": case.should_not_include_agents,
            "label_source": case.label_source,
            "quality_conclusion_allowed": case.quality_conclusion_allowed,
            "label_schema_version": case.schema_version,
            "task_type": case.task_type,
            "difficulty": case.difficulty,
            "risk_level": case.risk_level,
            "labels": {
                "must_include_agents": case.must_include_agents or case.expected_agents,
                "critical_agents": case.critical_agents,
                "nice_to_have_agents": case.nice_to_have_agents,
                "should_not_include_agents": case.should_not_include_agents,
            },
            "tags": case.tags,
            "enabled": bool(shadow.get("enabled", False)),
            "retrieval_reason": str(shadow.get("retrieval_reason", "") or ""),
            "confidence_band": _shadow_confidence_band(shadow),
            "low_confidence_fallback": bool(shadow.get("low_confidence_fallback", False)),
            "ordinary_pool_size": len(_as_str_list(shadow.get("ordinary_pool"))),
            "shortlist_size": len(_as_str_list(shadow.get("awake_agents"))),
            "awake_agents": _as_str_list(shadow.get("awake_agents")),
            "top_ranked_ids": top_ranked_ids,
            "route_scores_top10": route_scores_top10,
            "route_scores_all_agent_ids": [
                str(item.get("agent_id", "") or "")
                for item in route_scores_all_light
                if item.get("agent_id")
            ],
            "route_scores_all_light": route_scores_all_light,
            "wildcard_agents": _as_str_list(shadow.get("wildcard_agents")),
            "cache_hits": int(shadow.get("cache_hits", 0) or 0),
            "cache_misses": int(shadow.get("cache_misses", 0) or 0),
            "invalid_expected_agents": invalid_expected_agents,
            "invalid_label_agents": invalid_expected_agents,
            "reason_codes": _shadow_reason_codes(shadow),
            "case_metrics": _case_metrics(
                case,
                awake_agents=_as_str_list(shadow.get("awake_agents")),
                top_ranked_ids=top_ranked_ids,
                low_confidence_fallback=bool(shadow.get("low_confidence_fallback", False)),
                metadata_by_id=metadata_by_id,
            ),
            "error": "",
        }
        if rarp_scoring_enabled:
            try:
                from react_agent.route_reliability import (  # type: ignore[import-not-found]
                    build_route_reliability_shadow,
                )

                record["route_reliability"] = build_route_reliability_shadow(
                    route_scores=route_scores_all_light,
                    metadata_by_id=metadata_by_id,
                    ordinary_pool=_as_str_list(shadow.get("ordinary_pool")),
                    wildcard_agents=_as_str_list(shadow.get("wildcard_agents")),
                    reliability_table=reliability_table,
                    profile_cards=profile_cards,
                    low_confidence_fallback=bool(shadow.get("low_confidence_fallback", False)),
                    confidence_band=_shadow_confidence_band(shadow),
                    task_type=case.task_type,
                )
                record["rarp_scoring_enabled"] = True
            except Exception as scorer_exc:
                record["rarp_scoring_enabled"] = False
                record["route_reliability_error"] = (
                    f"{type(scorer_exc).__name__}: {scorer_exc}"
                )
    except Exception as exc:
        record = {
            "schema_version": "route_prior_run_v2",
            "id": case.case_id,
            "question_hash": _question_hash(case.question),
            "question_preview": _question_preview(case.question),
            "question": case.question,
            "expected_agents": case.expected_agents,
            "must_include_agents": case.must_include_agents or case.expected_agents,
            "critical_agents": case.critical_agents,
            "nice_to_have_agents": case.nice_to_have_agents,
            "should_not_include_agents": case.should_not_include_agents,
            "label_source": case.label_source,
            "quality_conclusion_allowed": case.quality_conclusion_allowed,
            "label_schema_version": case.schema_version,
            "task_type": case.task_type,
            "difficulty": case.difficulty,
            "risk_level": case.risk_level,
            "labels": {
                "must_include_agents": case.must_include_agents or case.expected_agents,
                "critical_agents": case.critical_agents,
                "nice_to_have_agents": case.nice_to_have_agents,
                "should_not_include_agents": case.should_not_include_agents,
            },
            "tags": case.tags,
            "enabled": False,
            "retrieval_reason": "runner_error",
            "confidence_band": "",
            "low_confidence_fallback": False,
            "ordinary_pool_size": 0,
            "shortlist_size": 0,
            "awake_agents": [],
            "top_ranked_ids": [],
            "route_scores_top10": [],
            "route_scores_all_agent_ids": [],
            "route_scores_all_light": [],
            "wildcard_agents": [],
            "cache_hits": 0,
            "cache_misses": 0,
            "invalid_expected_agents": invalid_expected_agents,
            "invalid_label_agents": invalid_expected_agents,
            "reason_codes": [],
            "case_metrics": {
                "recall_at_5": 0.0,
                "safe_shortlist_recall": 0.0,
                "effective_shortlist_recall": 0.0,
                "critical_miss": bool(case.critical_agents),
                "negative_selection_rate": 0.0,
                "shortlist_cost": 0.0,
            },
            "error": f"{type(exc).__name__}: {exc}",
        }
        if rarp_scoring_enabled:
            record["rarp_scoring_enabled"] = False
            record["route_reliability_error"] = "route_prior_unavailable"
    if case.formal_router_selected is not None:
        record["formal_router_selected"] = case.formal_router_selected
    return record


def write_jsonl(records: Sequence[JsonMapping], path: Path) -> None:
    """Write route-prior run records as JSONL."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for record in records:
            fh.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")


def write_json(payload: JsonMapping, path: Path) -> None:
    """Write a JSON payload to disk with stable formatting."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def build_run_summary(
    records: Sequence[JsonMapping],
    *,
    dataset: Path,
    invalid_cases: Sequence[JsonMapping],
    prewarm_summary: JsonMapping | None,
    rarp_scoring: JsonMapping | None = None,
) -> JsonDict:
    """Build a compact summary for one route-prior eval run."""
    return {
        "meta": {
            "phase": "RP-2A",
            "scope": "offline_eval_tooling",
            "schema_version": "route_prior_run_summary_v2",
            "legacy_rp1b_compatible": True,
            "runtime_semantics_changed": False,
            "formal_router_changed": False,
            "public_surface_changed": False,
            "labels_warning": "draft labels are not final quality evidence",
        },
        "dataset": str(dataset),
        "case_count": len(records),
        "enabled_count": sum(1 for record in records if bool(record.get("enabled", False))),
        "disabled_count": sum(1 for record in records if not bool(record.get("enabled", False))),
        "invalid_case_count": len(invalid_cases),
        "invalid_cases": list(invalid_cases),
        "prewarm": dict(prewarm_summary or {}),
        "rarp_scoring": dict(rarp_scoring or {"enabled": False}),
    }


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Run offline route-prior validation.")
    parser.add_argument("--dataset", required=True, help="Labeled question JSONL path.")
    parser.add_argument(
        "--out-dir",
        default=str(REPO_ROOT / "ops" / "regression" / "route_prior" / "out"),
        help="Output directory.",
    )
    parser.add_argument("--max-items", type=int, default=None, help="Optional max case count.")
    parser.add_argument(
        "--require-enabled",
        action="store_true",
        help="Fail if any run record has enabled=false.",
    )
    parser.add_argument(
        "--prewarm-endpoint",
        action="store_true",
        help="Prewarm the configured embeddings endpoint with ordinary profile texts.",
    )
    parser.add_argument("--prewarm-timeout", type=float, default=120.0, help="Prewarm timeout seconds.")
    parser.add_argument(
        "--include-invalid-labels",
        action="store_true",
        help="Include cases with unknown expected agent ids instead of failing early.",
    )
    parser.add_argument(
        "--output-jsonl",
        default="route_prior_runs.jsonl",
        help="Output run-record JSONL file name.",
    )
    parser.add_argument(
        "--summary-json",
        default="route_prior_run_summary.json",
        help="Output run-summary JSON file name.",
    )
    parser.add_argument(
        "--enable-rarp-scoring",
        action="store_true",
        help="Include optional RP-2B reliability cards in offline run artifacts.",
    )
    parser.add_argument(
        "--profile-cards-dir",
        default="",
        help="Optional internal route profile cards directory for RP-2B scoring.",
    )
    parser.add_argument(
        "--reliability-table",
        default="",
        help="Optional internal route reliability table JSON for RP-2B scoring.",
    )
    return parser.parse_args()


async def _run(args: argparse.Namespace) -> int:
    from react_agent.agents import (  # type: ignore[import-not-found]
        AGENT_METADATA,
        load_metadata_from_dir,
    )
    from react_agent.route_profile_registry import (  # type: ignore[import-not-found]
        build_route_profile_registry,
        load_route_profile_cards,
    )
    from react_agent.route_reliability import (  # type: ignore[import-not-found]
        load_reliability_table,
    )

    dataset = Path(args.dataset)
    out_dir = Path(args.out_dir)
    cases = load_label_cases(dataset)
    max_items = args.max_items
    if isinstance(max_items, int) and max_items >= 0:
        cases = cases[:max_items]

    AGENT_METADATA.clear()
    load_metadata_from_dir(REPO_ROOT / "config" / "agents")
    registry = build_route_profile_registry(AGENT_METADATA)
    known_agent_ids = set(AGENT_METADATA.keys())
    rarp_scoring_enabled = bool(args.enable_rarp_scoring)
    profile_card_result = load_route_profile_cards(
        Path(args.profile_cards_dir) if str(args.profile_cards_dir or "").strip() else None,
        AGENT_METADATA,
    ) if rarp_scoring_enabled else None
    reliability_table = load_reliability_table(
        Path(args.reliability_table) if str(args.reliability_table or "").strip() else None
    ) if rarp_scoring_enabled else {}

    invalid_cases: list[JsonMapping] = []
    runnable_cases: list[tuple[LabelCase, list[str]]] = []
    for case in cases:
        invalid = validate_label_case(case, known_agent_ids)
        if invalid:
            invalid_cases.append({"id": case.case_id, "invalid_expected_agents": invalid})
            if not bool(args.include_invalid_labels):
                continue
        runnable_cases.append((case, invalid))

    prewarm_summary: JsonMapping | None = None
    if bool(args.prewarm_endpoint):
        prewarm_summary = await prewarm_embedding_endpoint(
            list(registry.values()),
            timeout=float(args.prewarm_timeout),
        )

    records: list[JsonDict] = []
    for case, invalid in runnable_cases:
        records.append(
            await run_case(
                case,
                AGENT_METADATA,
                invalid_expected_agents=invalid,
                rarp_scoring_enabled=rarp_scoring_enabled,
                profile_cards=profile_card_result.cards if profile_card_result else None,
                reliability_table=reliability_table,
            )
        )

    out_jsonl = out_dir / str(args.output_jsonl)
    summary_json = out_dir / str(args.summary_json)
    write_jsonl(records, out_jsonl)
    summary = build_run_summary(
        records,
        dataset=dataset,
        invalid_cases=invalid_cases,
        prewarm_summary=prewarm_summary,
        rarp_scoring={
            "enabled": rarp_scoring_enabled,
            "schema_version": "route_reliability_shadow_v0",
            "algorithm": "rarp_v0",
            "profile_cards": profile_card_result.summary() if profile_card_result else {},
            "reliability_table_loaded": bool(reliability_table),
        },
    )
    write_json(summary, summary_json)

    sys.stdout.write(f"case_count: {summary['case_count']}\n")
    sys.stdout.write(f"enabled_count: {summary['enabled_count']}\n")
    sys.stdout.write(f"invalid_case_count: {summary['invalid_case_count']}\n")
    sys.stdout.write(f"runs: {out_jsonl}\n")
    sys.stdout.write(f"summary: {summary_json}\n")

    if invalid_cases and not bool(args.include_invalid_labels):
        sys.stderr.write("invalid expected agents found; pass --include-invalid-labels to keep them\n")
        return 2
    if bool(args.require_enabled) and any(not bool(record.get("enabled", False)) for record in records):
        sys.stderr.write("route-prior retrieval disabled for at least one case\n")
        return 1
    return 0


def main() -> int:
    """Run the RP-1B route-prior validation CLI."""
    return asyncio.run(_run(parse_args()))


if __name__ == "__main__":
    raise SystemExit(main())
