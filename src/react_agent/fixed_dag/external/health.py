"""Health-only identity validation for external fixed-DAG services.

The runtime compute adapter remains strict: mapped compute payloads must use the
formal fixed-DAG ``agent_id``.  This module only classifies controlled
``GET /health`` payloads for readiness audits, where some already-deployed
services still expose an explicit service-local primary id plus a formal
``fixed_dag_agent_id``.

(Moved from ``fixed_dag_external_health.py`` during Phase 1 consolidation.)
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any, Literal, TypedDict

from react_agent.fixed_dag_contracts import RESET_RUNTIME_AGENT_IDS

HealthIdentityProfile = Literal[
    "canonical",
    "explicit_bridge_compatibility",
    "registered_legacy_compatibility",
    "invalid",
]

HEALTH_SCHEMA_VERSION = "external_agent_health_v0"

# Explicit health-only aliases observed in controlled production readiness
# audits.  They are compatibility debt; they must not be accepted by compute
# mapping as formal ids.
EXTERNAL_HEALTH_IDENTITY_ALIASES: dict[str, tuple[str, ...]] = {
    "value_traditional_valuation": ("valuation_traditional",),
    "value_ml_valuation": ("valuation_ml",),
    "value_meta_valuation": ("valuation_meta",),
    "risk_crash": ("crash_risk",),
    "risk_financial_fraud": ("financial_fraud_agent",),
    "risk_identification": ("market_risk_reasoning",),
    "risk_compliance_review": ("announcement_compliance",),
    "macro_commodity_pricing": ("price_influence_agent",),
    "risk_composite": ("risk_synthesis",),
    "macro_composite": ("macro_synthesis", "macro_synthesis_service"),
}


class HealthIdentityValidation(TypedDict):
    """Structured result for a controlled health identity check."""

    expected_agent_id: str
    observed_agent_id: str
    observed_fixed_dag_agent_id: str
    observed_external_agent_id: str
    health_identity_pass: bool
    identity_profile: HealthIdentityProfile
    compatibility_debt: bool
    reason: str


def _text(value: Any) -> str:
    return str(value or "").strip()


def _legacy_primary_id(value: str) -> bool:
    return bool(re.fullmatch(r"a\d{1,3}(?:[_-].*)?", value.strip().lower()))


def _alias_index() -> dict[str, list[str]]:
    index: dict[str, list[str]] = {}
    for formal_id, aliases in EXTERNAL_HEALTH_IDENTITY_ALIASES.items():
        for alias in aliases:
            index.setdefault(alias, []).append(formal_id)
    return index


def _result(
    *,
    expected_agent_id: str,
    agent_id: str,
    fixed_dag_agent_id: str,
    external_agent_id: str,
    passed: bool,
    profile: HealthIdentityProfile,
    debt: bool,
    reason: str,
) -> HealthIdentityValidation:
    return {
        "expected_agent_id": expected_agent_id,
        "observed_agent_id": agent_id,
        "observed_fixed_dag_agent_id": fixed_dag_agent_id,
        "observed_external_agent_id": external_agent_id,
        "health_identity_pass": passed,
        "identity_profile": profile,
        "compatibility_debt": debt,
        "reason": reason,
    }


def validate_external_health_identity(
    payload: Mapping[str, Any] | None,
    *,
    expected_agent_id: str,
    expected_external_agent_id: str = "",
    expected_port: int | None = None,
    observed_port: int | None = None,
    source_matches: bool = True,
) -> HealthIdentityValidation:
    """Classify a health payload against a formal fixed-DAG service identity.

    ``registered_legacy_compatibility`` is deliberately narrower than compute
    mapping: it requires an explicit source-controlled alias, matching source
    and matching port evidence from the caller.
    """
    expected_agent_id = _text(expected_agent_id)
    expected_external_agent_id = _text(expected_external_agent_id)
    if not expected_agent_id or expected_agent_id not in RESET_RUNTIME_AGENT_IDS:
        return _result(
            expected_agent_id=expected_agent_id,
            agent_id="",
            fixed_dag_agent_id="",
            external_agent_id="",
            passed=False,
            profile="invalid",
            debt=False,
            reason="unknown_expected_agent_id",
        )
    if not source_matches:
        return _result(
            expected_agent_id=expected_agent_id,
            agent_id="",
            fixed_dag_agent_id="",
            external_agent_id="",
            passed=False,
            profile="invalid",
            debt=False,
            reason="source_mismatch",
        )
    if not isinstance(payload, Mapping):
        return _result(
            expected_agent_id=expected_agent_id,
            agent_id="",
            fixed_dag_agent_id="",
            external_agent_id="",
            passed=False,
            profile="invalid",
            debt=False,
            reason="health_payload_not_object",
        )

    agent_id = _text(payload.get("agent_id"))
    fixed_dag_agent_id = _text(payload.get("fixed_dag_agent_id"))
    external_agent_id = _text(payload.get("external_agent_id"))

    if fixed_dag_agent_id and fixed_dag_agent_id != expected_agent_id:
        return _result(
            expected_agent_id=expected_agent_id,
            agent_id=agent_id,
            fixed_dag_agent_id=fixed_dag_agent_id,
            external_agent_id=external_agent_id,
            passed=False,
            profile="invalid",
            debt=False,
            reason="fixed_dag_agent_id_mismatch",
        )
    if agent_id == expected_agent_id:
        if fixed_dag_agent_id and fixed_dag_agent_id != expected_agent_id:
            reason = "fixed_dag_agent_id_mismatch"
            passed = False
            profile: HealthIdentityProfile = "invalid"
        else:
            reason = "canonical"
            passed = True
            profile = "canonical"
        return _result(
            expected_agent_id=expected_agent_id,
            agent_id=agent_id,
            fixed_dag_agent_id=fixed_dag_agent_id,
            external_agent_id=external_agent_id,
            passed=passed,
            profile=profile,
            debt=False,
            reason=reason,
        )

    aliases = set(EXTERNAL_HEALTH_IDENTITY_ALIASES.get(expected_agent_id, ()))
    observed_service_ids = {value for value in (agent_id, external_agent_id) if value}

    if fixed_dag_agent_id == expected_agent_id:
        if not observed_service_ids:
            reason = "service_identity_missing"
            passed = False
        elif observed_service_ids <= aliases or (
            expected_external_agent_id
            and observed_service_ids <= {expected_external_agent_id, *aliases}
        ):
            reason = "explicit_bridge_compatibility"
            passed = True
        else:
            reason = "service_identity_not_registered"
            passed = False
        return _result(
            expected_agent_id=expected_agent_id,
            agent_id=agent_id,
            fixed_dag_agent_id=fixed_dag_agent_id,
            external_agent_id=external_agent_id,
            passed=passed,
            profile="explicit_bridge_compatibility" if passed else "invalid",
            debt=passed,
            reason=reason,
        )

    if _legacy_primary_id(agent_id):
        return _result(
            expected_agent_id=expected_agent_id,
            agent_id=agent_id,
            fixed_dag_agent_id=fixed_dag_agent_id,
            external_agent_id=external_agent_id,
            passed=False,
            profile="invalid",
            debt=False,
            reason="legacy_primary_id_not_allowed",
        )
    if expected_agent_id == "risk_composite" and agent_id == "company_sentiment_radar":
        return _result(
            expected_agent_id=expected_agent_id,
            agent_id=agent_id,
            fixed_dag_agent_id=fixed_dag_agent_id,
            external_agent_id=external_agent_id,
            passed=False,
            profile="invalid",
            debt=False,
            reason="sentiment_company_radar_not_risk",
        )

    alias_index = _alias_index()
    alias_owners = alias_index.get(agent_id, [])
    if len(alias_owners) > 1:
        reason = "legacy_alias_ambiguous"
        passed = False
    elif alias_owners != [expected_agent_id]:
        reason = "legacy_alias_not_registered"
        passed = False
    elif expected_port is None or observed_port != expected_port:
        reason = "legacy_alias_port_mismatch"
        passed = False
    elif external_agent_id and external_agent_id not in aliases:
        reason = "legacy_external_agent_id_not_registered"
        passed = False
    else:
        reason = "registered_legacy_compatibility"
        passed = True

    return _result(
        expected_agent_id=expected_agent_id,
        agent_id=agent_id,
        fixed_dag_agent_id=fixed_dag_agent_id,
        external_agent_id=external_agent_id,
        passed=passed,
        profile="registered_legacy_compatibility" if passed else "invalid",
        debt=passed,
        reason=reason,
    )


__all__ = [
    "EXTERNAL_HEALTH_IDENTITY_ALIASES",
    "HEALTH_SCHEMA_VERSION",
    "HealthIdentityProfile",
    "HealthIdentityValidation",
    "validate_external_health_identity",
]
