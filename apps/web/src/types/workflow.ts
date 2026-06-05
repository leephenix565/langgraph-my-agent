import type { ContinuityMode, FinalSource } from "./chat";

export type WorkflowStageKey =
  | "planning"
  | "evidence"
  | "l2_analysis"
  | "dimension_composite"
  | "decision"
  | "report";

export type WorkflowStageStatus = "waiting" | "running" | "completed" | "failed";

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

export type WorkflowStepResult = Record<string, unknown>;

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
