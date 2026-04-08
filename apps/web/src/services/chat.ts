import type { AgentCatalogModel } from "../types/agents";
import type {
  HealthResponse,
  PublicThreadDetail,
  SendMessageRequest,
  SendMessageResponse,
  SendMessageStreamEvent,
  StructuredInputModel,
  ThreadsResponse,
} from "../types/chat";
import { apiRequest, streamNdjson } from "./api";

export function getHealth() {
  return apiRequest<HealthResponse>("/api/health");
}

export function getThreads() {
  return apiRequest<ThreadsResponse>("/api/threads");
}

export function getAgentCatalog() {
  return apiRequest<AgentCatalogModel>("/api/agents");
}

export function createThread() {
  return apiRequest<PublicThreadDetail>("/api/threads", {
    method: "POST",
    body: JSON.stringify({}),
  });
}

export function getThread(threadId: string) {
  return apiRequest<PublicThreadDetail>(`/api/threads/${threadId}`);
}

export function sendMessage(threadId: string, text: string, structuredInput?: StructuredInputModel) {
  const payload: SendMessageRequest = structuredInput ? { text, structuredInput } : { text };
  return apiRequest<SendMessageResponse>(`/api/threads/${threadId}/messages`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function sendMessageStream(
  threadId: string,
  text: string,
  structuredInput: StructuredInputModel | undefined,
  onEvent: (event: SendMessageStreamEvent) => void,
) {
  const payload: SendMessageRequest = structuredInput ? { text, structuredInput } : { text };
  return streamNdjson<SendMessageStreamEvent>(
    `/api/threads/${threadId}/messages/stream`,
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
    onEvent,
  );
}
