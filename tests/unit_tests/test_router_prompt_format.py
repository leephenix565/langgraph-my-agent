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


def test_fixed_plan_exposes_all_reset_targets_once() -> None:
    plan = build_deterministic_fixed_dag_plan("question")
    assert plan["target_agent_ids"] == list(RESET_RUNTIME_AGENT_IDS)
    assert "sentiment_company_radar" in plan["target_agent_ids"]
    assert plan["target_agent_ids"].count("sentiment_company_radar") == 1
