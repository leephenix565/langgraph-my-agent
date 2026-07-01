# ruff: noqa: D101
"""Public API contracts for the chat-first web client."""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Union

from pydantic import BaseModel, ConfigDict, Field

FinalSource = Literal["reset_skeleton"]
ContinuityMode = Literal["persistent", "replay"]
PublicRoutingMode = Literal["selected"]
AgentLayer = Literal["L1", "L2", "L3", "L4"]
DagStepStatus = Literal[
    "complete",
    "running",
    "queued",
    "pending_implementation",
    "partial",
    "error",
    "skipped",
    "blocked",
    "failed",
]
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


class ReportSectionModel(PublicBaseModel):
    id: str
    title: str
    content: str


class AnswerCardModel(PublicBaseModel):
    answer: str
    finalSource: FinalSource
    confidence: str | None = None
    sections: List[ReportSectionModel] = Field(default_factory=list)
    citations: List[CitationModel] = Field(default_factory=list)
    evidenceCards: List[EvidenceCardModel] = Field(default_factory=list)
    evidenceCount: int | None = None
    limitations: List[str] = Field(default_factory=list)


class StructuredInputModel(PublicBaseModel):
    task: str
    context: str | None = None
    materials: List[str] = Field(default_factory=list)
    urlReferences: List[str] = Field(default_factory=list)
    constraints: str | None = None
    outputPreference: str | None = None


class WorkflowStageModel(PublicBaseModel):
    key: WorkflowStageKey
    title: str
    stepIds: List[str] = Field(default_factory=list)


class DagStepModel(PublicBaseModel):
    id: str
    stage: WorkflowStageKey
    agentId: str | None = None
    dimension: str | None = None
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
    executionStatus: str | None = None
    fallbackUsed: bool = False
    limitations: List[str] = Field(default_factory=list)
    selectedRoutingRequested: bool = False
    selectedRoutingFallback: bool = False
    fallbackReason: str | None = None
    routeGranularity: str | None = None
    selectedDimensions: List[str] = Field(default_factory=list)
    expandedAgentCount: int | None = None
    providerRouterEnabled: bool = False
    providerRouterInvoked: bool = False
    providerRouterMode: str | None = None
    providerRouterParseOk: bool = False
    providerRouterFallbackReason: str | None = None
    providerRouterErrorCode: str | None = None
    providerRouterSelectedDimensions: List[str] = Field(default_factory=list)
    performanceTelemetry: PerformanceTelemetryModel | None = None
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
    currentStage: WorkflowStageKey | None = None
    completedSteps: List[str] = Field(default_factory=list)
    executionBatches: List[List[str]] = Field(default_factory=list)
    stepResults: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    finalSource: FinalSource
    provenanceNote: str
    provenance: WorkflowProvenanceModel | None = None


class PublicTurn(PublicBaseModel):
    id: str
    role: Literal["user", "assistant"]
    text: str
    createdAt: str
    structuredInput: StructuredInputModel | None = None
    answerCard: AnswerCardModel | None = None
    workflow: WorkflowModel | None = None
    runId: str | None = None
    continuityMode: ContinuityMode | None = None


class ChatSessionSummary(PublicBaseModel):
    id: str
    title: str
    updatedAt: str
    preview: str
    finalSource: FinalSource
    phase: str
    active: bool | None = None
    continuityMode: ContinuityMode | None = None


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
    roleType: str | None = None
    defaultEnabled: bool


class AgentCatalogLayerModel(PublicBaseModel):
    layer: AgentLayer
    agents: List[PublicAgentMetadataModel] = Field(default_factory=list)


class AgentCatalogResponse(PublicBaseModel):
    totals: AgentCatalogTotalsModel
    layers: List[AgentCatalogLayerModel] = Field(default_factory=list)
    disabledAgents: List[PublicAgentMetadataModel] = Field(default_factory=list)


class CreateThreadRequest(PublicBaseModel):
    title: str | None = None


class PublicRoutingRequest(PublicBaseModel):
    mode: PublicRoutingMode


class SendMessageRequest(PublicBaseModel):
    text: str
    structuredInput: StructuredInputModel | None = None
    routing: PublicRoutingRequest | None = None


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
    currentStage: WorkflowStageKey | None = None


class WorkflowSnapshotEventData(PublicBaseModel):
    workflow: WorkflowModel
    runId: str | None = None
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
    hint: str | None = None


class CheckpointerStatus(PublicBaseModel):
    enabled: bool
    mode: str
    status: Literal["enabled", "disabled", "unavailable"]
    code: str
    hint: str | None = None


class ErrorDetail(PublicBaseModel):
    code: str
    message: str
    category: ErrorCategory


class AgentPerformanceTelemetryModel(PublicBaseModel):
    agentId: str
    stage: str | None = None
    dimension: str | None = None
    runtimeSource: str | None = None
    elapsedMs: int | None = None
    httpStatusClass: str | None = None
    mappedSchema: str | None = None
    mappedStatus: str | None = None
    fallback: bool = False
    degraded: bool = False
    timeout: bool = False
    providerCallCount: int | None = None
    providerTotalMs: int | None = None
    dbQueryCount: int | None = None
    dbTotalMs: int | None = None
    cacheHit: bool | None = None
    telemetryUnavailableReason: str | None = None


class PerformanceTelemetryModel(PublicBaseModel):
    requestTotalMs: int | None = None
    graphTotalMs: int | None = None
    routePlannerMs: int | None = None
    executeFixedDagMs: int | None = None
    finalEmitMs: int | None = None
    computeCallCount: int = 0
    providerCallCount: int | None = None
    providerTotalMs: int | None = None
    dbQueryCount: int | None = None
    dbTotalMs: int | None = None
    perAgentCompute: List[AgentPerformanceTelemetryModel] = Field(default_factory=list)
    instrumentationGaps: List[str] = Field(default_factory=list)


class HealthResponse(PublicBaseModel):
    status: Literal["ok"]
    apiVersion: str
    publicApiContractVersion: str = "public_api_contract_v4"
    routingRequestSupported: bool = True
    selectedRoutingRequestSchema: str = "routing.mode.selected"
    computeRegistryVersion: str | None = None
    computeRegistryAgentCount: int | None = None
    processStartTime: str | None = None
    processUptimeSeconds: int | None = None
    sourceVersionMarker: str | None = None
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
