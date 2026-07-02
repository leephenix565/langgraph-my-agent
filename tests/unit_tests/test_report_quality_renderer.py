import json
import subprocess
import sys
from pathlib import Path

from react_agent.fixed_dag.report_quality_renderer import (
    build_enriched_report_result_from_bundle,
    evaluate_renderer_quality_gate,
    render_improved_fixture,
    report_result_has_unsafe_markers,
    should_enrich_report_result,
)
from react_agent.fixed_dag_contracts import REPORT_INPUT_BUNDLE_SCHEMA_VERSION

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_PATH = (
    REPO_ROOT
    / "tests"
    / "fixtures"
    / "report_quality"
    / "real_e2e_quality_baseline_v1.json"
)


def _evidence_bundle() -> dict:
    routing_context = {
        "schema": "report_routing_context_v1",
        "routing_mode": "full_dag",
        "route_granularity": "full_dag",
        "selected_dimensions": ["value", "market", "risk", "macro"],
        "unselected_dimensions": [],
        "selected_dimension_count": 4,
        "unselected_dimension_count": 0,
    }
    return {
        "schema": "agent_evidence_bundle_v1",
        "question": "请从估值、市场、风险和宏观角度分析 600519.SH。",
        "routing_context": routing_context,
        "selected_scope": routing_context,
        "coverage_by_dimension": {
            "value": {"selected": True, "l2_total": 2, "l3_agent_id": "value_composite"},
            "market": {"selected": True, "l2_total": 0, "l3_agent_id": "market_composite"},
            "risk": {"selected": True, "l2_total": 1, "l3_agent_id": "risk_composite"},
            "macro": {"selected": True, "l2_total": 1, "l3_agent_id": "macro_composite"},
        },
        "quality_summary": {
            "l2_total": 4,
            "l2_complete": 3,
            "l2_partial": 1,
            "l3_total": 4,
            "l3_complete": 1,
            "l3_partial": 3,
        },
        "decision_output": {"decision": "research_hold"},
        "l2_agent_outputs": [
            {
                "agent_id": "value_traditional_valuation",
                "display_name": "传统企业估值",
                "dimension": "value",
                "status": "complete",
                "stance": "-0.35",
                "confidence": 0.8,
                "summary": "传统估值显示安全边际不足。",
                "evidence_items": [{"fact": "合理价值中枢低于当前市值。", "source": "spts_database"}],
            },
            {
                "agent_id": "value_ml_valuation",
                "display_name": "机器学习企业估值",
                "dimension": "value",
                "status": "complete",
                "stance": "0.42",
                "confidence": 0.6,
                "summary": "机器学习估值显示上行空间。",
                "evidence_items": [{"fact": "预测股价中枢高于现价。", "source": "xgboost_model"}],
            },
            {
                "agent_id": "risk_crash",
                "display_name": "股价崩盘风险",
                "dimension": "risk",
                "status": "complete",
                "stance": "risk_gate_member",
                "confidence": 0.8,
                "summary": "崩盘风险模型给出低风险档位。",
                "research_points": [
                    {"claim": "模型把该标的归入 低风险 的崩盘风险档位。"},
                    {"claim": "本次判级的主要解释来自模型特征表，而不是 LLM 主观判断。"},
                ],
                "evidence_items": [{"fact": "风险评分低于高风险阈值。", "source": "crash_risk_model/local_snapshot"}],
            },
            {
                "agent_id": "macro_index_valuation",
                "display_name": "股票指数估值",
                "dimension": "macro",
                "status": "partial",
                "stance": "-0.4",
                "confidence": 0.6,
                "summary": "指数估值和情绪偏高。",
                "research_points": [{"claim": "沪深300 的估值信号偏向 很高。"}],
                "evidence_items": [{"fact": "指数估值处于高分位。", "source": "local_snapshot/lixinger"}],
            },
        ],
        "l3_composite_outputs": [
            {
                "agent_id": "value_composite",
                "display_name": "价值综合",
                "dimension": "value",
                "status": "complete",
                "summary": "spts_database；xgboost_model",
                "confidence": 0.7,
                "members": [
                    {"display_name": "传统企业估值", "stance": "-0.35", "weight": 0.55, "confidence": 0.8, "status": "complete"},
                    {"display_name": "机器学习企业估值", "stance": "0.42", "weight": 0.45, "confidence": 0.6, "status": "complete"},
                ],
            },
            {
                "agent_id": "market_composite",
                "display_name": "市场综合",
                "dimension": "market",
                "status": "partial",
                "summary": "市场确认度不足。",
                "confidence": 0.5,
                "members": [],
            },
            {
                "agent_id": "risk_composite",
                "display_name": "风险综合",
                "dimension": "risk",
                "status": "partial",
                "summary": "风险门未阻断但合规审查缺失。",
                "gate": "manual_review",
                "risk_score": 0.3,
                "confidence": 0.6,
                "members": [],
            },
            {
                "agent_id": "macro_composite",
                "display_name": "宏观综合",
                "dimension": "macro",
                "status": "partial",
                "summary": "宏观调节器提示仓位约束。",
                "regime": "cautious",
                "dimension_weights": {"value": 0.55, "market": 0.45},
                "confidence": 0.5,
                "members": [],
            },
        ],
    }


