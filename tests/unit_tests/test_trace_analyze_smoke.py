import importlib.util
import json
from pathlib import Path


def _load_analyzer():
    script_path = Path(__file__).resolve().parents[2] / "ops" / "regression" / "analyze_trace.py"
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
                json.dumps(
                    {
                        "event": "node_latency",
                        "node": "router",
                        "elapsed_ms": 123.4,
                    }
                ),
                json.dumps(
                    {
                        "event": "agent_error",
                        "node": "agent",
                        "agent_id": "a01_cio_orchestrator",
                        "exception_type": "InternalServerError",
                        "error": "Error code: 502",
                    }
                ),
                '{"bad_json": ',
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    log_b.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "event": "stable_consume",
                        "node": "router",
                        "stable_summary_len": 123,
                        "stable_len": 3,
                    }
                ),
                json.dumps(
                    {
                        "event": "node_latency",
                        "node": "agent",
                        "agent_id": "a01_cio_orchestrator",
                        "elapsed_ms": 45.6,
                    }
                ),
                json.dumps(
                    {
                        "event": "node_latency",
                        "node": "summary",
                        "elapsed_ms": 88.8,
                    }
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    summary = analyzer.summarize_log_dir(tmp_path, window_size=20)

    assert "event_counts" in summary
    assert summary["event_counts"]["router_ctx"] == 1
    assert summary["event_counts"]["manager_ctx"] == 1
    assert summary["event_counts"]["stable_consume"] == 1
    assert summary["event_counts"]["node_latency"] == 3

    router_ctx = summary["ctx_stats"]["router_ctx"]
    assert router_ctx["ctx_messages_len"]["max"] == 10
    assert router_ctx["window_violations"] == 0

    stable = summary["stable_consume"]
    assert stable["count"] == 1
    assert "router" in stable["by_node"]

    latency = summary["latency_profile"]
    assert latency["count"] == 3
    assert latency["by_node"]["router"]["count"] == 1
    assert latency["by_node"]["agent"]["count"] == 1
    assert latency["agent_elapsed_ms"]["a01_cio_orchestrator"]["count"] == 1

    malformed = summary["malformed_jsonl"]
    assert malformed["total"] == 1
    assert malformed["by_file"]["run_a.jsonl"] == 1

    error_summary = summary["error_summary"]
    assert error_summary["count"] == 1
    assert error_summary["by_node"]["agent"] == 1
    assert error_summary["status_code_counts"]["502"] == 1
