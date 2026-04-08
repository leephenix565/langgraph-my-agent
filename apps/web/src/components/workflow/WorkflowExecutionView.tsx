import { agentNameLabel, agentStepStatusLabel, workflowModeLabel } from "../../content/zh-CN";
import type { WorkflowModel } from "../../types/workflow";

interface WorkflowExecutionViewProps {
  workflow: WorkflowModel;
}

const layerOrder = ["L1", "L2", "L3", "L4"] as const;

export function WorkflowExecutionView({ workflow }: WorkflowExecutionViewProps) {
  return (
    <div className="workflow-execution">
      {layerOrder.map((layer) => {
        const steps = workflow.agentSteps.filter((step) => step.layer === layer);
        if (steps.length === 0) {
          return null;
        }

        return (
          <div className="workflow-execution__layer" key={layer}>
            <div className="workflow-execution__header">
              <h5>{layer}</h5>
              <span>{workflowModeLabel(workflow.layerMode[layer])}</span>
            </div>
            <div className="workflow-step-list">
              {steps.map((step) => (
                <article className="workflow-step" key={step.id}>
                  <div className="workflow-step__meta">
                    <span>{agentNameLabel(step.agentId, step.title)}</span>
                    <span className={`workflow-status workflow-status--${step.status}`}>{agentStepStatusLabel(step.status)}</span>
                  </div>
                  <p>{step.summary}</p>
                  {step.signal ? <small>{step.signal}</small> : null}
                </article>
              ))}
            </div>
          </div>
        );
      })}
    </div>
  );
}
