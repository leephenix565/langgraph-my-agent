import { useCallback, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { AnswerCardModel, PublicTurn } from "../../types/chat";
import type { WorkflowModel, WorkflowStageKey } from "../../types/workflow";
import { citationLabel, continuityLabel, dimensionLabel, sourceLabel, uncoveredDimensions, zhCN } from "../../content/zh-CN";
import { ResearchThoughtChain } from "../workflow/ResearchThoughtChain";

interface AssistantAnswerCardProps {
  turn: PublicTurn;
}

const STREAMING_PLACEHOLDER_ANSWERS = new Set(["正在协作…", "正在协作..."]);
const PENDING_STAGE_COPY: Record<WorkflowStageKey, { title: string; summary: string }> = {
  planning: { title: "问题理解", summary: "正在把用户问题整理成可执行的研判任务。" },
  evidence: { title: "证据接入", summary: "正在整理本轮回答所需的基础材料。" },
  l2_analysis: { title: "并行分析", summary: "正在从价值、市场、风险、宏观等方向形成线索。" },
  dimension_composite: { title: "维度综合", summary: "正在汇总四维流程信号并处理差异。" },
  decision: { title: "决策生成", summary: "正在把流程线索组织成回答框架。" },
  report: { title: "文字报告输出", summary: "正在把结论、依据和限制整理成自然语言报告。" },
};

function isStreamingPlaceholderAnswer(answer: string) {
  return STREAMING_PLACEHOLDER_ANSWERS.has(answer.trim());
}

function isWorkflowReportComplete(workflow: WorkflowModel | undefined) {
  if (!workflow) return false;
  if (workflow.currentStage === "report") return true;
  const reportStage = workflow.stages.find((stage) => stage.key === "report");
  return Boolean(reportStage?.stepIds.some((stepId) => workflow.completedSteps.includes(stepId)));
}

function pendingStageCopy(workflow: WorkflowModel | undefined) {
  const key = workflow?.currentStage ?? "planning";
  return PENDING_STAGE_COPY[key] ?? PENDING_STAGE_COPY.planning;
}

function renderCitations(answerCard: AnswerCardModel) {
  if (!answerCard.citations?.length) return null;
  return (
    <div className="assistant-card__references">
      <div className="assistant-card__references-head">
        <span className="assistant-card__meta-label">{zhCN.answer.references}</span>
      </div>
      <ul className="citation-list" aria-label={zhCN.answer.references}>
        {answerCard.citations.map((citation) => (
          <li key={citation.label}>
            <strong>{citationLabel(citation.label)}</strong>
            <span>{citation.note}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

function renderRoutingBadge(provenance: Record<string, any> | undefined) {
  if (!provenance) return null;
  const selectedRoutingRequested = provenance.selectedRoutingRequested;
  const selectedRoutingFallback = provenance.selectedRoutingFallback;
  const selectedDimensions: string[] = provenance.selectedDimensions ?? [];

  if (selectedRoutingFallback) {
    return (
      <div className="routing-badge routing-badge--fallback">
        <span className="routing-badge__icon">⚠</span>
        <span className="routing-badge__text">{zhCN.answer.routingFallback}</span>
      </div>
    );
  }

  if (selectedRoutingRequested && selectedDimensions.length > 0) {
    return (
      <div className="routing-badge routing-badge--selected">
        <span className="routing-badge__label">{zhCN.answer.routingSelected}：</span>
        {selectedDimensions.map((d) => (
          <span key={d} className={`routing-badge__dim rbd-${d}`}>{zhCN.answer.dimensions[d as keyof typeof zhCN.answer.dimensions] ?? d}</span>
        ))}
      </div>
    );
  }

  return (
    <div className="routing-badge routing-badge--default">
      <span className="routing-badge__label">{zhCN.answer.routingDefault}</span>
    </div>
  );
}

function renderUncoveredScope(provenance: Record<string, any> | undefined) {
  if (!provenance) return null;
  const selectedDimensions: string[] = provenance.selectedDimensions ?? [];
  if (selectedDimensions.length === 0) return null;
  const uncovered = uncoveredDimensions(selectedDimensions);
  if (uncovered.length === 0) return null;

  return (
    <div className="uncovered-scope">
      <span className="uncovered-scope__label">{zhCN.answer.uncoveredScope}：</span>
      <span className="uncovered-scope__dims">{uncovered.map((d) => zhCN.answer.dimensions[d as keyof typeof zhCN.answer.dimensions] ?? d).join("、")}</span>
      <span className="uncovered-scope__note">{zhCN.answer.uncoveredScopeNote}</span>
    </div>
  );
}

function renderProgress(workflow: WorkflowModel | undefined) {
  if (!workflow) return null;
  const stage = pendingStageCopy(workflow);
  const dagIds = new Set(workflow.dagSteps.map((s) => s.id));
  const completed = workflow.completedSteps.filter((id) => dagIds.has(id)).length;
  const total = workflow.dagSteps.length;

  return (
    <div className="loading-progress">
      <div className="loading-progress__pulse" aria-hidden="true">
        <span className="loading-progress__dot" />
        <span className="loading-progress__dot" />
        <span className="loading-progress__dot" />
      </div>
      <div className="loading-progress__body">
        <div className="loading-progress__stage">
          <strong>{stage.title}</strong>
          <span>{stage.summary}</span>
        </div>
        {total > 0 && (
          <div className="loading-progress__count">
            <span className="loading-progress__step-counter">{completed}/{total}</span>
            <span className="loading-progress__step-label">{zhCN.answer.stepsComplete}</span>
          </div>
        )}
      </div>
    </div>
  );
}

function renderDebugMeta(turn: PublicTurn, answerCard: AnswerCardModel, open: boolean, onToggle: () => void) {
  const provenance = turn.workflow?.provenance;
  const evidenceCount = answerCard.evidenceCount ?? answerCard.evidenceCards?.length ?? 0;
  const items = [
    turn.continuityMode ? { label: zhCN.answer.debug.continuity, value: continuityLabel(turn.continuityMode) } : null,
    turn.runId ? { label: zhCN.answer.debug.runId, value: turn.runId } : null,
    { label: zhCN.answer.debug.evidence, value: String(evidenceCount) },
    provenance ? { label: zhCN.answer.debug.emit, value: sourceLabel(provenance.source) } : null,
  ].filter(Boolean) as Array<{ label: string; value: string }>;

  if (!items.length) return null;

  return (
    <div className="assistant-card__details">
      <button className="assistant-card__details-toggle" type="button" onClick={onToggle} aria-expanded={open}>
        <span>{open ? zhCN.answer.hideDetails : zhCN.answer.showDetails}</span>
      </button>
      {open ? (
        <div className="assistant-card__meta" aria-label="技术详情">
          {items.map((item) => (
            <span className="assistant-card__meta-item" key={`${item.label}-${item.value}`}>
              <span className="assistant-card__meta-label">{item.label}</span>
              <strong>{item.value}</strong>
            </span>
          ))}
        </div>
      ) : null}
    </div>
  );
}

function renderAnswerBody(turn: PublicTurn, answerCard: AnswerCardModel) {
  const showPendingAnswer =
    Boolean(turn.workflow) && !isWorkflowReportComplete(turn.workflow) && isStreamingPlaceholderAnswer(answerCard.answer);

  if (showPendingAnswer) {
    return (
      <div className="assistant-card__body assistant-card__pending-answer" aria-label={zhCN.answer.loadingKicker}>
        <span className="assistant-card__pending-kicker">{zhCN.answer.loadingKicker}</span>
        <h3>{zhCN.answer.loadingKicker}</h3>
        <p>{zhCN.answer.loadingStatus}</p>
        {renderProgress(turn.workflow)}
      </div>
    );
  }

  return (
    <div className="assistant-card__body assistant-card__markdown">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          a: ({ node: _node, ...props }) => <a {...props} target="_blank" rel="noreferrer" />,
        }}
      >
        {answerCard.answer}
      </ReactMarkdown>
    </div>
  );
}

export function AssistantAnswerCard({ turn }: AssistantAnswerCardProps) {
  const answerCard = turn.answerCard;
  const [detailsOpen, setDetailsOpen] = useState(false);
  const [copyLabel, setCopyLabel] = useState("复制回答");
  const provenance = turn.workflow?.provenance as Record<string, any> | undefined;
  const showPendingAnswer =
    Boolean(turn.workflow) && !isWorkflowReportComplete(turn.workflow) && isStreamingPlaceholderAnswer(answerCard?.answer ?? "");

  const handleCopy = useCallback(() => {
    if (!answerCard?.answer) return;
    navigator.clipboard.writeText(answerCard.answer).then(() => {
      setCopyLabel("已复制");
      setTimeout(() => setCopyLabel("复制回答"), 2000);
    }).catch(() => {
      setCopyLabel("复制失败");
      setTimeout(() => setCopyLabel("复制回答"), 2000);
    });
  }, [answerCard]);

  if (!answerCard) return null;

  return (
    <article className="assistant-card" aria-label="系统回答卡片">
      <div className="assistant-card__avatar" aria-hidden="true">智</div>
      <div className="assistant-card__content">
        {renderRoutingBadge(provenance)}
        {renderUncoveredScope(provenance)}
        {renderAnswerBody(turn, answerCard)}
        {showPendingAnswer ? null : (
          <button className="assistant-card__copy" type="button" onClick={handleCopy} aria-label={copyLabel}>
            {copyLabel}
          </button>
        )}
        {renderCitations(answerCard)}
        {turn.workflow ? <ResearchThoughtChain workflow={turn.workflow} /> : null}
        {renderDebugMeta(turn, answerCard, detailsOpen, () => setDetailsOpen((current) => !current))}
      </div>
    </article>
  );
}
