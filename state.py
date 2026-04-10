# state.py
"""Session state management.

Streamlit re-runs the script on each interaction; st.session_state is the backbone
of a wizard workflow.
"""

from __future__ import annotations

from typing import Any, Dict, cast

import streamlit as st

from constants import DEFAULT_LANGUAGE, SSKey, STEPS
from question_progress import AnswerMeta, AnswerMetaMap, value_hash
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
        SSKey.LAST_RENDERED_STEP.value: None,
        SSKey.NAV_SELECTED.value: STEPS[0].key,
        SSKey.NAV_SYNC_PENDING.value: False,
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
        SSKey.ANSWER_META.value: {},
        SSKey.UI_MODE.value: "standard",
        SSKey.OPEN_GROUPS.value: {},
        SSKey.BRIEF.value: None,
        SSKey.LAST_ERROR.value: None,
        SSKey.LAST_ERROR_DEBUG.value: None,
        SSKey.OPENAI_DEBUG_ERRORS.value: False,
        SSKey.DEBUG.value: False,
        SSKey.CONTENT_SHARING_CONSENT.value: False,
        SSKey.LLM_RESPONSE_CACHE.value: {},
        SSKey.JOBAD_CACHE_HIT.value: {},
        SSKey.SUMMARY_CACHE_HIT.value: False,
        SSKey.SUMMARY_LAST_MODE.value: None,
        SSKey.SUMMARY_LAST_MODELS.value: {},
        SSKey.SUMMARY_SELECTIONS.value: {},
        SSKey.SUMMARY_STYLEGUIDE_BLOCKS.value: [],
        SSKey.SUMMARY_CHANGE_REQUEST_BLOCKS.value: [],
        SSKey.SUMMARY_STYLEGUIDE_TEXT.value: "",
        SSKey.SUMMARY_CHANGE_REQUEST_TEXT.value: "",
        SSKey.SUMMARY_LOGO.value: None,
        SSKey.JOB_AD_DRAFT_CUSTOM.value: None,
        SSKey.JOB_AD_LAST_USAGE.value: {},
        SSKey.INTERVIEW_PREP_HR.value: None,
        SSKey.INTERVIEW_PREP_HR_LAST_USAGE.value: {},
        SSKey.INTERVIEW_PREP_HR_CACHE_HIT.value: False,
        SSKey.INTERVIEW_PREP_HR_LAST_MODE.value: None,
        SSKey.INTERVIEW_PREP_HR_LAST_MODELS.value: {},
        SSKey.INTERVIEW_PREP_FACH.value: None,
        SSKey.INTERVIEW_PREP_FACH_LAST_USAGE.value: {},
        SSKey.INTERVIEW_PREP_FACH_CACHE_HIT.value: False,
        SSKey.INTERVIEW_PREP_FACH_LAST_MODE.value: None,
        SSKey.INTERVIEW_PREP_FACH_LAST_MODELS.value: {},
        SSKey.BOOLEAN_SEARCH_STRING.value: None,
        SSKey.BOOLEAN_SEARCH_LAST_USAGE.value: {},
        SSKey.BOOLEAN_SEARCH_CACHE_HIT.value: False,
        SSKey.BOOLEAN_SEARCH_LAST_MODE.value: None,
        SSKey.BOOLEAN_SEARCH_LAST_MODELS.value: {},
        SSKey.EMPLOYMENT_CONTRACT_DRAFT.value: None,
        SSKey.EMPLOYMENT_CONTRACT_LAST_USAGE.value: {},
        SSKey.EMPLOYMENT_CONTRACT_CACHE_HIT.value: False,
        SSKey.EMPLOYMENT_CONTRACT_LAST_MODE.value: None,
        SSKey.EMPLOYMENT_CONTRACT_LAST_MODELS.value: {},
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
    st.session_state[SSKey.ANSWER_META.value] = {}
    st.session_state[SSKey.UI_MODE.value] = "standard"
    st.session_state[SSKey.OPEN_GROUPS.value] = {}
    st.session_state[SSKey.BRIEF.value] = None
    st.session_state[SSKey.JOBAD_CACHE_HIT.value] = {}
    st.session_state[SSKey.SUMMARY_CACHE_HIT.value] = False
    st.session_state[SSKey.SUMMARY_LAST_MODE.value] = None
    st.session_state[SSKey.SUMMARY_LAST_MODELS.value] = {}
    st.session_state[SSKey.SUMMARY_SELECTIONS.value] = {}
    st.session_state[SSKey.SUMMARY_STYLEGUIDE_BLOCKS.value] = []
    st.session_state[SSKey.SUMMARY_CHANGE_REQUEST_BLOCKS.value] = []
    st.session_state[SSKey.SUMMARY_STYLEGUIDE_TEXT.value] = ""
    st.session_state[SSKey.SUMMARY_CHANGE_REQUEST_TEXT.value] = ""
    st.session_state[SSKey.SUMMARY_LOGO.value] = None
    st.session_state[SSKey.JOB_AD_DRAFT_CUSTOM.value] = None
    st.session_state[SSKey.JOB_AD_LAST_USAGE.value] = {}
    st.session_state[SSKey.INTERVIEW_PREP_HR.value] = None
    st.session_state[SSKey.INTERVIEW_PREP_HR_LAST_USAGE.value] = {}
    st.session_state[SSKey.INTERVIEW_PREP_HR_CACHE_HIT.value] = False
    st.session_state[SSKey.INTERVIEW_PREP_HR_LAST_MODE.value] = None
    st.session_state[SSKey.INTERVIEW_PREP_HR_LAST_MODELS.value] = {}
    st.session_state[SSKey.INTERVIEW_PREP_FACH.value] = None
    st.session_state[SSKey.INTERVIEW_PREP_FACH_LAST_USAGE.value] = {}
    st.session_state[SSKey.INTERVIEW_PREP_FACH_CACHE_HIT.value] = False
    st.session_state[SSKey.INTERVIEW_PREP_FACH_LAST_MODE.value] = None
    st.session_state[SSKey.INTERVIEW_PREP_FACH_LAST_MODELS.value] = {}
    st.session_state[SSKey.BOOLEAN_SEARCH_STRING.value] = None
    st.session_state[SSKey.BOOLEAN_SEARCH_LAST_USAGE.value] = {}
    st.session_state[SSKey.BOOLEAN_SEARCH_CACHE_HIT.value] = False
    st.session_state[SSKey.BOOLEAN_SEARCH_LAST_MODE.value] = None
    st.session_state[SSKey.BOOLEAN_SEARCH_LAST_MODELS.value] = {}
    st.session_state[SSKey.EMPLOYMENT_CONTRACT_DRAFT.value] = None
    st.session_state[SSKey.EMPLOYMENT_CONTRACT_LAST_USAGE.value] = {}
    st.session_state[SSKey.EMPLOYMENT_CONTRACT_CACHE_HIT.value] = False
    st.session_state[SSKey.EMPLOYMENT_CONTRACT_LAST_MODE.value] = None
    st.session_state[SSKey.EMPLOYMENT_CONTRACT_LAST_MODELS.value] = {}
    st.session_state[SSKey.LAST_ERROR.value] = None
    st.session_state[SSKey.CURRENT_STEP.value] = STEPS[0].key
    st.session_state[SSKey.LAST_RENDERED_STEP.value] = STEPS[0].key
    st.session_state[SSKey.NAV_SELECTED.value] = STEPS[0].key
    st.session_state[SSKey.NAV_SYNC_PENDING.value] = False


