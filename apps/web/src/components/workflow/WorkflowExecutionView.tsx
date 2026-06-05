import { agentNameLabel, dagStepStatusLabel } from "../../content/zh-CN";
import type { DagStep, WorkflowModel, WorkflowStageKey } from "../../types/workflow";

interface WorkflowExecutionViewProps {
  workflow: WorkflowModel;
}

const stageOrder: WorkflowStageKey[] = [
  "planning",
  "evidence",
  "l2_analysis",
  "dimension_composite",
  "decision",
  "report",
];

function sortByStage(left: DagStep, right: DagStep) {
  return stageOrder.indexOf(left.stage) - stageOrder.indexOf(right.stage);
}

export function WorkflowExecutionView({ workflow }: WorkflowExecutionViewProps) {
  const steps = [...workflow.dagSteps].sort(sortByStage);

  if (!steps.length) {
    return <p className="workflow-empty">DAG steps are not available yet.</p>;
  }

  return (
    <div className="workflow-execution">
      {steps.map((step) => (
        <article className="workflow-step" key={step.id}>
          <div className="workflow-step__meta">
            <span>{agentNameLabel(step.agentId ?? step.id, step.title)}</span>
            <span className={`workflow-status workflow-status--${step.status}`}>{dagStepStatusLabel(step.status)}</span>
          </div>
          <p>{step.summary}</p>
          <small>
            {step.stage}
            {step.dimension ? ` / ${step.dimension}` : ""}
          </small>
        </article>
      ))}
    </div>
  );
}
