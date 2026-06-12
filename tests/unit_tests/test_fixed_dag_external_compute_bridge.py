import importlib
import json

from react_agent.context import Context
from react_agent.fixed_dag_contracts import (
    build_agent_task,
    build_route_intent,
    compile_selected_fixed_dag_plan,
)
from react_agent.fixed_dag_external_compute_bridge import (
    COMPUTE_PATH,
    DEMO_COMPUTE_SERVICE_REGISTRY,
    ExternalComputeDemoEntry,
    build_external_compute_request,
    invoke_external_compute,
    normalize_demo_allowlist,
    run_external_compute_for_plan,
    validate_demo_entry,
)


def _agent_conclusion(
    agent_id: str = "value_ml_valuation",
    *,
    external_agent_id: str = "valuation_ml",
    dimension: str = "value",
) -> dict[str, object]:
    role = "gate_member" if dimension == "risk" else "direction"
    payload: dict[str, object] = {
        "schema_version": "agent_conclusion_v1",
        "agent_id": agent_id,
        "external_agent_id": external_agent_id,
        "dimension": dimension,
        "role": role,
        "stance": "slightly_positive",
        "confidence": 0.66,
        "status": "ok",
        "evidence": [
            {
                "id": "safe-evidence",
                "fact": "Bounded external compute demo fixture.",
                "source": "unit_test",
                "as_of": "2026-06-05",
                "data_as_of": "2026-06-05",
            }
        ],
        "as_of": "2026-06-05",
        "data_as_of": "2026-06-05",
        "event_flags": [],
    }
    if role == "gate_member":
        payload.pop("stance")
        payload["risk_score"] = 0.34
    return payload


def _dimension_conclusion() -> dict[str, object]:
    return {
        "schema_version": "dimension_conclusion_v1",
        "agent_id": "value_composite",
        "external_agent_id": "composite_valuation",
        "dimension": "value",
        "role": "direction",
        "target": "600519.SH",
        "stance": 0.18,
        "confidence": 0.71,
        "members": [
            {
                "agent_id": "value_ml_valuation",
                "stance": 0.2,
                "confidence": 0.72,
                "weight": 0.6,
                "status": "ok",
            },
            {
                "agent_id": "value_research_synthesis",
                "stance": 0.1,
                "confidence": 0.68,
                "weight": 0.4,
                "status": "ok",
            },
        ],
        "method": "weighted_member_vote",
        "evidence": [
            {
                "id": "dimension-evidence",
                "fact": "Value members are mildly positive.",
                "source": "unit_test",
                "as_of": "2026-06-05",
                "data_as_of": "2026-06-05",
            }
        ],
        "as_of": "2026-06-05",
        "data_as_of": "2026-06-05",
        "status": "ok",
    }


def _data_bundle() -> dict[str, object]:
    return {
        "schema_version": "data_bundle_v1",
        "agent_id": "financial_data_service",
        "external_agent_id": "financial_data_service",
        "status": "ok",
        "target": "600519.SH",
        "as_of": "2026-06-05",
        "data_as_of": "2026-06-05",
        "snapshot_id": "unit-data-snapshot",
        "sources": [
            {"name": "daily_price", "source": "unit_test"},
            {"name": "financial_indicator", "source": "unit_test"},
        ],
        "feature_bundle": {
            "close": 1520.0,
            "pe_ttm": 28.4,
            "raw_response": "must_not_leak",
        },
        "missing_fields": [],
    }


def _entity_relation_bundle() -> dict[str, object]:
    return {
        "schema_version": "entity_relation_bundle_v1",
        "agent_id": "entity_relation_extractor",
        "external_agent_id": "entity_relation_agent",
        "legacy_agent_id": "a15_entity_relation_extraction",
        "status": "ok",
        "target": "600519.SH",
        "as_of": "2026-06-05",
        "data_as_of": "2026-06-05",
        "entities": [
            {"id": "stock:600519.SH", "name": "贵州茅台", "type": "company"},
            {"id": "industry:baijiu", "name": "白酒", "type": "industry"},
        ],
        "relations": [
            {
                "source": "stock:600519.SH",
                "target": "industry:baijiu",
                "type": "belongs_to",
            }
        ],
        "sources": [{"name": "unit_relation_extractor"}],
        "notes": ["raw_response should not leak"],
    }


def _compute_envelope(agent_id: str, external_agent_id: str, tool_result: dict[str, object]):
    return {
        "schema_version": "external_agent_compute_v0",
        "agent_id": agent_id,
        "external_agent_id": external_agent_id,
        "status": "ok",
        "tool_result": tool_result,
    }


