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

export interface WorkflowAgentEvidence {
  agent_id: string;
  display_name?: string;
  layer?: "L2" | string;
  dimension?: string;
  status?: string;
  stance?: string;
  confidence?: number;
  summary?: string;
  as_of?: string;
  data_as_of?: string;
  source?: string;
  risk_score?: number;
}

export interface WorkflowCompositeMemberEvidence {
  agent_id: string;
  display_name?: string;
  weight?: number;
  stance?: string;
  confidence?: number;
  status?: string;
}

export interface WorkflowCompositeEvidence {
  agent_id: string;
  display_name?: string;
  layer?: "L3" | string;
  dimension?: string;
  status?: string;
  stance?: string;
  confidence?: number;
  summary?: string;
  members?: WorkflowCompositeMemberEvidence[];
  gate?: string;
  veto?: boolean;
  penalty?: number;
  risk_score?: number;
  regime?: string;
  dimension_weights?: Record<string, number>;
  risk_sensitivity?: string | number;
  as_of?: string;
  data_as_of?: string;
  source?: string;
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
  agent_evidence?: WorkflowAgentEvidence;
  composite_evidence?: WorkflowCompositeEvidence;
}

export interface WorkflowProvenance {
  source: FinalSource;
  continuityMode: ContinuityMode;
  providerInvoked: boolean;
  externalInvoked: boolean;
  executionStatus?: string | null;
  fallbackUsed: boolean;
  limitations: string[];
  selectedRoutingRequested: boolean;
  selectedRoutingFallback: boolean;
  fallbackReason?: string | null;
  routeGranularity?: string | null;
  selectedDimensions: string[];
  expandedAgentCount?: number | null;
  providerRouterEnabled: boolean;
  providerRouterInvoked: boolean;
  providerRouterMode?: string | null;
  providerRouterParseOk: boolean;
  providerRouterFallbackReason?: string | null;
  providerRouterErrorCode?: string | null;
  providerRouterSelectedDimensions: string[];
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
