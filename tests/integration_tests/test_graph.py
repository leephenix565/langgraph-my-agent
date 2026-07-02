"""Blocking runtime graph smoke for the active reset quality gate."""

import json
from types import SimpleNamespace

import pytest

import react_agent.graph as graph_module
from react_agent.context import Context
from react_agent.fixed_dag_contracts import (
    DIMENSION_GROUPS,
    RESET_RUNTIME_AGENT_IDS,
    validate_decision_result,
    validate_dimension_composite_result,
    validate_fixed_dag_plan,
    validate_report_result,
    validate_selected_fixed_dag_plan,
    validate_workflow_snapshot_v2,
)
from react_agent.fixed_dag_executor import (
    validate_dag_execution_result,
    validate_selected_dag_steps,
)
from react_agent.fixed_dag_external_adapter import (
    map_external_response_to_fixed_dag_object,
)

pytestmark = pytest.mark.anyio


def _compute_envelope(agent_id: str, external_agent_id: str, tool_result: dict[str, object]):
    return {
        "schema_version": "external_agent_compute_v0",
        "agent_id": agent_id,
        "external_agent_id": external_agent_id,
        "status": "ok",
        "tool_result": tool_result,
    }


def _agent_conclusion() -> dict[str, object]:
    return {
        "schema_version": "agent_conclusion_v1",
        "agent_id": "value_ml_valuation",
        "external_agent_id": "valuation_ml",
        "dimension": "value",
        "role": "direction",
        "stance": "demo_positive",
        "confidence": 0.66,
        "status": "ok",
        "evidence": [
            {
                "id": "graph-demo-evidence",
                "fact": "Bounded graph demo fixture.",
                "source": "integration_test",
                "as_of": "2026-06-05",
                "data_as_of": "2026-06-05",
            }
        ],
        "as_of": "2026-06-05",
        "data_as_of": "2026-06-05",
        "event_flags": [],
    }


async def test_selected_routing_context_defaults_off_and_env_can_enable(monkeypatch) -> None:
    monkeypatch.delenv("ENABLE_SELECTED_ROUTING", raising=False)
    assert Context().enable_selected_routing is False

    monkeypatch.setenv("ENABLE_SELECTED_ROUTING", "1")
    assert Context().enable_selected_routing is True

    monkeypatch.delenv("ENABLE_LLM_DIMENSION_ROUTER", raising=False)
    assert Context().enable_llm_dimension_router is False

    monkeypatch.setenv("ENABLE_LLM_DIMENSION_ROUTER", "1")
    assert Context().enable_llm_dimension_router is True

    monkeypatch.delenv("LLM_DIMENSION_ROUTER_MODE", raising=False)
    assert Context().llm_dimension_router_mode == ""

    monkeypatch.setenv("LLM_DIMENSION_ROUTER_MODE", "real")
    assert Context().llm_dimension_router_mode == "real"

    monkeypatch.delenv("ENABLE_INTERNAL_LLM_PLACEHOLDERS", raising=False)
    assert Context().enable_internal_llm_placeholders is False

    monkeypatch.setenv("ENABLE_INTERNAL_LLM_PLACEHOLDERS", "1")
    assert Context().enable_internal_llm_placeholders is True

    monkeypatch.delenv("ENABLE_LLM_REPORT_SYNTHESIS", raising=False)
    assert Context().enable_llm_report_synthesis is False

    monkeypatch.setenv("ENABLE_LLM_REPORT_SYNTHESIS", "1")
    assert Context().enable_llm_report_synthesis is True

    monkeypatch.delenv("FIXED_DAG_AS_OF", raising=False)
    assert Context().fixed_dag_as_of == ""

    monkeypatch.setenv("FIXED_DAG_AS_OF", "2026-06-05")
    assert Context().fixed_dag_as_of == "2026-06-05"


