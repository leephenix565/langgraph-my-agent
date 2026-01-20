import os
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

os.environ.setdefault("TAVILY_API_KEY", "test")
os.environ.setdefault("OPENAI_API_KEY", "test")


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"
