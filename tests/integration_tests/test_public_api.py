import asyncio
import json
from types import TracebackType
from typing import Any

import httpx

from react_agent import public_api
from react_agent.context import Context
from react_agent.fixed_dag_contracts import RESET_RUNTIME_AGENT_IDS
from react_agent.public_contracts import (
    AnswerCardModel,
    CheckpointerStatus,
    DagStepModel,
    DimensionGroupModel,
    PublicTurn,
    ReadinessSurface,
    RunStartedEvent,
    RunStartedEventData,
    StreamErrorEventData,
    StructuredInputModel,
    WorkflowModel,
    WorkflowProvenanceModel,
    WorkflowSnapshotEvent,
    WorkflowSnapshotEventData,
    WorkflowStageEvent,
    WorkflowStageEventData,
    WorkflowStageModel,
    WorkflowStageProgressModel,
)
from react_agent.public_guardrails import (
    acquire_stream_slot,
    release_stream_slot,
    reset_public_guardrail_state,
)
from react_agent.public_mapping import (
    build_new_thread,
    compose_structured_input_text,
    replay_messages,
)
from react_agent.public_runtime import (
    PreparedPublicTurnInvoke,
    PublicRuntimeUnavailable,
    RuntimeReadinessProbe,
    StreamPublicTurnCompleted,
    prepare_public_turn_invoke,
    probe_public_runtime,
)
from react_agent.public_store import PublicThreadStore


def setup_function() -> None:
    reset_public_guardrail_state()


def teardown_function() -> None:
    reset_public_guardrail_state()


def _workflow(continuity_mode: str = "replay") -> WorkflowModel:
    return WorkflowModel(
        schema="workflow_snapshot_v2",
        planId="reset-fixed-dag-plan-v1",
        stages=[
            WorkflowStageModel(key="planning", title="Planning", stepIds=["route_planner"]),
            WorkflowStageModel(key="evidence", title="Evidence", stepIds=["financial_data_service"]),
            WorkflowStageModel(key="l2_analysis", title="L2", stepIds=["l2:value_traditional_valuation"]),
            WorkflowStageModel(key="dimension_composite", title="Composite", stepIds=["dimension:value"]),
            WorkflowStageModel(key="decision", title="Decision", stepIds=["decision_synthesizer"]),
            WorkflowStageModel(key="report", title="Report", stepIds=["report_generator"]),
        ],
        dagSteps=[
            DagStepModel(
                id="route_planner",
                stage="planning",
                agentId="route_planner",
                title="Route planner",
                summary="Fixed DAG planning.",
                status="complete",
            )
        ],
        dimensionGroups=[
            DimensionGroupModel(
                id="market",
                title="Market composite",
                stepIds=["dimension:market"],
                status="pending_implementation",
                summary="Placeholder composite.",
            )
        ],
        currentStage="report",
        completedSteps=["route_planner"],
        executionBatches=[["route_planner"]],
        stepResults={
            "route_planner": {
                "schema_version": "fixed_dag_step_result_v1",
                "step_id": "route_planner",
                "agent_id": "route_planner",
                "stage": "planning",
                "dimension": "l1",
                "status": "complete",
                "depends_on": [],
                "output_ref": "fixed_dag_plan",
                "summary": "Fixed DAG planning completed.",
                "warnings": [],
            }
        },
        finalSource="reset_skeleton",
        provenanceNote="Fixed DAG reset skeleton emitted the public answer.",
        provenance=WorkflowProvenanceModel(
            source="reset_skeleton",
            continuityMode=continuity_mode,  # type: ignore[arg-type]
            providerInvoked=False,
            externalInvoked=False,
            executionStatus="complete",
            fallbackUsed=False,
            limitations=[],
            summary="Fixed DAG reset skeleton emitted the public answer.",
        ),
    )


def _assistant_turn(continuity_mode: str = "replay") -> PublicTurn:
    return PublicTurn(
        id="assistant-test-1",
        role="assistant",
        text="Fixed DAG reset skeleton answer.",
        createdAt="2026-06-04 13:00",
        runId="run-r1b-1234",
        continuityMode=continuity_mode,  # type: ignore[arg-type]
        answerCard=AnswerCardModel(
            answer="Fixed DAG reset skeleton answer.",
            finalSource="reset_skeleton",
            confidence="low",
            citations=[],
            evidenceCards=[],
            evidenceCount=0,
        ),
        workflow=_workflow(continuity_mode),
    )


def _selected_assistant_turn(continuity_mode: str = "replay") -> PublicTurn:
    turn = _assistant_turn(continuity_mode)
    assert turn.workflow is not None
    turn.workflow.dimensionGroups = [
        DimensionGroupModel(
            id="value",
            title="Value composite",
            stepIds=["dimension:value"],
            status="pending_implementation",
            summary="Selected value dimension.",
        )
    ]
    assert turn.workflow.provenance is not None
    turn.workflow.provenance.selectedRoutingRequested = True
    turn.workflow.provenance.selectedRoutingFallback = False
    turn.workflow.provenance.routeGranularity = "dimension"
    turn.workflow.provenance.selectedDimensions = ["value"]
    turn.workflow.provenance.expandedAgentCount = 8
    turn.workflow.provenance.providerRouterEnabled = False
    turn.workflow.provenance.providerRouterInvoked = False
    return turn