async def test_react_agent_fixed_dag_skeleton_passthrough(monkeypatch) -> None:
    def fail_provider(*args, **kwargs):
        raise AssertionError("provider should not be called by R3 skeleton")

    def fail_external_client(*args, **kwargs):
        raise AssertionError("external HTTP should not be called by fixed DAG skeleton")

    def fail_selected_compiler(*args, **kwargs):
        raise AssertionError("selected compiler should stay default-off")

    monkeypatch.setattr("react_agent.default_agents.load_chat_model", fail_provider)
    monkeypatch.setattr("react_agent.external_http_agents.httpx.AsyncClient", fail_external_client)
    monkeypatch.setattr(graph_module, "compile_selected_fixed_dag_plan", fail_selected_compiler)

    res = graph_module.graph.invoke(
        {"messages": [("user", "Demo question: give a quick market view")]},  # type: ignore[arg-type]
        context=Context(model="deepseek/deepseek-chat", system_prompt="inactive"),
    )

    assert res["fixed_dag_plan"]["schema"] == "fixed_dag_plan_v1"
    valid, reason = validate_fixed_dag_plan(res["fixed_dag_plan"])
    assert valid, reason
    valid, reason = validate_dag_execution_result(res["dag_execution"])
    assert valid, reason
    assert res["dag_execution"]["provenance"]["provider_invoked"] is False
    assert res["dag_execution"]["provenance"]["external_invoked"] is False
    assert res["execution_batches"] == res["dag_execution"]["execution_batches"]
    assert res["dag_step_results"] == res["dag_execution"]["step_results"]
    assert res["dag_step_results"]["financial_data_service"]["runtime_kind"] == "external_http_candidate"
    assert res["dag_step_results"]["financial_data_service"]["invoke_enabled"] is False
    assert res["dag_step_results"]["financial_data_service"]["live_verified"] is False
    assert len(res["fixed_dag_plan"]["target_agent_ids"]) == 27
    assert res["workflow_snapshot"]["schema"] == "workflow_snapshot_v2"
    valid, reason = validate_workflow_snapshot_v2(res["workflow_snapshot"])
    assert valid, reason
    assert res["report_result"]["schema"] == "report_result_v1"
    valid, reason = validate_report_result(res["report_result"])
    assert valid, reason
    assert res["report_input_bundle"]["schema"] == "report_input_bundle_v1"
    assert "报告生成输入摘要" in res["report_result"]["answer"]
    valid, reason = validate_decision_result(res["decision_result"])
    assert valid, reason
    assert set(res["dimension_results"]) == set(DIMENSION_GROUPS)
    for item in res["dimension_results"].values():
        valid, reason = validate_dimension_composite_result(item)
        assert valid, reason
    assert len(res["workflow_snapshot"]["dagSteps"]) == len(res["fixed_dag_plan"]["steps"])
    assert res["workflow_snapshot"]["executionBatches"] == res["execution_batches"]
    assert res["workflow_snapshot"]["stepResults"] == res["dag_step_results"]
    assert len(res["workflow_snapshot"]["dimensionGroups"]) == 4
    assert res["emitted_bundle"]["provider_invoked"] is False
    assert res["emitted_bundle"]["external_invoked"] is False
    assert res["multi_agent_bundle"]["schema"] == "fixed_dag_reset_bundle_v1"
    assert res["multi_agent_bundle"]["dag_execution"]["schema_version"] == "fixed_dag_execution_v1"
    assert res["multi_agent_bundle"]["report_input_bundle"]["schema"] == "report_input_bundle_v1"


async def test_fixed_dag_context_as_of_propagates_to_plan(monkeypatch) -> None:
    def fail_provider(*args, **kwargs):
        raise AssertionError("provider should not be called by R3 skeleton")

    def fail_external_client(*args, **kwargs):
        raise AssertionError("external HTTP should not be called by fixed DAG skeleton")

    monkeypatch.setattr("react_agent.default_agents.load_chat_model", fail_provider)
    monkeypatch.setattr("react_agent.external_http_agents.httpx.AsyncClient", fail_external_client)

    res = graph_module.graph.invoke(
        {"messages": [("user", "请分析 600519.SH")]},  # type: ignore[arg-type]
        context=Context(
            model="deepseek/deepseek-chat",
            system_prompt="inactive",
            fixed_dag_as_of="2026-06-05",
        ),
    )

    assert res["fixed_dag_plan"]["as_of"] == "2026-06-05"
    assert res["dag_execution"]["agent_task_summaries"][0]["as_of"] == "2026-06-05"
    assert res["report_input_bundle"]["agent_task_summaries"][0]["as_of"] == "2026-06-05"
    assert res.get("messages")
    assert "研判流程" in res["messages"][-1].content
    assert "layer_plan" not in res
    assert "fusion_verdict" not in res
    assert "contract" not in graph_module.__dict__
    assert "AGENT_METADATA" not in graph_module.__dict__
    assert "AGENT_TOOLS" not in graph_module.__dict__


