from __future__ import annotations

import json

import pytest

from ops.regression.route_prior.run_route_prior_eval import label_case_from_record
from ops.regression.route_prior.run_router_advisory_ab import (
    build_case_record,
    build_summary,
    compare_parsed_outputs,
    load_prediction_artifact,
    parse_side,
    render_advisory_prompt,
    render_baseline_prompt,
    selected_jaccard,
)
from react_agent import prompts
from react_agent.public_contracts import (
    AgentCatalogResponse,
    HealthResponse,
    WorkflowModel,
)

AGENT_CATALOG = {
    "L1": ["a01_cio_orchestrator"],
    "L2": [
        "a03_macro_policy",
        "a04_industry_layout",
        "a05_product_pricing",
        "a14_single_stock_tech",
    ],
    "L3": ["a19_market_risk"],
    "L4": ["a25_report_center"],
}
FORBIDDEN_PUBLIC_FIELDS = {
    "routePrior",
    "route_prior",
    "routeReliability",
    "route_reliability",
    "reliabilityCards",
    "advisory",
    "routeScores",
}


def _raw(selected_l2: list[str], selected_l3: list[str] | None = None) -> str:
    return json.dumps(
        {
            "layers": [
                {
                    "layer": "L1",
                    "mode": "Chain",
                    "selected": ["a01_cio_orchestrator"],
                },
                {"layer": "L2", "mode": "Star", "selected": selected_l2},
                {"layer": "L3", "mode": "Star", "selected": selected_l3 or []},
                {"layer": "L4", "mode": "Chain", "selected": ["a25_report_center"]},
            ],
            "reason": "test",
        }
    )


def _case():
    return label_case_from_record(
        {
            "schema_version": "route_eval_label_v0",
            "id": "ab-case",
            "question": "q",
            "label_source": "manual_gold",
            "quality_conclusion_allowed": True,
            "must_include_agents": ["a03_macro_policy", "a04_industry_layout"],
            "critical_agents": ["a04_industry_layout"],
            "nice_to_have_agents": [],
            "should_not_include_agents": ["a05_product_pricing"],
        }
    )


def _advisory_payload(prompt: str) -> dict:
    marker = "Route prior advisory, non-binding (offline dry-run stub):"
    return json.loads(prompt.split(marker, maxsplit=1)[1].strip())


def _wrong_layer_regression_case():
    return label_case_from_record(
        {
            "schema_version": "route_eval_label_v0",
            "id": "rp3-manual-gold-0004",
            "question": "我只想评估一只股票未来一个月的波动率和回撤预警，不需要基本面分析。",
            "label_source": "manual_gold",
            "quality_conclusion_allowed": True,
            "must_include_agents": ["a19_market_risk"],
            "critical_agents": ["a19_market_risk"],
            "nice_to_have_agents": ["a14_single_stock_tech"],
            "should_not_include_agents": ["a20_fundamental_risk", "a06_financial_reports"],
        }
    )


def test_selected_jaccard_handles_overlap_and_empty_sets() -> None:
    assert selected_jaccard(["a", "b"], ["b", "c"]) == pytest.approx(1 / 3)
    assert selected_jaccard([], []) == pytest.approx(1.0)


def test_ab_comparison_metrics_cover_parser_and_label_deltas() -> None:
    case = _case()
    baseline = parse_side(_raw(["a03_macro_policy"]), AGENT_CATALOG)
    advisory = parse_side(
        _raw(["a03_macro_policy", "a04_industry_layout", "a05_product_pricing"]),
        AGENT_CATALOG,
    )

    comparison = compare_parsed_outputs(
        case=case,
        baseline=baseline,
        advisory=advisory,
        baseline_prompt_chars=100,
        advisory_prompt_chars=145,
    )

    assert comparison["parse_ok_delta"] == 0
    assert comparison["used_default_plan_delta"] == 0
    assert comparison["filtered_agents_delta"] == 0
    assert comparison["l2_truncated_delta"] == 0
    assert comparison["selected_jaccard"] == pytest.approx(3 / 5)
    assert comparison["must_include_recall_delta"] == pytest.approx(0.5)
    assert comparison["critical_agent_miss_delta"] == -1
    assert comparison["negative_selection_delta"] == 1
    assert comparison["prompt_char_delta"] == 45
    assert comparison["token_count_delta"] is None
    assert comparison["latency_ms_delta"] is None


