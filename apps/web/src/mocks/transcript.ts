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
        {
          label: "Fixed DAG bundle",
          note: "系统按照固定研判流程组织本轮分析，包括问题理解、信息整理、并行分析、维度综合与报告生成。",
        },
        { label: "User question", note: "围绕你提出的问题进行结构化梳理。" },
        { label: "Workflow", note: "如需查看过程，可展开“流程详情”。" },
      ],
      evidenceCount: 3,
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
      "已完成本轮研判流程。系统已按问题理解、信息整理、并行分析、维度综合与报告生成组织本轮回答。",
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
      "已完成本轮研判流程。核心结论以一条助手回答呈现，过程记录可在流程详情中查看。",
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
      "风险约束已在回答中汇总；如需查看过程，可展开流程详情。",
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
    "已完成本轮研判流程。系统按固定研判流程组织回答，过程记录可在流程详情中查看。";

  return buildAssistantTurn(`assistant-${Math.random().toString(36).slice(2, 10)}`, answer, input);
}