async def test_external_compute_demo_graph_path_uses_fake_bridge(monkeypatch) -> None:
    import react_agent.fixed_dag_external_compute_bridge as bridge

    def fail_provider(*args, **kwargs):
        raise AssertionError("provider should not be called by external compute demo")

    def fail_legacy_external_client(*args, **kwargs):
        raise AssertionError("legacy external HTTP client should not be used")

    def fake_invoke(entry, **_kwargs):
        assert entry.agent_id == "value_ml_valuation"
        mapped = map_external_response_to_fixed_dag_object(
            _compute_envelope(
                "value_ml_valuation",
                "valuation_ml",
                _agent_conclusion(),
            )
        )
        return {
            "agent_id": entry.agent_id,
            "status": "pass",
            "mapped": mapped,
            "failure_code": "",
            "warning": "",
        }

    monkeypatch.setattr("react_agent.default_agents.load_chat_model", fail_provider)
    monkeypatch.setattr("react_agent.external_http_agents.httpx.AsyncClient", fail_legacy_external_client)
    monkeypatch.setattr(bridge, "invoke_external_compute", fake_invoke)

    res = graph_module.graph.invoke(
        {"messages": [("user", "请从估值角度分析贵州茅台 600519.SH 当前是否值得关注。")]},  # type: ignore[arg-type]
        context=Context(
            enable_external_compute_demo=True,
            external_compute_demo_allowlist=("value_ml_valuation",),
            disable_external_compute_default=True,
        ),
    )
    rendered = json.dumps(
        {
            "dag_execution": res["dag_execution"],
            "workflow_snapshot": res["workflow_snapshot"],
            "report_result": res["report_result"],
            "l2_conclusions": res["l2_conclusions"],
        },
        ensure_ascii=False,
    ).lower()

    valid, reason = validate_dag_execution_result(res["dag_execution"])
    assert valid, reason
    assert res["dag_execution"]["provenance"]["external_invoked"] is False
    assert res["dag_execution"]["provenance"]["external_compute_demo_mapped_agents"] == [
        "value_ml_valuation"
    ]
    assert res["l2_conclusions"]["value_ml_valuation"]["status"] == "complete"
    assert res["report_input_bundle"]["schema"] == "report_input_bundle_v1"
    assert res["dag_step_results"]["l2:value_ml_valuation"]["agent_evidence"]["stance"] == "demo_positive"
    assert "研判流程输出" in res["messages"][-1].content
    assert "贵州茅台" in res["messages"][-1].content
    assert "外部计算演示摘要" not in res["messages"][-1].content
    assert "http://127.0.0.1" not in rendered
    assert "/v1/agent/invoke" not in res["messages"][-1].content
    assert "raw_response" not in rendered


async def test_graph_path_can_synthesize_llm_report_from_external_evidence(monkeypatch) -> None:
    import react_agent.fixed_dag_external_compute_bridge as bridge

    class FakeReportModel:
        def __init__(self) -> None:
            self.prompts: list[str] = []

        def invoke(self, prompt: str):
            self.prompts.append(prompt)
            return json.dumps(
                {
                    "title": "固定 DAG 大模型研判报告",
                    "answer": (
                        "估值维度接收到机器学习企业估值的 demo_positive 输入；"
                        "风险维度暂未触发风险否决。综合研判：本轮可以关注，但需要业务复核。"
                    ),
                    "sections": [
                        {
                            "id": "summary",
                            "title": "综合研判",
                            "content": "报告生成智能体已读取结构化输入包后整理最终报告。",
                        }
                    ],
                    "evidence_cards": [
                        {
                            "title": "输入覆盖",
                            "note": "包含 L2 单体智能体和 L3 综合智能体摘要。",
                        }
                    ],
                    "limitations": ["显式开关下的大模型报告综合，不代表默认生产调用。"],
                },
                ensure_ascii=False,
            )

    fake_model = FakeReportModel()

    def fake_invoke(entry, **_kwargs):
        assert entry.agent_id == "value_ml_valuation"
        mapped = map_external_response_to_fixed_dag_object(
            _compute_envelope(
                "value_ml_valuation",
                "valuation_ml",
                _agent_conclusion(),
            )
        )
        return {
            "agent_id": entry.agent_id,
            "status": "pass",
            "mapped": mapped,
            "failure_code": "",
            "warning": "",
        }

    monkeypatch.setattr("react_agent.default_agents.load_chat_model", lambda *_args, **_kwargs: fake_model)
    monkeypatch.setattr(
        "react_agent.fixed_dag_report_synthesizer.load_chat_model",
        lambda _model: fake_model,
    )
    monkeypatch.setattr(bridge, "invoke_external_compute", fake_invoke)

    res = graph_module.graph.invoke(
        {"messages": [("user", "请分析贵州茅台 600519.SH 当前是否值得关注。")]},  # type: ignore[arg-type]
        context=Context(
            enable_external_compute_demo=True,
            external_compute_demo_allowlist=("value_ml_valuation",),
            enable_llm_report_synthesis=True,
            disable_external_compute_default=True,
        ),
    )
    rendered = json.dumps(
        {
            "dag_execution": res["dag_execution"],
            "workflow_snapshot": res["workflow_snapshot"],
            "report_result": res["report_result"],
        },
        ensure_ascii=False,
    ).lower()

    valid, reason = validate_dag_execution_result(res["dag_execution"])
    assert valid, reason
    valid, reason = validate_workflow_snapshot_v2(res["workflow_snapshot"])
    assert valid, reason
    assert fake_model.prompts
    assert res["dag_execution"]["provenance"]["provider_invoked"] is True
    assert res["workflow_snapshot"]["provenance"]["providerInvoked"] is True
    assert "综合研判：本轮可以关注" in res["messages"][-1].content
    assert "报告生成输入摘要" not in res["messages"][-1].content
    assert "value_ml_valuation" in fake_model.prompts[0]
    assert "raw_response" not in rendered
    assert "/v1/agent/invoke" not in rendered


