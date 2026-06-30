import { continuityLabel, executionStatusLabel, zhCN } from "../../content/zh-CN";
import type { WorkflowModel } from "../../types/workflow";
import { SourceBadge } from "../chat/SourceBadge";

interface WorkflowProvenanceViewProps {
  workflow: WorkflowModel;
}

function boolLabel(value: boolean | undefined) {
  return value ? zhCN.workflow.boolean.yes : zhCN.workflow.boolean.no;
}

function renderTechnicalValue(label: string, raw: string) {
  return (
    <span className="workflow-technical-value">
      <span>{label}</span>
      <code>{raw}</code>
    </span>
  );
}

function listLabel(values: string[] | undefined) {
  return values?.length ? values.join(", ") : "-";
}

export function WorkflowProvenanceView({ workflow }: WorkflowProvenanceViewProps) {
  const provenance = workflow.provenance;

  return (
    <article className="workflow-provenance" aria-label={zhCN.workflow.sections.provenance}>
      <div className="workflow-provenance__head">
        <strong>{zhCN.workflow.sections.provenance}</strong>
        <SourceBadge source={workflow.finalSource} />
      </div>
      <p>{provenance?.summary ?? workflow.provenanceNote}</p>
      <dl className="workflow-metadata-grid">
        <div>
          <dt>{zhCN.workflow.provenance.planId}</dt>
          <dd>{workflow.planId}</dd>
        </div>
        <div>
          <dt>{zhCN.workflow.provenance.continuity}</dt>
          <dd>{continuityLabel(provenance?.continuityMode ?? "replay")}</dd>
        </div>
        <div>
          <dt>{zhCN.workflow.provenance.providerInvoked}</dt>
          <dd>{boolLabel(provenance?.providerInvoked)}</dd>
        </div>
        <div>
          <dt>{zhCN.workflow.provenance.externalInvoked}</dt>
          <dd>{boolLabel(provenance?.externalInvoked)}</dd>
        </div>
        <div>
          <dt>{zhCN.workflow.provenance.fallbackUsed}</dt>
          <dd>{boolLabel(provenance?.fallbackUsed)}</dd>
        </div>
        {provenance?.executionStatus ? (
          <div>
            <dt>{zhCN.workflow.provenance.executionStatus}</dt>
            <dd>{renderTechnicalValue(executionStatusLabel(provenance.executionStatus), provenance.executionStatus)}</dd>
          </div>
        ) : null}
        {provenance ? (
          <>
            <div>
              <dt>{zhCN.workflow.provenance.selectedRoutingRequested}</dt>
              <dd>{boolLabel(provenance.selectedRoutingRequested)}</dd>
            </div>
            <div>
              <dt>{zhCN.workflow.provenance.selectedRoutingFallback}</dt>
              <dd>{boolLabel(provenance.selectedRoutingFallback)}</dd>
            </div>
            {provenance.routeGranularity ? (
              <div>
                <dt>{zhCN.workflow.provenance.routeGranularity}</dt>
                <dd>{renderTechnicalValue(provenance.routeGranularity, provenance.routeGranularity)}</dd>
              </div>
            ) : null}
            <div>
              <dt>{zhCN.workflow.provenance.selectedDimensions}</dt>
              <dd>{listLabel(provenance.selectedDimensions)}</dd>
            </div>
            {typeof provenance.expandedAgentCount === "number" ? (
              <div>
                <dt>{zhCN.workflow.provenance.expandedAgentCount}</dt>
                <dd>{provenance.expandedAgentCount}</dd>
              </div>
            ) : null}
            <div>
              <dt>{zhCN.workflow.provenance.providerRouterEnabled}</dt>
              <dd>{boolLabel(provenance.providerRouterEnabled)}</dd>
            </div>
            <div>
              <dt>{zhCN.workflow.provenance.providerRouterInvoked}</dt>
              <dd>{boolLabel(provenance.providerRouterInvoked)}</dd>
            </div>
            {provenance.providerRouterMode ? (
              <div>
                <dt>{zhCN.workflow.provenance.providerRouterMode}</dt>
                <dd>{renderTechnicalValue(provenance.providerRouterMode, provenance.providerRouterMode)}</dd>
              </div>
            ) : null}
            <div>
              <dt>{zhCN.workflow.provenance.providerRouterParseOk}</dt>
              <dd>{boolLabel(provenance.providerRouterParseOk)}</dd>
            </div>
          </>
        ) : null}
      </dl>
      {provenance?.fallbackReason || provenance?.providerRouterFallbackReason || provenance?.providerRouterErrorCode ? (
        <div className="workflow-warning-list">
          <strong>{zhCN.workflow.provenance.rawDetails}</strong>
          <ul>
            {provenance.fallbackReason ? (
              <li>{renderTechnicalValue(zhCN.workflow.provenance.fallbackReason, provenance.fallbackReason)}</li>
            ) : null}
            {provenance.providerRouterFallbackReason ? (
              <li>
                {renderTechnicalValue(
                  zhCN.workflow.provenance.providerRouterFallbackReason,
                  provenance.providerRouterFallbackReason,
                )}
              </li>
            ) : null}
            {provenance.providerRouterErrorCode ? (
              <li>{renderTechnicalValue(zhCN.workflow.provenance.providerRouterErrorCode, provenance.providerRouterErrorCode)}</li>
            ) : null}
            {provenance.providerRouterSelectedDimensions.length ? (
              <li>
                {renderTechnicalValue(
                  zhCN.workflow.provenance.providerRouterSelectedDimensions,
                  listLabel(provenance.providerRouterSelectedDimensions),
                )}
              </li>
            ) : null}
          </ul>
        </div>
      ) : null}
      {provenance?.limitations?.length ? (
        <div className="workflow-warning-list">
          <strong>{zhCN.workflow.provenance.limitations}</strong>
          <ul>
            {provenance.limitations.map((limitation) => (
              <li key={limitation}>{limitation}</li>
            ))}
          </ul>
        </div>
      ) : null}
    </article>
  );
}
