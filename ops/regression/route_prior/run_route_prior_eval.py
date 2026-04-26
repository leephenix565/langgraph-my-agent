#!/usr/bin/env python
"""Run RP-1B offline route-prior validation against labeled questions."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

import httpx

JsonDict = dict[str, Any]
JsonMapping = Mapping[str, Any]


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
    """Represent one labeled RP-1B route-prior validation case."""

    case_id: str
    question: str
    expected_agents: list[str]
    tags: list[str]
    label_source: str
    formal_router_selected: list[str] | None = None
    notes: str = ""


def _as_str_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str) and item]


def _required_str(payload: JsonMapping, key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Label case missing required string field: {key}")
    return value.strip()


def label_case_from_record(payload: JsonMapping) -> LabelCase:
    """Build a LabelCase from one JSON object."""
    expected_agents = _as_str_list(payload.get("expected_agents"))
    if not expected_agents:
        raise ValueError("Label case expected_agents must be a non-empty list[str]")
    formal_router_selected: list[str] | None = None
    if "formal_router_selected" in payload:
        formal_router_selected = _as_str_list(payload.get("formal_router_selected"))
    notes = payload.get("notes")
    return LabelCase(
        case_id=_required_str(payload, "id"),
        question=_required_str(payload, "question"),
        expected_agents=expected_agents,
        tags=_as_str_list(payload.get("tags")),
        label_source=_required_str(payload, "label_source"),
        formal_router_selected=formal_router_selected,
        notes=notes if isinstance(notes, str) else "",
    )


def load_label_cases(path: Path) -> list[LabelCase]:
    """Load labeled RP-1B cases from JSONL."""
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
    """Return expected agent ids that are not present in known metadata."""
    return [agent_id for agent_id in case.expected_agents if agent_id not in known_agent_ids]


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


def _score_top10(route_scores: object) -> list[JsonDict]:
    if not isinstance(route_scores, list):
        return []
    items: list[JsonDict] = []
    for raw_item in route_scores[:10]:
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


async def run_case(
    case: LabelCase,
    metadata_by_id: Mapping[str, Any],
    *,
    invalid_expected_agents: list[str],
) -> JsonDict:
    """Run one labeled case through the RP-1A shadow helper."""
    from react_agent import route_prior

    try:
        shadow = await route_prior.compute_route_prior_shadow(case.question, metadata_by_id)
        route_scores_top10 = _score_top10(shadow.get("route_scores"))
        record: JsonDict = {
            "id": case.case_id,
            "question": case.question,
            "expected_agents": case.expected_agents,
            "label_source": case.label_source,
            "tags": case.tags,
            "enabled": bool(shadow.get("enabled", False)),
            "retrieval_reason": str(shadow.get("retrieval_reason", "") or ""),
            "confidence_band": _shadow_confidence_band(shadow),
            "low_confidence_fallback": bool(shadow.get("low_confidence_fallback", False)),
            "ordinary_pool_size": len(_as_str_list(shadow.get("ordinary_pool"))),
            "shortlist_size": len(_as_str_list(shadow.get("awake_agents"))),
            "awake_agents": _as_str_list(shadow.get("awake_agents")),
            "top_ranked_ids": [
                str(item.get("agent_id", "") or "") for item in route_scores_top10 if item.get("agent_id")
            ],
            "route_scores_top10": route_scores_top10,
            "wildcard_agents": _as_str_list(shadow.get("wildcard_agents")),
            "cache_hits": int(shadow.get("cache_hits", 0) or 0),
            "cache_misses": int(shadow.get("cache_misses", 0) or 0),
            "invalid_expected_agents": invalid_expected_agents,
            "reason_codes": _shadow_reason_codes(shadow),
            "error": "",
        }
    except Exception as exc:
        record = {
            "id": case.case_id,
            "question": case.question,
            "expected_agents": case.expected_agents,
            "label_source": case.label_source,
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
            "wildcard_agents": [],
            "cache_hits": 0,
            "cache_misses": 0,
            "invalid_expected_agents": invalid_expected_agents,
            "reason_codes": [],
            "error": f"{type(exc).__name__}: {exc}",
        }
    if case.formal_router_selected is not None:
        record["formal_router_selected"] = case.formal_router_selected
    return record


def write_jsonl(records: Sequence[JsonMapping], path: Path) -> None:
    """Write RP-1B run records as JSONL."""
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
) -> JsonDict:
    """Build a compact summary for one RP-1B run."""
    return {
        "meta": {
            "phase": "RP-1B",
            "scope": "offline_shadow_validation",
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
    }


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Run RP-1B offline route-prior validation.")
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
    return parser.parse_args()


async def _run(args: argparse.Namespace) -> int:
    from react_agent.agents import (  # type: ignore[import-not-found]
        AGENT_METADATA,
        load_metadata_from_dir,
    )
    from react_agent.route_profile_registry import (  # type: ignore[import-not-found]
        build_route_profile_registry,
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
        records.append(await run_case(case, AGENT_METADATA, invalid_expected_agents=invalid))

    out_jsonl = out_dir / str(args.output_jsonl)
    summary_json = out_dir / str(args.summary_json)
    write_jsonl(records, out_jsonl)
    summary = build_run_summary(
        records,
        dataset=dataset,
        invalid_cases=invalid_cases,
        prewarm_summary=prewarm_summary,
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
