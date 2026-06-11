import {
  agentNameLabel,
  dagStepStatusLabel,
  dimensionLabel,
  implementationStatusLabel,
  runtimeKindLabel,
  stageLabel,
  zhCN,
} from "../../content/zh-CN";
import type {
  WorkflowAgentEvidence,
  WorkflowCompositeEvidence,
  DagStep,
  WorkflowModel,
  WorkflowStepResult,
} from "../../types/workflow";

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

function renderTechnicalValue(label: string, raw: string) {
  return (
    <span className="workflow-technical-value">
      <span>{label}</span>
      <code>{raw}</code>
    </span>
  );
}

function formatNumber(value: unknown) {
  return typeof value === "number" && Number.isFinite(value) ? value.toFixed(2) : null;
}

function renderEvidenceField(label: string, value: unknown) {
  const text = typeof value === "number" ? formatNumber(value) : asDisplayString(value);
  if (!text) {
    return null;
  }
  return (
    <div>
      <dt>{label}</dt>
      <dd>{text}</dd>
    </div>
  );
}

function renderAgentEvidence(evidence: WorkflowAgentEvidence | undefined) {
  if (!evidence) {
    return null;
  }
  const confidence = formatNumber(evidence.confidence);
  const riskScore = formatNumber(evidence.risk_score);
  return (
    <section className="workflow-evidence-card">
      <strong>{zhCN.workflow.resultFields.agentEvidence}</strong>
      <dl className="workflow-metadata-grid">
        {renderEvidenceField(zhCN.workflow.resultFields.signal, evidence.stance)}
        {confidence ? renderEvidenceField(zhCN.workflow.resultFields.confidence, confidence) : null}
        {riskScore ? renderEvidenceField(zhCN.workflow.resultFields.riskScore, riskScore) : null}
        {renderEvidenceField(zhCN.workflow.resultFields.source, evidence.source)}
      </dl>
      {evidence.summary ? <p>{evidence.summary}</p> : null}
    </section>
  );
}

function renderCompositeEvidence(evidence: WorkflowCompositeEvidence | undefined) {
  if (!evidence) {
    return null;
  }
  const confidence = formatNumber(evidence.confidence);
  const weights = evidence.dimension_weights
    ? Object.entries(evidence.dimension_weights)
        .filter(([key]) => key === "value" || key === "market")
        .map(([key, value]) => `${dimensionLabel(key)} ${formatNumber(value) ?? value}`)
        .join(" / ")
    : "";
  return (
    <section className="workflow-evidence-card">
      <strong>{zhCN.workflow.resultFields.compositeEvidence}</strong>
      <dl className="workflow-metadata-grid">
        {renderEvidenceField(zhCN.workflow.resultFields.signal, evidence.stance ?? evidence.regime)}
        {confidence ? renderEvidenceField(zhCN.workflow.resultFields.confidence, confidence) : null}
        {renderEvidenceField(zhCN.workflow.resultFields.riskGate, evidence.gate)}
        {renderEvidenceField(zhCN.workflow.resultFields.riskScore, evidence.risk_score)}
        {weights ? renderEvidenceField(zhCN.workflow.resultFields.macroWeights, weights) : null}
        {renderEvidenceField(zhCN.workflow.resultFields.source, evidence.source)}
      </dl>
      {evidence.summary ? <p>{evidence.summary}</p> : null}
      {evidence.members?.length ? (
        <div className="workflow-evidence-members">
          <span>{zhCN.workflow.resultFields.members}</span>
          <div className="workflow-chip-row">
            {evidence.members.slice(0, 8).map((member) => (
              <span className="workflow-chip" key={member.agent_id}>
                {member.display_name ?? member.agent_id}
                {typeof member.weight === "number" ? ` ${member.weight.toFixed(2)}` : ""}
              </span>
            ))}
          </div>
        </div>
      ) : null}
    </section>
  );
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
          <dd>{step.dimension ? renderTechnicalValue(dimensionLabel(step.dimension), step.dimension) : zhCN.workflow.none}</dd>
        </div>
        {runtimeKind ? (
          <div>
            <dt>{zhCN.workflow.resultFields.runtimeKind}</dt>
            <dd>{renderTechnicalValue(runtimeKindLabel(runtimeKind), runtimeKind)}</dd>
          </div>
        ) : null}
        {implementationStatus ? (
          <div>
            <dt>{zhCN.workflow.resultFields.implementationStatus}</dt>
            <dd>{renderTechnicalValue(implementationStatusLabel(implementationStatus), implementationStatus)}</dd>
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

      {renderAgentEvidence(result?.agent_evidence)}
      {renderCompositeEvidence(result?.composite_evidence)}

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
