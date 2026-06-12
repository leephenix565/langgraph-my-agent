import json
from pathlib import Path
from types import SimpleNamespace

from react_agent.context import Context
from react_agent.fixed_dag_contracts import (
    build_agent_task,
    build_default_fixed_dag_plan,
    build_route_intent,
    compile_selected_fixed_dag_plan,
    validate_conclusion_object,
)
from react_agent.fixed_dag_llm_placeholders import (
    INTERNAL_LLM_PLACEHOLDER_SOURCE,
    build_l2_conclusions_with_internal_placeholders,
    build_l2_placeholder_prompt,
    parse_l2_placeholder_response,
)


class FakeModel:
    def __init__(self, response: str) -> None:
        self.response = response
        self.prompts: list[str] = []

    def invoke(self, prompt: str):
        self.prompts.append(prompt)
        return SimpleNamespace(content=self.response)


def _json_response(**overrides) -> str:
    payload = {
        "analysis": "该功能位可先从业务框架、缺失数据和风险边界做非结论性梳理。",
        "key_points": ["需要补齐正式业务 agent 的结构化证据。"],
        "evidence": [{"fact": "当前仅为主系统内部占位观察。"}],
        "confidence": 0.31,
    }
    payload.update(overrides)
    return json.dumps(payload, ensure_ascii=False)


def test_context_internal_llm_placeholder_flag_defaults_off_and_env_can_enable(monkeypatch) -> None:
    monkeypatch.delenv("ENABLE_INTERNAL_LLM_PLACEHOLDERS", raising=False)
    assert Context().enable_internal_llm_placeholders is False

    monkeypatch.setenv("ENABLE_INTERNAL_LLM_PLACEHOLDERS", "1")
    assert Context().enable_internal_llm_placeholders is True


def test_internal_llm_placeholder_success_builds_safe_partial_conclusion(monkeypatch) -> None:
    fake_model = FakeModel(_json_response(confidence=0.99))
    monkeypatch.setattr(
        "react_agent.fixed_dag_llm_placeholders.load_chat_model",
        lambda _model: fake_model,
    )

    plan = build_default_fixed_dag_plan("分析公司舆情", as_of="2026-06-09")
    conclusions = build_l2_conclusions_with_internal_placeholders(
        plan,
        question="分析公司舆情",
        as_of="2026-06-09",
        context=Context(enable_internal_llm_placeholders=True),
    )
    conclusion = conclusions["sentiment_company_radar"]
    valid, reason = validate_conclusion_object(conclusion)

    assert valid, reason
    assert fake_model.prompts
    assert conclusion["status"] == "partial"
    assert conclusion["stance"] == "placeholder_neutral"
    assert conclusion["confidence"] <= 0.4
    assert conclusion["provenance"]["source"] == INTERNAL_LLM_PLACEHOLDER_SOURCE
    assert conclusion["provenance"]["runtime_path"] == INTERNAL_LLM_PLACEHOLDER_SOURCE
    assert conclusion["provenance"]["provider_invoked"] is True
    assert conclusion["provenance"]["external_invoked"] is False
    assert conclusion["provenance"]["deployed_but_deferred"] is True
    assert conclusion["output_routes"] == ["market_composite"]
    assert "真实外部专属智能体" in fake_model.prompts[0]


def test_internal_llm_placeholder_prompt_includes_agent_task_contract() -> None:
    task = build_agent_task(
        "value_ml_valuation",
        question="请分析贵州茅台 600519.SH",
        as_of="2026-06-09",
        data_bundle={"schema": "data_bundle_v1", "target": "600519.SH"},
        entity_relation_bundle={"schema": "entity_relation_bundle_v1"},
    )

    prompt = build_l2_placeholder_prompt(
        question="请分析贵州茅台 600519.SH",
        agent_id="value_ml_valuation",
        dimension="value",
        agent_label="机器学习企业估值",
        plan=build_default_fixed_dag_plan("请分析贵州茅台", as_of="2026-06-09"),
        as_of="2026-06-09",
        agent_task=task,
    )

    assert "agent_task_present: true" in prompt
    assert "agent_task_schema: agent_task_v1" in prompt
    assert "required_output_schema: agent_conclusion_v1" in prompt
    assert "has_l1_data_bundle: True" in prompt
    assert "机器学习企业估值智能体" in prompt