def _report_input_bundle() -> dict:
    evidence = _evidence_bundle()
    return {
        "schema": REPORT_INPUT_BUNDLE_SCHEMA_VERSION,
        "schema_version": REPORT_INPUT_BUNDLE_SCHEMA_VERSION,
        "status": "complete",
        "agent_task_summaries": [],
        "agent_evidence_bundle": evidence,
        "l2_agent_summaries": [],
        "l3_composite_summaries": [],
        "risk_gate": {"gate": "manual_review"},
        "macro_regulator": {"regime": "cautious"},
        "decision_context": {"decision": "research_hold"},
        "limitations": ["public-safe only"],
        "provenance": {"provider_invoked": False, "external_invoked": False},
    }


def test_enriched_report_has_business_first_core_and_no_core_source_labels() -> None:
    report = build_enriched_report_result_from_bundle(
        question="请分析 600519.SH。",
        agent_evidence_bundle=_evidence_bundle(),
        existing_report_result={"status": "pending_implementation", "limitations": ["模板报告。"]},
    )
    core = report["answer"] + " " + report["sections"][0]["content"]

    assert report["status"] == "complete"
    assert "行动含义" in core
    assert "触发条件" in core
    assert "人工复核" in core
    assert "公告合规审查未被当前 生产策略（production policy） 调用" in json.dumps(
        report,
        ensure_ascii=False,
    )
    assert "spts_database" not in core
    assert "xgboost_model" not in core
    assert "crash_risk_model" not in core


def test_enriched_report_respects_selected_scope_dimensions() -> None:
    evidence = json.loads(json.dumps(_evidence_bundle(), ensure_ascii=False))
    evidence["routing_context"] = {
        "schema": "report_routing_context_v1",
        "routing_mode": "selected",
        "route_granularity": "dimension",
        "selected_dimensions": ["value", "risk"],
        "unselected_dimensions": ["market", "macro"],
        "selected_dimension_count": 2,
        "unselected_dimension_count": 2,
    }
    evidence["selected_scope"] = evidence["routing_context"]
    report = build_enriched_report_result_from_bundle(
        question="请分析 600519.SH。",
        agent_evidence_bundle=evidence,
    )
    section_ids = {section["id"] for section in report["sections"]}
    rendered = json.dumps(report, ensure_ascii=False)

    assert {"value_dimension", "risk_dimension", "unselected_scope"} <= section_ids
    assert "market_dimension" not in section_ids
    assert "macro_dimension" not in section_ids
    assert "本轮 选择路由（selected routing） 的真实分析范围为价值、风险" in report["answer"]
    assert "市场、宏观未被本轮 选择路由（selected routing） 选中" in report["answer"]
    assert "用户问题覆盖估值、市场、风险和宏观四个维度" not in rendered
    assert "市场维度：价格、资金与情绪确认度" not in rendered
    assert "宏观维度：宏观调节器与仓位约束" not in rendered


def test_enriched_report_localizes_public_terminology_and_metrics() -> None:
    evidence = json.loads(json.dumps(_evidence_bundle(), ensure_ascii=False))
    evidence["routing_context"] = {
        "schema": "report_routing_context_v1",
        "routing_mode": "selected",
        "route_granularity": "dimension",
        "selected_dimensions": ["value", "risk"],
        "unselected_dimensions": ["market", "macro"],
        "selected_dimension_count": 2,
        "unselected_dimension_count": 2,
    }
    evidence["selected_scope"] = evidence["routing_context"]
    evidence["decision_output"] = {"decision": "balanced_watch"}
    evidence["l2_agent_outputs"][2]["domain_metrics"] = {
        "risk_bridge": {
            "risk_score": 0.2523,
            "risk_level": "low",
            "trade_date": "2024-12-31",
        },
        "market_snapshot": {
            "current_price": "None",
            "PE": "None",
            "ROE": "None",
        },
    }
    evidence["l2_agent_outputs"][2]["drivers"] = [
        {"name": "risk_score", "value": 0.2523},
        {"name": "valuation_method", "value": "xgboost_pe_montecarlo"},
    ]

    report = build_enriched_report_result_from_bundle(
        question="请分析 600519.SH。",
        agent_evidence_bundle=evidence,
    )
    rendered = json.dumps(report, ensure_ascii=False)

    assert "选择路由（selected routing）" in rendered
    assert "选择范围（selected scope）" in rendered
    assert "完整分析图（full DAG）" in rendered
    assert "均衡观察（balanced_watch）" in rendered
    assert "风险分（risk_score）" in rendered
    assert "当前价格（current_price）" in rendered
    assert "交易日期（trade_date）" in rendered
    assert "估值方法（valuation_method）" in rendered
    assert "每股收益（EPS）" not in rendered
    assert "市盈率（PE）=未提供" in rendered
    assert "净资产收益率（ROE）=未提供" in rendered
    assert "确定性报告增强（deterministic report enrichment）" in rendered
    assert "仅计算路径（compute-only）" in rendered
    assert "未调用 invoke（no-invoke）" in rendered
    assert "未直接调用服务商（no-provider）" in rendered
    assert "未保留原始响应（no-raw-response）" in rendered


