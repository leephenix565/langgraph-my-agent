from pydantic import TypeAdapter

from react_agent.agents import AgentOutput
from react_agent.state import State


def test_agent_output_schema_is_generatable() -> None:
    schema = TypeAdapter(AgentOutput).json_schema()

    assert schema["type"] == "object"
    assert "analysis" in schema.get("properties", {})
    assert "parse_ok" in schema.get("properties", {})
    assert "contract" in schema.get("properties", {})


def test_state_schema_accepts_agent_output_fields() -> None:
    schema = TypeAdapter(State).json_schema()

    assert schema["type"] == "object"
    assert "analyst_results" in schema.get("properties", {})
    assert "ephemeral_results" in schema.get("properties", {})
