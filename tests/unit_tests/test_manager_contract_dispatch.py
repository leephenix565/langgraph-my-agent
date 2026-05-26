import types

import anyio

import react_agent.graph as graph_module
from react_agent.context import Context


def _build_contract(selected_agents):
    tasks = []
    for agent_id in selected_agents:
        tasks.append(
            {
                "agent_id": agent_id,
                "task_id": f"task-{agent_id}",
                "objective": f"objective for {agent_id}",
                "steps": [f"step for {agent_id}", f"step followup for {agent_id}"],
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


def test_manager_broadcast_uses_contract_steps() -> None:
    selected_agents = ["a01_cio_orchestrator", "a03_macro_industry_research", "a19_risk_identification"]
    contract = _build_contract(selected_agents)

    state = {
        "layer_plan": {"L1": ["a01_cio_orchestrator"], "L2": ["a03_macro_industry_research", "a19_risk_identification"]},
        "layer_mode": {"L1": "Chain", "L2": "Star"},
        "current_layer": "L2",
        "plan": ["a03_macro_industry_research", "a19_risk_identification"],
        "analyst_results": {
            "a01_cio_orchestrator": {
                "analysis": "ok",
                "key_points": [],
                "evidence": [],
                "confidence": 0.7,
                "parse_ok": True,
                "contract": contract,
            }
        },
        "messages": [],
        "run_id": "test",
    }
    runtime = types.SimpleNamespace(context=Context())

    cmd = anyio.run(graph_module.manager_broadcast, state, runtime)  # type: ignore[arg-type]
    send = cmd.goto[0]
    assignment_text = send.arg["messages"][-1].content  # type: ignore[index]
    assert "合同目标" in assignment_text
    assert "step for a03_macro_industry_research" in assignment_text or "step for a19_risk_identification" in assignment_text


def test_manager_broadcast_fallback_without_valid_contract() -> None:
    selected_agents = ["a01_cio_orchestrator", "a03_macro_industry_research"]
    contract = _build_contract(selected_agents)
    contract["schema_version"] = "invalid_version"

    state = {
        "layer_plan": {"L1": ["a01_cio_orchestrator"], "L2": ["a03_macro_industry_research"]},
        "layer_mode": {"L1": "Chain", "L2": "Star"},
        "current_layer": "L2",
        "plan": ["a03_macro_industry_research"],
        "analyst_results": {
            "a01_cio_orchestrator": {
                "analysis": "ok",
                "key_points": [],
                "evidence": [],
                "confidence": 0.7,
                "parse_ok": True,
                "contract": contract,
            }
        },
        "messages": [],
        "run_id": "test",
    }
    runtime = types.SimpleNamespace(context=Context())

    cmd = anyio.run(graph_module.manager_broadcast, state, runtime)  # type: ignore[arg-type]
    send = cmd.goto[0]
    assignment_text = send.arg["messages"][-1].content  # type: ignore[index]
    assert "本层候选" in assignment_text
