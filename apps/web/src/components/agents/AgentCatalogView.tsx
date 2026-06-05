import { agentDescriptionLabel, agentNameLabel, capabilityLabel, teamLabel, zhCN } from "../../content/zh-CN";
import type { AgentCatalogModel, AgentLayerGroup } from "../../types/agents";

interface AgentCatalogViewProps {
  catalog: AgentCatalogModel;
  query: string;
}

function layerCopy(layer: AgentLayerGroup["layer"]) {
  return zhCN.agents.layers[layer];
}

function roleTypeLabel(roleType?: string) {
  if (!roleType) {
    return zhCN.agents.roleUnknown;
  }
  return (zhCN.agents.roleTypes as Record<string, string | undefined>)[roleType] ?? roleType;
}

const implementationCapabilityTokens = new Set(["deterministic_skeleton", "pending_implementation", "external_candidate_disabled"]);

function renderCapabilities(capabilities: string[]) {
  const visibleCapabilities = capabilities.filter((capability) => !implementationCapabilityTokens.has(capability));
  if (!visibleCapabilities.length) {
    return null;
  }
  return (
    <div className="agent-row__capabilities" aria-label={zhCN.agents.capabilitiesLabel}>
      {visibleCapabilities.map((capability) => (
        <span className="workflow-pill" key={capability}>
          {capabilityLabel(capability)}
        </span>
      ))}
    </div>
  );
}

export function AgentCatalogView({ catalog, query }: AgentCatalogViewProps) {
  const normalizedQuery = query.trim().toLowerCase();
  const layerStats = catalog.layers.map((layer) => {
    const copy = layerCopy(layer.layer);
    return {
      id: layer.layer,
      title: copy.title.replace(/^L\d\s*/, ""),
      count: layer.agents.length,
    };
  });
  const dimensionStats = ["value", "market", "risk", "macro"].map((dimension) => ({
    id: dimension,
    title: teamLabel(dimension),
    count: catalog.layers.flatMap((layer) => layer.agents).filter((agent) => agent.team === dimension).length,
  }));
  const layers = catalog.layers
    .map((layer) => ({
      ...layer,
      agents: layer.agents.filter((agent) => {
        if (!normalizedQuery) {
          return true;
        }

        return (
          agent.id.toLowerCase().includes(normalizedQuery) ||
          agent.name.toLowerCase().includes(normalizedQuery) ||
          agentNameLabel(agent.id, agent.name).toLowerCase().includes(normalizedQuery) ||
          agent.team.toLowerCase().includes(normalizedQuery) ||
          agent.description.toLowerCase().includes(normalizedQuery) ||
          agentDescriptionLabel(agent.id, agent.description).toLowerCase().includes(normalizedQuery) ||
          agent.capabilities.some(
            (capability) =>
              capability.toLowerCase().includes(normalizedQuery) ||
              capabilityLabel(capability).toLowerCase().includes(normalizedQuery),
          )
        );
      }),
    }))
    .filter((layer) => layer.agents.length > 0);

  return (
    <div className="agent-catalog">
      <section className="agent-catalog__stats" aria-label={zhCN.agents.statsLabel}>
        {layerStats.map((item) => (
          <div key={item.id}>
            <span>{item.title}</span>
            <strong>{item.count}</strong>
          </div>
        ))}
      </section>

      <section className="agent-catalog__dimensions" aria-label="维度能力">
        {dimensionStats.map((item) => (
          <div key={item.id}>
            <span>{item.title}维</span>
            <strong>{item.count}</strong>
          </div>
        ))}
      </section>

      <details className="agent-catalog__details" open={Boolean(normalizedQuery)}>
        <summary>{zhCN.agents.detailsSummary}</summary>

        {catalog.disabledAgents.length ? (
          <section className="agent-catalog__disabled">
            <div className="agent-catalog__section-head">
              <h3>{zhCN.agents.reservedTitle}</h3>
              <p>{zhCN.agents.reservedDescription}</p>
            </div>
            {catalog.disabledAgents.map((agent) => (
              <div className="agent-row agent-row--disabled" key={agent.id}>
                <div className="agent-row__title">
                  <strong>{agentNameLabel(agent.id, agent.name)}</strong>
                  <span>{agent.id}</span>
                </div>
                <p>{agentDescriptionLabel(agent.id, agent.description)}</p>
                {renderCapabilities(agent.capabilities)}
                <div className="agent-row__meta">
                  <span>{teamLabel(agent.team)}</span>
                  <span>{roleTypeLabel(agent.roleType)}</span>
                  <span>{zhCN.agents.disabledState}</span>
                </div>
              </div>
            ))}
          </section>
        ) : null}

        <div className="agent-layer-list">
          {layers.map((layer) => {
            const copy = layerCopy(layer.layer);
            return (
              <section className="agent-layer" key={layer.layer}>
                <header className="agent-layer__header">
                  <div>
                    <span className="agent-layer__eyebrow">{layer.layer}</span>
                    <h3>{copy.title}</h3>
                  </div>
                  <p>{copy.description}</p>
                </header>
                <div className="agent-layer__rows">
                  {layer.agents.map((agent) => (
                    <article className="agent-row" key={agent.id}>
                      <div className="agent-row__title">
                        <strong>{agentNameLabel(agent.id, agent.name)}</strong>
                        <span>{agent.id}</span>
                      </div>
                      <p>{agentDescriptionLabel(agent.id, agent.description)}</p>
                      {renderCapabilities(agent.capabilities)}
                      <div className="agent-row__meta">
                        <span>{teamLabel(agent.team)}</span>
                        <span>{roleTypeLabel(agent.roleType)}</span>
                        <span>{agent.defaultEnabled ? zhCN.agents.enabled : zhCN.agents.disabledState}</span>
                      </div>
                    </article>
                  ))}
                </div>
              </section>
            );
          })}
        </div>
      </details>
    </div>
  );
}
