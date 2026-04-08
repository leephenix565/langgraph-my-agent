import importlib
import json
import types

import pytest
from google.genai import types as google_types
from langchain_core.messages import HumanMessage

import react_agent.baseline_sidecar as baseline_sidecar_module
from react_agent.context import Context

pytestmark = pytest.mark.anyio


def _reload_baseline_module():
    return importlib.reload(baseline_sidecar_module)


class _FakeGeminiModels:
    def __init__(self, captured):
        self.captured = captured

    def generate_content(self, *, model, contents, config):  # type: ignore[override]
        self.captured["model"] = model
        self.captured["contents"] = contents
        self.captured["config"] = config
        grounding = google_types.GroundingMetadata(
            web_search_queries=["Euro 2024 winner"],
            grounding_chunks=[
                google_types.GroundingChunk(
                    web=google_types.GroundingChunkWeb(
                        domain="www.uefa.com",
                        title="UEFA match report",
                        uri="https://www.uefa.com/example",
                    )
                )
            ],
            grounding_supports=[
                google_types.GroundingSupport(grounding_chunk_indices=[0])
            ],
        )
        candidate = types.SimpleNamespace(grounding_metadata=grounding)
        return types.SimpleNamespace(
            text=json.dumps(
                {
                    "answer": "Spain won Euro 2024.",
                    "key_points": ["Spain beat England in the final."],
                    "evidence_cards": ["model supplied card"],
                    "search_meta": {"coverage_note": "model coverage note"},
                    "confidence": 0.82,
                },
                ensure_ascii=False,
            ),
            candidates=[candidate],
        )


class _FakeGeminiClient:
    def __init__(self, captured):
        self.models = _FakeGeminiModels(captured)


async def test_gemini_provider_uses_grounded_sdk_path_and_records_receipts(monkeypatch) -> None:
    baseline_module = _reload_baseline_module()
    captured = {}
    monkeypatch.setenv("GOOGLE_API_KEY", "test-google-key")

    def _fake_make_client(api_key: str):
        captured["api_key"] = api_key
        return _FakeGeminiClient(captured)

    monkeypatch.setattr(baseline_module, "_make_gemini_client", _fake_make_client)
    monkeypatch.setattr(
        baseline_module,
        "load_chat_model",
        lambda name: (_ for _ in ()).throw(
            AssertionError("generic load_chat_model path should not be used for google_genai baseline")
        ),
    )

    state = {
        "messages": [HumanMessage(content="Who won Euro 2024?")],
        "current_question": "Who won Euro 2024?",
        "thread_summary": "THREAD SHOULD NOT LEAK",
        "stable_findings": [],
        "layer_plan": {"L1": ["SHOULD_NOT_LEAK_LAYER_PLAN"]},
        "analyst_results": {"a25_report_center": {"analysis": "SHOULD_NOT_LEAK_RESULTS"}},
        "ephemeral_results": {"a25_report_center": {"analysis": "SHOULD_NOT_LEAK_EPHEMERAL"}},
        "multi_agent_bundle": {"answer": "SHOULD_NOT_LEAK_MAINLINE_BUNDLE"},
    }
    runtime = types.SimpleNamespace(
        context=Context(
            model="deepseek/deepseek-chat",
            baseline_model="google_genai/gemini-2.5-flash",
            enable_fair_fusion=True,
            baseline_force_search=True,
            run_id="gemini-test",
        )
    )

    out = await baseline_module.run_baseline_sidecar(state, runtime)  # type: ignore[arg-type]

    assert out["baseline_status"] == "ready"
    assert captured["api_key"] == "test-google-key"
    assert captured["model"] == "gemini-2.5-flash"
    assert "SHOULD_NOT_LEAK_LAYER_PLAN" not in captured["contents"]
    assert "SHOULD_NOT_LEAK_RESULTS" not in captured["contents"]
    assert "SHOULD_NOT_LEAK_EPHEMERAL" not in captured["contents"]
    assert "SHOULD_NOT_LEAK_MAINLINE_BUNDLE" not in captured["contents"]
    assert len(captured["config"].tools) == 1
    assert captured["config"].tools[0].google_search is not None
    assert captured["config"].response_mime_type is None

    bundle = out["baseline_bundle"]
    assert bundle["answer"] == "Spain won Euro 2024."
    assert any(
        isinstance(card, dict) and card.get("detail") == "https://www.uefa.com/example"
        for card in bundle["evidence_cards"]
    )
    search_meta = bundle["search_meta"]
    assert search_meta["provider"] == "google_genai"
    assert search_meta["search_binding"] == "gemini_google_search"
    assert search_meta["search_executed"] is True
    assert search_meta["grounding_metadata_present"] is True
    assert search_meta["web_search_queries"] == ["Euro 2024 winner"]
    assert search_meta["grounding_chunk_count"] == 1
    assert search_meta["grounding_support_count"] == 1


