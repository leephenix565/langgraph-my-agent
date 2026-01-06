import os

import pytest


os.environ.setdefault("TAVILY_API_KEY", "test")
os.environ.setdefault("OPENAI_API_KEY", "test")


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"
