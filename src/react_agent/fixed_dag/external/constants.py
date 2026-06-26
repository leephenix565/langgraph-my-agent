"""Constants for fixed-DAG external compute boundaries."""

EXTERNAL_COMPUTE_DEMO_SOURCE = "external_compute_demo_bridge"
EXTERNAL_COMPUTE_DEFAULT_SOURCE = "external_compute_default_runtime"
EXTERNAL_AGENT_REQUEST_SCHEMA_VERSION = "external_agent_request_v0"
EXTERNAL_AGENT_COMPUTE_SCHEMA_VERSION = "external_agent_compute_v0"
COMPUTE_PATH = "/v1/agent/compute"
MAX_RESPONSE_BYTES = 2_000_000
_UPSTREAM_UNSAFE_TEXT_TOKENS = (
    "api_key",
    "apikey",
    "secret",
    "token",
    "password",
    "authorization",
    "cookie",
    "set-cookie",
    "endpoint",
    "default_url",
    "raw_response",
    "raw_provider_response",
    "raw_external_json",
    "traceback",
    "chain_of_thought",
    "chain-of-thought",
    "cot",
)
_UPSTREAM_RESEARCH_POINT_TEXT_KEYS = (
    "claim",
    "support",
    "interpretation",
    "decision_implication",
    "caveat",
)

__all__ = [
    "COMPUTE_PATH",
    "EXTERNAL_AGENT_COMPUTE_SCHEMA_VERSION",
    "EXTERNAL_AGENT_REQUEST_SCHEMA_VERSION",
    "EXTERNAL_COMPUTE_DEFAULT_SOURCE",
    "EXTERNAL_COMPUTE_DEMO_SOURCE",
    "MAX_RESPONSE_BYTES",
]
