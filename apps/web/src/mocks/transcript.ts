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
        { label: "Fixed DAG bundle", note: "Public answer projected from the reset skeleton fixed DAG path." },
        { label: "Workflow", note: "DAG details are rendered in the inspector, not as extra transcript turns." },
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
      text: "Summarize the EV company risk profile.",
      createdAt: nowStamp("08:48"),
    },
    buildAssistantTurn(
      "fixed-dag-assistant-1",
      "The reset skeleton answer keeps the conclusion visible while the DAG workflow stays in the inspector.",
      "EV company risk profile",
    ),
  ],
  "session-fixed-dag-2": [
    {
      id: "fixed-dag-user-2",
      role: "user",
      text: "Give me a semiconductor supply-chain update.",
      createdAt: nowStamp("09:01"),
    },
    buildAssistantTurn(
      "fixed-dag-assistant-2",
      "The public transcript remains a single assistant answer. The workflow snapshot records stages, batches, and step results.",
      "Semiconductor supply-chain update",
    ),
  ],
  "session-fixed-dag-3": [
    {
      id: "fixed-dag-user-3",
      role: "user",
      text: "Review the portfolio with risk constraints.",
      createdAt: nowStamp("09:12"),
    },
    buildAssistantTurn(
      "fixed-dag-assistant-3",
      "Risk constraints are summarized in the answer; internal step metadata is kept in the workflow inspector.",
      "Portfolio risk constraints",
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
    "This mock uses the fixed DAG reset skeleton. User/assistant text stays in the transcript; DAG details stay in the inspector.";

  return buildAssistantTurn(`assistant-${Math.random().toString(36).slice(2, 10)}`, answer, input);
}
