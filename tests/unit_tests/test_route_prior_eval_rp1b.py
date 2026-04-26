from __future__ import annotations

from pathlib import Path

import pytest

from ops.regression.route_prior.eval_route_prior_outputs import (
    aggregate_metrics,
    collect_false_negatives,
    expected_recall,
    jaccard,
    top_ranked_ids,
    topk_hit,
)
from ops.regression.route_prior.run_route_prior_eval import (
    LabelCase,
    label_case_from_record,
    load_label_cases,
    validate_label_case,
)


def test_metrics_topk_hit_calculation() -> None:
    record = {
        "expected_agents": ["a1"],
        "top_ranked_ids": ["a1", "a2"],
    }

    assert topk_hit(record, 1) is True
    assert topk_hit(record, 3) is True


def test_top_ranked_ids_falls_back_to_route_scores_top10() -> None:
    record = {
        "route_scores_top10": [
            {"agent_id": "a1", "semantic_similarity_score": 0.9},
            {"agent_id": "a2", "semantic_similarity_score": 0.8},
        ]
    }

    assert top_ranked_ids(record) == ["a1", "a2"]


def test_shortlist_recall_calculation() -> None:
    assert expected_recall(["a1", "a2"], ["a1", "a3"]) == 0.5


def test_jaccard_boundaries() -> None:
    assert jaccard([], []) == 0.0
    assert jaccard(["a1"], ["a1"]) == 1.0
    assert jaccard(["a1"], ["a2"]) == 0.0


def test_false_negative_extraction() -> None:
    records = [
        {
            "id": "case-1",
            "question": "question",
            "expected_agents": ["a1", "a3"],
            "awake_agents": ["a1", "a2"],
            "top_ranked_ids": ["a1", "a2"],
            "confidence_band": "normal",
            "low_confidence_fallback": False,
            "retrieval_reason": "ok",
            "reason_codes": ["retrieval:ok"],
            "label_source": "manual",
        }
    ]

    examples = collect_false_negatives(records)

    assert examples[0]["id"] == "case-1"
    assert examples[0]["missing_expected_agents"] == ["a3"]


def test_aggregate_low_confidence_fallback_rate() -> None:
    metrics = aggregate_metrics(
        [
            {
                "id": "case-1",
                "expected_agents": ["a1"],
                "awake_agents": ["a1"],
                "top_ranked_ids": ["a1"],
                "ordinary_pool_size": 4,
                "enabled": True,
                "retrieval_reason": "ok",
                "confidence_band": "low",
                "low_confidence_fallback": True,
                "wildcard_agents": ["a15"],
                "label_source": "manual",
            },
            {
                "id": "case-2",
                "expected_agents": ["a2"],
                "awake_agents": ["a3"],
                "top_ranked_ids": ["a3"],
                "ordinary_pool_size": 4,
                "enabled": True,
                "retrieval_reason": "ok",
                "confidence_band": "normal",
                "low_confidence_fallback": False,
                "wildcard_agents": ["a15"],
                "label_source": "manual",
            },
        ]
    )

    assert metrics["low_confidence_fallback_rate"] == 0.5
    assert metrics["shortlist_recall"] == 0.5


def test_formal_router_overlap_observation_present_and_absent() -> None:
    with_overlap = aggregate_metrics(
        [
            {
                "id": "case-1",
                "expected_agents": ["a1"],
                "awake_agents": ["a1", "a2"],
                "top_ranked_ids": ["a1", "a2"],
                "formal_router_selected": ["a2", "a3"],
                "ordinary_pool_size": 4,
                "enabled": True,
                "retrieval_reason": "ok",
                "confidence_band": "normal",
                "low_confidence_fallback": False,
                "label_source": "manual",
            }
        ]
    )
    without_overlap = aggregate_metrics(
        [
            {
                "id": "case-2",
                "expected_agents": ["a1"],
                "awake_agents": ["a1"],
                "top_ranked_ids": ["a1"],
                "ordinary_pool_size": 4,
                "enabled": True,
                "retrieval_reason": "ok",
                "confidence_band": "normal",
                "low_confidence_fallback": False,
                "label_source": "manual",
            }
        ]
    )

    observation = with_overlap["formal_router_overlap_observation"]
    assert observation is not None
    assert observation["avg_overlap_count"] == 1.0
    assert observation["avg_jaccard"] == pytest.approx(1 / 3)
    assert without_overlap["formal_router_overlap_observation"] is None


def test_invalid_expected_agent_detection() -> None:
    case = LabelCase(
        case_id="case-1",
        question="question",
        expected_agents=["a1", "missing"],
        tags=[],
        label_source="manual",
    )

    assert validate_label_case(case, {"a1", "a2"}) == ["missing"]


def test_label_case_loader_skips_blank_lines(tmp_path: Path) -> None:
    dataset = tmp_path / "labels.jsonl"
    dataset.write_text(
        '{"id":"case-1","question":"q","expected_agents":["a1"],'
        '"label_source":"manual","formal_router_selected":["a2"]}\n\n',
        encoding="utf-8",
    )

    cases = load_label_cases(dataset)

    assert len(cases) == 1
    assert cases[0].case_id == "case-1"
    assert cases[0].formal_router_selected == ["a2"]


def test_label_case_from_record_rejects_missing_expected_agents() -> None:
    with pytest.raises(ValueError, match="expected_agents"):
        label_case_from_record(
            {
                "id": "case-1",
                "question": "q",
                "expected_agents": [],
                "label_source": "manual",
            }
        )


def test_draft_labels_disable_quality_conclusion() -> None:
    metrics = aggregate_metrics(
        [
            {
                "id": "case-1",
                "expected_agents": ["a1"],
                "awake_agents": ["a1"],
                "top_ranked_ids": ["a1"],
                "ordinary_pool_size": 2,
                "enabled": True,
                "retrieval_reason": "ok",
                "confidence_band": "normal",
                "low_confidence_fallback": False,
                "label_source": "draft_for_human_review",
            }
        ]
    )

    assert metrics["quality_conclusion_allowed"] is False
    assert metrics["meta"]["quality_conclusion_allowed"] is False


def test_aggregate_can_exclude_draft_labels() -> None:
    records = [
        {
            "id": "manual",
            "expected_agents": ["a1"],
            "awake_agents": ["a1"],
            "top_ranked_ids": ["a1"],
            "ordinary_pool_size": 2,
            "enabled": True,
            "retrieval_reason": "ok",
            "confidence_band": "normal",
            "low_confidence_fallback": False,
            "label_source": "manual",
        },
        {
            "id": "draft",
            "expected_agents": ["a2"],
            "awake_agents": ["a2"],
            "top_ranked_ids": ["a2"],
            "ordinary_pool_size": 2,
            "enabled": True,
            "retrieval_reason": "ok",
            "confidence_band": "normal",
            "low_confidence_fallback": False,
            "label_source": "draft_for_human_review",
        },
    ]

    metrics = aggregate_metrics(records, include_draft_labels=False)

    assert metrics["case_count"] == 1
    assert metrics["label_source_counts"] == {"manual": 1}
