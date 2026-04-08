import type { WorkflowModel, WorkflowStageKey, WorkflowStageProgress } from "./workflow";

export type FinalSource = "mainline" | "baseline" | "fused";
export type ContinuityMode = "persistent" | "replay";
export type OverallStatus = "ready" | "degraded";
export type ErrorCategory = "runtime" | "provider_env" | "store" | "contract" | "request";

export interface CitationModel {
  label: string;
  note: string;
}

export interface EvidenceCardModel {
  title: string;
  note: string;
}

export interface AnswerCardModel {
  answer: string;
  finalSource: FinalSource;
  confidence?: string;
  citations?: CitationModel[];
  evidenceCards?: EvidenceCardModel[];
  evidenceCount?: number;
}

export interface StructuredInputModel {
  task: string;
  context?: string;
  materials?: string[];
  urlReferences?: string[];
  constraints?: string;
  outputPreference?: string;
}

export interface PublicTurn {
  id: string;
  role: "user" | "assistant";
  text: string;
  createdAt: string;
  structuredInput?: StructuredInputModel;
  answerCard?: AnswerCardModel;
  workflow?: WorkflowModel;
  runId?: string;
  continuityMode?: ContinuityMode;
}

export interface ChatSessionSummary {
  id: string;
  title: string;
  updatedAt: string;
  preview: string;
  finalSource: FinalSource;
  phase: string;
  active?: boolean;
  continuityMode?: ContinuityMode;
}

export interface PublicThreadDetail {
  thread: ChatSessionSummary;
  turns: PublicTurn[];
}

export interface ThreadsResponse {
  threads: ChatSessionSummary[];
}

export interface SendMessageResponse {
  thread: ChatSessionSummary;
  assistantTurn: PublicTurn;
  turns: PublicTurn[];
}

export interface SendMessageRequest {
  text: string;
  structuredInput?: StructuredInputModel;
}

export interface RunStartedEvent {
  type: "run.started";
  data: {
    threadId: string;
    continuityMode: ContinuityMode;
  };
}

export interface WorkflowStageEvent {
  type: "workflow.stage";
  data: {
    stages: WorkflowStageProgress[];
    currentStage?: WorkflowStageKey | null;
  };
}

export interface WorkflowSnapshotEvent {
  type: "workflow.snapshot";
  data: {
    workflow: WorkflowModel;
    runId?: string | null;
    continuityMode: ContinuityMode;
  };
}

export interface AnswerFinalEvent {
  type: "answer.final";
  data: {
    response: SendMessageResponse;
  };
}

export interface StreamErrorEvent {
  type: "error";
  data: {
    code: string;
    message: string;
    category: ErrorCategory;
  };
}

export type SendMessageStreamEvent =
  | RunStartedEvent
  | WorkflowStageEvent
  | WorkflowSnapshotEvent
  | AnswerFinalEvent
  | StreamErrorEvent;

export interface ReadinessSurface {
  status: string;
  code: string;
  hint?: string;
}

export interface HealthResponse {
  status: "ok";
  apiVersion: string;
  overallStatus: OverallStatus;
  checkpointer: {
    enabled: boolean;
    mode: string;
    status: "enabled" | "disabled" | "unavailable";
    code: string;
    hint?: string;
  };
  continuityDefault: ContinuityMode;
  runtime: ReadinessSurface;
  providerEnv: ReadinessSurface;
  searchEnv: ReadinessSurface;
  store: "json-file";
}

export interface ErrorDetail {
  code?: string;
  message?: string;
  category?: ErrorCategory;
}