def test_context_external_compute_demo_defaults_off_and_env(monkeypatch) -> None:
    monkeypatch.delenv("ENABLE_EXTERNAL_COMPUTE_DEMO", raising=False)
    monkeypatch.delenv("EXTERNAL_COMPUTE_DEMO_ALLOWLIST", raising=False)
    monkeypatch.delenv("EXTERNAL_COMPUTE_DEMO_TIMEOUT_SECONDS", raising=False)

    context = Context()

    assert context.enable_external_compute_demo is False
    assert context.external_compute_demo_allowlist == ()
    assert context.external_compute_demo_timeout_seconds == 20.0

    monkeypatch.setenv("ENABLE_EXTERNAL_COMPUTE_DEMO", "1")
    monkeypatch.setenv(
        "EXTERNAL_COMPUTE_DEMO_ALLOWLIST",
        "value_ml_valuation, risk_identification",
    )
    monkeypatch.setenv("EXTERNAL_COMPUTE_DEMO_TIMEOUT_SECONDS", "7.5")

    context = Context()

    assert context.enable_external_compute_demo is True
    assert context.external_compute_demo_allowlist == (
        "value_ml_valuation",
        "risk_identification",
    )
    assert context.external_compute_demo_timeout_seconds == 7.5


def test_normalize_demo_allowlist_dedupes_and_strips() -> None:
    assert normalize_demo_allowlist(" a, b, a ,,") == ("a", "b")
    assert normalize_demo_allowlist(["a", "b", "a"]) == ("a", "b")
    assert normalize_demo_allowlist(None) == ()


def test_demo_entry_rejects_non_loopback_and_invoke_path() -> None:
    bad_host = ExternalComputeDemoEntry(
        agent_id="value_ml_valuation",
        base_url="http://192.168.0.10:10001",
        compute_path=COMPUTE_PATH,
        expected_payload="agent_conclusion_v1",
        dimension="value",
        external_agent_id="valuation_ml",
    )
    valid, reason = validate_demo_entry(bad_host)
    assert not valid
    assert reason == "non_loopback_host"

    bad_path = ExternalComputeDemoEntry(
        agent_id="value_ml_valuation",
        base_url="http://127.0.0.1:10001",
        compute_path="/v1/agent/invoke",
        expected_payload="agent_conclusion_v1",
        dimension="value",
        external_agent_id="valuation_ml",
    )
    valid, reason = validate_demo_entry(bad_path)
    assert not valid
    assert reason == "compute_path_not_allowed"


def test_demo_base_url_env_override_is_loopback_only(monkeypatch) -> None:
    import react_agent.fixed_dag_external_compute_bridge as bridge

    monkeypatch.setenv(
        "EXTERNAL_COMPUTE_DEMO_URL_VALUE_COMPOSITE",
        "http://127.0.0.1:19015",
    )
    reloaded = importlib.reload(bridge)
    entry = reloaded.DEMO_COMPUTE_SERVICE_REGISTRY["value_composite"]

    assert entry.base_url == "http://127.0.0.1:19015"
    assert reloaded.validate_demo_entry(entry) == (True, "ok")
    monkeypatch.delenv("EXTERNAL_COMPUTE_DEMO_URL_VALUE_COMPOSITE", raising=False)
    importlib.reload(reloaded)


def test_build_external_compute_request_uses_compute_only_contract() -> None:
    entry = DEMO_COMPUTE_SERVICE_REGISTRY["value_ml_valuation"]
    agent_task = build_agent_task(
        "value_ml_valuation",
        question="请分析 600519.SH",
        as_of="2026-06-05",
    )
    request = build_external_compute_request(
        entry,
        question="请分析 600519.SH",
        as_of="2026-06-05",
        request_id="unit-request",
        agent_task=agent_task,
    )

    assert request["schema_version"] == "external_agent_request_v0"
    assert request["agent_id"] == "value_ml_valuation"
    assert request["external_agent_id"] == "valuation_ml"
    assert request["target"] == "600519.SH"
    assert request["options"]["allow_llm"] is False
    assert request["options"]["return_tool_result"] is True
    assert request["agent_task"]["schema"] == "agent_task_v1"
    assert request["context"]["agent_task"]["agent_id"] == "value_ml_valuation"
    assert request["context"]["task_instruction"] == agent_task["task_instruction"]
    assert entry.compute_path == "/v1/agent/compute"
    assert "/v1/agent/invoke" not in json.dumps(request).lower()


