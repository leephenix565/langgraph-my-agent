import type { ContinuityMode, ErrorCategory, FinalSource, HealthResponse } from "../types/chat";
import type { AgentStep, FusionStep, WorkflowModel } from "../types/workflow";

type ConnectionState = "loading" | "live" | "degraded" | "unavailable";
type EmitPath = NonNullable<WorkflowModel["provenance"]>["emitPath"];

export const zhCN = {
  sidebar: {
    primaryAction: "开启新对话",
    history: "对话历史",
    deleteThread: "删除会话",
    deletingThread: "删除中",
    confirmDeleteThread: "确认删除此会话？此操作不可撤销。",
    navAgents: "智能体目录",
    navSettings: "系统设置",
    serviceStatus: "服务状态",
    empty: "暂无会话，发起一个问题开始使用。",
  },
  thread: {
    fallbackTitle: "新对话",
    updatedAt: "最近更新",
    degradedMeta: "部分能力受限",
    menuLabel: "会话导航",
    clearMessages: "清空记录",
    clearingMessages: "清空中",
    confirmClearMessages: "确认清空当前会话记录？此操作不可撤销。",
  },
  answer: {
    references: "参考依据",
    details: "技术详情",
    showDetails: "查看技术详情",
    hideDetails: "收起技术详情",
    debug: {
      continuity: "连续性",
      runId: "runId",
      evidence: "证据数",
      emit: "输出路径",
    },
  },
  workflow: {
    title: "协作过程",
    expand: "查看过程",
    collapse: "收起",
    empty: "后台已完成分析",
    sections: {
      planning: "规划",
      execution: "执行",
      fusion: "融合",
      final: "最终来源",
    },
  },
  composer: {
    label: "继续提问",
    taskLabel: "任务/问题",
    helper: "系统会在后台完成协作，并以单助手视图返回结果。",
    placeholder: "发送消息或指令给分析系统…",
    taskPlaceholder: "输入任务或问题…",
    unavailablePlaceholder: "系统暂时不可用，请稍后重试。",
    submit: "发送",
    submitting: "发送中",
    expandStructured: "结构化输入",
    collapseStructured: "收起结构化输入",
    structuredLabel: "结构化输入",
    structuredHelper: "补充背景、约束和输出偏好，系统会自动整理为一条可重放的输入文本。",
    contextLabel: "已知背景/材料",
    contextPlaceholder: "补充已有材料、背景事实或需要一并考虑的信息…",
    constraintsLabel: "约束要求",
    constraintsPlaceholder: "例如时间范围、分析边界、必须覆盖的点…",
    outputPreferenceLabel: "输出偏好",
    outputPreferencePlaceholder: "例如篇幅、结构、语气或是否需要表格/要点…",
    inputTooLong: "输入过长，请缩短后重试。",
  },
  states: {
    unavailableTitle: "系统暂时不可用，请稍后重试",
    unavailableBody: "当前无法连接智能服务，请确认 Python public adapter 已启动。",
    degradedTitle: "系统已连接，但部分能力未就绪",
    degradedBody: "当前仍可继续使用，但部分外部能力可能受限。",
    errorTitle: "本次请求处理失败，请重试",
    errorBody: "请稍后重试，或调整问题后重新发送。",
    loadingTitle: "正在同步会话",
    loadingBody: "正在加载当前对话内容。",
    emptyTitle: "从一个问题开始",
    emptyBody: "围绕研究、判断与组合建议发起对话，系统会在后台完成多阶段协作。",
  },
  agents: {
    eyebrow: "系统说明",
    title: "智能体目录",
    description: "当前目录展示运行时可见的智能体元数据，用于说明分层协作拓扑与默认启用状态。",
    searchLabel: "查找智能体",
    searchPlaceholder: "按 ID、名称或团队搜索",
    loadingTitle: "正在同步智能体目录",
    loadingBody: "正在读取只读智能体目录，请稍候。",
    unavailableTitle: "当前无法读取智能体目录",
    unavailableBody: "请先确认公共适配器服务可访问，再刷新页面查看智能体目录。",
    errorTitle: "智能体目录暂时不可用",
    errorBody: "当前无法完成目录加载，请稍后重试。",
    statsLabel: "智能体目录统计",
    totals: {
      config: "配置智能体",
      runtime: "默认启用节点",
      disabled: "默认禁用",
    },
    none: "无",
    reservedTitle: "保留 / 默认禁用",
    reservedDescription: "存在于元数据中，但默认不进入活跃运行时节点集合。",
    enabled: "默认启用",
    disabledState: "默认禁用",
    capabilitiesLabel: "能力标签",
    roleUnknown: "角色未标注",
    roleTypes: {
      system: "系统角色",
    },
    layers: {
      L1: {
        title: "统筹与规划",
        description: "负责目标界定、任务拆分与分层协作起点。",
      },
      L2: {
        title: "研究与市场情报",
        description: "并行汇集研究、市场与客户侧的关键输入。",
      },
      L3: {
        title: "风险、估值与组合检查",
        description: "围绕风险、估值、合规与组合适配做收敛检查。",
      },
      L4: {
        title: "最终成文",
        description: "整合前序阶段结果，生成最终对外回答。",
      },
    },
  },
  settings: {
    eyebrow: "系统状态",
    title: "系统设置",
    description: "当前页面只展示只读系统状态，用于确认运行时、模型环境、搜索能力与连续性基线。",
    loadingTitle: "正在同步系统状态",
    loadingBody: "正在读取公共适配器的只读 readiness 信息。",
    unavailableTitle: "当前无法读取系统状态",
    unavailableBody: "请先确认公共适配器服务可访问，再刷新页面查看系统状态。",
    overallTitle: "系统总体状态",
    runtimeTitle: "运行时状态",
    providerTitle: "模型环境状态",
    searchTitle: "搜索环境状态",
    checkpointerTitle: "持久化状态",
    continuityTitle: "默认连续性模式",
    storeTitle: "存储方式",
    currentValue: "当前状态",
    modeLabel: "模式",
    hintLabel: "说明",
    ready: "已就绪",
    degraded: "部分能力受限",
    continuityPersistentBody: "当前默认使用持久线程连续性。",
    continuityReplayBody: "当前默认使用回放连续性。它弱于持久线程连续性。",
    storeJsonFile: "JSON 文件存储",
  },
} as const;

