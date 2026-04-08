import { useDeferredValue, useEffect, useState } from "react";
import { AgentCatalogView } from "../components/agents/AgentCatalogView";
import { zhCN } from "../content/zh-CN";
import { ApiError, getApiErrorMessage, isApiUnavailableError } from "../services/api";
import { getAgentCatalog } from "../services/chat";
import type { AgentCatalogModel } from "../types/agents";

export function AgentsPage() {
  const [query, setQuery] = useState("");
  const [catalog, setCatalog] = useState<AgentCatalogModel | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<ApiError | null>(null);
  const deferredQuery = useDeferredValue(query);
  const unavailableError = !!error && isApiUnavailableError(error);
  const errorMessage = error?.message || zhCN.agents.errorBody;

  useEffect(() => {
    let cancelled = false;

    void (async () => {
      setIsLoading(true);
      setError(null);
      try {
        const nextCatalog = await getAgentCatalog();
        if (!cancelled) {
          setCatalog(nextCatalog);
        }
      } catch (caught) {
        if (!cancelled) {
          setError(caught instanceof ApiError ? caught : new ApiError(getApiErrorMessage(caught)));
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    })();

    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="page page--agents">
      <header className="agents-header">
        <div className="agents-header__copy">
          <span className="agents-header__eyebrow">{zhCN.agents.eyebrow}</span>
          <h1>{zhCN.agents.title}</h1>
          <p>{zhCN.agents.description}</p>
        </div>
        <label className="agents-search" htmlFor="agent-search">
          <span>{zhCN.agents.searchLabel}</span>
          <input
            id="agent-search"
            type="search"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder={zhCN.agents.searchPlaceholder}
            disabled={!catalog}
          />
        </label>
      </header>

      {isLoading ? (
        <section className="thread-notice" aria-label={zhCN.agents.loadingTitle}>
          <strong>{zhCN.agents.loadingTitle}</strong>
          <p>{zhCN.agents.loadingBody}</p>
        </section>
      ) : null}

      {!isLoading && unavailableError ? (
        <section className="thread-notice thread-notice--unavailable" aria-label={zhCN.agents.unavailableTitle}>
          <strong>{zhCN.agents.unavailableTitle}</strong>
          <p>{zhCN.agents.unavailableBody}</p>
        </section>
      ) : null}

      {!isLoading && error && !unavailableError ? (
        <section className="thread-notice thread-notice--error" aria-label={zhCN.agents.errorTitle}>
          <strong>{zhCN.agents.errorTitle}</strong>
          <p>{errorMessage}</p>
        </section>
      ) : null}

      {catalog ? <AgentCatalogView catalog={catalog} query={deferredQuery} /> : null}
    </div>
  );
}