def _probe(continuity_mode: str = "replay") -> RuntimeReadinessProbe:
    return RuntimeReadinessProbe(
        continuity_mode=continuity_mode,  # type: ignore[arg-type]
        runtime=ReadinessSurface(status="ready", code="runtime_ready"),
        provider_env=ReadinessSurface(status="missing", code="provider_env_missing_optional_for_reset"),
        search_env=ReadinessSurface(status="missing", code="search_env_missing_optional_for_reset"),
        checkpointer=CheckpointerStatus(
            enabled=continuity_mode == "persistent",
            mode="memory" if continuity_mode == "persistent" else "none",
            status="enabled" if continuity_mode == "persistent" else "disabled",
            code="checkpointer_enabled" if continuity_mode == "persistent" else "checkpointer_disabled",
            hint=None,
        ),
        overall_status="ready" if continuity_mode == "persistent" else "degraded",
        graph_module=None,
    )


def _structured_input(**overrides) -> StructuredInputModel:
    payload = {
        "task": "Please summarize the investment committee request.",
        "context": "Background materials already cover public filings.",
        "materials": ["Material one", "Material two"],
        "urlReferences": [],
        "constraints": "Use only public information.",
        "outputPreference": "Short conclusion first.",
    }
    payload.update(overrides)
    return StructuredInputModel(**payload)


class _AsgiStreamContext:
    def __init__(self, response: httpx.Response) -> None:
        self.response = response

    def __enter__(self) -> httpx.Response:
        return self.response

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        asyncio.run(self.response.aclose())


class _AsgiTestClient:
    def __init__(self, app: Any) -> None:
        self.app = app

    async def _request_async(self, method: str, url: str, **kwargs: Any) -> httpx.Response:
        transport = httpx.ASGITransport(app=self.app)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://testserver",
        ) as client:
            return await client.request(method, url, **kwargs)

    def request(self, method: str, url: str, **kwargs: Any) -> httpx.Response:
        return asyncio.run(self._request_async(method, url, **kwargs))

    def get(self, url: str, **kwargs: Any) -> httpx.Response:
        return self.request("GET", url, **kwargs)

    def post(self, url: str, **kwargs: Any) -> httpx.Response:
        return self.request("POST", url, **kwargs)

    def delete(self, url: str, **kwargs: Any) -> httpx.Response:
        return self.request("DELETE", url, **kwargs)

    def stream(self, method: str, url: str, **kwargs: Any) -> _AsgiStreamContext:
        return _AsgiStreamContext(self.request(method, url, **kwargs))


def _configure_test_app(tmp_path, monkeypatch, *, continuity_mode: str) -> _AsgiTestClient:
    reset_public_guardrail_state()
    store = PublicThreadStore(tmp_path / "threads.json")
    monkeypatch.setattr(public_api, "store", store)
    monkeypatch.setattr(public_api, "_readiness_probe", lambda: _probe(continuity_mode))

    async def _fake_invoke_public_turn(*, thread_id, history_turns, user_text, context=None):
        assert thread_id
        assert user_text
        return _assistant_turn(continuity_mode), continuity_mode

    monkeypatch.setattr(public_api, "invoke_public_turn", _fake_invoke_public_turn)
    return _AsgiTestClient(public_api.app)


