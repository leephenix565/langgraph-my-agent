import type { PublicTurn } from "../types/chat";
import { createWorkflowVariant } from "./workflow";

function nowStamp(seed: string): string {
  return `2026-04-03 ${seed}`;
}

function buildAssistantTurn(id: string, answer: string, prompt: string): PublicTurn {
  return {
    id,
    role: "assistant",
    text: answer,
    createdAt: nowStamp("09:32"),
    runId: "mock-reset-skeleton-001",
    continuityMode: "replay",
    answerCard: {
      answer,
      finalSource: "reset_skeleton",
      confidence: "medium",
      citations: [
        { label: "Fixed DAG bundle", note: "公开回答由固定 DAG 研判流程生成。" },
        { label: "Workflow", note: "流程详情显示在检查器中，不作为额外 transcript 轮次。" },
      ],
      evidenceCount: 2,
    },
    workflow: createWorkflowVariant(prompt),
  };
}

export const TRANSCRIPTS_BY_SESSION: Record<string, PublicTurn[]> = {
  "session-fixed-dag-1": [
    {
      id: "fixed-dag-user-1",
      role: "user",
      text: "总结电动车公司的风险画像。",
      createdAt: nowStamp("08:48"),
    },
    buildAssistantTurn(
      "fixed-dag-assistant-1",
      "已完成本轮固定 DAG 研判流程。公开回答保留核心结论，流程详情可在检查器中查看。",
      "电动车公司风险画像",
    ),
  ],
  "session-fixed-dag-2": [
    {
      id: "fixed-dag-user-2",
      role: "user",
      text: "给我一份半导体供应链更新。",
      createdAt: nowStamp("09:01"),
    },
    buildAssistantTurn(
      "fixed-dag-assistant-2",
      "公开 transcript 仍是一条助手回答；流程快照记录阶段、批次和步骤结果。",
      "半导体供应链更新",
    ),
  ],
  "session-fixed-dag-3": [
    {
      id: "fixed-dag-user-3",
      role: "user",
      text: "按风险约束复盘组合。",
      createdAt: nowStamp("09:12"),
    },
    buildAssistantTurn(
      "fixed-dag-assistant-3",
      "风险约束在回答中汇总；内部步骤元数据保留在工作流检查器中。",
      "组合风险约束",
    ),
  ],
};

export function createUserTurn(input: string): PublicTurn {
  return {
    id: `user-${Math.random().toString(36).slice(2, 10)}`,
    role: "user",
    text: input,
    createdAt: "2026-04-03 now",
  };
}

export function createMockAssistantTurn(input: string): PublicTurn {
  const answer =
    "这个 mock 使用固定 DAG 研判流程。用户/助手文本保留在 transcript 中；流程详情保留在检查器中。";

  return buildAssistantTurn(`assistant-${Math.random().toString(36).slice(2, 10)}`, answer, input);
}
