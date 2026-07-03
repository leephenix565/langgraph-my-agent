import json

from react_agent.context import Context
from react_agent.fixed_dag_contracts import (
    build_default_fixed_dag_plan,
    build_dimension_results,
    build_l2_conclusions,
    validate_dimension_composite_result,
)
from react_agent.fixed_dag_l3_explanation_synthesizer import (
    build_l3_explanation_prompt,
    synthesize_l3_explanations,
)


class FakeL3ExplanationModel:
    def __init__(self, response: str):
        self.response = response
        self.prompts: list[str] = []

    def invoke(self, prompt: str):
        self.prompts.append(prompt)
        return self.response


def _value_inputs():
    question = "请分析 600519.SH 的估值冲突。"
    plan = build_default_fixed_dag_plan(question, as_of="2026-06-18")
    conclusions = build_l2_conclusions(plan, as_of="2026-06-18")
    for agent_id, stance, confidence, fact in (
        ("value_traditional_valuation", "-0.002", 0.95, "传统估值接近合理价值中枢。"),
        ("value_ml_valuation", "0.024", 0.69, "ML 估值给出小幅上行空间。"),
        ("value_meta_valuation", "-0.27", 0.70, "同业估值显示高估。"),
        ("value_research_synthesis", "0.19", 0.70, "研报共识目标价偏正。"),
    ):
        conclusions[agent_id].update(
            {
                "status": "complete",
                "stance": stance,
                "confidence": confidence,
                "evidence": [
                    {
                        "id": f"{agent_id}-evidence",
                        "fact": fact,
                        "source": "unit_test",
                        "as_of": "2026-06-18",
                        "data_as_of": "2026-06-18",
                    }
                ],
                "provenance": {
                    **conclusions[agent_id]["provenance"],
                    "research_points": [
                        {
                            "claim": fact,
                            "support": "来自单体智能体结构化材料。",
                        }
                    ],
                },
            }
        )
    dimensions = build_dimension_results(conclusions, as_of="2026-06-18")
    return question, conclusions, dimensions


def test_context_llm_l3_explanation_defaults_off_and_env(monkeypatch) -> None:
    monkeypatch.delenv("ENABLE_LLM_L3_EXPLANATION", raising=False)
    monkeypatch.delenv("LLM_L3_EXPLANATION_MODEL", raising=False)

    assert Context().enable_llm_l3_explanation is False
    assert Context().llm_l3_explanation_model == ""

    monkeypatch.setenv("ENABLE_LLM_L3_EXPLANATION", "1")
    monkeypatch.setenv("LLM_L3_EXPLANATION_MODEL", "deepseek/l3-model")
    context = Context()

    assert context.enable_llm_l3_explanation is True
    assert context.llm_l3_explanation_model == "deepseek/l3-model"


def test_build_l3_explanation_prompt_is_public_safe() -> None:
    question, conclusions, dimensions = _value_inputs()
    prompt = build_l3_explanation_prompt(
        question=question,
        l2_conclusions=conclusions,
        dimension_results=dimensions,
    )

    assert "deterministic L3" in prompt
    assert "value_traditional_valuation" in prompt
    assert "不得修改或重算" in prompt
    assert "/v1/agent/invoke" not in prompt
    assert "raw_response" not in prompt.lower()


def test_l3_explanation_adds_research_points_without_overriding_fusion(monkeypatch) -> None:
    question, conclusions, dimensions = _value_inputs()
    before = dict(dimensions["value"])
    fake_model = FakeL3ExplanationModel(
        json.dumps(
            {
                "dimensions": [
                    {
                        "dimension": "value",
                        "research_points": [
                            {
                                "claim": "价值维分歧主要来自同业估值与研报共识的参考系不同。",
                                "support": "传统和 ML 接近合理，元学习偏负，研报偏正。",
                                "interpretation": "L3 应把该冲突写成估值口径差异，而不是简单平均。",
                                "decision_implication": "最终报告应维持中性关注，不给出强买卖信号。",
                                "caveat": "解释层不改变 deterministic L3 加权分和成员权重。",
                            }
                        ],
                        "notes": ["language-only explanation"],
                    }
                ]
            },
            ensure_ascii=False,
        )
    )
    monkeypatch.setattr(
        "react_agent.fixed_dag_l3_explanation_synthesizer.load_chat_model",
        lambda _model: fake_model,
    )

    outcome = synthesize_l3_explanations(
        question=question,
        l2_conclusions=conclusions,
        dimension_results=dimensions,
        context=Context(model="test/l3-model", enable_llm_l3_explanation=True),
    )
    value = outcome["dimension_results"]["value"]
    valid, reason = validate_dimension_composite_result(value)
    rendered = json.dumps(value, ensure_ascii=False).lower()

    assert valid, reason
    assert outcome["used_llm_explanation"] is True
    assert outcome["provider_invoked"] is True
    assert fake_model.prompts
    for field in (
        "stance",
        "confidence",
        "status",
        "contributing_agents",
        "evidence_refs",
    ):
        assert value[field] == before[field]
    assert value["provenance"]["research_points"][0]["claim"].startswith("价值维分歧")
    assert value["provenance"]["llm_explanation"]["language_only"] is True
    assert value["provenance"]["llm_explanation"]["fusion_fields_overridden"] is False
    assert "raw_response" not in rendered
    assert "secret" not in rendered


def test_l3_explanation_missing_credential_short_circuits(monkeypatch) -> None:
    question, conclusions, dimensions = _value_inputs()
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    def fail_load(_model: str):
        raise AssertionError("provider should not load when credentials are missing")

    monkeypatch.setattr(
        "react_agent.fixed_dag_l3_explanation_synthesizer.load_chat_model",
        fail_load,
    )

    outcome = synthesize_l3_explanations(
        question=question,
        l2_conclusions=conclusions,
        dimension_results=dimensions,
        context=Context(
            enable_llm_l3_explanation=True,
            llm_l3_explanation_model="deepseek/deepseek-v4-flash",
        ),
    )

    assert outcome["used_llm_explanation"] is False
    assert outcome["provider_invoked"] is False
    assert outcome["fallback_reason"] == "provider_configuration_missing:missing_credential"
    assert outcome["dimension_results"]["value"] == dimensions["value"]
