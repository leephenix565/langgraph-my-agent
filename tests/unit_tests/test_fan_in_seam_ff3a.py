import importlib
import json
import types

import pytest
from langchain_core.messages import AIMessage, HumanMessage

import react_agent.baseline_sidecar as baseline_sidecar_module
import react_agent.default_agents as default_agents
import react_agent.graph as graph_module
from react_agent.context import Context

pytestmark = pytest.mark.anyio


def _reload_modules():
    baseline_module = importlib.reload(baseline_sidecar_module)
    graph_mod = importlib.reload(graph_module)
    return graph_mod, baseline_module


def _empty_router_plan_json() -> str:
    return json.dumps(
        {
            "layers": [
                {"layer": "L1", "mode": "Chain", "selected": []},
                {"layer": "L2", "mode": "Star", "selected": []},
                {"layer": "L3", "mode": "Star", "selected": []},
                {"layer": "L4", "mode": "Chain", "selected": []},
            ],
            "reason": "test",
        },
        ensure_ascii=False,
    )


class _FakeMainlineModel:
    async def ainvoke(self, msgs, config=None):  # type: ignore[override]
        system_content = ""
        if msgs and isinstance(msgs[0], dict):
            system_content = str(msgs[0].get("content", ""))
        if "You are the Router Agent" in system_content:
            return AIMessage(content=_empty_router_plan_json())
        return AIMessage(content="mainline final answer")


class _BaselineModel:
    async def ainvoke(self, msgs, config=None):  # type: ignore[override]
        return AIMessage(
            content=json.dumps(
                {
                    "answer": "baseline sidecar answer",
                    "key_points": ["bp1"],
                    "evidence_cards": ["be1"],
                    "search_meta": {"coverage_note": "baseline"},
                    "confidence": 0.55,
                },
                ensure_ascii=False,
            )
        )


async def test_router_resets_ff3a_mainline_fields(monkeypatch) -> None:
    graph_mod, _baseline_module = _reload_modules()
    monkeypatch.setattr(graph_mod, "load_chat_model", lambda name: _FakeMainlineModel())

    state = {
        "messages": [HumanMessage(content="hello")],
        "mainline_status": "ready",
        "mainline_emit_payload": {"response_text": "stale"},
        "final_answer_source": "mainline",
        "judge_status": "ready",
        "fusion_verdict": {"decision": "mainline"},
        "multi_agent_bundle": {"answer": "stale bundle"},
        "baseline_status": "ready",
        "baseline_bundle": {"answer": "stale baseline"},
    }
    runtime = types.SimpleNamespace(context=Context(run_id="ff3a-router-reset"))

    out = await graph_mod.router_node(state, runtime)  # type: ignore[arg-type]

    assert out["mainline_status"] == ""
    assert out["mainline_emit_payload"] == {}
    assert out["final_answer_source"] == ""
    assert out["judge_status"] == ""
    assert out["fusion_verdict"] == {}
    assert out["multi_agent_bundle"] == {}
    assert out["baseline_status"] == ""
    assert out["baseline_bundle"] == {}


async def test_manager_summary_stages_mainline_ready_without_setting_last_step(monkeypatch) -> None:
    graph_mod, _baseline_module = _reload_modules()
    monkeypatch.setattr(graph_mod, "load_chat_model", lambda name: _FakeMainlineModel())

    result = {
        "analysis": "from a25",
        "key_points": ["k1"],
        "evidence": ["e1"],
        "confidence": 0.9,
        "parse_ok": True,
    }
    state = {
        "layer_plan": {"L4": ["a25_report_center"]},
        "layer_mode": {"L4": "Chain"},
        "current_layer": "L4",
        "plan": ["a25_report_center"],
        "messages": [],
        "current_question": "q",
        "analyst_results": {"a25_report_center": result},
        "stable_findings": [],
        "run_id": "ff3a-stage-manager",
    }
    runtime = types.SimpleNamespace(
        context=Context(
            run_id="ff3a-stage-manager",
            enable_fair_fusion=True,
            system_prompt="You are a helpful AI assistant.",
        )
    )

    out = await graph_mod.manager_summary(state, runtime)  # type: ignore[arg-type]

    assert out["mainline_status"] == "ready"
    assert out["multi_agent_bundle"]["answer"] == "mainline final answer"
    assert out["mainline_emit_payload"]["response_text"] == "mainline final answer"
    assert out["mainline_emit_payload"]["summary_source"] == "manager_summary"
    assert out["mainline_emit_payload"]["layer_done"]["L4"] is True
    assert "is_last_step" not in out
    assert "messages" not in out


async def test_finalize_summary_stages_mainline_ready_without_setting_last_step(monkeypatch) -> None:
    graph_mod, _baseline_module = _reload_modules()
    monkeypatch.setattr(graph_mod, "load_chat_model", lambda name: _FakeMainlineModel())

    result = {
        "analysis": "from a25",
        "key_points": ["k1"],
        "evidence": ["e1"],
        "confidence": 0.9,
        "parse_ok": True,
    }
    state = {
        "layer_plan": {"L4": ["a25_report_center"]},
        "layer_mode": {"L4": "Chain"},
        "current_layer": "L4",
        "plan": ["a25_report_center"],
        "messages": [],
        "current_question": "q",
        "analyst_results": {"a25_report_center": result},
        "stable_findings": [],
        "run_id": "ff3a-stage-finalize",
    }
    runtime = types.SimpleNamespace(
        context=Context(
            run_id="ff3a-stage-finalize",
            enable_fair_fusion=True,
            system_prompt="You are a helpful AI assistant.",
        )
    )

    out = await graph_mod.finalize_summary(state, runtime)  # type: ignore[arg-type]

    assert out["mainline_status"] == "ready"
    assert out["multi_agent_bundle"]["answer"] == "mainline final answer"
    assert out["mainline_emit_payload"]["summary_source"] == "finalize_summary"
    assert "is_last_step" not in out
    assert "messages" not in out


