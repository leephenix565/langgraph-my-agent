import { fusionKindLabel, fusionStatusLabel } from "../../content/zh-CN";
import type { WorkflowModel } from "../../types/workflow";

interface WorkflowFusionViewProps {
  workflow: WorkflowModel;
}

export function WorkflowFusionView({ workflow }: WorkflowFusionViewProps) {
  return (
    <div className="workflow-fusion">
      {workflow.fusionSteps.map((step) => (
        <article className="workflow-sidecar" key={step.id}>
          <div className="workflow-sidecar__meta">
            <span>{fusionKindLabel(step.kind)}</span>
            <span className={`workflow-status workflow-status--${step.status}`}>{fusionStatusLabel(step.status)}</span>
          </div>
          <p>{step.summary}</p>
        </article>
      ))}
    </div>
  );
}
