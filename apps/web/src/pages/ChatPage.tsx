import type { ApiError } from "../services/api";
import { Composer } from "../components/shell/Composer";
import { MessageList } from "../components/shell/MessageList";
import { ThreadHeader } from "../components/shell/ThreadHeader";
import { degradedSignalLabels, errorCategoryLabel, zhCN } from "../content/zh-CN";
import type { ChatSessionSummary, HealthResponse, PublicTurn, StructuredInputModel } from "../types/chat";

interface ChatPageProps {
  session: ChatSessionSummary | null;
  turns: PublicTurn[];
  onSendMessage: (value: string, structuredInput?: StructuredInputModel) => void;
  onClearMessages: () => void;
  isLoading: boolean;
  isSending: boolean;
  isClearing: boolean;
  unavailable: boolean;
  degraded: boolean;
  errorMessage: string | null;
  errorMeta: ApiError | null;
  health: HealthResponse | null;
}

function renderErrorMeta(errorMeta: ApiError | null) {
  const meta = [errorMeta?.category ? errorCategoryLabel(errorMeta.category) : null, errorMeta?.code ?? null].filter(Boolean);
  if (!meta.length) {
    return null;
  }
  return <small className="thread-notice__meta">{meta.join(" · ")}</small>;
}

export function ChatPage({
  session,
  turns,
  onSendMessage,
  onClearMessages,
  isLoading,
  isSending,
  isClearing,
  unavailable,
  degraded,
  errorMessage,
  errorMeta,
  health,
}: ChatPageProps) {
  const degradedSignals = degradedSignalLabels(health);

  return (
    <div className="page page--chat">
      <ThreadHeader
        session={session}
        health={health}
        hasMessages={turns.length > 0}
        onClearMessages={onClearMessages}
        clearDisabled={unavailable || isLoading || isSending}
        isClearing={isClearing}
      />

      {unavailable ? (
        <section className="thread-notice thread-notice--unavailable" aria-label="服务不可用提示">
          <strong>{zhCN.states.unavailableTitle}</strong>
          <p>{zhCN.states.unavailableBody}</p>
        </section>
      ) : null}

      {!unavailable && degraded ? (
        <section className="thread-notice thread-notice--degraded" aria-label="服务降级提示">
          <strong>{zhCN.states.degradedTitle}</strong>
          <p>{zhCN.states.degradedBody}</p>
          {degradedSignals.length ? (
            <div className="thread-notice__signals">
              {degradedSignals.map((signal) => (
                <span className="workflow-pill" key={signal}>
                  {signal}
                </span>
              ))}
            </div>
          ) : null}
        </section>
      ) : null}

      {!unavailable && errorMessage ? (
        <section className="thread-notice thread-notice--error" aria-label="请求失败提示">
          <strong>{zhCN.states.errorTitle}</strong>
          <p>{errorMessage || zhCN.states.errorBody}</p>
          {renderErrorMeta(errorMeta)}
        </section>
      ) : null}

      {isLoading ? (
        <section className="thread-notice" aria-label="正在同步会话">
          <strong>{zhCN.states.loadingTitle}</strong>
          <p>{zhCN.states.loadingBody}</p>
        </section>
      ) : null}

      <MessageList turns={turns} />

      {!turns.length && !isLoading && !unavailable ? (
        <section className="thread-empty" aria-label="空会话状态">
          <strong>{zhCN.states.emptyTitle}</strong>
          <p>{zhCN.states.emptyBody}</p>
        </section>
      ) : null}

      <Composer
        onSubmit={onSendMessage}
        disabled={!session || unavailable || isLoading}
        busy={isSending}
        unavailable={unavailable}
      />
    </div>
  );
}
