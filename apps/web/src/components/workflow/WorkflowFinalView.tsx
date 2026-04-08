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
        <span className="workflow-final__label">最终输出</span>
        <SourceBadge source={workflow.finalSource} />
      </div>

      <p>{provenance?.summary ?? workflow.provenanceNote}</p>

      <div className="workflow-pill-row">
        {workflow.layerDone.map((layer) => (
          <span className="workflow-pill workflow-pill--done" key={layer}>
            {layer} 已完成
          </span>
        ))}
      </div>
    </div>
  );
}
