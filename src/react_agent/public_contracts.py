# ruff: noqa: D101
"""Public API contracts for the chat-first web client."""

from __future__ import annotations

from typing import Dict, List, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field

FinalSource = Literal["reset_skeleton"]
ContinuityMode = Literal["persistent", "replay"]
AgentLayer = Literal["L1", "L2", "L3", "L4"]
DagStepStatus = Literal["complete", "running", "queued", "pending_implementation", "partial", "error"]
DimensionStatus = Literal["complete", "running", "queued", "pending_implementation", "partial", "error"]
OverallStatus = Literal["ready", "degraded"]
ErrorCategory = Literal["runtime", "provider_env", "store", "contract", "request"]
StreamEventType = Literal["run.started", "workflow.stage", "workflow.snapshot", "answer.final", "error"]
WorkflowStageKey = Literal[
    "planning",
    "evidence",
    "l2_analysis",
    "dimension_composite",
    "decision",
    "report",
]
WorkflowStageStatus = Literal["waiting", "running", "completed", "failed"]


class PublicBaseModel(BaseModel):
    """Base model that keeps the public contract closed."""

    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
        serialize_by_alias=True,
    )


class CitationModel(PublicBaseModel):
    label: str
    note: str


class EvidenceCardModel(PublicBaseModel):
    title: str
    note: str = ""


class AnswerCardModel(PublicBaseModel):
    answer: str
    finalSource: FinalSource
    confidence: Optional[str] = None
    citations: List[CitationModel] = Field(default_factory=list)
    evidenceCards: List[EvidenceCardModel] = Field(default_factory=list)
    evidenceCount: Optional[int] = None


class StructuredInputModel(PublicBaseModel):
    task: str
    context: Optional[str] = None
    materials: List[str] = Field(default_factory=list)
    urlReferences: List[str] = Field(default_factory=list)
    constraints: Optional[str] = None
    outputPreference: Optional[str] = None


class WorkflowStageModel(PublicBaseModel):
    key: WorkflowStageKey
    title: str
    stepIds: List[str] = Field(default_factory=list)


class DagStepModel(PublicBaseModel):
    id: str
    stage: WorkflowStageKey
    agentId: Optional[str] = None
    dimension: Optional[str] = None
    title: str
    summary: str
    status: DagStepStatus


class DimensionGroupModel(PublicBaseModel):
    id: str
    title: str
    stepIds: List[str] = Field(default_factory=list)
    status: DimensionStatus
    summary: str


class WorkflowProvenanceModel(PublicBaseModel):
    source: FinalSource
    continuityMode: ContinuityMode
    providerInvoked: bool = False
    externalInvoked: bool = False
    summary: str


class WorkflowModel(PublicBaseModel):
    schema_: Literal["workflow_snapshot_v2"] = Field(
        default="workflow_snapshot_v2",
        alias="schema",
    )
    planId: str
    stages: List[WorkflowStageModel] = Field(default_factory=list)
    dagSteps: List[DagStepModel] = Field(default_factory=list)
    dimensionGroups: List[DimensionGroupModel] = Field(default_factory=list)
    currentStage: Optional[WorkflowStageKey] = None
    completedSteps: List[str] = Field(default_factory=list)
    finalSource: FinalSource
    provenanceNote: str
    provenance: Optional[WorkflowProvenanceModel] = None


class PublicTurn(PublicBaseModel):
    id: str
    role: Literal["user", "assistant"]
    text: str
    createdAt: str
    structuredInput: Optional[StructuredInputModel] = None
    answerCard: Optional[AnswerCardModel] = None
    workflow: Optional[WorkflowModel] = None
    runId: Optional[str] = None
    continuityMode: Optional[ContinuityMode] = None


class ChatSessionSummary(PublicBaseModel):
    id: str
    title: str
    updatedAt: str
    preview: str
    finalSource: FinalSource
    phase: str
    active: Optional[bool] = None
    continuityMode: Optional[ContinuityMode] = None


