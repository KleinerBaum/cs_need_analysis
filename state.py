# state.py
"""Session state management.

Streamlit re-runs the script on each interaction; st.session_state is the backbone
of a wizard workflow.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

import os
import streamlit as st

from constants import DEFAULT_LANGUAGE, SSKey, STEPS


def init_session_state() -> None:
    # Default model can be provided via Streamlit secrets or environment
    default_model = 'gpt-4o-mini'
    try:
        default_model = st.secrets.get('OPENAI_MODEL', default_model)  # type: ignore[attr-defined]
    except Exception:
        pass
    default_model = os.getenv('OPENAI_MODEL', default_model)
    defaults = {
        SSKey.CURRENT_STEP.value: STEPS[0].key,
        SSKey.LANGUAGE.value: DEFAULT_LANGUAGE,
        SSKey.MODEL.value: default_model,
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
