"""Define the configurable parameters for the multi-agent graph."""

from __future__ import annotations

import os
import warnings
from dataclasses import dataclass, field, fields
from typing import Annotated, Dict

from . import prompts


@dataclass(kw_only=True)
class Context:
    """Shared context injected into every node."""

    model: Annotated[str, {"__template_metadata__": {"kind": "llm"}}] = field(
        default="deepseek/deepseek-chat",
        metadata={"description": "Underlying chat model (provider/model)."},
    )
    router_model: str = field(
        default="",
        metadata={
            "description": "Optional override for the Router model (provider/model). "
            "If empty, the Router uses `model`."
        },
    )
    router_openai_base_url: str = field(
        default="",
        metadata={
            "description": "Optional OpenAI-compatible base URL for Router-only calls. "
            "If empty, Router uses global OPENAI_BASE_URL."
        },
    )
    router_openai_api_key: str = field(
        default="",
        metadata={
            "description": "Optional OpenAI API key for Router-only calls. "
            "If empty, Router uses global OPENAI_API_KEY."
        },
    )
    run_id: str = field(
        default="",
        metadata={"description": "Optional run identifier for tracing/logging."},
    )
    system_prompt: str = field(
        default=prompts.MANAGER_SYSTEM_PROMPT,
        metadata={
            "description": "Top-level system prompt for the Manager agent. "
            "Router/Analyst prompts are sourced from prompts.py."
        },
    )
    analyst_profiles: Dict[str, str] = field(
        default_factory=lambda: prompts.ANALYST_PROFILES.copy(),
        metadata={"description": "Per-analyst system prompts keyed by analyst id."},
    )
    max_search_results: int = field(
        default=10,
        metadata={
            "description": "The maximum number of search results to return for each search query."
        },
    )

    def __post_init__(self) -> None:
        """Fetch env vars for attributes that were not passed as args."""
        for f in fields(self):
            if not f.init or not isinstance(f.default, str):
                continue

            if getattr(self, f.name) == f.default:
                setattr(self, f.name, os.environ.get(f.name.upper(), f.default))

        if not self.router_model:
            self.router_model = self.model

        max_env = os.environ.get("MAX_SEARCH_RESULTS")
        if max_env is None:
            return
        max_field = next((f for f in fields(self) if f.name == "max_search_results"), None)
        default_max = max_field.default if max_field and isinstance(max_field.default, int) else 10
        if self.max_search_results != default_max:
            return
        try:
            parsed = int(str(max_env).strip())
        except (TypeError, ValueError):
            warnings.warn(
                f"Invalid MAX_SEARCH_RESULTS='{max_env}', using default {default_max}.",
                RuntimeWarning,
            )
            return
        if parsed <= 0:
            warnings.warn(
                f"Invalid MAX_SEARCH_RESULTS='{max_env}', using default {default_max}.",
                RuntimeWarning,
            )
            return
        self.max_search_results = parsed
