import { agentNameLabel, workflowModeLabel } from "../../content/zh-CN";
import type { WorkflowModel } from "../../types/workflow";

interface WorkflowPlanViewProps {
  workflow: WorkflowModel;
}

export function WorkflowPlanView({ workflow }: WorkflowPlanViewProps) {
  return (
    <div className="workflow-plan">
      {workflow.layerPlan.map((item) => (
        <div className="workflow-plan__row" key={item.layer}>
          <div className="workflow-plan__layer">
            <span className="workflow-plan__layer-id">{item.layer}</span>
            <span className="workflow-plan__mode">{workflowModeLabel(item.mode)}</span>
          </div>
          <div className="workflow-plan__content">
            <div className="workflow-pill-row">
              {item.selected.map((agentId) => (
                <span className="workflow-pill" key={agentId}>
                  {agentNameLabel(agentId)}
                </span>
              ))}
            </div>
            {item.note ? <p>{item.note}</p> : null}
          </div>
        </div>
      ))}
    </div>
  );
}
