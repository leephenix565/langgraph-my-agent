from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ops.regression.route_prior.run_route_prior_eval import (
    label_case_from_record,
    validate_label_case,
)
from react_agent.agents import AgentMetadata
from react_agent.route_profile_registry import build_route_profile_registry

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE = (
    REPO_ROOT
    / "ops"
    / "regression"
    / "route_prior"
    / "fixtures"
    / "rp3_manual_gold_20.jsonl"
)
FORBIDDEN_SPECIAL_AGENT_IDS = {
    "a01_cio_orchestrator",
    "a02_task_router",
    "a25_report_center",
}


def _load_records() -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in FIXTURE.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _load_metadata() -> dict[str, AgentMetadata]:
    metadata: dict[str, AgentMetadata] = {}
    for path in sorted((REPO_ROOT / "config" / "agents").glob("agent_*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        meta = AgentMetadata(**payload)
        metadata[meta.id] = meta
    return metadata


def test_rp3_manual_gold_20_fixture_matches_route_eval_schema() -> None:
    records = _load_records()
    metadata = _load_metadata()
    ordinary_ids = set(build_route_profile_registry(metadata).keys())
    layer_by_agent = {
        agent_id: str(meta.layer or "").upper() for agent_id, meta in metadata.items()
    }

    assert len(records) == 20
    assert len({record["id"] for record in records}) == 20

    for record in records:
        assert record["schema_version"] == "route_eval_label_v0"
        assert record["label_source"] == "manual_gold"
        assert record["quality_conclusion_allowed"] is True
        assert record["review_status"] == "reviewed"

        case = label_case_from_record(record)
        must_include = set(case.must_include_agents)
        critical = set(case.critical_agents)
        should_not_include = set(case.should_not_include_agents)
        primary_agent = str(record["primary_agent"])

        assert critical.issubset(must_include)
        assert must_include.isdisjoint(should_not_include)
        assert primary_agent in must_include
        assert validate_label_case(case, ordinary_ids) == []

        label_agent_ids = (
            set(case.must_include_agents)
            | set(case.critical_agents)
            | set(case.nice_to_have_agents)
            | set(case.should_not_include_agents)
            | {primary_agent}
        )
        assert label_agent_ids.isdisjoint(FORBIDDEN_SPECIAL_AGENT_IDS)
        assert label_agent_ids.issubset(ordinary_ids)

        expected_layers = record["expected_layers"]
        assert isinstance(expected_layers, dict)
        for layer, agent_ids in expected_layers.items():
            assert isinstance(agent_ids, list)
            for agent_id in agent_ids:
                assert agent_id in ordinary_ids
                assert layer_by_agent[agent_id] == str(layer).upper()
