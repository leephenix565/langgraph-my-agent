import type { ChatSessionSummary } from "../types/chat";

export const INITIAL_SESSIONS: ChatSessionSummary[] = [
  {
    id: "session-fixed-dag-1",
    title: "电动车公司风险与估值",
    updatedAt: "今天 08:48",
    preview: "已完成风险与估值研判，过程记录可展开查看。",
    finalSource: "reset_skeleton",
    phase: "在线",
  },
  {
    id: "session-fixed-dag-2",
    title: "半导体供应链解读",
    updatedAt: "今天 09:01",
    preview: "已按固定研判流程整理供应链相关线索。",
    finalSource: "reset_skeleton",
    phase: "在线",
  },
  {
    id: "session-fixed-dag-3",
    title: "带风险约束的组合复盘",
    updatedAt: "今天 09:12",
    preview: "已汇总组合风险约束，过程记录可展开查看。",
    finalSource: "reset_skeleton",
    phase: "在线",
    active: true,
  },
];
