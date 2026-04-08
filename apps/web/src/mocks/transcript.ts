import type { FinalSource, PublicTurn } from "../types/chat";
import { createWorkflowVariant } from "./workflow";

function nowStamp(seed: string): string {
  return `2026-04-03 ${seed}`;
}

function buildAssistantTurn(id: string, source: FinalSource, answer: string, prompt: string): PublicTurn {
  return {
    id,
    role: "assistant",
    text: answer,
    createdAt: nowStamp("09:32"),
    runId: `mock-${source}-001`,
    continuityMode: "replay",
    answerCard: {
      answer,
      finalSource: source,
      confidence: source === "baseline" ? "medium" : "high",
      citations: [
        { label: "主线摘要", note: "聊天主线程只展示用户可见内容，不直接渲染 graph 内部消息。" },
        { label: "协作过程", note: "多智能体协作被压缩为可展开的过程层，而不是多个聊天说话人。" },
      ],
      evidenceCount: 2,
    },
    workflow: createWorkflowVariant(source, prompt),
  };
}

export const TRANSCRIPTS_BY_SESSION: Record<string, PublicTurn[]> = {
  "session-mainline": [
    {
      id: "mainline-user-1",
      role: "user",
      text: "请给我一个半导体景气度更新，重点看政策与行业情绪。",
      createdAt: nowStamp("08:48"),
    },
    buildAssistantTurn(
      "mainline-assistant-1",
      "mainline",
      "当前半导体链路更适合用“谨慎改善”来描述。政策边际缓和带来了估值修复空间，但行业情绪仍偏选择性回暖，因此结论更适合强调节奏改善，而不是全面反转。",
      "半导体景气度更新",
    ),
  ],
  "session-baseline": [
    {
      id: "baseline-user-1",
      role: "user",
      text: "帮我做一版医药板块风险扫描，先写 downside。",
      createdAt: nowStamp("09:01"),
    },
    buildAssistantTurn(
      "baseline-assistant-1",
      "baseline",
      "如果先写 downside，这一版更应该把估值回撤、政策节奏和业绩兑现的不确定性放在前面，再补充后续观察点，而不是直接给出乐观结论。",
      "医药板块风险扫描",
    ),
  ],
  "session-fused": [
    {
      id: "fused-user-1",
      role: "user",
      text: "请把新能源组合再平衡整理成一版可以直接发给投资经理的建议。",
      createdAt: nowStamp("09:12"),
    },
    buildAssistantTurn(
      "fused-assistant-1",
      "fused",
      "这版建议更适合用“保留主线、压低波动”来写。主线研究给出了配置方向，融合侧补入了风险约束，所以最终不是简单追高，而是在维持核心暴露的同时，把高波动环节压回到组合可承受区间。",
      "新能源组合再平衡",
    ),
  ],
};

function inferSource(text: string): FinalSource {
  if (text.includes("对照") || text.toLowerCase().includes("baseline") || text.includes("风险")) {
    return "baseline";
  }
  if (text.includes("融合") || text.includes("综合") || text.includes("平衡")) {
    return "fused";
  }
  return "mainline";
}

export function createUserTurn(input: string): PublicTurn {
  return {
    id: `user-${Math.random().toString(36).slice(2, 10)}`,
    role: "user",
    text: input,
    createdAt: "2026-04-03 now",
  };
}

export function createMockAssistantTurn(input: string): PublicTurn {
  const finalSource = inferSource(input);
  const answer =
    finalSource === "fused"
      ? "这次 mock 输出会选择融合视角：保留主线结论，同时把基线中的风险约束合并进最终表达。聊天线程只展示单助手回答，协作过程会放在下方 inspector 中。"
      : finalSource === "baseline"
        ? "这次 mock 输出会更强调基线视角，先写 downside 与约束条件，再补充后续观察点。公开线程中不会直接暴露 graph 内部消息。"
        : "这次 mock 输出保持主线为最终来源，先给结论，再补充约束与行动建议。协作过程会单独收在 workflow inspector 里。";

  return buildAssistantTurn(`assistant-${Math.random().toString(36).slice(2, 10)}`, finalSource, answer, input);
}
