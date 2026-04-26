#!/usr/bin/env python
"""Generate RP-1B DeepSeek teacher-proxy route-prior labels."""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol, cast

import httpx

JsonDict = dict[str, Any]
JsonMapping = Mapping[str, Any]

LABEL_SOURCE = "deepseek_teacher_v1"
DEFAULT_MODEL = "deepseek-v4-pro"
DEFAULT_BASE_URL = "https://api.deepseek.com"
SUMMARY_FILE_NAME = "rp1b_deepseek_teacher_v1_summary.json"
EXCLUDED_AGENT_IDS = {"a01_cio_orchestrator", "a02_task_router", "a25_report_center"}
NOT_HUMAN_GOLD_NOTE = "DeepSeek teacher-proxy label; not human gold"
TEACHER_LABELS_WARNING = (
    "DeepSeek teacher labels are model-generated proxy labels, not human/manual gold labels"
)


class HttpClient(Protocol):
    """Minimal sync HTTP client protocol used by the teacher-label generator."""

    def post(
        self,
        url: str,
        *,
        headers: Mapping[str, str],
        json: Mapping[str, object],
        timeout: float,
    ) -> httpx.Response:
        """Post a JSON request and return an HTTP response."""


@dataclass(frozen=True)
class QuestionRecord:
    """Represent one input question for teacher-proxy labeling."""

    case_id: str
    question: str
    tags: list[str]
    label_source: str
    notes: str = ""


@dataclass(frozen=True)
class AgentCatalogItem:
    """Represent one ordinary function agent offered to the teacher model."""

    agent_id: str
    name: str
    description: str
    capabilities: list[str]
    input_type: str
    team: str
    layer: str


def _find_repo_root(start: Path) -> Path:
    for candidate in (start, *start.parents):
        if (candidate / "pyproject.toml").exists():
            return candidate
    raise RuntimeError(f"Could not locate repo root from {start}")


REPO_ROOT = _find_repo_root(Path(__file__).resolve().parent)
SRC_DIR = REPO_ROOT / "src"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


def _as_str_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item.strip() for item in value if isinstance(item, str) and item.strip()]


def _required_str(payload: JsonMapping, key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"record missing required string field: {key}")
    return value.strip()


def _truncate_text(value: str, *, limit: int = 500) -> str:
    if len(value) <= limit:
        return value
    return value[:limit] + "...<truncated>"


def question_record_from_payload(payload: JsonMapping) -> QuestionRecord:
    """Build a QuestionRecord from one input JSON object."""
    notes = payload.get("notes")
    label_source = payload.get("label_source")
    return QuestionRecord(
        case_id=_required_str(payload, "id"),
        question=_required_str(payload, "question"),
        tags=_as_str_list(payload.get("tags")),
        label_source=label_source.strip() if isinstance(label_source, str) and label_source.strip() else "",
        notes=notes.strip() if isinstance(notes, str) else "",
    )


def load_question_records(path: Path, *, max_items: int | None = None) -> list[QuestionRecord]:
    """Load input route-prior questions from JSONL."""
    records: list[QuestionRecord] = []
    with path.open("r", encoding="utf-8-sig") as fh:
        for line_no, line in enumerate(fh, start=1):
            text = line.strip()
            if not text:
                continue
            payload = json.loads(text)
            if not isinstance(payload, dict):
                raise ValueError(f"Input line {line_no} is not a JSON object")
            records.append(question_record_from_payload(cast(JsonMapping, payload)))
            if max_items is not None and len(records) >= max_items:
                break
    return records


def load_agent_catalog() -> list[AgentCatalogItem]:
    """Load ordinary route-profile agents from tracked metadata."""
    from react_agent.agents import (  # type: ignore[import-not-found]
        AGENT_METADATA,
        load_metadata_from_dir,
    )
    from react_agent.route_profile_registry import (  # type: ignore[import-not-found]
        build_route_profile_registry,
    )

    AGENT_METADATA.clear()
    load_metadata_from_dir(REPO_ROOT / "config" / "agents")
    registry = build_route_profile_registry(AGENT_METADATA)
    catalog: list[AgentCatalogItem] = []
    for agent_id in sorted(registry):
        meta = AGENT_METADATA[agent_id]
        catalog.append(
            AgentCatalogItem(
                agent_id=agent_id,
                name=str(meta.name or agent_id).strip(),
                description=str(meta.description or "").strip(),
                capabilities=_as_str_list(list(meta.capabilities or [])),
                input_type=str(meta.input_type or "").strip(),
                team=str(meta.team or "").strip(),
                layer=str(meta.layer or "").strip(),
            )
        )
    return catalog


