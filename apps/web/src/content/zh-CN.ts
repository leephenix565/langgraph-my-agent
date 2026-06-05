import type { ContinuityMode, ErrorCategory, FinalSource, HealthResponse } from "../types/chat";
import type { DagStepStatus, DimensionStatus, WorkflowModel, WorkflowStageKey } from "../types/workflow";

type ConnectionState = "loading" | "live" | "degraded" | "unavailable";

export const zhCN = {
  sidebar: {
    primaryAction: "新建会话",
    history: "会话历史",
    deleteThread: "删除会话",
    deletingThread: "正在删除",
    confirmDeleteThread: "确定删除这个会话吗？此操作不可撤销。",
    navAgents: "能力",
    navSettings: "设置",
    serviceStatus: "服务状态",
    empty: "还没有会话。先输入一个问题。",
  },
  thread: {
    fallbackTitle: "新会话",
    updatedAt: "已更新",
    degradedMeta: "本地模式",
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
    title: "研判流程",
    inspectorLabel: "固定 DAG 研判流程详情",
    expand: "查看流程详情",
    collapse: "收起流程详情",
    empty: "等待流程快照",
    emptySteps: "暂无流程步骤。",
    emptyBatches: "暂无执行批次。",
    emptyDimensions: "暂无维度分组。",
    emptyResult: "选择一个流程步骤查看可公开展示的结果元数据。",
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
      steps: "流程步骤列表",
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
      runtimeKind: "运行方式",
      implementationStatus: "接入状态",
      invokeEnabled: "高级调用",
      liveVerified: "连接验证",
      warnings: "注意事项",
    },
    provenance: {
      planId: "计划 ID",
      continuity: "连续性",
      providerInvoked: "模型连接调用",
      externalInvoked: "高级连接调用",
      fallbackUsed: "备用路径",
      executionStatus: "执行状态",
      limitations: "技术说明",
      rawDetails: "技术枚举",
    },
    summaryStats: {
      stages: "6 个阶段",
      dimensions: "4 个维度综合",
    },
  },
  composer: {
    label: "继续",
    taskLabel: "任务/问题",
    helper: "输入公司、行业、事件或组合问题，系统会按固定流程组织分析。",
    placeholder: "输入公司、行业、事件或组合问题",
    taskPlaceholder: "例如：总结电动车公司的风险画像",
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
    degradedTitle: "基础功能可用",
    degradedBody: "当前使用本地固定 DAG 研判流程；高级连接状态可在设置中查看。",
    errorTitle: "请求失败",
    errorBody: "请稍后重试，或调整问题。",
    loadingTitle: "正在加载会话",
    loadingBody: "正在同步当前会话。",
    emptyTitle: "开始一次资本市场研判",
    emptyBody: "输入公司、行业、事件或组合问题，系统会按固定流程组织分析。",
    examplePrompts: [
      "总结电动车公司的风险画像",
      "给我一份半导体供应链更新",
      "按风险约束复盘组合",
    ],
  },
  agents: {
    eyebrow: "系统",
    title: "智能体能力结构",
    description: "系统按解析、分析、综合、报告四层组织研判流程。",
    searchLabel: "搜索能力",
    searchPlaceholder: "按 ID、名称、团队或能力搜索",
    loadingTitle: "正在加载能力结构",
    loadingBody: "正在读取公共固定 DAG 目录。",
    unavailableTitle: "能力结构不可用",
    unavailableBody: "请确认公共适配器可访问，然后刷新。",
    errorTitle: "能力结构暂时不可用",
    errorBody: "目录加载失败，请稍后重试。",
    statsLabel: "能力结构统计",
    totals: {
      config: "配置能力数",
      runtime: "流程能力数",
      disabled: "保留能力",
    },
    none: "无",
    reservedTitle: "保留能力",
    reservedDescription: "保留在能力结构中，暂不进入当前固定流程。",
    enabled: "固定流程",
    disabledState: "规划中",
    detailsTitle: "能力明细",
    detailsSummary: "查看各层智能体明细",
    capabilitiesLabel: "能力",
    roleUnknown: "未知角色",
    roleTypes: {
      system: "系统",
      system_planner: "系统规划",
      evidence_service: "证据服务",
      analysis_agent: "分析能力",
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
    title: "设置与状态诊断",
    description: "查看本地运行模式、连续性、存储和高级诊断状态。",
    loadingTitle: "正在加载系统状态",
    loadingBody: "正在读取公共就绪信息。",
    unavailableTitle: "系统状态不可用",
    unavailableBody: "请确认公共适配器可访问，然后刷新。",
    overallTitle: "总体状态",
    runtimeTitle: "运行时状态",
    providerTitle: "高级模型连接",
    searchTitle: "资料检索连接",
    checkpointerTitle: "连续性服务",
    continuityTitle: "默认连续性",
    storeTitle: "存储",
    currentValue: "当前值",
    modeLabel: "模式",
    hintLabel: "提示",
    ready: "就绪",
    degraded: "基础功能可用",
    continuityPersistentBody: "默认使用持久化会话连续性。",
    continuityReplayBody: "默认使用重放式会话连续性。",
    storeJsonFile: "JSON 文件存储",
    advancedDiagnostics: "高级诊断",
    advancedDiagnosticsBody: "以下信息用于开发和部署排查，普通使用无需处理。",
  },
} as const;