async def test_route_after_fusion_gate_waits_for_mainline_and_routes_via_shadow_judge(monkeypatch) -> None:
    graph_mod, _baseline_module = _reload_modules()

    assert (
        graph_mod.route_after_fusion_gate(
            {
                "mainline_status": "",
                "baseline_status": "ready",
                "baseline_bundle": {"answer": "baseline"},
            }
        )
        == "__end__"
    )
    assert (
        graph_mod.route_after_fusion_gate(
            {
                "mainline_status": "ready",
                "mainline_emit_payload": {"response_text": "mainline final answer"},
                "multi_agent_bundle": {"answer": "mainline final answer"},
                "baseline_status": "ready",
                "baseline_bundle": {"answer": "baseline"},
            }
        )
        == "fusion_judge_shadow"
    )
    assert (
        graph_mod.route_after_fusion_gate(
            {
                "mainline_status": "ready",
                "mainline_emit_payload": {"response_text": "mainline final answer"},
                "multi_agent_bundle": {"answer": "mainline final answer"},
                "baseline_status": "error",
                "baseline_bundle": {"error": "boom"},
            }
        )
        == "fusion_judge_shadow"
    )
    assert (
        graph_mod.route_after_fusion_gate(
            {
                "mainline_status": "ready",
                "mainline_emit_payload": {"response_text": "mainline final answer"},
                "multi_agent_bundle": {"answer": "mainline final answer"},
                "baseline_status": "disabled",
                "baseline_bundle": {},
            }
        )
        == "fusion_judge_shadow"
    )
    assert (
        graph_mod.route_after_fusion_gate(
            {
                "mainline_status": "ready",
                "mainline_emit_payload": {"response_text": "mainline final answer"},
                "multi_agent_bundle": {"answer": "mainline final answer"},
                "baseline_status": "ready",
                "baseline_bundle": {"answer": "baseline"},
                "judge_status": "ready",
            }
        )
        == "fusion_writer_shadow"
    )
    assert (
        graph_mod.route_after_fusion_gate(
            {
                "mainline_status": "ready",
                "mainline_emit_payload": {"response_text": "mainline final answer"},
                "multi_agent_bundle": {"answer": "mainline final answer"},
                "baseline_status": "ready",
                "baseline_bundle": {"answer": "baseline"},
                "judge_status": "ready",
                "writer_status": "ready",
            }
        )
        == "final_emit"
    )


async def test_mainline_emit_writes_final_answer_source_and_stable_findings(monkeypatch) -> None:
    monkeypatch.setenv("REACT_AGENT_RESULTS_POOLS", "1")
    graph_mod, _baseline_module = _reload_modules()

    state = {
        "current_layer": "L4",
        "current_question": "q",
        "messages": [],
        "stable_findings": [],
        "mainline_status": "ready",
        "mainline_emit_payload": {
            "response_text": "mainline final answer",
            "layer_done": {"L4": True},
            "filtered_results": {
                "a25_report_center": {
                    "analysis": "from a25",
                    "key_points": ["k1"],
                    "evidence": ["e1"],
                    "confidence": 0.9,
                    "parse_ok": True,
                }
            },
            "summary_source": "manager_summary",
        },
        "multi_agent_bundle": {
            "question": "q",
            "answer": "mainline final answer",
            "summary_source": "manager_summary",
            "evidence_cards": ["e1"],
        },
        "run_id": "ff3a-mainline-emit",
    }
    runtime = types.SimpleNamespace(context=Context(run_id="ff3a-mainline-emit"))

    out = await graph_mod.mainline_emit(state, runtime)  # type: ignore[arg-type]

    assert out["is_last_step"] is True
    assert out["messages"][0].content == "mainline final answer"
    assert out["final_answer_source"] == "mainline"
    assert out["mainline_status"] == "emitted"
    assert out["layer_done"]["L4"] is True
    assert len(out["stable_findings"]) == 1


async def test_graph_ff3a_fair_fusion_still_emits_mainline_answer_and_keeps_baseline_outside_results_pools(monkeypatch) -> None:
    monkeypatch.setenv("REACT_AGENT_RESULTS_POOLS", "1")
    graph_mod, baseline_module = _reload_modules()
    monkeypatch.setattr(graph_mod, "load_chat_model", lambda name: _FakeMainlineModel())
    monkeypatch.setattr(default_agents, "load_chat_model", lambda name: _FakeMainlineModel())
    monkeypatch.setattr(baseline_module, "load_chat_model", lambda name: _BaselineModel())

    res = await graph_mod.graph.ainvoke(
        {"messages": [("user", "demo question")]},  # type: ignore[arg-type]
        context=Context(
            model="deepseek/deepseek-chat",
            enable_fair_fusion=True,
            system_prompt="You are a helpful AI assistant.",
        ),
    )

    assert res["messages"][-1].content == "mainline final answer"
    assert res["baseline_bundle"]["answer"] == "baseline sidecar answer"
    assert res["final_answer_source"] == "mainline"
    assert res["mainline_status"] == "emitted"
    assert "baseline_bundle" not in res.get("analyst_results", {})
    assert "baseline_bundle" not in res.get("ephemeral_results", {})