def catalog_to_prompt_items(catalog: Sequence[AgentCatalogItem]) -> list[JsonDict]:
    """Return compact JSON-serializable agent catalog entries for prompts."""
    return [
        {
            "id": item.agent_id,
            "name": item.name,
            "description": item.description,
            "capabilities": item.capabilities,
            "input_type": item.input_type,
            "team": item.team,
            "layer": item.layer,
        }
        for item in catalog
    ]


def build_system_prompt() -> str:
    """Build the DeepSeek teacher-label system prompt."""
    return (
        "你是金融多智能体路由标注器。给定用户问题和可选 agent catalog，"
        "选择最应该被唤醒的 ordinary function agents。只输出 JSON 对象，"
        "不要输出 chain-of-thought。expected_agents 必须从 catalog 中选择。"
        "不要选择 orchestrator/router/report center。通常选择 2 到 5 个 agent，"
        "除非问题非常窄。多个 agent 相关时，优先选择必须参与的 agent，"
        "不要选择只是泛泛相关的 agent。teacher_reason 必须是简短解释。"
    )


def build_user_prompt(
    record: QuestionRecord,
    catalog: Sequence[AgentCatalogItem],
    *,
    strict_retry: bool = False,
) -> str:
    """Build the DeepSeek teacher-label user prompt."""
    payload = {
        "question": record.question,
        "agent_catalog": catalog_to_prompt_items(catalog),
        "target_json_example": {
            "expected_agents": ["a03_macro_policy", "a18_primary_secondary_valuation"],
            "tags": ["macro", "valuation"],
            "teacher_reason": "问题核心涉及利率路径和估值折现。",
            "teacher_confidence": 0.82,
        },
    }
    retry_instruction = ""
    if strict_retry:
        retry_instruction = "\nReturn only one valid JSON object. Do not include markdown fences."
    return (
        "请基于下面 JSON 输入生成 teacher-proxy route-prior label。"
        "输出必须是 JSON 对象，字段只包括 expected_agents, tags, teacher_reason, "
        f"teacher_confidence。\n{json.dumps(payload, ensure_ascii=False, indent=2)}"
        f"{retry_instruction}"
    )


def build_request_body(
    *,
    model: str,
    system_prompt: str,
    user_prompt: str,
    include_thinking: bool,
) -> JsonDict:
    """Build an OpenAI-compatible DeepSeek chat-completions request body."""
    body: JsonDict = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0,
        "max_tokens": 1200,
        "stream": False,
    }
    if include_thinking:
        body["thinking"] = {"type": "disabled"}
    return body


def parse_teacher_json(text: str) -> JsonDict:
    """Parse the teacher model JSON response content."""
    payload = json.loads(text)
    if not isinstance(payload, dict):
        raise ValueError("teacher response must be a JSON object")
    return cast(JsonDict, payload)


def _response_text(response: httpx.Response) -> str:
    try:
        return _truncate_text(response.text)
    except httpx.ResponseNotRead:
        return "<response text unavailable>"


def extract_response_content(response: httpx.Response) -> str:
    """Extract chat message content from a DeepSeek response."""
    body = response.json()
    if not isinstance(body, dict):
        raise ValueError("DeepSeek response body is not a JSON object")
    choices = body.get("choices")
    if not isinstance(choices, list) or not choices:
        raise ValueError("DeepSeek response missing choices")
    first = choices[0]
    if not isinstance(first, Mapping):
        raise ValueError("DeepSeek response choice is not an object")
    message = first.get("message")
    if not isinstance(message, Mapping):
        raise ValueError("DeepSeek response choice missing message")
    content = message.get("content")
    if not isinstance(content, str) or not content.strip():
        raise ValueError("DeepSeek response message content is empty")
    return content.strip()


def request_teacher_payload(
    client: HttpClient,
    *,
    base_url: str,
    api_key: str,
    model: str,
    record: QuestionRecord,
    catalog: Sequence[AgentCatalogItem],
    timeout: float = 120.0,
) -> JsonDict:
    """Request and parse one DeepSeek teacher label payload."""
    endpoint = f"{base_url.rstrip('/')}/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    system_prompt = build_system_prompt()
    last_error = ""
    for attempt in range(2):
        include_thinking = attempt == 0
        body = build_request_body(
            model=model,
            system_prompt=system_prompt,
            user_prompt=build_user_prompt(record, catalog, strict_retry=attempt > 0),
            include_thinking=include_thinking,
        )
        response = client.post(endpoint, headers=headers, json=body, timeout=timeout)
        if response.status_code >= 400:
            response_text = _response_text(response)
            last_error = f"HTTP {response.status_code}: {response_text}"
            if include_thinking and response.status_code in {400, 422}:
                continue
            raise RuntimeError(last_error)
        try:
            return parse_teacher_json(extract_response_content(response))
        except (json.JSONDecodeError, ValueError) as exc:
            last_error = f"{type(exc).__name__}: {_truncate_text(str(exc))}"
            continue
    raise RuntimeError(last_error or "DeepSeek teacher request failed")


