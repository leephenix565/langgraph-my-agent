from react_agent import prompts
from react_agent.fixed_dag_contracts import FIXED_DAG_STAGE_ORDER


def test_active_router_prompt_has_no_legacy_execution_modes() -> None:
    forbidden = ("Star", "Chain", "Debate", "Tree")
    for token in forbidden:
        assert token not in prompts.ROUTER_SYSTEM_PROMPT


def test_active_router_prompt_mentions_fixed_dag_stages() -> None:
    rendered = prompts.ROUTER_SYSTEM_PROMPT
    for stage in FIXED_DAG_STAGE_ORDER:
        assert stage in rendered
    assert "fixed_dag_plan_v1" in rendered
    assert "mode" not in rendered.lower()