def test_provider_missing_falls_back_to_deterministic_pending_without_raw_leakage(monkeypatch) -> None:
    def fail_load(_model: str):
        raise ValueError("api key missing: SECRET traceback endpoint raw_response")

    monkeypatch.setattr("react_agent.fixed_dag_llm_placeholders.load_chat_model", fail_load)

    conclusions = build_l2_conclusions_with_internal_placeholders(
        build_default_fixed_dag_plan("q", as_of="2026-06-09"),
        question="q",
        as_of="2026-06-09",
        context=Context(enable_internal_llm_placeholders=True),
    )
    conclusion = conclusions["value_research_synthesis"]
    valid, reason = validate_conclusion_object(conclusion)
    payload = json.dumps(conclusion, ensure_ascii=False).lower()

    assert valid, reason
    assert conclusion["status"] == "pending_implementation"
    assert conclusion["provenance"]["provider_invoked"] is False
    assert conclusion["provenance"]["external_invoked"] is False
    assert conclusion["provenance"]["internal_llm_placeholder_fallback"] is True
    assert conclusion["provenance"]["fallback_reason"] == "provider_configuration_missing"
    for forbidden in ("api_key", "secret", "traceback", "endpoint", "raw_response", "chain-of-thought"):
        assert forbidden not in payload


def test_parse_failure_falls_back_without_storing_raw_model_text(monkeypatch) -> None:
    fake_model = FakeModel("not json raw_response secret traceback endpoint")
    monkeypatch.setattr(
        "react_agent.fixed_dag_llm_placeholders.load_chat_model",
        lambda _model: fake_model,
    )

    conclusions = build_l2_conclusions_with_internal_placeholders(
        build_default_fixed_dag_plan("q", as_of="2026-06-09"),
        question="q",
        as_of="2026-06-09",
        context=Context(enable_internal_llm_placeholders=True),
    )
    payload = json.dumps(conclusions["macro_analysis"], ensure_ascii=False).lower()

    assert conclusions["macro_analysis"]["status"] == "pending_implementation"
    assert conclusions["macro_analysis"]["provenance"]["fallback_reason"] == "parse_failed"
    for forbidden in ("secret", "traceback", "endpoint", "raw_response", "chain-of-thought"):
        assert forbidden not in payload


def test_selected_plan_only_generates_selected_l2_placeholder(monkeypatch) -> None:
    fake_model = FakeModel(_json_response())
    monkeypatch.setattr(
        "react_agent.fixed_dag_llm_placeholders.load_chat_model",
        lambda _model: fake_model,
    )
    plan = compile_selected_fixed_dag_plan(
        build_route_intent(
            task_type="general",
            selected_dimensions=["value"],
            selected_agents=["value_ml_valuation"],
            fallback_reason="fallback to full DAG",
        ),
        user_text="q",
        as_of="2026-06-09",
    )

    conclusions = build_l2_conclusions_with_internal_placeholders(
        plan,
        question="q",
        as_of="2026-06-09",
        context=Context(enable_internal_llm_placeholders=True),
    )

    assert set(conclusions) == {"value_ml_valuation"}
    assert conclusions["value_ml_valuation"]["status"] == "partial"
    assert len(fake_model.prompts) == 1


def test_parser_sanitizes_unsafe_text_fields() -> None:
    parsed = parse_l2_placeholder_response(
        _json_response(
            analysis="contains api_key and endpoint",
            key_points=["safe", "raw_response should not persist"],
            evidence=[{"fact": "traceback should not persist"}],
        )
    )
    payload = json.dumps(parsed, ensure_ascii=False).lower()

    for forbidden in ("api_key", "endpoint", "raw_response", "traceback", "chain-of-thought"):
        assert forbidden not in payload


def test_docs_record_deployed_but_deferred_boundary() -> None:
    docs_root = Path("docs")
    inventory = (docs_root / "DEPLOYED_AGENT_INVENTORY_DEFERRED.md").read_text()
    readiness = (docs_root / "EXTERNAL_AGENT_READINESS_LADDER_FIXED_DAG.md").read_text()
    system_map = (docs_root / "SYSTEM_MAP.md").read_text()
    combined = "\n".join([inventory, readiness, system_map])

    assert "deployed_but_deferred" in combined
    assert "does not mean `live_verified=true`" in combined
    assert "does not mean `invoke_enabled_by_default=true`" in combined
    assert "does not call external `/v1/agent/invoke`" in combined
    assert "Runtime authority remains in `config/fixed_dag/agent_catalog.json`" in combined
