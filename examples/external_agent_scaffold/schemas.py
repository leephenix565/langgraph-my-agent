from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class TypedError(BaseModel):
    error_code: str
    error_message: str
    stage: str
    recoverable: bool
    retryable: bool
    user_action_required: bool
    suggested_user_action: Optional[str] = None


class ExternalAgentHealth(BaseModel):
    schema_version: Literal["external_agent_health_v0"]
    status: Literal["ok", "degraded", "error"]
    agent_id: str
    agent_name: str
    version: str
    capabilities: List[str]
    input_modes: List[str]
    output_modes: List[str]
    llm_configured: bool
    tools_configured: bool
    data_ready: bool
    max_concurrency: int
    timeout_seconds: float
    warnings: List[str] = Field(default_factory=list)


class ExternalAgentRequest(BaseModel):
    schema_version: Literal["external_agent_request_v0"]
    request_id: str
    agent_id: Optional[str] = None
    question: str
    language: str = "zh-CN"
    subtask: Optional[str] = None
    shared_context: Dict[str, Any] = Field(default_factory=dict)
    history: List[Dict[str, str]] = Field(default_factory=list)
    router_plan_summary: Dict[str, Any] = Field(default_factory=dict)
    options: Dict[str, Any] = Field(default_factory=dict)


class ExternalAgentResponse(BaseModel):
    schema_version: Literal["external_agent_response_v0"]
    request_id: str
    agent_id: str
    status: Literal["ok", "partial", "needs_clarification", "error"]
    question: str
    parsed_request: Dict[str, Any] = Field(default_factory=dict)
    tool_result: Dict[str, Any] = Field(default_factory=dict)
    native_answer: str = ""
    answer: str = ""
    answer_mode: str = "structured"
    confidence: Optional[float] = None
    key_points: List[str] = Field(default_factory=list)
    evidence: List[Dict[str, Any]] = Field(default_factory=list)
    data_sources: List[Dict[str, Any]] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    errors: List[TypedError] = Field(default_factory=list)

