from __future__ import annotations

import json
from pathlib import Path

from react_agent import route_profile_registry as registry_module
from react_agent.agents import AgentMetadata


def _meta(
    agent_id: str,
    *,
    description: str,
    capabilities: list[str],
    input_type: str,
    layer: str,
    team: str,
    cost_level: str = "normal",
    default_enabled: bool = True,
) -> AgentMetadata:
    return AgentMetadata(
        id=agent_id,
        name=agent_id,
        description=description,
        capabilities=capabilities,
        input_type=input_type,
        latency_level="medium",
        cost_level=cost_level,
        version="v0.2",
        layer=layer,
        team=team,
        role_type="system",
        default_enabled=default_enabled,
    )


def _metadata_fixture() -> dict[str, AgentMetadata]:
    return {
        "a01_cio_orchestrator": _meta(
            "a01_cio_orchestrator",
            description="Orchestrator",
            capabilities=["plan"],
            input_type="management",
            layer="L1",
            team="management",
        ),
        "a02_task_router": _meta(
            "a02_task_router",
            description="Reserved router",
            capabilities=["route"],
            input_type="management",
            layer="L1",
            team="management",
            default_enabled=False,
        ),
        "a03_macro_industry_research": _meta(
            "a03_macro_industry_research",
            description="Macro policy analyst.",
            capabilities=["macro", "policy"],
            input_type="macro",
            layer="L2",
            team="research",
        ),
        "a20_compliance_review": _meta(
            "a20_compliance_review",
            description="Regulatory compliance review.",
            capabilities=["compliance"],
            input_type="compliance",
            layer="L3",
            team="compliance",
            cost_level="low",
        ),
        "a25_report_center": _meta(
            "a25_report_center",
            description="Final report writer.",
            capabilities=["report"],
            input_type="report",
            layer="L4",
            team="reporting",
        ),
    }


def _write_card(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_profile_card_loader_applies_valid_card_and_fallbacks(tmp_path: Path) -> None:
    cards_dir = tmp_path / "route_profiles"
    cards_dir.mkdir()
    _write_card(
        cards_dir / "a03_macro_industry_research.json",
        {
            "schema_version": "route_profile_card_v0",
            "agent_id": "a03_macro_industry_research",
            "positive_examples": ["Fed path and policy transmission"],
            "negative_examples": ["single-stock technical chart"],
            "when_to_use": ["macro policy question"],
            "when_not_to_use": ["pure portfolio rebalance"],
            "evidence_expectations": ["central bank statement"],
            "common_misroutes": ["routing every risk question to macro"],
            "routing_keywords": ["Fed", "policy"],
            "risk_tags": ["macro"],
            "profile_version": "rp2-test",
        },
    )

    result = registry_module.load_route_profile_cards(cards_dir, _metadata_fixture())
    registry = registry_module.build_route_profile_registry(
        _metadata_fixture(),
        profile_cards=result.cards,
    )

    assert result.summary()["loaded_agent_ids"] == ["a03_macro_industry_research"]
    assert "positive_examples: Fed path and policy transmission" in registry["a03_macro_industry_research"].profile_text
    assert "profile_version: rp2-test" in registry["a03_macro_industry_research"].profile_text
    assert registry["a20_compliance_review"].profile_text == (
        "description: Regulatory compliance review.\n"
        "capabilities: compliance\n"
        "input_type: compliance\n"
        "team: compliance"
    )


def test_profile_card_loader_ignores_invalid_unknown_and_special_cards(tmp_path: Path) -> None:
    cards_dir = tmp_path / "route_profiles"
    cards_dir.mkdir()
    _write_card(
        cards_dir / "invalid.json",
        {
            "schema_version": "route_profile_card_v0",
            "agent_id": "a03_macro_industry_research",
            "positive_examples": "not-a-list",
        },
    )
    _write_card(
        cards_dir / "unknown.json",
        {
            "schema_version": "route_profile_card_v0",
            "agent_id": "missing_agent",
            "positive_examples": [],
            "negative_examples": [],
            "when_to_use": [],
            "when_not_to_use": [],
            "evidence_expectations": [],
            "common_misroutes": [],
            "routing_keywords": [],
            "risk_tags": [],
        },
    )
    _write_card(
        cards_dir / "a25_report_center.json",
        {
            "schema_version": "route_profile_card_v0",
            "agent_id": "a25_report_center",
            "positive_examples": [],
            "negative_examples": [],
            "when_to_use": [],
            "when_not_to_use": [],
            "evidence_expectations": [],
            "common_misroutes": [],
            "routing_keywords": [],
            "risk_tags": [],
        },
    )

    result = registry_module.load_route_profile_cards(cards_dir, _metadata_fixture())
    registry = registry_module.build_route_profile_registry(
        _metadata_fixture(),
        profile_cards=result.cards,
    )

    assert result.cards == {}
    assert [issue.reason for issue in result.invalid_cards] == [
        "invalid_card:ValueError:must be a list of strings"
    ]
    assert [issue.reason for issue in result.ignored_cards] == [
        "non_ordinary_agent",
        "unknown_agent",
    ]
    assert list(registry) == ["a03_macro_industry_research", "a20_compliance_review"]


def test_profile_card_missing_dir_is_fail_open(tmp_path: Path) -> None:
    result = registry_module.load_route_profile_cards(
        tmp_path / "missing",
        _metadata_fixture(),
    )

    assert result.cards == {}
    assert result.missing_dir is True
    assert result.summary()["loaded_count"] == 0
