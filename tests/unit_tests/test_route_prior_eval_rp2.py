from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import anyio
import pytest

from ops.regression.route_prior.eval_route_prior_outputs import aggregate_metrics
from ops.regression.route_prior.run_route_prior_eval import (
    label_case_from_record,
    run_case,
    validate_label_case,
)
from react_agent.route_profile_registry import RouteProfileCard

REPO_ROOT = Path(__file__).resolve().parents[2]
RP3_SEED_TEMPLATE = (
    REPO_ROOT
    / "ops"
    / "regression"
    / "route_prior"
    / "fixtures"
    / "rp3_manual_gold_seed_template.jsonl"
)


def test_route_eval_label_v0_parses_expanded_schema() -> None:
    case = label_case_from_record(
        {
            "schema_version": "route_eval_label_v0",
            "id": "rp2-case-1",
            "question": "q",
            "label_source": "manual_gold",
            "quality_conclusion_allowed": True,
            "must_include_agents": ["a1", "a2"],
            "critical_agents": ["a2"],
            "nice_to_have_agents": ["a3"],
            "should_not_include_agents": ["a4"],
            "task_type": "macro_rates",
            "difficulty": "multi_domain",
            "risk_level": "medium",
        }
    )

    assert case.schema_version == "route_eval_label_v0"
    assert case.expected_agents == ["a1", "a2"]
    assert case.must_include_agents == ["a1", "a2"]
    assert case.critical_agents == ["a2"]
    assert case.nice_to_have_agents == ["a3"]
    assert case.should_not_include_agents == ["a4"]
    assert case.quality_conclusion_allowed is True
    assert case.task_type == "macro_rates"
    assert case.difficulty == "multi_domain"
    assert case.risk_level == "medium"


def test_legacy_expected_agents_maps_to_must_include() -> None:
    case = label_case_from_record(
        {
            "id": "legacy-case",
            "question": "q",
            "expected_agents": ["a1"],
            "label_source": "manual",
        }
    )

    assert case.schema_version == "rp1b_legacy"
    assert case.expected_agents == ["a1"]
    assert case.must_include_agents == ["a1"]
    assert case.critical_agents == []
    assert case.nice_to_have_agents == []
    assert case.should_not_include_agents == []
    assert case.quality_conclusion_allowed is True


def test_expanded_label_validation_is_deterministic() -> None:
    with pytest.raises(ValueError, match="critical_agents"):
        label_case_from_record(
            {
                "id": "bad-critical",
                "question": "q",
                "label_source": "manual_gold",
                "must_include_agents": ["a1"],
                "critical_agents": ["a2"],
            }
        )

    with pytest.raises(ValueError, match="overlap"):
        label_case_from_record(
            {
                "id": "bad-negative",
                "question": "q",
                "label_source": "manual_gold",
                "must_include_agents": ["a1"],
                "should_not_include_agents": ["a1"],
            }
        )


def test_manual_gold_requires_quality_conclusion_true() -> None:
    with pytest.raises(ValueError, match="manual_gold requires"):
        label_case_from_record(
            {
                "id": "manual-gold-false",
                "question": "q",
                "label_source": "manual_gold",
                "quality_conclusion_allowed": False,
                "must_include_agents": ["a1"],
            }
        )


