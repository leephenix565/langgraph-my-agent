import { NavLink, useNavigate } from "react-router-dom";
import { appConfig } from "../../config/appConfig";
import { connectionStateLabel, zhCN } from "../../content/zh-CN";
import type { ChatSessionSummary } from "../../types/chat";

interface SidebarProps {
  sessions: ChatSessionSummary[];
  activeSessionId: string;
  onSelectSession: (sessionId: string) => void;
  onCreateThread: () => void;
  createDisabled?: boolean;
  connectionState: "loading" | "live" | "degraded" | "unavailable";
}

export function Sidebar({
  sessions,
  activeSessionId,
  onSelectSession,
  onCreateThread,
  createDisabled = false,
  connectionState,
}: SidebarProps) {
  const navigate = useNavigate();

  function handleSessionSelect(sessionId: string) {
    onSelectSession(sessionId);
    navigate("/");
  }

  function handleCreateThread() {
    onCreateThread();
    navigate("/");
  }

  return (
    <aside className="sidebar">
      <NavLink className="sidebar__brand" to="/">
        <span className="sidebar__brand-mark" aria-hidden="true">
          资
        </span>
        <div className="sidebar__brand-copy">
          <h2 className="sidebar__brand-title">
            {appConfig.brandLines.map((line) => (
              <span className="sidebar__brand-line" key={line}>
                {line}
              </span>
            ))}
          </h2>
          <p>{appConfig.description}</p>
        </div>
      </NavLink>

      <button className="sidebar__primary-action" type="button" onClick={handleCreateThread} disabled={createDisabled}>
        {zhCN.sidebar.primaryAction}
      </button>

      <section className="sidebar__sessions" aria-label={zhCN.sidebar.history}>
        <div className="sidebar__section-header">
          <span>{zhCN.sidebar.history}</span>
        </div>
        <div className="sidebar__session-list">
          {sessions.length === 0 ? <div className="sidebar__empty">{zhCN.sidebar.empty}</div> : null}
          {sessions.map((session) => (
            <button
              key={session.id}
              type="button"
              className={`sidebar__session${session.id === activeSessionId ? " is-active" : ""}`}
              onClick={() => handleSessionSelect(session.id)}
            >
              <span className="sidebar__session-marker" aria-hidden="true" />
              <div className="sidebar__session-copy">
                <strong>{session.title}</strong>
                <small>{session.updatedAt}</small>
              </div>
            </button>
          ))}
        </div>
      </section>

      <div className="sidebar__footer">
        <nav className="sidebar__secondary-nav" aria-label="次级导航">
          <NavLink className={({ isActive }) => `sidebar__secondary-link${isActive ? " is-active" : ""}`} to="/agents">
            {zhCN.sidebar.navAgents}
          </NavLink>
          <NavLink className={({ isActive }) => `sidebar__secondary-link${isActive ? " is-active" : ""}`} to="/settings">
            {zhCN.sidebar.navSettings}
          </NavLink>
        </nav>

        <div className="sidebar__status" aria-label={zhCN.sidebar.serviceStatus}>
          <span className={`sidebar__status-dot sidebar__status-dot--${connectionState}`} aria-hidden="true" />
          <div>
            <strong>{zhCN.sidebar.serviceStatus}</strong>
            <span>{connectionStateLabel(connectionState)}</span>
          </div>
        </div>
      </div>
    </aside>
  );
}
