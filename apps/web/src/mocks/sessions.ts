import type { ChatSessionSummary } from "../types/chat";

export const INITIAL_SESSIONS: ChatSessionSummary[] = [
  {
    id: "session-fixed-dag-1",
    title: "电动车公司风险与估值",
    updatedAt: "今天 08:48",
    preview: "固定 DAG 骨架返回了公开回答和工作流快照。",
    finalSource: "reset_skeleton",
    phase: "在线",
  },
  {
    id: "session-fixed-dag-2",
    title: "半导体供应链解读",
    updatedAt: "今天 09:01",
    preview: "工作流检查器展示 DAG 阶段、批次和步骤元数据。",
    finalSource: "reset_skeleton",
    phase: "在线",
  },
  {
    id: "session-fixed-dag-3",
    title: "带风险约束的组合复盘",
    updatedAt: "今天 09:12",
    preview: "Transcript 只保留用户与助手消息；工作流保留在检查器中。",
    finalSource: "reset_skeleton",
    phase: "在线",
    active: true,
  },
];