class PublicThreadDetail(PublicBaseModel):
    thread: ChatSessionSummary
    turns: List[PublicTurn] = Field(default_factory=list)


class ThreadsResponse(PublicBaseModel):
    threads: List[ChatSessionSummary] = Field(default_factory=list)


class AgentCatalogTotalsModel(PublicBaseModel):
    configCount: int
    runtimeCount: int
    disabledIds: List[str] = Field(default_factory=list)


class PublicAgentMetadataModel(PublicBaseModel):
    id: str
    name: str
    description: str
    capabilities: List[str] = Field(default_factory=list)
    layer: AgentLayer
    team: str = ""
    roleType: Optional[str] = None
    defaultEnabled: bool


class AgentCatalogLayerModel(PublicBaseModel):
    layer: AgentLayer
    agents: List[PublicAgentMetadataModel] = Field(default_factory=list)


class AgentCatalogResponse(PublicBaseModel):
    totals: AgentCatalogTotalsModel
    layers: List[AgentCatalogLayerModel] = Field(default_factory=list)
    disabledAgents: List[PublicAgentMetadataModel] = Field(default_factory=list)


class CreateThreadRequest(PublicBaseModel):
    title: Optional[str] = None


class SendMessageRequest(PublicBaseModel):
    text: str
    structuredInput: Optional[StructuredInputModel] = None


class SendMessageResponse(PublicBaseModel):
    thread: ChatSessionSummary
    assistantTurn: PublicTurn
    turns: List[PublicTurn] = Field(default_factory=list)


class WorkflowStageProgressModel(PublicBaseModel):
    key: WorkflowStageKey
    title: str
    status: WorkflowStageStatus


class RunStartedEventData(PublicBaseModel):
    threadId: str
    continuityMode: ContinuityMode


class WorkflowStageEventData(PublicBaseModel):
    stages: List[WorkflowStageProgressModel] = Field(default_factory=list)
    currentStage: Optional[WorkflowStageKey] = None


class WorkflowSnapshotEventData(PublicBaseModel):
    workflow: WorkflowModel
    runId: Optional[str] = None
    continuityMode: ContinuityMode


class AnswerFinalEventData(PublicBaseModel):
    response: SendMessageResponse


class StreamErrorEventData(PublicBaseModel):
    code: str
    message: str
    category: ErrorCategory


class RunStartedEvent(PublicBaseModel):
    type: Literal["run.started"]
    data: RunStartedEventData


class WorkflowStageEvent(PublicBaseModel):
    type: Literal["workflow.stage"]
    data: WorkflowStageEventData


class WorkflowSnapshotEvent(PublicBaseModel):
    type: Literal["workflow.snapshot"]
    data: WorkflowSnapshotEventData


class AnswerFinalEvent(PublicBaseModel):
    type: Literal["answer.final"]
    data: AnswerFinalEventData


class StreamErrorEvent(PublicBaseModel):
    type: Literal["error"]
    data: StreamErrorEventData


PublicStreamEvent = Union[
    RunStartedEvent,
    WorkflowStageEvent,
    WorkflowSnapshotEvent,
    AnswerFinalEvent,
    StreamErrorEvent,
]


class ReadinessSurface(PublicBaseModel):
    status: str
    code: str
    hint: Optional[str] = None


class CheckpointerStatus(PublicBaseModel):
    enabled: bool
    mode: str
    status: Literal["enabled", "disabled", "unavailable"]
    code: str
    hint: Optional[str] = None


class ErrorDetail(PublicBaseModel):
    code: str
    message: str
    category: ErrorCategory


class HealthResponse(PublicBaseModel):
    status: Literal["ok"]
    apiVersion: str
    overallStatus: OverallStatus
    checkpointer: CheckpointerStatus
    continuityDefault: ContinuityMode
    runtime: ReadinessSurface
    providerEnv: ReadinessSurface
    searchEnv: ReadinessSurface
    store: Literal["json-file"]


class StoreEnvelope(PublicBaseModel):
    version: int = 1
    threads: Dict[str, PublicThreadDetail] = Field(default_factory=dict)
