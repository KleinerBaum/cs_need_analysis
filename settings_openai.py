"""OpenAI runtime settings loading utilities."""

from __future__ import annotations

from dataclasses import dataclass
import math
import os
from typing import Any

import streamlit as st


@dataclass(frozen=True)
class OpenAISettings:
    """Normalized OpenAI configuration values for the app runtime."""

    openai_api_key: str | None
    openai_model: str
    default_model: str
    lightweight_model: str
    medium_reasoning_model: str
    high_reasoning_model: str
    reasoning_effort: str
    verbosity: str
    openai_request_timeout: float


_FINAL_MODEL_FALLBACK = "gpt-4o-mini"


_HARD_DEFAULTS: dict[str, str] = {
    "OPENAI_API_KEY": "",
    "OPENAI_MODEL": "",
    "DEFAULT_MODEL": "",
    "LIGHTWEIGHT_MODEL": _FINAL_MODEL_FALLBACK,
    "MEDIUM_REASONING_MODEL": _FINAL_MODEL_FALLBACK,
    "HIGH_REASONING_MODEL": "o3-mini",
    "REASONING_EFFORT": "medium",
    "VERBOSITY": "medium",
    "OPENAI_REQUEST_TIMEOUT": "60",
}


def _safe_secret_get(key: str) -> Any | None:
    """Return a top-level Streamlit secret value or ``None`` when unavailable."""

    try:
        return st.secrets.get(key)  # type: ignore[attr-defined]
    except Exception:
        return None


def _safe_nested_secret_get(namespace: str, key: str) -> Any | None:
    """Return a nested Streamlit secret value or ``None`` when unavailable."""

    try:
        section = st.secrets.get(namespace)  # type: ignore[attr-defined]
    except Exception:
        return None

    if section is None:
        return None

    try:
        return section.get(key)
    except Exception:
        return None


def _resolve_config_value(key: str) -> str:
    """Resolve a setting via secrets/env/default using the configured precedence."""

    nested = _safe_nested_secret_get("openai", key)
    if nested is not None:
        return str(nested)

    direct = _safe_secret_get(key)
    if direct is not None:
        return str(direct)

    env_val = os.getenv(key)
    if env_val is not None:
        return env_val

    return _HARD_DEFAULTS[key]


def _resolve_optional_config_value(key: str) -> str | None:
    """Resolve a setting and return ``None`` when unset/blank."""

    value = _resolve_config_value(key).strip()
    if not value:
        return None
    return value


def _parse_timeout_seconds(raw: str, default_value: float) -> float:
    """Parse timeout values robustly and return a positive seconds value."""

    text = raw.strip().replace(",", ".")
    if not text:
        return default_value

    try:
        parsed = float(text)
    except ValueError:
        return default_value

    if not math.isfinite(parsed) or parsed <= 0:
        return default_value
    return parsed


def load_openai_settings() -> OpenAISettings:
    """Load OpenAI-related settings from secrets/env/defaults."""

    openai_api_key = _resolve_optional_config_value("OPENAI_API_KEY")
    default_model = (
        _resolve_optional_config_value("DEFAULT_MODEL") or _FINAL_MODEL_FALLBACK
    )
    openai_model = _resolve_optional_config_value("OPENAI_MODEL") or default_model
    lightweight_model = (
        _resolve_optional_config_value("LIGHTWEIGHT_MODEL") or _FINAL_MODEL_FALLBACK
    )
    medium_reasoning_model = (
        _resolve_optional_config_value("MEDIUM_REASONING_MODEL")
        or _FINAL_MODEL_FALLBACK
    )
    high_reasoning_model = _resolve_config_value("HIGH_REASONING_MODEL")
    reasoning_effort = _resolve_config_value("REASONING_EFFORT")
    verbosity = _resolve_config_value("VERBOSITY")
    timeout_raw = _resolve_config_value("OPENAI_REQUEST_TIMEOUT")

    timeout_default = float(_HARD_DEFAULTS["OPENAI_REQUEST_TIMEOUT"])
    openai_request_timeout = _parse_timeout_seconds(timeout_raw, timeout_default)

    return OpenAISettings(
        openai_api_key=openai_api_key,
        openai_model=openai_model,
        default_model=default_model,
        lightweight_model=lightweight_model,
        medium_reasoning_model=medium_reasoning_model,
        high_reasoning_model=high_reasoning_model,
        reasoning_effort=reasoning_effort,
        verbosity=verbosity,
        openai_request_timeout=openai_request_timeout,
    )