def test_enriched_report_risk_compliance_zero_evidence_wording_is_honest() -> None:
    evidence = json.loads(json.dumps(_evidence_bundle(), ensure_ascii=False))
    evidence["l2_agent_outputs"].append(
        {
            "agent_id": "risk_compliance_review",
            "display_name": "公告合规审查",
            "dimension": "risk",
            "status": "partial",
            "confidence": 0.0,
            "summary": "公告合规审查输出无可读证据。",
            "evidence_count": 0,
            "evidence_items": [],
        }
    )
    evidence["agent_runtime_status_by_id"] = {
        "risk_compliance_review": {
            "agent_id": "risk_compliance_review",
            "attempted": True,
            "mapped": True,
            "failed": False,
        }
    }
    report = build_enriched_report_result_from_bundle(
        question="请分析 600519.SH。",
        agent_evidence_bundle=evidence,
    )
    rendered = json.dumps(report, ensure_ascii=False)

    assert "公告合规审查覆盖不足" in rendered
    assert "未获得可用于合规结论的公告证据" in rendered
    assert "不能作为降低风险的强证据" in rendered
    assert "公告合规审查已通过 production compute 映射，可作为风险维度的降权证据" not in rendered


def test_should_enrich_report_result_true_for_template_and_false_for_rich_complete() -> None:
    should, reason = should_enrich_report_result(
        existing_report_result={
            "status": "pending_implementation",
            "title": "研判流程",
            "answer": "固定研判流程 pending_implementation 模板报告",
            "sections": [],
            "evidence_cards": [],
            "limitations": [],
        },
        report_input_bundle=_report_input_bundle(),
    )
    assert should is True
    assert reason == "pending_implementation_report"

    rich_report = build_enriched_report_result_from_bundle(
        question="请分析 600519.SH。",
        agent_evidence_bundle=_evidence_bundle(),
    )
    should, reason = should_enrich_report_result(
        existing_report_result=rich_report,
        report_input_bundle=_report_input_bundle(),
    )
    assert should is False
    assert reason == "existing_report_quality_sufficient"


def test_should_enrich_report_result_fails_closed_on_missing_or_unsafe_bundle() -> None:
    should, reason = should_enrich_report_result(
        existing_report_result=None,
        report_input_bundle=None,
    )
    assert should is False
    assert reason == "missing_report_input_bundle"

    unsafe_bundle = dict(_report_input_bundle())
    unsafe_bundle["limitations"] = ["contains raw_response marker"]
    should, reason = should_enrich_report_result(
        existing_report_result=None,
        report_input_bundle=unsafe_bundle,
    )
    assert should is False
    assert reason.startswith("invalid_report_input_bundle:")


def test_report_result_unsafe_marker_scan_fails_closed() -> None:
    assert report_result_has_unsafe_markers({"answer": "bounded public report"}) is False
    assert report_result_has_unsafe_markers({"answer": "contains raw_response marker"}) is True


def test_renderer_quality_gate_passes_renderer_ready_metrics_and_fails_baseline_metrics() -> None:
    passing = {
        "quality_score": {"total": 29, "max": 45, "normalized": 0.644},
        "template_language": {"template_phrase_count": 0},
        "material_coverage": {"research_points_utilization_ratio": 0.92},
        "answer_section_parity": {
            "parity_ratio": 1.0,
            "limitations_count": 5,
            "evidence_cards_count": 8,
            "sections_count": 7,
        },
        "traceability": {"traceability_ratio": 0.925},
        "public_safety": {"unsafe_scan_pass": True},
        "source_label_leakage": {"core_source_label_leakage_count": 0},
        "action_implication": {"present": True},
        "dimension_sections_present": True,
    }
    assert evaluate_renderer_quality_gate(passing)["passed"] is True

    failing = dict(passing)
    failing["quality_score"] = {"total": 25, "max": 45, "normalized": 0.556}
    failing["template_language"] = {"template_phrase_count": 31}
    assert evaluate_renderer_quality_gate(failing)["passed"] is False


def test_renderer_fixture_mode_writes_gate_result(tmp_path) -> None:
    report = render_improved_fixture(fixture=FIXTURE_PATH, output_dir=tmp_path)
    gate = json.loads((tmp_path / "renderer_gate_result.json").read_text(encoding="utf-8"))

    assert report["status"] == "complete"
    assert gate["should_enrich"] is True
    assert (tmp_path / "run" / "summary.json").exists()
    assert (tmp_path / "run" / "final_report.md").exists()


def test_renderer_cli_fixture_mode(tmp_path) -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "react_agent.fixed_dag.report_quality_renderer",
            "--fixture",
            str(FIXTURE_PATH),
            "--output-dir",
            str(tmp_path / "cli"),
        ],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert (tmp_path / "cli" / "renderer_gate_result.json").exists()