async def test_selected_routing_flag_builds_and_executes_selected_plan(monkeypatch) -> None:
    def fail_provider(*args, **kwargs):
        raise AssertionError("provider should not be called by selected routing flag")

    def fail_external_client(*args, **kwargs):
        raise AssertionError("external HTTP should not be called by selected routing flag")

    def fail_router_provider(*args, **kwargs):
        raise AssertionError("router provider seam should not be called by selected routing flag")

    monkeypatch.setattr("react_agent.default_agents.load_chat_model", fail_provider)
    monkeypatch.setattr("react_agent.external_http_agents.httpx.AsyncClient", fail_external_client)
    monkeypatch.setattr(graph_module, "_invoke_dimension_router_provider", fail_router_provider)

    res = graph_module.graph.invoke(
        {"messages": [("user", "Explain discounted cash flow in simple terms.")]},  # type: ignore[arg-type]
        context=Context(
            enable_selected_routing=True,
            disable_external_compute_default=True,
            disable_non_l4_external_compute_default=True,
        ),
    )

    assert res["fixed_dag_plan"]["schema"] == "selected_fixed_dag_plan_v1"
    assert len(res["fixed_dag_plan"]["steps"]) < len(RESET_RUNTIME_AGENT_IDS)
    valid, reason = validate_selected_fixed_dag_plan(res["fixed_dag_plan"])
    assert valid, reason
    valid, reason = validate_selected_dag_steps(res["fixed_dag_plan"])
    assert valid, reason
    valid, reason = validate_dag_execution_result(res["dag_execution"])
    assert valid, reason
    valid, reason = validate_decision_result(res["decision_result"])
    assert valid, reason
    valid, reason = validate_report_result(res["report_result"])
    assert valid, reason
    assert res["fixed_dag_plan"]["provenance"]["selected_routing_requested"] is True
    assert res["fixed_dag_plan"]["provenance"]["selected_routing_fallback"] is False
    assert res["fixed_dag_plan"]["provenance"]["route_granularity"] == "dimension"
    assert res["fixed_dag_plan"]["selected_agents"] == res["fixed_dag_plan"]["target_agent_ids"]
    assert set(DIMENSION_GROUPS["value"]) <= set(res["fixed_dag_plan"]["target_agent_ids"])
    assert res["dag_execution"]["provenance"]["provider_invoked"] is False
    assert res["dag_execution"]["provenance"]["external_invoked"] is False
    assert set(res["dag_step_results"]) == {step["id"] for step in res["fixed_dag_plan"]["steps"]}
    assert "decision_synthesizer" in res["dag_step_results"]
    assert "report_generator" in res["dag_step_results"]
    assert res["report_result"]["answer"].strip()
    report_section_ids = {section["id"] for section in res["report_result"]["sections"]}
    assert "market_dimension" not in report_section_ids
    assert "macro_dimension" not in report_section_ids
    assert "unselected_scope" in report_section_ids
    assert "用户问题覆盖估值、市场、风险和宏观四个维度" not in res["report_result"]["answer"]
    assert res["emitted_bundle"]["answer"] == res["report_result"]["answer"]
    assert res["messages"][-1].content == res["report_result"]["answer"]
    assert set(res["workflow_snapshot"]["completedSteps"]) == set(res["dag_step_results"])
    valid, reason = validate_workflow_snapshot_v2(res["workflow_snapshot"])
    assert valid, reason
    assert {item["id"] for item in res["workflow_snapshot"]["dimensionGroups"]} == {"value"}
    assert res["workflow_snapshot"]["provenance"]["selectedRoutingRequested"] is True
    assert res["workflow_snapshot"]["provenance"]["selectedRoutingFallback"] is False
    assert res["workflow_snapshot"]["provenance"]["routeGranularity"] == "dimension"
    assert res["workflow_snapshot"]["provenance"]["selectedDimensions"] == ["value"]
    assert res["workflow_snapshot"]["provenance"]["providerInvoked"] is False
    assert res["workflow_snapshot"]["provenance"]["externalInvoked"] is False
    assert res["workflow_snapshot"]["provenance"]["providerRouterEnabled"] is False
    assert res["workflow_snapshot"]["provenance"]["providerRouterInvoked"] is False
    rendered = json.dumps(
        {
            "workflow": res["workflow_snapshot"],
            "emit": res["emitted_bundle"],
            "message": res["messages"][-1].content,
        },
        ensure_ascii=False,
    )
    assert "raw_response" not in rendered.lower()
    assert "/v1/agent/invoke" not in rendered
    assert "endpoint" not in rendered.lower()
    assert "secret" not in rendered.lower()
    assert "Traceback" not in rendered


