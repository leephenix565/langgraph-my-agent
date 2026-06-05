import { useEffect, useMemo, useState } from "react";
import { workflowSummaryLabel, zhCN } from "../../content/zh-CN";
import type { WorkflowModel, WorkflowStageProgress } from "../../types/workflow";
import { SourceBadge } from "../chat/SourceBadge";
import { WorkflowDagStepList } from "./WorkflowDagStepList";
import { WorkflowDimensionGroups } from "./WorkflowDimensionGroups";
import { WorkflowExecutionBatches } from "./WorkflowExecutionBatches";
import { WorkflowProvenanceView } from "./WorkflowProvenanceView";
import { WorkflowStageTimeline } from "./WorkflowStageTimeline";
import { WorkflowStepResults } from "./WorkflowStepResults";

interface WorkflowPanelProps {
  workflow: WorkflowModel;
}

const stageStatusLabel: Record<WorkflowStageProgress["status"], string> = {
  waiting: "等待中",
  running: "进行中",
  completed: "已完成",
  failed: "已失败",
};

function liveWorkflowSummary(workflow: WorkflowModel) {
  const liveProgress = workflow.liveProgress ?? [];
  const runningStage = liveProgress.find((stage) => stage.status === "running");
  const failedStage = liveProgress.find((stage) => stage.status === "failed");
  const completedCount = liveProgress.filter((stage) => stage.status === "completed").length;
  if (failedStage) {
    return `协作受阻 · ${failedStage.title}`;
  }
  if (runningStage) {
    return `正在执行固定 DAG · ${runningStage.title}`;
  }
  return `固定 DAG 已完成 · ${completedCount}/${liveProgress.length}`;
}

function renderLiveProgress(liveProgress: WorkflowStageProgress[]) {
  return (
    <div className="workflow-panel__live" aria-label="实时固定 DAG 进度">
      <div className="workflow-panel__live-list">
        {liveProgress.map((stage) => (
          <div className={`workflow-progress workflow-progress--${stage.status}`} key={stage.key}>
            <span className="workflow-progress__title">{stage.title}</span>
            <span className="workflow-progress__status">{stageStatusLabel[stage.status]}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function defaultSelectedStepId(workflow: WorkflowModel) {
  const firstResultId = Object.keys(workflow.stepResults)[0];
  return firstResultId ?? workflow.dagSteps[0]?.id ?? null;
}

export function WorkflowPanel({ workflow }: WorkflowPanelProps) {
  const liveProgress = workflow.liveProgress ?? null;
  const isLive = Boolean(liveProgress?.length);
  const [expanded, setExpanded] = useState(isLive);
  const [selectedStepId, setSelectedStepId] = useState<string | null>(() => defaultSelectedStepId(workflow));

  useEffect(() => {
    if (isLive) {
      setExpanded(true);
    }
  }, [isLive]);

  useEffect(() => {
    setSelectedStepId((current) => {
      if (current && workflow.dagSteps.some((step) => step.id === current)) {
        return current;
      }
      return defaultSelectedStepId(workflow);
    });
  }, [workflow]);

  const summaryLabel = useMemo(() => {
    if (isLive) {
      return liveWorkflowSummary(workflow);
    }
    return workflowSummaryLabel(workflow);
  }, [isLive, workflow]);

  return (
    <section className="workflow-panel">
      <button
        type="button"
        className="workflow-panel__toggle"
        aria-expanded={expanded}
        onClick={() => setExpanded((current) => !current)}
      >
        <div className="workflow-panel__summary">
          <span className="workflow-panel__glyph" aria-hidden="true">
            DAG
          </span>
          <strong>{summaryLabel}</strong>
        </div>
        <div className="workflow-panel__summary-meta">
          {isLive ? null : <SourceBadge source={workflow.finalSource} />}
          <span className="workflow-panel__action">{expanded ? zhCN.workflow.collapse : zhCN.workflow.expand}</span>
        </div>
      </button>

      {isLive ? renderLiveProgress(liveProgress ?? []) : null}

      {expanded ? (
        <div className="workflow-panel__content" aria-label={zhCN.workflow.inspectorLabel}>
          <div className="workflow-inspector">
            <section className="workflow-inspector__card workflow-inspector__card--wide">
              <header className="workflow-inspector__header">
                <span className="workflow-kicker">{zhCN.workflow.kickers.plan}</span>
                <h4>{zhCN.workflow.sections.timeline}</h4>
              </header>
              <WorkflowStageTimeline workflow={workflow} />
            </section>

            <section className="workflow-inspector__card">
              <header className="workflow-inspector__header">
                <span className="workflow-kicker">{zhCN.workflow.kickers.batches}</span>
                <h4>{zhCN.workflow.sections.batches}</h4>
              </header>
              <WorkflowExecutionBatches workflow={workflow} />
            </section>

            <section className="workflow-inspector__card">
              <header className="workflow-inspector__header">
                <span className="workflow-kicker">{zhCN.workflow.kickers.dimensions}</span>
                <h4>{zhCN.workflow.sections.dimensions}</h4>
              </header>
              <WorkflowDimensionGroups workflow={workflow} />
            </section>

            <section className="workflow-inspector__card workflow-inspector__card--wide">
              <header className="workflow-inspector__header">
                <span className="workflow-kicker">{zhCN.workflow.kickers.steps}</span>
                <h4>{zhCN.workflow.sections.steps}</h4>
              </header>
              <WorkflowDagStepList workflow={workflow} selectedStepId={selectedStepId} onSelectStep={setSelectedStepId} />
            </section>

            <section className="workflow-inspector__card">
              <header className="workflow-inspector__header">
                <span className="workflow-kicker">{zhCN.workflow.kickers.results}</span>
                <h4>{zhCN.workflow.sections.results}</h4>
              </header>
              <WorkflowStepResults workflow={workflow} selectedStepId={selectedStepId} />
            </section>

            <section className="workflow-inspector__card">
              <WorkflowProvenanceView workflow={workflow} />
            </section>
          </div>
        </div>
      ) : null}
    </section>
  );
}
