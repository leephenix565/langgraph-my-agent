# ruff: noqa: D103
"""FastAPI public adapter for the chat-first web client."""

from __future__ import annotations

import os
import uuid
from pathlib import Path
from typing import Any, List

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse

from react_agent.fixed_dag_catalog import fixed_dag_public_agent_catalog
from react_agent.public_contracts import (
    AgentCatalogResponse,
    AnswerFinalEvent,
    AnswerFinalEventData,
    ChatSessionSummary,
    CreateThreadRequest,
    ErrorDetail,
    HealthResponse,
    PublicThreadDetail,
    PublicTurn,
    SendMessageRequest,
    SendMessageResponse,
    StreamErrorEvent,
    StreamErrorEventData,
    StructuredInputModel,
    ThreadsResponse,
)
from react_agent.public_guardrails import (
    PublicApiGuardrailViolation,
    acquire_stream_slot,
    check_rate_limit,
    client_key_from_request,
    release_stream_slot,
    validate_message_length,
)
from react_agent.public_mapping import (
    append_turns,
    build_new_thread,
    build_user_turn,
    compose_structured_input_text,
    normalize_structured_input,
)
from react_agent.public_runtime import (
    PublicRuntimeError,
    PublicRuntimeUnavailable,
    RuntimeReadinessProbe,
    StreamPublicTurnCompleted,
    invoke_public_turn,
    prepare_public_turn_invoke,
    probe_public_runtime,
    stream_public_turn,
)
from react_agent.public_store import (
    PublicStoreError,
    PublicThreadStore,
    default_store_path,
)

API_VERSION = "phase-r3"


def _store_path_from_env() -> Path:
    configured = os.environ.get("REACT_AGENT_PUBLIC_STORE", "") or ""
    return Path(configured) if configured.strip() else default_store_path()


def _build_store() -> PublicThreadStore:
    return PublicThreadStore(_store_path_from_env())


app = FastAPI(title="react-agent public adapter", version=API_VERSION)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
store = _build_store()


def _readiness_probe() -> RuntimeReadinessProbe:
    return probe_public_runtime()


def _error_detail(code: str, message: str, category: str) -> dict:
    return ErrorDetail(code=code, message=message, category=category).model_dump()


def _http_error(status_code: int, *, code: str, message: str, category: str) -> HTTPException:
    return HTTPException(status_code=status_code, detail=_error_detail(code, message, category))


def _guardrail_http_error(exc: PublicApiGuardrailViolation) -> HTTPException:
    return _http_error(exc.status_code, code=exc.code, message=exc.message, category=exc.category)


@app.middleware("http")
async def _public_trial_guardrails(request: Request, call_next):
    path = request.url.path
    if path == "/api/health" or not path.startswith("/api/"):
        return await call_next(request)

    try:
        check_rate_limit(client_key_from_request(request))
    except PublicApiGuardrailViolation as exc:
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": _error_detail(exc.code, exc.message, exc.category)},
        )
    return await call_next(request)


def _sorted_summaries(details: List[PublicThreadDetail]) -> List[ChatSessionSummary]:
    return sorted(
        [detail.thread for detail in details],
        key=lambda item: item.updatedAt,
        reverse=True,
    )


def _build_agent_catalog_response() -> AgentCatalogResponse:
    return AgentCatalogResponse(**fixed_dag_public_agent_catalog())


