import { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { AnswerCardModel, PublicTurn } from "../../types/chat";
import type { WorkflowModel, WorkflowStageKey } from "../../types/workflow";
import { citationLabel, continuityLabel, sourceLabel, zhCN } from "../../content/zh-CN";
import { ResearchThoughtChain } from "../workflow/ResearchThoughtChain";
import { WorkflowPanel } from "../workflow/WorkflowPanel";

interface AssistantAnswerCardProps {
  turn: PublicTurn;
}

const STREAMING_PLACEHOLDER_ANSWERS = new Set(["正在协作…", "正在协作..."]);
const PENDING_STAGE_COPY: Record<WorkflowStageKey, { title: string; summary: string }> = {
  planning: {
    title: "问题理解",
    summary: "正在把用户问题整理成可执行的研判任务。",
  },
  evidence: {
    title: "证据接入",
    summary: "正在整理本轮回答所需的基础材料。",
  },
  l2_analysis: {
    title: "并行分析",
    summary: "正在从价值、市场、风险、宏观等方向形成线索。",
  },
  dimension_composite: {
    title: "维度综合",
    summary: "正在汇总四维流程信号并处理差异。",
  },
  decision: {
    title: "决策生成",
    summary: "正在把流程线索组织成回答框架。",
  },
  report: {
    title: "文字报告输出",
    summary: "正在把结论、依据和限制整理成自然语言报告。",
  },
};

function isStreamingPlaceholderAnswer(answer: string) {
  return STREAMING_PLACEHOLDER_ANSWERS.has(answer.trim());
}

function isWorkflowReportComplete(workflow: WorkflowModel | undefined) {
  if (!workflow) {
    return false;
  }
  if (workflow.currentStage === "report") {
    return true;
  }
  const reportStage = workflow.stages.find((stage) => stage.key === "report");
  return Boolean(reportStage?.stepIds.some((stepId) => workflow.completedSteps.includes(stepId)));
}

function pendingStageCopy(workflow: WorkflowModel | undefined) {
  const key = workflow?.currentStage ?? "planning";
  return PENDING_STAGE_COPY[key] ?? PENDING_STAGE_COPY.planning;
}

function renderCitations(answerCard: AnswerCardModel) {
  if (!answerCard.citations?.length) {
    return null;
  }

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

function renderDebugMeta(turn: PublicTurn, answerCard: AnswerCardModel, open: boolean, onToggle: () => void) {
  const provenance = turn.workflow?.provenance;
  const evidenceCount = answerCard.evidenceCount ?? answerCard.evidenceCards?.length ?? 0;
  const items = [
    turn.continuityMode ? { label: zhCN.answer.debug.continuity, value: continuityLabel(turn.continuityMode) } : null,
    turn.runId ? { label: zhCN.answer.debug.runId, value: turn.runId } : null,
    { label: zhCN.answer.debug.evidence, value: String(evidenceCount) },
    provenance ? { label: zhCN.answer.debug.emit, value: sourceLabel(provenance.source) } : null,
  ].filter(Boolean) as Array<{ label: string; value: string }>;

  if (!items.length) {
    return null;
  }

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
    const stage = pendingStageCopy(turn.workflow);
    return (
      <div className="assistant-card__body assistant-card__pending-answer" aria-label="正在组织研判答案">
        <span className="assistant-card__pending-kicker">正在组织研判答案</span>
        <h3>正在组织研判答案</h3>
        <p>研判中，最终文字报告将在流程完成后直接出现在这里。</p>
        <div className="assistant-card__pending-stage">
          <strong>{stage.title}</strong>
          <span>{stage.summary}</span>
        </div>
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

  if (!answerCard) {
    return null;
  }

  return (
    <article className="assistant-card" aria-label="系统回答卡片">
      <div className="assistant-card__avatar" aria-hidden="true">
        智
      </div>
      <div className="assistant-card__content">
        {renderAnswerBody(turn, answerCard)}
        {renderCitations(answerCard)}
        {turn.workflow ? <ResearchThoughtChain workflow={turn.workflow} /> : null}
        {turn.workflow ? <WorkflowPanel workflow={turn.workflow} /> : null}
        {renderDebugMeta(turn, answerCard, detailsOpen, () => setDetailsOpen((current) => !current))}
      </div>
    </article>
  );
}
