import type { WorkflowModel } from "../../types/workflow";
import { SourceBadge } from "../chat/SourceBadge";

interface WorkflowFinalViewProps {
  workflow: WorkflowModel;
}

export function WorkflowFinalView({ workflow }: WorkflowFinalViewProps) {
  const provenance = workflow.provenance;

  return (
    <div className="workflow-final">
      <div className="workflow-final__summary">
        <span className="workflow-final__label">Final source</span>
        <SourceBadge source={workflow.finalSource} />
      </div>

      <p>{provenance?.summary ?? workflow.provenanceNote}</p>

      <div className="workflow-pill-row">
        {workflow.completedSteps.map((stepId) => (
          <span className="workflow-pill workflow-pill--done" key={stepId}>
            {stepId} complete
          </span>
        ))}
      </div>
    </div>
  );
}
