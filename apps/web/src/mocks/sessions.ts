import type { ChatSessionSummary } from "../types/chat";

export const INITIAL_SESSIONS: ChatSessionSummary[] = [
  {
    id: "session-fixed-dag-1",
    title: "EV company risk and valuation",
    updatedAt: "Today 08:48",
    preview: "Fixed DAG skeleton returned a public-safe answer and workflow snapshot.",
    finalSource: "reset_skeleton",
    phase: "Live",
  },
  {
    id: "session-fixed-dag-2",
    title: "Semiconductor supply-chain readout",
    updatedAt: "Today 09:01",
    preview: "The workflow inspector shows DAG stages, batches, and step metadata.",
    finalSource: "reset_skeleton",
    phase: "Live",
  },
  {
    id: "session-fixed-dag-3",
    title: "Portfolio review with risk constraints",
    updatedAt: "Today 09:12",
    preview: "Transcript remains user and assistant only; workflow stays in the inspector.",
    finalSource: "reset_skeleton",
    phase: "Live",
    active: true,
  },
];
