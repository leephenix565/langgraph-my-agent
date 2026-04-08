import type { FinalSource } from "../types/chat";
import type { AgentStep, FusionStep, WorkflowModel } from "../types/workflow";

const layerPlan = [
  { layer: "L1", mode: "Chain", selected: ["a01_cio_orchestrator"], note: "明确问题边界与分层协作方式。" },
  {
    layer: "L2",
    mode: "Star",
    selected: ["a03_macro_policy", "a10_industry_sentiment", "a15_research_synthesis", "a17_client_profile"],
    note: "并行获取研究、行业情绪与客户约束背景。",
  },
  {
    layer: "L3",
    mode: "Star",
    selected: ["a18_primary_secondary_valuation", "a21_reg_compliance", "a23_portfolio_opt"],
    note: "补足估值、合规与组合适配检查。",
  },
  { layer: "L4", mode: "Chain", selected: ["a25_report_center"], note: "整理为对外可读的单助手回答。" },
] as const;

const layerMode = {
  L1: "Chain",
  L2: "Star",
  L3: "Star",
  L4: "Chain",
};

function buildAgentSteps(theme: string): AgentStep[] {
  return [
    {
      id: `${theme}-1`,
      layer: "L1",
      agentId: "a01_cio_orchestrator",
      title: "首席投资统筹",
      summary: "先把问题整理成分层计划，再约束最终输出形式。",
      status: "complete",
      signal: "contract-ready",
    },
    {
      id: `${theme}-2`,
      layer: "L2",
      agentId: "a03_macro_policy",
      title: "宏观政策分析师",
      summary: "梳理利率、流动性与政策变化对当前问题的直接影响。",
      status: "complete",
      signal: "macro easing",
    },
    {
      id: `${theme}-3`,
      layer: "L2",
      agentId: "a15_research_synthesis",
      title: "研究综合分析师",
      summary: "汇总研究观点，形成对外叙事的主线框架。",
      status: "complete",
      signal: "consensus forming",
    },
    {
      id: `${theme}-4`,
      layer: "L3",
      agentId: "a18_primary_secondary_valuation",
      title: "一二级估值分析师",
      summary: "用估值约束主线结论，避免回答只剩方向感。",
      status: "complete",
      signal: "valuation disciplined",
    },
    {
      id: `${theme}-5`,
      layer: "L4",
      agentId: "a25_report_center",
      title: "报告中心",
      summary: "将内部分析整理为单助手可直接展示的回答。",
      status: "complete",
      signal: "answer emitted",
    },
  ];
}

function buildFusionSteps(finalSource: FinalSource): FusionStep[] {
  const baselineSummary =
    finalSource === "baseline"
      ? "基线侧车给出了更清晰的风险表达，因此被选为最终来源。"
      : "基线侧车作为对照路径完成运行，但没有直接改变主线业务语义。";

  const judgeSummary =
    finalSource === "fused"
      ? "融合评判选择保留主线结构，并吸收基线中的风险表达。"
      : finalSource === "baseline"
        ? "融合评判认为基线版本更适合当前问题。"
        : "融合评判最终保留主线回答作为默认输出。";

  const writerSummary =
    finalSource === "fused"
      ? "融合写作生成了最终对外可见的回答。"
      : finalSource === "baseline"
        ? "融合写作采用基线版本作为最终可见输出。"
        : "融合写作保持影子模式，最终仍沿用主线输出。";

  return [
    { id: `baseline-${finalSource}`, kind: "baseline", label: "Baseline sidecar", status: "ready", summary: baselineSummary },
    {
      id: `judge-${finalSource}`,
      kind: "judge",
      label: "Fusion judge",
      status: finalSource === "mainline" ? "shadow" : "ready",
      summary: judgeSummary,
    },
    {
      id: `writer-${finalSource}`,
      kind: "writer",
      label: "Fusion writer",
      status: finalSource === "fused" || finalSource === "baseline" ? "selected" : "shadow",
      summary: writerSummary,
    },
  ];
}

export function createWorkflowVariant(finalSource: FinalSource, theme: string): WorkflowModel {
  return {
    layerPlan: layerPlan.map((item) => ({
      ...item,
      selected: [...item.selected],
    })),
    layerMode,
    currentLayer: "L4",
    layerDone: ["L1", "L2", "L3", "L4"],
    agentSteps: buildAgentSteps(theme),
    fusionSteps: buildFusionSteps(finalSource),
    finalSource,
    provenanceNote:
      finalSource === "fused"
        ? "最终回答来自融合写作路径，主线 bundle 仍保留为 canonical mainline。"
        : finalSource === "baseline"
          ? "最终回答来自隔离的基线路径，而不是原始 graph messages。"
          : "最终回答来自主线输出路径，基线、评判和写作仍保持 sidecar 语义。",
    provenance: {
      emitPath:
        finalSource === "fused" ? "fusion_writer" : finalSource === "baseline" ? "baseline_sidecar" : "mainline_summary",
      finalSource,
      continuityMode: "replay",
      summary:
        finalSource === "fused"
          ? "最终回答来自融合写作路径，并保留主线研究框架。"
          : finalSource === "baseline"
            ? "最终回答来自基线侧车路径，用于强调 downside 与风险约束。"
            : "最终回答直接采用主线摘要路径作为输出来源。",
    },
  };
}
