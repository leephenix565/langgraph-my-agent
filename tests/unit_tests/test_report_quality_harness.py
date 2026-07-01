import importlib.util
import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "quality" / "report_quality_audit.py"
FIXTURE_PATH = (
    REPO_ROOT
    / "tests"
    / "fixtures"
    / "report_quality"
    / "real_e2e_quality_baseline_v1.json"
)


def _load_harness():
    spec = importlib.util.spec_from_file_location("report_quality_audit", SCRIPT_PATH)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT_PATH), *args],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )


def test_fixture_loads_and_is_public_safe() -> None:
    payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    rendered = json.dumps(payload, ensure_ascii=False).lower()

    assert payload["schema"] == "report_quality_baseline_fixture_v1"
    assert payload["metadata"]["public_safe"] is True
    assert payload["metadata"]["external_response_body_retained"] is False
    assert payload["metadata"]["provider_response_body_retained"] is False
    for marker in (
        "api_key",
        "secret",
        "raw_response",
        "raw_provider_response",
        "raw_external_json",
        "traceback",
        "chain-of-thought",
        "/v1/agent/invoke",
        "http://",
        "https://",
    ):
        assert marker not in rendered


def test_fixture_baseline_score_and_counts() -> None:
    harness = _load_harness()
    result = harness.audit_fixture(FIXTURE_PATH)
    material = result["material_coverage"]

    assert result["quality_score"] == {"total": 25, "max": 45, "normalized": 0.556}
    assert material["agents_called"] == 23
    assert material["agents_mapped"] == 22
    assert material["agents_failed"] == 1
    assert material["failed_agents"] == ["risk_compliance_review"]
    assert material["l2_complete"] == 12
    assert material["l2_partial"] == 6
    assert material["l3_complete"] == 1
    assert material["l3_partial"] == 3
    assert material["l4_decision_mapped"] is True
    assert material["l4_report_mapped"] is True


def test_fixture_detects_risk_failure_template_language_and_report_surface_metrics() -> None:
    harness = _load_harness()
    result = harness.audit_fixture(FIXTURE_PATH)

    assert result["risk_compliance_review"] == {
        "failed": True,
        "failure_reason": "adapter_mapping_failed:unsupported_tool_result_schema",
        "impact": (
            "risk compliance is represented as placeholder/coverage limitation; "
            "risk_composite remains partial and depends on remaining risk agents"
        ),
    }
    assert result["template_language"]["template_phrase_count"] > 0
    assert result["material_coverage"]["research_points_total"] >= 0
    assert 0.0 <= result["material_coverage"]["research_points_utilization_ratio"] <= 1.0
    assert result["answer_section_parity"]["sections_count"] == 6
    assert result["answer_section_parity"]["evidence_cards_count"] == 5
    assert result["answer_section_parity"]["limitations_count"] == 4
    assert result["public_safety"]["unsafe_scan_pass"] is True


def test_unsafe_scan_fails_on_synthetic_unsafe_text() -> None:
    harness = _load_harness()
    result = harness.scan_unsafe_texts(
        [
            (
                "synthetic",
                "This synthetic report contains api_key and http://127.0.0.1/internal.",
            )
        ]
    )

    assert result["unsafe_scan_pass"] is False
    assert {item["marker"] for item in result["unsafe_hits"]} >= {"api_key", "http://"}


def test_cli_fixture_smoke_writes_json_and_markdown(tmp_path) -> None:
    output_dir = tmp_path / "fixture-audit"
    result = _run_cli(
        "--fixture",
        str(FIXTURE_PATH),
        "--output-dir",
        str(output_dir),
    )

    assert result.returncode == 0, result.stderr
    output_json = output_dir / "report_quality_audit_result.json"
    output_md = output_dir / "report_quality_audit_result.md"
    assert output_json.is_file()
    assert output_md.is_file()
    payload = json.loads(output_json.read_text(encoding="utf-8"))
    assert payload["quality_score"]["total"] == 25
    assert "Report Quality Audit" in output_md.read_text(encoding="utf-8")


