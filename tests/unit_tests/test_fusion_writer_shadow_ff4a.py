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


class _WriterShadowModel:
    def __init__(self, captured=None):
        self.captured = captured if captured is not None else {}
        self.judge_calls = 0
        self.writer_calls = 0

    async def ainvoke(self, msgs, config=None):  # type: ignore[override]
        system_content = ""
        if msgs and isinstance(msgs[0], dict):
            system_content = str(msgs[0].get("content", ""))
        if "You are the Router Agent" in system_content:
            return AIMessage(content=_empty_router_plan_json())
        if "You are the Fair Fusion Judge shadow node." in system_content:
            self.judge_calls += 1
            return AIMessage(
                content=json.dumps(
                    {
                        "decision": "fused",
                        "decision_reason": "Blend the stronger coverage with the safer facts.",
                        "winner_by_dimension": {
                            "accuracy": "mainline",
                            "coverage": "baseline",
                        },
                        "rewrite_plan": ["Use the mainline structure.", "Merge only supported baseline cards."],
                        "accepted_cards": ["m-card", {"title": "b-card", "detail": "baseline evidence"}],
                        "must_keep_facts": ["Fact A"],
                        "must_drop_facts": ["Fact B"],
                        "confidence": 0.73,
                    },
                    ensure_ascii=False,
                )
            )
        if "You are the Fair Fusion Writer shadow node." in system_content:
            self.writer_calls += 1
            self.captured["msgs"] = msgs
            return AIMessage(
                content=json.dumps(
                    {
                        "proposed_answer": "writer proposed fused answer",
                        "selected_source": "fused",
                        "accepted_cards": ["m-card"],
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


async def test_router_resets_ff4a_writer_fields(monkeypatch) -> None:
    graph_mod, _baseline_module = _reload_modules(monkeypatch)
    monkeypatch.setattr(graph_mod, "load_chat_model", lambda name: _WriterShadowModel())

    state = {
        "messages": [HumanMessage(content="hello")],
        "writer_status": "ready",
        "writer_output": {"selected_source": "fused"},
        "final_emit_payload": {"response_text": "stale"},
    }
    runtime = types.SimpleNamespace(context=Context(run_id="ff4a-router-reset"))

    out = await graph_mod.router_node(state, runtime)  # type: ignore[arg-type]

    assert out["writer_status"] == ""
    assert out["writer_output"] == {}
    assert out["final_emit_payload"] == {}


async def test_fusion_writer_shadow_reads_only_verdict_and_bundles(monkeypatch) -> None:
    graph_mod, _baseline_module = _reload_modules(monkeypatch)
    captured = {}
    writer_model = _WriterShadowModel(captured)
    monkeypatch.setattr(graph_mod, "load_chat_model", lambda name: writer_model)

    state = {
        "messages": [HumanMessage(content="SHOULD_NOT_LEAK_MESSAGE")],
        "current_question": "what changed?",
        "fusion_verdict": {
            "decision": "fused",
            "decision_reason": "blend",
            "winner_by_dimension": {"coverage": "baseline"},
            "rewrite_plan": ["merge facts"],
            "accepted_cards": ["m-card"],
            "must_keep_facts": ["Fact A"],
            "must_drop_facts": ["Fact B"],
            "confidence": 0.66,
        },
        "multi_agent_bundle": {
            "question": "what changed?",
            "answer": "mainline final answer",
            "evidence_cards": ["m-card"],
            "summary_source": "manager_summary",
        },
        "baseline_status": "ready",
        "baseline_bundle": {
            "question": "what changed?",
            "answer": "baseline sidecar answer",
            "evidence_cards": ["b-card"],
            "search_meta": {"coverage_note": "baseline"},
        },
        "analyst_results": {"a25_report_center": {"analysis": "SHOULD_NOT_LEAK_RESULTS"}},
        "ephemeral_results": {"a25_report_center": {"analysis": "SHOULD_NOT_LEAK_EPHEMERAL"}},
        "layer_plan": {"L4": ["SHOULD_NOT_LEAK_LAYER_PLAN"]},
        "a25_output": "SHOULD_NOT_LEAK_RAW_A25",
        "messages_window": "SHOULD_NOT_LEAK_MESSAGES",
        "run_id": "ff4a-writer-ready",
    }
    runtime = types.SimpleNamespace(context=Context(run_id="ff4a-writer-ready"))

    out = await graph_mod.fusion_writer_shadow(state, runtime)  # type: ignore[arg-type]

    assert out["writer_status"] == "ready"
    assert out["writer_output"]["selected_source"] == "fused"
    assert out["writer_output"]["proposed_answer"] == "writer proposed fused answer"
    assert out["final_emit_payload"]["selected_source"] == "mainline"
    assert out["final_emit_payload"]["response_text"] == "mainline final answer"
    assert "messages" not in out
    assert "final_answer_source" not in out
    rendered = json.dumps(captured["msgs"], ensure_ascii=False)
    assert "SHOULD_NOT_LEAK_RESULTS" not in rendered
    assert "SHOULD_NOT_LEAK_EPHEMERAL" not in rendered
    assert "SHOULD_NOT_LEAK_LAYER_PLAN" not in rendered
    assert "SHOULD_NOT_LEAK_RAW_A25" not in rendered
    assert "SHOULD_NOT_LEAK_MESSAGE" not in rendered


async def test_routes_after_judge_and_writer_target_source_neutral_emit(monkeypatch) -> None:
    graph_mod, _baseline_module = _reload_modules(monkeypatch)

    assert graph_mod.route_after_fusion_judge({"judge_status": "ready"}) == "fusion_writer_shadow"
    assert (
        graph_mod.route_after_fusion_judge({"judge_status": "ready", "writer_status": "ready"})
        == "final_emit"
    )
    assert graph_mod.route_after_fusion_writer({"writer_status": "ready"}) == "final_emit"


@pytest.mark.parametrize("baseline_status", ["error", "disabled"])
async def test_fusion_writer_shadow_degraded_paths_stay_stable(monkeypatch, baseline_status: str) -> None:
    graph_mod, _baseline_module = _reload_modules(monkeypatch)

    def _should_not_call_model(name):
        raise AssertionError("writer model should not be called for degraded baseline states")

    monkeypatch.setattr(graph_mod, "load_chat_model", _should_not_call_model)

    state = {
        "messages": [HumanMessage(content="q")],
        "current_question": "q",
        "fusion_verdict": {
            "decision": "mainline",
            "decision_reason": "baseline unavailable",
            "winner_by_dimension": {"overall": "mainline"},
            "rewrite_plan": [],
            "accepted_cards": [],
            "must_keep_facts": [],
            "must_drop_facts": [],
            "confidence": 0.4,
        },
        "multi_agent_bundle": {"question": "q", "answer": "mainline final answer", "summary_source": "manager_summary"},
        "baseline_status": baseline_status,
        "baseline_bundle": {} if baseline_status == "disabled" else {"error": "baseline boom"},
        "run_id": f"ff4a-writer-{baseline_status}",
    }
    runtime = types.SimpleNamespace(context=Context(run_id=f"ff4a-writer-{baseline_status}"))

    out = await graph_mod.fusion_writer_shadow(state, runtime)  # type: ignore[arg-type]

    assert out["writer_status"] == "ready"
    assert out["writer_output"]["selected_source"] == "mainline"
    assert baseline_status in out["writer_output"]["note"]
    assert out["final_emit_payload"]["selected_source"] == "mainline"
    assert "messages" not in out
    assert "final_answer_source" not in out


async def test_final_emit_is_source_neutral_seam_but_still_emits_mainline(monkeypatch) -> None:
    monkeypatch.setenv("REACT_AGENT_RESULTS_POOLS", "1")
    monkeypatch.setenv("REACT_AGENT_THREAD_SUMMARY", "1")
    graph_mod, _baseline_module = _reload_modules(monkeypatch)

    state = {
        "current_layer": "L4",
        "current_question": "q",
        "messages": [HumanMessage(content="q")],
        "stable_findings": [],
        "final_emit_payload": {
            "selected_source": "mainline",
            "response_text": "mainline final answer",
            "bundle": {
                "question": "q",
                "answer": "mainline final answer",
                "summary_source": "manager_summary",
                "evidence_cards": ["e1"],
            },
            "summary_source": "manager_summary",
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
        },
        "mainline_emit_payload": {
            "response_text": "stale legacy answer",
            "layer_done": {"L4": False},
            "filtered_results": {},
            "summary_source": "stale",
        },
        "multi_agent_bundle": {
            "question": "q",
            "answer": "mainline final answer",
            "summary_source": "manager_summary",
            "evidence_cards": ["e1"],
        },
        "run_id": "ff4a-final-emit",
    }
    runtime = types.SimpleNamespace(context=Context(run_id="ff4a-final-emit"))

    out = await graph_mod.final_emit(state, runtime)  # type: ignore[arg-type]

    assert out["is_last_step"] is True
    assert out["messages"][0].content == "mainline final answer"
    assert out["final_answer_source"] == "mainline"
    assert out["mainline_status"] == "emitted"
    assert out["layer_done"]["L4"] is True
    assert len(out["stable_findings"]) == 1

    merged_state = {
        **state,
        **out,
        "messages": [HumanMessage(content="q"), out["messages"][0]],
        "current_question": "q",
    }
    memory_out = await graph_mod.memory_update(merged_state, runtime)  # type: ignore[arg-type]
    assert memory_out["thread_summary"]


async def test_graph_ff4a_writer_shadow_keeps_visible_answer_on_mainline(monkeypatch) -> None:
    graph_mod, baseline_module = _reload_modules(monkeypatch)
    fusion_model = _WriterShadowModel()
    monkeypatch.setattr(graph_mod, "load_chat_model", lambda name: fusion_model)
    monkeypatch.setattr(default_agents, "load_chat_model", lambda name: fusion_model)
    monkeypatch.setattr(baseline_module, "load_chat_model", lambda name: _BaselineModel())

    res = await graph_mod.graph.ainvoke(
        {"messages": [("user", "demo question")]},  # type: ignore[arg-type]
        context=Context(
            model="deepseek/deepseek-chat",
            enable_fair_fusion=True,
            system_prompt="You are a helpful AI assistant.",
        ),
    )

    assert res["fusion_verdict"]["decision"] == "fused"
    assert res["fusion_verdict"]["rewrite_plan"]
    assert res["fusion_verdict"]["accepted_cards"]
    assert res["writer_status"] == "ready"
    assert res["writer_output"]["selected_source"] == "fused"
    assert res["final_emit_payload"]["selected_source"] == "mainline"
    assert res["messages"][-1].content == "mainline final answer"
    assert res["final_answer_source"] == "mainline"
    assert "writer_output" not in res.get("analyst_results", {})
    assert "writer_output" not in res.get("ephemeral_results", {})
