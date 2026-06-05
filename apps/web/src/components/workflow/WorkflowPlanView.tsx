import type { WorkflowModel } from "../../types/workflow";

interface WorkflowPlanViewProps {
  workflow: WorkflowModel;
}

export function WorkflowPlanView({ workflow }: WorkflowPlanViewProps) {
  return (
    <div className="workflow-plan">
      {workflow.stages.map((stage) => (
        <div className="workflow-plan__row" key={stage.key}>
          <div className="workflow-plan__layer">
            <span className="workflow-plan__layer-id">{stage.key}</span>
            <span className="workflow-plan__mode">{stage.stepIds.length} steps</span>
          </div>
          <div className="workflow-plan__content">
            <strong>{stage.title}</strong>
            {stage.stepIds.length ? <p>{stage.stepIds.join(", ")}</p> : <p>No bound DAG steps yet.</p>}
          </div>
        </div>
      ))}
    </div>
  );
}
