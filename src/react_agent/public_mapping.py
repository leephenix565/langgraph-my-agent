# ruff: noqa: D103
"""Safe mappings from runtime state to public web contracts."""

from __future__ import annotations

import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, List, Sequence
from urllib.parse import urlparse

from react_agent.agents import AGENT_METADATA, load_metadata_from_dir
from react_agent.fixed_dag_contracts import (
    build_default_fixed_dag_plan,
    build_workflow_snapshot_v2,
)
from react_agent.public_contracts import (
    AnswerCardModel,
    ChatSessionSummary,
    CitationModel,
    ContinuityMode,
    DagStepModel,
    DimensionGroupModel,
    EvidenceCardModel,
    FinalSource,
    PublicThreadDetail,
    PublicTurn,
    StructuredInputModel,
    WorkflowModel,
    WorkflowProvenanceModel,
    WorkflowStageModel,
)

CONFIG_AGENT_DIR = Path(__file__).resolve().parents[2] / "config" / "agents"
STRUCTURED_INPUT_SECTIONS: Sequence[tuple[str, str]] = (
    ("task", "[Task]"),
    ("context", "[Known context]"),
    ("materials", "[Supplemental materials]"),
    ("urlReferences", "[URL references]"),
    ("constraints", "[Constraints]"),
    ("outputPreference", "[Output preference]"),
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
    return "\n\n".join(f"[Material {index + 1}]\n{material}" for index, material in enumerate(materials))


def _compose_url_references_text(url_references: Sequence[str]) -> str:
    return "\n\n".join(f"[URL {index + 1}]\n{url}" for index, url in enumerate(url_references))


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
    del value
    return "reset_skeleton"


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
                note=card.note or "Evidence carried through the reset public adapter.",
            )
        )
    return citations[:3]


def build_user_turn(text: str, structured_input: StructuredInputModel | None = None) -> PublicTurn:
    normalized_text = text.strip()
    normalized_structured = None
    if structured_input is not None:
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


def _agent_title(agent_id: str) -> str:
    _ensure_agent_metadata()
    meta = AGENT_METADATA.get(agent_id)
    return meta.name if meta and meta.name else agent_id


def _workflow_snapshot_dict(state: dict[str, Any]) -> dict[str, Any]:
    raw = state.get("workflow_snapshot")
    if isinstance(raw, dict) and raw.get("schema") == "workflow_snapshot_v2":
        return raw
    plan = state.get("fixed_dag_plan")
    if not isinstance(plan, dict):
        plan = build_default_fixed_dag_plan(_coerce_str(state.get("current_question")))
    return build_workflow_snapshot_v2(
        plan=plan,
        l2_conclusions=state.get("l2_conclusions")
        if isinstance(state.get("l2_conclusions"), dict)
        else None,
        dimension_results=state.get("dimension_results")
        if isinstance(state.get("dimension_results"), dict)
        else None,
        decision_result=state.get("decision_result")
        if isinstance(state.get("decision_result"), dict)
        else None,
        report_result=state.get("report_result")
        if isinstance(state.get("report_result"), dict)
        else None,
        dag_execution=state.get("dag_execution")
        if isinstance(state.get("dag_execution"), dict)
        else None,
        step_results=state.get("dag_step_results")
        if isinstance(state.get("dag_step_results"), dict)
        else None,
        execution_batches=state.get("execution_batches")
        if isinstance(state.get("execution_batches"), list)
        else None,
    )


