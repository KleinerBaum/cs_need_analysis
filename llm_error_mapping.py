"""OpenAI error mapping helpers for llm_client."""

from __future__ import annotations

import re

from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    RateLimitError,
)
from pydantic import ValidationError


class OpenAICallError(RuntimeError):
    """Application-level error with user-facing and debug-safe details."""

    def __init__(
        self,
        ui_message: str,
        *,
        debug_detail: str | None = None,
        error_code: str | None = None,
    ) -> None:
        super().__init__(ui_message)
        self.ui_message = ui_message
        self.debug_detail = debug_detail
        self.error_code = error_code


_STRUCTURED_OUTPUT_RETRYABLE_ERROR_CODES = frozenset(
    {
        "OPENAI_BAD_REQUEST_STRUCTURED_OUTPUT_UNSUPPORTED",
        "OPENAI_BAD_REQUEST_MODEL_CAPABILITY",
        "OPENAI_BAD_REQUEST_ENDPOINT_INCOMPATIBLE",
    }
)


def _error_from_openai_exception(exc: Exception, *, endpoint: str) -> OpenAICallError:
    """Convert SDK exceptions into concise, user-safe app errors."""
    status_code = getattr(exc, "status_code", None)

    def _extract_api_error_message() -> str:
        """Extract nested API error messages from OpenAI SDK exceptions."""

        body = getattr(exc, "body", None)
        if isinstance(body, dict):
            error_obj = body.get("error")
            if isinstance(error_obj, dict):
                message = error_obj.get("message")
                if isinstance(message, str):
                    return message
            elif isinstance(error_obj, str):
                return error_obj
            message = body.get("message")
            if isinstance(message, str):
                return message

        error_attr = getattr(exc, "error", None)
        if isinstance(error_attr, dict):
            message = error_attr.get("message")
            if isinstance(message, str):
                return message

        return ""

    def _sanitize_api_message(message: str, *, max_len: int = 200) -> str:
        """Mask likely sensitive fragments and keep message compact."""

        collapsed = " ".join(message.split())
        redacted = re.sub(
            r"(?i)\b(sk-[A-Za-z0-9_-]{8,})\b", "[redacted-key]", collapsed
        )
        redacted = re.sub(
            r"(?i)\bbearer\s+[A-Za-z0-9._-]+", "Bearer [redacted]", redacted
        )
        redacted = re.sub(
            r"(?i)\b(api[_-]?key|token|secret|password)\s*[:=]\s*[^,;\s]+",
            r"\1=[redacted]",
            redacted,
        )

        if len(redacted) <= max_len:
            return redacted
        return f"{redacted[: max_len - 1].rstrip()}…"

    api_message_raw = _extract_api_error_message()
    api_message_sanitized = (
        _sanitize_api_message(api_message_raw) if api_message_raw else ""
    )
    api_message_norm = api_message_sanitized.lower()

    def _debug_detail() -> str:
        details = [f"endpoint={endpoint}", f"exception={type(exc).__name__}"]
        if status_code is not None:
            details.append(f"status_code={status_code}")
        if api_message_sanitized:
            details.append(f"api_message={api_message_sanitized}")
        return ", ".join(details)

    def _classify_bad_request() -> tuple[str, str]:
        """Return ``(error_code, ui_message)`` for common 400 API causes."""

        message = api_message_norm
        model_not_found_hint = (
            "model not found" in message or "unknown model" in message
        )
        endpoint_incompatibility_hint = (
            "endpoint" in message
            and ("not supported" in message or "incompatible" in message)
        ) or (
            "use /v1/chat/completions" in message
            or "use /v1/responses" in message
            or "responses api" in message
            or "chat.completions" in message
        )
        structured_output_hint = (
            "response_format" in message
            or "text_format" in message
            or "structured output" in message
            or "json_schema" in message
            or "json schema" in message
        ) and (
            "unsupported" in message
            or "not supported" in message
            or "unknown parameter" in message
            or "not allowed" in message
            or "invalid" in message
        )
        model_capability_hint = (
            "does not support" in message
            or "unsupported for model" in message
            or "model capability" in message
            or "not available for this model" in message
        ) and (
            "temperature" in message
            or "reasoning" in message
            or "verbosity" in message
            or "response_format" in message
            or "text_format" in message
            or "json_schema" in message
            or "max_output_tokens" in message
        )
        unsupported_hint = (
            "unsupported parameter" in message
            or "unknown parameter" in message
            or "not allowed" in message
            or "invalid type" in message
        )

        if model_not_found_hint:
            return (
                "OPENAI_BAD_REQUEST_MODEL_NOT_FOUND",
                "OpenAI-Modell nicht gefunden (DE) / OpenAI model not found (EN).",
            )
        if endpoint_incompatibility_hint:
            return (
                "OPENAI_BAD_REQUEST_ENDPOINT_INCOMPATIBLE",
                "OpenAI-Endpoint inkompatibel (DE) / Incompatible OpenAI endpoint (EN).",
            )
        if structured_output_hint:
            return (
                "OPENAI_BAD_REQUEST_STRUCTURED_OUTPUT_UNSUPPORTED",
                "Structured Output nicht unterstützt (DE) / Structured output unsupported (EN).",
            )
        if model_capability_hint:
            return (
                "OPENAI_BAD_REQUEST_MODEL_CAPABILITY",
                "OpenAI-Modellfähigkeit passt nicht (DE) / OpenAI model capability mismatch (EN).",
            )
        if unsupported_hint:
            return (
                "OPENAI_BAD_REQUEST_UNSUPPORTED_PARAMETER",
                "Nicht unterstützter OpenAI-Parameter (DE) / Unsupported OpenAI parameter (EN).",
            )
        return (
            "OPENAI_BAD_REQUEST_INVALID",
            "Ungültige OpenAI-Parameter (DE) / Invalid OpenAI parameters (EN).",
        )

    if isinstance(exc, (APITimeoutError, TimeoutError)):
        return OpenAICallError(
            "OpenAI-Timeout (DE) / OpenAI timeout (EN). Bitte erneut versuchen.",
            debug_detail=_debug_detail(),
            error_code="OPENAI_TIMEOUT",
        )

    if isinstance(exc, APIStatusError) and exc.status_code == 400:
        error_code, ui_message = _classify_bad_request()
        return OpenAICallError(
            ui_message,
            debug_detail=_debug_detail(),
            error_code=error_code,
        )

    if isinstance(exc, AuthenticationError):
        return OpenAICallError(
            "OpenAI-Authentifizierung fehlgeschlagen (DE) / OpenAI authentication failed (EN).",
            debug_detail=_debug_detail(),
            error_code="OPENAI_AUTH",
        )

    if isinstance(exc, APIConnectionError):
        return OpenAICallError(
            "OpenAI-Verbindung fehlgeschlagen (DE) / OpenAI connection failed (EN).",
            debug_detail=_debug_detail(),
            error_code="OPENAI_CONNECTION",
        )

    return OpenAICallError(
        "OpenAI-Aufruf fehlgeschlagen (DE) / OpenAI request failed (EN).",
        debug_detail=_debug_detail(),
        error_code="OPENAI_UNKNOWN",
    )


def _error_from_structured_output_exception(exc: Exception) -> OpenAICallError:
    """Map schema/validation failures to user-safe structured-output messages."""

    if isinstance(exc, ValidationError):
        return OpenAICallError(
            "Antwortformat ungültig (DE) / Invalid structured output (EN).",
            debug_detail="Pydantic validation failed for structured output.",
            error_code="OPENAI_PARSE",
        )

    return OpenAICallError(
        "Structured Output fehlgeschlagen (DE) / Structured output failed (EN).",
        debug_detail=f"Structured output parsing error: {type(exc).__name__}.",
        error_code="OPENAI_PARSE",
    )


def _is_retryable_openai_exception(exc: Exception) -> bool:
    """Return True for transient errors worth retrying."""

    return isinstance(
        exc, (APITimeoutError, TimeoutError, APIConnectionError, RateLimitError)
    )
