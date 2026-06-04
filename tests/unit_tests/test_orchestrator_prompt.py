from react_agent import prompts


def test_orchestrator_prompt_is_fixed_dag_compatibility_alias() -> None:
    assert prompts.ORCHESTRATOR_SYSTEM_PROMPT == prompts.FIXED_DAG_PLANNER_SYSTEM_PROMPT
    assert "a01_contract_v0" not in prompts.ORCHESTRATOR_SYSTEM_PROMPT
