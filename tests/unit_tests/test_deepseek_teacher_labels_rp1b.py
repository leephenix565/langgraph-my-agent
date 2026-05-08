from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import httpx
import pytest

from ops.regression.route_prior.generate_deepseek_teacher_labels import (
    LABEL_SOURCE,
    AgentCatalogItem,
    QuestionRecord,
    build_request_body,
    build_summary,
    build_system_prompt,
    build_user_prompt,
    generate_teacher_labels,
    load_question_records,
    parse_teacher_json,
    request_teacher_payload,
    sanitize_teacher_label,
)


class FakeClient:
    """Fake sync HTTP client for network-free DeepSeek tests."""

    def __init__(self, responses: list[httpx.Response]) -> None:
        self.responses = responses
        self.requests: list[dict[str, object]] = []

    def post(
        self,
        url: str,
        *,
        headers: Mapping[str, str],
        json: Mapping[str, object],
        timeout: float,
    ) -> httpx.Response:
        self.requests.append(
            {
                "url": url,
                "headers": headers,
                "json": json,
                "timeout": timeout,
            }
        )
        if not self.responses:
            raise AssertionError("unexpected extra fake request")
        return self.responses.pop(0)


def _catalog() -> list[AgentCatalogItem]:
    return [
        AgentCatalogItem(
            agent_id="a03_macro_policy",
            name="Macro Policy",
            description="Macro policy and rates analysis",
            capabilities=["macro", "rates"],
            input_type="question",
            team="macro",
            layer="L2",
        ),
        AgentCatalogItem(
            agent_id="a18_primary_secondary_valuation",
            name="Valuation",
            description="Primary and secondary market valuation",
            capabilities=["valuation"],
            input_type="question",
            team="valuation",
            layer="L3",
        ),
    ]


def _record() -> QuestionRecord:
    return QuestionRecord(
        case_id="case-1",
        question="如果利率上行，成长股估值压力如何？",
        tags=["macro"],
        label_source="draft_for_human_review",
    )


def _teacher_response(payload: dict[str, Any]) -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "choices": [
                {
                    "message": {
                        "content": json.dumps(payload, ensure_ascii=False),
                    }
                }
            ]
        },
    )


def test_prompt_construction_requires_json_and_catalog() -> None:
    system_prompt = build_system_prompt()
    user_prompt = build_user_prompt(_record(), _catalog())

    assert "JSON" in system_prompt
    assert "JSON" in user_prompt
    assert "expected_agents" in user_prompt
    assert "a03_macro_policy" in user_prompt
    assert "chain-of-thought" in system_prompt


def test_request_body_uses_json_output_and_optional_thinking() -> None:
    body = build_request_body(
        model="deepseek-v4-pro",
        system_prompt="system JSON",
        user_prompt="user JSON",
        include_thinking=True,
    )
    retry_body = build_request_body(
        model="deepseek-v4-pro",
        system_prompt="system JSON",
        user_prompt="user JSON",
        include_thinking=False,
    )

    assert body["response_format"] == {"type": "json_object"}
    assert body["thinking"] == {"type": "disabled"}
    assert "thinking" not in retry_body


def test_parse_teacher_json_rejects_non_object() -> None:
    assert parse_teacher_json('{"expected_agents":["a03_macro_policy"]}') == {
        "expected_agents": ["a03_macro_policy"]
    }
    with pytest.raises(ValueError, match="JSON object"):
        parse_teacher_json('["a03_macro_policy"]')


def test_sanitize_teacher_label_filters_invalid_and_excluded_agents() -> None:
    output = sanitize_teacher_label(
        _record(),
        {
            "expected_agents": [
                "a03_macro_policy",
                "a01_cio_orchestrator",
                "missing_agent",
                "a03_macro_policy",
            ],
            "tags": ["macro"],
            "teacher_reason": "涉及宏观利率。",
            "teacher_confidence": 1.2,
        },
        catalog_ids={"a03_macro_policy", "a18_primary_secondary_valuation"},
        model="deepseek-v4-pro",
    )

    assert output["label_source"] == LABEL_SOURCE
    assert output["quality_conclusion_allowed"] is False
    assert output["expected_agents"] == ["a03_macro_policy"]
    assert output["invalid_teacher_agents"] == ["a01_cio_orchestrator", "missing_agent"]
    assert output["teacher_confidence"] == 1.0
    assert "error" not in output


def test_sanitize_teacher_label_marks_empty_valid_agents_as_error() -> None:
    output = sanitize_teacher_label(
        _record(),
        {
            "expected_agents": ["missing_agent"],
            "teacher_reason": "未知 agent。",
            "teacher_confidence": 0.3,
        },
        catalog_ids={"a03_macro_policy"},
        model="deepseek-v4-pro",
    )

    assert output["expected_agents"] == []
    assert output["invalid_teacher_agents"] == ["missing_agent"]
    assert output["error"] == "teacher returned no valid ordinary expected_agents"


def test_request_teacher_payload_retries_without_thinking() -> None:
    client = FakeClient(
        [
            httpx.Response(400, text="unknown field thinking"),
            _teacher_response(
                {
                    "expected_agents": ["a03_macro_policy"],
                    "tags": ["macro"],
                    "teacher_reason": "涉及利率。",
                    "teacher_confidence": 0.8,
                }
            ),
        ]
    )

    payload = request_teacher_payload(
        client,
        base_url="https://api.deepseek.com",
        api_key="redacted",
        model="deepseek-v4-pro",
        record=_record(),
        catalog=_catalog(),
    )

    assert payload["expected_agents"] == ["a03_macro_policy"]
    assert len(client.requests) == 2
    first_body = client.requests[0]["json"]
    second_body = client.requests[1]["json"]
    assert isinstance(first_body, Mapping)
    assert isinstance(second_body, Mapping)
    assert "thinking" in first_body
    assert "thinking" not in second_body


def test_generate_teacher_labels_continues_on_case_error() -> None:
    client = FakeClient([httpx.Response(500, text="server error")])

    outputs = generate_teacher_labels(
        [_record()],
        catalog=_catalog(),
        client=client,
        base_url="https://api.deepseek.com",
        api_key="redacted",
        model="deepseek-v4-pro",
        fail_fast=False,
    )

    assert outputs[0]["expected_agents"] == []
    assert outputs[0]["label_source"] == LABEL_SOURCE
    assert outputs[0]["quality_conclusion_allowed"] is False
    assert "HTTP 500" in outputs[0]["error"]


def test_build_summary_marks_deepseek_labels_proxy_only() -> None:
    summary = build_summary(
        [
            {
                "expected_agents": ["a03_macro_policy"],
                "invalid_teacher_agents": ["missing_agent"],
            },
            {
                "expected_agents": [],
                "invalid_teacher_agents": [],
                "error": "no valid agents",
            },
        ],
        model="deepseek-v4-pro",
    )

    assert summary["case_count"] == 2
    assert summary["labeled_count"] == 1
    assert summary["error_count"] == 1
    assert summary["invalid_teacher_agent_count"] == 1
    assert summary["quality_conclusion_allowed"] is False
    assert summary["proxy_label_only"] is True


def test_load_question_records_reads_utf8_sig_jsonl(tmp_path: Path) -> None:
    dataset = tmp_path / "questions.jsonl"
    dataset.write_text(
        '\ufeff{"id":"case-1","question":"q","tags":["macro"],'
        '"label_source":"draft_for_human_review"}\n',
        encoding="utf-8",
    )

    records = load_question_records(dataset)

    assert len(records) == 1
    assert records[0].case_id == "case-1"
    assert records[0].tags == ["macro"]
