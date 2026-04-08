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


def _reload_modules(monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "test-key")
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


class _ShadowJudgeMainlineModel:
    def __init__(self, captured=None):
        self.captured = captured
        self.calls = 0

    async def ainvoke(self, msgs, config=None):  # type: ignore[override]
        self.calls += 1
        system_content = ""
        if msgs and isinstance(msgs[0], dict):
            system_content = str(msgs[0].get("content", ""))
        if "You are the Router Agent" in system_content:
            return AIMessage(content=_empty_router_plan_json())
        if "You are the Fair Fusion Judge shadow node." in system_content:
            if self.captured is not None:
                self.captured["msgs"] = msgs
            return AIMessage(
                content=json.dumps(
                    {
                        "decision": "baseline",
                        "decision_reason": "Baseline covered the question better.",
                        "winner_by_dimension": {
                            "coverage": "baseline",
                            "accuracy": "mainline",
                        },
                        "must_keep_facts": ["Fact A"],
                        "must_drop_facts": ["Fact B"],
                        "confidence": 0.74,
                    },
                    ensure_ascii=False,
                )
            )
        return AIMessage(content="mainline final answer")


class _BaselineModel:
    async def ainvoke(self, msgs, config=None):  # type: ignore[override]
        return AIMessage(
            content=json.dumps(
                {
                    "answer": "baseline sidecar answer",
                    "key_points": ["bp1"],
                    "evidence_cards": ["be1"],
                    "search_meta": {"coverage_note": "baseline coverage"},
                    "confidence": 0.61,
                },
                ensure_ascii=False,
            )
        )


async def test_router_resets_ff3b_judge_fields(monkeypatch) -> None:
    graph_mod, _baseline_module = _reload_modules(monkeypatch)
    judge_model = _ShadowJudgeMainlineModel()
    monkeypatch.setattr(graph_mod, "load_chat_model", lambda name: judge_model)

    state = {
        "messages": [HumanMessage(content="hello")],
        "judge_status": "ready",
        "fusion_verdict": {"decision": "baseline"},
    }
    runtime = types.SimpleNamespace(context=Context(run_id="ff3b-router-reset"))

    out = await graph_mod.router_node(state, runtime)  # type: ignore[arg-type]

    assert out["judge_status"] == ""
    assert out["fusion_verdict"] == {}


async def test_fusion_judge_shadow_ready_path_writes_verdict_without_leaking_internal_state(monkeypatch) -> None:
    graph_mod, _baseline_module = _reload_modules(monkeypatch)
    captured = {}
    judge_model = _ShadowJudgeMainlineModel(captured)
    monkeypatch.setattr(graph_mod, "load_chat_model", lambda name: judge_model)

    state = {
        "messages": [HumanMessage(content="what changed?")],
        "current_question": "what changed?",
        "multi_agent_bundle": {
            "question": "what changed?",
            "answer": "mainline final answer",
            "evidence_cards": ["m1"],
            "summary_source": "manager_summary",
        },
        "baseline_status": "ready",
        "baseline_bundle": {
            "question": "what changed?",
            "answer": "baseline sidecar answer",
            "evidence_cards": ["b1"],
            "search_meta": {"coverage_note": "baseline coverage"},
            "confidence": 0.55,
        },
        "analyst_results": {"a25_report_center": {"analysis": "SHOULD_NOT_LEAK_RESULTS"}},
        "ephemeral_results": {"a25_report_center": {"analysis": "SHOULD_NOT_LEAK_EPHEMERAL"}},
        "layer_plan": {"L4": ["SHOULD_NOT_LEAK_LAYER_PLAN"]},
        "a25_output": "SHOULD_NOT_LEAK_RAW_A25",
        "mainline_emit_payload": {"response_text": "SHOULD_NOT_LEAK_EMIT_PAYLOAD"},
        "run_id": "ff3b-shadow-ready",
    }
    runtime = types.SimpleNamespace(context=Context(run_id="ff3b-shadow-ready"))

    out = await graph_mod.fusion_judge_shadow(state, runtime)  # type: ignore[arg-type]

    assert out["judge_status"] == "ready"
    assert out["fusion_verdict"]["decision"] == "baseline"
    assert "messages" not in out
    assert "final_answer_source" not in out
    rendered = json.dumps(captured["msgs"], ensure_ascii=False)
    assert "SHOULD_NOT_LEAK_RESULTS" not in rendered
    assert "SHOULD_NOT_LEAK_EPHEMERAL" not in rendered
    assert "SHOULD_NOT_LEAK_LAYER_PLAN" not in rendered
    assert "SHOULD_NOT_LEAK_RAW_A25" not in rendered
    assert "SHOULD_NOT_LEAK_EMIT_PAYLOAD" not in rendered


