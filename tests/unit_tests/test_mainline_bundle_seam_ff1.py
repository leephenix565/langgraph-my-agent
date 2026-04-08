import importlib
import time
import types

import anyio
from langchain_core.messages import AIMessage

from react_agent.context import Context


def _reload_graph(monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "test-key")
    import react_agent.graph as graph_module

    return importlib.reload(graph_module)


class _FakeSummaryModel:
    async def ainvoke(self, msgs, config=None):  # type: ignore[override]
        return AIMessage(content="final answer text")


def _sample_result():
    return {
        "analysis": "from a25",
        "key_points": ["k1"],
        "evidence": ["e1"],
        "confidence": 0.9,
        "parse_ok": True,
    }


def test_build_mainline_bundle_returns_bundle_and_response(monkeypatch) -> None:
    graph_module = _reload_graph(monkeypatch)
    monkeypatch.setattr(graph_module, "load_chat_model", lambda name: _FakeSummaryModel())

    result = _sample_result()
    state = {
        "layer_plan": {"L4": ["a25_report_center"]},
        "layer_mode": {"L4": "Chain"},
        "current_layer": "L4",
        "messages": [],
        "current_question": "q",
        "stable_findings": [],
        "run_id": "test-run",
    }
    runtime = types.SimpleNamespace(context=Context(run_id="test-run"))
    logger = graph_module.get_run_logger("test-run")

    bundle, response = anyio.run(
        graph_module._build_mainline_bundle,
        state,
        runtime,
        {"a25_report_center": result},
        {"a25_report_center": result},
        0,
        "manager_summary",
        logger,
        "L4",
        time.perf_counter(),
    )

    assert isinstance(response, AIMessage)
    assert bundle["question"] == "q"
    assert bundle["answer"].startswith("final answer text")
    assert bundle["summary_source"] == "manager_summary"
    assert bundle["filtered_out"] == 0
    assert bundle["process_health"]["result_count"] == 1
    assert bundle["process_health"]["a25_present"] is True
    assert bundle["evidence_cards"]
    assert "is_last_step" not in bundle


def test_run_final_summary_adds_multi_agent_bundle(monkeypatch) -> None:
    graph_module = _reload_graph(monkeypatch)
    monkeypatch.setattr(graph_module, "load_chat_model", lambda name: _FakeSummaryModel())

    result = _sample_result()
    state = {
        "layer_plan": {"L4": ["a25_report_center"]},
        "layer_mode": {"L4": "Chain"},
        "current_layer": "L4",
        "messages": [],
        "current_question": "q",
        "layer_done": {"L1": True, "L2": True, "L3": True},
        "stable_findings": [],
        "run_id": "test-run",
    }
    runtime = types.SimpleNamespace(context=Context(run_id="test-run"))

    out = anyio.run(
        graph_module._run_final_summary,
        state,
        runtime,
        {"L1": True, "L2": True, "L3": True, "L4": True},
        {"a25_report_center": result},
        {"a25_report_center": result},
        0,
        "manager_summary",
    )

    assert out["is_last_step"] is True
    assert isinstance(out["messages"][0], AIMessage)
    assert out["multi_agent_bundle"]["question"] == "q"
    assert out["multi_agent_bundle"]["answer"].startswith("final answer text")
    assert out["multi_agent_bundle"]["summary_source"] == "manager_summary"


def test_finalize_summary_preserves_emit_and_stable_findings_with_bundle(monkeypatch) -> None:
    graph_module = _reload_graph(monkeypatch)
    monkeypatch.setenv("REACT_AGENT_RESULTS_POOLS", "1")
    monkeypatch.setattr(graph_module, "load_chat_model", lambda name: _FakeSummaryModel())

    result = _sample_result()
    state = {
        "layer_plan": {"L4": ["a25_report_center"]},
        "layer_mode": {"L4": "Chain"},
        "current_layer": "L4",
        "plan": ["a25_report_center"],
        "ephemeral_results": {"a25_report_center": result},
        "analyst_results": {"a25_report_center": result},
        "messages": [],
        "current_question": "q",
        "layer_done": {"L1": True, "L2": True, "L3": True},
        "stable_findings": [],
        "run_id": "test-run",
    }
    runtime = types.SimpleNamespace(context=Context(run_id="test-run"))

    out = anyio.run(graph_module.finalize_summary, state, runtime)  # type: ignore[arg-type]

    assert out["is_last_step"] is True
    assert isinstance(out["messages"][0], AIMessage)
    assert out["layer_done"]["L4"] is True
    assert out["multi_agent_bundle"]["summary_source"] == "finalize_summary"
    assert out["multi_agent_bundle"]["process_health"]["filtered_out"] == 0
    assert out["multi_agent_bundle"]["process_health"]["result_count"] == 1
    assert len(out["stable_findings"]) == 1
