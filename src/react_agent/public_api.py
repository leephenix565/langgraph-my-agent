"""FastAPI public adapter for the chat-first web client."""

from __future__ import annotations

import os
import uuid
from pathlib import Path
from typing import Any, List

from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from react_agent.agents import (
    AGENT_METADATA,
    AgentMetadata,
    agent_sort_key,
    load_metadata_from_dir,
)
from react_agent.public_contracts import (
    AnswerFinalEvent,
    AnswerFinalEventData,
    AgentCatalogLayerModel,
    AgentCatalogResponse,
    AgentCatalogTotalsModel,
    ChatSessionSummary,
    CreateThreadRequest,
    ErrorDetail,
    HealthResponse,
    PublicAgentMetadataModel,
    PublicThreadDetail,
    PublicTurn,
    SendMessageRequest,
    SendMessageResponse,
    StreamErrorEvent,
    StreamErrorEventData,
    StructuredInputModel,
    ThreadsResponse,
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
    invoke_public_turn,
    prepare_public_turn_invoke,
    probe_public_runtime,
    StreamPublicTurnCompleted,
    stream_public_turn,
)
from react_agent.public_store import PublicStoreError, PublicThreadStore, default_store_path

API_VERSION = "phase-f3"
AGENT_LAYER_ORDER = ("L1", "L2", "L3", "L4")


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


def _sorted_summaries(details: List[PublicThreadDetail]) -> List[ChatSessionSummary]:
    return sorted(
        [detail.thread for detail in details],
        key=lambda item: item.updatedAt,
        reverse=True,
    )


def _ensure_public_agent_metadata() -> List[AgentMetadata]:
    if not AGENT_METADATA:
        load_metadata_from_dir(Path(__file__).resolve().parents[2] / "config" / "agents")
    return sorted(AGENT_METADATA.values(), key=agent_sort_key)


def _public_agent_metadata(meta: AgentMetadata) -> PublicAgentMetadataModel:
    return PublicAgentMetadataModel(
        id=meta.id,
        name=meta.name,
        description=meta.description,
        capabilities=list(meta.capabilities or []),
        layer=(meta.layer or "L1"),  # type: ignore[arg-type]
        team=meta.team or "",
        roleType=meta.role_type,
        defaultEnabled=bool(meta.default_enabled),
    )


def _build_agent_catalog_response() -> AgentCatalogResponse:
    metadata = _ensure_public_agent_metadata()
    enabled = [meta for meta in metadata if meta.default_enabled]
    disabled = [meta for meta in metadata if not meta.default_enabled]

    layers = [
        AgentCatalogLayerModel(
            layer=layer,  # type: ignore[arg-type]
            agents=[_public_agent_metadata(meta) for meta in metadata if (meta.layer or "").upper() == layer],
        )
        for layer in AGENT_LAYER_ORDER
    ]

    return AgentCatalogResponse(
        totals=AgentCatalogTotalsModel(
            configCount=len(metadata),
            runtimeCount=len(enabled),
            disabledIds=[meta.id for meta in disabled],
        ),
        layers=layers,
        disabledAgents=[_public_agent_metadata(meta) for meta in disabled],
    )


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
async def send_message_stream(thread_id: str, payload: SendMessageRequest) -> StreamingResponse:
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

    async def _event_stream():
        completion: StreamPublicTurnCompleted | None = None
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
                )
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

    return StreamingResponse(_event_stream(), media_type="application/x-ndjson")
