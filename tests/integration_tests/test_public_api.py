import json

from fastapi.testclient import TestClient

from react_agent import public_api
from react_agent.public_contracts import (
    AgentStepModel,
    AnswerCardModel,
    CheckpointerStatus,
    FusionStepModel,
    LayerPlanItem,
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
    WorkflowStageProgressModel,
)
from react_agent.public_guardrails import acquire_stream_slot, release_stream_slot, reset_public_guardrail_state
from react_agent.public_mapping import compose_structured_input_text, replay_messages
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


def _assistant_turn(final_source: str = "mainline", continuity_mode: str = "replay") -> PublicTurn:
    return PublicTurn(
        id="assistant-test-1",
        role="assistant",
        text="Public answer from emitted bundle.",
        createdAt="2026-04-03 13:00",
        runId="run-f3-1234",
        continuityMode=continuity_mode,  # type: ignore[arg-type]
        answerCard=AnswerCardModel(
            answer="Public answer from emitted bundle.",
            finalSource=final_source,  # type: ignore[arg-type]
            confidence="high",
            citations=[],
            evidenceCards=[],
            evidenceCount=0,
        ),
        workflow=WorkflowModel(
            layerPlan=[
                LayerPlanItem(layer="L1", mode="Chain", selected=["a01_cio_orchestrator"]),
                LayerPlanItem(layer="L2", mode="Star", selected=["a03_macro_industry_research"]),
                LayerPlanItem(layer="L3", mode="Star", selected=["a17_traditional_valuation"]),
                LayerPlanItem(layer="L4", mode="Chain", selected=["a25_report_center"]),
            ],
            layerMode={"L1": "Chain", "L2": "Star", "L3": "Star", "L4": "Chain"},
            currentLayer="L4",
            layerDone=["L1", "L2", "L3", "L4"],
            agentSteps=[
                AgentStepModel(
                    id="step-1",
                    layer="L1",
                    agentId="a01_cio_orchestrator",
                    title="CIO Orchestrator",
                    summary="Framed the request.",
                    status="complete",
                )
            ],
            fusionSteps=[
                FusionStepModel(
                    id="fusion-baseline",
                    kind="baseline",
                    label="Baseline sidecar",
                    status="shadow",
                    summary="Baseline completed in shadow mode.",
                )
            ],
            finalSource=final_source,  # type: ignore[arg-type]
            provenanceNote="Continuity uses transcript replay, which is weaker than persistent graph state.",
            provenance=WorkflowProvenanceModel(
                emitPath="fusion_writer",
                finalSource=final_source,  # type: ignore[arg-type]
                continuityMode=continuity_mode,  # type: ignore[arg-type]
                summary="The final answer was emitted from the fusion writer path. Continuity uses transcript replay, which is weaker than persistent graph state.",
            ),
        ),
    )


def _probe(continuity_mode: str = "replay") -> RuntimeReadinessProbe:
    return RuntimeReadinessProbe(
        continuity_mode=continuity_mode,  # type: ignore[arg-type]
        runtime=ReadinessSurface(status="ready", code="runtime_ready"),
        provider_env=ReadinessSurface(status="configured", code="provider_env_configured"),
        search_env=ReadinessSurface(status="configured", code="search_env_configured"),
        checkpointer=CheckpointerStatus(
            enabled=continuity_mode == "persistent",
            mode="memory" if continuity_mode == "persistent" else "none",
            status="enabled" if continuity_mode == "persistent" else "disabled",
            code="checkpointer_enabled" if continuity_mode == "persistent" else "checkpointer_disabled",
            hint=None if continuity_mode == "persistent" else "Set REACT_AGENT_CHECKPOINTER=memory or sqlite for persistent continuity.",
        ),
        overall_status="ready" if continuity_mode == "persistent" else "degraded",
        graph_module=None,
    )


def _structured_input(**overrides) -> StructuredInputModel:
    payload = {
        "task": "Please summarize the investment committee request.",
        "context": "Background materials already cover public filings and market pricing pressure.",
        "materials": [
            "Material one: earnings-call notes highlight persistent pricing pressure.",
            "Material two: a recent policy memo points to tighter subsidy discipline.",
        ],
        "urlReferences": [],
        "constraints": "Use only public information.",
        "outputPreference": "Respond in Chinese with a short conclusion first.",
    }
    payload.update(overrides)
    return StructuredInputModel(**payload)


