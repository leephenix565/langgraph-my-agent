import type { ContinuityMode, ErrorCategory, FinalSource, HealthResponse } from "../types/chat";
import type { DagStepStatus, DimensionStatus, WorkflowModel, WorkflowStageKey } from "../types/workflow";

type ConnectionState = "loading" | "live" | "degraded" | "unavailable";

export const zhCN = {
  sidebar: {
    primaryAction: "New thread",
    history: "Thread history",
    deleteThread: "Delete thread",
    deletingThread: "Deleting",
    confirmDeleteThread: "Delete this thread? This cannot be undone.",
    navAgents: "Agents",
    navSettings: "Settings",
    serviceStatus: "Service status",
    empty: "No threads yet. Start with a question.",
  },
  thread: {
    fallbackTitle: "New thread",
    updatedAt: "Updated",
    degradedMeta: "Degraded",
    menuLabel: "Thread navigation",
    clearMessages: "Clear messages",
    clearingMessages: "Clearing",
    confirmClearMessages: "Clear the current thread messages? This cannot be undone.",
  },
  answer: {
    references: "References",
    details: "Technical details",
    showDetails: "Show technical details",
    hideDetails: "Hide technical details",
    debug: {
      continuity: "Continuity",
      runId: "runId",
      evidence: "Evidence",
      emit: "Public source",
    },
  },
  workflow: {
    title: "Workflow",
    inspectorLabel: "Fixed DAG workflow inspector",
    expand: "Open DAG inspector",
    collapse: "Collapse inspector",
    empty: "Waiting for the fixed DAG snapshot",
    emptySteps: "No DAG steps are available yet.",
    emptyBatches: "No execution batches are available yet.",
    emptyDimensions: "No dimension groups are available yet.",
    emptyResult: "Select a DAG step to inspect its public-safe result metadata.",
    selectedStep: "Selected step",
    none: "None",
    batchLabel: "Batch",
    units: {
      steps: "steps",
    },
    boolean: {
      yes: "Yes",
      no: "No",
    },
    kickers: {
      plan: "Plan",
      batches: "Batches",
      dimensions: "Dimensions",
      steps: "Steps",
      results: "Result",
    },
    sections: {
      timeline: "Stage timeline",
      steps: "DAG step list",
      batches: "Execution batches",
      dimensions: "Dimension groups",
      results: "Step result metadata",
      provenance: "Final source and provenance",
    },
    stageStatus: {
      waiting: "Waiting",
      running: "Running",
      completed: "Completed",
      failed: "Failed",
    },
    resultFields: {
      stepId: "Step id",
      agentId: "Agent id",
      stage: "Stage",
      dimension: "Dimension",
      runtimeKind: "Runtime kind",
      implementationStatus: "Implementation status",
      invokeEnabled: "Invoke enabled",
      liveVerified: "Live verified",
      warnings: "Warnings",
    },
    provenance: {
      planId: "Plan id",
      continuity: "Continuity",
      providerInvoked: "Provider invoked",
      externalInvoked: "External invoked",
      fallbackUsed: "Fallback used",
      executionStatus: "Execution status",
      limitations: "Limitations",
    },
  },
  composer: {
    label: "Continue",
    taskLabel: "Task / question",
    helper: "The system returns a single assistant answer. Workflow details stay in the inspector.",
    placeholder: "Send a message or instruction",
    taskPlaceholder: "Enter the task or question",
    unavailablePlaceholder: "System unavailable. Try again later.",
    submit: "Send",
    submitting: "Sending",
    expandStructured: "Structured input",
    collapseStructured: "Hide structured input",
    structuredLabel: "Structured input",
    structuredHelper: "Add context, materials, constraints, and output preferences for replayable input.",
    contextLabel: "Context / materials",
    contextPlaceholder: "Known facts, source notes, or context to consider",
    constraintsLabel: "Constraints",
    constraintsPlaceholder: "Time range, boundary, required points, or restrictions",
    outputPreferenceLabel: "Output preference",
    outputPreferencePlaceholder: "Length, structure, tone, or whether tables are needed",
    inputTooLong: "Input is too long. Please shorten it and try again.",
  },
  states: {
    unavailableTitle: "System unavailable",
    unavailableBody: "The public adapter cannot be reached. Confirm the Python adapter is running.",
    degradedTitle: "System connected with degraded capabilities",
    degradedBody: "You can continue, but some runtime capabilities may be limited.",
    errorTitle: "Request failed",
    errorBody: "Try again later or adjust the question.",
    loadingTitle: "Loading thread",
    loadingBody: "Synchronizing the current thread.",
    emptyTitle: "Start with a question",
    emptyBody: "Ask for research, judgment, or portfolio-oriented analysis.",
  },
  agents: {
    eyebrow: "System",
    title: "Agent catalog",
    description: "Read-only fixed DAG agent catalog exposed by the public adapter.",
    searchLabel: "Search agents",
    searchPlaceholder: "Search by id, name, team, or capability",
    loadingTitle: "Loading agent catalog",
    loadingBody: "Reading the public fixed DAG catalog.",
    unavailableTitle: "Agent catalog unavailable",
    unavailableBody: "Confirm the public adapter is reachable, then refresh.",
    errorTitle: "Agent catalog temporarily unavailable",
    errorBody: "The catalog could not be loaded. Try again later.",
    statsLabel: "Agent catalog statistics",
    totals: {
      config: "Configured agents",
      runtime: "Runtime agents",
      disabled: "Disabled ids",
    },
    none: "None",
    reservedTitle: "Reserved / disabled",
    reservedDescription: "Agents present in metadata but not enabled by default.",
    enabled: "Enabled",
    disabledState: "Disabled",
    capabilitiesLabel: "Capabilities",
    roleUnknown: "Unknown role",
    roleTypes: {
      system: "System",
      system_planner: "System planner",
      evidence_service: "Evidence service",
      analysis_agent: "Analysis agent",
      dimension_composite: "Dimension composite",
      decision_synthesizer: "Decision synthesizer",
      report_generator: "Report generator",
    },
    layers: {
      L1: {
        title: "L1 planning and evidence",
        description: "Route planning plus data and entity evidence seams.",
      },
      L2: {
        title: "L2 analysis",
        description: "Parallel value, market, risk, and macro analysis agents.",
      },
      L3: {
        title: "L3 dimension composites",
        description: "Composite agents for value, market, risk, and macro dimensions.",
      },
      L4: {
        title: "L4 decision and report",
        description: "Final decision synthesis and public report generation.",
      },
    },
  },
  settings: {
    eyebrow: "System status",
    title: "Settings",
    description: "Read-only readiness surface for runtime, provider, search, store, and continuity.",
    loadingTitle: "Loading system status",
    loadingBody: "Reading public readiness information.",
    unavailableTitle: "System status unavailable",
    unavailableBody: "Confirm the public adapter is reachable, then refresh.",
    overallTitle: "Overall status",
    runtimeTitle: "Runtime status",
    providerTitle: "Provider environment",
    searchTitle: "Search environment",
    checkpointerTitle: "Checkpointer",
    continuityTitle: "Default continuity",
    storeTitle: "Store",
    currentValue: "Current value",
    modeLabel: "Mode",
    hintLabel: "Hint",
    ready: "Ready",
    degraded: "Degraded",
    continuityPersistentBody: "Persistent thread continuity is the default.",
    continuityReplayBody: "Replay continuity is the default.",
    storeJsonFile: "JSON file store",
  },
} as const;