async def test_llm_dimension_router_flag_alone_keeps_full_dag_and_does_not_invoke(
    monkeypatch,
) -> None:
    def fail_router_provider(*args, **kwargs):
        raise AssertionError("provider flag alone must not call router provider seam")

    monkeypatch.setattr(graph_module, "_invoke_dimension_router_provider", fail_router_provider)

    res = graph_module.graph.invoke(
        {"messages": [("user", "Explain discounted cash flow in simple terms.")]},  # type: ignore[arg-type]
        context=Context(
            enable_llm_dimension_router=True,
            disable_external_compute_default=True,
            disable_non_l4_external_compute_default=True,
        ),
    )

    plan = res["fixed_dag_plan"]
    assert plan["schema"] == "fixed_dag_plan_v1"
    assert plan["provenance"]["provider_router_enabled"] is True
    assert plan["provenance"]["provider_router_invoked"] is False
    assert plan["provenance"]["provider_router_fallback_reason"] == "selected_routing_disabled"
    assert res["workflow_snapshot"]["provenance"]["providerRouterEnabled"] is True
    assert res["workflow_snapshot"]["provenance"]["providerRouterInvoked"] is False


def _dimension_router_payload(dimensions: list[str], **overrides: object) -> str:
    payload: dict[str, object] = {
        "schema": "route_intent_v1",
        "schema_version": "route_intent_v1",
        "task_type": "general",
        "targets": ["example company"],
        "selected_dimensions": dimensions,
        "route_confidence": 0.84,
        "needs_clarification": False,
        "clarification_question": "",
        "fallback_reason": "",
        "provenance": {"source": "fake_provider_fixture"},
    }
    payload.update(overrides)
    return json.dumps(payload, ensure_ascii=False)


@pytest.mark.parametrize(
    ("dimensions", "expected_dimensions"),
    [
        (["value"], {"value"}),
        (["market"], {"market"}),
        (["risk", "macro"], {"risk", "macro"}),
    ],
)
async def test_selected_routing_with_fake_llm_dimension_router_builds_selected_plan(
    monkeypatch,
    dimensions: list[str],
    expected_dimensions: set[str],
) -> None:
    raw_marker = "NEVER_STORE_FAKE_ROUTER_RAW_MARKER"

    def fake_router_provider(_question, _context):
        return _dimension_router_payload(
            dimensions,
            provenance={
                "source": "fake_provider_fixture",
                "raw_marker": raw_marker,
            },
        )

    def fail_model_factory(*args, **kwargs):
        raise AssertionError("load_chat_model must not be called by fake router seam")

    monkeypatch.setattr(graph_module, "_invoke_dimension_router_provider", fake_router_provider)
    monkeypatch.setattr("react_agent.utils.load_chat_model", fail_model_factory)
    monkeypatch.setattr("react_agent.default_agents.load_chat_model", fail_model_factory)

    res = graph_module.graph.invoke(
        {"messages": [("user", "Please route this fixed DAG question.")]},  # type: ignore[arg-type]
        context=Context(
            enable_selected_routing=True,
            enable_llm_dimension_router=True,
            disable_external_compute_default=True,
            disable_non_l4_external_compute_default=True,
        ),
    )

    rendered = json.dumps(
        {
            "plan": res["fixed_dag_plan"],
            "workflow": res["workflow_snapshot"],
            "message": res["messages"][-1].content,
        },
        ensure_ascii=False,
    )
    plan = res["fixed_dag_plan"]
    assert plan["schema"] == "selected_fixed_dag_plan_v1"
    valid, reason = validate_selected_fixed_dag_plan(plan)
    assert valid, reason
    assert set(plan["selected_dimensions"]) == expected_dimensions
    for dimension in expected_dimensions:
        assert set(DIMENSION_GROUPS[dimension]) <= set(plan["target_agent_ids"])
    assert plan["provenance"]["provider_router_enabled"] is True
    assert plan["provenance"]["provider_router_invoked"] is True
    assert plan["provenance"]["provider_router_parse_ok"] is True
    assert plan["provenance"]["provider_invoked"] is False
    assert plan["provenance"]["external_invoked"] is False
    assert res["workflow_snapshot"]["provenance"]["providerRouterEnabled"] is True
    assert res["workflow_snapshot"]["provenance"]["providerRouterInvoked"] is True
    assert res["workflow_snapshot"]["provenance"]["providerRouterMode"] == "fake"
    assert res["workflow_snapshot"]["provenance"]["providerRouterParseOk"] is True
    assert raw_marker not in rendered
    assert "raw_response" not in rendered.lower()
    assert "/v1/agent/invoke" not in rendered


