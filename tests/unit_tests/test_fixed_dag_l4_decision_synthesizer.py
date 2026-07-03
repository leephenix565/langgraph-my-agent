import json
from types import SimpleNamespace

from react_agent.fixed_dag_contracts import build_decision_result, validate_decision_result
from react_agent.fixed_dag_l4_decision_synthesizer import (
    synthesize_decision_result_with_llm,
)


class FakeModel:
    def __init__(self, content: dict[str, object]) -> None:
        self.content = json.dumps(content, ensure_ascii=False)

    def invoke(self, _prompt: str):
        return SimpleNamespace(content=self.content)


def _dimension_results() -> dict[str, dict[str, object]]:
    return {
        "value": {
            "schema": "dimension_composite_result_v1",
            "agent_id": "value_composite",
            "dimension": "value",
            "stance": "0.22",
            "confidence": 0.75,
            "status": "complete",
        },
        "market": {
            "schema": "dimension_composite_result_v1",
            "agent_id": "market_composite",
            "dimension": "market",
            "stance": "-0.48",
            "confidence": 0.68,
            "status": "partial",
        },
        "risk": {
            "schema": "dimension_composite_result_v1",
            "agent_id": "risk_composite",
            "dimension": "risk",
            "stance": "risk_gate",
            "gate": "manual_review",
            "risk_score": 0.42,
            "confidence": 0.71,
            "status": "complete",
        },
        "macro": {
            "schema": "dimension_composite_result_v1",
            "agent_id": "macro_composite",
            "dimension": "macro",
            "stance": "macro_regulator",
            "dimension_weights": {"value": 0.45, "market": 0.55},
            "risk_sensitivity": 0.8,
            "confidence": 0.6,
            "status": "complete",
        },
    }


def test_l4_decision_llm_output_is_guarded_by_risk_manual_review(monkeypatch) -> None:
    monkeypatch.setenv("DEEPSEEK_API_KEY", "not_printed")
    fake_output = {
        "decision": "positive_watch",
        "score": 0.44,
        "target_price_range": {"low": None, "mid": None, "high": None},
        "dimension_views": {
            "value": {"stance": "positive", "confidence": 0.75, "status": "complete"}
        },
        "reasoning_trace": [
            {"stage": "dimension_induction", "summary": "价值偏正，市场偏负。"},
            {"stage": "macro_risk_adjustment", "summary": "宏观更偏重市场信号。"},
            {"stage": "conflict_resolution", "summary": "模型倾向正向观察。"},
        ],
        "confidence": 0.9,
        "status": "complete",
        "as_of": "2026-06-05",
    }
    monkeypatch.setattr(
        "react_agent.fixed_dag_l4_decision_synthesizer.load_chat_model",
        lambda _model: FakeModel(fake_output),
    )
    dimensions = _dimension_results()
    fallback = build_decision_result(dimensions, as_of="2026-06-05")

    outcome = synthesize_decision_result_with_llm(
        question="请分析 600519.SH",
        dimension_results=dimensions,
        fallback_decision_result=fallback,
        context=SimpleNamespace(model="deepseek/deepseek-v4-flash"),
        as_of="2026-06-05",
    )
    decision = outcome["decision_result"]
    valid, reason = validate_decision_result(decision)

    assert valid, reason
    assert outcome["used_llm_decision"] is True
    assert outcome["provider_invoked"] is True
    assert decision["decision"] == "manual_review"
    assert decision["score"] <= 0
    assert decision["confidence"] <= 0.55
    assert decision["status"] == "partial"
    assert any(item["stage"] == "risk_guard" for item in decision["reasoning_trace"])


def test_l4_decision_missing_credential_falls_back_without_provider_call(monkeypatch) -> None:
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr(
        "react_agent.fixed_dag_l4_decision_synthesizer.load_chat_model",
        lambda _model: (_ for _ in ()).throw(AssertionError("provider should not load")),
    )
    dimensions = _dimension_results()
    fallback = build_decision_result(dimensions, as_of="2026-06-05")

    outcome = synthesize_decision_result_with_llm(
        question="请分析 600519.SH",
        dimension_results=dimensions,
        fallback_decision_result=fallback,
        context=SimpleNamespace(model="deepseek/deepseek-v4-flash"),
        as_of="2026-06-05",
    )

    assert outcome["used_llm_decision"] is False
    assert outcome["provider_invoked"] is False
    assert outcome["fallback_reason"] == "provider_configuration_missing:missing_credential"
    assert outcome["decision_result"] == fallback
    assert outcome["provider_config"]["credential_status"] == "missing"


def test_l4_decision_default_reasoning_uses_public_language(monkeypatch) -> None:
    monkeypatch.setenv("DEEPSEEK_API_KEY", "not_printed")
    fake_output = {
        "decision": "positive_watch",
        "score": 0.02,
        "target_price_range": {"low": None, "mid": None, "high": None},
        "dimension_views": {},
        "reasoning_trace": [],
        "confidence": 0.9,
        "status": "complete",
        "as_of": "2026-06-05",
    }
    monkeypatch.setattr(
        "react_agent.fixed_dag_l4_decision_synthesizer.load_chat_model",
        lambda _model: FakeModel(fake_output),
    )
    dimensions = _dimension_results()
    dimensions["risk"]["gate"] = "pass"
    fallback = build_decision_result(dimensions, as_of="2026-06-05")

    outcome = synthesize_decision_result_with_llm(
        question="请分析 600519.SH",
        dimension_results=dimensions,
        fallback_decision_result=fallback,
        context=SimpleNamespace(model="deepseek/deepseek-v4-flash"),
        as_of="2026-06-05",
    )
    decision = outcome["decision_result"]
    rendered_trace = "\n".join(item["summary"] for item in decision["reasoning_trace"])

    assert decision["decision"] == "research_hold"
    assert decision["score"] == 0.02
    assert decision["confidence"] <= 0.65
    assert "stance" not in rendered_trace
    assert "status" not in rendered_trace
    assert "partial" not in rendered_trace
    assert "证据不完整" in rendered_trace
