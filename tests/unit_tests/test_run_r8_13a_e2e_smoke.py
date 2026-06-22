import importlib.util
from pathlib import Path


def _load_runner():
    script_path = (
        Path(__file__).resolve().parents[2]
        / "scripts"
        / "dev"
        / "run_r8_13a_e2e_smoke.py"
    )
    spec = importlib.util.spec_from_file_location("run_r8_13a_e2e_smoke", script_path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def test_render_report_markdown_includes_full_report_result() -> None:
    runner = _load_runner()

    markdown = runner._render_report_markdown(
        {
            "title": "测试报告",
            "status": "complete",
            "answer": "主回答",
            "sections": [
                {
                    "id": "value",
                    "title": "价值分析",
                    "content": "估值细节",
                }
            ],
            "evidence_cards": [
                {
                    "title": "估值证据",
                    "note": "PE 与目标价",
                }
            ],
            "limitations": ["显式开关路径。"],
        },
        "fallback answer",
    )

    assert "# 测试报告" in markdown
    assert "Status: `complete`" in markdown
    assert "主回答" in markdown
    assert "### 价值分析 (`value`)" in markdown
    assert "估值细节" in markdown
    assert "- **估值证据**: PE 与目标价" in markdown
    assert "- 显式开关路径。" in markdown
    assert "fallback answer" not in markdown


def test_render_report_markdown_falls_back_to_final_answer() -> None:
    runner = _load_runner()

    markdown = runner._render_report_markdown({}, "fallback answer")

    assert markdown.startswith("# Fixed DAG report")
    assert "fallback answer" in markdown


def test_fake_invoke_accepts_l4_context_kwargs_and_maps_report() -> None:
    runner = _load_runner()
    entry = runner.bridge.DEMO_COMPUTE_SERVICE_REGISTRY["report_generator"]

    result = runner.fake_invoke_external_compute(
        entry,
        question="请分析 600519.SH",
        as_of="2026-06-05",
        request_id="unit-l4-report",
        timeout_seconds=3,
        dimension_results={"value": {"agent_id": "value_composite"}},
        decision_result={"schema": "decision_result_v1", "decision": "defensive_observe"},
        report_result={},
        report_input_bundle={"schema": "report_input_bundle_v1"},
    )

    assert result["status"] == "pass"
    assert result["mapped"]["schema"] == "report_result_v1"
    assert result["mapped"]["sections"][0]["title"] == "综合结论"


def test_summary_from_l3_projects_member_weight_summary() -> None:
    runner = _load_runner()

    summary = runner._summary_from_l3(
        "market",
        {
            "agent_id": "market_composite",
            "dimension": "market",
            "status": "partial",
            "contributing_agents": ["market_stock_technical"],
            "provenance": {
                "member_weight_summary": [
                    {
                        "agent_id": "market_stock_technical",
                        "status": "complete",
                        "weight": 1.0,
                        "confidence": 0.6,
                    },
                    {
                        "agent_id": "market_fund_manager_behavior",
                        "status": "pending_implementation",
                        "weight": 0.0,
                        "confidence": 0.0,
                    },
                ],
            },
        },
    )

    assert summary["member_count"] == 2
    assert [item["agent_id"] for item in summary["members"]] == [
        "market_stock_technical",
        "market_fund_manager_behavior",
    ]
    assert summary["contributing_agents"] == ["market_stock_technical"]
