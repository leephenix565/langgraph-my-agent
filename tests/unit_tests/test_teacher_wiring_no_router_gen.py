from pathlib import Path


def test_teacher_wiring_calls_local_call_teacher() -> None:
    path = Path("tools/generate_a01_teacher_contracts.py")
    text = path.read_text(encoding="utf-8")
    assert "router_gen._call_teacher" not in text
    assert "assistant_text, _, retries, timeouts = _call_teacher(" in text
