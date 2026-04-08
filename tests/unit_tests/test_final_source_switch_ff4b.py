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


class _FusionSwitchModel:
    def __init__(self, *, selected_source: str):
        self.selected_source = selected_source

    async def ainvoke(self, msgs, config=None):  # type: ignore[override]
        system_content = ""
        if msgs and isinstance(msgs[0], dict):
            system_content = str(msgs[0].get("content", ""))
        if "You are the Router Agent" in system_content:
            return AIMessage(content=_empty_router_plan_json())
        if "You are the Fair Fusion Judge shadow node." in system_content:
            return AIMessage(
                content=json.dumps(
                    {
                        "decision": self.selected_source,
                        "decision_reason": f"prefer {self.selected_source}",
                        "winner_by_dimension": {
                            "accuracy": "mainline",
                            "coverage": "baseline",
                        },
                        "rewrite_plan": ["Preserve supported facts only."],
                        "accepted_cards": ["m-card", {"title": "b-card", "detail": "baseline evidence"}],
                        "must_keep_facts": ["Fact A"],
                        "must_drop_facts": ["Fact B"],
                        "confidence": 0.71,
                    },
                    ensure_ascii=False,
                )
            )
        if "You are the Fair Fusion Writer shadow node." in system_content:
            return AIMessage(
                content=json.dumps(
                    {
                        "proposed_answer": "writer proposed fused answer",
                        "selected_source": self.selected_source,
                        "accepted_cards": ["m-card", {"title": "b-card", "detail": "baseline evidence"}],
                        "dropped_cards": ["drop-card"],
                        "note": "shadow writer note",
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


async def test_router_resets_ff4b_emitted_bundle(monkeypatch) -> None:
    graph_mod, _baseline_module = _reload_modules(monkeypatch)
    monkeypatch.setattr(graph_mod, "load_chat_model", lambda name: _FusionSwitchModel(selected_source="fused"))

    state = {
        "messages": [HumanMessage(content="hello")],
        "emitted_bundle": {"answer": "stale"},
    }
    runtime = types.SimpleNamespace(context=Context(run_id="ff4b-router-reset"))

    out = await graph_mod.router_node(state, runtime)  # type: ignore[arg-type]

    assert out["emitted_bundle"] == {}


async def test_graph_ff4b_flag_off_keeps_visible_answer_on_mainline(monkeypatch) -> None:
    graph_mod, baseline_module = _reload_modules(monkeypatch)
    fusion_model = _FusionSwitchModel(selected_source="fused")
    monkeypatch.setattr(graph_mod, "load_chat_model", lambda name: fusion_model)
    monkeypatch.setattr(default_agents, "load_chat_model", lambda name: fusion_model)
    monkeypatch.setattr(baseline_module, "load_chat_model", lambda name: _BaselineModel())

    res = await graph_mod.graph.ainvoke(
        {"messages": [("user", "demo question")]},  # type: ignore[arg-type]
        context=Context(
            model="deepseek/deepseek-chat",
            enable_fair_fusion=True,
            enable_fair_fusion_source_switch=False,
            system_prompt="You are a helpful AI assistant.",
        ),
    )

    assert res["writer_output"]["selected_source"] == "fused"
    assert res["final_emit_payload"]["selected_source"] == "mainline"
    assert res["messages"][-1].content == "mainline final answer"
    assert res["final_answer_source"] == "mainline"
    assert res["emitted_bundle"]["answer"] == "mainline final answer"


async def test_graph_ff4b_flag_on_emits_baseline_and_tracks_emitted_bundle(monkeypatch) -> None:
    monkeypatch.setenv("REACT_AGENT_RESULTS_POOLS", "1")
    graph_mod, baseline_module = _reload_modules(monkeypatch)
    fusion_model = _FusionSwitchModel(selected_source="baseline")
    monkeypatch.setattr(graph_mod, "load_chat_model", lambda name: fusion_model)
    monkeypatch.setattr(default_agents, "load_chat_model", lambda name: fusion_model)
    monkeypatch.setattr(baseline_module, "load_chat_model", lambda name: _BaselineModel())

    res = await graph_mod.graph.ainvoke(
        {"messages": [("user", "demo question")]},  # type: ignore[arg-type]
        context=Context(
            model="deepseek/deepseek-chat",
            enable_fair_fusion=True,
            enable_fair_fusion_source_switch=True,
            system_prompt="You are a helpful AI assistant.",
        ),
    )

    assert res["writer_output"]["selected_source"] == "baseline"
    assert res["final_emit_payload"]["selected_source"] == "baseline"
    assert res["messages"][-1].content == "baseline sidecar answer"
    assert res["final_answer_source"] == "baseline"
    assert res["emitted_bundle"]["answer"] == "baseline sidecar answer"
    assert res["emitted_bundle"]["summary_source"] == "baseline_sidecar"
    assert res["multi_agent_bundle"]["answer"] == "mainline final answer"
    assert res["stable_findings"][-1]["final_answer"] == "baseline sidecar answer"
    assert res["stable_findings"][-1]["question"] == "demo question"


async def test_graph_ff4b_flag_on_emits_fused_and_memory_update_follows_final_messages(monkeypatch) -> None:
    monkeypatch.setenv("REACT_AGENT_RESULTS_POOLS", "1")
    monkeypatch.setenv("REACT_AGENT_THREAD_SUMMARY", "1")
    graph_mod, baseline_module = _reload_modules(monkeypatch)
    fusion_model = _FusionSwitchModel(selected_source="fused")
    monkeypatch.setattr(graph_mod, "load_chat_model", lambda name: fusion_model)
    monkeypatch.setattr(default_agents, "load_chat_model", lambda name: fusion_model)
    monkeypatch.setattr(baseline_module, "load_chat_model", lambda name: _BaselineModel())

    res = await graph_mod.graph.ainvoke(
        {"messages": [("user", "demo question")]},  # type: ignore[arg-type]
        context=Context(
            model="deepseek/deepseek-chat",
            enable_fair_fusion=True,
            enable_fair_fusion_source_switch=True,
            system_prompt="You are a helpful AI assistant.",
        ),
    )

    assert res["writer_output"]["selected_source"] == "fused"
    assert res["final_emit_payload"]["selected_source"] == "fused"
    assert res["messages"][-1].content == "writer proposed fused answer"
    assert res["final_answer_source"] == "fused"
    assert res["emitted_bundle"]["answer"] == "writer proposed fused answer"
    assert res["emitted_bundle"]["summary_source"] == "fusion_writer_shadow"
    assert res["emitted_bundle"]["evidence_cards"] == res["writer_output"]["accepted_cards"]
    assert res["stable_findings"][-1]["final_answer"] == "writer proposed fused answer"
    assert "Recent final answer:\nwriter proposed fused answer" in res["thread_summary"]


@pytest.mark.parametrize(
    ("selected_source", "baseline_status", "baseline_bundle", "writer_output"),
    [
        (
            "baseline",
            "ready",
            {"question": "q", "answer": ""},
            {"selected_source": "baseline", "proposed_answer": "writer baseline"},
        ),
        (
            "fused",
            "ready",
            {"question": "q", "answer": "baseline sidecar answer"},
            {"selected_source": "fused", "proposed_answer": ""},
        ),
    ],
)
async def test_build_final_emit_payload_ff4b_falls_back_to_mainline_for_invalid_sources(
    monkeypatch,
    selected_source: str,
    baseline_status: str,
    baseline_bundle: dict,
    writer_output: dict,
) -> None:
    graph_mod, _baseline_module = _reload_modules(monkeypatch)

    state = {
        "current_question": "q",
        "judge_status": "ready",
        "fusion_verdict": {"decision": selected_source, "confidence": 0.8},
        "baseline_status": baseline_status,
        "baseline_bundle": baseline_bundle,
        "writer_status": "ready",
        "writer_output": writer_output,
        "mainline_emit_payload": {
            "response_text": "mainline final answer",
            "layer_done": {"L4": True},
            "filtered_results": {},
            "summary_source": "manager_summary",
        },
        "multi_agent_bundle": {
            "question": "q",
            "answer": "mainline final answer",
            "summary_source": "manager_summary",
        },
    }

    payload = graph_mod._build_final_emit_payload(  # type: ignore[attr-defined]
        state=state,
        mainline_bundle=state["multi_agent_bundle"],
        selected_source="mainline",
        source_switch_enabled=True,
        writer_output=writer_output,
        writer_status="ready",
        fusion_verdict=state["fusion_verdict"],
        judge_status="ready",
    )

    assert payload["selected_source"] == "mainline"
    assert payload["response_text"] == "mainline final answer"
    assert payload["bundle"]["answer"] == "mainline final answer"