def test_rp3_manual_gold_seed_template_is_pending_human_review() -> None:
    required_fields = {
        "schema_version",
        "id",
        "question",
        "language",
        "task_type",
        "difficulty",
        "risk_level",
        "label_source",
        "quality_conclusion_allowed",
        "review_status",
        "must_include_agents",
        "critical_agents",
        "nice_to_have_agents",
        "should_not_include_agents",
        "expected_layers",
        "primary_agent",
        "notes",
    }
    known_agent_ids = {
        "a03_macro_policy",
        "a05_product_pricing",
        "a09_macro_sentiment",
        "a14_single_stock_tech",
        "a15_research_synthesis",
        "a17_client_profile",
        "a19_market_risk",
        "a21_reg_compliance",
        "a22_suitability_review",
        "a23_portfolio_opt",
        "a27_portfolio_backtest",
    }

    records = [
        json.loads(line)
        for line in RP3_SEED_TEMPLATE.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    assert records
    for record in records:
        assert required_fields.issubset(record)
        assert record["label_source"] == "draft_for_human_review"
        assert record["quality_conclusion_allowed"] is False
        assert record["review_status"] == "seed_template_pending_human_review"

        case = label_case_from_record(record)
        assert case.quality_conclusion_allowed is False
        assert validate_label_case(case, known_agent_ids) == []


def test_validate_label_case_checks_all_expanded_agent_sets() -> None:
    case = label_case_from_record(
        {
            "id": "invalid-expanded",
            "question": "q",
            "label_source": "manual_gold",
            "must_include_agents": ["a1"],
            "critical_agents": ["a1"],
            "nice_to_have_agents": ["missing_nice"],
            "should_not_include_agents": ["missing_negative"],
        }
    )

    assert validate_label_case(case, {"a1"}) == ["missing_nice", "missing_negative"]


def test_teacher_proxy_cannot_claim_quality_conclusion() -> None:
    with pytest.raises(ValueError, match="quality_conclusion_allowed"):
        label_case_from_record(
            {
                "id": "teacher-case",
                "question": "q",
                "expected_agents": ["a1"],
                "label_source": "deepseek_teacher_v1",
                "quality_conclusion_allowed": True,
            }
        )


def test_rp2_metrics_cover_recall_cost_calibration_and_label_groups() -> None:
    records = [
        {
            "id": "manual",
            "label_source": "manual_gold",
            "quality_conclusion_allowed": True,
            "must_include_agents": ["a1", "a2"],
            "critical_agents": ["a2"],
            "nice_to_have_agents": ["a3"],
            "should_not_include_agents": ["a4"],
            "awake_agents": ["a1", "a3", "a4"],
            "top_ranked_ids": ["a1", "a3", "a4", "a2"],
            "route_scores_all_light": [
                {"agent_id": "a1", "semantic_similarity_score": 0.9},
                {"agent_id": "a3", "semantic_similarity_score": 0.6},
                {"agent_id": "a4", "semantic_similarity_score": 0.7},
                {"agent_id": "a2", "semantic_similarity_score": 0.8},
            ],
            "ordinary_pool_size": 4,
            "enabled": True,
            "retrieval_reason": "ok",
            "confidence_band": "high",
            "low_confidence_fallback": False,
            "wildcard_agents": [],
        },
        {
            "id": "teacher",
            "label_source": "deepseek_teacher_v1",
            "quality_conclusion_allowed": True,
            "must_include_agents": ["b1"],
            "awake_agents": ["b1", "b2"],
            "top_ranked_ids": ["b1", "b2"],
            "route_scores_all_light": [
                {"agent_id": "b1", "semantic_similarity_score": 0.6},
                {"agent_id": "b2", "semantic_similarity_score": 0.4},
            ],
            "ordinary_pool_size": 3,
            "enabled": True,
            "retrieval_reason": "ok",
            "confidence_band": "low",
            "low_confidence_fallback": True,
            "wildcard_agents": [],
        },
    ]

    metrics = aggregate_metrics(
        records,
        agent_costs={
            "a1": "low",
            "a3": "high",
            "a4": "normal",
            "b1": "normal",
            "b2": "normal",
        },
    )

    assert metrics["expected_agent_recall@1"] == pytest.approx(0.75)
    assert metrics["expected_agent_recall@3"] == pytest.approx(0.75)
    assert metrics["expected_agent_recall@5"] == pytest.approx(1.0)
    assert metrics["shortlist_recall"] == pytest.approx(0.75)
    assert metrics["safe_shortlist_recall"] == pytest.approx(0.75)
    assert metrics["effective_shortlist_recall"] == pytest.approx(0.25)
    assert metrics["critical_agent_miss_rate"] == pytest.approx(1.0)
    assert metrics["precision_at_shortlist"] == pytest.approx((1 / 3 + 1 / 2) / 2)
    assert metrics["f1_at_shortlist"] == pytest.approx((0.4 + 2 / 3) / 2)
    assert metrics["jaccard_at_shortlist"] == pytest.approx((0.25 + 0.5) / 2)
    assert metrics["nice_to_have_recall"] == pytest.approx(1.0)
    assert metrics["negative_selection_rate"] == pytest.approx(1.0)
    assert metrics["avg_shortlist_size"] == pytest.approx(2.5)
    assert metrics["avg_cost"] == pytest.approx(5.0)
    assert metrics["recall_per_cost"] == pytest.approx((0.5 / 6 + 1 / 4) / 2)
    assert metrics["high_confidence_wrong_rate"] == pytest.approx(1.0)
    assert metrics["Brier"] == pytest.approx((0.01 + 0.49 + 0.04 + 0.16) / 4)
    assert metrics["ECE"] is not None
    assert metrics["calibration_pair_count"] == 4
    assert metrics["quality_conclusion_allowed"] is True

    grouped = metrics["label_source_grouped_metrics"]
    assert grouped["manual_gold"]["quality_conclusion_allowed"] is True
    assert grouped["deepseek_teacher_v1"]["quality_conclusion_allowed"] is False
    assert grouped["deepseek_teacher_v1"]["proxy_quality_conclusion_only"] is True


def test_run_case_writes_rp2_artifact_without_raw_embeddings(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_shadow(_question: str, _metadata_by_id: object) -> dict[str, object]:
        return {
            "enabled": True,
            "retrieval_reason": "ok",
            "routing_hint": {
                "confidence_band": "normal",
                "reason_codes": ["retrieval:ok"],
            },
            "low_confidence_fallback": False,
            "ordinary_pool": ["a1", "a2", "a3"],
            "awake_agents": ["a1", "a3"],
            "route_scores": [
                {
                    "agent_id": "a1",
                    "semantic_similarity_score": 0.9,
                    "cost_tiebreak_score": 0.0,
                    "wildcard_flag": False,
                    "confidence_band": "normal",
                },
                {
                    "agent_id": "a2",
                    "semantic_similarity_score": 0.8,
                    "cost_tiebreak_score": 0.0,
                    "wildcard_flag": False,
                    "confidence_band": "normal",
                },
                {
                    "agent_id": "a3",
                    "semantic_similarity_score": 0.7,
                    "cost_tiebreak_score": 0.0,
                    "wildcard_flag": False,
                    "confidence_band": "normal",
                },
            ],
            "wildcard_agents": [],
            "cache_hits": 0,
            "cache_misses": 0,
        }

    from react_agent import route_prior

    monkeypatch.setattr(route_prior, "compute_route_prior_shadow", fake_shadow)
    case = label_case_from_record(
        {
            "schema_version": "route_eval_label_v0",
            "id": "artifact-case",
            "question": "q",
            "label_source": "manual_gold",
            "quality_conclusion_allowed": True,
            "must_include_agents": ["a1", "a2"],
            "critical_agents": ["a2"],
            "nice_to_have_agents": ["a3"],
            "should_not_include_agents": [],
        }
    )

    async def invoke() -> dict[str, object]:
        return await run_case(
            case,
            {"a1": SimpleNamespace(cost_level="low"), "a3": SimpleNamespace(cost_level="high")},
            invalid_expected_agents=[],
            rarp_scoring_enabled=True,
            profile_cards={
                "a1": RouteProfileCard(
                    schema_version="route_profile_card_v0",
                    agent_id="a1",
                    positive_examples=("internal profile card text",),
                )
            },
            reliability_table={
                "global": {
                    "a1": {
                        "historical_reliability": 0.9,
                        "historical_uncertainty": 0.1,
                    }
                }
            },
        )

    record = anyio.run(invoke)

    assert record["schema_version"] == "route_prior_run_v2"
    assert record["label_schema_version"] == "route_eval_label_v0"
    assert record["question_hash"].startswith("sha256:")
    assert record["question_preview"] == "q"
    assert record["labels"]["must_include_agents"] == ["a1", "a2"]
    assert record["case_metrics"]["recall_at_5"] == pytest.approx(1.0)
    assert record["case_metrics"]["safe_shortlist_recall"] == pytest.approx(0.5)
    assert record["case_metrics"]["effective_shortlist_recall"] == pytest.approx(0.5)
    assert record["case_metrics"]["critical_miss"] is True
    assert record["case_metrics"]["shortlist_cost"] == pytest.approx(4.0)
    assert record["rarp_scoring_enabled"] is True
    assert record["route_reliability"]["schema_version"] == "route_reliability_shadow_v0"
    assert record["route_reliability"]["cards"][0]["agent_id"] == "a1"
    assert "profile_card:present" in record["route_reliability"]["cards"][0]["reason_codes"]

    encoded = json.dumps(record, ensure_ascii=False).lower()
    assert "embedding" not in encoded
    assert "profile_text" not in encoded
    assert "internal profile card text" not in encoded
