import { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { AnswerCardModel, PublicTurn } from "../../types/chat";
import { citationLabel, continuityLabel, sourceLabel, zhCN } from "../../content/zh-CN";
import { WorkflowPanel } from "../workflow/WorkflowPanel";

interface AssistantAnswerCardProps {
  turn: PublicTurn;
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
      <ul className="citation-list" aria-label="参考依据">
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
        {renderCitations(answerCard)}
        {turn.workflow ? <WorkflowPanel workflow={turn.workflow} /> : null}
        {renderDebugMeta(turn, answerCard, detailsOpen, () => setDetailsOpen((current) => !current))}
      </div>
    </article>
  );
}
