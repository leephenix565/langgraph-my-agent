"""Define the configurable parameters for the multi-agent graph."""

from __future__ import annotations

import os
import warnings
from dataclasses import dataclass, field, fields
from typing import Annotated, Dict

from . import prompts


def _parse_bool_env(raw: str, *, name: str, default: bool) -> bool:
    value = (raw or "").strip().lower()
    if value in {"1", "true", "on", "yes"}:
        return True
    if value in {"0", "false", "off", "no"}:
        return False
    warnings.warn(
        f"Invalid {name}='{raw}', using default {default}.",
        RuntimeWarning,
    )
    return default


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
    baseline_model: str = field(
        default="",
        metadata={
            "description": "Optional override for the baseline sidecar model (provider/model). "
            "If empty, baseline sidecar uses `model`."
        },
    )
    baseline_openai_base_url: str = field(
        default="",
        metadata={
            "description": "Optional OpenAI-compatible base URL for baseline-sidecar calls. "
            "If empty, baseline sidecar uses the global provider/env path."
        },
    )
    baseline_openai_api_key: str = field(
        default="",
        metadata={
            "description": "Optional OpenAI API key for baseline-sidecar calls. "
            "If empty, baseline sidecar uses the global provider/env path."
        },
    )
    enable_fair_fusion: bool = field(
        default=False,
        metadata={"description": "Enable the isolated baseline sidecar shadow scaffold."},
    )
    baseline_force_search: bool = field(
        default=True,
        metadata={
            "description": "Request force-search behavior in baseline sidecar metadata. "
            "FF-2A records the request but does not hard-bind provider-native search."
        },
    )
    enable_fair_fusion_source_switch: bool = field(
        default=False,
        metadata={
            "description": "Enable final source switching across mainline/baseline/fused emit paths. "
            "Defaults off so the visible answer stays on the mainline path."
        },
    )
    enable_selected_routing: bool = field(
        default=False,
        metadata={
            "description": "Enable provider-free selected fixed DAG routing. "
            "Defaults off so the active graph keeps the full DAG path."
        },
    )
    enable_internal_llm_placeholders: bool = field(
        default=False,
        metadata={
            "description": "Enable default-off internal LLM placeholders for fixed-DAG L2 slots. "
            "Provider failures fall back to deterministic placeholders."
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
        if not self.baseline_model:
            self.baseline_model = self.model

        bool_envs = {
            "enable_fair_fusion": "ENABLE_FAIR_FUSION",
            "baseline_force_search": "BASELINE_FORCE_SEARCH",
            "enable_fair_fusion_source_switch": "ENABLE_FAIR_FUSION_SOURCE_SWITCH",
            "enable_selected_routing": "ENABLE_SELECTED_ROUTING",
            "enable_internal_llm_placeholders": "ENABLE_INTERNAL_LLM_PLACEHOLDERS",
        }
        for field_name, env_name in bool_envs.items():
            field_obj = next((f for f in fields(self) if f.name == field_name), None)
            if field_obj is None or not isinstance(field_obj.default, bool):
                continue
            if getattr(self, field_name) != field_obj.default:
                continue
            raw = os.environ.get(env_name)
            if raw is None:
                continue
            setattr(
                self,
                field_name,
                _parse_bool_env(raw, name=env_name, default=field_obj.default),
            )

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