@pytest.mark.parametrize(
    "raw_output",
    [
        "```json\n" + _dimension_router_payload(["value", "risk"]) + "\n```",
        "Route intent:\n" + _dimension_router_payload(["market"]) + "\nDone.",
    ],
)
async def test_selected_routing_with_fake_llm_dimension_router_extracts_wrapped_json(
    monkeypatch,
    raw_output: str,
) -> None:
    monkeypatch.setattr(
        graph_module,
        "_invoke_dimension_router_provider",
        lambda _question, _context: raw_output,
    )

    res = graph_module.graph.invoke(
        {"messages": [("user", "Please route this fixed DAG question.")]},  # type: ignore[arg-type]
        context=Context(
            enable_selected_routing=True,
            enable_llm_dimension_router=True,
            disable_external_compute_default=True,
            disable_non_l4_external_compute_default=True,
        ),
    )

    rendered = json.dumps(
        {
            "plan": res["fixed_dag_plan"],
            "workflow": res["workflow_snapshot"],
            "message": res["messages"][-1].content,
        },
        ensure_ascii=False,
    )
    plan = res["fixed_dag_plan"]
    assert plan["schema"] == "selected_fixed_dag_plan_v1"
    assert plan["provenance"]["selected_routing_requested"] is True
    assert plan["provenance"]["selected_routing_fallback"] is False
    assert plan["provenance"]["provider_router_enabled"] is True
    assert plan["provenance"]["provider_router_invoked"] is True
    assert plan["provenance"]["provider_router_parse_ok"] is True
    assert res["workflow_snapshot"]["provenance"]["providerRouterParseOk"] is True
    assert raw_output not in rendered
    assert "raw_response" not in rendered.lower()
    assert "/v1/agent/invoke" not in rendered


async def test_selected_routing_with_real_llm_dimension_router_uses_openai_compatible_json(
    monkeypatch,
) -> None:
    requests: list[dict[str, object]] = []

    class FakeResponse:
        status_code = 200

        def json(self):
            return {
                "choices": [
                    {
                        "message": {
                            "content": _dimension_router_payload(["market"]),
                        }
                    }
                ]
            }

    class FakeClient:
        def __init__(self, *, timeout):
            self.timeout = timeout

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def post(self, url, *, headers, json):
            requests.append({"url": url, "headers": headers, "json": json})
            return FakeResponse()

    monkeypatch.setattr(graph_module.httpx, "Client", FakeClient)

    res = graph_module.graph.invoke(
        {"messages": [("user", "只看 000001 的市场交易面和资金流。")]},  # type: ignore[arg-type]
        context=Context(
            enable_selected_routing=True,
            enable_llm_dimension_router=True,
            llm_dimension_router_mode="real",
            router_model="deepseek/deepseek-chat",
            router_openai_base_url="https://provider.example",
            router_openai_api_key="test-key",
            disable_external_compute_default=True,
            disable_non_l4_external_compute_default=True,
        ),
    )

    plan = res["fixed_dag_plan"]
    rendered = json.dumps(
        {
            "plan": plan,
            "workflow": res["workflow_snapshot"],
            "message": res["messages"][-1].content,
        },
        ensure_ascii=False,
    )
    assert requests
    request = requests[0]
    assert request["url"] == "https://provider.example/v1/chat/completions"
    assert request["headers"]["Authorization"] == "Bearer test-key"
    assert request["json"]["model"] == "deepseek-chat"
    assert request["json"]["response_format"] == {"type": "json_object"}
    assert request["json"]["max_tokens"] == 220
    assert plan["schema"] == "selected_fixed_dag_plan_v1"
    assert plan["selected_dimensions"] == ["market"]
    assert plan["provenance"]["provider_invoked"] is False
    assert plan["provenance"]["provider_router_mode"] == "real"
    assert plan["provenance"]["provider_router_invoked"] is True
    assert plan["provenance"]["provider_router_parse_ok"] is True
    assert res["workflow_snapshot"]["provenance"]["providerRouterMode"] == "real"
    assert res["workflow_snapshot"]["provenance"]["providerRouterSelectedDimensions"] == [
        "market"
    ]
    assert "test-key" not in rendered
    assert "provider.example" not in rendered
    assert "raw_response" not in rendered.lower()
    assert "/v1/agent/invoke" not in rendered


