import { zhCN } from "../../content/zh-CN";
import type { ChatSessionSummary, HealthResponse } from "../../types/chat";

interface ThreadHeaderProps {
  session: ChatSessionSummary | null;
  health: HealthResponse | null;
  hasMessages: boolean;
  onClearMessages: () => void;
  clearDisabled?: boolean;
  isClearing?: boolean;
}

export function ThreadHeader({
  session,
  health,
  hasMessages,
  onClearMessages,
  clearDisabled = false,
  isClearing = false,
}: ThreadHeaderProps) {
  const degraded = health?.overallStatus === "degraded";

  return (
    <header className="thread-header">
      <div className="thread-header__row">
        <span className="thread-header__menu" aria-hidden="true">
          ≡
        </span>
        <div className="thread-header__title-group">
          <h1>{session?.title ?? zhCN.thread.fallbackTitle}</h1>
          {degraded ? <span className="thread-header__note">{zhCN.thread.degradedMeta}</span> : null}
        </div>
        {session?.updatedAt ? (
          <span className="thread-header__timestamp">
            {zhCN.thread.updatedAt} · {session.updatedAt}
          </span>
        ) : null}
        <button
          className="thread-header__action"
          type="button"
          onClick={onClearMessages}
          disabled={!session || !hasMessages || clearDisabled || isClearing}
        >
          {isClearing ? zhCN.thread.clearingMessages : zhCN.thread.clearMessages}
        </button>
      </div>
    </header>
  );
}
