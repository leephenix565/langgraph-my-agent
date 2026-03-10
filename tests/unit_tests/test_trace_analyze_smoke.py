import importlib.util
import json
from pathlib import Path


def _load_analyzer():
    script_path = Path(__file__).resolve().parents[2] / "scripts" / "analyze_trace.py"
    spec = importlib.util.spec_from_file_location("analyze_trace_script", script_path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def test_summarize_log_dir_smoke(tmp_path) -> None:
    analyzer = _load_analyzer()

    log_a = tmp_path / "run_a.jsonl"
    log_b = tmp_path / "run_b.jsonl"
    log_a.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "event": "router_ctx",
                        "ctx_messages_len": 10,
                        "full_messages_len": 25,
                    }
                ),
                json.dumps(
                    {
                        "event": "manager_ctx",
                        "ctx_messages_len": 20,
                        "full_messages_len": 40,
                    }
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    log_b.write_text(
        json.dumps(
            {
                "event": "stable_consume",
                "node": "router",
                "stable_summary_len": 123,
                "stable_len": 3,
            }
        )
        + "\n",
        encoding="utf-8",
    )

    summary = analyzer.summarize_log_dir(tmp_path, window_size=20)

    assert "event_counts" in summary
    assert summary["event_counts"]["router_ctx"] == 1
    assert summary["event_counts"]["manager_ctx"] == 1
    assert summary["event_counts"]["stable_consume"] == 1

    router_ctx = summary["ctx_stats"]["router_ctx"]
    assert router_ctx["ctx_messages_len"]["max"] == 10
    assert router_ctx["window_violations"] == 0

    stable = summary["stable_consume"]
    assert stable["count"] == 1
    assert "router" in stable["by_node"]