def test_public_thread_store_repairs_invalid_legacy_thread_entries(tmp_path):
    path = tmp_path / "threads.json"
    valid = build_new_thread("thread-valid", "replay")
    legacy_invalid = {
        "thread": {
            "id": "thread-invalid",
            "title": "Legacy invalid thread",
        },
        "turns": [{"role": "assistant", "text": "legacy missing required fields"}],
    }
    path.write_text(
        json.dumps(
            {
                "version": 1,
                "threads": {
                    "thread-valid": valid.model_dump(mode="json"),
                    "thread-invalid": legacy_invalid,
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    store = PublicThreadStore(path)
    details = store.list_threads()

    assert [detail.thread.id for detail in details] == ["thread-valid"]
    repaired = json.loads(path.read_text(encoding="utf-8"))
    assert set(repaired["threads"]) == {"thread-valid"}
    assert "thread-invalid" not in repaired["threads"]


def _stream_lines(response) -> list[dict]:
    return [json.loads(line) for line in response.iter_lines() if line]


def test_health_contract(tmp_path, monkeypatch):
    client = _configure_test_app(tmp_path, monkeypatch, continuity_mode="replay")
    response = client.get("/api/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["apiVersion"] == "phase-r3"
    assert payload["publicApiContractVersion"] == "public_api_contract_v5"
    assert payload["routingRequestSupported"] is True
    assert payload["selectedRoutingRequestSchema"] == "routing.mode.selected"
    assert payload["selectedRoutingDefault"] is False
    assert payload["defaultRoutingMode"] == "full_dag"
    assert payload["selectedRoutingRouterMode"] == "deterministic"
    assert payload["llmDimensionRouterEnabled"] is False
    assert payload["computeRegistryVersion"] == "fixed_dag_compute_registry_v1"
    assert payload["computeRegistryAgentCount"] == 26
    assert payload["processStartTime"]
    assert isinstance(payload["processUptimeSeconds"], int)
    assert payload["sourceVersionMarker"] == "fixed_dag_public_api_llm_router"
    assert payload["overallStatus"] == "degraded"
    assert payload["providerEnv"]["code"] == "provider_env_missing_optional_for_reset"
    assert payload["searchEnv"]["code"] == "search_env_missing_optional_for_reset"


def test_public_api_default_trial_guardrails_allow_normal_request(tmp_path, monkeypatch):
    client = _configure_test_app(tmp_path, monkeypatch, continuity_mode="replay")
    thread_id = client.post("/api/threads", json={}).json()["thread"]["id"]
    response = client.post(
        f"/api/threads/{thread_id}/messages",
        json={"text": "A normal short public trial request."},
    )
    assert response.status_code == 200
    assert response.json()["assistantTurn"]["role"] == "assistant"


def test_public_api_rejects_message_over_configured_length(tmp_path, monkeypatch):
    monkeypatch.setenv("PUBLIC_API_MAX_MESSAGE_CHARS", "10")
    client = _configure_test_app(tmp_path, monkeypatch, continuity_mode="replay")
    thread_id = client.post("/api/threads", json={}).json()["thread"]["id"]
    response = client.post(f"/api/threads/{thread_id}/messages", json={"text": "x" * 11})
    assert response.status_code == 413
    assert response.json()["detail"]["code"] == "message_too_long"


def test_public_api_rate_limit_returns_safe_429(tmp_path, monkeypatch):
    monkeypatch.setenv("PUBLIC_API_RATE_LIMIT_PER_MINUTE", "1")
    client = _configure_test_app(tmp_path, monkeypatch, continuity_mode="replay")
    assert client.get("/api/threads").status_code == 200
    second = client.get("/api/threads")
    assert second.status_code == 429
    assert second.json()["detail"]["code"] == "public_rate_limit_exceeded"
    assert "Traceback" not in second.text


def test_public_api_health_is_not_blocked_by_rate_limit(tmp_path, monkeypatch):
    monkeypatch.setenv("PUBLIC_API_RATE_LIMIT_PER_MINUTE", "1")
    client = _configure_test_app(tmp_path, monkeypatch, continuity_mode="replay")
    assert client.get("/api/health").status_code == 200
    assert client.get("/api/health").status_code == 200


def test_public_api_stream_active_limit_returns_safe_429(tmp_path, monkeypatch):
    monkeypatch.setenv("PUBLIC_API_RATE_LIMIT_PER_MINUTE", "0")
    monkeypatch.setenv("PUBLIC_API_MAX_ACTIVE_STREAMS_PER_IP", "1")
    client = _configure_test_app(tmp_path, monkeypatch, continuity_mode="replay")
    thread_id = client.post("/api/threads", json={}).json()["thread"]["id"]
    acquire_stream_slot("127.0.0.1")
    try:
        response = client.post(
            f"/api/threads/{thread_id}/messages/stream",
            json={"text": "Stream while another stream is active."},
        )
    finally:
        release_stream_slot("127.0.0.1")
    assert response.status_code == 429
    assert response.json()["detail"]["code"] == "public_stream_limit_exceeded"


def test_public_runtime_allows_missing_provider_and_search_for_reset(monkeypatch):
    for key in ("OPENAI_API_KEY", "ROUTER_OPENAI_API_KEY", "BASELINE_OPENAI_API_KEY", "GOOGLE_API_KEY", "TAVILY_API_KEY"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.delenv("SEARCH_REQUIRED", raising=False)
    probe = probe_public_runtime()
    assert probe.provider_env.code == "provider_env_missing_optional_for_reset"
    assert probe.search_env.code == "search_env_missing_optional_for_reset"
    prepared = prepare_public_turn_invoke(thread_id="thread-reset", history_turns=[], user_text="hello")
    assert prepared.continuity_mode in {"replay", "persistent"}


def test_agent_catalog_contract(tmp_path, monkeypatch):
    client = _configure_test_app(tmp_path, monkeypatch, continuity_mode="replay")
    response = client.get("/api/agents")
    assert response.status_code == 200
    payload = response.json()
    assert payload["totals"]["configCount"] == 27
    assert payload["totals"]["runtimeCount"] == 27
    assert payload["totals"]["disabledIds"] == []
    assert set(payload) == {"totals", "layers", "disabledAgents"}
    assert set(payload["totals"]) == {"configCount", "runtimeCount", "disabledIds"}
    assert [layer["layer"] for layer in payload["layers"]] == ["L1", "L2", "L3", "L4"]
    assert [len(layer["agents"]) for layer in payload["layers"]] == [3, 18, 4, 2]
    agents = [agent for layer in payload["layers"] for agent in layer["agents"]]
    ids = [agent["id"] for agent in agents]
    assert ids == list(RESET_RUNTIME_AGENT_IDS)
    for agent in agents:
        assert set(agent) == {
            "id",
            "name",
            "description",
            "capabilities",
            "layer",
            "team",
            "roleType",
            "defaultEnabled",
        }
    assert all(not agent_id.startswith("a") or not agent_id[1:3].isdigit() for agent_id in ids)
    assert "value_financial_analysis" not in ids
    sentiment = next(agent for agent in agents if agent["id"] == "sentiment_company_radar")
    assert sentiment["layer"] == "L2"
    assert sentiment["team"] == "market"
    assert "pending_implementation" in sentiment["capabilities"]
    assert payload["disabledAgents"] == []
    for forbidden in [
        "messages",
        "analyst_results",
        "ephemeral_results",
        "manager_assignment",
        "tool_call",
        "runtimeBinding",
        "legacyAgentId",
        "externalAgentId",
        "endpoint",
        "envVar",
    ]:
        assert forbidden not in response.text


def test_thread_lifecycle_and_fixed_workflow_contract(tmp_path, monkeypatch):
    client = _configure_test_app(tmp_path, monkeypatch, continuity_mode="replay")
    created = client.post("/api/threads", json={}).json()
    thread_id = created["thread"]["id"]
    assert created["thread"]["phase"] == "固定研判流程"
    assert created["thread"]["finalSource"] == "reset_skeleton"

    response = client.post(
        f"/api/threads/{thread_id}/messages",
        json={"text": "Please summarize the public answer."},
    )
    assert response.status_code == 200
    payload = response.json()
    workflow = payload["assistantTurn"]["workflow"]
    assert payload["assistantTurn"]["answerCard"]["finalSource"] == "reset_skeleton"
    assert workflow["schema"] == "workflow_snapshot_v2"
    assert workflow["finalSource"] == "reset_skeleton"
    assert workflow["currentStage"] == "report"
    assert "dagSteps" in workflow
    assert workflow["executionBatches"] == [["route_planner"]]
    assert workflow["stepResults"]["route_planner"]["status"] == "complete"
    for forbidden in ["layerMode", "fusionSteps", "layerPlan", "messages", "analyst_results"]:
        assert forbidden not in response.text


def test_delete_thread_removes_only_target_thread(tmp_path, monkeypatch):
    client = _configure_test_app(tmp_path, monkeypatch, continuity_mode="replay")
    first_id = client.post("/api/threads", json={}).json()["thread"]["id"]
    second_id = client.post("/api/threads", json={}).json()["thread"]["id"]
    assert client.delete(f"/api/threads/{first_id}").status_code == 204
    list_after = client.get("/api/threads").json()
    assert {thread["id"] for thread in list_after["threads"]} == {second_id}
    assert client.get(f"/api/threads/{first_id}").status_code == 404


def test_clear_thread_messages_preserves_thread_and_does_not_affect_others(tmp_path, monkeypatch):
    client = _configure_test_app(tmp_path, monkeypatch, continuity_mode="replay")
    first_id = client.post("/api/threads", json={"title": "Keep title"}).json()["thread"]["id"]
    second_id = client.post("/api/threads", json={"title": "Other thread"}).json()["thread"]["id"]
    assert client.post(f"/api/threads/{first_id}/messages", json={"text": "one"}).status_code == 200
    assert client.post(f"/api/threads/{second_id}/messages", json={"text": "two"}).status_code == 200
    clear_response = client.delete(f"/api/threads/{first_id}/messages")
    assert clear_response.status_code == 200
    assert clear_response.json()["thread"]["finalSource"] == "reset_skeleton"
    assert clear_response.json()["turns"] == []
    assert len(client.get(f"/api/threads/{second_id}").json()["turns"]) == 2


def test_send_message_accepts_structured_input_and_replay_uses_text(tmp_path, monkeypatch):
    client = _configure_test_app(tmp_path, monkeypatch, continuity_mode="replay")
    thread_id = client.post("/api/threads", json={}).json()["thread"]["id"]
    structured_input = _structured_input()
    canonical_text = compose_structured_input_text(structured_input)
    response = client.post(
        f"/api/threads/{thread_id}/messages",
        json={"text": canonical_text, "structuredInput": structured_input.model_dump(mode="json")},
    )
    assert response.status_code == 200
    user_turn = response.json()["turns"][0]
    assert user_turn["text"] == canonical_text
    assert user_turn["structuredInput"]["task"] == structured_input.task
    turns = [PublicTurn.model_validate(item) for item in response.json()["turns"]]
    assert replay_messages(turns, "Pending follow-up")[-1] == ("user", "Pending follow-up")


def test_send_message_omitted_and_null_routing_keep_default_context(tmp_path, monkeypatch):
    captured_contexts: list[Context | None] = []
    store = PublicThreadStore(tmp_path / "threads.json")
    monkeypatch.setattr(public_api, "store", store)
    monkeypatch.setattr(public_api, "_readiness_probe", lambda: _probe("replay"))

    async def _fake_invoke_public_turn(*, thread_id, history_turns, user_text, context=None):
        captured_contexts.append(context)
        return _assistant_turn("replay"), "replay"

    monkeypatch.setattr(public_api, "invoke_public_turn", _fake_invoke_public_turn)
    client = _AsgiTestClient(public_api.app)
    thread_id = client.post("/api/threads", json={}).json()["thread"]["id"]

    omitted = client.post(
        f"/api/threads/{thread_id}/messages",
        json={"text": "Default routing request."},
    )
    null_routing = client.post(
        f"/api/threads/{thread_id}/messages",
        json={"text": "Null routing request.", "routing": None},
    )

    assert omitted.status_code == 200
    assert null_routing.status_code == 200
    assert captured_contexts == [None, None]


def test_send_message_selected_routing_passes_selected_context(tmp_path, monkeypatch):
    monkeypatch.delenv("PUBLIC_SELECTED_ROUTING_ENABLE_LLM_ROUTER", raising=False)
    monkeypatch.setenv("ENABLE_LLM_DIMENSION_ROUTER", "1")
    captured: dict[str, Any] = {}
    store = PublicThreadStore(tmp_path / "threads.json")
    monkeypatch.setattr(public_api, "store", store)
    monkeypatch.setattr(public_api, "_readiness_probe", lambda: _probe("replay"))

    async def _fake_invoke_public_turn(*, thread_id, history_turns, user_text, context=None):
        captured["context"] = context
        return _selected_assistant_turn("replay"), "replay"

    monkeypatch.setattr(public_api, "invoke_public_turn", _fake_invoke_public_turn)
    client = _AsgiTestClient(public_api.app)
    thread_id = client.post("/api/threads", json={}).json()["thread"]["id"]

    response = client.post(
        f"/api/threads/{thread_id}/messages",
        json={"text": "Run selected routing.", "routing": {"mode": "selected"}},
    )

    assert response.status_code == 200
    assert isinstance(captured["context"], Context)
    assert captured["context"].enable_selected_routing is True
    assert captured["context"].enable_llm_dimension_router is False
    assert captured["context"].llm_dimension_router_mode == ""
    assert captured["context"].enable_external_compute_demo is False
    provenance = response.json()["assistantTurn"]["workflow"]["provenance"]
    assert provenance["selectedRoutingRequested"] is True
    assert provenance["selectedRoutingFallback"] is False
    assert provenance["selectedDimensions"] == ["value"]
    assert provenance["providerRouterEnabled"] is False
    assert provenance["providerRouterInvoked"] is False


def test_send_message_selected_routing_can_enable_real_llm_router_context(tmp_path, monkeypatch):
    monkeypatch.setenv("PUBLIC_SELECTED_ROUTING_ENABLE_LLM_ROUTER", "1")
    captured: dict[str, Any] = {}
    store = PublicThreadStore(tmp_path / "threads.json")
    monkeypatch.setattr(public_api, "store", store)
    monkeypatch.setattr(public_api, "_readiness_probe", lambda: _probe("replay"))

    async def _fake_invoke_public_turn(*, thread_id, history_turns, user_text, context=None):
        captured["context"] = context
        return _selected_assistant_turn("replay"), "replay"

    monkeypatch.setattr(public_api, "invoke_public_turn", _fake_invoke_public_turn)
    client = _AsgiTestClient(public_api.app)
    health_payload = client.get("/api/health").json()
    thread_id = client.post("/api/threads", json={}).json()["thread"]["id"]

    response = client.post(
        f"/api/threads/{thread_id}/messages",
        json={"text": "Run LLM selected routing.", "routing": {"mode": "selected"}},
    )

    assert response.status_code == 200
    assert health_payload["selectedRoutingRouterMode"] == "llm_real"
    assert health_payload["llmDimensionRouterEnabled"] is True
    assert isinstance(captured["context"], Context)
    assert captured["context"].enable_selected_routing is True
    assert captured["context"].enable_llm_dimension_router is True
    assert captured["context"].llm_dimension_router_mode == "real"


def test_send_message_omitted_routing_can_default_to_real_llm_router_context(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setenv("PUBLIC_SELECTED_ROUTING_DEFAULT", "1")
    monkeypatch.setenv("PUBLIC_SELECTED_ROUTING_ENABLE_LLM_ROUTER", "1")
    captured_contexts: list[Context | None] = []
    store = PublicThreadStore(tmp_path / "threads.json")
    monkeypatch.setattr(public_api, "store", store)
    monkeypatch.setattr(public_api, "_readiness_probe", lambda: _probe("replay"))

    async def _fake_invoke_public_turn(*, thread_id, history_turns, user_text, context=None):
        captured_contexts.append(context)
        return _selected_assistant_turn("replay"), "replay"

    monkeypatch.setattr(public_api, "invoke_public_turn", _fake_invoke_public_turn)
    client = _AsgiTestClient(public_api.app)
    health_payload = client.get("/api/health").json()
    thread_id = client.post("/api/threads", json={}).json()["thread"]["id"]

    omitted = client.post(
        f"/api/threads/{thread_id}/messages",
        json={"text": "Default should use selected LLM routing."},
    )
    null_routing = client.post(
        f"/api/threads/{thread_id}/messages",
        json={"text": "Null should use selected LLM routing.", "routing": None},
    )

    assert omitted.status_code == 200
    assert null_routing.status_code == 200
    assert health_payload["selectedRoutingDefault"] is True
    assert health_payload["defaultRoutingMode"] == "selected"
    assert health_payload["selectedRoutingRouterMode"] == "llm_real"
    assert len(captured_contexts) == 2
    for context in captured_contexts:
        assert isinstance(context, Context)
        assert context.enable_selected_routing is True
        assert context.enable_llm_dimension_router is True
        assert context.llm_dimension_router_mode == "real"


def test_send_message_selected_routing_endpoint_free_e2e_report(tmp_path, monkeypatch):
    monkeypatch.setenv("DISABLE_EXTERNAL_COMPUTE_DEFAULT", "1")
    monkeypatch.setenv("DISABLE_NON_L4_EXTERNAL_COMPUTE_DEFAULT", "1")
    monkeypatch.setenv("ENABLE_EXTERNAL_COMPUTE_DEMO", "0")
    monkeypatch.setenv("ENABLE_LLM_DIMENSION_ROUTER", "0")
    monkeypatch.delenv("PUBLIC_SELECTED_ROUTING_ENABLE_LLM_ROUTER", raising=False)
    store = PublicThreadStore(tmp_path / "threads.json")
    monkeypatch.setattr(public_api, "store", store)
    monkeypatch.setattr(public_api, "_readiness_probe", lambda: _probe("replay"))
    client = _AsgiTestClient(public_api.app)
    thread_id = client.post("/api/threads", json={}).json()["thread"]["id"]

    response = client.post(
        f"/api/threads/{thread_id}/messages",
        json={
            "text": "Analyze the valuation outlook for 600519.SH.",
            "routing": {"mode": "selected"},
        },
    )

    assert response.status_code == 200
    payload = response.json()
    workflow = payload["assistantTurn"]["workflow"]
    provenance = workflow["provenance"]
    assert provenance["selectedRoutingRequested"] is True
    assert provenance["selectedRoutingFallback"] is False
    assert provenance["selectedDimensions"]
    assert provenance["providerRouterEnabled"] is False
    assert provenance["providerRouterInvoked"] is False
    answer_card = payload["assistantTurn"]["answerCard"]
    assert answer_card["answer"].strip()
    if set(provenance["selectedDimensions"]) != {"value", "market", "risk", "macro"}:
        section_ids = {section["id"] for section in answer_card["sections"]}
        assert "unselected_scope" in section_ids
        assert "用户问题覆盖估值、市场、风险和宏观四个维度" not in answer_card["answer"]
    assert workflow["currentStage"] == "report"
    assert {group["id"] for group in workflow["dimensionGroups"]} <= {"value", "market", "risk", "macro"}
    rendered = json.dumps(payload, ensure_ascii=False)
    for forbidden in ["raw_response", "/v1/agent/invoke", "secret", "Traceback", "chain-of-thought"]:
        assert forbidden not in rendered


def test_send_message_rejects_invalid_routing_value_and_extra_key(tmp_path, monkeypatch):
    client = _configure_test_app(tmp_path, monkeypatch, continuity_mode="replay")
    thread_id = client.post("/api/threads", json={}).json()["thread"]["id"]

    invalid_value = client.post(
        f"/api/threads/{thread_id}/messages",
        json={"text": "Invalid routing.", "routing": {"mode": "full_dag"}},
    )
    extra_key = client.post(
        f"/api/threads/{thread_id}/messages",
        json={"text": "Invalid routing.", "routing": {"mode": "selected", "provider": "fake"}},
    )

    assert invalid_value.status_code == 422
    assert extra_key.status_code == 422


def test_send_message_stream_rejects_invalid_routing_value(tmp_path, monkeypatch):
    client = _configure_test_app(tmp_path, monkeypatch, continuity_mode="replay")
    thread_id = client.post("/api/threads", json={}).json()["thread"]["id"]

    response = client.post(
        f"/api/threads/{thread_id}/messages/stream",
        json={"text": "Invalid stream routing.", "routing": {"mode": "full_dag"}},
    )

    assert response.status_code == 422


def test_send_message_rejects_structured_input_text_mismatch(tmp_path, monkeypatch):
    client = _configure_test_app(tmp_path, monkeypatch, continuity_mode="replay")
    thread_id = client.post("/api/threads", json={}).json()["thread"]["id"]
    response = client.post(
        f"/api/threads/{thread_id}/messages",
        json={
            "text": "Free-form text that does not match the structured input.",
            "structuredInput": _structured_input().model_dump(mode="json"),
        },
    )
    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "structured_input_text_mismatch"


def test_send_message_runtime_failure_contract(tmp_path, monkeypatch):
    store = PublicThreadStore(tmp_path / "threads.json")
    monkeypatch.setattr(public_api, "store", store)
    monkeypatch.setattr(public_api, "_readiness_probe", lambda: _probe("replay"))
    client = _AsgiTestClient(public_api.app)
    thread_id = client.post("/api/threads", json={}).json()["thread"]["id"]

    async def _failing_invoke_public_turn(*, thread_id, history_turns, user_text, context=None):
        raise PublicRuntimeUnavailable(
            "LangGraph runtime is unavailable for public invocation.",
            code="runtime_import_unavailable",
            category="runtime",
        )

    monkeypatch.setattr(public_api, "invoke_public_turn", _failing_invoke_public_turn)
    response = client.post(f"/api/threads/{thread_id}/messages", json={"text": "fail"})
    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "runtime_import_unavailable"
    assert "Traceback" not in response.text


def test_send_message_stream_success_persists_only_final_turns(tmp_path, monkeypatch):
    monkeypatch.setenv("PUBLIC_API_RATE_LIMIT_PER_MINUTE", "0")
    monkeypatch.setenv("PUBLIC_API_MAX_ACTIVE_STREAMS_PER_IP", "1")
    store = PublicThreadStore(tmp_path / "threads.json")
    monkeypatch.setattr(public_api, "store", store)
    monkeypatch.setattr(public_api, "_readiness_probe", lambda: _probe("persistent"))
    prepared = PreparedPublicTurnInvoke(
        continuity_mode="persistent",
        graph_app=object(),
        invoke_input={"messages": [("user", "Stream the final answer.")]},
        invoke_kwargs={"context": object(), "config": {"configurable": {"thread_id": "unused"}}},
    )
    monkeypatch.setattr(public_api, "prepare_public_turn_invoke", lambda **_: prepared)

    async def _fake_stream_public_turn(*, thread_id, user_text, prepared):
        yield RunStartedEvent(
            type="run.started",
            data=RunStartedEventData(threadId=thread_id, continuityMode="persistent"),
        )
        yield WorkflowStageEvent(
            type="workflow.stage",
            data=WorkflowStageEventData(
                stages=[
                    WorkflowStageProgressModel(key="planning", title="Planning", status="completed"),
                    WorkflowStageProgressModel(key="evidence", title="Evidence", status="running"),
                ],
                currentStage="evidence",
            ),
        )
        yield WorkflowSnapshotEvent(
            type="workflow.snapshot",
            data=WorkflowSnapshotEventData(
                workflow=_workflow("persistent"),
                runId="run-stream-1",
                continuityMode="persistent",
            ),
        )
        yield StreamPublicTurnCompleted(
            assistant_turn=_assistant_turn("persistent"),
            continuity_mode="persistent",
        )

    monkeypatch.setattr(public_api, "stream_public_turn", _fake_stream_public_turn)
    client = _AsgiTestClient(public_api.app)
    thread_id = client.post("/api/threads", json={}).json()["thread"]["id"]
    with client.stream(
        "POST",
        f"/api/threads/{thread_id}/messages/stream",
        json={"text": "Stream the final answer."},
    ) as response:
        assert response.status_code == 200
        events = _stream_lines(response)
    assert [event["type"] for event in events] == [
        "run.started",
        "workflow.stage",
        "workflow.snapshot",
        "answer.final",
    ]
    assert events[2]["data"]["workflow"]["schema"] == "workflow_snapshot_v2"
    persisted = store.get_thread(thread_id)
    assert persisted is not None
    assert len(persisted.turns) == 2


def test_send_message_stream_selected_routing_passes_selected_context(tmp_path, monkeypatch):
    monkeypatch.setenv("PUBLIC_API_RATE_LIMIT_PER_MINUTE", "0")
    monkeypatch.delenv("PUBLIC_SELECTED_ROUTING_ENABLE_LLM_ROUTER", raising=False)
    monkeypatch.setenv("ENABLE_LLM_DIMENSION_ROUTER", "1")
    captured: dict[str, Any] = {}
    store = PublicThreadStore(tmp_path / "threads.json")
    monkeypatch.setattr(public_api, "store", store)
    monkeypatch.setattr(public_api, "_readiness_probe", lambda: _probe("replay"))

    def _fake_prepare_public_turn_invoke(**kwargs):
        captured["context"] = kwargs.get("context")
        return PreparedPublicTurnInvoke(
            continuity_mode="replay",
            graph_app=object(),
            invoke_input={"messages": [("user", kwargs["user_text"])]},
            invoke_kwargs={"context": kwargs.get("context")},
        )

    async def _fake_stream_public_turn(*, thread_id, user_text, prepared):
        yield RunStartedEvent(
            type="run.started",
            data=RunStartedEventData(threadId=thread_id, continuityMode="replay"),
        )
        yield StreamPublicTurnCompleted(
            assistant_turn=_assistant_turn("replay"),
            continuity_mode="replay",
        )

    monkeypatch.setattr(public_api, "prepare_public_turn_invoke", _fake_prepare_public_turn_invoke)
    monkeypatch.setattr(public_api, "stream_public_turn", _fake_stream_public_turn)
    client = _AsgiTestClient(public_api.app)
    thread_id = client.post("/api/threads", json={}).json()["thread"]["id"]

    with client.stream(
        "POST",
        f"/api/threads/{thread_id}/messages/stream",
        json={"text": "Stream selected routing.", "routing": {"mode": "selected"}},
    ) as response:
        events = _stream_lines(response)

    assert response.status_code == 200
    assert events[-1]["type"] == "answer.final"
    assert isinstance(captured["context"], Context)
    assert captured["context"].enable_selected_routing is True
    assert captured["context"].enable_llm_dimension_router is False
    assert captured["context"].llm_dimension_router_mode == ""


def test_send_message_stream_omitted_and_null_routing_keep_default_context(tmp_path, monkeypatch):
    monkeypatch.setenv("PUBLIC_API_RATE_LIMIT_PER_MINUTE", "0")
    captured_contexts: list[Context | None] = []
    store = PublicThreadStore(tmp_path / "threads.json")
    monkeypatch.setattr(public_api, "store", store)
    monkeypatch.setattr(public_api, "_readiness_probe", lambda: _probe("replay"))

    def _fake_prepare_public_turn_invoke(**kwargs):
        captured_contexts.append(kwargs.get("context"))
        return PreparedPublicTurnInvoke(
            continuity_mode="replay",
            graph_app=object(),
            invoke_input={"messages": [("user", kwargs["user_text"])]},
            invoke_kwargs={"context": kwargs.get("context")},
        )

    async def _fake_stream_public_turn(*, thread_id, user_text, prepared):
        yield RunStartedEvent(
            type="run.started",
            data=RunStartedEventData(threadId=thread_id, continuityMode="replay"),
        )
        yield StreamPublicTurnCompleted(
            assistant_turn=_assistant_turn("replay"),
            continuity_mode="replay",
        )

    monkeypatch.setattr(public_api, "prepare_public_turn_invoke", _fake_prepare_public_turn_invoke)
    monkeypatch.setattr(public_api, "stream_public_turn", _fake_stream_public_turn)
    client = _AsgiTestClient(public_api.app)
    thread_id = client.post("/api/threads", json={}).json()["thread"]["id"]

    omitted = client.post(
        f"/api/threads/{thread_id}/messages/stream",
        json={"text": "Stream default routing."},
    )
    null_routing = client.post(
        f"/api/threads/{thread_id}/messages/stream",
        json={"text": "Stream null routing.", "routing": None},
    )

    assert omitted.status_code == 200
    assert null_routing.status_code == 200
    assert captured_contexts == [None, None]


def test_send_message_stream_omitted_routing_can_default_to_real_llm_router_context(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setenv("PUBLIC_API_RATE_LIMIT_PER_MINUTE", "0")
    monkeypatch.setenv("PUBLIC_SELECTED_ROUTING_DEFAULT", "1")
    monkeypatch.setenv("PUBLIC_SELECTED_ROUTING_ENABLE_LLM_ROUTER", "1")
    captured_contexts: list[Context | None] = []
    store = PublicThreadStore(tmp_path / "threads.json")
    monkeypatch.setattr(public_api, "store", store)
    monkeypatch.setattr(public_api, "_readiness_probe", lambda: _probe("replay"))

    def _fake_prepare_public_turn_invoke(**kwargs):
        captured_contexts.append(kwargs.get("context"))
        return PreparedPublicTurnInvoke(
            continuity_mode="replay",
            graph_app=object(),
            invoke_input={"messages": [("user", kwargs["user_text"])]},
            invoke_kwargs={"context": kwargs.get("context")},
        )

    async def _fake_stream_public_turn(*, thread_id, user_text, prepared):
        yield RunStartedEvent(
            type="run.started",
            data=RunStartedEventData(threadId=thread_id, continuityMode="replay"),
        )
        yield StreamPublicTurnCompleted(
            assistant_turn=_selected_assistant_turn("replay"),
            continuity_mode="replay",
        )

    monkeypatch.setattr(public_api, "prepare_public_turn_invoke", _fake_prepare_public_turn_invoke)
    monkeypatch.setattr(public_api, "stream_public_turn", _fake_stream_public_turn)
    client = _AsgiTestClient(public_api.app)
    thread_id = client.post("/api/threads", json={}).json()["thread"]["id"]

    with client.stream(
        "POST",
        f"/api/threads/{thread_id}/messages/stream",
        json={"text": "Stream default should use selected LLM routing."},
    ) as response:
        events = _stream_lines(response)

    assert response.status_code == 200
    assert events[-1]["type"] == "answer.final"
    assert len(captured_contexts) == 1
    context = captured_contexts[0]
    assert isinstance(context, Context)
    assert context.enable_selected_routing is True
    assert context.enable_llm_dimension_router is True
    assert context.llm_dimension_router_mode == "real"


def test_send_message_stream_emits_error_and_does_not_persist_failed_turn(tmp_path, monkeypatch):
    store = PublicThreadStore(tmp_path / "threads.json")
    monkeypatch.setattr(public_api, "store", store)
    monkeypatch.setattr(public_api, "_readiness_probe", lambda: _probe("replay"))
    monkeypatch.setattr(
        public_api,
        "prepare_public_turn_invoke",
        lambda **_: PreparedPublicTurnInvoke(
            continuity_mode="replay",
            graph_app=object(),
            invoke_input={"messages": [("user", "Trigger in-stream failure.")]},
            invoke_kwargs={"context": object()},
        ),
    )

    async def _failing_stream_public_turn(*, thread_id, user_text, prepared):
        yield RunStartedEvent(
            type="run.started",
            data=RunStartedEventData(threadId=thread_id, continuityMode="replay"),
        )
        raise PublicRuntimeUnavailable(
            "LangGraph 运行时在生成公开回答前调用失败。",
            code="runtime_invoke_unavailable",
            category="runtime",
        )

    monkeypatch.setattr(public_api, "stream_public_turn", _failing_stream_public_turn)
    client = _AsgiTestClient(public_api.app)
    thread_id = client.post("/api/threads", json={}).json()["thread"]["id"]
    with client.stream(
        "POST",
        f"/api/threads/{thread_id}/messages/stream",
        json={"text": "Trigger in-stream failure."},
    ) as response:
        events = _stream_lines(response)
    assert [event["type"] for event in events] == ["run.started", "error"]
    error_event = StreamErrorEventData.model_validate(events[-1]["data"])
    assert error_event.code == "runtime_invoke_unavailable"
    assert store.get_thread(thread_id).turns == []
