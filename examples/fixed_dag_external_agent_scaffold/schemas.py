"""Pydantic schemas for the sample-only fixed DAG external agent."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

ExternalStatus = Literal["ok", "partial", "needs_clarification", "error"]
FixedDagDimension = Literal["value", "market", "risk", "macro"]
ImplementationType = Literal[
    "model_compute_agent",
    "llm_structured_agent",
    "data_service_agent",
    "composite_or_decision_agent",
    "rule_or_statistics_agent",
    "hybrid_agent",
]


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
    value: float | None = None
    unit: str = ""


class EventFlag(BaseModel):
    """Optional event flag used by market or risk-aware agents."""

    type: str
    severity: float = Field(ge=0.0, le=1.0)
    direction: Literal["risk", "sentiment", "neutral"] = "neutral"
    as_of: str


class ImplementationNotes(BaseModel):
    """Optional explanatory metadata about the service internals."""

    implementation_type: ImplementationType
    uses_llm: bool = False
    llm_role: str = ""
    compute_core: str = ""
    explanation_layer: str = ""


class ExternalAgentHealth(BaseModel):
    """Safe health payload for external-agent readiness review."""

    schema_version: Literal["external_agent_health_v0"] = "external_agent_health_v0"
    status: Literal["ok", "degraded", "error"] = "ok"
    agent_id: str
    external_agent_id: str
    agent_name: str
    version: str
    fixed_dag_agent_id: str
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
    implementation_notes: ImplementationNotes
    warnings: list[str] = Field(default_factory=list)


class ExternalAgentRequest(BaseModel):
    """Natural-language invoke request using current fixed DAG ids."""

    schema_version: Literal["external_agent_request_v0"] = "external_agent_request_v0"
    request_id: str
    agent_id: str
    external_agent_id: str
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
    target: str
    as_of: str
    language: str = "zh-CN"
    context: dict[str, Any] = Field(default_factory=dict)
    options: dict[str, Any] = Field(default_factory=dict)


class AgentConclusionToolResult(BaseModel):
    """External agent-level result that maps to conclusion_object_v1."""

    schema_version: Literal["agent_conclusion_v1"] = "agent_conclusion_v1"
    agent_id: str
    external_agent_id: str
    dimension: FixedDagDimension
    target: str
    stance: float = Field(ge=-1.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)
    label: str
    evidence: list[EvidenceItem] = Field(default_factory=list)
    event_flags: list[EventFlag] = Field(default_factory=list)
    as_of: str
    data_as_of: str
    status: Literal["ok", "partial", "error"] = "ok"
    warnings: list[str] = Field(default_factory=list)
    implementation_notes: ImplementationNotes


class ExternalAgentResponse(BaseModel):
    """Standard external response envelope for compute and invoke."""

    schema_version: Literal["external_agent_response_v0"] = "external_agent_response_v0"
    request_id: str
    agent_id: str
    external_agent_id: str
    status: ExternalStatus
    answer: str = ""
    key_points: list[str] = Field(default_factory=list)
    tool_result: AgentConclusionToolResult | dict[str, Any] = Field(default_factory=dict)
    confidence: float = Field(ge=0.0, le=1.0)
    warnings: list[str] = Field(default_factory=list)
    errors: list[TypedError] = Field(default_factory=list)
