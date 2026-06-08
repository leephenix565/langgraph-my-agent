import type { ContinuityMode, FinalSource } from "./chat";

export type WorkflowStageKey =
  | "planning"
  | "evidence"
  | "l2_analysis"
  | "dimension_composite"
  | "decision"
  | "report";

export type WorkflowStageStatus = "waiting" | "running" | "completed" | "failed";

export type WorkflowRuntimeKind =
  | "deterministic_system"
  | "deterministic_l1_bundle"
  | "external_http_candidate"
  | "pending_placeholder"
  | "deterministic_composite"
  | "deterministic_decision"
  | "deterministic_report";

export type WorkflowImplementationStatus =
  | "deterministic_skeleton"
  | "external_candidate_disabled"
  | "pending_implementation";

export type DagStepStatus =
  | "complete"
  | "running"
  | "queued"
  | "pending_implementation"
  | "partial"
  | "error"
  | "skipped"
  | "blocked"
  | "failed";

export type DimensionStatus = "complete" | "running" | "queued" | "pending_implementation" | "partial" | "error";

export interface WorkflowStage {
  key: WorkflowStageKey;
  title: string;
  stepIds: string[];
}

export interface WorkflowStageProgress {
  key: WorkflowStageKey;
  title: string;
  status: WorkflowStageStatus;
}

export interface DagStep {
  id: string;
  stage: WorkflowStageKey;
  agentId?: string | null;
  dimension?: string | null;
  title: string;
  summary: string;
  status: DagStepStatus;
}

export interface DimensionGroup {
  id: string;
  title: string;
  stepIds: string[];
  status: DimensionStatus;
  summary: string;
}

export interface WorkflowStepResult extends Record<string, unknown> {
  status?: DagStepStatus | string;
  runtime_kind?: WorkflowRuntimeKind;
  implementation_status?: WorkflowImplementationStatus;
  binding_source?: string;
  legacy_agent_id?: string;
  external_agent_id?: string;
  invoke_enabled?: boolean;
  live_verified?: boolean;
  warnings?: string[] | string;
}

export interface WorkflowProvenance {
  source: FinalSource;
  continuityMode: ContinuityMode;
  providerInvoked: boolean;
  externalInvoked: boolean;
  executionStatus?: string | null;
  fallbackUsed: boolean;
  limitations: string[];
  summary: string;
}

export interface WorkflowSnapshotV2 {
  schema: "workflow_snapshot_v2";
  planId: string;
  stages: WorkflowStage[];
  dagSteps: DagStep[];
  dimensionGroups: DimensionGroup[];
  currentStage?: WorkflowStageKey | null;
  completedSteps: string[];
  executionBatches: string[][];
  stepResults: Record<string, WorkflowStepResult>;
  finalSource: FinalSource;
  provenanceNote: string;
  provenance?: WorkflowProvenance | null;
}

export interface WorkflowModel extends WorkflowSnapshotV2 {
  liveProgress?: WorkflowStageProgress[];
}
