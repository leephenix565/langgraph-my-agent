import type { ContinuityMode, ErrorCategory, FinalSource, HealthResponse } from "../types/chat";
import type { DagStepStatus, DimensionStatus, WorkflowModel, WorkflowStageKey } from "../types/workflow";

type ConnectionState = "loading" | "live" | "degraded" | "unavailable";

function withRaw(label: string, raw: string) {
  return `${label} (${raw})`;
}

export const zhCN = {
  sidebar: {
    primaryAction: "新建会话",
    history: "会话历史",
    deleteThread: "删除会话",
    deletingThread: "正在删除",
    confirmDeleteThread: "确定删除这个会话吗？此操作不可撤销。",
    navAgents: "Agent",
    navSettings: "设置",
    serviceStatus: "服务状态",
    empty: "还没有会话。先输入一个问题。",
  },
  thread: {
    fallbackTitle: "新会话",
    updatedAt: "已更新",
    degradedMeta: "降级",
    menuLabel: "会话导航",
    clearMessages: "清空消息",
    clearingMessages: "正在清空",
    confirmClearMessages: "确定清空当前会话消息吗？此操作不可撤销。",
  },
  answer: {
    references: "参考依据",
    details: "技术详情",
    showDetails: "显示技术详情",
    hideDetails: "隐藏技术详情",
    debug: {
      continuity: "连续性",
      runId: "runId",
      evidence: "证据",
      emit: "公开来源",
    },
  },
  workflow: {
    title: "工作流",
    inspectorLabel: "固定 DAG 工作流检查器",
    expand: "打开 DAG 检查器",
    collapse: "收起 DAG 检查器",
    empty: "等待固定 DAG 快照",
    emptySteps: "暂无 DAG 步骤。",
    emptyBatches: "暂无执行批次。",
    emptyDimensions: "暂无维度分组。",
    emptyResult: "选择一个 DAG 步骤查看可公开展示的结果元数据。",
    selectedStep: "当前步骤",
    none: "无",
    batchLabel: "批次",
    boolean: {
      yes: "是",
      no: "否",
    },
    kickers: {
      plan: "计划",
      batches: "批次",
      dimensions: "维度",
      steps: "步骤",
      results: "结果",
    },
    sections: {
      timeline: "阶段时间线",
      steps: "DAG 步骤列表",
      batches: "执行批次",
      dimensions: "维度分组",
      results: "步骤结果元数据",
      provenance: "最终来源与溯源",
    },
    stageStatus: {
      waiting: "等待中",
      running: "运行中",
      completed: "已完成",
      failed: "已失败",
    },
    resultFields: {
      stepId: "步骤 ID",
      agentId: "Agent ID",
      stage: "阶段",
      dimension: "维度",
      runtimeKind: "运行时类型",
      implementationStatus: "实现状态",
      invokeEnabled: "允许调用",
      liveVerified: "已实时验证",
      warnings: "注意事项",
    },
    provenance: {
      planId: "计划 ID",
      continuity: "连续性",
      providerInvoked: "已调用 provider",
      externalInvoked: "已调用外部服务",
      fallbackUsed: "已使用兜底",
      executionStatus: "执行状态",
      limitations: "限制说明",
    },
  },
  composer: {
    label: "继续",
    taskLabel: "任务/问题",
    helper: "系统只返回一条助手回答；工作流细节保留在检查器中。",
    placeholder: "输入消息或指令",
    taskPlaceholder: "输入任务或问题",
    unavailablePlaceholder: "系统不可用，请稍后再试。",
    submit: "发送",
    submitting: "正在发送",
    expandStructured: "结构化输入",
    collapseStructured: "隐藏结构化输入",
    structuredLabel: "结构化输入",
    structuredHelper: "补充上下文、材料、约束和输出偏好，便于重放与审计。",
    contextLabel: "上下文/材料",
    contextPlaceholder: "已知事实、来源笔记或需要考虑的背景",
    constraintsLabel: "约束",
    constraintsPlaceholder: "时间范围、边界、必须覆盖的要点或限制",
    outputPreferenceLabel: "输出偏好",
    outputPreferencePlaceholder: "长度、结构、语气，或是否需要表格",
    inputTooLong: "输入过长，请缩短后再试。",
  },
  states: {
    unavailableTitle: "系统不可用",
    unavailableBody: "无法连接公共适配器。请确认 Python adapter 正在运行。",
    degradedTitle: "系统已连接，但部分能力降级",
    degradedBody: "仍可继续使用，但某些运行时能力可能受限。",
    errorTitle: "请求失败",
    errorBody: "请稍后重试，或调整问题。",
    loadingTitle: "正在加载会话",
    loadingBody: "正在同步当前会话。",
    emptyTitle: "先输入一个问题",
    emptyBody: "可以提出研究、研判或组合建议相关的问题。",
  },
  agents: {
    eyebrow: "系统",
    title: "Agent 目录",
    description: "公共适配器暴露的只读固定 DAG Agent 目录。",
    searchLabel: "搜索 Agent",
    searchPlaceholder: "按 ID、名称、团队或能力搜索",
    loadingTitle: "正在加载 Agent 目录",
    loadingBody: "正在读取公共固定 DAG 目录。",
    unavailableTitle: "Agent 目录不可用",
    unavailableBody: "请确认公共适配器可访问，然后刷新。",
    errorTitle: "Agent 目录暂时不可用",
    errorBody: "目录加载失败，请稍后重试。",
    statsLabel: "Agent 目录统计",
    totals: {
      config: "配置 Agent 数",
      runtime: "运行时 Agent 数",
      disabled: "禁用 ID",
    },
    none: "无",
    reservedTitle: "保留/禁用",
    reservedDescription: "存在于元数据中，但默认不启用的 Agent。",
    enabled: "启用",
    disabledState: "禁用",
    capabilitiesLabel: "能力",
    roleUnknown: "未知角色",
    roleTypes: {
      system: "系统",
      system_planner: "系统规划",
      evidence_service: "证据服务",
      analysis_agent: "分析 Agent",
      dimension_composite: "维度综合",
      decision_synthesizer: "决策综合",
      report_generator: "报告生成",
    },
    layers: {
      L1: {
        title: "L1 解析与证据",
        description: "负责路径规划、数据包和实体关系等证据接入点。",
      },
      L2: {
        title: "L2 分析",
        description: "并行承载价值、市场、风险和宏观方向的分析 Agent。",
      },
      L3: {
        title: "L3 维度综合",
        description: "按价值、市场、风险和宏观维度汇总 L2 结论。",
      },
      L4: {
        title: "L4 决策与报告",
        description: "生成综合研判和最终公开报告。",
      },
    },
  },
  settings: {
    eyebrow: "系统状态",
    title: "设置",
    description: "只读展示运行时、provider、搜索、存储和连续性的就绪状态。",
    loadingTitle: "正在加载系统状态",
    loadingBody: "正在读取公共就绪信息。",
    unavailableTitle: "系统状态不可用",
    unavailableBody: "请确认公共适配器可访问，然后刷新。",
    overallTitle: "总体状态",
    runtimeTitle: "运行时状态",
    providerTitle: "Provider 环境",
    searchTitle: "搜索环境",
    checkpointerTitle: "Checkpointer",
    continuityTitle: "默认连续性",
    storeTitle: "存储",
    currentValue: "当前值",
    modeLabel: "模式",
    hintLabel: "提示",
    ready: "就绪",
    degraded: "降级",
    continuityPersistentBody: "默认使用持久化会话连续性。",
    continuityReplayBody: "默认使用重放式会话连续性。",
    storeJsonFile: "JSON 文件存储",
  },
} as const;