async def test_gemini_provider_falls_back_from_global_model_when_baseline_model_blank(monkeypatch) -> None:
    baseline_module = _reload_baseline_module()
    captured = {}
    monkeypatch.setenv("GOOGLE_API_KEY", "test-google-key")
    monkeypatch.setattr(
        baseline_module,
        "_make_gemini_client",
        lambda api_key: _FakeGeminiClient(captured),
    )

    runtime = types.SimpleNamespace(
        context=Context(
            model="google_genai/gemini-2.5-flash",
            baseline_model="",
            enable_fair_fusion=True,
            baseline_force_search=True,
        )
    )
    state = {
        "messages": [HumanMessage(content="baseline question")],
        "current_question": "baseline question",
        "stable_findings": [],
    }

    out = await baseline_module.run_baseline_sidecar(state, runtime)  # type: ignore[arg-type]

    assert out["baseline_status"] == "ready"
    assert captured["model"] == "gemini-2.5-flash"


async def test_gemini_grounding_tool_omits_response_mime_type_but_still_parses_json(monkeypatch) -> None:
    baseline_module = _reload_baseline_module()
    captured = {}
    monkeypatch.setenv("GOOGLE_API_KEY", "test-google-key")

    class _LooseJsonGeminiModels:
        def generate_content(self, *, model, contents, config):  # type: ignore[override]
            captured["model"] = model
            captured["contents"] = contents
            captured["config"] = config
            grounding = google_types.GroundingMetadata(
                web_search_queries=["today news"],
                grounding_chunks=[
                    google_types.GroundingChunk(
                        web=google_types.GroundingChunkWeb(
                            domain="example.com",
                            title="Example citation",
                            uri="https://example.com/citation",
                        )
                    )
                ],
            )
            candidate = types.SimpleNamespace(grounding_metadata=grounding)
            return types.SimpleNamespace(
                text=(
                    'Preface that should be ignored '
                    + json.dumps(
                        {
                            "answer": "grounded baseline answer",
                            "key_points": ["kp1"],
                            "evidence_cards": [],
                            "search_meta": {"coverage_note": "grounded"},
                            "confidence": 0.73,
                        },
                        ensure_ascii=False,
                    )
                    + " trailing note"
                ),
                candidates=[candidate],
            )

    class _LooseJsonGeminiClient:
        def __init__(self):
            self.models = _LooseJsonGeminiModels()

    monkeypatch.setattr(
        baseline_module,
        "_make_gemini_client",
        lambda api_key: _LooseJsonGeminiClient(),
    )
    monkeypatch.setattr(
        baseline_module,
        "load_chat_model",
        lambda name: (_ for _ in ()).throw(
            AssertionError("generic load_chat_model path should not be used for google_genai baseline")
        ),
    )

    runtime = types.SimpleNamespace(
        context=Context(
            baseline_model="google_genai/gemini-3-pro-preview",
            enable_fair_fusion=True,
            baseline_force_search=True,
            run_id="gemini-json-compat",
        )
    )
    state = {
        "messages": [HumanMessage(content="summarize today")],
        "current_question": "summarize today",
        "stable_findings": [],
    }

    out = await baseline_module.run_baseline_sidecar(state, runtime)  # type: ignore[arg-type]

    assert captured["config"].tools[0].google_search is not None
    assert captured["config"].response_mime_type is None
    assert out["baseline_status"] == "ready"
    assert out["baseline_bundle"]["answer"] == "grounded baseline answer"
    assert out["baseline_bundle"]["search_meta"]["provider"] == "google_genai"
    assert out["baseline_bundle"]["search_meta"]["search_binding"] == "gemini_google_search"
    assert out["baseline_bundle"]["search_meta"]["search_executed"] is True
