# state.py
"""Session state management.

Streamlit re-runs the script on each interaction; st.session_state is the backbone
of a wizard workflow.
"""

from __future__ import annotations

from typing import Any, Dict

import streamlit as st

from constants import DEFAULT_LANGUAGE, SSKey, STEPS
from settings_openai import load_openai_settings


def get_model_override() -> str | None:
    """Return a cleaned model override from the UI, if provided."""

    model_override = st.session_state.get(SSKey.MODEL.value)
    if isinstance(model_override, str):
        cleaned_override = model_override.strip()
        if cleaned_override:
            return cleaned_override
    return None


def get_active_model() -> str:
    """Return UI override model or OpenAI settings fallback model."""

    return get_model_override() or load_openai_settings().openai_model


def init_session_state() -> None:
    defaults = {
        SSKey.CURRENT_STEP.value: STEPS[0].key,
        SSKey.LANGUAGE.value: DEFAULT_LANGUAGE,
        SSKey.MODEL.value: load_openai_settings().openai_model,
        SSKey.STORE_API_OUTPUT.value: False,
        SSKey.SOURCE_TEXT.value: "",
        SSKey.SOURCE_FILE_META.value: {},
        SSKey.SOURCE_REDACT_PII.value: True,
        SSKey.JOB_EXTRACT.value: None,
        SSKey.QUESTION_PLAN.value: None,
        SSKey.QUESTION_LIMITS.value: {},
        SSKey.ANSWERS.value: {},
        SSKey.BRIEF.value: None,
        SSKey.LAST_ERROR.value: None,
        SSKey.DEBUG.value: False,
        SSKey.CONTENT_SHARING_CONSENT.value: False,
        SSKey.LLM_RESPONSE_CACHE.value: {},
        SSKey.JOBAD_CACHE_HIT.value: {},
        SSKey.SUMMARY_CACHE_HIT.value: False,
        SSKey.SUMMARY_LAST_MODE.value: None,
        SSKey.SUMMARY_LAST_MODELS.value: {},
        SSKey.SUMMARY_SELECTIONS.value: {},
        SSKey.JOB_AD_DRAFT_CUSTOM.value: None,
        SSKey.JOB_AD_LAST_USAGE.value: {},
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def reset_vacancy() -> None:
    """Reset only vacancy-related state, not preferences."""
    st.session_state[SSKey.SOURCE_TEXT.value] = ""
    st.session_state[SSKey.SOURCE_FILE_META.value] = {}
    st.session_state[SSKey.JOB_EXTRACT.value] = None
    st.session_state[SSKey.QUESTION_PLAN.value] = None
    st.session_state[SSKey.QUESTION_LIMITS.value] = {}
    st.session_state[SSKey.ANSWERS.value] = {}
    st.session_state[SSKey.BRIEF.value] = None
    st.session_state[SSKey.JOBAD_CACHE_HIT.value] = {}
    st.session_state[SSKey.SUMMARY_CACHE_HIT.value] = False
    st.session_state[SSKey.SUMMARY_LAST_MODE.value] = None
    st.session_state[SSKey.SUMMARY_LAST_MODELS.value] = {}
    st.session_state[SSKey.SUMMARY_SELECTIONS.value] = {}
    st.session_state[SSKey.JOB_AD_DRAFT_CUSTOM.value] = None
    st.session_state[SSKey.JOB_AD_LAST_USAGE.value] = {}
    st.session_state[SSKey.LAST_ERROR.value] = None
    st.session_state[SSKey.CURRENT_STEP.value] = STEPS[0].key


def get_answers() -> Dict[str, Any]:
    return st.session_state.get(SSKey.ANSWERS.value, {}) or {}


def set_answer(question_id: str, value: Any) -> None:
    answers = get_answers()
    answers[question_id] = value
    st.session_state[SSKey.ANSWERS.value] = answers


def set_error(msg: str) -> None:
    st.session_state[SSKey.LAST_ERROR.value] = msg


def set_safe_error_debug(
    *,
    step: str,
    error_type: str,
    error_code: str | None = None,
) -> None:
    """Store non-sensitive debug details for optional UI display."""

    st.session_state["cs.last_error_debug"] = None
    if not bool(st.session_state.get("OPENAI_DEBUG_ERRORS", False)):
        return

    details: list[str] = [f"step={step}", f"type={error_type}"]
    if error_code:
        details.insert(1, f"code={error_code}")
    st.session_state["cs.last_error_debug"] = " | ".join(details)


def handle_unexpected_exception(
    *,
    step: str,
    exc: Exception,
    error_type: str | None = None,
    error_code: str | None = None,
    user_message: str = "Es ist ein unerwarteter Fehler aufgetreten. Bitte erneut versuchen.",
) -> None:
    """Set a generic UI error plus safe non-sensitive debug metadata."""

    resolved_error_type = error_type or type(exc).__name__
    set_error(user_message)
    set_safe_error_debug(
        step=step,
        error_type=resolved_error_type,
        error_code=error_code,
    )


def clear_error() -> None:
    st.session_state[SSKey.LAST_ERROR.value] = None
    st.session_state["cs.last_error_debug"] = None
