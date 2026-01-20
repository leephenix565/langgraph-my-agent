import os

from react_agent.context import Context


def test_context_init() -> None:
    context = Context(model="openai/gpt-4o-mini")
    assert context.model == "openai/gpt-4o-mini"


def test_context_init_with_env_vars() -> None:
    os.environ["MODEL"] = "openai/gpt-4o-mini"
    context = Context()
    assert context.model == "openai/gpt-4o-mini"


def test_context_init_with_env_vars_and_passed_values() -> None:
    os.environ["MODEL"] = "openai/gpt-4o-mini"
    context = Context(model="openai/gpt-5o-mini")
    assert context.model == "openai/gpt-5o-mini"


def test_context_env_override_int() -> None:
    previous = os.environ.get("MAX_SEARCH_RESULTS")
    os.environ["MAX_SEARCH_RESULTS"] = "7"
    try:
        context = Context()
        assert context.max_search_results == 7
    finally:
        if previous is None:
            os.environ.pop("MAX_SEARCH_RESULTS", None)
        else:
            os.environ["MAX_SEARCH_RESULTS"] = previous
