import { useState } from "react";
import { zhCN } from "../../content/zh-CN";
import type { StructuredInputModel } from "../../types/chat";
import {
  composeStructuredPrompt,
  EMPTY_STRUCTURED_INPUT_DRAFT,
  getStructuredInputValidationError,
  toStructuredInputModel,
  type StructuredInputDraft,
} from "../../utils/structuredInput";

interface ComposerProps {
  onSubmit: (value: string, structuredInput?: StructuredInputModel) => void;
  disabled?: boolean;
  busy?: boolean;
  unavailable?: boolean;
}

export function Composer({ onSubmit, disabled = false, busy = false, unavailable = false }: ComposerProps) {
  const [structuredOpen, setStructuredOpen] = useState(false);
  const [draft, setDraft] = useState<StructuredInputDraft>(EMPTY_STRUCTURED_INPUT_DRAFT);
  const materialsLabel = "补充材料 / 笔记";
  const materialsPlaceholder =
    "可粘贴一段或多段研究笔记、会议纪要或摘录内容；多段内容请用空行分隔。";
  const urlReferencesLabel = "链接参考 / URL 引用";
  const urlReferencesPlaceholder = "每行填写一个完整链接，例如 https://example.com/report";
  const validationError = getStructuredInputValidationError(draft);

  function updateDraft(field: keyof StructuredInputDraft, value: string) {
    setDraft((current) => ({ ...current, [field]: value }));
  }

  function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const nextValue = composeStructuredPrompt(draft);
    const nextStructuredInput = toStructuredInputModel(draft);
    if (!nextValue || !nextStructuredInput || disabled || busy) {
      return;
    }
    onSubmit(nextValue, nextStructuredInput);
    setDraft(EMPTY_STRUCTURED_INPUT_DRAFT);
  }

  const canSubmit = Boolean(composeStructuredPrompt(draft)) && !validationError && !disabled && !busy;

  return (
    <form className="composer" onSubmit={handleSubmit}>
      <label className="composer__label" htmlFor="chat-composer">
        {zhCN.composer.taskLabel}
      </label>
      <div className="composer__surface">
        <textarea
          id="chat-composer"
          className="composer__input"
          value={draft.task}
          onChange={(event) => updateDraft("task", event.target.value)}
          rows={2}
          disabled={disabled || busy}
          placeholder={unavailable ? zhCN.composer.unavailablePlaceholder : zhCN.composer.taskPlaceholder}
          aria-label={zhCN.composer.taskLabel}
        />
        <button className="composer__submit" type="submit" disabled={!canSubmit} aria-label={zhCN.composer.submit}>
          {busy ? "…" : "↗"}
        </button>
      </div>
      <button
        className="composer__toggle"
        type="button"
        onClick={() => setStructuredOpen((current) => !current)}
        aria-expanded={structuredOpen}
        disabled={disabled || busy}
      >
        {structuredOpen ? zhCN.composer.collapseStructured : zhCN.composer.expandStructured}
      </button>
      {structuredOpen ? (
        <div className="composer__structured" aria-label={zhCN.composer.structuredLabel}>
          <p className="composer__structured-hint">{zhCN.composer.structuredHelper}</p>
          <div className="composer__structured-grid">
            <label className="composer__field" htmlFor="chat-context">
              <span>{zhCN.composer.contextLabel}</span>
              <textarea
                id="chat-context"
                value={draft.context}
                onChange={(event) => updateDraft("context", event.target.value)}
                rows={3}
                disabled={disabled || busy}
                placeholder={zhCN.composer.contextPlaceholder}
              />
            </label>
            <label className="composer__field" htmlFor="chat-materials">
              <span>{materialsLabel}</span>
              <textarea
                id="chat-materials"
                value={draft.materialsText}
                onChange={(event) => updateDraft("materialsText", event.target.value)}
                rows={5}
                disabled={disabled || busy}
                placeholder={materialsPlaceholder}
              />
            </label>
            <label className="composer__field" htmlFor="chat-url-references">
              <span>{urlReferencesLabel}</span>
              <textarea
                id="chat-url-references"
                value={draft.urlReferencesText}
                onChange={(event) => updateDraft("urlReferencesText", event.target.value)}
                rows={3}
                disabled={disabled || busy}
                placeholder={urlReferencesPlaceholder}
              />
            </label>
            <label className="composer__field" htmlFor="chat-constraints">
              <span>{zhCN.composer.constraintsLabel}</span>
              <textarea
                id="chat-constraints"
                value={draft.constraints}
                onChange={(event) => updateDraft("constraints", event.target.value)}
                rows={3}
                disabled={disabled || busy}
                placeholder={zhCN.composer.constraintsPlaceholder}
              />
            </label>
            <label className="composer__field" htmlFor="chat-output-preference">
              <span>{zhCN.composer.outputPreferenceLabel}</span>
              <textarea
                id="chat-output-preference"
                value={draft.outputPreference}
                onChange={(event) => updateDraft("outputPreference", event.target.value)}
                rows={2}
                disabled={disabled || busy}
                placeholder={zhCN.composer.outputPreferencePlaceholder}
              />
            </label>
          </div>
          {validationError ? <p className="composer__structured-warning">{validationError}</p> : null}
        </div>
      ) : null}
      <p className="composer__hint">{zhCN.composer.helper}</p>
    </form>
  );
}