const sourceLabels: Record<FinalSource, string> = {
  mainline: "主线",
  baseline: "基线",
  fused: "融合",
};

const continuityLabels: Record<ContinuityMode, string> = {
  persistent: "持久线程",
  replay: "回放连续性",
};

const emitPathLabels: Record<EmitPath, string> = {
  mainline_summary: "主线摘要",
  baseline_sidecar: "基线侧车",
  fusion_writer: "融合写作",
};

const workflowModeLabels: Record<string, string> = {
  Chain: "串行",
  Star: "并行",
  Debate: "辩论",
  Tree: "树形",
};

const stepStatusLabels: Record<AgentStep["status"], string> = {
  complete: "已完成",
  running: "执行中",
  queued: "等待中",
};

const fusionStatusLabels: Record<FusionStep["status"], string> = {
  disabled: "未启用",
  shadow: "影子对照",
  ready: "已就绪",
  selected: "已采用",
  error: "异常",
};

const fusionKindLabels: Record<FusionStep["kind"], string> = {
  baseline: "基线侧车",
  judge: "融合评判",
  writer: "融合写作",
};

const connectionLabels: Record<ConnectionState, string> = {
  loading: "正在同步",
  live: "服务已连接",
  degraded: "部分能力受限",
  unavailable: "服务不可用",
};

const errorCategoryLabels: Record<ErrorCategory, string> = {
  runtime: "运行时",
  provider_env: "模型环境",
  store: "存储",
  contract: "契约",
  request: "请求",
};

const teamLabels: Record<string, string> = {
  management: "统筹",
  research: "研究",
  fundamental: "基本面",
  technology: "技术",
  market: "市场",
  quant: "量化",
  client: "客户",
  valuation: "估值",
  risk: "风险",
  compliance: "合规",
  portfolio: "组合",
  reporting: "报告",
};

const confidenceLabels: Record<string, string> = {
  high: "高把握",
  medium: "中等把握",
  low: "低把握",
};

const agentNameLabels: Record<string, string> = {
  a01_cio_orchestrator: "资本市场决策协作智能体",
  a03_macro_industry_research: "宏观经济与产业链行业研究智能体",
  a04_commodity_hedging: "商品定价分析智能体",
  a05_annual_report_analysis: "公司年报分析智能体",
  a06_financial_statement_analysis: "公司财报分析智能体",
  a07_macro_sentiment: "宏观情绪感知智能体",
  a08_industry_hotspot: "行业热点洞悉智能体",
  a09_company_sentiment_radar: "企业舆情雷达智能体",
  a10_stock_technical_analysis: "个股技术分析智能体",
  a11_index_technical_analysis: "指数技术分析智能体",
  a12_research_synthesis: "分析师研报与观点集成智能体",
  a13_fund_manager_behavior: "基金经理投资行为分析智能体",
  a14_ipo_investor_behavior: "IPO投资者构成与行为分析智能体",
  a15_entity_relation_extraction: "实体关系抽取智能体",
  a16_ml_valuation: "机器学习估值智能体",
  a17_traditional_valuation: "传统估值智能体",
  a18_meta_valuation: "元学习估值智能体",
  a19_risk_identification: "风险识别智能体",
  a20_compliance_review: "合规审查智能体",
  a21_portfolio_manager: "投资组合经理智能体",
  a25_report_center: "综合推理结构与报告生成智能体",
};

const citationLabels: Record<string, string> = {
  "Mainline bundle": "主线摘要",
  "Emitted bundle": "最终输出摘要",
  "主线摘要": "主线摘要",
  "协作过程": "协作过程",
};

const readinessStatusLabels: Record<string, string> = {
  ready: "已就绪",
  import_unavailable: "不可用",
  configured: "已配置",
  missing: "未配置",
  unknown: "未知",
};

const checkpointerStatusLabels: Record<HealthResponse["checkpointer"]["status"], string> = {
  enabled: "已启用",
  disabled: "已关闭",
  unavailable: "不可用",
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
  return mode === "persistent" ? "持久" : "回放";
}

export function emitPathLabel(path: EmitPath) {
  return emitPathLabels[path] ?? path;
}

export function workflowModeLabel(mode: string) {
  return workflowModeLabels[mode] ?? mode;
}

export function agentStepStatusLabel(status: AgentStep["status"]) {
  return stepStatusLabels[status] ?? status;
}

export function fusionStatusLabel(status: FusionStep["status"]) {
  return fusionStatusLabels[status] ?? status;
}

export function fusionKindLabel(kind: FusionStep["kind"]) {
  return fusionKindLabels[kind] ?? kind;
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
    signals.push("运行时未就绪");
  }
  if (health.providerEnv.status !== "configured") {
    signals.push("模型环境未就绪");
  }
  if (health.searchEnv.status !== "configured") {
    signals.push("外部搜索未就绪");
  }
  return signals;
}

export function workflowSummaryLabel(workflow: WorkflowModel) {
  const completed = workflow.layerDone.length;
  if (completed <= 0) {
    return `${zhCN.workflow.title} · ${zhCN.workflow.empty}`;
  }
  return `${zhCN.workflow.title} · ${completed}个阶段已完成`;
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
