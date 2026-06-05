import { continuityLabel, executionStatusLabel, zhCN } from "../../content/zh-CN";
import type { WorkflowModel } from "../../types/workflow";
import { SourceBadge } from "../chat/SourceBadge";

interface WorkflowProvenanceViewProps {
  workflow: WorkflowModel;
}

function boolLabel(value: boolean | undefined) {
  return value ? zhCN.workflow.boolean.yes : zhCN.workflow.boolean.no;
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
            <dd>{executionStatusLabel(provenance.executionStatus)}</dd>
          </div>
        ) : null}
      </dl>
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
