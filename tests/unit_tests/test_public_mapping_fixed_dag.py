import json

from react_agent.fixed_dag_contracts import (
    DIMENSION_GROUPS,
    build_default_fixed_dag_plan,
)
from react_agent.public_mapping import build_workflow_snapshot


def test_public_workflow_fallback_uses_fixed_dag_snapshot_contract() -> None:
    workflow = build_workflow_snapshot(
        {"fixed_dag_plan": build_default_fixed_dag_plan("q")},
        "replay",
    )
    payload = workflow.model_dump(mode="json", by_alias=True)

    assert payload["schema"] == "workflow_snapshot_v2"
    assert payload["finalSource"] == "reset_skeleton"
    assert {item["id"] for item in payload["dimensionGroups"]} == set(DIMENSION_GROUPS)
    assert payload["provenance"]["providerInvoked"] is False
    assert payload["provenance"]["externalInvoked"] is False
    text = json.dumps(payload)
    assert "layerMode" not in text
    assert "fusionSteps" not in text
