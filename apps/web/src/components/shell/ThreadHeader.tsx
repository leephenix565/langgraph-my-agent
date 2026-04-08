import { zhCN } from "../../content/zh-CN";
import type { ChatSessionSummary, HealthResponse } from "../../types/chat";

interface ThreadHeaderProps {
  session: ChatSessionSummary | null;
  health: HealthResponse | null;
}

export function ThreadHeader({ session, health }: ThreadHeaderProps) {
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
      </div>
    </header>
  );
}
