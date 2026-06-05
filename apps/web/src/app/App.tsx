import { startTransition, useEffect, useRef, useState } from "react";
import { BrowserRouter, useLocation } from "react-router-dom";
import { Sidebar } from "../components/shell/Sidebar";
import {
  clearThreadMessages,
  createThread,
  deleteThread,
  getHealth,
  getThread,
  getThreads,
  sendMessage,
  sendMessageStream,
} from "../services/chat";
import { ApiError, getApiErrorMessage, isApiUnavailableError } from "../services/api";
import { zhCN } from "../content/zh-CN";
import type {
  ChatSessionSummary,
  HealthResponse,
  PublicThreadDetail,
  PublicTurn,
  SendMessageResponse,
  SendMessageStreamEvent,
  StructuredInputModel,
} from "../types/chat";
import type { WorkflowModel, WorkflowStageProgress } from "../types/workflow";
import { AppRoutes } from "./routes";

const STREAMING_PLACEHOLDER_ANSWER = "\u6b63\u5728\u534f\u4f5c\u2026";
const STREAMING_INITIAL_PROGRESS: WorkflowStageProgress[] = [
  { key: "planning", title: "Planning", status: "running" },
  { key: "evidence", title: "Evidence seams", status: "waiting" },
  { key: "l2_analysis", title: "L2 analysis", status: "waiting" },
  { key: "dimension_composite", title: "Dimension composites", status: "waiting" },
  { key: "decision", title: "Decision", status: "waiting" },
  { key: "report", title: "Report", status: "waiting" },
];

interface WorkspaceFrameProps {
  sessions: ChatSessionSummary[];
  activeSessionId: string | null;
  activeTurns: PublicTurn[];
  onSelectSession: (sessionId: string) => void;
  onCreateThread: () => void;
  onDeleteThread: (sessionId: string) => void;
  onSendMessage: (value: string, structuredInput?: StructuredInputModel) => void;
  onClearMessages: () => void;
  isLoading: boolean;
  isSending: boolean;
  deletingThreadId: string | null;
  clearingThreadId: string | null;
  unavailable: boolean;
  degraded: boolean;
  errorMessage: string | null;
  errorMeta: ApiError | null;
  health: HealthResponse | null;
}

function nowLabel() {
  return new Date().toISOString().slice(0, 16).replace("T", " ");
}

function makeClientId(prefix: string) {
  return `${prefix}-${Math.random().toString(16).slice(2, 10)}`;
}

function createStreamingWorkflow(base?: WorkflowModel, liveProgress?: WorkflowStageProgress[]): WorkflowModel {
  const nextProgress = liveProgress ?? base?.liveProgress ?? STREAMING_INITIAL_PROGRESS;
  const runningStage = nextProgress.find((stage) => stage.status === "running");
  return {
    schema: base?.schema ?? "workflow_snapshot_v2",
    planId: base?.planId ?? "streaming-placeholder",
    stages: base?.stages?.length
      ? base.stages
      : nextProgress.map((stage) => ({ key: stage.key, title: stage.title, stepIds: [] })),
    dagSteps: base?.dagSteps ?? [],
    dimensionGroups: base?.dimensionGroups ?? [],
    currentStage: base?.currentStage ?? runningStage?.key ?? null,
    completedSteps: base?.completedSteps ?? [],
    executionBatches: base?.executionBatches ?? [],
    stepResults: base?.stepResults ?? {},
    finalSource: base?.finalSource ?? "reset_skeleton",
    provenanceNote: base?.provenanceNote ?? "Generating a public-safe fixed DAG workflow summary.",
    provenance: base?.provenance ?? null,
    liveProgress: nextProgress,
  };
}

function buildOptimisticUserTurn(text: string, structuredInput?: StructuredInputModel): PublicTurn {
  return {
    id: makeClientId("user-optimistic"),
    role: "user",
    text,
    createdAt: nowLabel(),
    structuredInput,
  };
}

function buildOptimisticAssistantTurn(): PublicTurn {
  return {
    id: makeClientId("assistant-stream"),
    role: "assistant",
    text: STREAMING_PLACEHOLDER_ANSWER,
    createdAt: nowLabel(),
    answerCard: {
      answer: STREAMING_PLACEHOLDER_ANSWER,
      finalSource: "reset_skeleton",
    },
    workflow: createStreamingWorkflow(undefined, STREAMING_INITIAL_PROGRESS),
  };
}

