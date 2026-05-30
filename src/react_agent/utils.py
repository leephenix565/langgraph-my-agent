"""Utility & helper functions."""

import os

from langchain.chat_models import init_chat_model
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage
from langchain_openai import ChatOpenAI


def get_message_text(msg: BaseMessage) -> str:
    """Get the text content of a message."""
    content = msg.content
    if isinstance(content, str):
        return content
    elif isinstance(content, dict):
        return content.get("text", "")
    else:
        txts = [c if isinstance(c, str) else (c.get("text") or "") for c in content]
        return "".join(txts).strip()


def load_chat_model(fully_specified_name: str) -> BaseChatModel:
    """Load a chat model from a fully specified name.

    Args:
        fully_specified_name (str): String in the format 'provider/model'.
    """
    if "/" not in fully_specified_name:
        raise ValueError(
            f"model must be in 'provider/model' format (e.g., 'xai/grok-4-1-fast-non-reasoning-latest'), "
            f"got '{fully_specified_name}'"
        )
    provider, model = fully_specified_name.split("/", maxsplit=1)
    if provider == "deepseek":
        return ChatOpenAI(
            model=model,
            base_url=os.environ.get("DEEPSEEK_BASE_URL")
            or os.environ.get("OPENAI_BASE_URL")
            or "https://api.deepseek.com",
            api_key=os.environ.get("DEEPSEEK_API_KEY") or os.environ.get("OPENAI_API_KEY"),
        )
    try:
        return init_chat_model(model, model_provider=provider)
    except (ImportError, ValueError) as exc:
        # Provide a friendlier message when provider integrations are missing.
        hint = (
            f"Provider '{provider}' may require installing langchain-{provider} "
            f"and setting {provider.upper()}_API_KEY"
        )
        raise type(exc)(f"{hint}: {exc}") from exc
