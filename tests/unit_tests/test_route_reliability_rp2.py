from __future__ import annotations

import json
from pathlib import Path

import pytest

from react_agent.agents import AgentMetadata
from react_agent.route_profile_registry import RouteProfileCard
from react_agent.route_reliability import (
    build_route_reliability_shadow,
    cost_penalty_for_level,
    load_reliability_table,
    reliability_stats_for_agent,
    runtime_reliability_config_from_env,
)


def _meta(agent_id: str, *, cost_level: str = "normal") -> AgentMetadata:
    return AgentMetadata(
        id=agent_id,
        name=agent_id,
        description=f"{agent_id} profile",
        capabilities=["analysis"],
        input_type="question",
        latency_level="medium",
        cost_level=cost_level,
        version="v0.2",
        layer="L2",
        team="research",
        role_type="system",
        default_enabled=True,
    )


def test_cold_start_defaults_and_cost_penalty() -> None:
    shadow = build_route_reliability_shadow(
        route_scores=[
            {"agent_id": "a_low", "semantic_similarity_score": 0.9, "wildcard_flag": False},
            {"agent_id": "a_high", "semantic_similarity_score": 0.9, "wildcard_flag": False},
        ],
        metadata_by_id={
            "a_low": _meta("a_low", cost_level="low"),
            "a_high": _meta("a_high", cost_level="high"),
        },
        ordinary_pool=["a_low", "a_high"],
        wildcard_agents=[],
    )

    cards = {card["agent_id"]: card for card in shadow["cards"]}
    assert cards["a_low"]["historical_reliability"] == pytest.approx(0.5)
    assert cards["a_low"]["historical_uncertainty"] == pytest.approx(1.0)
    assert cards["a_low"]["combined_route_score"] == pytest.approx(0.61)
    assert cards["a_high"]["cost_penalty"] == pytest.approx(1.0)
    assert cards["a_high"]["combined_route_score"] == pytest.approx(0.56)
    assert shadow["groups"]["candidate"] == ["a_low", "a_high"]


def test_reliability_table_can_create_strong_priority_and_groups(tmp_path: Path) -> None:
    table_path = tmp_path / "reliability.json"
    table_path.write_text(
        json.dumps(
            {
                "schema_version": "route_reliability_table_v0",
                "global": {
                    "a_strong": {
                        "historical_reliability": 0.9,
                        "historical_uncertainty": 0.1,
                    }
                },
            }
        ),
        encoding="utf-8",
    )

    table = load_reliability_table(table_path)
    shadow = build_route_reliability_shadow(
        route_scores=[
            {"agent_id": "a_strong", "semantic_similarity_score": 0.95, "wildcard_flag": False},
            {"agent_id": "a_wild", "semantic_similarity_score": 0.7, "wildcard_flag": True},
            {"agent_id": "a_hidden", "semantic_similarity_score": 0.1, "wildcard_flag": False},
        ],
        metadata_by_id={
            "a_strong": _meta("a_strong", cost_level="low"),
            "a_wild": _meta("a_wild", cost_level="normal"),
            "a_hidden": _meta("a_hidden", cost_level="high"),
        },
        ordinary_pool=["a_strong", "a_wild", "a_hidden"],
        wildcard_agents=["a_wild"],
        reliability_table=table,
        confidence_band="normal",
    )

    assert shadow["schema_version"] == "route_reliability_shadow_v0"
    assert shadow["algorithm"] == "rarp_v0"
    assert shadow["shadow_only"] is True
    assert shadow["groups"]["strongly_recommended"] == ["a_strong"]
    assert shadow["groups"]["wildcard"] == ["a_wild"]
    assert shadow["groups"]["deprioritized"] == ["a_wild"]
    assert "a_hidden" not in shadow["groups"]["deprioritized"]

    strong = shadow["cards"][0]
    assert strong["agent_id"] == "a_strong"
    assert strong["priority"] == "strong"
    assert strong["score_band"] == "high"
    assert strong["combined_route_score"] == pytest.approx(0.8125)
    assert strong["selection_hint"] == "recommended"


def test_task_type_table_overrides_global_and_smoothing() -> None:
    table = {
        "global": {
            "a1": {
                "historical_reliability": 0.2,
                "historical_uncertainty": 0.9,
            }
        },
        "by_task_type": {
            "macro": {
                "a1": {
                    "trials": 6,
                    "successes": 4,
                }
            }
        },
    }

    stats = reliability_stats_for_agent("a1", table, task_type="macro")

    assert stats.reliability == pytest.approx(0.6)
    assert stats.uncertainty == pytest.approx(1 / 10**0.5)
    assert stats.source == "table_smoothed"


def test_profile_cards_only_mark_presence_without_leaking_text() -> None:
    card = RouteProfileCard(
        schema_version="route_profile_card_v0",
        agent_id="a1",
        positive_examples=("internal example",),
        negative_examples=("internal negative",),
    )
    shadow = build_route_reliability_shadow(
        route_scores=[
            {"agent_id": "a1", "semantic_similarity_score": 0.9, "wildcard_flag": False}
        ],
        metadata_by_id={"a1": _meta("a1", cost_level="low")},
        ordinary_pool=["a1"],
        wildcard_agents=[],
        profile_cards={"a1": card},
    )

    encoded = json.dumps(shadow, ensure_ascii=False).lower()
    assert "profile_card:present" in shadow["cards"][0]["reason_codes"]
    assert "internal example" not in encoded
    assert "internal negative" not in encoded
    assert "profile_text" not in encoded
    assert "embedding" not in encoded


def test_cost_penalty_mapping() -> None:
    assert cost_penalty_for_level("low") == 0.0
    assert cost_penalty_for_level("normal") == 0.5
    assert cost_penalty_for_level("medium") == 0.5
    assert cost_penalty_for_level("high") == 1.0
    assert cost_penalty_for_level("surprise") == 0.5


def test_runtime_reliability_config_is_private_and_default_off() -> None:
    default_config = runtime_reliability_config_from_env({})
    enabled_config = runtime_reliability_config_from_env(
        {
            "ROUTE_PRIOR_RELIABILITY_ENABLED": "1",
            "ROUTE_PRIOR_PROFILE_CARDS_DIR": "config/route_profiles",
            "ROUTE_PRIOR_RELIABILITY_TABLE": "tmp/reliability.json",
            "ROUTE_PRIOR_TRACE_TOP_CARDS": "3",
        }
    )

    assert default_config.enabled is False
    assert default_config.profile_cards_dir == ""
    assert default_config.reliability_table_path == ""
    assert enabled_config.enabled is True
    assert enabled_config.profile_cards_dir == "config/route_profiles"
    assert enabled_config.reliability_table_path == "tmp/reliability.json"
    assert enabled_config.trace_top_cards == 3