def _dedupe(items: Sequence[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result


def _confidence(value: object) -> float:
    if isinstance(value, int | float):
        return min(max(float(value), 0.0), 1.0)
    return 0.0


def sanitize_teacher_label(
    record: QuestionRecord,
    teacher_payload: JsonMapping,
    *,
    catalog_ids: set[str],
    model: str,
) -> JsonDict:
    """Validate and normalize one teacher-proxy label record."""
    raw_expected = _dedupe(_as_str_list(teacher_payload.get("expected_agents")))
    invalid_agents = [
        agent_id
        for agent_id in raw_expected
        if agent_id not in catalog_ids or agent_id in EXCLUDED_AGENT_IDS
    ]
    expected_agents = [
        agent_id
        for agent_id in raw_expected
        if agent_id in catalog_ids and agent_id not in EXCLUDED_AGENT_IDS
    ]
    teacher_reason = teacher_payload.get("teacher_reason")
    candidate_agents = _as_str_list(teacher_payload.get("candidate_agents_considered"))
    if not candidate_agents:
        candidate_agents = raw_expected
    output: JsonDict = {
        "id": record.case_id,
        "question": record.question,
        "expected_agents": expected_agents,
        "tags": _as_str_list(teacher_payload.get("tags")),
        "label_source": LABEL_SOURCE,
        "teacher_model": model,
        "teacher_reason": _truncate_text(teacher_reason.strip() if isinstance(teacher_reason, str) else ""),
        "teacher_confidence": _confidence(teacher_payload.get("teacher_confidence")),
        "candidate_agents_considered": _dedupe(candidate_agents),
        "invalid_teacher_agents": _dedupe(invalid_agents),
        "notes": NOT_HUMAN_GOLD_NOTE,
    }
    if not expected_agents:
        output["error"] = "teacher returned no valid ordinary expected_agents"
    return output


def build_summary(records: Sequence[JsonMapping], *, model: str) -> JsonDict:
    """Build the DeepSeek teacher-label generation summary."""
    labeled_count = sum(
        1
        for record in records
        if _as_str_list(record.get("expected_agents")) and not str(record.get("error", "") or "")
    )
    invalid_teacher_agent_count = sum(
        len(_as_str_list(record.get("invalid_teacher_agents"))) for record in records
    )
    error_count = sum(1 for record in records if str(record.get("error", "") or ""))
    return {
        "case_count": len(records),
        "labeled_count": labeled_count,
        "error_count": error_count,
        "invalid_teacher_agent_count": invalid_teacher_agent_count,
        "teacher_model": model,
        "label_source": LABEL_SOURCE,
        "quality_conclusion_allowed": False,
        "proxy_label_only": True,
        "proxy_quality_conclusion_only": True,
        "labels_warning": TEACHER_LABELS_WARNING,
    }


def write_jsonl(records: Sequence[JsonMapping], path: Path) -> None:
    """Write teacher-proxy labels as JSONL."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for record in records:
            fh.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")


def write_json(payload: JsonMapping, path: Path) -> None:
    """Write stable JSON to disk."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def generate_teacher_labels(
    records: Sequence[QuestionRecord],
    *,
    catalog: Sequence[AgentCatalogItem],
    client: HttpClient,
    base_url: str,
    api_key: str,
    model: str,
    fail_fast: bool,
) -> list[JsonDict]:
    """Generate DeepSeek teacher-proxy labels for input records."""
    catalog_ids = {item.agent_id for item in catalog}
    outputs: list[JsonDict] = []
    for record in records:
        try:
            payload = request_teacher_payload(
                client,
                base_url=base_url,
                api_key=api_key,
                model=model,
                record=record,
                catalog=catalog,
            )
            outputs.append(
                sanitize_teacher_label(
                    record,
                    payload,
                    catalog_ids=catalog_ids,
                    model=model,
                )
            )
        except Exception as exc:
            if fail_fast:
                raise
            outputs.append(
                {
                    "id": record.case_id,
                    "question": record.question,
                    "expected_agents": [],
                    "tags": record.tags,
                    "label_source": LABEL_SOURCE,
                    "teacher_model": model,
                    "teacher_reason": "",
                    "teacher_confidence": 0.0,
                    "candidate_agents_considered": [],
                    "invalid_teacher_agents": [],
                    "notes": NOT_HUMAN_GOLD_NOTE,
                    "error": f"{type(exc).__name__}: {_truncate_text(str(exc))}",
                }
            )
    return outputs


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Generate RP-1B DeepSeek teacher-proxy labels.")
    parser.add_argument("--input", required=True, help="Input question JSONL path.")
    parser.add_argument(
        "--out",
        default=str(
            REPO_ROOT / "ops" / "regression" / "route_prior" / "out" / "rp1b_deepseek_teacher_v1.jsonl"
        ),
        help="Output teacher-label JSONL path.",
    )
    parser.add_argument("--max-items", type=int, default=None, help="Optional max question count.")
    parser.add_argument(
        "--model",
        default=os.environ.get("DEEPSEEK_TEACHER_MODEL", DEFAULT_MODEL),
        help="DeepSeek teacher model name.",
    )
    parser.add_argument(
        "--base-url",
        default=os.environ.get("DEEPSEEK_BASE_URL", DEFAULT_BASE_URL),
        help="DeepSeek OpenAI-compatible base URL.",
    )
    parser.add_argument(
        "--api-key-env",
        default="DEEPSEEK_API_KEY",
        help="Environment variable containing the DeepSeek API key.",
    )
    parser.add_argument("--fail-fast", action="store_true", help="Stop on the first labeling error.")
    parser.add_argument("--dry-run", action="store_true", help="Print prompt summary without calling DeepSeek.")
    parser.add_argument(
        "--include-agent-catalog-debug",
        action="store_true",
        help="In dry-run mode, print agent ids only; never prints the full prompt.",
    )
    parser.add_argument(
        "--allow-draft-input",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Allow input rows whose label_source is draft_for_human_review.",
    )
    return parser.parse_args()


def _ensure_allowed_input(records: Sequence[QuestionRecord], *, allow_draft_input: bool) -> None:
    if allow_draft_input:
        return
    draft_ids = [
        record.case_id for record in records if record.label_source == "draft_for_human_review"
    ]
    if draft_ids:
        raise ValueError(
            "draft_for_human_review input rows are not allowed: "
            + ", ".join(draft_ids[:10])
        )


def main() -> int:
    """Run the DeepSeek teacher-label generation CLI."""
    args = parse_args()
    records = load_question_records(Path(args.input), max_items=args.max_items)
    _ensure_allowed_input(records, allow_draft_input=bool(args.allow_draft_input))
    catalog = load_agent_catalog()
    model = str(args.model or DEFAULT_MODEL)
    out_path = Path(args.out)
    summary_path = out_path.parent / SUMMARY_FILE_NAME

    if bool(args.dry_run):
        sys.stdout.write(f"case_count: {len(records)}\n")
        sys.stdout.write(f"agent_catalog_size: {len(catalog)}\n")
        sys.stdout.write(f"model: {model}\n")
        sys.stdout.write(f"base_url: {str(args.base_url).rstrip('/')}\n")
        sys.stdout.write("api_key_present: not checked in dry-run\n")
        if bool(args.include_agent_catalog_debug):
            sys.stdout.write("agent_ids: " + ", ".join(item.agent_id for item in catalog) + "\n")
        return 0

    api_key = str(os.environ.get(str(args.api_key_env), "") or "").strip()
    if not api_key:
        sys.stderr.write(f"missing API key env: {args.api_key_env}\n")
        return 2

    with httpx.Client() as client:
        labels = generate_teacher_labels(
            records,
            catalog=catalog,
            client=client,
            base_url=str(args.base_url),
            api_key=api_key,
            model=model,
            fail_fast=bool(args.fail_fast),
        )
    summary = build_summary(labels, model=model)
    write_jsonl(labels, out_path)
    write_json(summary, summary_path)
    sys.stdout.write(f"case_count: {summary['case_count']}\n")
    sys.stdout.write(f"labeled_count: {summary['labeled_count']}\n")
    sys.stdout.write(f"error_count: {summary['error_count']}\n")
    sys.stdout.write(f"invalid_teacher_agent_count: {summary['invalid_teacher_agent_count']}\n")
    sys.stdout.write(f"out: {out_path}\n")
    sys.stdout.write(f"summary: {summary_path}\n")
    if int(summary["error_count"]) > 0:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