def _configure_test_app(tmp_path, monkeypatch, *, continuity_mode: str) -> TestClient:
    reset_public_guardrail_state()
    store = PublicThreadStore(tmp_path / "threads.json")
    monkeypatch.setattr(public_api, "store", store)
    monkeypatch.setattr(public_api, "_readiness_probe", lambda: _probe(continuity_mode))

    async def _fake_invoke_public_turn(*, thread_id, history_turns, user_text):
        assert thread_id
        assert user_text
        return _assistant_turn("fused", continuity_mode), continuity_mode

    monkeypatch.setattr(public_api, "invoke_public_turn", _fake_invoke_public_turn)
    return TestClient(public_api.app)


def _stream_lines(response) -> list[dict]:
    return [json.loads(line) for line in response.iter_lines() if line]


def test_health_contract(tmp_path, monkeypatch):
    client = _configure_test_app(tmp_path, monkeypatch, continuity_mode="replay")
    response = client.get("/api/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["apiVersion"] == "phase-f3"
    assert payload["overallStatus"] == "degraded"
    assert payload["continuityDefault"] == "replay"
    assert payload["runtime"]["code"] == "runtime_ready"
    assert payload["providerEnv"]["code"] == "provider_env_configured"
    assert payload["searchEnv"]["code"] == "search_env_configured"
    assert payload["checkpointer"]["status"] == "disabled"
    assert payload["checkpointer"]["code"] == "checkpointer_disabled"
    assert payload["store"] == "json-file"


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

    response = client.post(
        f"/api/threads/{thread_id}/messages",
        json={"text": "x" * 11},
    )

    assert response.status_code == 413
    assert response.json()["detail"]["code"] == "message_too_long"
    assert response.json()["detail"]["category"] == "request"


def test_public_api_rate_limit_returns_safe_429(tmp_path, monkeypatch):
    monkeypatch.setenv("PUBLIC_API_RATE_LIMIT_PER_MINUTE", "1")
    client = _configure_test_app(tmp_path, monkeypatch, continuity_mode="replay")

    first = client.get("/api/threads")
    second = client.get("/api/threads")

    assert first.status_code == 200
    assert second.status_code == 429
    assert second.json()["detail"]["code"] == "public_rate_limit_exceeded"
    assert "Traceback" not in second.text


def test_public_api_health_is_not_blocked_by_rate_limit(tmp_path, monkeypatch):
    monkeypatch.setenv("PUBLIC_API_RATE_LIMIT_PER_MINUTE", "1")
    client = _configure_test_app(tmp_path, monkeypatch, continuity_mode="replay")

    first = client.get("/api/health")
    second = client.get("/api/health")

    assert first.status_code == 200
    assert second.status_code == 200


def test_public_api_stream_active_limit_returns_safe_429(tmp_path, monkeypatch):
    monkeypatch.setenv("PUBLIC_API_RATE_LIMIT_PER_MINUTE", "0")
    monkeypatch.setenv("PUBLIC_API_MAX_ACTIVE_STREAMS_PER_IP", "1")
    client = _configure_test_app(tmp_path, monkeypatch, continuity_mode="replay")
    thread_id = client.post("/api/threads", json={}).json()["thread"]["id"]

    acquire_stream_slot("testclient")
    try:
        response = client.post(
            f"/api/threads/{thread_id}/messages/stream",
            json={"text": "Stream while another stream is active."},
        )
    finally:
        release_stream_slot("testclient")

    assert response.status_code == 429
    assert response.json()["detail"]["code"] == "public_stream_limit_exceeded"
    assert "Traceback" not in response.text


def test_public_runtime_allows_disabled_search_without_tavily(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-provider-key")
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    monkeypatch.setenv("DISABLE_SEARCH", "true")
    monkeypatch.delenv("SEARCH_REQUIRED", raising=False)

    probe = probe_public_runtime()
    assert probe.search_env.status == "disabled"
    assert probe.search_env.code == "search_env_disabled"

    prepared = prepare_public_turn_invoke(thread_id="thread-search-disabled", history_turns=[], user_text="hello")
    assert prepared.continuity_mode in {"replay", "persistent"}


def test_public_runtime_allows_optional_missing_tavily(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-provider-key")
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    monkeypatch.delenv("DISABLE_SEARCH", raising=False)
    monkeypatch.delenv("SEARCH_REQUIRED", raising=False)

    probe = probe_public_runtime()
    assert probe.search_env.status == "missing"
    assert probe.search_env.code == "search_env_missing_optional"

    prepared = prepare_public_turn_invoke(thread_id="thread-search-optional", history_turns=[], user_text="hello")
    assert prepared.continuity_mode in {"replay", "persistent"}


def test_public_runtime_blocks_missing_required_tavily(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-provider-key")
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    monkeypatch.delenv("DISABLE_SEARCH", raising=False)
    monkeypatch.setenv("SEARCH_REQUIRED", "true")

    probe = probe_public_runtime()
    assert probe.search_env.status == "missing"
    assert probe.search_env.code == "search_env_missing_required"

    try:
        prepare_public_turn_invoke(thread_id="thread-search-required", history_turns=[], user_text="hello")
    except PublicRuntimeUnavailable as exc:
        assert exc.code == "search_env_missing_required"
        assert exc.category == "provider_env"
    else:  # pragma: no cover - defensive assertion for explicit contract.
        raise AssertionError("missing required search should block public invocation")


def test_public_runtime_marks_tavily_as_available(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-provider-key")
    monkeypatch.setenv("TAVILY_API_KEY", "test-search-key")
    monkeypatch.delenv("DISABLE_SEARCH", raising=False)
    monkeypatch.delenv("SEARCH_REQUIRED", raising=False)

    probe = probe_public_runtime()
    assert probe.search_env.status == "configured"
    assert probe.search_env.code == "search_env_available"


def test_agent_catalog_contract(tmp_path, monkeypatch):
    client = _configure_test_app(tmp_path, monkeypatch, continuity_mode="replay")

    response = client.get("/api/agents")
    assert response.status_code == 200
    payload = response.json()

    assert payload["totals"]["configCount"] == 27
    assert payload["totals"]["runtimeCount"] == 25
    assert payload["totals"]["disabledIds"] == [
        "a05_annual_report_analysis",
        "a21_portfolio_manager",
    ]
    assert [layer["layer"] for layer in payload["layers"]] == ["L1", "L2", "L3", "L4"]
    assert [len(layer["agents"]) for layer in payload["layers"]] == [2, 20, 4, 1]

    l1_agents = payload["layers"][0]["agents"]
    assert l1_agents[0]["id"] == "a01_cio_orchestrator"
    assert l1_agents[0]["name"] == "问题解析与协同编排智能体"
    assert l1_agents[0]["capabilities"] == ["orchestration", "routing", "evidence_control"]
    assert l1_agents[0]["team"] == "management"
    assert l1_agents[0]["roleType"] == "system"
    assert l1_agents[0]["defaultEnabled"] is True
    assert l1_agents[1]["id"] == "a22_financial_data_service"

    assert [agent["id"] for agent in payload["disabledAgents"]] == [
        "a05_annual_report_analysis",
        "a21_portfolio_manager",
    ]
    all_ids = {
        agent["id"]
        for layer in payload["layers"]
        for agent in layer["agents"]
    }
    assert {"a16_ml_valuation", "a17_traditional_valuation", "a18_meta_valuation"} <= all_ids
    assert "a02_task_router" not in all_ids

    response_text = response.text
    for forbidden in ["messages", "analyst_results", "ephemeral_results", "manager_assignment", "tool_call"]:
        assert forbidden not in response_text


def test_thread_lifecycle_and_replay_contract(tmp_path, monkeypatch):
    client = _configure_test_app(tmp_path, monkeypatch, continuity_mode="replay")

    create_response = client.post("/api/threads", json={})
    assert create_response.status_code == 200
    created = create_response.json()
    thread_id = created["thread"]["id"]
    assert created["thread"]["continuityMode"] == "replay"
    assert created["thread"]["phase"] == "Phase F3 / health-debug polish"
    assert created["turns"] == []

    message_response = client.post(
        f"/api/threads/{thread_id}/messages",
        json={"text": "Please summarize the public answer."},
    )
    assert message_response.status_code == 200
    payload = message_response.json()
    assert payload["thread"]["continuityMode"] == "replay"
    assert payload["assistantTurn"]["role"] == "assistant"
    assert payload["assistantTurn"]["runId"] == "run-f3-1234"
    assert payload["assistantTurn"]["continuityMode"] == "replay"
    assert payload["assistantTurn"]["answerCard"]["finalSource"] == "fused"
    assert payload["assistantTurn"]["answerCard"]["evidenceCount"] == 0
    assert payload["assistantTurn"]["workflow"]["finalSource"] == "fused"
    assert payload["assistantTurn"]["workflow"]["provenance"]["emitPath"] == "fusion_writer"
    assert payload["assistantTurn"]["workflow"]["provenance"]["continuityMode"] == "replay"

    response_text = message_response.text
    for forbidden in [
        "messages",
        "analyst_results",
        "ephemeral_results",
        "mainline_emit_payload",
        "final_emit_payload",
        "thread_summary",
        "stable_findings",
    ]:
        assert forbidden not in response_text


def test_delete_thread_removes_only_target_thread(tmp_path, monkeypatch):
    client = _configure_test_app(tmp_path, monkeypatch, continuity_mode="replay")

    first = client.post("/api/threads", json={}).json()
    second = client.post("/api/threads", json={}).json()
    first_id = first["thread"]["id"]
    second_id = second["thread"]["id"]

    list_before = client.get("/api/threads").json()
    assert {thread["id"] for thread in list_before["threads"]} == {first_id, second_id}

    delete_response = client.delete(f"/api/threads/{first_id}")
    assert delete_response.status_code == 204
    assert not delete_response.content

    list_after = client.get("/api/threads").json()
    assert {thread["id"] for thread in list_after["threads"]} == {second_id}

    missing_get = client.get(f"/api/threads/{first_id}")
    assert missing_get.status_code == 404
    assert missing_get.json()["detail"]["code"] == "thread_not_found"

    remaining_get = client.get(f"/api/threads/{second_id}")
    assert remaining_get.status_code == 200
    assert remaining_get.json()["thread"]["id"] == second_id


def test_delete_missing_thread_returns_404(tmp_path, monkeypatch):
    client = _configure_test_app(tmp_path, monkeypatch, continuity_mode="replay")

    response = client.delete("/api/threads/thread-missing")

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "thread_not_found"


def test_clear_thread_messages_preserves_thread_and_does_not_affect_others(tmp_path, monkeypatch):
    client = _configure_test_app(tmp_path, monkeypatch, continuity_mode="replay")

    first_id = client.post("/api/threads", json={"title": "Keep title"}).json()["thread"]["id"]
    second_id = client.post("/api/threads", json={"title": "Other thread"}).json()["thread"]["id"]

    first_message = client.post(
        f"/api/threads/{first_id}/messages",
        json={"text": "Please summarize the public answer."},
    )
    second_message = client.post(
        f"/api/threads/{second_id}/messages",
        json={"text": "Leave this thread intact."},
    )
    assert first_message.status_code == 200
    assert second_message.status_code == 200
    assert len(first_message.json()["turns"]) == 2
    assert len(second_message.json()["turns"]) == 2
    first_title_before_clear = first_message.json()["thread"]["title"]
    second_title_before_clear = second_message.json()["thread"]["title"]

    clear_response = client.delete(f"/api/threads/{first_id}/messages")

    assert clear_response.status_code == 200
    cleared = clear_response.json()
    assert cleared["thread"]["id"] == first_id
    assert cleared["thread"]["title"] == first_title_before_clear
    assert cleared["thread"]["preview"] == "Awaiting first message."
    assert cleared["turns"] == []

    first_get = client.get(f"/api/threads/{first_id}").json()
    second_get = client.get(f"/api/threads/{second_id}").json()
    assert first_get["turns"] == []
    assert len(second_get["turns"]) == 2
    assert second_get["thread"]["title"] == second_title_before_clear


def test_clear_missing_thread_returns_404(tmp_path, monkeypatch):
    client = _configure_test_app(tmp_path, monkeypatch, continuity_mode="replay")

    response = client.delete("/api/threads/thread-missing/messages")

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "thread_not_found"


def test_send_message_accepts_structured_input_and_get_thread_returns_it(tmp_path, monkeypatch):
    client = _configure_test_app(tmp_path, monkeypatch, continuity_mode="replay")

    create_response = client.post("/api/threads", json={})
    thread_id = create_response.json()["thread"]["id"]

    structured_input = _structured_input()
    canonical_text = compose_structured_input_text(structured_input)

    message_response = client.post(
        f"/api/threads/{thread_id}/messages",
        json={
            "text": canonical_text,
            "structuredInput": structured_input.model_dump(mode="json"),
        },
    )
    assert message_response.status_code == 200
    payload = message_response.json()
    user_turn = payload["turns"][0]
    assert user_turn["text"] == canonical_text
    assert user_turn["structuredInput"]["task"] == structured_input.task
    assert user_turn["structuredInput"]["context"] == structured_input.context
    assert user_turn["structuredInput"]["materials"] == structured_input.materials
    assert user_turn["structuredInput"]["urlReferences"] == structured_input.urlReferences
    assert user_turn["structuredInput"]["constraints"] == structured_input.constraints
    assert user_turn["structuredInput"]["outputPreference"] == structured_input.outputPreference

    thread_response = client.get(f"/api/threads/{thread_id}")
    assert thread_response.status_code == 200
    thread_payload = thread_response.json()
    persisted_user_turn = thread_payload["turns"][0]
    assert persisted_user_turn["text"] == canonical_text
    assert persisted_user_turn["structuredInput"]["task"] == structured_input.task
    assert persisted_user_turn["structuredInput"]["materials"] == structured_input.materials
    assert persisted_user_turn["structuredInput"]["urlReferences"] == structured_input.urlReferences


def test_send_message_accepts_url_references_and_get_thread_returns_them(tmp_path, monkeypatch):
    client = _configure_test_app(tmp_path, monkeypatch, continuity_mode="replay")

    create_response = client.post("/api/threads", json={})
    thread_id = create_response.json()["thread"]["id"]

    structured_input = _structured_input(
        context="Background covers public policy commentary only.",
        materials=[],
        urlReferences=[
            "https://example.com/policy-brief",
            "https://example.com/company-update",
        ],
        constraints=None,
        outputPreference=None,
    )
    canonical_text = compose_structured_input_text(structured_input)

    message_response = client.post(
        f"/api/threads/{thread_id}/messages",
        json={
            "text": canonical_text,
            "structuredInput": structured_input.model_dump(mode="json"),
        },
    )
    assert message_response.status_code == 200
    payload = message_response.json()
    user_turn = payload["turns"][0]
    assert user_turn["text"] == canonical_text
    assert "【链接参考 / URL 引用】" in canonical_text
    assert "[链接 1]" in canonical_text
    assert user_turn["structuredInput"]["urlReferences"] == structured_input.urlReferences

    thread_response = client.get(f"/api/threads/{thread_id}")
    assert thread_response.status_code == 200
    thread_payload = thread_response.json()
    persisted_user_turn = thread_payload["turns"][0]
    assert persisted_user_turn["structuredInput"]["urlReferences"] == structured_input.urlReferences


def test_send_message_rejects_structured_input_text_mismatch(tmp_path, monkeypatch):
    client = _configure_test_app(tmp_path, monkeypatch, continuity_mode="replay")

    create_response = client.post("/api/threads", json={})
    thread_id = create_response.json()["thread"]["id"]

    message_response = client.post(
        f"/api/threads/{thread_id}/messages",
        json={
            "text": "Free-form text that does not match the structured input.",
            "structuredInput": _structured_input().model_dump(mode="json"),
        },
    )
    assert message_response.status_code == 400
    payload = message_response.json()
    assert payload["detail"]["code"] == "structured_input_text_mismatch"
    assert payload["detail"]["category"] == "request"


def test_replay_messages_uses_turn_text_even_when_structured_input_exists():
    turns = [
        PublicTurn(
            id="user-structured-1",
            role="user",
            text="Canonical replay text",
            createdAt="2026-04-04 18:10",
            structuredInput=_structured_input(task="Canonical replay text"),
        ),
        PublicTurn(
            id="assistant-structured-1",
            role="assistant",
            text="Assistant reply",
            createdAt="2026-04-04 18:11",
        ),
    ]

    replay = replay_messages(turns, "Pending follow-up")
    assert replay == [
        ("user", "Canonical replay text"),
        ("assistant", "Assistant reply"),
        ("user", "Pending follow-up"),
    ]


def test_thread_lifecycle_and_persistent_contract(tmp_path, monkeypatch):
    client = _configure_test_app(tmp_path, monkeypatch, continuity_mode="persistent")

    create_response = client.post("/api/threads", json={})
    assert create_response.status_code == 200
    thread_id = create_response.json()["thread"]["id"]
    assert create_response.json()["thread"]["continuityMode"] == "persistent"

    message_response = client.post(
        f"/api/threads/{thread_id}/messages",
        json={"text": "Keep continuity on the persistent path."},
    )
    assert message_response.status_code == 200
    payload = message_response.json()
    assert payload["thread"]["continuityMode"] == "persistent"
    assert payload["assistantTurn"]["continuityMode"] == "persistent"
    assert payload["turns"][0]["role"] == "user"
    assert payload["turns"][1]["role"] == "assistant"


def test_send_message_runtime_failure_contract(tmp_path, monkeypatch):
    store = PublicThreadStore(tmp_path / "threads.json")
    monkeypatch.setattr(public_api, "store", store)
    monkeypatch.setattr(public_api, "_readiness_probe", lambda: _probe("replay"))

    client = TestClient(public_api.app)
    create_response = client.post("/api/threads", json={})
    thread_id = create_response.json()["thread"]["id"]

    async def _failing_invoke_public_turn(*, thread_id, history_turns, user_text):
        raise PublicRuntimeUnavailable(
            "LangGraph runtime is unavailable for public invocation.",
            code="runtime_import_unavailable",
            category="runtime",
        )

    monkeypatch.setattr(public_api, "invoke_public_turn", _failing_invoke_public_turn)

    message_response = client.post(
        f"/api/threads/{thread_id}/messages",
        json={"text": "Trigger the public runtime failure path."},
    )
    assert message_response.status_code == 503
    payload = message_response.json()
    assert payload["detail"]["code"] == "runtime_import_unavailable"
    assert payload["detail"]["category"] == "runtime"
    assert payload["detail"]["message"] == "LangGraph runtime is unavailable for public invocation."

    response_text = message_response.text
    assert "Traceback" not in response_text
    for forbidden in [
        "messages",
        "analyst_results",
        "ephemeral_results",
        "thread_summary",
        "stable_findings",
    ]:
        assert forbidden not in response_text


def test_send_message_unexpected_exception_is_sanitized(tmp_path, monkeypatch):
    store = PublicThreadStore(tmp_path / "threads.json")
    monkeypatch.setattr(public_api, "store", store)
    monkeypatch.setattr(public_api, "_readiness_probe", lambda: _probe("replay"))

    client = TestClient(public_api.app)
    thread_id = client.post("/api/threads", json={}).json()["thread"]["id"]

    async def _unexpected_invoke_public_turn(*, thread_id, history_turns, user_text):
        raise RuntimeError("Traceback provider raw body secret-token should not be returned")

    monkeypatch.setattr(public_api, "invoke_public_turn", _unexpected_invoke_public_turn)

    response = client.post(
        f"/api/threads/{thread_id}/messages",
        json={"text": "Trigger unexpected exception sanitization."},
    )

    assert response.status_code == 500
    payload = response.json()
    assert payload["detail"]["code"] == "public_runtime_unexpected"
    assert payload["detail"]["category"] == "runtime"
    assert "Traceback" not in response.text
    assert "secret-token" not in response.text
    assert "provider raw body" not in response.text


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
        assert thread_id
        assert user_text == "Stream the final answer."
        assert prepared is prepared_session
        yield RunStartedEvent(
            type="run.started",
            data=RunStartedEventData(threadId=thread_id, continuityMode="persistent"),
        )
        yield WorkflowStageEvent(
            type="workflow.stage",
            data=WorkflowStageEventData(
                stages=[
                    WorkflowStageProgressModel(key="routing", title="路由规划", status="completed"),
                    WorkflowStageProgressModel(key="analysis", title="多角度分析", status="running"),
                    WorkflowStageProgressModel(key="risk", title="风险校验", status="waiting"),
                    WorkflowStageProgressModel(key="summary", title="汇总结论", status="waiting"),
                    WorkflowStageProgressModel(key="fusion", title="融合判断", status="waiting"),
                ],
                currentStage="analysis",
            ),
        )
        yield WorkflowSnapshotEvent(
            type="workflow.snapshot",
            data=WorkflowSnapshotEventData(
                workflow=_assistant_turn("fused", "persistent").workflow,
                runId="run-stream-1",
                continuityMode="persistent",
            ),
        )
        yield StreamPublicTurnCompleted(
            assistant_turn=_assistant_turn("fused", "persistent"),
            continuity_mode="persistent",
        )

    prepared_session = prepared
    monkeypatch.setattr(public_api, "stream_public_turn", _fake_stream_public_turn)

    client = TestClient(public_api.app)
    create_response = client.post("/api/threads", json={})
    thread_id = create_response.json()["thread"]["id"]

    with client.stream(
        "POST",
        f"/api/threads/{thread_id}/messages/stream",
        json={"text": "Stream the final answer."},
    ) as response:
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("application/x-ndjson")
        events = _stream_lines(response)

    assert [event["type"] for event in events] == [
        "run.started",
        "workflow.stage",
        "workflow.snapshot",
        "answer.final",
    ]
    final_response = events[-1]["data"]["response"]
    assert final_response["assistantTurn"]["continuityMode"] == "persistent"
    assert final_response["turns"][0]["role"] == "user"
    assert final_response["turns"][1]["role"] == "assistant"

    persisted = store.get_thread(thread_id)
    assert persisted is not None
    assert len(persisted.turns) == 2
    assert persisted.turns[1].role == "assistant"
    assert persisted.turns[1].continuityMode == "persistent"

    with client.stream(
        "POST",
        f"/api/threads/{thread_id}/messages/stream",
        json={"text": "Stream the final answer."},
    ) as second_response:
        assert second_response.status_code == 200
        second_events = _stream_lines(second_response)
    assert second_events[-1]["type"] == "answer.final"


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
            "LangGraph runtime invocation failed before a public answer could be produced.",
            code="runtime_invoke_unavailable",
            category="runtime",
        )

    monkeypatch.setattr(public_api, "stream_public_turn", _failing_stream_public_turn)

    client = TestClient(public_api.app)
    create_response = client.post("/api/threads", json={})
    thread_id = create_response.json()["thread"]["id"]

    with client.stream(
        "POST",
        f"/api/threads/{thread_id}/messages/stream",
        json={"text": "Trigger in-stream failure."},
    ) as response:
        assert response.status_code == 200
        events = _stream_lines(response)

    assert [event["type"] for event in events] == ["run.started", "error"]
    error_event = StreamErrorEventData.model_validate(events[-1]["data"])
    assert error_event.code == "runtime_invoke_unavailable"
    assert error_event.category == "runtime"

    persisted = store.get_thread(thread_id)
    assert persisted is not None
    assert persisted.turns == []


def test_send_message_stream_preflight_validation_and_missing_thread(tmp_path, monkeypatch):
    client = _configure_test_app(tmp_path, monkeypatch, continuity_mode="replay")

    missing_response = client.post(
        "/api/threads/thread-missing/messages/stream",
        json={"text": "Anything"},
    )
    assert missing_response.status_code == 404
    assert missing_response.json()["detail"]["code"] == "thread_not_found"

    create_response = client.post("/api/threads", json={})
    thread_id = create_response.json()["thread"]["id"]
    empty_response = client.post(
        f"/api/threads/{thread_id}/messages/stream",
        json={"text": "   "},
    )
    assert empty_response.status_code == 400
    assert empty_response.json()["detail"]["code"] == "empty_message_text"
