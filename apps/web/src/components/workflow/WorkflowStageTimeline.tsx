import { zhCN } from "../../content/zh-CN";
import type { DagStep, WorkflowModel, WorkflowStage, WorkflowStageKey, WorkflowStageStatus } from "../../types/workflow";

interface WorkflowStageTimelineProps {
  workflow: WorkflowModel;
}

const failedStepStatuses = new Set(["blocked", "error", "failed"]);
const activeStepStatuses = new Set(["running", "partial", "pending_implementation"]);

function stepById(workflow: WorkflowModel, stepId: string) {
  return workflow.dagSteps.find((step) => step.id === stepId);
}

function liveStatusForStage(workflow: WorkflowModel, stageKey: WorkflowStageKey) {
  return workflow.liveProgress?.find((stage) => stage.key === stageKey)?.status ?? null;
}

function isStepCompleted(workflow: WorkflowModel, step: DagStep | undefined) {
  if (!step) {
    return false;
  }
  return step.status === "complete" || workflow.completedSteps.includes(step.id);
}

function stageStatus(workflow: WorkflowModel, stage: WorkflowStage): WorkflowStageStatus {
  const liveStatus = liveStatusForStage(workflow, stage.key);
  if (liveStatus) {
    return liveStatus;
  }

  const steps = stage.stepIds.map((stepId) => stepById(workflow, stepId)).filter(Boolean) as DagStep[];
  if (steps.some((step) => failedStepStatuses.has(step.status))) {
    return "failed";
  }
  if (stage.stepIds.length > 0 && stage.stepIds.every((stepId) => isStepCompleted(workflow, stepById(workflow, stepId)))) {
    return "completed";
  }
  if (workflow.currentStage === stage.key || steps.some((step) => activeStepStatuses.has(step.status))) {
    return "running";
  }
  return "waiting";
}

export function WorkflowStageTimeline({ workflow }: WorkflowStageTimelineProps) {
  if (!workflow.stages.length) {
    return <p className="workflow-empty">{zhCN.workflow.empty}</p>;
  }

  return (
    <ol className="workflow-stage-timeline" aria-label={zhCN.workflow.sections.timeline}>
      {workflow.stages.map((stage, index) => {
        const status = stageStatus(workflow, stage);
        return (
          <li className={`workflow-stage workflow-stage--${status}`} key={stage.key}>
            <span className="workflow-stage__index">{index + 1}</span>
            <span className="workflow-stage__body">
              <strong>{stage.title}</strong>
              <span>
                {stage.stepIds.length} {zhCN.workflow.units.steps}
              </span>
            </span>
            <span className={`workflow-status workflow-status--${status}`}>{zhCN.workflow.stageStatus[status]}</span>
          </li>
        );
      })}
    </ol>
  );
}
