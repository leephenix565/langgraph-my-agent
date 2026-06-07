"""Pydantic schemas and semantic validators for the fixed DAG scaffold.

This package is sample-only. The schemas define the target external handoff
contract for future fixed DAG adapters; they do not register or enable any
main-system runtime binding.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from datetime import date
from typing import Any, Literal, TypeAlias

from pydantic import BaseModel, Field

ExternalStatus = Literal["ok", "partial", "needs_clarification", "error"]
FixedDagDimension = Literal["value", "market", "risk", "macro"]
DirectionRole = Literal["direction"]
AgentConclusionRole = Literal["direction", "gate_member"]
GateRole = Literal["gate"]
RegulatorRole = Literal["regulator"]
ImplementationType = Literal[
    "model_compute_agent",
    "llm_structured_agent",
    "data_service_agent",
    "composite_or_decision_agent",
    "rule_or_statistics_agent",
    "deterministic_rule_agent",
    "hybrid_agent",
    "llm_function_call_agent",
]

DIM_ALIAS = {
    "价值": "value",
    "市場面": "market",
    "市场面": "market",
    "风险": "risk",
    "風險": "risk",
    "宏观": "macro",
    "宏觀": "macro",
}
CANONICAL_DIMENSIONS = {"value", "market", "risk", "macro"}
DIRECTION_DIMENSIONS = {"value", "market"}
_ANN_ID_PATTERN = re.compile(r"^a\d{2}_")


class TypedError(BaseModel):
    """Structured error that avoids raw traceback and secret leakage."""

    error_code: str
    error_message: str
    stage: str
    recoverable: bool
    retryable: bool
    user_action_required: bool
    suggested_user_action: str = ""


class EvidenceItem(BaseModel):
    """Evidence item suitable for later fixed DAG mapping."""

    fact: str
    source: str
    as_of: str
    data_as_of: str
    publish_time: str | None = None
    value: float | None = None
    unit: str = ""


class EventFlag(BaseModel):
    """Optional event flag used by market, risk, macro, or eval agents."""

    type: str
    severity: float = Field(ge=0.0, le=1.0)
    direction: Literal["value", "market", "risk", "macro", "sentiment", "neutral"] = (
        "neutral"
    )
    as_of: str


class ImplementationNotes(BaseModel):
    """Optional explanatory metadata about the service internals."""

    implementation_type: ImplementationType
    uses_llm: bool = False
    llm_role: str = ""
    compute_core: str = ""
    explanation_layer: str = ""


class DimensionMember(BaseModel):
    """Structured L3 member contribution used by dimension composites."""

    agent_id: str
    stance: float = Field(ge=-1.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)
    weight: float = Field(ge=0.0, le=1.0)
    status: ExternalStatus = "ok"


class ReasoningStep(BaseModel):
    """Minimal typed reasoning step for L4 decision trace depth checks."""

    stage: int | str
    type: str = ""
    claim: str = ""
    inputs: list[str] | dict[str, Any] | list[Any] | None = None


class ExternalAgentHealth(BaseModel):
    """Safe health payload for external-agent readiness review."""

    schema_version: Literal["external_agent_health_v0"] = "external_agent_health_v0"
    status: Literal["ok", "degraded", "error"] = "ok"
    agent_id: str
    external_agent_id: str
    agent_name: str
    version: str
    legacy_agent_id: str = ""
    capabilities: list[str] = Field(default_factory=list)
    input_modes: list[str] = Field(default_factory=list)
    output_modes: list[str] = Field(default_factory=list)
    supported_dimensions: list[FixedDagDimension] = Field(default_factory=list)
    llm_configured: bool = False
    tools_configured: bool = False
    data_ready: bool = True
    max_concurrency: int = 1
    timeout_seconds: float = 30.0
    implementation_notes: ImplementationNotes | None = None
    warnings: list[str] = Field(default_factory=list)


class ExternalAgentRequest(BaseModel):
    """Natural-language invoke request using current fixed DAG ids."""

    schema_version: Literal["external_agent_request_v0"] = "external_agent_request_v0"
    request_id: str
    agent_id: str
    external_agent_id: str
    legacy_agent_id: str = ""
    target: str
    question: str
    as_of: str
    language: str = "zh-CN"
    context: dict[str, Any] = Field(default_factory=dict)
    options: dict[str, Any] = Field(default_factory=dict)


class ComputeRequest(BaseModel):
    """Structured compute request with no natural-language requirement."""

    schema_version: Literal["external_agent_request_v0"] = "external_agent_request_v0"
    request_id: str
    agent_id: str
    external_agent_id: str
    legacy_agent_id: str = ""
    target: str
    as_of: str
    language: str = "zh-CN"
    context: dict[str, Any] = Field(default_factory=dict)
    options: dict[str, Any] = Field(default_factory=dict)


class AgentConclusionToolResult(BaseModel):
    """L2 external agent result that maps to conclusion_object_v1."""

    schema_version: Literal["agent_conclusion_v1"] = "agent_conclusion_v1"
    agent_id: str
    external_agent_id: str
    legacy_agent_id: str = ""
    dimension: FixedDagDimension
    role: AgentConclusionRole = "direction"
    target: str
    stance: float | None = Field(None, ge=-1.0, le=1.0)
    risk_score: float | None = Field(None, ge=0.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)
    label: str
    raw_output: dict[str, Any] = Field(default_factory=dict)
    quality: dict[str, Any] = Field(default_factory=dict)
    evidence: list[EvidenceItem] = Field(default_factory=list)
    event_flags: list[EventFlag] = Field(default_factory=list)
    as_of: str
    data_as_of: str
    status: ExternalStatus = "ok"
    warnings: list[str] = Field(default_factory=list)
    implementation_notes: ImplementationNotes | None = None


class DimensionConclusionToolResult(BaseModel):
    """L3 value or market composite result."""

    schema_version: Literal["dimension_conclusion_v1"] = "dimension_conclusion_v1"
    agent_id: str
    external_agent_id: str = ""
    legacy_agent_id: str = ""
    dimension: FixedDagDimension
    role: DirectionRole = "direction"
    target: str
    stance: float = Field(ge=-1.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)
    members: list[DimensionMember]
    dispersion: float = Field(ge=0.0)
    fair_value_range: dict[str, float | None] | None = None
    timing_signal: str | None = None
    evidence: list[EvidenceItem] = Field(default_factory=list)
    event_flags: list[EventFlag] = Field(default_factory=list)
    as_of: str
    data_as_of: str
    status: ExternalStatus = "ok"
    implementation_notes: ImplementationNotes | None = None


class RiskConclusionToolResult(BaseModel):
    """L3 risk gate result. Risk has no direction stance."""

    schema_version: Literal["risk_conclusion_v1"] = "risk_conclusion_v1"
    agent_id: str
    external_agent_id: str = ""
    legacy_agent_id: str = ""
    dimension: Literal["risk"] = "risk"
    role: GateRole = "gate"
    target: str
    gate: Literal["pass", "penalty", "veto", "manual_review"]
    risk_score: float = Field(ge=0.0, le=1.0)
    penalty: float = Field(ge=0.0, le=1.0)
    triggered_flags: list[str] = Field(default_factory=list)
    red_lines: list[str] = Field(default_factory=list)
    evidence: list[EvidenceItem] = Field(default_factory=list)
    event_flags: list[EventFlag] = Field(default_factory=list)
    as_of: str
    data_as_of: str
    status: ExternalStatus = "ok"
    implementation_notes: ImplementationNotes | None = None


class MacroConclusionToolResult(BaseModel):
    """L3 macro regulator result. Macro has no direction stance."""

    schema_version: Literal["macro_conclusion_v1"] = "macro_conclusion_v1"
    agent_id: str
    external_agent_id: str = ""
    legacy_agent_id: str = ""
    dimension: Literal["macro"] = "macro"
    role: RegulatorRole = "regulator"
    target: str = ""
    scope: str = ""
    regime: str
    dimension_weights: dict[str, float]
    risk_sensitivity: float = Field(ge=0.0, le=1.0)
    style_bias: dict[str, float] = Field(default_factory=dict)
    evidence: list[EvidenceItem] = Field(default_factory=list)
    event_flags: list[EventFlag] = Field(default_factory=list)
    as_of: str
    data_as_of: str
    status: ExternalStatus = "ok"
    implementation_notes: ImplementationNotes | None = None


class DecisionConclusionToolResult(BaseModel):
    """L4 decision synthesis result."""

    schema_version: Literal["decision_conclusion_v1"] = "decision_conclusion_v1"
    agent_id: str
    external_agent_id: str = ""
    legacy_agent_id: str = ""
    target: str
    decision: str
    score: float = Field(ge=-1.0, le=1.0)
    target_price_range: dict[str, float | None]
    dimension_views: dict[str, dict[str, Any]]
    calculation_trace: dict[str, Any]
    reasoning_trace: list[ReasoningStep]
    conflicts: list[dict[str, Any]] = Field(default_factory=list)
    evidence: list[EvidenceItem] = Field(default_factory=list)
    event_flags: list[EventFlag] = Field(default_factory=list)
    as_of: str
    data_as_of: str | None = None
    status: ExternalStatus = "ok"
    confidence: float = Field(ge=0.0, le=1.0)
    implementation_notes: ImplementationNotes | None = None


class EvalRecord(BaseModel):
    """Replay, routing F1, reasoning F1, and backtest evaluation record."""

    schema_version: Literal["eval_record_v1"] = "eval_record_v1"
    metric: str
    gold: dict[str, Any] | list[Any] | str | float | int | bool | None
    pred: dict[str, Any] | list[Any] | str | float | int | bool | None
    tp: int = Field(ge=0)
    fp: int = Field(ge=0)
    fn: int = Field(ge=0)
    replay_id: str
    trace_id: str
    as_of: str
    status: ExternalStatus = "ok"


class FixedDagPlanPayload(BaseModel):
    """External planning payload for route and replay planning."""

    schema_version: Literal["fixed_dag_plan_v1"] = "fixed_dag_plan_v1"
    task: str
    targets: list[str]
    selected_dimensions: list[FixedDagDimension]
    selected_agents: list[str]
    route_prior: dict[str, Any] = Field(default_factory=dict)
    fallback: dict[str, Any] = Field(default_factory=dict)
    as_of: str
    status: ExternalStatus = "ok"


class DataBundlePayload(BaseModel):
    """L1 point-in-time data bundle for replayable downstream analysis."""

    schema_version: Literal["data_bundle_v1"] = "data_bundle_v1"
    target: str
    as_of: str
    data_as_of: str
    publish_time: str
    snapshot_id: str
    sources: list[dict[str, Any] | str]
    feature_bundle: dict[str, Any] = Field(default_factory=dict)
    missing_fields: list[str] = Field(default_factory=list)
    status: ExternalStatus = "ok"


ToolResultPayload: TypeAlias = (
    AgentConclusionToolResult
    | DimensionConclusionToolResult
    | RiskConclusionToolResult
    | MacroConclusionToolResult
    | DecisionConclusionToolResult
    | EvalRecord
    | FixedDagPlanPayload
    | DataBundlePayload
)


class ExternalAgentResponse(BaseModel):
    """Standard external response envelope for compute and invoke."""

    schema_version: Literal["external_agent_response_v0"] = "external_agent_response_v0"
    request_id: str
    agent_id: str
    external_agent_id: str
    legacy_agent_id: str = ""
    status: ExternalStatus
    answer: str = ""
    key_points: list[str] = Field(default_factory=list)
    tool_result: ToolResultPayload | dict[str, Any] = Field(default_factory=dict)
    confidence: float = Field(ge=0.0, le=1.0)
    warnings: list[str] = Field(default_factory=list)
    errors: list[TypedError] = Field(default_factory=list)


def normalize_dimension(value: Any) -> str:
    """Normalize Chinese migration aliases into canonical English dimensions."""
    text = str(value or "").strip()
    normalized = DIM_ALIAS.get(text, text)
    if normalized not in CANONICAL_DIMENSIONS:
        raise ValueError(f"unsupported_dimension:{text}")
    return normalized


def normalize_dimensions(values: Sequence[Any]) -> list[str]:
    """Normalize a list of dimensions while preserving order."""
    return [normalize_dimension(value) for value in values]


def _is_legacy_primary_agent_id(agent_id: Any) -> bool:
    return bool(_ANN_ID_PATTERN.match(str(agent_id or "")))


def _as_mapping(payload: Any) -> dict[str, Any]:
    if isinstance(payload, BaseModel):
        return payload.model_dump(mode="json")
    if isinstance(payload, Mapping):
        return dict(payload)
    raise TypeError("payload_not_mapping")


def _normalize_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    normalized = dict(payload)
    if "dimension" in normalized:
        normalized["dimension"] = normalize_dimension(normalized["dimension"])
    if "selected_dimensions" in normalized and isinstance(
        normalized["selected_dimensions"], list
    ):
        normalized["selected_dimensions"] = normalize_dimensions(
            normalized["selected_dimensions"]
        )
    if "dimension_weights" in normalized and isinstance(
        normalized["dimension_weights"], Mapping
    ):
        normalized["dimension_weights"] = {
            normalize_dimension(key): float(value)
            for key, value in normalized["dimension_weights"].items()
        }
    return normalized


def _not_after(left: Any, right: Any) -> bool:
    return _norm_date(left) <= _norm_date(right)


def _norm_date(value: Any) -> str:
    """Normalize date-like inputs to YYYYMMDD for point-in-time comparisons."""
    text = str(value or "").strip()
    if not text:
        raise ValueError("empty_date")
    if re.fullmatch(r"\d{8}(\d{6})?", text):
        date_text = text[:8]
        year = int(date_text[0:4])
        month = int(date_text[4:6])
        day = int(date_text[6:8])
        date(year, month, day)
        return date_text
    match = re.match(r"^(\d{4})-(\d{2})-(\d{2})(?:$|[T\s].*)", text)
    if match:
        year, month, day = (int(part) for part in match.groups())
        date(year, month, day)
        return f"{year:04d}{month:02d}{day:02d}"
    raise ValueError("unsupported_date_format")


def _weights_sum_to_one(weights: Mapping[str, Any], tolerance: float = 0.001) -> bool:
    try:
        total = sum(float(value) for value in weights.values())
    except (TypeError, ValueError):
        return False
    return abs(total - 1.0) <= tolerance


def _dimension_member_weight_sum(members: Sequence[Mapping[str, Any]]) -> float:
    return sum(float(member["weight"]) for member in members)


def _dimension_member_weighted_stance(members: Sequence[Mapping[str, Any]]) -> float:
    return sum(float(member["weight"]) * float(member["stance"]) for member in members)


def _validate_primary_agent_id(payload: Mapping[str, Any]) -> tuple[bool, str]:
    if _is_legacy_primary_agent_id(payload.get("agent_id")):
        return False, "legacy_agent_id_as_primary"
    return True, "ok"


def _validate_evidence(payload: Mapping[str, Any]) -> tuple[bool, str]:
    if payload.get("status") not in {"ok", "complete"}:
        return True, "ok"
    evidence = payload.get("evidence")
    if not isinstance(evidence, list) or not evidence:
        return False, "evidence_missing"
    as_of = payload.get("as_of")
    for item in evidence:
        if not isinstance(item, Mapping):
            return False, "invalid_evidence_item"
        if not item.get("fact") or not item.get("source"):
            return False, "evidence_fact_or_source_missing"
        item_as_of = item.get("as_of")
        item_data_as_of = item.get("data_as_of")
        if not (item_as_of or item_data_as_of):
            return False, "evidence_time_missing"
        if item_as_of and as_of and not _not_after(item_as_of, as_of):
            return False, "evidence_as_of_after_payload_as_of"
        if item_data_as_of and as_of and not _not_after(item_data_as_of, as_of):
            return False, "evidence_data_as_of_after_payload_as_of"
        if item.get("publish_time") and as_of and not _not_after(
            item.get("publish_time"), as_of
        ):
            return False, "evidence_publish_time_after_as_of"
    return True, "ok"


def _validate_times(payload: Mapping[str, Any]) -> tuple[bool, str]:
    as_of = payload.get("as_of")
    data_as_of = payload.get("data_as_of")
    publish_time = payload.get("publish_time")
    if data_as_of is not None and not _not_after(data_as_of, as_of):
        return False, "data_as_of_after_as_of"
    if publish_time is not None and not _not_after(publish_time, as_of):
        return False, "publish_time_after_as_of"
    return True, "ok"


def _validate_common(payload: Mapping[str, Any]) -> tuple[bool, str]:
    for check in (_validate_primary_agent_id, _validate_times, _validate_evidence):
        valid, reason = check(payload)
        if not valid:
            return valid, reason
    return True, "ok"


def _model_validate(model: type[BaseModel], payload: Mapping[str, Any]) -> BaseModel:
    return model.model_validate(payload)


def validate_tool_result(payload: Any) -> tuple[bool, str]:
    """Validate a v2.3.1 domain payload by schema_version and semantic rules."""
    try:
        raw = _as_mapping(payload)
        schema_version = str(raw.get("schema_version") or "")
        if schema_version == "external_agent_response_v0":
            tool_result = raw.get("tool_result")
            if raw.get("status") == "ok" and not tool_result:
                return False, "tool_result_missing"
            if not tool_result:
                return True, "ok"
            return validate_tool_result(tool_result)

        normalized = _normalize_payload(raw)
        if schema_version == "agent_conclusion_v1":
            _model_validate(AgentConclusionToolResult, normalized)
            role = normalized.get("role", "direction")
            if role == "direction":
                if normalized.get("stance") is None:
                    return False, "direction_stance_missing"
                if normalized.get("risk_score") is not None:
                    return False, "direction_must_not_have_risk_score"
            elif role == "gate_member":
                if normalized.get("risk_score") is None:
                    return False, "gate_member_risk_score_missing"
            else:
                return False, "invalid_role"
            if not isinstance(normalized.get("raw_output", {}), Mapping):
                return False, "raw_output_must_be_dict"
            if not isinstance(normalized.get("quality", {}), Mapping):
                return False, "quality_must_be_dict"
            return _validate_common(normalized)

        if schema_version == "dimension_conclusion_v1":
            _model_validate(DimensionConclusionToolResult, normalized)
            if normalized.get("dimension") not in {"value", "market"}:
                return False, "dimension_conclusion_invalid_dimension"
            if normalized.get("role") != "direction":
                return False, "invalid_role"
            members = normalized.get("members")
            if not isinstance(members, list) or not members:
                return False, "dimension_members_missing"
            if not all(isinstance(member, Mapping) for member in members):
                return False, "dimension_members_must_be_objects"
            if abs(_dimension_member_weight_sum(members) - 1.0) > 0.01:
                return False, "member_weights_sum_not_one"
            if abs(_dimension_member_weighted_stance(members) - float(normalized["stance"])) > 0.02:
                return False, "weighted_stance_mismatch"
            return _validate_common(normalized)

        if schema_version == "risk_conclusion_v1":
            if "stance" in raw:
                return False, "risk_must_not_have_stance"
            _model_validate(RiskConclusionToolResult, normalized)
            if normalized.get("role") != "gate":
                return False, "risk_role_must_be_gate"
            return _validate_common(normalized)

        if schema_version == "macro_conclusion_v1":
            if "stance" in raw:
                return False, "macro_must_not_have_stance"
            _model_validate(MacroConclusionToolResult, normalized)
            if normalized.get("role") != "regulator":
                return False, "macro_role_must_be_regulator"
            weights = normalized.get("dimension_weights")
            if not isinstance(weights, Mapping):
                return False, "dimension_weights_missing"
            if set(weights) - DIRECTION_DIMENSIONS:
                return False, "dimension_weights_invalid_keys"
            if not _weights_sum_to_one(weights):
                return False, "dimension_weights_sum_not_one"
            return _validate_common(normalized)

        if schema_version == "decision_conclusion_v1":
            _model_validate(DecisionConclusionToolResult, normalized)
            reasoning_trace = normalized.get("reasoning_trace") or []
            if not all(isinstance(step, Mapping) and step.get("stage") is not None for step in reasoning_trace):
                return False, "reasoning_trace_stage_missing"
            if len({str(step["stage"]) for step in reasoning_trace}) < 3:
                return False, "reasoning_trace_stage_depth_too_shallow"
            calculation_trace = normalized.get("calculation_trace")
            if not isinstance(calculation_trace, Mapping):
                return False, "calculation_trace_missing"
            if "final_score" not in calculation_trace:
                return False, "calculation_trace_final_score_missing"
            if abs(float(calculation_trace["final_score"]) - float(normalized["score"])) > 0.01:
                return False, "score_mismatch"
            return _validate_common(normalized)

        if schema_version == "eval_record_v1":
            _model_validate(EvalRecord, normalized)
            return True, "ok"

        if schema_version == "fixed_dag_plan_v1":
            _model_validate(FixedDagPlanPayload, normalized)
            return _validate_primary_agent_id(normalized)

        if schema_version == "data_bundle_v1":
            _model_validate(DataBundlePayload, normalized)
            if not normalized.get("snapshot_id"):
                return False, "snapshot_id_missing"
            return _validate_times(normalized)

        return False, "unsupported_schema_version"
    except Exception as exc:  # noqa: BLE001 - validator returns safe reason strings.
        return False, f"validation_error:{exc.__class__.__name__}"
