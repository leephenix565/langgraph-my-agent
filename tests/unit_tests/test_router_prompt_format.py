from react_agent import prompts
from react_agent.fixed_dag_contracts import (
    RESET_RUNTIME_AGENT_IDS,
    build_deterministic_fixed_dag_plan,
)


def test_router_prompt_format_has_no_dynamic_placeholders() -> None:
    rendered = prompts.ROUTER_SYSTEM_PROMPT
    assert "{system_time}" not in rendered
    assert "{agent_catalog}" not in rendered
    assert "fixed_dag_plan_v1" in rendered


def test_router_prompt_does_not_restore_broad_or_mode_logic() -> None:
    rendered = prompts.ROUTER_SYSTEM_PROMPT
    forbidden = [
        "first 5",
        "first five",
        "a02_task_router",
        "baseline",
        "fusion",
        "manager assignment",
        "Star",
        "Chain",
        "Debate",
        "Tree",
    ]
    for text in forbidden:
        assert text not in rendered


def test_route_intent_prompt_is_separate_provider_free_contract() -> None:
    rendered = prompts.build_route_intent_prompt(
        "Should I evaluate example company?",
        catalog_summary={
            "allowed_agents": ["value_research_synthesis", "risk_identification"],
            "dimensions": {
                "value": ["value_research_synthesis"],
                "risk": ["risk_identification"],
            },
        },
    )

    assert "route_intent_v1" in rendered
    assert "selected_dimensions" in rendered
    assert "selected_agents" in rendered
    assert "dag_steps" in rendered
    assert "depends_on" in rendered
    assert "Do not emit dag_steps" in rendered
    assert "Do not claim that a provider" in rendered
    assert "value_research_synthesis" in rendered
    assert "risk_identification" in rendered
    assert "old numbered ids" in rendered
    assert "route-mode dispatch labels" in rendered


def test_active_router_prompt_remains_full_dag_plan_prompt() -> None:
    assert prompts.ROUTER_SYSTEM_PROMPT == prompts.FIXED_DAG_PLANNER_SYSTEM_PROMPT
    assert prompts.ROUTER_SYSTEM_PROMPT != prompts.FIXED_DAG_ROUTE_INTENT_SYSTEM_PROMPT
    assert "route_intent_v1" not in prompts.ROUTER_SYSTEM_PROMPT
    assert "fixed_dag_plan_v1" in prompts.ROUTER_SYSTEM_PROMPT


def test_fixed_plan_exposes_all_reset_targets_once() -> None:
    plan = build_deterministic_fixed_dag_plan("question")
    assert plan["target_agent_ids"] == list(RESET_RUNTIME_AGENT_IDS)
    assert "sentiment_company_radar" in plan["target_agent_ids"]
    assert plan["target_agent_ids"].count("sentiment_company_radar") == 1