function mergeStreamingAssistantTurn(turn: PublicTurn, event: SendMessageStreamEvent): PublicTurn {
  if (turn.role !== "assistant") {
    return turn;
  }

  switch (event.type) {
    case "run.started":
      return {
        ...turn,
        continuityMode: event.data.continuityMode,
        workflow: createStreamingWorkflow(turn.workflow, turn.workflow?.liveProgress ?? STREAMING_INITIAL_PROGRESS),
      };
    case "workflow.stage":
      return {
        ...turn,
        workflow: createStreamingWorkflow(
          {
            ...turn.workflow,
            currentStage: event.data.currentStage ?? turn.workflow?.currentStage ?? null,
          } as WorkflowModel,
          event.data.stages,
        ),
      };
    case "workflow.snapshot":
      return {
        ...turn,
        runId: event.data.runId ?? turn.runId,
        continuityMode: event.data.continuityMode,
        workflow: createStreamingWorkflow(event.data.workflow, turn.workflow?.liveProgress),
      };
    default:
      return turn;
  }
}

function WorkspaceFrame({
  sessions,
  activeSessionId,
  activeTurns,
  onSelectSession,
  onCreateThread,
  onDeleteThread,
  onSendMessage,
  onClearMessages,
  isLoading,
  isSending,
  deletingThreadId,
  clearingThreadId,
  unavailable,
  degraded,
  errorMessage,
  errorMeta,
  health,
}: WorkspaceFrameProps) {
  const location = useLocation();
  const activeSession = sessions.find((session) => session.id === activeSessionId) ?? sessions[0] ?? null;
  const connectionState = unavailable ? "unavailable" : isLoading ? "loading" : degraded ? "degraded" : "live";
  const shellMode = location.pathname === "/agents" ? "agents" : location.pathname === "/settings" ? "settings" : "chat";

  return (
    <div className={`app-shell app-shell--${shellMode}`}>
      <Sidebar
        sessions={sessions}
        activeSessionId={activeSession?.id ?? ""}
        onSelectSession={onSelectSession}
        onCreateThread={onCreateThread}
        onDeleteThread={onDeleteThread}
        createDisabled={unavailable || isLoading}
        deleteDisabled={unavailable || isLoading || isSending || Boolean(deletingThreadId)}
        deletingThreadId={deletingThreadId}
        connectionState={connectionState}
      />
      <main className="app-main">
        <AppRoutes
          activeSession={activeSession}
          activeTurns={activeTurns}
          onSendMessage={onSendMessage}
          onClearMessages={onClearMessages}
          isLoading={isLoading}
          isSending={isSending}
          isClearing={Boolean(activeSession?.id && clearingThreadId === activeSession.id)}
          unavailable={unavailable}
          degraded={degraded}
          errorMessage={errorMessage}
          errorMeta={errorMeta}
          health={health}
        />
      </main>
    </div>
  );
}

function markActiveSession(sessions: ChatSessionSummary[], activeSessionId: string | null) {
  return sessions.map((session) => ({ ...session, active: session.id === activeSessionId }));
}

