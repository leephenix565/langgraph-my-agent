"""Isolated Fair Fusion baseline sidecar scaffold."""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import re
from datetime import UTC, datetime
from typing import Any, Dict, List, Tuple

from langchain_core.messages import AIMessage, HumanMessage
from langgraph.runtime import Runtime

from react_agent import prompts
from react_agent.context import Context
from react_agent.graph_runtime_features import (
    _build_stable_summary,
    _stable_consume_enabled,
    _stable_summary_system_msg,
    _thread_summary_enabled,
    _thread_summary_system_msg,
)
from react_agent.state import State
from react_agent.utils import get_message_text, load_chat_model


def _get_latest_user_question(messages) -> str:
    for msg in reversed(list(messages or [])):
        if isinstance(msg, HumanMessage):
            text = get_message_text(msg)
            if text:
                return text
    return ""


async def _with_temp_openai_env(base_url: str, api_key: str, fn):
    had_base = "OPENAI_BASE_URL" in os.environ
    old_base = os.environ.get("OPENAI_BASE_URL")
    had_key = "OPENAI_API_KEY" in os.environ
    old_key = os.environ.get("OPENAI_API_KEY")
    if base_url:
        os.environ["OPENAI_BASE_URL"] = base_url
    if api_key:
        os.environ["OPENAI_API_KEY"] = api_key
    try:
        return await fn()
    finally:
        if base_url:
            if had_base:
                os.environ["OPENAI_BASE_URL"] = old_base
            else:
                os.environ.pop("OPENAI_BASE_URL", None)
        if api_key:
            if had_key:
                os.environ["OPENAI_API_KEY"] = old_key
            else:
                os.environ.pop("OPENAI_API_KEY", None)


def _resolve_baseline_model_name(runtime: Runtime[Context]) -> str:
    return runtime.context.baseline_model or runtime.context.model


def _split_provider_model(model_name: str) -> Tuple[str, str]:
    if "/" not in model_name:
        raise ValueError(
            f"baseline model must be in 'provider/model' format, got '{model_name}'"
        )
    return model_name.split("/", maxsplit=1)


def _load_google_genai_sdk():
    try:
        from google import genai
        from google.genai import types
    except ImportError as exc:
        raise ImportError(
            "Gemini grounding baseline requires the 'google-genai' package."
        ) from exc
    return genai, types


def _make_gemini_client(api_key: str):
    genai, _types = _load_google_genai_sdk()
    return genai.Client(vertexai=False, api_key=api_key)


def _build_baseline_messages(state: State, runtime: Runtime[Context], question: str) -> List[Dict[str, str]]:
    force_search_requested = bool(runtime.context.baseline_force_search)
    msgs: List[Dict[str, str]] = [
        {"role": "system", "content": prompts.BASELINE_SIDECAR_SYSTEM_PROMPT}
    ]
    if _stable_consume_enabled():
        stable_summary = _build_stable_summary(state)
        if stable_summary:
            msgs.append(_stable_summary_system_msg(stable_summary))
    thread_summary = state.get("thread_summary", "")
    if _thread_summary_enabled() and thread_summary:
        msgs.append(_thread_summary_system_msg(thread_summary))
    msgs.append(
        {
            "role": "user",
            "content": json.dumps(
                {
                    "question": question,
                    "force_search_requested": force_search_requested,
                },
                ensure_ascii=False,
            ),
        }
    )
    return msgs


def _extract_json(text: str) -> str | None:
    try:
        json.loads(text)
        return text
    except Exception:
        match = re.search(r"\{.*\}", text, flags=re.S)
        return match.group(0) if match else None


def _normalize_evidence_cards(raw_cards: Any) -> List[Any]:
    cards: List[Any] = []
    if not isinstance(raw_cards, list):
        return cards
    for item in raw_cards:
        if isinstance(item, str):
            text = item.strip()
            if text:
                cards.append(text)
        elif isinstance(item, dict):
            title = str(item.get("title", "")).strip()
            detail = str(item.get("detail", "")).strip()
            normalized: Dict[str, str] = {}
            if title:
                normalized["title"] = title
            if detail:
                normalized["detail"] = detail
            if normalized:
                cards.append(normalized)
    return cards


def _merge_evidence_cards(*groups: List[Any]) -> List[Any]:
    merged: List[Any] = []
    seen = set()
    for group in groups:
        for item in group:
            if isinstance(item, dict):
                key = json.dumps(item, ensure_ascii=False, sort_keys=True)
            else:
                key = f"str::{item}"
            if key in seen:
                continue
            seen.add(key)
            merged.append(item)
    return merged


def _extract_gemini_text(response: Any) -> str:
    text = getattr(response, "text", "")
    if isinstance(text, str) and text.strip():
        return text.strip()
    candidates = getattr(response, "candidates", None) or []
    if not candidates:
        return ""
    content = getattr(candidates[0], "content", None)
    parts = getattr(content, "parts", None) or []
    chunks: List[str] = []
    for part in parts:
        part_text = getattr(part, "text", "")
        if isinstance(part_text, str) and part_text:
            chunks.append(part_text)
    return "".join(chunks).strip()


