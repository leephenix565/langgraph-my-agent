import json

from react_agent.context import Context
from react_agent.fixed_dag_contracts import (
    build_decision_result,
    build_default_fixed_dag_plan,
    build_dimension_results,
    build_l2_conclusions,
    build_report_input_bundle,
    build_report_result,
    validate_report_result,
)
from react_agent.fixed_dag_report_synthesizer import (
    build_llm_report_prompt,
    synthesize_report_result_with_llm,
)


class FakeReportModel:
    def __init__(self, response: str):
        self.response = response
        self.prompts: list[str] = []

    def invoke(self, prompt: str):
        self.prompts.append(prompt)
        return self.response


def _bundle_and_fallback():
    question = "请分析 600519.SH 是否值得关注。"
    plan = build_default_fixed_dag_plan(question, as_of="2026-06-11")
    conclusions = build_l2_conclusions(plan, as_of="2026-06-11")
    conclusions["value_ml_valuation"]["status"] = "complete"
    conclusions["value_ml_valuation"]["stance"] = "cautious_positive"
    conclusions["value_ml_valuation"]["confidence"] = 0.66
    conclusions["value_ml_valuation"]["evidence"] = [
        {
            "id": "value-ml-demo",
            "fact": "估值模型给出偏积极但需复核的结构化信号。",
            "source": "unit_test",
        }
    ]
    dimensions = build_dimension_results(conclusions, as_of="2026-06-11")
    dimensions["risk"]["gate"] = "pass"
    dimensions["risk"]["risk_score"] = 0.28
    decision = build_decision_result(dimensions, as_of="2026-06-11")
    bundle = build_report_input_bundle(
        question=question,
        l2_conclusions=conclusions,
        dimension_results=dimensions,
        decision_result=decision,
    )
    fallback = build_report_result(
        decision,
        question=question,
        report_input_bundle=bundle,
    )
    return question, bundle, fallback


def test_context_llm_report_synthesis_defaults_off_and_env(monkeypatch) -> None:
    monkeypatch.delenv("ENABLE_LLM_REPORT_SYNTHESIS", raising=False)
    monkeypatch.delenv("LLM_REPORT_SYNTHESIS_MODEL", raising=False)

    assert Context().enable_llm_report_synthesis is False
    assert Context().llm_report_synthesis_model == ""

    monkeypatch.setenv("ENABLE_LLM_REPORT_SYNTHESIS", "1")
    monkeypatch.setenv("LLM_REPORT_SYNTHESIS_MODEL", "deepseek/report-model")
    context = Context()

    assert context.enable_llm_report_synthesis is True
    assert context.llm_report_synthesis_model == "deepseek/report-model"


def test_build_llm_report_prompt_uses_public_safe_bundle_only() -> None:
    question, bundle, _fallback = _bundle_and_fallback()
    prompt = build_llm_report_prompt(question=question, report_input_bundle=bundle)

    assert "report_input_bundle_v1" in prompt
    assert "机器学习企业估值" in prompt
    assert "估值模型给出偏积极" in prompt
    assert "raw_response" not in prompt.lower()
    assert "/v1/agent/invoke" not in prompt


def test_synthesize_report_result_with_llm_success(monkeypatch) -> None:
    question, bundle, fallback = _bundle_and_fallback()
    fake_model = FakeReportModel(
        json.dumps(
            {
                "title": "贵州茅台固定 DAG 研判报告",
                "answer": (
                    "估值维度显示偏积极但需要复核；市场维度暂未形成强信号；"
                    "风险综合为 pass，宏观权重维持 value/market 均衡。"
                    "综合研判：可以关注，但应等待更多确认。"
                ),
                "sections": [
                    {
                        "id": "summary",
                        "title": "综合研判",
                        "content": "基于单体智能体和综合智能体输入，当前结论偏审慎关注。",
                    }
                ],
                "evidence_cards": [
                    {
                        "title": "风险门",
                        "note": "风险综合未触发 veto。",
                    }
                ],
                "limitations": ["显式开关下的大模型报告综合，不代表默认生产调用。"],
            },
            ensure_ascii=False,
        )
    )
    monkeypatch.setattr(
        "react_agent.fixed_dag_report_synthesizer.load_chat_model",
        lambda _model: fake_model,
    )

    outcome = synthesize_report_result_with_llm(
        question=question,
        report_input_bundle=bundle,
        fallback_report_result=fallback,
        context=Context(enable_llm_report_synthesis=True),
    )
    report = outcome["report_result"]
    valid, reason = validate_report_result(report)
    payload = json.dumps(report, ensure_ascii=False).lower()

    assert valid, reason
    assert outcome["used_llm_report"] is True
    assert outcome["attempted"] is True
    assert outcome["provider_invoked"] is True
    assert fake_model.prompts
    assert "研判流程报告" in report["answer"]
    assert "综合研判：可以关注" in report["answer"]
    assert "raw_response" not in payload
    assert "http://" not in payload


def test_synthesize_report_result_with_llm_invalid_output_falls_back(monkeypatch) -> None:
    question, bundle, fallback = _bundle_and_fallback()
    fake_model = FakeReportModel("not json raw_response secret traceback")
    monkeypatch.setattr(
        "react_agent.fixed_dag_report_synthesizer.load_chat_model",
        lambda _model: fake_model,
    )

    outcome = synthesize_report_result_with_llm(
        question=question,
        report_input_bundle=bundle,
        fallback_report_result=fallback,
        context=Context(enable_llm_report_synthesis=True),
    )
    rendered = json.dumps(outcome["report_result"], ensure_ascii=False).lower()

    assert outcome["used_llm_report"] is False
    assert outcome["attempted"] is True
    assert outcome["provider_invoked"] is True
    assert "报告生成输入摘要" in outcome["report_result"]["answer"]
    assert "raw_response" not in rendered
    assert "secret" not in rendered