export default function App() {
  const [sessions, setSessions] = useState<ChatSessionSummary[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [turnsBySession, setTurnsBySession] = useState<Record<string, PublicTurn[]>>({});
  const [isLoading, setIsLoading] = useState(true);
  const [isSending, setIsSending] = useState(false);
  const [deletingThreadId, setDeletingThreadId] = useState<string | null>(null);
  const [clearingThreadId, setClearingThreadId] = useState<string | null>(null);
  const [unavailable, setUnavailable] = useState(false);
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [errorMeta, setErrorMeta] = useState<ApiError | null>(null);
  const bootstrappedRef = useRef(false);

  const activeTurns = activeSessionId ? turnsBySession[activeSessionId] ?? [] : [];
  const degraded = !unavailable && health?.overallStatus === "degraded";

  async function refreshHealthState() {
    const nextHealth = await getHealth();
    setHealth(nextHealth);
    setUnavailable(false);
    return nextHealth;
  }

  function setRequestError(error: unknown, fallback: string) {
    const nextError = error instanceof ApiError ? error : null;
    setErrorMeta(nextError);
    setErrorMessage(getApiErrorMessage(error, fallback));
    setUnavailable(isApiUnavailableError(error));
  }

  function setStreamError(message: string, code: string, category: ApiError["category"]) {
    setErrorMeta(new ApiError(message, { code, category }));
    setErrorMessage(message);
    setUnavailable(false);
  }

  async function hydrateFirstThread() {
    await refreshHealthState();
    const threadList = await getThreads();
    let sessionsFromApi = threadList.threads;
    let initialDetail: PublicThreadDetail | null = null;

    if (!sessionsFromApi.length) {
      initialDetail = await createThread();
      sessionsFromApi = [initialDetail.thread];
    }

    const nextActiveSessionId = initialDetail?.thread.id ?? sessionsFromApi[0]?.id ?? null;
    const nextTurnsBySession: Record<string, PublicTurn[]> = {};

    if (initialDetail) {
      nextTurnsBySession[initialDetail.thread.id] = initialDetail.turns;
    } else if (nextActiveSessionId) {
      const detail = await getThread(nextActiveSessionId);
      sessionsFromApi = sessionsFromApi.map((session) => (session.id === detail.thread.id ? detail.thread : session));
      nextTurnsBySession[nextActiveSessionId] = detail.turns;
    }

    startTransition(() => {
      setSessions(markActiveSession(sessionsFromApi, nextActiveSessionId));
      setActiveSessionId(nextActiveSessionId);
      setTurnsBySession(nextTurnsBySession);
    });
  }

  useEffect(() => {
    if (bootstrappedRef.current) {
      return;
    }
    bootstrappedRef.current = true;

    void (async () => {
      setIsLoading(true);
      setErrorMessage(null);
      setErrorMeta(null);
      try {
        await hydrateFirstThread();
      } catch (error) {
        setRequestError(error, "Failed to bootstrap public thread list.");
      } finally {
        setIsLoading(false);
      }
    })();
  }, []);

  async function handleSelectSession(sessionId: string) {
    if (sessionId === activeSessionId) {
      return;
    }
    setIsLoading(true);
    setErrorMessage(null);
    setErrorMeta(null);
    try {
      const detail = await getThread(sessionId);
      await refreshHealthState();
      startTransition(() => {
        setActiveSessionId(sessionId);
        setTurnsBySession((current) => ({ ...current, [sessionId]: detail.turns }));
        setSessions((current) =>
          markActiveSession(
            current.map((session) => (session.id === sessionId ? detail.thread : session)),
            sessionId,
          ),
        );
      });
    } catch (error) {
      setRequestError(error, "Failed to load thread detail.");
      if (!isApiUnavailableError(error)) {
        try {
          await refreshHealthState();
        } catch {
          // Keep the original request error visible.
        }
      }
    } finally {
      setIsLoading(false);
    }
  }

  async function handleSendMessage(value: string, structuredInput?: StructuredInputModel) {
    const sessionId = activeSessionId;
    if (!sessionId) {
      return;
    }
    setIsSending(true);
    setErrorMessage(null);
    setErrorMeta(null);

    const optimisticUserTurn = buildOptimisticUserTurn(value, structuredInput);
    const optimisticAssistantTurn = buildOptimisticAssistantTurn();
    startTransition(() => {
      setTurnsBySession((current) => ({
        ...current,
        [sessionId]: [...(current[sessionId] ?? []), optimisticUserTurn, optimisticAssistantTurn],
      }));
    });

    try {
      const streamState: {
        finalResponse: SendMessageResponse | null;
        error: { code: string; message: string; category: ApiError["category"] } | null;
      } = {
        finalResponse: null,
        error: null,
      };
      const streamed = await sendMessageStream(sessionId, value, structuredInput, (event) => {
        if (event.type === "answer.final") {
          streamState.finalResponse = event.data.response;
          return;
        }
        if (event.type === "error") {
          streamState.error = event.data;
          return;
        }
        startTransition(() => {
          setTurnsBySession((current) => ({
            ...current,
            [sessionId]: (current[sessionId] ?? []).map((turn) =>
              turn.id === optimisticAssistantTurn.id ? mergeStreamingAssistantTurn(turn, event) : turn,
            ),
          }));
        });
      });

      if (!streamed) {
        const response = await sendMessage(sessionId, value, structuredInput);
        await refreshHealthState();
        startTransition(() => {
          setTurnsBySession((current) => ({ ...current, [sessionId]: response.turns }));
          setSessions((current) =>
            markActiveSession(
              current.map((session) => (session.id === sessionId ? response.thread : session)),
              sessionId,
            ),
          );
        });
        return;
      }

      if (streamState.finalResponse) {
        await refreshHealthState();
        startTransition(() => {
          setTurnsBySession((current) => ({ ...current, [sessionId]: streamState.finalResponse!.turns }));
          setSessions((current) =>
            markActiveSession(
              current.map((session) => (session.id === sessionId ? streamState.finalResponse!.thread : session)),
              sessionId,
            ),
          );
        });
        return;
      }

      startTransition(() => {
        setTurnsBySession((current) => ({
          ...current,
          [sessionId]: (current[sessionId] ?? []).filter(
            (turn) => turn.id !== optimisticUserTurn.id && turn.id !== optimisticAssistantTurn.id,
          ),
        }));
      });
      if (streamState.error) {
        setStreamError(streamState.error.message, streamState.error.code, streamState.error.category);
      } else {
        setStreamError(
          "Streaming response ended before a final public answer was received.",
          "runtime_stream_incomplete",
          "runtime",
        );
      }
    } catch (error) {
      startTransition(() => {
        setTurnsBySession((current) => ({
          ...current,
          [sessionId]: (current[sessionId] ?? []).filter(
            (turn) => turn.id !== optimisticUserTurn.id && turn.id !== optimisticAssistantTurn.id,
          ),
        }));
      });
      setRequestError(error, "Failed to send message.");
      if (!isApiUnavailableError(error)) {
        try {
          await refreshHealthState();
        } catch {
          // Keep the original request error visible.
        }
      }
    } finally {
      setIsSending(false);
    }
  }

  async function handleCreateThread() {
    setIsLoading(true);
    setErrorMessage(null);
    setErrorMeta(null);
    try {
      const detail = await createThread();
      await refreshHealthState();
      startTransition(() => {
        setActiveSessionId(detail.thread.id);
        setTurnsBySession((current) => ({ ...current, [detail.thread.id]: detail.turns }));
        setSessions((current) => {
          const nextSessions = [detail.thread, ...current.filter((session) => session.id !== detail.thread.id)];
          return markActiveSession(nextSessions, detail.thread.id);
        });
      });
    } catch (error) {
      setRequestError(error, "Failed to create a new public thread.");
      if (!isApiUnavailableError(error)) {
        try {
          await refreshHealthState();
        } catch {
          // Keep the original request error visible.
        }
      }
    } finally {
      setIsLoading(false);
    }
  }

  async function handleDeleteThread(sessionId: string) {
    if (deletingThreadId || isSending || !window.confirm(zhCN.sidebar.confirmDeleteThread)) {
      return;
    }
    setDeletingThreadId(sessionId);
    setErrorMessage(null);
    setErrorMeta(null);
    try {
      await deleteThread(sessionId);
      await refreshHealthState();

      const threadList = await getThreads();
      let nextSessions = threadList.threads;
      let nextActiveSessionId =
        activeSessionId === sessionId ? nextSessions[0]?.id ?? null : activeSessionId;
      let nextDetail: PublicThreadDetail | null = null;

      if (!nextSessions.length) {
        nextDetail = await createThread();
        nextSessions = [nextDetail.thread];
        nextActiveSessionId = nextDetail.thread.id;
      } else if (nextActiveSessionId && !turnsBySession[nextActiveSessionId]) {
        nextDetail = await getThread(nextActiveSessionId);
        nextSessions = nextSessions.map((session) =>
          session.id === nextDetail!.thread.id ? nextDetail!.thread : session,
        );
      }

      startTransition(() => {
        setActiveSessionId(nextActiveSessionId);
        setTurnsBySession((current) => {
          const nextTurns = { ...current };
          delete nextTurns[sessionId];
          if (nextDetail) {
            nextTurns[nextDetail.thread.id] = nextDetail.turns;
          }
          return nextTurns;
        });
        setSessions(markActiveSession(nextSessions, nextActiveSessionId));
      });
    } catch (error) {
      setRequestError(error, "删除会话失败，请稍后重试。");
      if (!isApiUnavailableError(error)) {
        try {
          await refreshHealthState();
        } catch {
          // Keep the original request error visible.
        }
      }
    } finally {
      setDeletingThreadId(null);
    }
  }

  async function handleClearMessages() {
    const sessionId = activeSessionId;
    if (
      !sessionId ||
      !activeTurns.length ||
      clearingThreadId ||
      isSending ||
      !window.confirm(zhCN.thread.confirmClearMessages)
    ) {
      return;
    }
    setClearingThreadId(sessionId);
    setErrorMessage(null);
    setErrorMeta(null);
    try {
      const detail = await clearThreadMessages(sessionId);
      await refreshHealthState();
      startTransition(() => {
        setTurnsBySession((current) => ({ ...current, [sessionId]: detail.turns }));
        setSessions((current) =>
          markActiveSession(
            current.map((session) => (session.id === sessionId ? detail.thread : session)),
            sessionId,
          ),
        );
      });
    } catch (error) {
      setRequestError(error, "清空会话记录失败，请稍后重试。");
      if (!isApiUnavailableError(error)) {
        try {
          await refreshHealthState();
        } catch {
          // Keep the original request error visible.
        }
      }
    } finally {
      setClearingThreadId(null);
    }
  }

  return (
    <BrowserRouter>
      <WorkspaceFrame
        sessions={sessions}
        activeSessionId={activeSessionId}
        activeTurns={activeTurns}
        onSelectSession={handleSelectSession}
        onCreateThread={handleCreateThread}
        onDeleteThread={handleDeleteThread}
        onSendMessage={handleSendMessage}
        onClearMessages={handleClearMessages}
        isLoading={isLoading}
        isSending={isSending}
        deletingThreadId={deletingThreadId}
        clearingThreadId={clearingThreadId}
        unavailable={unavailable}
        degraded={degraded}
        errorMessage={errorMessage}
        errorMeta={errorMeta}
        health={health}
      />
    </BrowserRouter>
  );
}
