import { agentNameLabel, dagStepStatusLabel, stageLabel, zhCN } from "../../content/zh-CN";
import type { DagStep, WorkflowModel, WorkflowStepResult } from "../../types/workflow";

interface WorkflowStepResultsProps {
  workflow: WorkflowModel;
  selectedStepId: string | null;
}

function asDisplayString(value: unknown) {
  return typeof value === "string" && value.trim() ? value : null;
}

function asBooleanLabel(value: unknown) {
  if (value === true) {
    return zhCN.workflow.boolean.yes;
  }
  if (value === false) {
    return zhCN.workflow.boolean.no;
  }
  return null;
}

function warningList(result: WorkflowStepResult | undefined) {
  const warnings = result?.warnings;
  if (Array.isArray(warnings)) {
    return warnings.filter((warning): warning is string => typeof warning === "string" && warning.trim().length > 0);
  }
  if (typeof warnings === "string" && warnings.trim()) {
    return [warnings];
  }
  return [];
}

function selectedStep(workflow: WorkflowModel, selectedStepId: string | null): DagStep | null {
  if (!selectedStepId) {
    return null;
  }
  return workflow.dagSteps.find((step) => step.id === selectedStepId) ?? null;
}

export function WorkflowStepResults({ workflow, selectedStepId }: WorkflowStepResultsProps) {
  const step = selectedStep(workflow, selectedStepId);
  const result = selectedStepId ? workflow.stepResults[selectedStepId] : undefined;

  if (!step) {
    return <p className="workflow-empty">{zhCN.workflow.emptyResult}</p>;
  }

  const runtimeKind = asDisplayString(result?.runtime_kind);
  const implementationStatus = asDisplayString(result?.implementation_status);
  const invokeEnabled = asBooleanLabel(result?.invoke_enabled);
  const liveVerified = asBooleanLabel(result?.live_verified);
  const warnings = warningList(result);

  return (
    <article className="workflow-result-card" aria-label={zhCN.workflow.sections.results}>
      <div className="workflow-result-card__head">
        <div>
          <span className="workflow-kicker">{zhCN.workflow.selectedStep}</span>
          <h4>{agentNameLabel(step.agentId ?? step.id, step.title)}</h4>
        </div>
        <span className={`workflow-status workflow-status--${step.status}`}>{dagStepStatusLabel(step.status)}</span>
      </div>

      <p>{step.summary}</p>

      <dl className="workflow-metadata-grid">
        <div>
          <dt>{zhCN.workflow.resultFields.stepId}</dt>
          <dd>{step.id}</dd>
        </div>
        <div>
          <dt>{zhCN.workflow.resultFields.agentId}</dt>
          <dd>{step.agentId ?? step.id}</dd>
        </div>
        <div>
          <dt>{zhCN.workflow.resultFields.stage}</dt>
          <dd>{stageLabel(step.stage)}</dd>
        </div>
        <div>
          <dt>{zhCN.workflow.resultFields.dimension}</dt>
          <dd>{step.dimension ?? zhCN.workflow.none}</dd>
        </div>
        {runtimeKind ? (
          <div>
            <dt>{zhCN.workflow.resultFields.runtimeKind}</dt>
            <dd>{runtimeKind}</dd>
          </div>
        ) : null}
        {implementationStatus ? (
          <div>
            <dt>{zhCN.workflow.resultFields.implementationStatus}</dt>
            <dd>{implementationStatus}</dd>
          </div>
        ) : null}
        {invokeEnabled ? (
          <div>
            <dt>{zhCN.workflow.resultFields.invokeEnabled}</dt>
            <dd>{invokeEnabled}</dd>
          </div>
        ) : null}
        {liveVerified ? (
          <div>
            <dt>{zhCN.workflow.resultFields.liveVerified}</dt>
            <dd>{liveVerified}</dd>
          </div>
        ) : null}
      </dl>

      {warnings.length ? (
        <div className="workflow-warning-list">
          <strong>{zhCN.workflow.resultFields.warnings}</strong>
          <ul>
            {warnings.map((warning) => (
              <li key={warning}>{warning}</li>
            ))}
          </ul>
        </div>
      ) : null}
    </article>
  );
}
