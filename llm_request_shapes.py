"""Request-shape helpers for OpenAI structured-output calls."""

from __future__ import annotations

from typing import Any

from model_capabilities import (
    normalize_reasoning_effort,
    supports_reasoning,
    supports_temperature,
    supports_verbosity,
)


def normalize_verbosity(verbosity: str | None) -> str | None:
    """Normalize verbosity values and drop unsupported inputs."""

    if verbosity is None:
        return None

    normalized_verbosity = verbosity.strip().lower()
    if normalized_verbosity in {"low", "medium", "high"}:
        return normalized_verbosity

    return None


def _build_responses_capability_gated_request_kwargs(
    *,
    model: str,
    maybe_temperature: float | None = None,
    reasoning_effort: str | None,
    verbosity: str | None,
) -> dict[str, Any]:
    """Build capability-gated kwargs for the Responses API."""

    normalized_reasoning_effort = normalize_reasoning_effort(model, reasoning_effort)
    normalized_verbosity = normalize_verbosity(verbosity)

    request_kwargs: dict[str, Any] = {}
    if maybe_temperature is not None and supports_temperature(
        model, normalized_reasoning_effort
    ):
        request_kwargs["temperature"] = maybe_temperature
    if supports_reasoning(model) and normalized_reasoning_effort is not None:
        request_kwargs["reasoning"] = {"effort": normalized_reasoning_effort}
    if supports_verbosity(model) and normalized_verbosity is not None:
        request_kwargs["text"] = {"verbosity": normalized_verbosity}

    return request_kwargs


def _build_chat_capability_gated_request_kwargs(
    *,
    model: str,
    maybe_temperature: float | None = None,
    reasoning_effort: str | None,
    verbosity: str | None,
) -> dict[str, Any]:
    """Build capability-gated kwargs for Chat Completions parse."""

    normalized_reasoning_effort = normalize_reasoning_effort(model, reasoning_effort)
    normalized_verbosity = normalize_verbosity(verbosity)

    request_kwargs: dict[str, Any] = {}
    if maybe_temperature is not None and supports_temperature(
        model, normalized_reasoning_effort
    ):
        request_kwargs["temperature"] = maybe_temperature
    if supports_reasoning(model) and normalized_reasoning_effort is not None:
        request_kwargs["reasoning_effort"] = normalized_reasoning_effort
    if supports_verbosity(model) and normalized_verbosity is not None:
        request_kwargs["verbosity"] = normalized_verbosity

    return request_kwargs


def build_responses_request_kwargs(
    *,
    model: str,
    store: bool,
    maybe_temperature: float | None = None,
    reasoning_effort: str | None,
    verbosity: str | None,
    max_output_tokens: int | None = None,
    previous_response_id: str | None = None,
) -> dict[str, Any]:
    """Build kwargs for `responses.parse` with endpoint-specific fields."""

    request_kwargs: dict[str, Any] = {"model": model, "store": store}
    if max_output_tokens is not None:
        request_kwargs["max_output_tokens"] = max_output_tokens
    if previous_response_id:
        request_kwargs["previous_response_id"] = previous_response_id
    request_kwargs.update(
        _build_responses_capability_gated_request_kwargs(
            model=model,
            maybe_temperature=maybe_temperature,
            reasoning_effort=reasoning_effort,
            verbosity=verbosity,
        )
    )
    return request_kwargs


def build_chat_parse_request_kwargs(
    *,
    model: str,
    maybe_temperature: float | None = None,
    reasoning_effort: str | None,
    verbosity: str | None,
) -> dict[str, Any]:
    """Build kwargs for `chat.completions.parse` without responses-only fields."""

    request_kwargs: dict[str, Any] = {"model": model}
    request_kwargs.update(
        _build_chat_capability_gated_request_kwargs(
            model=model,
            maybe_temperature=maybe_temperature,
            reasoning_effort=reasoning_effort,
            verbosity=verbosity,
        )
    )
    return request_kwargs
