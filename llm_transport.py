"""Transport helpers for OpenAI client construction and retries."""

from __future__ import annotations

import hashlib
import logging
import os
import time
from typing import Any, Callable

import streamlit as st
from openai import OpenAI

from llm_error_mapping import OpenAICallError, _is_retryable_openai_exception
from settings_openai import OpenAISettings, load_openai_settings

logger = logging.getLogger(__name__)


def _safe_hash(text: str, n: int = 10) -> str:
    return hashlib.sha1(text.encode("utf-8"), usedforsecurity=False).hexdigest()[:n]


def _build_openai_client(settings: OpenAISettings) -> OpenAI:
    """Create an OpenAI SDK client from normalized app settings."""

    timeout = settings.openai_request_timeout
    if settings.openai_api_key:
        return OpenAI(api_key=settings.openai_api_key, timeout=timeout)

    # Allow OpenAI SDK default env var fallback handling.
    return OpenAI(timeout=timeout)


def _build_openai_client_from_runtime_settings(
    *,
    timeout_seconds: float,
    explicit_api_key: str | None,
) -> OpenAI:
    """Create an OpenAI SDK client from runtime cache key inputs."""

    if explicit_api_key:
        return OpenAI(api_key=explicit_api_key, timeout=timeout_seconds)
    return OpenAI(timeout=timeout_seconds)


@st.cache_resource
def _get_cached_openai_client(
    timeout_seconds: float,
    api_key_hash: str,
    has_any_api_key: bool,
    _explicit_api_key: str | None = None,
) -> OpenAI:
    """Return cached OpenAI client keyed by non-sensitive runtime fingerprint."""

    # Keep these parameters explicit for deterministic cache invalidation.
    _ = (api_key_hash, has_any_api_key)
    return _build_openai_client_from_runtime_settings(
        timeout_seconds=timeout_seconds,
        explicit_api_key=_explicit_api_key,
    )


def get_openai_client(*, settings: OpenAISettings | None = None) -> OpenAI:
    """Create a cached OpenAI client.

    Priority for API key:
    1) st.secrets["OPENAI_API_KEY"] (common in Streamlit deployments)
    2) Environment variable OPENAI_API_KEY (local dev / CI)
    """
    settings = settings or load_openai_settings()
    resolved_api_key = settings.openai_api_key or os.getenv("OPENAI_API_KEY")
    has_any_api_key = bool(resolved_api_key)
    api_key_hash = _safe_hash(resolved_api_key) if resolved_api_key else "missing"

    return _get_cached_openai_client(
        timeout_seconds=settings.openai_request_timeout,
        api_key_hash=api_key_hash,
        has_any_api_key=has_any_api_key,
        _explicit_api_key=settings.openai_api_key,
    )


def _has_any_openai_api_key(settings: OpenAISettings) -> bool:
    """Check whether a key is present via app settings or SDK env fallback."""

    return bool(settings.openai_api_key or os.getenv("OPENAI_API_KEY"))


def _raise_missing_api_key_hint() -> None:
    """Raise a clear message for UI and logs without exposing secrets."""

    raise OpenAICallError(
        "OpenAI API-Key fehlt (DE) / Missing OpenAI API key (EN).",
        debug_detail="No OPENAI_API_KEY found in st.secrets or environment.",
        error_code="OPENAI_AUTH",
    )


def _run_openai_call_with_retry(
    *,
    fn: Callable[[], Any],
    label: str,
    max_attempts: int = 3,
    base_delay_seconds: float = 0.4,
    on_retry: Callable[[], None] | None = None,
    sleep: Callable[[float], None] = time.sleep,
) -> Any:
    """Run OpenAI call with exponential backoff for transient errors."""

    for attempt in range(1, max_attempts + 1):
        try:
            return fn()
        except Exception as exc:
            if not _is_retryable_openai_exception(exc) or attempt >= max_attempts:
                raise
            if on_retry is not None:
                on_retry()
            delay = base_delay_seconds * (2 ** (attempt - 1))
            logger.warning(
                "%s transient error (%s), retrying in %.2fs (%d/%d).",
                label,
                type(exc).__name__,
                delay,
                attempt,
                max_attempts,
            )
            sleep(delay)
