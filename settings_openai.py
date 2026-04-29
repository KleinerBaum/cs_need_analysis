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
    openai_model_override: str | None
    default_model: str
    lightweight_model: str
    medium_reasoning_model: str
    high_reasoning_model: str
    reasoning_effort: str | None
    verbosity: str | None
    openai_request_timeout: float
    esco_vector_store_id: str | None
    esco_rag_enabled: bool
    esco_rag_max_results: int
    task_max_output_tokens: dict[str, int | None]
    task_max_bullets_per_field: dict[str, int | None]
    task_max_sentences_per_field: dict[str, int | None]
    resolved_from: dict[str, str]


_FINAL_MODEL_FALLBACK = "gpt-4o-mini"
DEFAULT_TIMEOUT_SECONDS = 120.0
_TASK_KINDS = (
    "extract_job_ad",
    "generate_question_plan",
    "generate_vacancy_brief",
    "generate_job_ad",
    "generate_interview_sheet_hr",
    "generate_interview_sheet_hm",
    "generate_boolean_search",
    "generate_employment_contract",
    "generate_requirement_gap_suggestions",
)


_HARD_DEFAULTS: dict[str, str] = {
    "OPENAI_API_KEY": "",
    "OPENAI_MODEL": "",
    "DEFAULT_MODEL": "",
    "LIGHTWEIGHT_MODEL": _FINAL_MODEL_FALLBACK,
    "MEDIUM_REASONING_MODEL": _FINAL_MODEL_FALLBACK,
    "HIGH_REASONING_MODEL": "o3-mini",
    "OPENAI_REQUEST_TIMEOUT": str(int(DEFAULT_TIMEOUT_SECONDS)),
    "ESCO_VECTOR_STORE_ID": "",
    "ESCO_RAG_ENABLED": "false",
    "ESCO_RAG_MAX_RESULTS": "8",
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


def _resolve_config_value_with_source(key: str) -> tuple[str, str]:
    """Resolve a setting and return both value and non-sensitive source."""

    nested = _safe_nested_secret_get("openai", key)
    if nested is not None:
        return str(nested), "nested_secret"

    direct = _safe_secret_get(key)
    if direct is not None:
        return str(direct), "root_secret"

    env_val = os.getenv(key)
    if env_val is not None:
        return env_val, "env"

    return _HARD_DEFAULTS.get(key, ""), "default"


def _resolve_config_value(key: str) -> str:
    """Resolve a setting via secrets/env/default using the configured precedence."""

    value, _ = _resolve_config_value_with_source(key)
    return value


def _resolve_optional_config_value_with_source(key: str) -> tuple[str | None, str]:
    """Resolve a setting and return ``None`` when unset/blank."""

    value, source = _resolve_config_value_with_source(key)
    value = value.strip()
    if not value:
        return None, "default"
    return value, source


def _resolve_optional_config_value(key: str) -> str | None:
    """Resolve a setting and return ``None`` when unset/blank."""

    value, _ = _resolve_optional_config_value_with_source(key)
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


def _parse_optional_positive_int(raw: str | None) -> int | None:
    """Parse optional positive integer values and return ``None`` when invalid."""

    if raw is None:
        return None
    text = raw.strip()
    if not text:
        return None
    try:
        parsed = int(text)
    except ValueError:
        return None
    if parsed <= 0:
        return None
    return parsed


def _parse_bool(raw: str | None, default_value: bool) -> bool:
    """Parse boolean-like string values with a conservative fallback."""

    if raw is None:
        return default_value
    text = raw.strip().lower()
    if text in {"1", "true", "yes", "on"}:
        return True
    if text in {"0", "false", "no", "off"}:
        return False
    return default_value


def load_openai_settings() -> OpenAISettings:
    """Load OpenAI-related settings from secrets/env/defaults."""

    openai_api_key = _resolve_optional_config_value("OPENAI_API_KEY")
    resolved_from: dict[str, str] = {}
    default_model_candidate, default_model_source = (
        _resolve_optional_config_value_with_source("DEFAULT_MODEL")
    )
    default_model = default_model_candidate or _FINAL_MODEL_FALLBACK
    openai_model_override, openai_model_source = (
        _resolve_optional_config_value_with_source("OPENAI_MODEL")
    )
    openai_model = openai_model_override or default_model
    resolved_from["OPENAI_MODEL"] = openai_model_source
    resolved_from["DEFAULT_MODEL"] = default_model_source
    lightweight_model = (
        _resolve_optional_config_value("LIGHTWEIGHT_MODEL") or _FINAL_MODEL_FALLBACK
    )
    medium_reasoning_model = (
        _resolve_optional_config_value("MEDIUM_REASONING_MODEL")
        or _FINAL_MODEL_FALLBACK
    )
    high_reasoning_model = _resolve_config_value("HIGH_REASONING_MODEL")
    reasoning_effort, reasoning_source = _resolve_optional_config_value_with_source(
        "REASONING_EFFORT"
    )
    verbosity, verbosity_source = _resolve_optional_config_value_with_source(
        "VERBOSITY"
    )
    timeout_raw, timeout_source = _resolve_config_value_with_source(
        "OPENAI_REQUEST_TIMEOUT"
    )
    resolved_from["REASONING_EFFORT"] = reasoning_source
    resolved_from["VERBOSITY"] = verbosity_source
    resolved_from["OPENAI_REQUEST_TIMEOUT"] = timeout_source

    timeout_default = DEFAULT_TIMEOUT_SECONDS
    openai_request_timeout = _parse_timeout_seconds(timeout_raw, timeout_default)
    esco_vector_store_id, esco_vector_store_source = (
        _resolve_optional_config_value_with_source("ESCO_VECTOR_STORE_ID")
    )
    esco_rag_enabled_raw, esco_rag_enabled_source = _resolve_config_value_with_source(
        "ESCO_RAG_ENABLED"
    )
    esco_rag_max_results_raw, esco_rag_max_results_source = (
        _resolve_config_value_with_source("ESCO_RAG_MAX_RESULTS")
    )
    esco_rag_max_results = _parse_optional_positive_int(esco_rag_max_results_raw) or 8
    esco_rag_enabled = _parse_bool(esco_rag_enabled_raw, False) and bool(
        esco_vector_store_id
    )
    resolved_from["ESCO_VECTOR_STORE_ID"] = esco_vector_store_source
    resolved_from["ESCO_RAG_ENABLED"] = esco_rag_enabled_source
    resolved_from["ESCO_RAG_MAX_RESULTS"] = esco_rag_max_results_source
    task_max_output_tokens: dict[str, int | None] = {}
    task_max_bullets_per_field: dict[str, int | None] = {}
    task_max_sentences_per_field: dict[str, int | None] = {}
    for task_kind in _TASK_KINDS:
        task_upper = task_kind.upper()
        max_tokens_raw, max_tokens_source = _resolve_config_value_with_source(
            f"{task_upper}_MAX_OUTPUT_TOKENS"
        )
        max_bullets_raw, max_bullets_source = _resolve_config_value_with_source(
            f"{task_upper}_MAX_BULLETS_PER_FIELD"
        )
        max_sentences_raw, max_sentences_source = _resolve_config_value_with_source(
            f"{task_upper}_MAX_SENTENCES_PER_FIELD"
        )
        task_max_output_tokens[task_kind] = _parse_optional_positive_int(max_tokens_raw)
        task_max_bullets_per_field[task_kind] = _parse_optional_positive_int(
            max_bullets_raw
        )
        task_max_sentences_per_field[task_kind] = _parse_optional_positive_int(
            max_sentences_raw
        )
        resolved_from[f"{task_upper}_MAX_OUTPUT_TOKENS"] = max_tokens_source
        resolved_from[f"{task_upper}_MAX_BULLETS_PER_FIELD"] = max_bullets_source
        resolved_from[f"{task_upper}_MAX_SENTENCES_PER_FIELD"] = max_sentences_source

    return OpenAISettings(
        openai_api_key=openai_api_key,
        openai_model=openai_model,
        openai_model_override=openai_model_override,
        default_model=default_model,
        lightweight_model=lightweight_model,
        medium_reasoning_model=medium_reasoning_model,
        high_reasoning_model=high_reasoning_model,
        reasoning_effort=reasoning_effort,
        verbosity=verbosity,
        openai_request_timeout=openai_request_timeout,
        esco_vector_store_id=esco_vector_store_id,
        esco_rag_enabled=esco_rag_enabled,
        esco_rag_max_results=esco_rag_max_results,
        task_max_output_tokens=task_max_output_tokens,
        task_max_bullets_per_field=task_max_bullets_per_field,
        task_max_sentences_per_field=task_max_sentences_per_field,
        resolved_from=resolved_from,
    )
