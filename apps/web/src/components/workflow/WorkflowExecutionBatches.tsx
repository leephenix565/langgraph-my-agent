import { agentNameLabel, zhCN } from "../../content/zh-CN";
import type { WorkflowModel } from "../../types/workflow";

interface WorkflowExecutionBatchesProps {
  workflow: WorkflowModel;
}

export function WorkflowExecutionBatches({ workflow }: WorkflowExecutionBatchesProps) {
  if (!workflow.executionBatches.length) {
    return <p className="workflow-empty">{zhCN.workflow.emptyBatches}</p>;
  }

  return (
    <div className="workflow-batch-list" aria-label={zhCN.workflow.sections.batches}>
      {workflow.executionBatches.map((batch, index) => (
        <article className="workflow-batch" key={`${index}-${batch.join("-")}`}>
          <div className="workflow-batch__head">
            <strong>
              {zhCN.workflow.batchLabel} {index + 1}
            </strong>
            <span className="workflow-status workflow-status--queued">
              {batch.length} {zhCN.workflow.units.steps}
            </span>
          </div>
          <div className="workflow-chip-row">
            {batch.map((stepId) => {
              const step = workflow.dagSteps.find((candidate) => candidate.id === stepId);
              return (
                <span className="workflow-chip workflow-chip--strong" key={stepId}>
                  {agentNameLabel(step?.agentId ?? stepId, step?.title)}
                </span>
              );
            })}
          </div>
        </article>
      ))}
    </div>
  );
}
