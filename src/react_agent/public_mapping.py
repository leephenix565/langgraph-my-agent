"""Safe mappings from runtime state to public web contracts."""

from __future__ import annotations

import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence
from urllib.parse import urlparse

from react_agent.agents import AGENT_METADATA, load_metadata_from_dir
from react_agent.public_contracts import (
    AgentStepModel,
    AnswerCardModel,
    ChatSessionSummary,
    CitationModel,
    ContinuityMode,
    EmitPath,
    EvidenceCardModel,
    FinalSource,
    FusionStepModel,
    LayerPlanItem,
    PublicThreadDetail,
    PublicTurn,
    StructuredInputModel,
    WorkflowModel,
    WorkflowProvenanceModel,
)

LAYER_ORDER: Sequence[str] = ("L1", "L2", "L3", "L4")
CONFIG_AGENT_DIR = Path(__file__).resolve().parents[2] / "config" / "agents"
STRUCTURED_INPUT_SECTIONS: Sequence[tuple[str, str]] = (
    ("task", "【任务】"),
    ("context", "【已知背景/材料】"),
    ("materials", "【补充材料/笔记】"),
    ("urlReferences", "【链接参考 / URL 引用】"),
    ("constraints", "【约束要求】"),
    ("outputPreference", "【输出偏好】"),
)


def _now_label() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def _truncate(text: str, limit: int) -> str:
    value = str(text or "").strip()
    if len(value) <= limit:
        return value
    return value[: max(limit - 3, 0)].rstrip() + "..."


def _ensure_agent_metadata() -> None:
    if not AGENT_METADATA:
        load_metadata_from_dir(CONFIG_AGENT_DIR)


