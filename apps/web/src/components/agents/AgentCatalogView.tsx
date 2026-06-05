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

function renderCapabilities(capabilities: string[]) {
  if (!capabilities.length) {
    return null;
  }
  return (
    <div className="agent-row__capabilities" aria-label={zhCN.agents.capabilitiesLabel}>
      {capabilities.map((capability) => (
        <span className="workflow-pill" key={capability}>
          {capabilityLabel(capability)}
        </span>
      ))}
    </div>
  );
}

export function AgentCatalogView({ catalog, query }: AgentCatalogViewProps) {
  const normalizedQuery = query.trim().toLowerCase();
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
        <div>
          <span>{zhCN.agents.totals.config}</span>
          <strong>{catalog.totals.configCount}</strong>
        </div>
        <div>
          <span>{zhCN.agents.totals.runtime}</span>
          <strong>{catalog.totals.runtimeCount}</strong>
        </div>
        <div>
          <span>{zhCN.agents.totals.disabled}</span>
          <strong>{catalog.totals.disabledIds.length ? catalog.totals.disabledIds.join(", ") : zhCN.agents.none}</strong>
        </div>
      </section>

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
    </div>
  );
}