def test_build_external_compute_request_includes_safe_upstream_outputs() -> None:
    entry = DEMO_COMPUTE_SERVICE_REGISTRY["value_composite"]
    agent_task = build_agent_task(
        "value_composite",
        question="请分析 600519.SH",
        as_of="2026-06-05",
    )
    upstream_outputs = {
        "value_ml_valuation": {
            "schema": "conclusion_object_v1",
            "schema_version": "conclusion_object_v1",
            "agent_id": "value_ml_valuation",
            "dimension": "value",
            "status": "complete",
            "stance": 0.2,
            "confidence": 0.7,
            "summary": "ML 估值偏正面",
            "evidence": [
                {
                    "fact": "安全证据",
                    "source": "unit_test",
                    "as_of": "2026-06-05",
                    "data_as_of": "2026-06-05",
                    "raw_response": "must_not_leak",
                }
            ],
            "raw_response": "must_not_leak",
            "traceback": "must_not_leak",
        }
    }

    request = build_external_compute_request(
        entry,
        question="请分析 600519.SH",
        as_of="2026-06-05",
        request_id="unit-request",
        agent_task=agent_task,
        upstream_outputs=upstream_outputs,
    )
    upstream = request["context"]["upstream_outputs"]["value_ml_valuation"]
    rendered = json.dumps(request, ensure_ascii=False).lower()

    assert upstream["summary"] == "ML 估值偏正面"
    assert upstream["evidence"][0]["fact"] == "安全证据"
    assert request["context"]["upstream_output_schema"] == "fixed_dag_mapped_outputs_v1"
    assert "must_not_leak" not in rendered
    assert "raw_response" not in rendered
    assert "traceback" not in rendered


def test_fake_l2_external_compute_maps_to_conclusion_object() -> None:
    entry = DEMO_COMPUTE_SERVICE_REGISTRY["value_ml_valuation"]
    calls = []

    def transport(sent_entry, request, timeout):
        calls.append((sent_entry, request, timeout))
        return _compute_envelope(
            "value_ml_valuation",
            "valuation_ml",
            _agent_conclusion(),
        )

    result = invoke_external_compute(
        entry,
        question="q",
        as_of="2026-06-05",
        request_id="unit-l2",
        timeout_seconds=3,
        transport=transport,
    )

    assert result["status"] == "pass"
    assert result["mapped"]["schema"] == "conclusion_object_v1"
    assert result["mapped"]["agent_id"] == "value_ml_valuation"
    assert calls[0][0].compute_path == "/v1/agent/compute"


def test_fake_l1_data_external_compute_maps_to_data_bundle() -> None:
    entry = DEMO_COMPUTE_SERVICE_REGISTRY["financial_data_service"]

    def transport(_entry, _request, _timeout):
        return _compute_envelope(
            "financial_data_service",
            "financial_data_service",
            _data_bundle(),
        )

    result = invoke_external_compute(
        entry,
        question="请分析 600519.SH",
        as_of="2026-06-05",
        request_id="unit-l1-data",
        timeout_seconds=3,
        transport=transport,
    )
    rendered = json.dumps(result, ensure_ascii=False).lower()

    assert result["status"] == "pass"
    assert result["mapped"]["schema"] == "data_bundle_v1"
    assert result["mapped"]["status"] == "complete"
    assert result["mapped"]["sources"]
    assert "raw_response" not in rendered
    assert "must_not_leak" not in rendered


def test_fake_l1_entity_external_compute_maps_to_entity_relation_bundle() -> None:
    entry = DEMO_COMPUTE_SERVICE_REGISTRY["entity_relation_extractor"]

    def transport(_entry, _request, _timeout):
        return _compute_envelope(
            "entity_relation_extractor",
            "entity_relation_agent",
            _entity_relation_bundle(),
        )

    result = invoke_external_compute(
        entry,
        question="请分析贵州茅台",
        as_of="2026-06-05",
        request_id="unit-l1-entity",
        timeout_seconds=3,
        transport=transport,
    )
    rendered = json.dumps(result, ensure_ascii=False).lower()

    assert result["status"] == "pass"
    assert result["mapped"]["schema"] == "entity_relation_bundle_v1"
    assert result["mapped"]["status"] == "complete"
    assert len(result["mapped"]["entities"]) == 2
    assert len(result["mapped"]["relations"]) == 1
    assert "raw_response" not in rendered


def test_fake_l3_external_compute_maps_to_dimension_result() -> None:
    entry = DEMO_COMPUTE_SERVICE_REGISTRY["value_composite"]

    def transport(_entry, _request, _timeout):
        return _compute_envelope(
            "value_composite",
            "composite_valuation",
            _dimension_conclusion(),
        )

    result = invoke_external_compute(
        entry,
        question="q",
        as_of="2026-06-05",
        request_id="unit-l3",
        timeout_seconds=3,
        transport=transport,
    )

    assert result["status"] == "pass"
    assert result["mapped"]["schema"] == "dimension_composite_result_v1"
    assert result["mapped"]["agent_id"] == "value_composite"


