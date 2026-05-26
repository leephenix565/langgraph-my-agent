from __future__ import annotations

import json
from argparse import Namespace

from ops.regression.route_prior import generate_router_advisory_predictions as generator
from ops.regression.route_prior.generate_router_advisory_predictions import (
    DRY_RUN_MODE,
    LIVE_MODE,
    build_dry_run_prediction,
    build_provided_advisory_context,
    load_advisory_artifact,
    load_agent_catalog,
    render_provided_advisory_prompt,
    run,
)
from ops.regression.route_prior.run_route_prior_eval import label_case_from_record
from ops.regression.route_prior.run_router_advisory_ab import (
    build_case_record,
    load_prediction_artifact,
)


def _record() -> dict:
    return {
        "schema_version": "route_eval_label_v0",
        "id": "rp3-prediction-0001",
        "question": "If policy easing improves liquidity, assess macro impact.",
        "language": "en",
        "task_type": "macro_policy",
        "difficulty": "easy",
        "risk_level": "medium",
        "label_source": "manual_gold",
        "quality_conclusion_allowed": True,
        "review_status": "reviewed",
        "must_include_agents": ["a03_macro_industry_research"],
        "critical_agents": ["a03_macro_industry_research"],
        "nice_to_have_agents": [],
        "should_not_include_agents": ["a05_annual_report_analysis"],
        "expected_layers": {"L2": ["a03_macro_industry_research"], "L3": []},
        "primary_agent": "a03_macro_industry_research",
        "notes": "test fixture",
    }


def _write_dataset(path) -> None:
    path.write_text(json.dumps(_record(), ensure_ascii=False) + "\n", encoding="utf-8")


def _args(dataset, out, summary, *, mode=DRY_RUN_MODE, model="", api_key_env="") -> Namespace:
    return Namespace(
        dataset=str(dataset),
        out=str(out),
        summary_out=str(summary),
        max_items=1,
        mode=mode,
        model=model,
        base_url="",
        api_key_env=api_key_env,
        advisory_source="label_stub",
        advisory_artifact="",
    )


def test_dry_run_generator_writes_schema_valid_predictions(tmp_path) -> None:
    dataset = tmp_path / "labels.jsonl"
    out = tmp_path / "predictions.jsonl"
    summary = tmp_path / "summary.json"
    _write_dataset(dataset)

    assert run(_args(dataset, out, summary)) == 0

    records = [json.loads(line) for line in out.read_text(encoding="utf-8").splitlines()]
    payload = records[0]
    assert payload["schema_version"] == "router_advisory_prediction_v0"
    assert payload["id"] == "rp3-prediction-0001"
    assert payload["advisory_source"] == "label_stub"
    assert payload["baseline"]["raw"]
    assert payload["advisory"]["raw"]
    assert payload["baseline"]["prompt_chars"] > 0
    assert payload["advisory"]["prompt_chars"] > payload["baseline"]["prompt_chars"]
    assert payload["baseline"]["prompt_hash"].startswith("sha256:")
    assert payload["baseline"]["catalog_hash"].startswith("sha256:")
    assert payload["baseline"]["latency_ms"] == 0.0
    assert payload["baseline"]["token_count"] is None
    assert "prompt" not in payload["baseline"]
    assert "prompt_body" not in payload["advisory"]

    summary_payload = json.loads(summary.read_text(encoding="utf-8"))
    assert summary_payload["status"] == "ready"
    assert summary_payload["generated_count"] == 1
    assert summary_payload["skipped_count"] == 0
    assert summary_payload["token_metadata_complete_count"] == 0
    assert summary_payload["advisory_applied_count"] == 1
    assert summary_payload["advisory_noop_count"] == 0
    assert summary_payload["routing_quality_promotion_evidence"] is False