const sourceLabels: Record<FinalSource, string> = {
  reset_skeleton: "固定 DAG 研判流程",
};

const continuityLabels: Record<ContinuityMode, string> = {
  persistent: "持久化",
  replay: "重放",
};

const dagStepStatusLabels: Record<DagStepStatus, string> = {
  complete: "已完成",
  running: "运行中",
  queued: "排队中",
  pending_implementation: "待接入",
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
  pending_implementation: "待接入",
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
  degraded: "本地模式",
  unavailable: "不可用",
};

const errorCategoryLabels: Record<ErrorCategory, string> = {
  runtime: "运行时",
  provider_env: "高级模型连接",
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
  route_planner: "为本轮问题组织固定 DAG 研判路径。",
  financial_data_service: "整理研判所需的金融数据入口与上下文。",
  entity_relation_extractor: "梳理公司、行业、事件和关系线索。",
  value_traditional_valuation: "从传统估值框架观察价值维度。",
  value_ml_valuation: "从机器学习估值框架观察价值维度。",
  value_meta_valuation: "从同类样本与元学习框架观察价值维度。",
  value_research_synthesis: "综合研报观点与价值判断线索。",
  market_stock_technical: "从个股技术结构观察市场维度。",
  market_fund_manager_behavior: "观察基金经理行为对市场维度的影响。",
  market_ipo_investor_behavior: "观察 IPO 投资者构成与行为。",
  market_capital_flow_chip: "观察资金流与筹码结构。",
  sentiment_company_radar: "观察企业舆情线索，并汇入市场维度。",
  risk_crash: "识别股价崩盘相关风险线索。",
  risk_financial_fraud: "识别财务欺诈相关风险线索。",
  risk_identification: "汇集通用风险识别线索。",
  risk_compliance_review: "观察公告合规审查线索。",
  macro_analysis: "观察宏观环境变化。",
  macro_commodity_pricing: "观察商品定价对研判的影响。",
  macro_index_valuation: "观察指数估值变化。",
  macro_sentiment: "观察宏观情绪线索。",
  macro_industry_hotspot: "发现行业热点变化。",
  value_composite: "综合价值维度结论。",
  market_composite: "综合市场维度结论，包含企业舆情雷达。",
  risk_composite: "综合风险维度结论，企业舆情不进入该维度。",
  macro_composite: "综合宏观维度结论。",
  decision_synthesizer: "综合价值、市场、风险和宏观结果形成决策线索。",
  report_generator: "生成最终公开回答。",
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
  deterministic_skeleton: "固定流程",
  deterministic_system: "固定流程",
  deterministic_l1_bundle: "固定数据入口",
  deterministic_composite: "固定综合流程",
  deterministic_decision: "固定决策流程",
  deterministic_report: "固定报告流程",
  external_http_candidate: "可接入连接",
  pending_placeholder: "规划中",
  placeholder: "规划中",
};

const implementationStatusLabels: Record<string, string> = {
  deterministic_skeleton: "固定流程",
  pending_implementation: "待接入",
  external_candidate_disabled: "高级连接未启用",
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
  industry: "行业",
  hotspot: "热点",
  public_answer: "公开回答",
  deterministic_skeleton: "固定流程",
  pending_implementation: "待接入",
  external_candidate_disabled: "高级连接未启用",
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
  return dimensionLabels[dimension] ?? dimension;
}

export function runtimeKindLabel(value: string) {
  return runtimeKindLabels[value] ?? value;
}

export function implementationStatusLabel(value: string) {
  return implementationStatusLabels[value] ?? value;
}

export function executionStatusLabel(value: string) {
  return implementationStatusLabel(value);
}

export function capabilityLabel(value: string) {
  return capabilityLabels[value] ?? value;
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
    signals.push("运行时检查中");
  }
  if (health.providerEnv.status !== "configured") {
    signals.push("高级模型连接未启用");
  }
  if (health.searchEnv.status !== "configured") {
    signals.push("资料检索连接未启用");
  }
  return signals;
}

export function workflowSummaryLabel(workflow: WorkflowModel) {
  const completed = workflow.completedSteps.length;
  const total = workflow.dagSteps.length;
  if (completed <= 0) {
    return `${zhCN.workflow.title} - ${zhCN.workflow.empty}`;
  }
  return `${zhCN.workflow.title}：${completed}/${total || completed} 个步骤已完成`;
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
