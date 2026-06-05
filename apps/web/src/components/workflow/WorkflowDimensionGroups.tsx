import { agentNameLabel, dimensionStatusLabel, zhCN } from "../../content/zh-CN";
import type { WorkflowModel } from "../../types/workflow";

interface WorkflowDimensionGroupsProps {
  workflow: WorkflowModel;
}

export function WorkflowDimensionGroups({ workflow }: WorkflowDimensionGroupsProps) {
  if (!workflow.dimensionGroups.length) {
    return <p className="workflow-empty">{zhCN.workflow.emptyDimensions}</p>;
  }

  return (
    <div className="workflow-dimension-grid" aria-label={zhCN.workflow.sections.dimensions}>
      {workflow.dimensionGroups.map((group) => (
        <article className="workflow-dimension-card" key={group.id}>
          <div className="workflow-dimension-card__head">
            <strong>{group.title}</strong>
            <span className={`workflow-status workflow-status--${group.status}`}>{dimensionStatusLabel(group.status)}</span>
          </div>
          <p>{group.summary}</p>
          <div className="workflow-chip-row">
            {group.stepIds.map((stepId) => {
              const step = workflow.dagSteps.find((candidate) => candidate.id === stepId);
              return (
                <span className="workflow-chip" key={stepId}>
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