def build_workflow_snapshot(state: dict[str, Any], continuity_mode: ContinuityMode) -> WorkflowModel:
    snapshot = _workflow_snapshot_dict(state)
    provenance_raw = snapshot.get("provenance", {})
    provenance_raw = provenance_raw if isinstance(provenance_raw, dict) else {}
    provenance = WorkflowProvenanceModel(
        source="reset_skeleton",
        continuityMode=continuity_mode,
        providerInvoked=bool(provenance_raw.get("providerInvoked", False)),
        externalInvoked=bool(provenance_raw.get("externalInvoked", False)),
        executionStatus=_optional_str(provenance_raw.get("executionStatus")),
        fallbackUsed=bool(provenance_raw.get("fallbackUsed", False)),
        limitations=[
            _coerce_str(item)
            for item in provenance_raw.get("limitations", [])
            if _coerce_str(item)
        ]
        if isinstance(provenance_raw.get("limitations", []), list)
        else [],
        summary=(
            "Fixed DAG reset skeleton emitted the public answer. No provider or "
            "external agent endpoint was invoked."
        ),
    )
    return WorkflowModel(
        schema="workflow_snapshot_v2",
        planId=_coerce_str(snapshot.get("planId")) or "reset-fixed-dag-plan-v1",
        stages=[
            WorkflowStageModel(
                key=item.get("key"),  # type: ignore[arg-type]
                title=_coerce_str(item.get("title")) or _coerce_str(item.get("key")),
                stepIds=list(item.get("stepIds", []) or []),
            )
            for item in snapshot.get("stages", [])
            if isinstance(item, dict) and item.get("key")
        ],
        dagSteps=[
            DagStepModel(
                id=_coerce_str(item.get("id")),
                stage=item.get("stage"),  # type: ignore[arg-type]
                agentId=_optional_str(item.get("agentId")),
                dimension=_optional_str(item.get("dimension")),
                title=_coerce_str(item.get("title")) or _coerce_str(item.get("id")),
                summary=_coerce_str(item.get("summary")),
                status=item.get("status", "pending_implementation"),  # type: ignore[arg-type]
            )
            for item in snapshot.get("dagSteps", [])
            if isinstance(item, dict) and item.get("id") and item.get("stage")
        ],
        dimensionGroups=[
            DimensionGroupModel(
                id=_coerce_str(item.get("id")),
                title=_coerce_str(item.get("title")) or _coerce_str(item.get("id")),
                stepIds=list(item.get("stepIds", []) or []),
                status=item.get("status", "pending_implementation"),  # type: ignore[arg-type]
                summary=_coerce_str(item.get("summary")),
            )
            for item in snapshot.get("dimensionGroups", [])
            if isinstance(item, dict) and item.get("id")
        ],
        currentStage=snapshot.get("currentStage"),  # type: ignore[arg-type]
        completedSteps=list(snapshot.get("completedSteps", []) or []),
        executionBatches=[
            [str(step_id) for step_id in batch]
            for batch in snapshot.get("executionBatches", [])
            if isinstance(batch, list)
        ],
        stepResults={
            str(step_id): dict(result)
            for step_id, result in (snapshot.get("stepResults", {}) or {}).items()
            if isinstance(result, dict)
        }
        if isinstance(snapshot.get("stepResults", {}), dict)
        else {},
        finalSource="reset_skeleton",
        provenanceNote=provenance.summary,
        provenance=provenance,
    )


def build_assistant_turn(state: dict[str, Any], continuity_mode: ContinuityMode) -> PublicTurn:
    bundle = state.get("emitted_bundle", {})
    if not isinstance(bundle, dict):
        raise ValueError("emitted_bundle missing from completed state")
    answer = _coerce_str(bundle.get("answer"))
    if not answer:
        raise ValueError("emitted_bundle.answer missing from completed state")
    evidence_cards = _normalize_evidence_cards(bundle.get("evidence_cards", []))
    answer_card = AnswerCardModel(
        answer=answer,
        finalSource=_normalize_final_source(state.get("final_answer_source")),
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
    return ChatSessionSummary(
        id=thread_id,
        title=_truncate(title_source or "New thread", 24) or "New thread",
        updatedAt=updated_at,
        preview=_truncate(preview_source or "Awaiting first message.", 72) or "Awaiting first message.",
        finalSource="reset_skeleton",
        phase="Phase R3 / plan-driven fixed DAG execution",
        continuityMode=continuity_mode,
    )


def build_new_thread(thread_id: str, continuity_mode: ContinuityMode) -> PublicThreadDetail:
    turns: List[PublicTurn] = []
    summary = ChatSessionSummary(
        id=thread_id,
        title="New thread",
        updatedAt=_now_label(),
        preview="Awaiting first message.",
        finalSource="reset_skeleton",
        phase="Phase R3 / plan-driven fixed DAG execution",
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
    messages: List[tuple[str, str]] = []
    for turn in turns:
        role = "assistant" if turn.role == "assistant" else "user"
        messages.append((role, turn.text))
    messages.append(("user", pending_user_text))
    return messages