@pytest.mark.parametrize(
    ("raw_output", "expected_reason"),
    [
        (
            _dimension_router_payload(["value"], selected_agents=["value_research_synthesis"]),
            "agent_level_route_not_allowed_in_dimension_mode",
        ),
        (_dimension_router_payload(["credit"]), "unknown_selected_dimension"),
        (
            _dimension_router_payload(["value"], provenance={"source": "fixture", "route_mode": "Star"}),
            "legacy_route_value_present",
        ),
        (
            _dimension_router_payload(
                ["value"],
                runtime_bindings={"route_planner": "x"},
            ),
            "forbidden_route_intent_field_present",
        ),
        ("The route is value and risk.", "router_provider_missing_output"),
        ("{\"schema\":\"route_intent_v1\",}", "router_provider_invalid_json"),
        (_dimension_router_payload(["value"], route_confidence=0.1), "low_route_confidence"),
        (
            _dimension_router_payload(
                ["value"],
                needs_clarification=True,
                clarification_question="Which target?",
            ),
            "route_intent_needs_clarification",
        ),
    ],
)
async def test_selected_routing_with_fake_llm_dimension_router_invalid_output_falls_back(
    monkeypatch,
    raw_output: str,
    expected_reason: str,
) -> None:
    monkeypatch.setattr(
        graph_module,
        "_invoke_dimension_router_provider",
        lambda _question, _context: raw_output,
    )

    res = graph_module.graph.invoke(
        {"messages": [("user", "Please route this fixed DAG question.")]},  # type: ignore[arg-type]
        context=Context(
            enable_selected_routing=True,
            enable_llm_dimension_router=True,
            disable_external_compute_default=True,
            disable_non_l4_external_compute_default=True,
        ),
    )

    rendered = json.dumps(
        {
            "plan": res["fixed_dag_plan"],
            "workflow": res["workflow_snapshot"],
            "message": res["messages"][-1].content,
        },
        ensure_ascii=False,
    )
    plan = res["fixed_dag_plan"]
    assert plan["schema"] == "fixed_dag_plan_v1"
    valid, reason = validate_fixed_dag_plan(plan)
    assert valid, reason
    assert plan["provenance"]["selected_routing_requested"] is True
    assert plan["provenance"]["selected_routing_fallback"] is True
    assert plan["provenance"]["fallback_reason"] == expected_reason
    assert plan["provenance"]["provider_router_enabled"] is True
    assert plan["provenance"]["provider_router_invoked"] is True
    assert plan["provenance"]["provider_router_parse_ok"] is False
    assert plan["provenance"]["provider_router_error_code"] == expected_reason
    assert plan["provenance"]["provider_invoked"] is False
    assert res["workflow_snapshot"]["provenance"]["providerRouterInvoked"] is True
    assert res["workflow_snapshot"]["provenance"]["providerRouterFallbackReason"] == expected_reason
    assert raw_output not in rendered


@pytest.mark.parametrize(
    ("provider", "expected_reason", "expected_invoked"),
    [
        (lambda _question, _context: None, "router_provider_missing_output", False),
        (
            lambda _question, _context: (_ for _ in ()).throw(TimeoutError("slow")),
            "router_provider_timeout",
            True,
        ),
        (
            lambda _question, _context: (_ for _ in ()).throw(RuntimeError("secret details")),
            "router_provider_exception",
            True,
        ),
    ],
)
async def test_selected_routing_with_fake_llm_dimension_router_provider_failure_falls_back(
    monkeypatch,
    provider,
    expected_reason: str,
    expected_invoked: bool,
) -> None:
    monkeypatch.setattr(graph_module, "_invoke_dimension_router_provider", provider)

    res = graph_module.graph.invoke(
        {"messages": [("user", "Please route this fixed DAG question.")]},  # type: ignore[arg-type]
        context=Context(
            enable_selected_routing=True,
            enable_llm_dimension_router=True,
            disable_external_compute_default=True,
            disable_non_l4_external_compute_default=True,
        ),
    )

    rendered = json.dumps(
        {
            "plan": res["fixed_dag_plan"],
            "workflow": res["workflow_snapshot"],
            "message": res["messages"][-1].content,
        },
        ensure_ascii=False,
    )
    plan = res["fixed_dag_plan"]
    assert plan["schema"] == "fixed_dag_plan_v1"
    assert plan["provenance"]["fallback_reason"] == expected_reason
    assert plan["provenance"]["provider_router_invoked"] is expected_invoked
    assert plan["provenance"]["provider_router_error_code"] in {
        "router_provider_unavailable",
        expected_reason,
    }
    assert plan["provenance"]["provider_invoked"] is False
    assert "secret details" not in rendered
    assert "Traceback" not in rendered