def test_live_mode_missing_env_writes_skipped_summary(tmp_path, monkeypatch) -> None:
    dataset = tmp_path / "labels.jsonl"
    out = tmp_path / "predictions.jsonl"
    summary = tmp_path / "summary.json"
    _write_dataset(dataset)
    monkeypatch.delenv("RP3A3_MISSING_KEY", raising=False)

    rc = run(
        _args(
            dataset,
            out,
            summary,
            mode=LIVE_MODE,
            model="openai/test-router",
            api_key_env="RP3A3_MISSING_KEY",
        )
    )

    assert rc == 0
    assert out.read_text(encoding="utf-8") == ""
    summary_payload = json.loads(summary.read_text(encoding="utf-8"))
    assert summary_payload["status"] == "skipped"
    assert summary_payload["generated_count"] == 0
    assert summary_payload["skipped_count"] == 1
    assert summary_payload["missing_env_reason"] == "missing env RP3A3_MISSING_KEY"


def test_prompt_and_catalog_hashes_are_stable_for_dry_run() -> None:
    case = label_case_from_record(_record())
    agent_catalog = load_agent_catalog()

    first = build_dry_run_prediction(
        case,
        agent_catalog=agent_catalog,
        expected_layers=_record()["expected_layers"],
        model_spec="dry-run/router-stub",
        advisory_source="label_stub",
    )
    second = build_dry_run_prediction(
        case,
        agent_catalog=agent_catalog,
        expected_layers=_record()["expected_layers"],
        model_spec="dry-run/router-stub",
        advisory_source="label_stub",
    )

    assert first["baseline"]["prompt_hash"] == second["baseline"]["prompt_hash"]
    assert first["advisory"]["prompt_hash"] == second["advisory"]["prompt_hash"]
    assert first["baseline"]["catalog_hash"] == second["baseline"]["catalog_hash"]


def test_generated_predictions_are_consumable_by_ab_replay(tmp_path) -> None:
    dataset = tmp_path / "labels.jsonl"
    out = tmp_path / "predictions.jsonl"
    summary = tmp_path / "summary.json"
    _write_dataset(dataset)

    assert run(_args(dataset, out, summary)) == 0

    predictions = load_prediction_artifact(out)
    case = label_case_from_record(_record())
    record = build_case_record(
        case,
        agent_catalog=load_agent_catalog(),
        prediction=predictions[case.case_id],
        expected_layers=_record()["expected_layers"],
    )

    assert record["prediction_schema_version"] == "router_advisory_prediction_v0"
    assert record["baseline"]["parse_stats"]["parse_ok"] is True
    assert record["advisory"]["parse_stats"]["parse_ok"] is True
    assert record["comparison"]["latency_ms_delta"] == 0.0


