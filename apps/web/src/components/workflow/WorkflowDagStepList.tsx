import { agentNameLabel, dagStepStatusLabel, stageLabel, zhCN } from "../../content/zh-CN";
import type { DagStep, WorkflowModel } from "../../types/workflow";

interface WorkflowDagStepListProps {
  workflow: WorkflowModel;
  selectedStepId: string | null;
  onSelectStep: (stepId: string) => void;
}

function sortByStage(workflow: WorkflowModel) {
  const stageOrder = workflow.stages.map((stage) => stage.key);
  return (left: DagStep, right: DagStep) => {
    const leftIndex = stageOrder.indexOf(left.stage);
    const rightIndex = stageOrder.indexOf(right.stage);
    const stageDiff = (leftIndex === -1 ? Number.MAX_SAFE_INTEGER : leftIndex) - (rightIndex === -1 ? Number.MAX_SAFE_INTEGER : rightIndex);
    return stageDiff === 0 ? left.id.localeCompare(right.id) : stageDiff;
  };
}

export function WorkflowDagStepList({ workflow, selectedStepId, onSelectStep }: WorkflowDagStepListProps) {
  const steps = [...workflow.dagSteps].sort(sortByStage(workflow));

  if (!steps.length) {
    return <p className="workflow-empty">{zhCN.workflow.emptySteps}</p>;
  }

  return (
    <div className="workflow-step-list" aria-label={zhCN.workflow.sections.steps}>
      {steps.map((step) => (
        <button
          type="button"
          className={`workflow-step-card${selectedStepId === step.id ? " workflow-step-card--selected" : ""}`}
          key={step.id}
          aria-pressed={selectedStepId === step.id}
          onClick={() => onSelectStep(step.id)}
        >
          <span className="workflow-step-card__head">
            <strong>{agentNameLabel(step.agentId ?? step.id, step.title)}</strong>
            <span className={`workflow-status workflow-status--${step.status}`}>{dagStepStatusLabel(step.status)}</span>
          </span>
          <span className="workflow-step-card__summary">{step.summary}</span>
          <span className="workflow-chip-row">
            <span className="workflow-chip">{stageLabel(step.stage)}</span>
            {step.dimension ? <span className="workflow-chip">{step.dimension}</span> : null}
            <span className="workflow-chip">{step.id}</span>
          </span>
        </button>
      ))}
    </div>
  );
}