def test_invoke_external_compute_sends_upstream_outputs_to_l3() -> None:
    entry = DEMO_COMPUTE_SERVICE_REGISTRY["value_composite"]
    captured = {}

    def transport(_entry, request, _timeout):
        captured["request"] = request
        return _compute_envelope(
            "value_composite",
            "composite_valuation",
            _dimension_conclusion(),
        )

    result = invoke_external_compute(
        entry,
        question="q",
        as_of="2026-06-05",
        request_id="unit-l3",
        timeout_seconds=3,
        upstream_outputs={
            "value_ml_valuation": {
                "schema": "conclusion_object_v1",
                "agent_id": "value_ml_valuation",
                "dimension": "value",
                "status": "complete",
                "stance": 0.2,
                "confidence": 0.7,
                "summary": "ML 估值偏正面",
            }
        },
        transport=transport,
    )

    assert result["status"] == "pass"
    assert "upstream_outputs" in captured["request"]["context"]


def test_adapter_failure_returns_controlled_result_without_raw_leakage() -> None:
    entry = DEMO_COMPUTE_SERVICE_REGISTRY["value_ml_valuation"]

    def transport(_entry, _request, _timeout):
        return _compute_envelope(
            "value_ml_valuation",
            "valuation_ml",
            {
                "schema_version": "unsupported_schema",
                "raw_response": "secret traceback",
            },
        )

    result = invoke_external_compute(
        entry,
        question="q",
        as_of="2026-06-05",
        request_id="unit-failure",
        timeout_seconds=3,
        transport=transport,
    )

    assert result["status"] == "failed"
    rendered = json.dumps(result, ensure_ascii=False).lower()
    assert "adapter_mapping_failed" in rendered
    assert "secret" not in rendered
    assert "traceback" not in rendered
    assert "raw_response" not in rendered


def test_run_external_compute_for_selected_plan_only_calls_selected_allowlisted_agent() -> None:
    intent = build_route_intent(
        task_type="general",
        selected_dimensions=["value"],
        selected_agents=["value_ml_valuation"],
        route_confidence=0.7,
        fallback_reason="fallback to full DAG",
    )
    plan = compile_selected_fixed_dag_plan(intent, user_text="q", as_of="2026-06-05")
    called = []

    def transport(entry, _request, _timeout):
        called.append(entry.agent_id)
        return _compute_envelope(
            "value_ml_valuation",
            "valuation_ml",
            _agent_conclusion(),
        )

    result = run_external_compute_for_plan(
        plan,
        question="q",
        as_of="2026-06-05",
        context=Context(
            enable_external_compute_demo=True,
            external_compute_demo_allowlist=(
                "value_ml_valuation",
                "value_meta_valuation",
            ),
        ),
        l2_conclusions={"value_ml_valuation": {}},
        stages=("l2_analysis",),
        transport=transport,
    )

    assert called == ["value_ml_valuation"]
    assert result["mapped_agents"] == ["value_ml_valuation"]
    assert result["l2_conclusions"]["value_ml_valuation"]["schema"] == "conclusion_object_v1"


def test_run_external_compute_for_plan_updates_l1_bundles_before_l2() -> None:
    plan = compile_selected_fixed_dag_plan(
        build_route_intent(
            task_type="general",
            selected_dimensions=["value"],
            selected_agents=["value_ml_valuation"],
            route_confidence=0.7,
            fallback_reason="fallback to full DAG",
        ),
        user_text="请分析 600519.SH",
        as_of="2026-06-05",
    )
    called = []

    def transport(entry, _request, _timeout):
        called.append(entry.agent_id)
        if entry.agent_id == "financial_data_service":
            return _compute_envelope(
                "financial_data_service",
                "financial_data_service",
                _data_bundle(),
            )
        if entry.agent_id == "entity_relation_extractor":
            return _compute_envelope(
                "entity_relation_extractor",
                "entity_relation_agent",
                _entity_relation_bundle(),
            )
        raise AssertionError(f"unexpected agent {entry.agent_id}")

    result = run_external_compute_for_plan(
        plan,
        question="请分析 600519.SH",
        as_of="2026-06-05",
        context=Context(
            enable_external_compute_demo=True,
            external_compute_demo_allowlist=(
                "financial_data_service",
                "entity_relation_extractor",
            ),
        ),
        data_bundle={"schema": "data_bundle_v1", "schema_version": "data_bundle_v1"},
        entity_relation_bundle={
            "schema": "entity_relation_bundle_v1",
            "schema_version": "entity_relation_bundle_v1",
        },
        l2_conclusions={},
        stages=("evidence",),
        transport=transport,
    )

    assert called == ["financial_data_service", "entity_relation_extractor"]
    assert result["mapped_agents"] == [
        "financial_data_service",
        "entity_relation_extractor",
    ]
    assert result["data_bundle"]["status"] == "complete"
    assert result["data_bundle"]["sources"]
    assert result["entity_relation_bundle"]["status"] == "complete"
    assert len(result["entity_relation_bundle"]["entities"]) == 2