async def test_selected_routing_and_internal_llm_placeholder_flags_can_coexist(monkeypatch) -> None:
    class FakeModel:
        def invoke(self, _prompt: str):
            return SimpleNamespace(
                content=json.dumps(
                    {
                        "analysis": "企业舆情功能位当前只做内部占位框架梳理。",
                        "key_points": ["需等待真实舆情雷达服务完成 readiness。"],
                        "evidence": [{"fact": "内部 LLM 占位，不代表外部服务输出。"}],
                        "confidence": 0.28,
                    },
                    ensure_ascii=False,
                )
            )

    def fail_external_client(*args, **kwargs):
        raise AssertionError("external HTTP should not be called by internal placeholders")

    monkeypatch.setattr(
        "react_agent.fixed_dag_llm_placeholders.load_chat_model",
        lambda _model: FakeModel(),
    )
    monkeypatch.setattr("react_agent.external_http_agents.httpx.AsyncClient", fail_external_client)

    res = graph_module.graph.invoke(
        {"messages": [("user", "Please summarize public opinion and sentiment for this company.")]},  # type: ignore[arg-type]
        context=Context(
            enable_selected_routing=True,
            enable_internal_llm_placeholders=True,
        ),
    )

    assert res["fixed_dag_plan"]["schema"] == "selected_fixed_dag_plan_v1"
    assert set(DIMENSION_GROUPS["market"]) <= set(res["fixed_dag_plan"]["target_agent_ids"])
    assert set(res["l2_conclusions"]) == set(DIMENSION_GROUPS["market"])
    conclusion = res["l2_conclusions"]["sentiment_company_radar"]
    assert conclusion["status"] == "partial"
    assert conclusion["confidence"] <= 0.4
    assert conclusion["provenance"]["source"] == "internal_llm_placeholder"
    assert conclusion["provenance"]["provider_invoked"] is True
    assert conclusion["provenance"]["external_invoked"] is False
    assert res["dag_execution"]["provenance"]["internal_llm_placeholders_enabled"] is True
    assert res["dag_execution"]["provenance"]["internal_llm_placeholder_conclusions"] == len(
        DIMENSION_GROUPS["market"]
    )
    assert res["dag_execution"]["provenance"]["external_invoked"] is False
    assert set(res["dag_step_results"]) == {step["id"] for step in res["fixed_dag_plan"]["steps"]}
    assert {item["id"] for item in res["workflow_snapshot"]["dimensionGroups"]} == {"market"}
    assert res["workflow_snapshot"]["provenance"]["routeGranularity"] == "dimension"
    assert res["workflow_snapshot"]["provenance"]["selectedDimensions"] == ["market"]
    assert "risk" not in res["dimension_results"]


async def test_selected_routing_failure_falls_back_to_full_dag(monkeypatch) -> None:
    def fail_compile(*args, **kwargs):
        raise ValueError("forced selected compiler failure")

    monkeypatch.setattr(graph_module, "compile_selected_fixed_dag_plan", fail_compile)

    res = graph_module.graph.invoke(
        {"messages": [("user", "Explain discounted cash flow in simple terms.")]},  # type: ignore[arg-type]
        context=Context(enable_selected_routing=True),
    )

    plan = res["fixed_dag_plan"]
    assert plan["schema"] == "fixed_dag_plan_v1"
    assert len(plan["steps"]) == len(RESET_RUNTIME_AGENT_IDS)
    valid, reason = validate_fixed_dag_plan(plan)
    assert valid, reason
    assert plan["provenance"]["selected_routing_requested"] is True
    assert plan["provenance"]["selected_routing_fallback"] is True
    assert plan["provenance"]["fallback_reason"] == "selected_routing_compile_failed:ValueError"
    assert plan["provenance"]["provider_invoked"] is False
    assert plan["provenance"]["external_invoked"] is False
    assert res["workflow_snapshot"]["provenance"]["selectedRoutingRequested"] is True
    assert res["workflow_snapshot"]["provenance"]["selectedRoutingFallback"] is True
    assert res["workflow_snapshot"]["provenance"]["fallbackReason"] == "selected_routing_compile_failed:ValueError"
    assert res["workflow_snapshot"]["provenance"]["routeGranularity"] == "dimension"
    assert "provider" not in plan["provenance"]["fallback_reason"]
    valid, reason = validate_dag_execution_result(res["dag_execution"])
    assert valid, reason
