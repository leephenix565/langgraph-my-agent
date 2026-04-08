import re
from pathlib import Path


def test_teacher_wiring_calls_local_call_teacher() -> None:
    path = Path("ops/train_eval/a01/generate_a01_teacher_contracts.py")
    text = path.read_text(encoding="utf-8")
    assert "router_gen._call_teacher" not in text
    call_match = re.search(
        r"assistant_text\s*,\s*([A-Za-z_][A-Za-z0-9_]*)\s*,\s*retries\s*,\s*timeouts\s*=\s*_call_teacher\(",
        text,
    )
    assert call_match is not None
    second_var = call_match.group(1)
    assert re.search(
        rf"compute_teacher_observability\(\s*assistant_text\s*,\s*{re.escape(second_var)}\s*,\s*elapsed_ms\s*\)",
        text,
    )