async def test_gate_reentry_skips_duplicate_judge_and_routes_to_writer_then_final_emit(monkeypatch) -> None:
    graph_mod, _baseline_module = _reload_modules(monkeypatch)
    judge_model = _ShadowJudgeMainlineModel()
    monkeypatch.setattr(graph_mod, "load_chat_model", lambda name: judge_model)

    state = {
        "mainline_status": "ready",
        "mainline_emit_payload": {"response_text": "mainline final answer"},
        "multi_agent_bundle": {"question": "q", "answer": "mainline final answer"},
        "baseline_status": "ready",
        "baseline_bundle": {"answer": "baseline sidecar answer"},
        "judge_status": "ready",
    }

    assert graph_mod.route_after_fusion_gate(state) == "fusion_writer_shadow"
    assert graph_mod.route_after_fusion_gate({**state, "writer_status": "ready"}) == "final_emit"
    runtime = types.SimpleNamespace(context=Context(run_id="ff3b-reentry"))
    out = await graph_mod.fusion_judge_shadow(state, runtime)  # type: ignore[arg-type]
    assert out == {}
    assert judge_model.calls == 0


@pytest.mark.parametrize("baseline_status", ["error", "disabled"])
async def test_fusion_judge_shadow_degraded_paths_are_stable(monkeypatch, baseline_status: str) -> None:
    graph_mod, _baseline_module = _reload_modules(monkeypatch)

    def _should_not_call_model(name):
        raise AssertionError("judge model should not be called for degraded baseline states")

    monkeypatch.setattr(graph_mod, "load_chat_model", _should_not_call_model)

    state = {
        "messages": [HumanMessage(content="q")],
        "current_question": "q",
        "multi_agent_bundle": {"question": "q", "answer": "mainline final answer"},
        "baseline_status": baseline_status,
        "baseline_bundle": {} if baseline_status == "disabled" else {"error": "baseline boom"},
        "run_id": f"ff3b-degraded-{baseline_status}",
    }
    runtime = types.SimpleNamespace(context=Context(run_id=f"ff3b-degraded-{baseline_status}"))

    out = await graph_mod.fusion_judge_shadow(state, runtime)  # type: ignore[arg-type]

    assert out["judge_status"] == "ready"
    assert out["fusion_verdict"]["decision"] == "mainline"
    assert baseline_status in out["fusion_verdict"]["decision_reason"]


async def test_graph_ff3b_shadow_verdict_does_not_change_final_answer_source(monkeypatch) -> None:
    graph_mod, baseline_module = _reload_modules(monkeypatch)
    judge_model = _ShadowJudgeMainlineModel()
    monkeypatch.setattr(graph_mod, "load_chat_model", lambda name: judge_model)
    monkeypatch.setattr(default_agents, "load_chat_model", lambda name: judge_model)
    monkeypatch.setattr(baseline_module, "load_chat_model", lambda name: _BaselineModel())

    res = await graph_mod.graph.ainvoke(
        {"messages": [("user", "demo question")]},  # type: ignore[arg-type]
        context=Context(
            model="deepseek/deepseek-chat",
            enable_fair_fusion=True,
            system_prompt="You are a helpful AI assistant.",
        ),
    )

    assert res["fusion_verdict"]["decision"] == "baseline"
    assert res["judge_status"] == "ready"
    assert res["messages"][-1].content == "mainline final answer"
    assert res["final_answer_source"] == "mainline"
    assert "fusion_verdict" not in res.get("analyst_results", {})
    assert "fusion_verdict" not in res.get("ephemeral_results", {})