@app.get("/api/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    probe = _readiness_probe()
    return HealthResponse(
        status="ok",
        apiVersion=API_VERSION,
        overallStatus=probe.overall_status,
        checkpointer=probe.checkpointer,
        continuityDefault=probe.continuity_mode,
        runtime=probe.runtime,
        providerEnv=probe.provider_env,
        searchEnv=probe.search_env,
        store="json-file",
    )


@app.get("/api/threads", response_model=ThreadsResponse)
async def list_threads() -> ThreadsResponse:
    try:
        return ThreadsResponse(threads=_sorted_summaries(store.list_threads()))
    except PublicStoreError as exc:
        raise _http_error(
            500,
            code="public_store_unavailable",
            message="Public thread store is unavailable.",
            category="store",
        ) from exc


@app.get("/api/agents", response_model=AgentCatalogResponse)
async def list_agents() -> AgentCatalogResponse:
    return _build_agent_catalog_response()


@app.post("/api/threads", response_model=PublicThreadDetail)
async def create_thread(payload: CreateThreadRequest | None = None) -> PublicThreadDetail:
    try:
        probe = _readiness_probe()
        thread_id = f"thread-{uuid.uuid4().hex[:10]}"
        detail = build_new_thread(thread_id, probe.continuity_mode)
        if payload and payload.title:
            detail.thread.title = payload.title.strip() or detail.thread.title
        return store.upsert_thread(detail)
    except PublicStoreError as exc:
        raise _http_error(
            500,
            code="public_store_unavailable",
            message="Public thread store is unavailable.",
            category="store",
    ) from exc


def _get_thread_detail(thread_id: str) -> PublicThreadDetail:
    try:
        detail = store.get_thread(thread_id)
    except PublicStoreError as exc:
        raise _http_error(
            500,
            code="public_store_unavailable",
            message="Public thread store is unavailable.",
            category="store",
        ) from exc
    if detail is None:
        raise _http_error(
            404,
            code="thread_not_found",
            message=f"Unknown thread_id: {thread_id}",
            category="request",
        )
    return detail


def _prepare_user_message(payload: SendMessageRequest) -> tuple[str, StructuredInputModel | None, PublicTurn]:
    user_text = payload.text.strip()
    if not user_text:
        raise _http_error(
            400,
            code="empty_message_text",
            message="Message text must not be empty.",
            category="request",
        )

    structured_input = None
    if payload.structuredInput is not None:
        try:
            # text stays canonical; typed structured input, including pasted materials and URL references,
            # is only an additive mirror.
            structured_input = normalize_structured_input(payload.structuredInput)
            canonical_text = compose_structured_input_text(structured_input)
        except ValueError:
            raise _http_error(
                400,
                code="invalid_structured_input",
                message="Structured input must include a non-empty task.",
                category="request",
            ) from None
        if user_text != canonical_text:
            raise _http_error(
                400,
                code="structured_input_text_mismatch",
                message="Message text must match the canonical structured input text.",
                category="request",
            )

    try:
        validate_message_length(user_text)
    except PublicApiGuardrailViolation as exc:
        raise _guardrail_http_error(exc) from exc

    return user_text, structured_input, build_user_turn(user_text, structured_input)


def _encode_ndjson_event(event: Any) -> bytes:
    return (event.model_dump_json() + "\n").encode("utf-8")


@app.get("/api/threads/{thread_id}", response_model=PublicThreadDetail)
async def get_thread(thread_id: str) -> PublicThreadDetail:
    return _get_thread_detail(thread_id)


@app.delete("/api/threads/{thread_id}", status_code=204)
async def delete_thread(thread_id: str) -> Response:
    try:
        deleted = store.delete_thread(thread_id)
    except PublicStoreError as exc:
        raise _http_error(
            500,
            code="public_store_unavailable",
            message="Public thread store is unavailable.",
            category="store",
        ) from exc
    if not deleted:
        raise _http_error(
            404,
            code="thread_not_found",
            message=f"Unknown thread_id: {thread_id}",
            category="request",
        )
    return Response(status_code=204)


@app.delete("/api/threads/{thread_id}/messages", response_model=PublicThreadDetail)
async def clear_thread_messages(thread_id: str) -> PublicThreadDetail:
    try:
        detail = store.clear_thread_messages(thread_id)
    except PublicStoreError as exc:
        raise _http_error(
            500,
            code="public_store_unavailable",
            message="Public thread store is unavailable.",
            category="store",
        ) from exc
    if detail is None:
        raise _http_error(
            404,
            code="thread_not_found",
            message=f"Unknown thread_id: {thread_id}",
            category="request",
        )
    return detail


@app.post("/api/threads/{thread_id}/messages", response_model=SendMessageResponse)
async def send_message(thread_id: str, payload: SendMessageRequest) -> SendMessageResponse:
    detail = _get_thread_detail(thread_id)
    user_text, structured_input, user_turn = _prepare_user_message(payload)
    try:
        assistant_turn, continuity_mode = await invoke_public_turn(
            thread_id=thread_id,
            history_turns=detail.turns,
            user_text=user_text,
        )
    except PublicRuntimeUnavailable as exc:
        raise _http_error(503, code=exc.code, message=exc.message, category=exc.category) from exc
    except PublicRuntimeError as exc:
        raise _http_error(502, code=exc.code, message=exc.message, category=exc.category) from exc
    except Exception as exc:
        raise _http_error(
            500,
            code="public_runtime_unexpected",
            message="Public runtime failed before a safe response could be produced.",
            category="runtime",
        ) from exc

    updated_detail = append_turns(detail, user_turn, assistant_turn, continuity_mode)
    try:
        store.upsert_thread(updated_detail)
    except PublicStoreError as exc:
        raise _http_error(
            500,
            code="public_store_unavailable",
            message="Public thread store is unavailable.",
            category="store",
        ) from exc

    return SendMessageResponse(
        thread=updated_detail.thread,
        assistantTurn=assistant_turn,
        turns=updated_detail.turns,
    )


@app.post("/api/threads/{thread_id}/messages/stream")
async def send_message_stream(thread_id: str, request: Request, payload: SendMessageRequest) -> StreamingResponse:
    detail = _get_thread_detail(thread_id)
    user_text, structured_input, user_turn = _prepare_user_message(payload)
    try:
        prepared = prepare_public_turn_invoke(
            thread_id=thread_id,
            history_turns=detail.turns,
            user_text=user_text,
        )
    except PublicRuntimeUnavailable as exc:
        raise _http_error(503, code=exc.code, message=exc.message, category=exc.category) from exc
    except PublicRuntimeError as exc:
        raise _http_error(502, code=exc.code, message=exc.message, category=exc.category) from exc
    except Exception as exc:
        raise _http_error(
            500,
            code="public_runtime_unexpected",
            message="Public runtime failed before a safe streaming response could be produced.",
            category="runtime",
        ) from exc

    client_key = client_key_from_request(request)
    try:
        acquire_stream_slot(client_key)
    except PublicApiGuardrailViolation as exc:
        raise _guardrail_http_error(exc) from exc

    async def _event_stream():
        completion: StreamPublicTurnCompleted | None = None
        try:
            try:
                async for event in stream_public_turn(
                    thread_id=thread_id,
                    user_text=user_text,
                    prepared=prepared,
                ):
                    if isinstance(event, StreamPublicTurnCompleted):
                        completion = event
                        break
                    yield _encode_ndjson_event(event)
            except PublicRuntimeUnavailable as exc:
                yield _encode_ndjson_event(
                    StreamErrorEvent(
                        type="error",
                        data=StreamErrorEventData(code=exc.code, message=exc.message, category=exc.category),
                    )
                )
                return
            except PublicRuntimeError as exc:
                yield _encode_ndjson_event(
                    StreamErrorEvent(
                        type="error",
                        data=StreamErrorEventData(code=exc.code, message=exc.message, category=exc.category),
                    )
                )
                return
            except Exception:
                yield _encode_ndjson_event(
                    StreamErrorEvent(
                        type="error",
                        data=StreamErrorEventData(
                            code="runtime_stream_unexpected",
                            message="Streaming invocation ended unexpectedly before a final public answer could be produced.",
                            category="runtime",
                        ),
                    )
                )
                return

            if completion is None:
                yield _encode_ndjson_event(
                    StreamErrorEvent(
                        type="error",
                        data=StreamErrorEventData(
                            code="runtime_stream_incomplete",
                            message="LangGraph runtime stream ended before a final public answer could be produced.",
                            category="runtime",
                        ),
                    ),
                )
                return

            updated_detail = append_turns(detail, user_turn, completion.assistant_turn, completion.continuity_mode)
            try:
                store.upsert_thread(updated_detail)
            except PublicStoreError:
                yield _encode_ndjson_event(
                    StreamErrorEvent(
                        type="error",
                        data=StreamErrorEventData(
                            code="public_store_unavailable",
                            message="Public thread store is unavailable.",
                            category="store",
                        ),
                    )
                )
                return

            yield _encode_ndjson_event(
                AnswerFinalEvent(
                    type="answer.final",
                    data=AnswerFinalEventData(
                        response=SendMessageResponse(
                            thread=updated_detail.thread,
                            assistantTurn=completion.assistant_turn,
                            turns=updated_detail.turns,
                        )
                    ),
                )
            )
        finally:
            release_stream_slot(client_key)

    return StreamingResponse(_event_stream(), media_type="application/x-ndjson")