def _extract_gemini_grounding_metadata(response: Any) -> Any:
    candidates = getattr(response, "candidates", None) or []
    if not candidates:
        return None
    return getattr(candidates[0], "grounding_metadata", None)


def _extract_gemini_evidence_cards(response: Any) -> List[Any]:
    grounding = _extract_gemini_grounding_metadata(response)
    if grounding is None:
        return []
    cards: List[Any] = []
    for chunk in getattr(grounding, "grounding_chunks", None) or []:
        web = getattr(chunk, "web", None)
        if web is None:
            continue
        title = str(getattr(web, "title", "") or getattr(web, "domain", "") or "grounding_source").strip()
        uri = str(getattr(web, "uri", "") or "").strip()
        if not uri:
            continue
        cards.append({"title": title, "detail": uri})
    return cards


def _build_gemini_search_receipt(response: Any, force_search_requested: bool) -> Dict[str, Any]:
    grounding = _extract_gemini_grounding_metadata(response)
    web_search_queries = list(getattr(grounding, "web_search_queries", None) or []) if grounding else []
    grounding_chunks = list(getattr(grounding, "grounding_chunks", None) or []) if grounding else []
    grounding_supports = list(getattr(grounding, "grounding_supports", None) or []) if grounding else []
    search_entry_point_present = bool(getattr(grounding, "search_entry_point", None)) if grounding else False
    grounding_metadata_present = grounding is not None
    search_executed = grounding_metadata_present and (
        bool(web_search_queries) or bool(grounding_chunks) or bool(grounding_supports) or search_entry_point_present
    )
    if search_executed:
        coverage_note = "Gemini Google Search grounding metadata present in response."
    elif force_search_requested:
        coverage_note = (
            "Gemini Google Search grounding was requested, but the response did not expose grounding metadata."
        )
    else:
        coverage_note = "Gemini baseline run without Google Search grounding request."
    return {
        "provider": "google_genai",
        "search_binding": "gemini_google_search" if force_search_requested else "none",
        "search_executed": search_executed,
        "grounding_metadata_present": grounding_metadata_present,
        "web_search_queries": [str(item) for item in web_search_queries if str(item).strip()],
        "grounding_chunk_count": len(grounding_chunks),
        "grounding_support_count": len(grounding_supports),
        "search_entry_point_present": search_entry_point_present,
        "coverage_note": coverage_note,
    }


def _normalize_baseline_bundle(
    parsed: Dict[str, Any] | None,
    *,
    question: str,
    force_search_requested: bool,
    provider: str = "",
    search_receipt: Dict[str, Any] | None = None,
    extra_evidence_cards: List[Any] | None = None,
    error: str = "",
) -> Dict[str, Any]:
    parsed = parsed or {}
    retrieved_at_utc = datetime.now(tz=UTC).isoformat()
    search_meta_raw = parsed.get("search_meta", {})
    coverage_note = ""
    if isinstance(search_meta_raw, dict):
        coverage_note = str(search_meta_raw.get("coverage_note", "")).strip()
    if not coverage_note and isinstance(search_receipt, dict):
        coverage_note = str(search_receipt.get("coverage_note", "")).strip()
    if not coverage_note:
        if force_search_requested:
            coverage_note = (
                "force_search_requested=true in FF-2A scaffold; provider-native search "
                "binding is requested in metadata only."
            )
        else:
            coverage_note = "FF-2A scaffold baseline without explicit force-search request."
    confidence_raw = parsed.get("confidence", 0.0)
    try:
        confidence = float(confidence_raw)
    except (TypeError, ValueError):
        confidence = 0.0
    normalized_cards = _normalize_evidence_cards(parsed.get("evidence_cards", []))
    evidence_cards = _merge_evidence_cards(extra_evidence_cards or [], normalized_cards)
    search_meta: Dict[str, Any] = {
        "force_search_requested": force_search_requested,
        "retrieved_at_utc": retrieved_at_utc,
        "coverage_note": coverage_note,
    }
    if provider:
        search_meta["provider"] = provider
    if isinstance(search_receipt, dict):
        for key, value in search_receipt.items():
            if key in {"force_search_requested", "retrieved_at_utc", "coverage_note", "provider"}:
                continue
            search_meta[key] = value
        if "provider" in search_receipt and search_receipt.get("provider"):
            search_meta["provider"] = search_receipt["provider"]
    bundle: Dict[str, Any] = {
        "question": question,
        "answer": str(parsed.get("answer", "") or ""),
        "key_points": [
            str(item).strip()
            for item in parsed.get("key_points", [])
            if isinstance(item, str) and str(item).strip()
        ],
        "evidence_cards": evidence_cards,
        "search_meta": search_meta,
        "confidence": confidence,
    }
    if error:
        bundle["error"] = error
    return bundle


