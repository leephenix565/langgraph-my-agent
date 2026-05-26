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
            description="Orchestrates the layered workflow.",
            capabilities=["orchestrate", "plan"],
            input_type="management",
            layer="L1",
            team="management",
        ),
        "a02_task_router": _meta(
            "a02_task_router",
            description="Reserved task router.",
            capabilities=["route", "plan"],
            input_type="management",
            layer="L1",
            team="management",
            default_enabled=False,
        ),
        "a03_macro_industry_research": _meta(
            "a03_macro_industry_research",
            description="Macro policy analyst for top-down market questions.",
            capabilities=["macro", "policy", "liquidity"],
            input_type="macro",
            layer="L2",
            team="research",
        ),
        "a15_entity_relation_extraction": _meta(
            "a15_entity_relation_extraction",
            description="Cross-domain synthesis and consensus ranking.",
            capabilities=["synthesis", "scenario", "narrative"],
            input_type="research",
            layer="L2",
            team="research",
        ),
        "a20_compliance_review": _meta(
            "a20_compliance_review",
            description="Regulatory and compliance rule review.",
            capabilities=["compliance", "regulatory", "policy"],
            input_type="compliance",
            layer="L3",
            team="compliance",
            cost_level="low",
        ),
        "a25_report_center": _meta(
            "a25_report_center",
            description="Final answer writer.",
            capabilities=["report", "synthesis"],
            input_type="report",
            layer="L4",
            team="reporting",
        ),
    }


def test_route_profile_registry_filters_ordinary_pool_and_derives_profile_text() -> None:
    registry = registry_module.build_route_profile_registry(_metadata_fixture())

    assert list(registry.keys()) == [
        "a03_macro_industry_research",
        "a15_entity_relation_extraction",
        "a20_compliance_review",
    ]
    assert registry_module.ordinary_pool_ids(_metadata_fixture()) == [
        "a03_macro_industry_research",
        "a15_entity_relation_extraction",
        "a20_compliance_review",
    ]

    a03 = registry["a03_macro_industry_research"]
    assert a03.wildcard is False
    assert a03.cost_tier == "normal"
    assert (
        a03.profile_text
        == "description: Macro policy analyst for top-down market questions.\n"
        "capabilities: macro, policy, liquidity\n"
        "input_type: macro\n"
        "team: research"
    )

    a15 = registry["a15_entity_relation_extraction"]
    assert a15.wildcard is True
    assert a15.layer == "L2"
    assert a15.team == "research"

    a21 = registry["a20_compliance_review"]
    assert a21.cost_tier == "low"


def test_profile_text_override_wins_over_derived_text(monkeypatch) -> None:
    monkeypatch.setitem(
        registry_module._REGISTRY_OVERRIDES,  # type: ignore[attr-defined]
        "a03_macro_industry_research",
        {
            "wildcard": False,
            "profile_text_override": "override: macro policy shadow profile",
        },
    )
    registry = registry_module.build_route_profile_registry(_metadata_fixture())
    assert registry["a03_macro_industry_research"].profile_text == "override: macro policy shadow profile"