const sourceLabels: Record<FinalSource, string> = {
  reset_skeleton: "固定 DAG 骨架",
};

const continuityLabels: Record<ContinuityMode, string> = {
  persistent: "持久化",
  replay: "重放",
};

const dagStepStatusLabels: Record<DagStepStatus, string> = {
  complete: "已完成",
  running: "运行中",
  queued: "排队中",
  pending_implementation: "待实现",
  partial: "部分完成",
  error: "错误",
  skipped: "已跳过",
  blocked: "已阻塞",
  failed: "已失败",
};

const dimensionStatusLabels: Record<DimensionStatus, string> = {
  complete: "已完成",
  running: "运行中",
  queued: "排队中",
  pending_implementation: "待实现",
  partial: "部分完成",
  error: "错误",
};

const stageLabels: Record<WorkflowStageKey, string> = {
  planning: "规划",
  evidence: "证据",
  l2_analysis: "L2 分析",
  dimension_composite: "维度综合",
  decision: "决策",
  report: "报告",
};

const connectionLabels: Record<ConnectionState, string> = {
  loading: "加载中",
  live: "在线",
  degraded: "降级",
  unavailable: "不可用",
};

const errorCategoryLabels: Record<ErrorCategory, string> = {
  runtime: "运行时",
  provider_env: "Provider 环境",
  store: "存储",
  contract: "契约",
  request: "请求",
};