def get_answers() -> Dict[str, Any]:
    return st.session_state.get(SSKey.ANSWERS.value, {}) or {}


def set_answer(question_id: str, value: Any) -> None:
    answers = get_answers()
    answers[question_id] = value
    st.session_state[SSKey.ANSWERS.value] = answers


def get_answer_meta() -> AnswerMetaMap:
    raw = st.session_state.get(SSKey.ANSWER_META.value, {})
    return raw if isinstance(raw, dict) else {}


def mark_answer_touched(
    question_id: str, previous_value: Any, current_value: Any
) -> None:
    """Persist touch-state when the value differs from the previous value."""

    meta = dict(get_answer_meta())
    current = cast(AnswerMeta, dict(meta.get(question_id, {})))
    previous_hash = value_hash(previous_value)
    current_hash = value_hash(current_value)
    if previous_hash != current_hash:
        current["touched"] = True
    current["last_value_hash"] = current_hash
    current.setdefault("confirmed", False)
    meta[question_id] = current
    st.session_state[SSKey.ANSWER_META.value] = meta


def set_error(msg: str) -> None:
    st.session_state[SSKey.LAST_ERROR.value] = msg


def set_safe_error_debug(
    *,
    step: str,
    error_type: str,
    error_code: str | None = None,
) -> None:
    """Store non-sensitive debug details for optional UI display."""

    st.session_state[SSKey.LAST_ERROR_DEBUG.value] = None
    if not bool(st.session_state.get(SSKey.OPENAI_DEBUG_ERRORS.value, False)):
        return

    details: list[str] = [
        f"step={step}",
        f"type={error_type}",
        f"category={error_type}",
    ]
    if error_code:
        details.insert(1, f"code={error_code}")
    st.session_state[SSKey.LAST_ERROR_DEBUG.value] = " | ".join(details)


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
    st.session_state[SSKey.LAST_ERROR_DEBUG.value] = None