async def _invoke_generic_baseline_model(
    runtime: Runtime[Context], question: str, msgs: List[Dict[str, str]]
) -> AIMessage:
    model_name = _resolve_baseline_model_name(runtime)
    metadata = {
        "run_id": runtime.context.run_id or "",
        "node_name": "baseline_sidecar",
        "question_hash": hashlib.sha256(question.encode("utf-8")).hexdigest()[:12] if question else "",
    }
    tags = ["react_agent", "baseline_sidecar"] + (
        [f"run_id:{runtime.context.run_id}"] if runtime.context.run_id else []
    )

    async def _invoke() -> AIMessage:
        model = load_chat_model(model_name)
        return await model.ainvoke(msgs, config={"metadata": metadata, "tags": tags})

    if runtime.context.baseline_openai_base_url:
        return await _with_temp_openai_env(
            runtime.context.baseline_openai_base_url,
            runtime.context.baseline_openai_api_key,
            _invoke,
        )
    return await _invoke()


async def _invoke_gemini_grounded_model(
    runtime: Runtime[Context], question: str, msgs: List[Dict[str, str]]
) -> Any:
    _genai, types = _load_google_genai_sdk()
    model_name = _resolve_baseline_model_name(runtime)
    _provider, bare_model = _split_provider_model(model_name)
    api_key = (os.environ.get("GOOGLE_API_KEY", "") or "").strip()
    if not api_key:
        raise ValueError(
            "GOOGLE_API_KEY is required for Gemini Developer API baseline grounding."
        )

    system_instruction = ""
    if msgs and isinstance(msgs[0], dict):
        system_instruction = str(msgs[0].get("content", "") or "")
    contents = "\n\n".join(
        str(msg.get("content", "") or "")
        for msg in msgs[1:]
        if isinstance(msg, dict) and str(msg.get("content", "") or "").strip()
    )
    tools = [types.Tool(google_search=types.GoogleSearch())] if runtime.context.baseline_force_search else None
    config_kwargs: Dict[str, Any] = {
        "system_instruction": system_instruction or prompts.BASELINE_SIDECAR_SYSTEM_PROMPT,
        "tools": tools,
    }
    # Gemini grounding/search rejects tool use when JSON response mode is forced.
    # Keep JSON constrained by prompt and parse response.text locally instead.
    if not tools:
        config_kwargs["response_mime_type"] = "application/json"
    config = types.GenerateContentConfig(**config_kwargs)

    def _call():
        client = _make_gemini_client(api_key)
        return client.models.generate_content(
            model=bare_model,
            contents=contents or question,
            config=config,
        )

    return await asyncio.to_thread(_call)


async def run_baseline_sidecar(
    state: State, runtime: Runtime[Context]
) -> Dict[str, object]:
    """Run isolated baseline shadow scaffolding without affecting the mainline graph."""
    if not runtime.context.enable_fair_fusion:
        return {"baseline_status": "disabled", "baseline_bundle": {}}

    question = state.get("current_question") or _get_latest_user_question(state.get("messages", []))
    force_search_requested = bool(runtime.context.baseline_force_search)
    msgs = _build_baseline_messages(state, runtime, question)
    model_name = _resolve_baseline_model_name(runtime)
    provider_name = ""
    try:
        provider_name, _bare_model = _split_provider_model(model_name)
    except Exception:
        provider_name = ""
    try:
        if provider_name == "google_genai":
            response = await _invoke_gemini_grounded_model(runtime, question, msgs)
            raw_text = _extract_gemini_text(response)
            search_receipt = _build_gemini_search_receipt(response, force_search_requested)
            extra_evidence_cards = _extract_gemini_evidence_cards(response)
        else:
            response = await _invoke_generic_baseline_model(runtime, question, msgs)
            raw_text = get_message_text(response)
            search_receipt = None
            extra_evidence_cards = []
        json_str = _extract_json(raw_text)
        if not json_str:
            raise ValueError("baseline sidecar did not return a JSON object")
        parsed = json.loads(json_str)
        if not isinstance(parsed, dict):
            raise ValueError("baseline sidecar JSON output must be an object")
        bundle = _normalize_baseline_bundle(
            parsed,
            question=question,
            force_search_requested=force_search_requested,
            provider=provider_name,
            search_receipt=search_receipt,
            extra_evidence_cards=extra_evidence_cards,
        )
        return {"baseline_status": "ready", "baseline_bundle": bundle}
    except Exception as exc:
        bundle = _normalize_baseline_bundle(
            None,
            question=question,
            force_search_requested=force_search_requested,
            provider=provider_name,
            error=f"{type(exc).__name__}: {exc}",
        )
        return {"baseline_status": "error", "baseline_bundle": bundle}