const teamLabels: Record<string, string> = {
  l1: "L1",
  value: "价值",
  market: "市场",
  risk: "风险",
  macro: "宏观",
  composite: "综合",
  l4: "L4",
};

const confidenceLabels: Record<string, string> = {
  high: "高",
  medium: "中",
  low: "低",
};

const agentNameLabels: Record<string, string> = {
  route_planner: "路径规划器",
  financial_data_service: "金融数据服务",
  entity_relation_extractor: "实体关系抽取器",
  value_traditional_valuation: "传统企业估值",
  value_ml_valuation: "机器学习企业估值",
  value_meta_valuation: "元学习企业估值",
  value_research_synthesis: "研报观点综合",
  market_stock_technical: "个股技术分析",
  market_fund_manager_behavior: "基金经理行为分析",
  market_ipo_investor_behavior: "IPO 投资者行为分析",
  market_capital_flow_chip: "资金流与筹码分析",
  sentiment_company_radar: "企业舆情雷达",
  risk_crash: "股价崩盘风险",
  risk_financial_fraud: "财务欺诈风险",
  risk_identification: "风险识别",
  risk_compliance_review: "公告合规审查",
  macro_analysis: "宏观分析",
  macro_commodity_pricing: "商品定价分析",
  macro_index_valuation: "股票指数估值",
  macro_sentiment: "宏观情绪感知",
  macro_industry_hotspot: "行业热点洞察",
  value_composite: "价值综合",
  market_composite: "市场综合",
  risk_composite: "风险综合",
  macro_composite: "宏观综合",
  decision_synthesizer: "决策综合器",
  report_generator: "报告生成器",
};

const agentDescriptionLabels: Record<string, string> = {
  route_planner: "创建确定性的固定 DAG 计划；真实业务路由智能仍待实现。",
  financial_data_service: "准备金融数据包占位接口，不调用 provider、搜索或外部服务。",
  entity_relation_extractor: "准备实体与关系证据占位接口，不进行实时查询。",
  value_traditional_valuation: "价值维度 L2 占位：传统企业估值。",
  value_ml_valuation: "价值维度 L2 占位：机器学习企业估值。",
  value_meta_valuation: "价值维度 L2 占位：元学习和同类样本估值。",
  value_research_synthesis: "价值维度 L2 占位：分析师研报与观点综合。",
  market_stock_technical: "市场维度 L2 占位：个股技术分析。",
  market_fund_manager_behavior: "市场维度 L2 占位：基金经理投资行为分析。",
  market_ipo_investor_behavior: "市场维度 L2 占位：IPO 投资者构成与行为分析。",
  market_capital_flow_chip: "市场维度 L2 占位：资金流与筹码结构分析。",
  sentiment_company_radar: "市场维度 L2 占位：企业舆情雷达；只汇入 market_composite。",
  risk_crash: "风险维度 L2 占位：股价崩盘风险。",
  risk_financial_fraud: "风险维度 L2 占位：财务欺诈风险。",
  risk_identification: "风险维度 L2 占位：通用风险识别。",
  risk_compliance_review: "风险维度 L2 占位：公告合规审查。",
  macro_analysis: "宏观维度 L2 占位：宏观分析。",
  macro_commodity_pricing: "宏观维度 L2 占位：商品定价分析。",
  macro_index_valuation: "宏观维度 L2 占位：股票指数估值。",
  macro_sentiment: "宏观维度 L2 占位：宏观情绪感知。",
  macro_industry_hotspot: "宏观维度 L2 占位：行业热点发现。",
  value_composite: "L3 占位：综合价值维度 L2 结论。",
  market_composite: "L3 占位：综合市场维度 L2 结论，包含企业舆情雷达。",
  risk_composite: "L3 占位：综合风险维度 L2 结论，不读取企业舆情雷达。",
  macro_composite: "L3 占位：综合宏观维度 L2 结论。",
  decision_synthesizer: "L4 占位：综合价值、市场、风险和宏观结果形成决策。",
  report_generator: "L4 占位：生成最终公开的重置骨架回答。",
};

const citationLabels: Record<string, string> = {
  "Fixed DAG bundle": "固定 DAG 数据包",
  "Emitted bundle": "输出数据包",
  Workflow: "工作流",
};

const readinessStatusLabels: Record<string, string> = {
  ready: "就绪",
  import_unavailable: "导入不可用",
  configured: "已配置",
  missing: "缺失",
  disabled: "已禁用",
  enabled: "已启用",
  unavailable: "不可用",
  unknown: "未知",
};