const sourceLabels: Record<FinalSource, string> = {
  reset_skeleton: "Fixed DAG skeleton",
};

const continuityLabels: Record<ContinuityMode, string> = {
  persistent: "Persistent",
  replay: "Replay",
};

const dagStepStatusLabels: Record<DagStepStatus, string> = {
  complete: "Complete",
  running: "Running",
  queued: "Queued",
  pending_implementation: "Pending implementation",
  partial: "Partial",
  error: "Error",
  skipped: "Skipped",
  blocked: "Blocked",
  failed: "Failed",
};

const dimensionStatusLabels: Record<DimensionStatus, string> = {
  complete: "Complete",
  running: "Running",
  queued: "Queued",
  pending_implementation: "Pending implementation",
  partial: "Partial",
  error: "Error",
};

const stageLabels: Record<WorkflowStageKey, string> = {
  planning: "Planning",
  evidence: "Evidence",
  l2_analysis: "L2 analysis",
  dimension_composite: "Dimension composite",
  decision: "Decision",
  report: "Report",
};

const connectionLabels: Record<ConnectionState, string> = {
  loading: "Loading",
  live: "Live",
  degraded: "Degraded",
  unavailable: "Unavailable",
};

const errorCategoryLabels: Record<ErrorCategory, string> = {
  runtime: "Runtime",
  provider_env: "Provider environment",
  store: "Store",
  contract: "Contract",
  request: "Request",
};

const teamLabels: Record<string, string> = {
  l1: "L1",
  value: "Value",
  market: "Market",
  risk: "Risk",
  macro: "Macro",
  composite: "Composite",
  l4: "L4",
};

const confidenceLabels: Record<string, string> = {
  high: "High",
  medium: "Medium",
  low: "Low",
};

