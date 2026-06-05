import { dimensionStatusLabel } from "../../content/zh-CN";
import type { WorkflowModel } from "../../types/workflow";

interface WorkflowFusionViewProps {
  workflow: WorkflowModel;
}

export function WorkflowFusionView({ workflow }: WorkflowFusionViewProps) {
  return (
    <div className="workflow-fusion">
      {workflow.dimensionGroups.map((group) => (
        <article className="workflow-sidecar" key={group.id}>
          <div className="workflow-sidecar__meta">
            <span>{group.title}</span>
            <span className={`workflow-status workflow-status--${group.status}`}>{dimensionStatusLabel(group.status)}</span>
          </div>
          <p>{group.summary}</p>
          <small>{group.stepIds.join(", ")}</small>
        </article>
      ))}
      {workflow.executionBatches.length ? (
        <article className="workflow-sidecar">
          <div className="workflow-sidecar__meta">
            <span>Execution batches</span>
            <span className="workflow-status workflow-status--complete">{workflow.executionBatches.length}</span>
          </div>
          {workflow.executionBatches.map((batch, index) => (
            <p key={`${index}-${batch.join("-")}`}>
              Batch {index + 1}: {batch.join(", ")}
            </p>
          ))}
        </article>
      ) : null}
    </div>
  );
}
