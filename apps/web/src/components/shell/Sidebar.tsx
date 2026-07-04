import { NavLink, useNavigate } from "react-router-dom";
import { appConfig } from "../../config/appConfig";
import { connectionStateLabel, zhCN } from "../../content/zh-CN";
import type { ChatSessionSummary } from "../../types/chat";

interface SidebarProps {
  sessions: ChatSessionSummary[];
  activeSessionId: string;
  onSelectSession: (sessionId: string) => void;
  onCreateThread: () => void;
  onDeleteThread: (sessionId: string) => void;
  createDisabled?: boolean;
  deleteDisabled?: boolean;
  deletingThreadId?: string | null;
  connectionState: "loading" | "live" | "degraded" | "unavailable";
  isOpen: boolean;
  onToggle: () => void;
  onClose: () => void;
}

export function Sidebar({
  sessions,
  activeSessionId,
  onSelectSession,
  onCreateThread,
  onDeleteThread,
  createDisabled = false,
  deleteDisabled = false,
  deletingThreadId = null,
  connectionState,
  isOpen,
  onToggle,
  onClose,
}: SidebarProps) {
  const navigate = useNavigate();

  function handleSessionSelect(sessionId: string) {
    onSelectSession(sessionId);
    navigate("/");
    onClose();
  }

  function handleCreateThread() {
    onCreateThread();
    navigate("/");
    onClose();
  }

  return (
    <>
      <button className="sidebar-hamburger" type="button" onClick={onToggle} aria-label="打开导航菜单">
        ≡
      </button>
      <aside className={`sidebar${isOpen ? " sidebar--open" : ""}`}>
        <button className="sidebar__close" type="button" onClick={onClose} aria-label="关闭导航菜单">
          🗙
        </button>
        <NavLink className="sidebar__brand" to="/" onClick={onClose}>
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
              <div
                key={session.id}
                className={`sidebar__session-row${session.id === activeSessionId ? " is-active" : ""}`}
              >
                <button
                  type="button"
                  className="sidebar__session"
                  onClick={() => handleSessionSelect(session.id)}
                >
                  <span className="sidebar__session-marker" aria-hidden="true" />
                  <div className="sidebar__session-copy">
                    <strong>{session.title}</strong>
                    {session.preview && <span className="sidebar__session-preview">{session.preview.slice(0, 40)}</span>}
                    <small>{session.updatedAt}</small>
                  </div>
                </button>
                <button
                  type="button"
                  className="sidebar__session-delete"
                  onClick={() => onDeleteThread(session.id)}
                  disabled={deleteDisabled || deletingThreadId === session.id}
                  aria-label={`${zhCN.sidebar.deleteThread}: ${session.title}`}
                  title={zhCN.sidebar.deleteThread}
                >
                  {deletingThreadId === session.id ? "…" : "—"}
                </button>
              </div>
            ))}
          </div>
        </section>

        <div className="sidebar__footer">
          <nav className="sidebar__secondary-nav" aria-label="次级导航">
            <NavLink className={({ isActive }) => `sidebar__secondary-link${isActive ? " is-active" : ""}`} to="/agents" onClick={onClose}>
              {zhCN.sidebar.navAgents}
            </NavLink>
            <NavLink className={({ isActive }) => `sidebar__secondary-link${isActive ? " is-active" : ""}`} to="/settings" onClick={onClose}>
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
    </>
  );
}
