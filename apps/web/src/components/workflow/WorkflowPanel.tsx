import { useEffect, useMemo, useState } from "react";
import { workflowSummaryLabel, zhCN } from "../../content/zh-CN";
import type { WorkflowModel, WorkflowStageProgress } from "../../types/workflow";
import { SourceBadge } from "../chat/SourceBadge";
import { WorkflowExecutionView } from "./WorkflowExecutionView";
import { WorkflowFinalView } from "./WorkflowFinalView";
import { WorkflowFusionView } from "./WorkflowFusionView";
import { WorkflowPlanView } from "./WorkflowPlanView";
import { WorkflowSection } from "./WorkflowSection";

interface WorkflowPanelProps {
  workflow: WorkflowModel;
}

const stageStatusLabel: Record<WorkflowStageProgress["status"], string> = {
  waiting: "\u7b49\u5f85\u4e2d",
  running: "\u8fdb\u884c\u4e2d",
  completed: "\u5df2\u5b8c\u6210",
  failed: "\u5df2\u5931\u8d25",
};

function liveWorkflowSummary(workflow: WorkflowModel) {
  const liveProgress = workflow.liveProgress ?? [];
  const runningStage = liveProgress.find((stage) => stage.status === "running");
  const failedStage = liveProgress.find((stage) => stage.status === "failed");
  const completedCount = liveProgress.filter((stage) => stage.status === "completed").length;
  if (failedStage) {
    return `\u534f\u4f5c\u53d7\u963b \u00b7 ${failedStage.title}`;
  }
  if (runningStage) {
    return `\u6b63\u5728\u534f\u4f5c \u00b7 ${runningStage.title}`;
  }
  return `\u534f\u4f5c\u5df2\u5b8c\u6210 \u00b7 ${completedCount}/${liveProgress.length}`;
}

function renderLiveProgress(liveProgress: WorkflowStageProgress[]) {
  return (
    <div className="workflow-panel__live" aria-label="\u5b9e\u65f6\u534f\u4f5c\u8fdb\u5ea6">
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

export function WorkflowPanel({ workflow }: WorkflowPanelProps) {
  const liveProgress = workflow.liveProgress ?? null;
  const isLive = Boolean(liveProgress?.length);
  const [expanded, setExpanded] = useState(isLive);

  useEffect(() => {
    if (isLive) {
      setExpanded(true);
    }
  }, [isLive]);

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
            协
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
        <div className="workflow-panel__content">
          <WorkflowSection eyebrow={zhCN.workflow.sections.planning} title={zhCN.workflow.sections.planning} icon="策">
            <WorkflowPlanView workflow={workflow} />
          </WorkflowSection>
          <WorkflowSection eyebrow={zhCN.workflow.sections.execution} title={zhCN.workflow.sections.execution} icon="研">
            <WorkflowExecutionView workflow={workflow} />
          </WorkflowSection>
          <WorkflowSection eyebrow={zhCN.workflow.sections.fusion} title={zhCN.workflow.sections.fusion} icon="融">
            <WorkflowFusionView workflow={workflow} />
          </WorkflowSection>
          <WorkflowSection eyebrow={zhCN.workflow.sections.final} title={zhCN.workflow.sections.final} icon="结" isLast>
            <WorkflowFinalView workflow={workflow} />
          </WorkflowSection>
        </div>
      ) : null}
    </section>
  );
}