const checkpointerStatusLabels: Record<HealthResponse["checkpointer"]["status"], string> = {
  enabled: "已启用",
  disabled: "已禁用",
  unavailable: "不可用",
};

const storeLabels: Record<HealthResponse["store"], string> = {
  "json-file": zhCN.settings.storeJsonFile,
};

const dimensionLabels: Record<string, string> = {
  l1: "L1 解析",
  value: "价值",
  market: "市场",
  risk: "风险",
  macro: "宏观",
  composite: "综合",
  l4: "L4 报告",
};

const runtimeKindLabels: Record<string, string> = {
  deterministic_skeleton: "确定性骨架",
  deterministic_system: "确定性系统",
  deterministic_l1_bundle: "确定性 L1 数据包",
  deterministic_composite: "确定性维度综合",
  deterministic_decision: "确定性决策",
  deterministic_report: "确定性报告",
  external_http_candidate: "外部 HTTP 候选",
  pending_placeholder: "待实现占位",
  placeholder: "占位实现",
};

const implementationStatusLabels: Record<string, string> = {
  deterministic_skeleton: "确定性骨架",
  pending_implementation: "待实现",
  external_candidate_disabled: "外部候选未启用",
};

const capabilityLabels: Record<string, string> = {
  planning: "规划",
  evidence: "证据",
  l2_analysis: "L2 分析",
  dimension_composite: "维度综合",
  decision: "决策",
  report: "报告",
  l1: "L1 解析",
  value: "价值",
  market: "市场",
  risk: "风险",
  macro: "宏观",
  composite: "综合",
  l4: "L4 报告",
  fixed_dag: "固定 DAG",
  data_bundle: "数据包",
  financial_data: "金融数据",
  entity_relation: "实体关系",
  valuation: "估值",
  dcf: "DCF",
  ml: "机器学习",
  peer: "同类样本",
  research: "研报",
  synthesis: "综合",
  technical: "技术分析",
  fund_manager: "基金经理",
  ipo: "IPO",
  capital_flow: "资金流",
  chip: "筹码",
  sentiment: "舆情",
  crash_risk: "崩盘风险",
  fraud: "欺诈风险",
  compliance: "合规",
  commodity: "商品",
  index: "指数",
  hotspot: "热点",
  deterministic_skeleton: "确定性骨架",
  pending_implementation: "待实现",
  external_candidate_disabled: "外部候选未启用",
};

export function sourceLabel(source: FinalSource) {
  return sourceLabels[source] ?? source;
}

export function continuityLabel(mode: ContinuityMode, short = false) {
  if (!short) {
    return continuityLabels[mode] ?? mode;
  }
  return mode === "persistent" ? "持久化" : "重放";
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

export function agentDescriptionLabel(agentId: string, fallback: string) {
  return agentDescriptionLabels[agentId] ?? fallback;
}

export function citationLabel(label: string) {
  return citationLabels[label] ?? label;
}

export function dimensionLabel(dimension: string) {
  return dimensionLabels[dimension] ? withRaw(dimensionLabels[dimension], dimension) : dimension;
}

export function runtimeKindLabel(value: string) {
  return runtimeKindLabels[value] ? withRaw(runtimeKindLabels[value], value) : value;
}

export function implementationStatusLabel(value: string) {
  return implementationStatusLabels[value] ? withRaw(implementationStatusLabels[value], value) : value;
}

export function executionStatusLabel(value: string) {
  return implementationStatusLabel(value);
}

export function capabilityLabel(value: string) {
  return capabilityLabels[value] ? withRaw(capabilityLabels[value], value) : value;
}

export function stepCountLabel(count: number) {
  return `${count} 个步骤`;
}

export function degradedSignalLabels(health: HealthResponse | null): string[] {
  if (!health || health.overallStatus !== "degraded") {
    return [];
  }

  const signals: string[] = [];
  if (health.runtime.status !== "ready") {
    signals.push("运行时未就绪");
  }
  if (health.providerEnv.status !== "configured") {
    signals.push("Provider 环境未配置");
  }
  if (health.searchEnv.status !== "configured") {
    signals.push("搜索环境未配置");
  }
  return signals;
}

export function workflowSummaryLabel(workflow: WorkflowModel) {
  const completed = workflow.completedSteps.length;
  const total = workflow.dagSteps.length;
  if (completed <= 0) {
    return `${zhCN.workflow.title} - ${zhCN.workflow.empty}`;
  }
  return `${zhCN.workflow.title} - ${completed}/${total || completed} 个 DAG 步骤已完成`;
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
