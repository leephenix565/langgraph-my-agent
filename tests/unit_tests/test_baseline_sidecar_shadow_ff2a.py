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
        return AIMessage(content="final answer text")


class _CaptureBaselineModel:
    def __init__(self, captured):
        self.captured = captured

    async def ainvoke(self, msgs, config=None):  # type: ignore[override]
        self.captured["msgs"] = msgs
        return AIMessage(
            content=json.dumps(
                {
                    "answer": "baseline answer",
                    "key_points": ["bp1"],
                    "evidence_cards": ["ev1"],
                    "search_meta": {
                        "force_search_requested": True,
                        "retrieved_at_utc": "2026-04-02T00:00:00+00:00",
                        "coverage_note": "baseline coverage",
                    },
                    "confidence": 0.61,
                },
                ensure_ascii=False,
            )
        )


class _ErrorBaselineModel:
    async def ainvoke(self, msgs, config=None):  # type: ignore[override]
        raise RuntimeError("baseline boom")


async def test_graph_flag_off_keeps_final_output_and_marks_baseline_disabled(monkeypatch) -> None:
    graph_mod, baseline_module = _reload_modules()
    monkeypatch.setattr(graph_mod, "load_chat_model", lambda name: _FakeMainlineModel())
    monkeypatch.setattr(default_agents, "load_chat_model", lambda name: _FakeMainlineModel())

    class _ShouldNotBeCalled:
        async def ainvoke(self, msgs, config=None):  # type: ignore[override]
            raise AssertionError("baseline model should not be called when fair fusion is disabled")

    monkeypatch.setattr(baseline_module, "load_chat_model", lambda name: _ShouldNotBeCalled())

    res = await graph_mod.graph.ainvoke(
        {"messages": [("user", "demo question")]},  # type: ignore[arg-type]
        context=Context(model="deepseek/deepseek-chat", enable_fair_fusion=False, system_prompt="You are a helpful AI assistant."),
    )

    assert res["messages"][-1].content == "final answer text"
    assert res["baseline_status"] == "disabled"
    assert res["baseline_bundle"] == {}


async def test_baseline_sidecar_success_is_isolated_and_does_not_leak_mainline_inputs(monkeypatch) -> None:
    _graph_mod, baseline_module = _reload_modules()
    captured = {}
    monkeypatch.setattr(baseline_module, "load_chat_model", lambda name: _CaptureBaselineModel(captured))

    state = {
        "messages": [HumanMessage(content="what is the baseline outlook?")],
        "current_question": "what is the baseline outlook?",
        "thread_summary": "recent thread summary",
        "stable_findings": [],
        "layer_plan": {"L1": ["SHOULD_NOT_LEAK_LAYER_PLAN"]},
        "analyst_results": {"a25_report_center": {"analysis": "SHOULD_NOT_LEAK_RESULTS"}},
        "ephemeral_results": {"a25_report_center": {"analysis": "SHOULD_NOT_LEAK_EPHEMERAL"}},
        "multi_agent_bundle": {"answer": "SHOULD_NOT_LEAK_MAINLINE_BUNDLE"},
        "a25_output": "SHOULD_NOT_LEAK_A25_OUTPUT",
    }
    runtime = types.SimpleNamespace(
        context=Context(
            enable_fair_fusion=True,
            baseline_force_search=True,
            run_id="baseline-test",
        )
    )

    out = await baseline_module.run_baseline_sidecar(state, runtime)  # type: ignore[arg-type]

    assert out["baseline_status"] == "ready"
    assert "analyst_results" not in out
    assert "ephemeral_results" not in out
    assert out["baseline_bundle"]["question"] == "what is the baseline outlook?"
    assert out["baseline_bundle"]["answer"] == "baseline answer"
    assert out["baseline_bundle"]["search_meta"]["force_search_requested"] is True
    rendered = json.dumps(captured["msgs"], ensure_ascii=False)
    assert "SHOULD_NOT_LEAK_LAYER_PLAN" not in rendered
    assert "SHOULD_NOT_LEAK_RESULTS" not in rendered
    assert "SHOULD_NOT_LEAK_EPHEMERAL" not in rendered
    assert "SHOULD_NOT_LEAK_MAINLINE_BUNDLE" not in rendered
    assert "SHOULD_NOT_LEAK_A25_OUTPUT" not in rendered


async def test_router_resets_ff2a_sidecar_fields(monkeypatch) -> None:
    graph_mod, _baseline_module = _reload_modules()
    monkeypatch.setattr(graph_mod, "load_chat_model", lambda name: _FakeMainlineModel())

    state = {
        "messages": [HumanMessage(content="hello")],
        "multi_agent_bundle": {"answer": "stale"},
        "baseline_status": "ready",
        "baseline_bundle": {"answer": "stale baseline"},
    }
    runtime = types.SimpleNamespace(context=Context(run_id="router-reset"))

    out = await graph_mod.router_node(state, runtime)  # type: ignore[arg-type]

    assert out["multi_agent_bundle"] == {}
    assert out["baseline_status"] == ""
    assert out["baseline_bundle"] == {}


async def test_graph_flag_on_writes_baseline_bundle_without_changing_final_output(monkeypatch) -> None:
    graph_mod, baseline_module = _reload_modules()
    monkeypatch.setattr(graph_mod, "load_chat_model", lambda name: _FakeMainlineModel())
    monkeypatch.setattr(default_agents, "load_chat_model", lambda name: _FakeMainlineModel())
    monkeypatch.setattr(baseline_module, "load_chat_model", lambda name: _CaptureBaselineModel({}))

    res = await graph_mod.graph.ainvoke(
        {"messages": [("user", "demo question")]},  # type: ignore[arg-type]
        context=Context(model="deepseek/deepseek-chat", enable_fair_fusion=True, system_prompt="You are a helpful AI assistant."),
    )

    assert res["messages"][-1].content == "final answer text"
    assert res["baseline_status"] == "ready"
    assert res["baseline_bundle"]["answer"] == "baseline answer"
    assert res["baseline_bundle"]["search_meta"]["force_search_requested"] is True


async def test_graph_still_completes_when_baseline_sidecar_errors(monkeypatch) -> None:
    graph_mod, baseline_module = _reload_modules()
    monkeypatch.setattr(graph_mod, "load_chat_model", lambda name: _FakeMainlineModel())
    monkeypatch.setattr(default_agents, "load_chat_model", lambda name: _FakeMainlineModel())
    monkeypatch.setattr(baseline_module, "load_chat_model", lambda name: _ErrorBaselineModel())

    res = await graph_mod.graph.ainvoke(
        {"messages": [("user", "demo question")]},  # type: ignore[arg-type]
        context=Context(model="deepseek/deepseek-chat", enable_fair_fusion=True, system_prompt="You are a helpful AI assistant."),
    )

    assert res["messages"][-1].content == "final answer text"
    assert res["baseline_status"] == "error"
    assert "error" in res["baseline_bundle"]
