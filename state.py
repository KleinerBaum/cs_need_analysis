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
        SSKey.ANSWERS.value: {},
        SSKey.BRIEF.value: None,
        SSKey.LAST_ERROR.value: None,
        SSKey.DEBUG.value: False,
        SSKey.CONTENT_SHARING_CONSENT.value: False,
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
    st.session_state[SSKey.ANSWERS.value] = {}
    st.session_state[SSKey.BRIEF.value] = None
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


def clear_error() -> None:
    st.session_state[SSKey.LAST_ERROR.value] = None
    st.session_state["cs.last_error_debug"] = None
