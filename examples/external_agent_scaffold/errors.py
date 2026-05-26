from __future__ import annotations

from typing import Optional

from schemas import TypedError


def typed_error(
    error_code: str,
    error_message: str,
    stage: str,
    *,
    recoverable: bool,
    retryable: bool,
    user_action_required: bool,
    suggested_user_action: Optional[str] = None,
) -> TypedError:
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
    return typed_error(
        "EMPTY_QUESTION",
        "question must not be empty",
        "request_validation",
        recoverable=True,
        retryable=False,
        user_action_required=True,
        suggested_user_action="Provide a non-empty question.",
    )


def forced_error() -> TypedError:
    return typed_error(
        "EXAMPLE_FORCED_ERROR",
        "the request asked the scaffold to return an example error",
        "example_handler",
        recoverable=True,
        retryable=False,
        user_action_required=False,
        suggested_user_action="Remove options.force_error or send a normal question.",
    )