const agentNameLabels: Record<string, string> = {
  route_planner: "Route planner",
  financial_data_service: "Financial data service",
  entity_relation_extractor: "Entity relation extractor",
  value_traditional_valuation: "Traditional valuation",
  value_ml_valuation: "ML valuation",
  value_meta_valuation: "Meta valuation",
  value_research_synthesis: "Research synthesis",
  market_stock_technical: "Stock technical analysis",
  market_fund_manager_behavior: "Fund manager behavior",
  market_ipo_investor_behavior: "IPO investor behavior",
  market_capital_flow_chip: "Capital flow and chip analysis",
  sentiment_company_radar: "Company sentiment radar",
  risk_crash: "Crash risk",
  risk_financial_fraud: "Financial fraud risk",
  risk_identification: "Risk identification",
  risk_compliance_review: "Compliance review",
  macro_analysis: "Macro analysis",
  macro_commodity_pricing: "Commodity pricing",
  macro_index_valuation: "Index valuation",
  macro_sentiment: "Macro sentiment",
  macro_industry_hotspot: "Industry hotspot",
  value_composite: "Value composite",
  market_composite: "Market composite",
  risk_composite: "Risk composite",
  macro_composite: "Macro composite",
  decision_synthesizer: "Decision synthesizer",
  report_generator: "Report generator",
};

const citationLabels: Record<string, string> = {
  "Fixed DAG bundle": "Fixed DAG bundle",
  "Emitted bundle": "Emitted bundle",
  "Workflow": "Workflow",
};

const readinessStatusLabels: Record<string, string> = {
  ready: "Ready",
  import_unavailable: "Unavailable",
  configured: "Configured",
  missing: "Missing",
  unknown: "Unknown",
};

const checkpointerStatusLabels: Record<HealthResponse["checkpointer"]["status"], string> = {
  enabled: "Enabled",
  disabled: "Disabled",
  unavailable: "Unavailable",
};

const storeLabels: Record<HealthResponse["store"], string> = {
  "json-file": zhCN.settings.storeJsonFile,
};

export function sourceLabel(source: FinalSource) {
  return sourceLabels[source] ?? source;
}

export function continuityLabel(mode: ContinuityMode, short = false) {
  if (!short) {
    return continuityLabels[mode] ?? mode;
  }
  return mode === "persistent" ? "Persistent" : "Replay";
}

export function dagStepStatusLabel(status: DagStepStatus) {
  return dagStepStatusLabels[status] ?? status;
}

export function dimensionStatusLabel(status: DimensionStatus) {
  return dimensionStatusLabels[status] ?? status;
}

export function stageLabel(stage: WorkflowStageKey) {
  return stageLabels[stage] ?? stage;
}

export function connectionStateLabel(state: ConnectionState) {
  return connectionLabels[state] ?? state;
}

export function errorCategoryLabel(category: ErrorCategory) {
  return errorCategoryLabels[category] ?? category;
}

export function teamLabel(team: string) {
  return teamLabels[team] ?? team;
}

export function confidenceLabel(confidence?: string) {
  if (!confidence) {
    return null;
  }
  return confidenceLabels[confidence] ?? confidence;
}

export function agentNameLabel(agentId: string, fallback?: string) {
  return agentNameLabels[agentId] ?? fallback ?? agentId;
}

export function citationLabel(label: string) {
  return citationLabels[label] ?? label;
}

export function degradedSignalLabels(health: HealthResponse | null): string[] {
  if (!health || health.overallStatus !== "degraded") {
    return [];
  }

  const signals: string[] = [];
  if (health.runtime.status !== "ready") {
    signals.push("Runtime not ready");
  }
  if (health.providerEnv.status !== "configured") {
    signals.push("Provider environment not configured");
  }
  if (health.searchEnv.status !== "configured") {
    signals.push("Search environment not configured");
  }
  return signals;
}

export function workflowSummaryLabel(workflow: WorkflowModel) {
  const completed = workflow.completedSteps.length;
  const total = workflow.dagSteps.length;
  if (completed <= 0) {
    return `${zhCN.workflow.title} - ${zhCN.workflow.empty}`;
  }
  return `${zhCN.workflow.title} - ${completed}/${total || completed} DAG steps complete`;
}

export function overallStatusLabel(status: HealthResponse["overallStatus"]) {
  return status === "ready" ? zhCN.settings.ready : zhCN.settings.degraded;
}

export function readinessStatusLabel(status: string) {
  return readinessStatusLabels[status] ?? status;
}

export function checkpointerStatusLabel(status: HealthResponse["checkpointer"]["status"]) {
  return checkpointerStatusLabels[status] ?? status;
}

export function storeLabel(store: HealthResponse["store"]) {
  return storeLabels[store] ?? store;
}
