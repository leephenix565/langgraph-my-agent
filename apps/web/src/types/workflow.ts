import type { ContinuityMode, FinalSource } from "./chat";

export type WorkflowStageKey = "routing" | "analysis" | "risk" | "summary" | "fusion";
export type WorkflowStageStatus = "waiting" | "running" | "completed" | "failed";

export interface WorkflowStageProgress {
  key: WorkflowStageKey;
  title: string;
  status: WorkflowStageStatus;
}

export interface LayerPlanItem {
  layer: "L1" | "L2" | "L3" | "L4";
  mode: string;
  selected: string[];
  note?: string;
}

export interface AgentStep {
  id: string;
  layer: "L1" | "L2" | "L3" | "L4";
  agentId: string;
  title: string;
  summary: string;
  status: "complete" | "running" | "queued";
  signal?: string;
}

export interface FusionStep {
  id: string;
  kind: "baseline" | "judge" | "writer";
  label: string;
  status: "disabled" | "shadow" | "ready" | "selected" | "error";
  summary: string;
}

export interface WorkflowModel {
  layerPlan: LayerPlanItem[];
  layerMode: Record<string, string>;
  currentLayer: string;
  layerDone: string[];
  agentSteps: AgentStep[];
  fusionSteps: FusionStep[];
  finalSource: FinalSource;
  provenanceNote: string;
  provenance?: {
    emitPath: "mainline_summary" | "baseline_sidecar" | "fusion_writer";
    finalSource: FinalSource;
    continuityMode: ContinuityMode;
    summary: string;
  };
  liveProgress?: WorkflowStageProgress[];
}
