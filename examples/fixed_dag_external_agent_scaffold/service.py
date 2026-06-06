"""Sample-only FastAPI service for fixed DAG external-agent handoff."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from typing import Any

from errors import empty_question_error, legacy_agent_id_error, target_required_error
from fastapi import FastAPI
from schemas import (
    AgentConclusionToolResult,
    ComputeRequest,
    EventFlag,
    EvidenceItem,
    ExternalAgentHealth,
    ExternalAgentRequest,
    ExternalAgentResponse,
    FixedDagDimension,
    ImplementationNotes,
    TypedError,
)

FIXED_DAG_AGENT_ID = "value_ml_valuation"
EXTERNAL_AGENT_ID = "valuation_ml"
LEGACY_AGENT_ID = "a16_ml_valuation"
AGENT_NAME = "Fixed DAG sample valuation agent"
VERSION = "0.1.0"

PROVIDER_CALL_COUNT = 0
EXTERNAL_CALL_COUNT = 0

DIMENSION_LABELS = {
    "value": "价值维",
    "market": "市场面维",
    "risk": "风险维",
    "macro": "宏观维",
}

IMPLEMENTATION_NOTES = ImplementationNotes(
    implementation_type="model_compute_agent",
    uses_llm=False,
    llm_role="",
    compute_core="deterministic_sample_v1",
    explanation_layer="deterministic_template",
)

_RESULT_CACHE: dict[str, AgentConclusionToolResult] = {}
_ANN_ID_PATTERN = re.compile(r"^a\d{2}_")

app = FastAPI(title=AGENT_NAME, version=VERSION)


def is_legacy_primary_agent_id(agent_id: str) -> bool:
    """Return whether the request used an old aNN id as the primary id."""
    return bool(_ANN_ID_PATTERN.match(agent_id))


def make_cache_key(
    *,
    agent_id: str,
    external_agent_id: str,
    target: str,
    as_of: str,
    options: Mapping[str, Any],
) -> str:
    """Build a deterministic cache key that includes the point-in-time date."""
    payload = {
        "agent_id": agent_id,
        "external_agent_id": external_agent_id,
        "target": target.strip().upper(),
        "as_of": as_of,
        "missing_fields": sorted(str(item) for item in options.get("missing_fields", [])),
        "model_version": str(options.get("model_version", "sample_v1")),
    }
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]


def compute_core(
    *,
    agent_id: str,
    external_agent_id: str,
    target: str,
    as_of: str,
    dimension: FixedDagDimension = "value",
    options: Mapping[str, Any] | None = None,
) -> AgentConclusionToolResult:
    """Run deterministic local compute with no LLM, provider, or HTTP call."""
    options = options or {}
    cache_key = make_cache_key(
        agent_id=agent_id,
        external_agent_id=external_agent_id,
        target=target,
        as_of=as_of,
        options=options,
    )
    cached = _RESULT_CACHE.get(cache_key)
    if cached is not None:
        return cached

    missing_fields = [str(item) for item in options.get("missing_fields", [])]
    degraded = bool(missing_fields)
    confidence = round(max(0.2, 0.72 - 0.12 * len(missing_fields)), 4)
    stance = round(min(0.85, max(-0.85, (len(target.strip()) % 9 - 4) / 10)), 4)
    label = "slightly_positive" if stance >= 0 else "slightly_negative"
    warnings = [f"missing field: {field}" for field in missing_fields]

    result = AgentConclusionToolResult(
        agent_id=agent_id,
        external_agent_id=external_agent_id,
        dimension=dimension,
        target=target.strip().upper(),
        stance=stance,
        confidence=confidence,
        label=label,
        evidence=[
            EvidenceItem(
                fact="Deterministic sample feature set is bounded by as_of.",
                source="sample_local_snapshot",
                as_of=as_of,
                data_as_of=as_of,
                value=float(len(target.strip())),
                unit="sample_score",
            )
        ],
        event_flags=[
            EventFlag(
                type="sample_point_in_time_check",
                severity=0.1,
                direction="neutral",
                as_of=as_of,
            )
        ],
        as_of=as_of,
        data_as_of=as_of,
        status="partial" if degraded else "ok",
        warnings=warnings,
        implementation_notes=IMPLEMENTATION_NOTES,
    )
    _RESULT_CACHE[cache_key] = result
    return result


def external_status_to_fixed_dag_status(status: str) -> str:
    """Map external envelope status into fixed DAG result status."""
    if status == "ok":
        return "complete"
    if status in {"partial", "needs_clarification"}:
        return "partial"
    return "error"


def map_response_to_conclusion_object(
    response: ExternalAgentResponse | Mapping[str, Any],
) -> dict[str, Any]:
    """Map an external response into a fixed DAG conclusion_object_v1 shape."""
    response_dict = (
        response.model_dump(mode="json")
        if hasattr(response, "model_dump")
        else dict(response)
    )
    tool_result = response_dict.get("tool_result") or {}
    if hasattr(tool_result, "model_dump"):
        tool_result = tool_result.model_dump(mode="json")
    legacy_agent_id = str(
        response_dict.get("legacy_agent_id") or tool_result.get("legacy_agent_id") or ""
    )

    agent_id = str(tool_result.get("agent_id") or response_dict.get("agent_id") or "")
    mapped = {
        "schema": "conclusion_object_v1",
        "schema_version": "conclusion_object_v1",
        "agent_id": agent_id,
        "dimension": tool_result.get("dimension"),
        "stance": tool_result.get("stance"),
        "confidence": tool_result.get("confidence", response_dict.get("confidence", 0.0)),
        "status": external_status_to_fixed_dag_status(str(response_dict.get("status"))),
        "evidence": tool_result.get("evidence", []),
        "as_of": tool_result.get("as_of"),
        "data_as_of": tool_result.get("data_as_of"),
        "event_flags": tool_result.get("event_flags", []),
        "provenance": {
            "source": "fixed_dag_external_agent_scaffold",
            "external_agent_id": response_dict.get("external_agent_id", ""),
            "legacy_agent_id": legacy_agent_id,
            "provider_invoked": False,
            "external_invoked": False,
        },
    }
    if agent_id == "sentiment_company_radar":
        mapped["output_routes"] = ["market_composite"]
    return mapped


def _error_response(
    *,
    request_id: str,
    agent_id: str,
    external_agent_id: str,
    legacy_agent_id: str,
    error: TypedError,
    answer: str,
) -> ExternalAgentResponse:
    return ExternalAgentResponse(
        request_id=request_id,
        agent_id=agent_id,
        external_agent_id=external_agent_id,
        legacy_agent_id=legacy_agent_id,
        status="error",
        answer=answer,
        key_points=[],
        tool_result={},
        confidence=0.0,
        warnings=[],
        errors=[error],
    )


def _validate_request_ids(
    *,
    request_id: str,
    agent_id: str,
    external_agent_id: str,
    legacy_agent_id: str,
    target: str,
    question: str = "structured compute",
) -> ExternalAgentResponse | None:
    if is_legacy_primary_agent_id(agent_id):
        return _error_response(
            request_id=request_id,
            agent_id=agent_id,
            external_agent_id=external_agent_id,
            legacy_agent_id=legacy_agent_id,
            error=legacy_agent_id_error(agent_id),
            answer="Use the fixed DAG snake_case agent_id as the primary id.",
        )
    if not target.strip():
        return _error_response(
            request_id=request_id,
            agent_id=agent_id,
            external_agent_id=external_agent_id,
            legacy_agent_id=legacy_agent_id,
            error=target_required_error(),
            answer="Provide a target before running the sample service.",
        )
    if not question.strip():
        return _error_response(
            request_id=request_id,
            agent_id=agent_id,
            external_agent_id=external_agent_id,
            legacy_agent_id=legacy_agent_id,
            error=empty_question_error(),
            answer="Provide a non-empty question before invoking the sample service.",
        )
    return None


@app.get("/health", response_model=ExternalAgentHealth)
async def health() -> ExternalAgentHealth:
    """Return safe health metadata for local readiness review."""
    return ExternalAgentHealth(
        agent_id=FIXED_DAG_AGENT_ID,
        external_agent_id=EXTERNAL_AGENT_ID,
        agent_name=AGENT_NAME,
        version=VERSION,
        legacy_agent_id=LEGACY_AGENT_ID,
        capabilities=[
            "fixed_dag_external_scaffold",
            "structured_response",
            "fail_soft",
            "compute_endpoint",
            "point_in_time",
            "idempotent",
            "deterministic",
            "graceful_degradation",
        ],
        input_modes=["structured", "question"],
        output_modes=["external_agent_response_v0", "agent_conclusion_v1"],
        supported_dimensions=["value"],
        llm_configured=False,
        tools_configured=False,
        data_ready=True,
        max_concurrency=1,
        timeout_seconds=30.0,
        implementation_notes=IMPLEMENTATION_NOTES,
        warnings=[
            "sample-only; not registered in the active fixed DAG graph",
            "runtime_bindings remain disabled and not live verified",
        ],
    )


@app.post("/v1/agent/compute", response_model=ExternalAgentResponse)
async def compute(req: ComputeRequest) -> ExternalAgentResponse:
    """Return deterministic structured output from the shared compute core."""
    validation_error = _validate_request_ids(
        request_id=req.request_id,
        agent_id=req.agent_id,
        external_agent_id=req.external_agent_id,
        legacy_agent_id=req.legacy_agent_id,
        target=req.target,
    )
    if validation_error is not None:
        return validation_error

    dimension = str(req.context.get("dimension", "value"))
    if dimension not in DIMENSION_LABELS:
        dimension = "value"
    tool_result = compute_core(
        agent_id=req.agent_id,
        external_agent_id=req.external_agent_id,
        target=req.target,
        as_of=req.as_of,
        dimension=dimension,  # type: ignore[arg-type]
        options=req.options,
    )
    return ExternalAgentResponse(
        request_id=req.request_id,
        agent_id=req.agent_id,
        external_agent_id=req.external_agent_id,
        legacy_agent_id=req.legacy_agent_id,
        status=tool_result.status,
        answer="",
        key_points=[],
        tool_result=tool_result,
        confidence=tool_result.confidence,
        warnings=tool_result.warnings,
        errors=[],
    )


@app.post("/v1/agent/invoke", response_model=ExternalAgentResponse)
async def invoke(req: ExternalAgentRequest) -> ExternalAgentResponse:
    """Return an explanation shell over the shared deterministic compute core."""
    validation_error = _validate_request_ids(
        request_id=req.request_id,
        agent_id=req.agent_id,
        external_agent_id=req.external_agent_id,
        legacy_agent_id=req.legacy_agent_id,
        target=req.target,
        question=req.question,
    )
    if validation_error is not None:
        return validation_error

    dimension = str(req.context.get("dimension", "value"))
    if dimension not in DIMENSION_LABELS:
        dimension = "value"
    tool_result = compute_core(
        agent_id=req.agent_id,
        external_agent_id=req.external_agent_id,
        target=req.target,
        as_of=req.as_of,
        dimension=dimension,  # type: ignore[arg-type]
        options=req.options,
    )
    return ExternalAgentResponse(
        request_id=req.request_id,
        agent_id=req.agent_id,
        external_agent_id=req.external_agent_id,
        legacy_agent_id=req.legacy_agent_id,
        status=tool_result.status,
        answer=(
            f"Sample-only deterministic explanation for {tool_result.target}: "
            f"{tool_result.label} with confidence {tool_result.confidence:.2f}."
        ),
        key_points=[
            "compute and invoke share the same deterministic compute_core",
            "the structured tool_result is the source for fixed DAG mapping",
            "this sample did not call a provider or external service",
        ],
        tool_result=tool_result,
        confidence=tool_result.confidence,
        warnings=tool_result.warnings,
        errors=[],
    )
