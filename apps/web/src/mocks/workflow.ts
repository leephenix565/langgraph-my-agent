import type { FinalSource } from "../types/chat";
import type { AgentStep, FusionStep, WorkflowModel } from "../types/workflow";

const layerPlan = [
  { layer: "L1", mode: "Chain", selected: ["a01_cio_orchestrator"], note: "明确问题边界与分层协作方式。" },
  {
    layer: "L2",
    mode: "Star",
    selected: [
      "a03_macro_industry_research",
      "a07_macro_sentiment",
      "a12_research_synthesis",
      "a15_entity_relation_extraction",
    ],
    note: "并行获取宏观、情绪、研报与关系网络证据。",
  },
  {
    layer: "L3",
    mode: "Star",
    selected: ["a16_ml_valuation", "a17_traditional_valuation", "a18_meta_valuation"],
    note: "通过外部估值服务形成多模型估值视角。",
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
      title: "问题解析与协同编排智能体",
      summary: "先把问题整理成分层计划，再约束最终输出形式。",
      status: "complete",
      signal: "contract-ready",
    },
    {
      id: `${theme}-2`,
      layer: "L2",
      agentId: "a03_macro_industry_research",
      title: "宏观分析智能体",
      summary: "梳理宏观周期、产业链韧性与行业竞争格局。",
      status: "complete",
      signal: "macro and industry evidence",
    },
    {
      id: `${theme}-3`,
      layer: "L2",
      agentId: "a12_research_synthesis",
      title: "分析师研报与观点集成智能体",
      summary: "汇总卖方研报观点，形成一致预期与分歧度线索。",
      status: "complete",
      signal: "consensus forming",
    },
    {
      id: `${theme}-4`,
      layer: "L3",
      agentId: "a17_traditional_valuation",
      title: "传统企业估值智能体",
      summary: "通过外部传统估值服务约束目标价区间与敏感性。",
      status: "complete",
      signal: "external valuation",
    },
    {
      id: `${theme}-5`,
      layer: "L4",
      agentId: "a25_report_center",
      title: "报告生成智能体",
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