def test_provided_artifact_source_uses_reliability_shadow_not_manual_labels(
    tmp_path,
) -> None:
    case = label_case_from_record(
        {
            **_record(),
            "must_include_agents": ["a03_macro_industry_research"],
            "critical_agents": ["a03_macro_industry_research"],
            "expected_layers": {"L2": ["a03_macro_industry_research"], "L3": []},
        }
    )
    artifact = tmp_path / "route_prior_runs.jsonl"
    artifact.write_text(
        json.dumps(
            {
                "id": case.case_id,
                "enabled": True,
                "retrieval_reason": "test",
                "route_reliability": {
                    "schema_version": "route_reliability_shadow_v0",
                    "confidence_band": "high",
                    "low_confidence_fallback": False,
                    "cards": [
                        {
                            "agent_id": "a19_risk_identification",
                            "priority": "strong",
                            "reason_codes": ["semantic:high", "priority:strong"],
                        }
                    ],
                    "groups": {
                        "strongly_recommended": ["a19_risk_identification"],
                        "candidate": [],
                        "wildcard": [],
                        "deprioritized": [],
                    },
                },
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    records = load_advisory_artifact(artifact)
    context = build_provided_advisory_context(
        case_id=case.case_id,
        requested_source="provided_artifact",
        artifact_path=artifact,
        artifact_hash_value="sha256:test",
        records=records,
        agent_catalog=load_agent_catalog(),
    )

    prediction = build_dry_run_prediction(
        case,
        agent_catalog=load_agent_catalog(),
        expected_layers=_record()["expected_layers"],
        model_spec="dry-run/router-stub",
        advisory_source="provided_artifact",
        advisory_context=context,
    )
    prompt = render_provided_advisory_prompt("baseline", context=context)

    assert prediction["advisory_source"] == "provided_artifact"
    assert prediction["advisory_applied"] is True
    assert prediction["advisory_status"] == "provided_artifact_applied"
    assert prediction["advisory_case_found"] is True
    assert prediction["advisory_confidence_band"] == "high"
    assert prediction["advisory_agent_ids"] == ["a19_risk_identification"]
    assert prediction["advisory_reason_codes"] == {
        "a19_risk_identification": ["semantic:high", "priority:strong"]
    }
    assert "a03_macro_industry_research" not in prediction["advisory_agent_ids"]
    assert '"L3": ["a19_risk_identification"]' in prompt
    assert '"L2": ["a03_macro_industry_research"]' not in prompt
    assert "manual_gold" not in prompt
    assert "must_include_agents_by_layer" not in prompt
    assert "critical_agents_by_layer" not in prompt
    assert "prompt" not in prediction["baseline"]
    assert "prompt_body" not in prediction["advisory"]


def test_provided_artifact_missing_case_degrades_without_label_stub() -> None:
    case = label_case_from_record(_record())
    context = build_provided_advisory_context(
        case_id=case.case_id,
        requested_source="provided_artifact",
        artifact_path=None,
        artifact_hash_value=None,
        records={},
        agent_catalog=load_agent_catalog(),
    )
    prediction = build_dry_run_prediction(
        case,
        agent_catalog=load_agent_catalog(),
        expected_layers=_record()["expected_layers"],
        model_spec="dry-run/router-stub",
        advisory_source="provided_artifact",
        advisory_context=context,
    )

    assert prediction["advisory_source"] == "provided_artifact_missing"
    assert prediction["advisory_applied"] is False
    assert prediction["advisory_status"] == "provided_artifact_missing"
    assert prediction["advisory_noop_reason"] == "noop_no_advisory"
    assert prediction["advisory_case_found"] is False
    assert prediction["advisory_missing_reason"] == "artifact_not_configured"
    assert prediction["advisory_agent_ids"] == []
    assert prediction["advisory_artifact_path"] is None
    assert prediction["baseline"]["prompt_hash"] == prediction["advisory"]["prompt_hash"]
    assert prediction["baseline"]["prompt_chars"] == prediction["advisory"]["prompt_chars"]
    assert prediction["baseline"]["raw"] == prediction["advisory"]["raw"]


def test_provided_artifact_existing_file_missing_case_is_marked_case_not_found(
    tmp_path,
) -> None:
    case = label_case_from_record(_record())
    artifact = tmp_path / "route_prior_runs.jsonl"
    artifact.write_text(
        json.dumps(
            {
                "id": "different-case",
                "route_reliability": {
                    "schema_version": "route_reliability_shadow_v0",
                    "cards": [],
                    "groups": {},
                },
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    context = build_provided_advisory_context(
        case_id=case.case_id,
        requested_source="provided_artifact",
        artifact_path=artifact,
        artifact_hash_value="sha256:test",
        records=load_advisory_artifact(artifact),
        agent_catalog=load_agent_catalog(),
    )

    assert context["advisory_source"] == "provided_artifact_missing"
    assert context["advisory_case_found"] is False
    assert context["advisory_missing_reason"] == "case_not_found"
    assert context["advisory_agent_ids"] == []


def test_provided_artifact_empty_cards_marked_missing(tmp_path) -> None:
    case = label_case_from_record(_record())
    artifact = tmp_path / "route_prior_runs.jsonl"
    artifact.write_text(
        json.dumps(
            {
                "id": case.case_id,
                "enabled": False,
                "retrieval_reason": "disabled_flag_off",
                "route_reliability": {
                    "schema_version": "route_reliability_shadow_v0",
                    "confidence_band": "low",
                    "low_confidence_fallback": True,
                    "cards": [],
                    "groups": {
                        "strongly_recommended": [],
                        "candidate": [],
                        "wildcard": [],
                        "deprioritized": [],
                    },
                },
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    context = build_provided_advisory_context(
        case_id=case.case_id,
        requested_source="rarp_shadow",
        artifact_path=artifact,
        artifact_hash_value="sha256:test",
        records=load_advisory_artifact(artifact),
        agent_catalog=load_agent_catalog(),
    )

    assert context["advisory_source"] == "rarp_shadow_disabled"
    assert context["advisory_status"] == "rarp_shadow_disabled"
    assert context["advisory_applied"] is False
    assert context["advisory_noop_reason"] == "noop_no_advisory"
    assert context["advisory_case_found"] is True
    assert context["advisory_confidence_band"] == "low"
    assert context["advisory_low_confidence_fallback"] is True
    assert context["advisory_retrieval_enabled"] is False
    assert context["advisory_retrieval_reason"] == "disabled_flag_off"
    assert context["advisory_missing_reason"] == "retrieval_disabled"


def test_provided_artifact_enabled_empty_cards_noop(tmp_path) -> None:
    case = label_case_from_record(_record())
    artifact = tmp_path / "route_prior_runs.jsonl"
    artifact.write_text(
        json.dumps(
            {
                "id": case.case_id,
                "enabled": True,
                "retrieval_reason": "ok",
                "route_reliability": {
                    "schema_version": "route_reliability_shadow_v0",
                    "confidence_band": "normal",
                    "low_confidence_fallback": False,
                    "cards": [],
                    "groups": {
                        "strongly_recommended": [],
                        "candidate": [],
                        "wildcard": [],
                        "deprioritized": [],
                    },
                },
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    context = build_provided_advisory_context(
        case_id=case.case_id,
        requested_source="provided_artifact",
        artifact_path=artifact,
        artifact_hash_value="sha256:test",
        records=load_advisory_artifact(artifact),
        agent_catalog=load_agent_catalog(),
    )
    prompt = render_provided_advisory_prompt("baseline", context=context)

    assert context["advisory_source"] == "provided_artifact_missing"
    assert context["advisory_applied"] is False
    assert context["advisory_status"] == "provided_artifact_missing"
    assert context["advisory_missing_reason"] == "reliability_cards_empty"
    assert prompt == "baseline"


def test_provided_artifact_wildcard_only_without_domain_card_noop(tmp_path) -> None:
    case = label_case_from_record(_record())
    artifact = tmp_path / "route_prior_runs.jsonl"
    artifact.write_text(
        json.dumps(
            {
                "id": case.case_id,
                "enabled": True,
                "retrieval_reason": "ok",
                "top_ranked_ids": ["a15_entity_relation_extraction"],
                "route_reliability": {
                    "schema_version": "route_reliability_shadow_v0",
                    "confidence_band": "normal",
                    "low_confidence_fallback": False,
                    "cards": [
                        {
                            "agent_id": "a15_entity_relation_extraction",
                            "priority": "hidden",
                            "wildcard_flag": True,
                            "reason_codes": ["guardrail:wildcard"],
                        }
                    ],
                    "groups": {
                        "strongly_recommended": [],
                        "candidate": [],
                        "wildcard": ["a15_entity_relation_extraction"],
                        "deprioritized": [],
                    },
                },
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    context = build_provided_advisory_context(
        case_id=case.case_id,
        requested_source="provided_artifact",
        artifact_path=artifact,
        artifact_hash_value="sha256:test",
        records=load_advisory_artifact(artifact),
        agent_catalog=load_agent_catalog(),
    )
    prompt = render_provided_advisory_prompt("baseline", context=context)

    assert context["advisory_source"] == "provided_artifact_wildcard_only"
    assert context["advisory_status"] == "noop_wildcard_only"
    assert context["advisory_applied"] is False
    assert context["advisory_noop_reason"] == "noop_wildcard_only"
    assert context["advisory_missing_reason"] == "wildcard_only"
    assert context["advisory_agent_ids"] == []
    assert context["advisory_secondary_agent_ids"] == ["a15_entity_relation_extraction"]
    assert prompt == "baseline"


def test_provided_artifact_wildcard_only_uses_non_wildcard_fallback(tmp_path) -> None:
    case = label_case_from_record(_record())
    artifact = tmp_path / "route_prior_runs.jsonl"
    artifact.write_text(
        json.dumps(
            {
                "id": case.case_id,
                "enabled": True,
                "retrieval_reason": "ok",
                "top_ranked_ids": [
                    "a04_commodity_hedging",
                    "a15_entity_relation_extraction",
                    "a03_macro_industry_research",
                ],
                "route_reliability": {
                    "schema_version": "route_reliability_shadow_v0",
                    "confidence_band": "normal",
                    "low_confidence_fallback": False,
                    "cards": [
                        {
                            "agent_id": "a04_commodity_hedging",
                            "priority": "hidden",
                            "wildcard_flag": False,
                            "reason_codes": ["semantic:low", "priority:hidden"],
                        },
                        {
                            "agent_id": "a15_entity_relation_extraction",
                            "priority": "hidden",
                            "wildcard_flag": True,
                            "reason_codes": ["guardrail:wildcard"],
                        },
                        {
                            "agent_id": "a03_macro_industry_research",
                            "priority": "hidden",
                            "wildcard_flag": False,
                            "reason_codes": ["semantic:low", "priority:hidden"],
                        },
                    ],
                    "groups": {
                        "strongly_recommended": [],
                        "candidate": [],
                        "wildcard": ["a15_entity_relation_extraction"],
                        "deprioritized": [],
                    },
                },
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    context = build_provided_advisory_context(
        case_id=case.case_id,
        requested_source="provided_artifact",
        artifact_path=artifact,
        artifact_hash_value="sha256:test",
        records=load_advisory_artifact(artifact),
        agent_catalog=load_agent_catalog(),
    )
    prompt = render_provided_advisory_prompt("baseline", context=context)

    assert context["advisory_applied"] is True
    assert context["advisory_status"] == "provided_artifact_weak_non_wildcard_fallback"
    assert context["advisory_selection_reason"] == "weak_non_wildcard_fallback"
    assert context["advisory_agent_ids"] == ["a04_commodity_hedging", "a03_macro_industry_research"]
    assert context["advisory_secondary_agent_ids"] == ["a15_entity_relation_extraction"]
    assert context["advisory_agent_ids"] != ["a15_entity_relation_extraction"]
    assert '"L2": ["a04_commodity_hedging", "a03_macro_industry_research"]' in prompt
    assert "secondary_agents_by_layer" in prompt
    assert "a15_entity_relation_extraction" in prompt
    assert "Secondary agents are context only" in prompt


def test_regression_like_wildcard_only_artifacts_include_domain_cards(tmp_path) -> None:
    cases = [
        (
            "rp3-manual-gold-0002",
            ["a04_commodity_hedging", "a08_industry_hotspot", "a15_entity_relation_extraction"],
            ["a04_commodity_hedging"],
        ),
        (
            "rp3-manual-gold-0013",
            [
                "a03_macro_industry_research",
                "a04_commodity_hedging",
                "a07_macro_sentiment",
                "a15_entity_relation_extraction",
            ],
            ["a03_macro_industry_research", "a04_commodity_hedging"],
        ),
        (
            "rp3-manual-gold-0014",
            [
                "a05_annual_report_analysis",
                "a19_risk_identification",
                "a19_risk_identification",
                "a06_financial_statement_analysis",
                "a04_commodity_hedging",
                "a15_entity_relation_extraction",
            ],
            ["a05_annual_report_analysis", "a04_commodity_hedging"],
        ),
    ]
    records = []
    for case_id, top_ranked_ids, _expected in cases:
        records.append(
            {
                "id": case_id,
                "enabled": True,
                "retrieval_reason": "ok",
                "top_ranked_ids": top_ranked_ids,
                "route_reliability": {
                    "schema_version": "route_reliability_shadow_v0",
                    "confidence_band": "normal",
                    "low_confidence_fallback": False,
                    "cards": [
                        {
                            "agent_id": agent_id,
                            "priority": "hidden",
                            "wildcard_flag": agent_id == "a15_entity_relation_extraction",
                            "reason_codes": ["guardrail:wildcard"]
                            if agent_id == "a15_entity_relation_extraction"
                            else ["semantic:low", "priority:hidden"],
                        }
                        for agent_id in top_ranked_ids
                    ],
                    "groups": {
                        "strongly_recommended": [],
                        "candidate": [],
                        "wildcard": ["a15_entity_relation_extraction"],
                        "deprioritized": [],
                    },
                },
            }
        )
    artifact = tmp_path / "route_prior_runs.jsonl"
    artifact.write_text(
        "\n".join(json.dumps(record, ensure_ascii=False) for record in records) + "\n",
        encoding="utf-8",
    )
    loaded = load_advisory_artifact(artifact)

    for case_id, _top_ranked_ids, expected_agent_ids in cases:
        context = build_provided_advisory_context(
            case_id=case_id,
            requested_source="provided_artifact",
            artifact_path=artifact,
            artifact_hash_value="sha256:test",
            records=loaded,
            agent_catalog=load_agent_catalog(),
        )

        assert context["advisory_applied"] is True
        assert context["advisory_status"] == "provided_artifact_weak_non_wildcard_fallback"
        assert set(expected_agent_ids).issubset(set(context["advisory_agent_ids"]))
        assert context["advisory_agent_ids"] != ["a15_entity_relation_extraction"]
        assert context["advisory_secondary_agent_ids"] == ["a15_entity_relation_extraction"]


def test_provided_artifact_low_confidence_cards_noop(tmp_path) -> None:
    case = label_case_from_record(_record())
    artifact = tmp_path / "route_prior_runs.jsonl"
    artifact.write_text(
        json.dumps(
            {
                "id": case.case_id,
                "enabled": True,
                "retrieval_reason": "low_margin",
                "route_reliability": {
                    "schema_version": "route_reliability_shadow_v0",
                    "confidence_band": "low",
                    "low_confidence_fallback": True,
                    "cards": [
                        {
                            "agent_id": "a19_risk_identification",
                            "priority": "strong",
                            "reason_codes": ["semantic:high"],
                        }
                    ],
                    "groups": {
                        "strongly_recommended": ["a19_risk_identification"],
                        "candidate": [],
                        "wildcard": [],
                        "deprioritized": [],
                    },
                },
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    context = build_provided_advisory_context(
        case_id=case.case_id,
        requested_source="provided_artifact",
        artifact_path=artifact,
        artifact_hash_value="sha256:test",
        records=load_advisory_artifact(artifact),
        agent_catalog=load_agent_catalog(),
    )

    assert context["advisory_source"] == "provided_artifact_low_confidence"
    assert context["advisory_status"] == "provided_artifact_low_confidence"
    assert context["advisory_applied"] is False
    assert context["advisory_missing_reason"] == "low_confidence_fallback"
    assert context["advisory_agent_ids"] == []


def test_run_writes_provided_artifact_predictions_and_summary(tmp_path) -> None:
    dataset = tmp_path / "labels.jsonl"
    out = tmp_path / "predictions.jsonl"
    summary = tmp_path / "summary.json"
    artifact = tmp_path / "route_prior_runs.jsonl"
    _write_dataset(dataset)
    artifact.write_text(
        json.dumps(
            {
                "id": "rp3-prediction-0001",
                "enabled": True,
                "retrieval_reason": "test",
                "route_reliability": {
                    "schema_version": "route_reliability_shadow_v0",
                    "confidence_band": "high",
                    "low_confidence_fallback": False,
                    "cards": [
                        {
                            "agent_id": "a19_risk_identification",
                            "priority": "strong",
                            "reason_codes": ["semantic:high"],
                        }
                    ],
                    "groups": {
                        "strongly_recommended": ["a19_risk_identification"],
                        "candidate": [],
                        "wildcard": [],
                        "deprioritized": [],
                    },
                },
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    args = _args(dataset, out, summary)
    args.advisory_source = "provided_artifact"
    args.advisory_artifact = str(artifact)

    assert run(args) == 0

    payload = json.loads(out.read_text(encoding="utf-8").splitlines()[0])
    summary_payload = json.loads(summary.read_text(encoding="utf-8"))
    assert payload["advisory_source"] == "provided_artifact"
    assert payload["advisory_applied"] is True
    assert payload["advisory_status"] == "provided_artifact_applied"
    assert payload["advisory_case_found"] is True
    assert payload["advisory_confidence_band"] == "high"
    assert payload["advisory_agent_ids"] == ["a19_risk_identification"]
    assert payload["advisory_reason_codes"] == {"a19_risk_identification": ["semantic:high"]}
    assert payload["advisory_artifact_path"] == str(artifact)
    assert payload["advisory_artifact_hash"].startswith("sha256:")
    assert "prompt" not in payload["baseline"]
    assert "prompt_body" not in payload["advisory"]
    assert summary_payload["advisory_source_counts"] == {"provided_artifact": 1}
    assert summary_payload["advisory_applied_count"] == 1
    assert summary_payload["advisory_noop_count"] == 0


def test_live_noop_provided_artifact_invokes_only_baseline_side(
    tmp_path,
    monkeypatch,
) -> None:
    dataset = tmp_path / "labels.jsonl"
    out = tmp_path / "predictions.jsonl"
    summary = tmp_path / "summary.json"
    _write_dataset(dataset)
    calls: list[str] = []

    async def fake_invoke_router_side(**kwargs):
        calls.append(kwargs["system_prompt"])
        return (
            json.dumps(
                {
                    "layers": [
                        {"layer": "L1", "mode": "Chain", "selected": []},
                        {"layer": "L2", "mode": "Star", "selected": ["a03_macro_industry_research"]},
                        {"layer": "L3", "mode": "Star", "selected": []},
                        {"layer": "L4", "mode": "Chain", "selected": []},
                    ],
                    "reason": "test",
                }
            ),
            12.5,
            42,
        )

    monkeypatch.setattr(generator, "invoke_router_side", fake_invoke_router_side)
    args = _args(
        dataset,
        out,
        summary,
        mode=LIVE_MODE,
        model="openai/test-router",
        api_key_env="none",
    )
    args.advisory_source = "provided_artifact"

    assert run(args) == 0

    payload = json.loads(out.read_text(encoding="utf-8").splitlines()[0])
    summary_payload = json.loads(summary.read_text(encoding="utf-8"))
    assert len(calls) == 1
    assert payload["advisory_applied"] is False
    assert payload["advisory_status"] == "provided_artifact_missing"
    assert payload["advisory_noop_reason"] == "noop_no_advisory"
    assert payload["baseline"]["raw"] == payload["advisory"]["raw"]
    assert payload["baseline"]["prompt_hash"] == payload["advisory"]["prompt_hash"]
    assert payload["baseline"]["latency_ms"] == payload["advisory"]["latency_ms"]
    assert summary_payload["advisory_applied_count"] == 0
    assert summary_payload["advisory_noop_count"] == 1
