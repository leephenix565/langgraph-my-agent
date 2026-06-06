"""Typed error helpers for the sample fixed DAG external agent."""

from __future__ import annotations

from schemas import TypedError


def typed_error(
    error_code: str,
    error_message: str,
    stage: str,
    *,
    recoverable: bool,
    retryable: bool,
    user_action_required: bool,
    suggested_user_action: str = "",
) -> TypedError:
    """Build a structured error without traceback or secret fields."""
    return TypedError(
        error_code=error_code,
        error_message=error_message,
        stage=stage,
        recoverable=recoverable,
        retryable=retryable,
        user_action_required=user_action_required,
        suggested_user_action=suggested_user_action,
    )


def empty_question_error() -> TypedError:
    """Return the standard empty-question validation error."""
    return typed_error(
        "EMPTY_QUESTION",
        "question must not be empty",
        "request_validation",
        recoverable=True,
        retryable=False,
        user_action_required=True,
        suggested_user_action="Provide a non-empty question.",
    )


def legacy_agent_id_error(agent_id: str) -> TypedError:
    """Return an error for old aNN ids used as current primary ids."""
    return typed_error(
        "LEGACY_AGENT_ID_AS_PRIMARY",
        f"{agent_id} is a legacy migration id, not a fixed DAG primary agent_id",
        "id_validation",
        recoverable=True,
        retryable=False,
        user_action_required=True,
        suggested_user_action="Use a fixed DAG snake_case agent_id such as value_ml_valuation.",
    )


def target_required_error() -> TypedError:
    """Return the standard missing-target validation error."""
    return typed_error(
        "TARGET_REQUIRED",
        "target must not be empty",
        "request_validation",
        recoverable=True,
        retryable=False,
        user_action_required=True,
        suggested_user_action="Provide a target symbol or entity.",
    )
