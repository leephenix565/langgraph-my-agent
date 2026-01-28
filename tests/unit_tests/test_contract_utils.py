from react_agent.contract_utils import validate_contract


def _build_contract(selected_agents, steps_len=2):
    tasks = []
    for agent_id in selected_agents:
        tasks.append(
            {
                "agent_id": agent_id,
                "task_id": f"task-{agent_id}",
                "objective": f"objective for {agent_id}",
                "steps": [f"step {i+1}" for i in range(steps_len)],
                "agent_can_extend_steps": True,
                "extension_policy": "extend only if needed",
            }
        )
    return {
        "schema_version": "a01_contract_v0",
        "objective": "overall objective",
        "constraints": ["keep aligned with router plan"],
        "selected_agents": selected_agents,
        "tasks": tasks,
        "aggregation": {"strategy": "merge", "handoff_notes": "follow layer order"},
        "budget": {"time_budget": "", "cost_budget": "", "token_budget": ""},
        "output_spec": {"required_sections": ["summary"], "final_answer_format": "bullets"},
    }


def test_validate_contract_steps_bounds() -> None:
    selected_agents = ["a01_cio_orchestrator", "a03_macro_policy"]

    ok, _, _ = validate_contract(_build_contract(selected_agents, steps_len=2), selected_agents)
    assert ok is True

    ok, _, _ = validate_contract(_build_contract(selected_agents, steps_len=6), selected_agents)
    assert ok is True

    ok, reason, _ = validate_contract(_build_contract(selected_agents, steps_len=1), selected_agents)
    assert ok is False
    assert reason == "invalid_steps"

    ok, reason, _ = validate_contract(_build_contract(selected_agents, steps_len=7), selected_agents)
    assert ok is False
    assert reason == "invalid_steps"


def test_validate_contract_requires_a01() -> None:
    selected_agents = ["a03_macro_policy"]
    ok, reason, _ = validate_contract(_build_contract(selected_agents, steps_len=2), selected_agents)
    assert ok is False
    assert reason == "missing_a01"