def test_case_record_uses_supplied_predictions_without_live_model() -> None:
    case = _case()
    prediction = {
        "baseline_raw": _raw(["a03_macro_policy"]),
        "advisory_raw": _raw(["a03_macro_policy", "a04_industry_layout"]),
    }

    record = build_case_record(
        case,
        agent_catalog=AGENT_CATALOG,
        prediction=prediction,
    )

    assert record["schema_version"] == "router_advisory_ab_run_v0"
    assert record["mode"] == "network-free"
    assert record["baseline"]["parse_stats"]["parse_ok"] is True
    assert record["advisory"]["parse_stats"]["parse_ok"] is True
    assert record["comparison"]["critical_agent_miss_delta"] == -1
    assert record["comparison"]["selected_jaccard"] < 1.0
    assert record["comparison"]["latency_ms_delta"] is None


def test_noop_prediction_does_not_count_advisory_induced_regression() -> None:
    case = _case()
    record = build_case_record(
        case,
        agent_catalog=AGENT_CATALOG,
        prediction={
            "schema_version": "router_advisory_prediction_v0",
            "advisory_source": "provided_artifact_missing",
            "advisory_applied": False,
            "advisory_status": "provided_artifact_missing",
            "advisory_noop_reason": "noop_no_advisory",
            "baseline": {
                "raw": _raw(["a03_macro_policy", "a04_industry_layout"]),
                "prompt_chars": 100,
                "token_count": 10,
                "latency_ms": 20.0,
            },
            "advisory": {
                "raw": _raw(["a03_macro_policy"]),
                "prompt_chars": 100,
                "token_count": 10,
                "latency_ms": 20.0,
            },
        },
    )

    assert record["advisory_applied"] is False
    assert record["advisory_status"] == "provided_artifact_missing"
    assert record["comparison"]["advisory_comparison_mode"] == "noop_no_advisory"
    assert record["comparison"]["critical_agent_miss_delta"] == 0
    assert record["comparison"]["must_include_recall_delta"] == 0.0
    assert record["comparison"]["selected_jaccard"] == 1.0
    summary = build_summary([record], dataset=__file__)
    assert summary["critical_miss_regressions"] == 0
    assert summary["advisory_applied_count"] == 0
    assert summary["advisory_noop_count"] == 1
    assert summary["advisory_missing_count"] == 1


def test_loaded_noop_prediction_preserves_advisory_metadata(tmp_path) -> None:
    predictions_path = tmp_path / "predictions.jsonl"
    predictions_path.write_text(
        json.dumps(
            {
                "schema_version": "router_advisory_prediction_v0",
                "id": "ab-case",
                "advisory_source": "provided_artifact_disabled",
                "advisory_applied": False,
                "advisory_status": "provided_artifact_disabled",
                "advisory_noop_reason": "noop_no_advisory",
                "baseline": {"raw": _raw(["a03_macro_policy", "a04_industry_layout"])},
                "advisory": {"raw": _raw(["a03_macro_policy"])},
            },
        )
        + "\n",
        encoding="utf-8",
    )

    predictions = load_prediction_artifact(predictions_path)
    record = build_case_record(
        _case(),
        agent_catalog=AGENT_CATALOG,
        prediction=predictions["ab-case"],
    )

    assert record["advisory_applied"] is False
    assert record["advisory_status"] == "provided_artifact_disabled"
    assert record["comparison"]["advisory_comparison_mode"] == "noop_no_advisory"
    assert record["comparison"]["critical_agent_miss_delta"] == 0
    summary = build_summary([record], dataset=tmp_path / "dataset.jsonl")
    assert summary["advisory_applied_count"] == 0
    assert summary["advisory_noop_count"] == 1


