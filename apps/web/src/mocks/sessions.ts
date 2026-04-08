import type { ChatSessionSummary } from "../types/chat";

export const INITIAL_SESSIONS: ChatSessionSummary[] = [
  {
    id: "session-mainline",
    title: "新能源汽车企业财报与风险",
    updatedAt: "今天 08:48",
    preview: "政策边际缓和，但行业情绪仍偏选择性修复。",
    finalSource: "mainline",
    phase: "Live",
  },
  {
    id: "session-baseline",
    title: "全球半导体供应链推演",
    updatedAt: "今天 09:01",
    preview: "先写 downside，再补充观察点。",
    finalSource: "baseline",
    phase: "Live",
  },
  {
    id: "session-fused",
    title: "新能源组合再平衡",
    updatedAt: "今天 09:12",
    preview: "保留主线配置方向，同时压低高波动暴露。",
    finalSource: "fused",
    phase: "Live",
    active: true,
  },
];