def _coerce_str(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    return str(value).strip()


def _optional_str(value: Any) -> str | None:
    normalized = _coerce_str(value)
    return normalized or None


def _normalize_materials(raw: Any) -> List[str]:
    if not isinstance(raw, list):
        return []
    materials: List[str] = []
    for item in raw:
        normalized = _coerce_str(item)
        if normalized:
            materials.append(normalized)
    return materials


def _is_valid_url_reference(value: str) -> bool:
    if not value or any(character.isspace() for character in value):
        return False
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _normalize_url_references(raw: Any) -> List[str]:
    if not isinstance(raw, list):
        return []
    url_references: List[str] = []
    for item in raw:
        normalized = _coerce_str(item)
        if not normalized:
            continue
        if not _is_valid_url_reference(normalized):
            raise ValueError("Structured input URL references must be absolute http(s) URLs.")
        url_references.append(normalized)
    return url_references


def normalize_structured_input(structured_input: StructuredInputModel) -> StructuredInputModel:
    return StructuredInputModel(
        task=_coerce_str(structured_input.task),
        context=_optional_str(structured_input.context),
        materials=_normalize_materials(structured_input.materials),
        urlReferences=_normalize_url_references(structured_input.urlReferences),
        constraints=_optional_str(structured_input.constraints),
        outputPreference=_optional_str(structured_input.outputPreference),
    )


def _compose_materials_text(materials: Sequence[str]) -> str:
    return "\n\n".join(f"[材料 {index + 1}]\n{material}" for index, material in enumerate(materials))


def _compose_url_references_text(url_references: Sequence[str]) -> str:
    return "\n\n".join(f"[链接 {index + 1}]\n{url}" for index, url in enumerate(url_references))


def compose_structured_input_text(structured_input: StructuredInputModel) -> str:
    normalized = normalize_structured_input(structured_input)
    if not normalized.task:
        raise ValueError("Structured input task must not be empty.")

    has_supplemental_input = bool(
        normalized.context
        or normalized.materials
        or normalized.urlReferences
        or normalized.constraints
        or normalized.outputPreference
    )
    if not has_supplemental_input:
        return normalized.task

    parts = []
    for key, heading in STRUCTURED_INPUT_SECTIONS:
        value = getattr(normalized, key)
        if key == "materials":
            if value:
                parts.append(f"{heading}\n{_compose_materials_text(value)}")
            continue
        if key == "urlReferences":
            if value:
                parts.append(f"{heading}\n{_compose_url_references_text(value)}")
            continue
        if value:
            parts.append(f"{heading}\n{value}")
    return "\n\n".join(parts)


def _normalize_final_source(value: Any) -> FinalSource:
    source = _coerce_str(value).lower()
    if source in {"baseline", "fused"}:
        return source
    return "mainline"


def _confidence_label(value: Any) -> str | None:
    if value is None or value == "":
        return None
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        text = _coerce_str(value).lower()
        return text or None
    if numeric >= 0.8:
        return "high"
    if numeric >= 0.5:
        return "medium"
    return "low"


def _normalize_evidence_cards(raw: Any) -> List[EvidenceCardModel]:
    if not isinstance(raw, list):
        return []
    cards: List[EvidenceCardModel] = []
    for idx, item in enumerate(raw, start=1):
        if isinstance(item, str):
            text = item.strip()
            if text:
                cards.append(EvidenceCardModel(title=text, note=""))
            continue
        if isinstance(item, dict):
            title = (
                _coerce_str(item.get("title"))
                or _coerce_str(item.get("label"))
                or _coerce_str(item.get("agent_id"))
                or _coerce_str(item.get("source"))
                or f"Evidence {idx}"
            )
            note = (
                _coerce_str(item.get("note"))
                or _coerce_str(item.get("summary"))
                or _coerce_str(item.get("snippet"))
                or _coerce_str(item.get("evidence"))
                or _coerce_str(item.get("analysis"))
            )
            cards.append(EvidenceCardModel(title=title, note=note))
            continue
        text = _coerce_str(item)
        if text:
            cards.append(EvidenceCardModel(title=text, note=""))
    return cards


def _derive_citations(cards: Iterable[EvidenceCardModel]) -> List[CitationModel]:
    citations: List[CitationModel] = []
    for card in cards:
        citations.append(
            CitationModel(
                label=card.title,
                note=card.note or "Evidence carried through the public adapter.",
            )
        )
    return citations[:3]


def build_user_turn(text: str, structured_input: StructuredInputModel | None = None) -> PublicTurn:
    normalized_text = text.strip()
    normalized_structured = None
    if structured_input is not None:
        # Keep transcript text as the canonical public truth; structured input is only an additive mirror.
        normalized_structured = normalize_structured_input(structured_input)
        if compose_structured_input_text(normalized_structured) != normalized_text:
            raise ValueError("Structured input does not match canonical transcript text.")

    stamp = _now_label()
    return PublicTurn(
        id=f"user-{uuid.uuid4().hex[:10]}",
        role="user",
        text=normalized_text,
        createdAt=stamp,
        structuredInput=normalized_structured,
    )


def _layer_plan_items(layer_plan_raw: Any, layer_mode_raw: Any) -> List[LayerPlanItem]:
    layer_plan = layer_plan_raw if isinstance(layer_plan_raw, dict) else {}
    layer_mode = layer_mode_raw if isinstance(layer_mode_raw, dict) else {}
    items: List[LayerPlanItem] = []
    for layer in LAYER_ORDER:
        selected_raw = layer_plan.get(layer, [])
        selected = (
            [str(item).strip() for item in selected_raw if str(item).strip()]
            if isinstance(selected_raw, list)
            else []
        )
        mode = _coerce_str(layer_mode.get(layer)) or "Star"
        items.append(
            LayerPlanItem(
                layer=layer,  # type: ignore[arg-type]
                mode=mode,
                selected=selected,
                note="No agents selected." if not selected else None,
            )
        )
    return items


def _layer_done_list(raw: Any) -> List[str]:
    if not isinstance(raw, dict):
        return []
    return [layer for layer in LAYER_ORDER if bool(raw.get(layer))]


def _agent_summary(agent_id: str) -> str:
    _ensure_agent_metadata()
    meta = AGENT_METADATA.get(agent_id)
    if meta and meta.description:
        return _truncate(meta.description.replace("\n", " "), 140)
    return "Selected in the workflow plan."


def _agent_title(agent_id: str) -> str:
    _ensure_agent_metadata()
    meta = AGENT_METADATA.get(agent_id)
    return meta.name if meta and meta.name else agent_id


def _build_agent_steps(
    layer_plan_raw: Any,
    layer_done_raw: Any,
    fanout_targets_raw: Any,
) -> List[AgentStepModel]:
    layer_plan = layer_plan_raw if isinstance(layer_plan_raw, dict) else {}
    done = set(_layer_done_list(layer_done_raw))
    fanout_targets = (
        {str(item).strip() for item in fanout_targets_raw if str(item).strip()}
        if isinstance(fanout_targets_raw, list)
        else set()
    )
    steps: List[AgentStepModel] = []
    for layer in LAYER_ORDER:
        selected = layer_plan.get(layer, [])
        if not isinstance(selected, list):
            continue
        for index, agent_id in enumerate(selected):
            agent_id = str(agent_id).strip()
            if not agent_id:
                continue
            if layer in done:
                status = "complete"
            elif agent_id in fanout_targets:
                status = "running"
            else:
                status = "queued"
            steps.append(
                AgentStepModel(
                    id=f"{layer}-{agent_id}-{index}",
                    layer=layer,  # type: ignore[arg-type]
                    agentId=agent_id,
                    title=_agent_title(agent_id),
                    summary=_agent_summary(agent_id),
                    status=status,  # type: ignore[arg-type]
                    signal="Completed in the final answer path." if status == "complete" else None,
                )
            )
    return steps


def _fusion_step_status(kind: str, raw_status: str, final_source: FinalSource) -> str:
    status = raw_status.strip().lower()
    if status in {"", "disabled"}:
        return "disabled"
    if status == "error":
        return "error"
    if kind == "baseline" and final_source == "baseline" and status == "ready":
        return "selected"
    if kind == "writer" and final_source == "fused" and status == "ready":
        return "selected"
    if status == "ready":
        return "shadow"
    return "shadow"


def _fusion_step_summary(kind: str, status: str, final_source: FinalSource) -> str:
    if status == "disabled":
        return "This sidecar was not active for the completed turn."
    if status == "error":
        return "This sidecar encountered an error and did not become the public answer."
    if status == "selected":
        if kind == "baseline":
            return "The baseline sidecar supplied the final visible answer."
        if kind == "writer":
            return "The fusion writer produced the final visible answer."
    if kind == "judge":
        return "Judge output stayed in sidecar mode and informed the fusion decision without becoming a transcript speaker."
    return "This sidecar completed in shadow mode and stayed outside the public transcript."


def _build_fusion_steps(state: Dict[str, Any], final_source: FinalSource) -> List[FusionStepModel]:
    raw_steps = [
        ("baseline", "Baseline sidecar", _coerce_str(state.get("baseline_status"))),
        ("judge", "Fusion judge", _coerce_str(state.get("judge_status"))),
        ("writer", "Fusion writer", _coerce_str(state.get("writer_status"))),
    ]
    steps: List[FusionStepModel] = []
    for kind, label, raw_status in raw_steps:
        status = _fusion_step_status(kind, raw_status, final_source)
        steps.append(
            FusionStepModel(
                id=f"fusion-{kind}",
                kind=kind,  # type: ignore[arg-type]
                label=label,
                status=status,  # type: ignore[arg-type]
                summary=_fusion_step_summary(kind, status, final_source),
            )
        )
    return steps


def _normalize_emit_path(summary_source: Any) -> EmitPath:
    normalized = _coerce_str(summary_source).lower()
    if normalized == "baseline_sidecar":
        return "baseline_sidecar"
    if normalized == "fusion_writer_shadow":
        return "fusion_writer"
    return "mainline_summary"


def _provenance_summary(
    emit_path: EmitPath,
    final_source: FinalSource,
    continuity_mode: ContinuityMode,
) -> str:
    if emit_path == "baseline_sidecar":
        summary = "The final answer was emitted from the baseline sidecar path."
    elif emit_path == "fusion_writer":
        summary = "The final answer was emitted from the fusion writer path."
    else:
        summary = "The final answer was emitted from the mainline summary path."
    if final_source == "baseline":
        summary += " Final source stayed on the baseline branch."
    elif final_source == "fused":
        summary += " Final source stayed on the fused writer branch."
    else:
        summary += " Final source stayed on the mainline branch."
    if continuity_mode == "replay":
        summary += " Continuity uses transcript replay, which is weaker than persistent graph state."
    return summary


def _build_provenance(state: Dict[str, Any], continuity_mode: ContinuityMode) -> WorkflowProvenanceModel:
    final_source = _normalize_final_source(state.get("final_answer_source"))
    emitted_bundle = state.get("emitted_bundle", {})
    emitted_bundle = emitted_bundle if isinstance(emitted_bundle, dict) else {}
    emit_path = _normalize_emit_path(emitted_bundle.get("summary_source"))
    return WorkflowProvenanceModel(
        emitPath=emit_path,
        finalSource=final_source,
        continuityMode=continuity_mode,
        summary=_provenance_summary(emit_path, final_source, continuity_mode),
    )


def build_workflow_snapshot(state: Dict[str, Any], continuity_mode: ContinuityMode) -> WorkflowModel:
    final_source = _normalize_final_source(state.get("final_answer_source"))
    provenance = _build_provenance(state, continuity_mode)
    return WorkflowModel(
        layerPlan=_layer_plan_items(state.get("layer_plan", {}), state.get("layer_mode", {})),
        layerMode=state.get("layer_mode", {}) if isinstance(state.get("layer_mode", {}), dict) else {},
        currentLayer=_coerce_str(state.get("current_layer")),
        layerDone=_layer_done_list(state.get("layer_done", {})),
        agentSteps=_build_agent_steps(
            state.get("layer_plan", {}),
            state.get("layer_done", {}),
            state.get("fanout_targets", []),
        ),
        fusionSteps=_build_fusion_steps(state, final_source),
        finalSource=final_source,
        provenanceNote=provenance.summary,
        provenance=provenance,
    )


def build_assistant_turn(state: Dict[str, Any], continuity_mode: ContinuityMode) -> PublicTurn:
    bundle = state.get("emitted_bundle", {})
    if not isinstance(bundle, dict):
        raise ValueError("emitted_bundle missing from completed state")
    answer = _coerce_str(bundle.get("answer"))
    if not answer:
        raise ValueError("emitted_bundle.answer missing from completed state")
    final_source = _normalize_final_source(state.get("final_answer_source"))
    evidence_cards = _normalize_evidence_cards(bundle.get("evidence_cards", []))
    answer_card = AnswerCardModel(
        answer=answer,
        finalSource=final_source,
        confidence=_confidence_label(bundle.get("confidence")),
        evidenceCards=evidence_cards,
        citations=_derive_citations(evidence_cards),
        evidenceCount=len(evidence_cards),
    )
    run_id = _coerce_str(state.get("run_id")) or None
    return PublicTurn(
        id=f"assistant-{uuid.uuid4().hex[:10]}",
        role="assistant",
        text=answer,
        createdAt=_now_label(),
        answerCard=answer_card,
        workflow=build_workflow_snapshot(state, continuity_mode),
        runId=run_id,
        continuityMode=continuity_mode,
    )


def build_thread_summary(
    thread_id: str,
    turns: Sequence[PublicTurn],
    continuity_mode: ContinuityMode,
) -> ChatSessionSummary:
    user_turns = [turn for turn in turns if turn.role == "user"]
    assistant_turns = [turn for turn in turns if turn.role == "assistant" and turn.answerCard]
    latest_turn = turns[-1] if turns else None
    latest_assistant = assistant_turns[-1] if assistant_turns else None
    title_source = user_turns[0].text if user_turns else "New thread"
    preview_source = (
        latest_assistant.answerCard.answer
        if latest_assistant and latest_assistant.answerCard
        else latest_turn.text if latest_turn else "Awaiting first message."
    )
    updated_at = latest_turn.createdAt if latest_turn else _now_label()
    final_source = (
        latest_assistant.answerCard.finalSource
        if latest_assistant and latest_assistant.answerCard
        else "mainline"
    )
    return ChatSessionSummary(
        id=thread_id,
        title=_truncate(title_source or "New thread", 24) or "New thread",
        updatedAt=updated_at,
        preview=_truncate(preview_source or "Awaiting first message.", 72) or "Awaiting first message.",
        finalSource=final_source,  # type: ignore[arg-type]
        phase="Phase F3 / health-debug polish",
        continuityMode=continuity_mode,
    )


def build_new_thread(thread_id: str, continuity_mode: ContinuityMode) -> PublicThreadDetail:
    turns: List[PublicTurn] = []
    summary = ChatSessionSummary(
        id=thread_id,
        title="New thread",
        updatedAt=_now_label(),
        preview="Awaiting first message.",
        finalSource="mainline",
        phase="Phase F3 / health-debug polish",
        continuityMode=continuity_mode,
    )
    return PublicThreadDetail(thread=summary, turns=turns)


def append_turns(
    detail: PublicThreadDetail,
    user_turn: PublicTurn,
    assistant_turn: PublicTurn,
    continuity_mode: ContinuityMode,
) -> PublicThreadDetail:
    turns = [*detail.turns, user_turn, assistant_turn]
    return PublicThreadDetail(
        thread=build_thread_summary(detail.thread.id, turns, continuity_mode),
        turns=turns,
    )


def replay_messages(turns: Sequence[PublicTurn], pending_user_text: str) -> List[tuple[str, str]]:
    # Replay stays anchored to stored transcript text even when a typed structured-input mirror exists.
    messages: List[tuple[str, str]] = []
    for turn in turns:
        role = "assistant" if turn.role == "assistant" else "user"
        messages.append((role, turn.text))
    messages.append(("user", pending_user_text))
    return messages