def test_legacy_prediction_artifact_schema_still_loads(tmp_path) -> None:
    predictions_path = tmp_path / "predictions.jsonl"
    predictions_path.write_text(
        json.dumps(
            {
                "case_id": "ab-case",
                "baseline_raw": _raw(["a03_macro_policy"]),
                "advisory_raw": _raw(["a03_macro_policy", "a04_industry_layout"]),
            }
        )
        + "\n",
        encoding="utf-8",
    )

    predictions = load_prediction_artifact(predictions_path)
    record = build_case_record(
        _case(),
        agent_catalog=AGENT_CATALOG,
        prediction=predictions["ab-case"],
    )

    assert record["baseline"]["selected_agents"] == [
        "a01_cio_orchestrator",
        "a03_macro_policy",
        "a25_report_center",
    ]
    assert "a04_industry_layout" in record["advisory"]["selected_agents"]
    assert record["baseline"]["model_name"] is None
    assert record["comparison"]["token_count_delta"] is None


def test_enriched_prediction_artifact_preserves_side_metadata_and_deltas(tmp_path) -> None:
    predictions_path = tmp_path / "predictions.jsonl"
    predictions_path.write_text(
        json.dumps(
            {
                "schema_version": "router_advisory_prediction_v0",
                "id": "ab-case",
                "baseline": {
                    "raw": json.loads(_raw(["a03_macro_policy"])),
                    "model_name": "router-baseline",
                    "model_spec": "offline/baseline",
                    "prompt_chars": 1000,
                    "token_count": 250,
                    "latency_ms": 800.0,
                    "prompt_hash": "sha256:baseline",
                    "catalog_hash": "sha256:catalog",
                    "parse_latency_ms": 2.0,
                    "prompt": "do not persist",
                },
                "advisory": {
                    "raw": json.loads(
                        _raw(["a03_macro_policy", "a04_industry_layout"])
                    ),
                    "model_name": "router-advisory",
                    "model_spec": "offline/advisory",
                    "prompt_chars": 1234,
                    "token_count": 301,
                    "latency_ms": 945.5,
                    "prompt_hash": "sha256:advisory",
                    "catalog_hash": "sha256:catalog",
                    "parse_latency_ms": 2.5,
                    "prompt_body": "do not persist",
                },
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    predictions = load_prediction_artifact(predictions_path)
    record = build_case_record(
        _case(),
        agent_catalog=AGENT_CATALOG,
        prediction=predictions["ab-case"],
    )

    assert record["prediction_schema_version"] == "router_advisory_prediction_v0"
    assert isinstance(record["baseline"]["raw"], str)
    assert record["baseline"]["model_name"] == "router-baseline"
    assert record["advisory"]["model_spec"] == "offline/advisory"
    assert record["baseline"]["prompt_hash"] == "sha256:baseline"
    assert record["advisory"]["catalog_hash"] == "sha256:catalog"
    assert record["advisory"]["parse_latency_ms"] == pytest.approx(2.5)
    assert "prompt" not in record["baseline"]
    assert "prompt_body" not in record["advisory"]
    assert record["comparison"]["prompt_char_delta"] == 234
    assert record["comparison"]["token_count_delta"] == 51
    assert record["comparison"]["latency_ms_delta"] == pytest.approx(145.5)

    summary = build_summary([record], dataset=tmp_path / "dataset.jsonl")
    assert summary["avg_prompt_char_delta"] == pytest.approx(234.0)
    assert summary["avg_token_count_delta"] == pytest.approx(51.0)
    assert summary["avg_latency_ms_delta"] == pytest.approx(145.5)
    assert summary["latency_ms_delta_p50"] == pytest.approx(145.5)
    assert summary["latency_ms_delta_p90"] == pytest.approx(145.5)
    assert summary["latency_ms_delta_p95"] == pytest.approx(145.5)
    assert summary["prediction_records_with_complete_prompt_char_metadata"] == 1
    assert summary["prediction_records_with_complete_token_metadata"] == 1
    assert summary["prediction_records_with_complete_latency_metadata"] == 1
    assert summary["routing_quality_promotion_evidence"] is False


def test_missing_prediction_metadata_yields_null_token_and_latency_deltas() -> None:
    record = build_case_record(
        _case(),
        agent_catalog=AGENT_CATALOG,
        prediction={
            "schema_version": "router_advisory_prediction_v0",
            "baseline": {"raw": _raw(["a03_macro_policy"])},
            "advisory": {"raw": _raw(["a03_macro_policy", "a04_industry_layout"])},
        },
    )

    assert record["baseline"]["token_count"] is None
    assert record["advisory"]["latency_ms"] is None
    assert record["comparison"]["token_count_delta"] is None
    assert record["comparison"]["latency_ms_delta"] is None

    summary = build_summary([record], dataset=__file__)
    assert summary["avg_token_count_delta"] is None
    assert summary["avg_latency_ms_delta"] is None
    assert summary["latency_ms_delta_p95"] is None
    assert summary["prediction_records_with_complete_token_metadata"] == 0
    assert summary["prediction_records_with_complete_latency_metadata"] == 0


def test_case_record_uses_expected_layers_stub_without_prediction() -> None:
    case = _case()
    record = build_case_record(
        case,
        agent_catalog=AGENT_CATALOG,
        expected_layers={"L2": ["a03_macro_policy"], "L3": ["a19_market_risk"]},
    )

    assert record["baseline"]["selected_agents"] == [
        "a03_macro_policy",
        "a19_market_risk",
    ]
    assert record["advisory"]["selected_agents"] == [
        "a03_macro_policy",
        "a19_market_risk",
    ]


def test_offline_advisory_prompt_render_does_not_mutate_runtime_router_prompt() -> None:
    case = _case()
    original_prompt = prompts.ROUTER_SYSTEM_PROMPT
    baseline_prompt = render_baseline_prompt(AGENT_CATALOG)
    advisory_prompt = render_advisory_prompt(baseline_prompt, case)

    assert prompts.ROUTER_SYSTEM_PROMPT == original_prompt
    assert "Route prior advisory" not in original_prompt
    assert "Route prior advisory" not in baseline_prompt
    assert "Route prior advisory" in advisory_prompt


def test_label_stub_advisory_groups_agents_by_expected_layer() -> None:
    case = _wrong_layer_regression_case()
    baseline_prompt = render_baseline_prompt(AGENT_CATALOG)
    advisory_prompt = render_advisory_prompt(
        baseline_prompt,
        case,
        agent_catalog=AGENT_CATALOG,
        expected_layers={"L2": [], "L3": ["a19_market_risk"]},
    )
    advisory = _advisory_payload(advisory_prompt)

    assert advisory["critical_agents_by_layer"] == {"L3": ["a19_market_risk"]}
    assert advisory["must_include_agents_by_layer"] == {"L3": ["a19_market_risk"]}
    assert advisory["nice_to_have_agents_by_layer"] == {
        "L2": ["a14_single_stock_tech"]
    }
    assert "a19_market_risk" not in advisory["critical_agents_by_layer"].get("L2", [])
    assert "Do not move L3 agents into L2 or L2 agents into L3" in advisory["instruction"]
    assert "Return only the existing Router JSON schema" in advisory["instruction"]


def test_case_record_uses_layer_aware_advisory_prompt_without_persisting_prompt_body() -> None:
    case = _wrong_layer_regression_case()
    record = build_case_record(
        case,
        agent_catalog=AGENT_CATALOG,
        expected_layers={"L2": [], "L3": ["a19_market_risk"]},
    )

    assert record["advisory_prompt_chars"] > record["baseline_prompt_chars"]
    assert "prompt" not in record["baseline"]
    assert "prompt" not in record["advisory"]
    assert "a19_market_risk" in record["advisory"]["selected_agents"]
    assert record["advisory"]["parse_stats"]["filtered_agents"] == 0


def test_public_contract_models_do_not_gain_route_prior_or_advisory_fields() -> None:
    for model in (WorkflowModel, AgentCatalogResponse, HealthResponse):
        assert FORBIDDEN_PUBLIC_FIELDS.isdisjoint(model.model_fields)