def test_cli_real_artifact_mode_can_run_on_temp_fixture_artifact(tmp_path) -> None:
    fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    artifact_root = tmp_path / "artifact"
    run_dir = artifact_root / "run"
    run_dir.mkdir(parents=True)
    summary = {
        "provenance": {
            "external_compute_demo_called_agents": ["value_ml_valuation"],
            "external_compute_demo_mapped_agents": ["value_ml_valuation"],
            "external_compute_demo_failed_agents": [],
            "external_compute_default_called_agents": [
                "decision_synthesizer",
                "report_generator",
            ],
            "external_compute_default_mapped_agents": [
                "decision_synthesizer",
                "report_generator",
            ],
            "external_compute_default_failed_agents": [],
        },
        "l2_agent_outputs": {
            "value_ml_valuation": {
                "agent_id": "value_ml_valuation",
                "dimension": "value",
                "status": "complete",
            }
        },
        "l3_composite_outputs": {
            "value": {
                "agent_id": "value_composite",
                "dimension": "value",
                "status": "complete",
            }
        },
        "report_result": fixture["report_result"],
        "non_claims": fixture["non_claims"],
        "workflow_step_count": 27,
    }
    evidence_bundle = {
        "quality_summary": fixture["quality_summary"],
        "l2_agent_outputs": [
            {
                "agent_id": "value_ml_valuation",
                "display_name": "机器学习企业估值",
                "dimension": "value",
                "status": "complete",
                "research_points": [
                    {"claim": "模型把该标的归入 低风险 的崩盘风险档位。"}
                ],
            }
        ],
        "l3_composite_outputs": [],
    }
    (run_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False),
        encoding="utf-8",
    )
    (run_dir / "agent_evidence_bundle.json").write_text(
        json.dumps(evidence_bundle, ensure_ascii=False),
        encoding="utf-8",
    )
    (run_dir / "workflow_trace.json").write_text("{}", encoding="utf-8")
    (run_dir / "final_report.md").write_text("# Fixture report\n", encoding="utf-8")
    (artifact_root / "public_agent_report.md").write_text("# Public report\n", encoding="utf-8")

    output_dir = tmp_path / "artifact-audit"
    result = _run_cli(
        "--artifact-root",
        str(artifact_root),
        "--output-dir",
        str(output_dir),
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(
        (output_dir / "report_quality_audit_result.json").read_text(encoding="utf-8")
    )
    assert payload["input_mode"] == "real_artifact"
    assert payload["material_coverage"]["l4_decision_mapped"] is True
    assert payload["material_coverage"]["l4_report_mapped"] is True


def test_cli_real_artifact_flags_l3_contributor_integrity_violation(tmp_path) -> None:
    fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    artifact_root = tmp_path / "direct-artifact"
    artifact_root.mkdir(parents=True)
    summary = {
        "provenance": {
            "external_compute_demo_called_agents": ["risk_composite"],
            "external_compute_demo_mapped_agents": ["risk_composite"],
            "external_compute_demo_failed_agents": [],
        },
        "l2_agent_outputs": {},
        "l3_composite_outputs": {
            "risk": {
                "agent_id": "risk_composite",
                "dimension": "risk",
                "status": "partial",
                "contributing_agents": ["risk_compliance_review"],
            }
        },
        "report_result": fixture["report_result"],
        "non_claims": fixture["non_claims"],
        "workflow_step_count": 27,
    }
    evidence_bundle = {
        "quality_summary": fixture["quality_summary"],
        "l2_agent_outputs": [],
        "l3_composite_outputs": [
            {
                "agent_id": "risk_composite",
                "display_name": "风险综合",
                "dimension": "risk",
                "status": "partial",
                "contributing_agents": ["risk_compliance_review"],
                "evidence_refs": ["risk_compliance_review"],
                "provenance_notes": {
                    "non_contributor_members": [
                        {"agent_id": "risk_compliance_review", "weight": 0.0}
                    ],
                    "member_weight_summary": [
                        {"agent_id": "risk_compliance_review", "weight": 0.0}
                    ],
                },
            }
        ],
    }
    (artifact_root / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False),
        encoding="utf-8",
    )
    (artifact_root / "agent_evidence_bundle.json").write_text(
        json.dumps(evidence_bundle, ensure_ascii=False),
        encoding="utf-8",
    )
    (artifact_root / "workflow_trace.json").write_text("{}", encoding="utf-8")
    (artifact_root / "final_report.md").write_text("# Fixture report\n", encoding="utf-8")

    output_dir = tmp_path / "audit"
    result = _run_cli(
        "--artifact-root",
        str(artifact_root),
        "--output-dir",
        str(output_dir),
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(
        (output_dir / "report_quality_audit_result.json").read_text(encoding="utf-8")
    )
    assert payload["input_mode"] == "real_artifact"
    assert payload["l3_contributor_integrity"]["passed"] is False
    assert {
        item["reason"] for item in payload["l3_contributor_integrity"]["violations"]
    } >= {
        "non_contributor_listed_as_contributor",
        "non_contributor_evidence_ref_retained",
    }


def test_cli_real_artifact_flags_selected_scope_integrity_violation(tmp_path) -> None:
    artifact_root = tmp_path / "selected-scope-artifact"
    artifact_root.mkdir(parents=True)
    report_result = {
        "status": "complete",
        "title": "selected report",
        "answer": "本轮 selected routing 的真实分析范围为价值、风险，但错误展示市场维度。",
        "sections": [
            {"id": "core_decision", "title": "核心结论与行动含义", "content": "行动含义：观察。"},
            {"id": "value_dimension", "title": "价值维度：估值分歧与安全边际", "content": "价值材料。"},
            {"id": "market_dimension", "title": "市场维度：价格、资金与情绪确认度", "content": "市场材料。"},
            {"id": "risk_dimension", "title": "风险维度：风险门与缺失合规证据", "content": "风险材料。"},
            {"id": "unselected_scope", "title": "未覆盖维度", "content": "市场、宏观不在本轮。"},
            {"id": "coverage_and_triggers", "title": "关键证据与观察触发条件", "content": "触发条件。"},
        ],
        "evidence_cards": [{"title": f"证据 {index}", "note": "public-safe"} for index in range(8)],
        "limitations": ["deterministic 边界。", "合规审查边界。", "partial 计数。", "no-invoke no-provider。"],
    }
    summary = {
        "provenance": {
            "external_compute_demo_called_agents": ["value_composite", "risk_composite"],
            "external_compute_demo_mapped_agents": ["value_composite", "risk_composite"],
            "external_compute_demo_failed_agents": [],
        },
        "l2_agent_outputs": {
            "value_ml_valuation": {"agent_id": "value_ml_valuation", "dimension": "value", "status": "complete"},
            "risk_crash": {"agent_id": "risk_crash", "dimension": "risk", "status": "complete"},
        },
        "l3_composite_outputs": {
            "value": {"agent_id": "value_composite", "dimension": "value", "status": "complete"},
            "risk": {"agent_id": "risk_composite", "dimension": "risk", "status": "partial"},
        },
        "report_result": report_result,
        "workflow_step_count": 15,
    }
    evidence_bundle = {
        "routing_context": {
            "schema": "report_routing_context_v1",
            "routing_mode": "selected",
            "selected_dimensions": ["value", "risk"],
            "unselected_dimensions": ["market", "macro"],
        },
        "quality_summary": {"l2_total": 2, "l2_complete": 2, "l3_total": 2, "l3_complete": 1, "l3_partial": 1},
        "decision_output": {"decision": "research_hold"},
        "coverage_by_dimension": {"value": {"selected": True}, "risk": {"selected": True}},
        "l2_agent_outputs": [
            {"agent_id": "value_ml_valuation", "dimension": "value", "status": "complete", "research_points": [{"claim": "价值证据"}]},
            {"agent_id": "risk_crash", "dimension": "risk", "status": "complete", "research_points": [{"claim": "风险证据"}]},
        ],
        "l3_composite_outputs": [
            {"agent_id": "value_composite", "dimension": "value", "status": "complete"},
            {"agent_id": "risk_composite", "dimension": "risk", "status": "partial"},
        ],
    }
    (artifact_root / "summary.json").write_text(json.dumps(summary, ensure_ascii=False), encoding="utf-8")
    (artifact_root / "agent_evidence_bundle.json").write_text(json.dumps(evidence_bundle, ensure_ascii=False), encoding="utf-8")
    (artifact_root / "workflow_trace.json").write_text("{}", encoding="utf-8")
    (artifact_root / "final_report.md").write_text("# selected report\n", encoding="utf-8")

    output_dir = tmp_path / "audit"
    result = _run_cli("--artifact-root", str(artifact_root), "--output-dir", str(output_dir))
    payload = json.loads((output_dir / "report_quality_audit_result.json").read_text(encoding="utf-8"))

    assert result.returncode == 0, result.stderr
    assert payload["selected_scope_integrity"]["passed"] is False
    assert payload["selected_scope_integrity"]["unselected_dimension_overstatement_count"] >= 1
    assert payload["evidence_bundle_completeness"]["passed"] is True


def test_cli_real_artifact_reports_evidence_bundle_completeness_gaps(tmp_path) -> None:
    artifact_root = tmp_path / "incomplete-artifact"
    artifact_root.mkdir(parents=True)
    summary = {
        "provenance": {"external_compute_demo_called_agents": [], "external_compute_demo_mapped_agents": [], "external_compute_demo_failed_agents": []},
        "l2_agent_outputs": {
            "value_ml_valuation": {"agent_id": "value_ml_valuation", "dimension": "value", "status": "complete"}
        },
        "l3_composite_outputs": {},
        "report_result": {
            "status": "complete",
            "title": "report",
            "answer": "行动含义：观察。",
            "sections": [{"id": "core_decision", "title": "核心结论与行动含义", "content": "行动含义：观察。"}],
            "evidence_cards": [],
            "limitations": ["generic"],
        },
    }
    evidence_bundle = {
        "quality_summary": {"l2_total": 1, "l2_complete": 1},
        "decision_output": {"decision": "research_hold"},
        "l2_agent_outputs": [],
        "l3_composite_outputs": [],
    }
    (artifact_root / "summary.json").write_text(json.dumps(summary, ensure_ascii=False), encoding="utf-8")
    (artifact_root / "agent_evidence_bundle.json").write_text(json.dumps(evidence_bundle, ensure_ascii=False), encoding="utf-8")
    (artifact_root / "workflow_trace.json").write_text("{}", encoding="utf-8")
    (artifact_root / "final_report.md").write_text("# report\n", encoding="utf-8")

    output_dir = tmp_path / "audit"
    result = _run_cli("--artifact-root", str(artifact_root), "--output-dir", str(output_dir))
    payload = json.loads((output_dir / "report_quality_audit_result.json").read_text(encoding="utf-8"))

    assert result.returncode == 0, result.stderr
    assert payload["evidence_bundle_completeness"]["passed"] is False
    assert "routing_context" in payload["evidence_bundle_completeness"]["missing_required_fields"]
    assert payload["evidence_bundle_completeness"]["missing_l2_detail_ids"] == ["value_ml_valuation"]


def test_threshold_failure_and_pass_behaviors(tmp_path) -> None:
    fail_result = _run_cli(
        "--fixture",
        str(FIXTURE_PATH),
        "--output-dir",
        str(tmp_path / "threshold-fail"),
        "--fail-on-threshold",
        "--min-score",
        "30",
    )
    pass_result = _run_cli(
        "--fixture",
        str(FIXTURE_PATH),
        "--output-dir",
        str(tmp_path / "threshold-pass"),
        "--fail-on-threshold",
        "--min-score",
        "20",
        "--require-unsafe-pass",
    )

    assert fail_result.returncode == 2
    assert pass_result.returncode == 0, pass_result.stderr


def test_renderer_quality_gate_threshold_behavior(tmp_path) -> None:
    baseline_fail = _run_cli(
        "--fixture",
        str(FIXTURE_PATH),
        "--output-dir",
        str(tmp_path / "renderer-gate-baseline"),
        "--fail-on-threshold",
        "--require-renderer-quality-gate",
    )
    assert baseline_fail.returncode == 2

    rendered_dir = tmp_path / "rendered"
    render = subprocess.run(
        [
            sys.executable,
            "-m",
            "react_agent.fixed_dag.report_quality_renderer",
            "--fixture",
            str(FIXTURE_PATH),
            "--output-dir",
            str(rendered_dir),
        ],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert render.returncode == 0, render.stderr

    gate_pass = _run_cli(
        "--artifact-root",
        str(rendered_dir),
        "--output-dir",
        str(tmp_path / "renderer-gate-pass"),
        "--fail-on-threshold",
        "--require-renderer-quality-gate",
        "--require-unsafe-pass",
    )
    payload = json.loads(
        (tmp_path / "renderer-gate-pass" / "report_quality_audit_result.json").read_text(
            encoding="utf-8"
        )
    )

    assert gate_pass.returncode == 0, gate_pass.stderr
    assert payload["pipeline_quality_score"] == payload["quality_score"]
    assert payload["renderer_quality_gate"]["passed"] is True
    assert payload["source_label_leakage"]["core_source_label_leakage_count"] == 0
    assert payload["action_implication"]["present"] is True


def test_harness_source_has_no_live_runtime_dependencies() -> None:
    source = SCRIPT_PATH.read_text(encoding="utf-8")

    assert "requests" not in source
    assert "httpx" not in source
    assert "load_chat_model" not in source
    assert "os.environ" not in source
    assert "/v1/agent/compute" not in source
