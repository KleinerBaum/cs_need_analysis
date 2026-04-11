# state.py
"""Session state management.

Streamlit re-runs the script on each interaction; st.session_state is the backbone
of a wizard workflow.
"""

from __future__ import annotations

import os
from typing import Any, Dict, cast

import streamlit as st

from constants import DEFAULT_LANGUAGE, SSKey, STEPS
from eures_mapping import load_national_code_lookup_from_file
from question_progress import AnswerMeta, AnswerMetaMap, value_hash
from schemas import EscoConceptRef, EscoMappingReport, EscoSuggestionItem
from settings_openai import load_openai_settings

DEFAULT_ESCO_API_BASE_URL = "https://ec.europa.eu/esco/api/"


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
    configured_language = st.session_state.get(SSKey.LANGUAGE.value, DEFAULT_LANGUAGE)
    if not isinstance(configured_language, str) or not configured_language.strip():
        configured_language = DEFAULT_LANGUAGE
    configured_esco_base_url = os.getenv("ESCO_API_BASE_URL", "").strip()
    if not configured_esco_base_url:
        configured_esco_base_url = DEFAULT_ESCO_API_BASE_URL
    configured_eures_nace_source = os.getenv("EURES_NACE_MAPPING_CSV", "").strip()
    eures_nace_lookup: dict[str, str] = {}
    if configured_eures_nace_source:
        try:
            eures_nace_lookup = load_national_code_lookup_from_file(
                configured_eures_nace_source
            )
        except Exception:
            eures_nace_lookup = {}

    defaults: Dict[str, Any] = {
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
        SSKey.UI_PREFERENCES.value: {
            "details_expanded_default": False,
            "step_compact": {},
        },
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
        SSKey.SUMMARY_DIRTY.value: False,
        SSKey.SUMMARY_INPUT_FINGERPRINT.value: "",
        SSKey.SUMMARY_LAST_BRIEF_FINGERPRINT.value: "",
        SSKey.SUMMARY_ACTIVE_ARTIFACT.value: "brief",
        SSKey.SUMMARY_SHOW_JOB_AD_CONFIG.value: False,
        SSKey.SUMMARY_LAST_MODE.value: None,
        SSKey.SUMMARY_LAST_MODELS.value: {},
        SSKey.SUMMARY_FACTS_SEARCH.value: "",
        SSKey.SUMMARY_FACTS_STATUS_FILTER.value: "Alle",
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
        SSKey.ESCO_CONFIG.value: {
            "base_url": configured_esco_base_url,
            "selected_version": "latest",
            "language": configured_language,
            "view_obsolete": False,
        },
        SSKey.ESCO_OCCUPATION_SELECTED.value: None,
        SSKey.ESCO_OCCUPATION_PAYLOAD.value: None,
        SSKey.ESCO_OCCUPATION_CANDIDATES.value: [],
        SSKey.ESCO_MATCH_REASON.value: None,
        SSKey.ESCO_MATCH_CONFIDENCE.value: None,
        SSKey.ESCO_MATCH_PROVENANCE.value: [],
        SSKey.ESCO_SKILLS_SELECTED_MUST.value: [],
        SSKey.ESCO_SKILLS_SELECTED_NICE.value: [],
        SSKey.ESCO_SKILLS_MAPPING_REPORT.value: None,
        SSKey.ESCO_OCCUPATION_TITLE_VARIANTS.value: {},
        SSKey.ESCO_MIGRATION_LOG.value: [],
        SSKey.ESCO_MIGRATION_PENDING.value: None,
        SSKey.EURES_NACE_TO_ESCO.value: eures_nace_lookup,
        SSKey.EURES_NACE_SOURCE.value: configured_eures_nace_source,
        SSKey.COMPANY_NACE_CODE.value: "",
        SSKey.ROLE_TASKS_JOBSPEC_SUGGESTED.value: [],
        SSKey.ROLE_TASKS_ESCO_SUGGESTED.value: [],
        SSKey.ROLE_TASKS_LLM_SUGGESTED.value: [],
        SSKey.ROLE_TASKS_SELECTED.value: [],
        SSKey.ROLE_TASKS_SUGGEST_COUNT.value: 5,
        SSKey.SKILLS_JOBSPEC_SUGGESTED.value: [],
        SSKey.SKILLS_LLM_SUGGESTED.value: [],
        SSKey.SKILLS_SELECTED.value: [],
        SSKey.SKILLS_SUGGEST_COUNT.value: 5,
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
    if SSKey.UI_PREFERENCES.value not in st.session_state:
        st.session_state[SSKey.UI_PREFERENCES.value] = {
            "details_expanded_default": False,
            "step_compact": {},
        }
    st.session_state[SSKey.OPEN_GROUPS.value] = {}
    st.session_state[SSKey.BRIEF.value] = None
    st.session_state[SSKey.JOBAD_CACHE_HIT.value] = {}
    st.session_state[SSKey.SUMMARY_CACHE_HIT.value] = False
    st.session_state[SSKey.SUMMARY_DIRTY.value] = False
    st.session_state[SSKey.SUMMARY_INPUT_FINGERPRINT.value] = ""
    st.session_state[SSKey.SUMMARY_LAST_BRIEF_FINGERPRINT.value] = ""
    st.session_state[SSKey.SUMMARY_ACTIVE_ARTIFACT.value] = "brief"
    st.session_state[SSKey.SUMMARY_SHOW_JOB_AD_CONFIG.value] = False
    st.session_state[SSKey.SUMMARY_LAST_MODE.value] = None
    st.session_state[SSKey.SUMMARY_LAST_MODELS.value] = {}
    st.session_state[SSKey.SUMMARY_FACTS_SEARCH.value] = ""
    st.session_state[SSKey.SUMMARY_FACTS_STATUS_FILTER.value] = "Alle"
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
    st.session_state[SSKey.ESCO_OCCUPATION_SELECTED.value] = None
    st.session_state[SSKey.ESCO_OCCUPATION_PAYLOAD.value] = None
    st.session_state[SSKey.ESCO_OCCUPATION_CANDIDATES.value] = []
    st.session_state[SSKey.ESCO_MATCH_REASON.value] = None
    st.session_state[SSKey.ESCO_MATCH_CONFIDENCE.value] = None
    st.session_state[SSKey.ESCO_MATCH_PROVENANCE.value] = []
    st.session_state[SSKey.ESCO_SKILLS_SELECTED_MUST.value] = []
    st.session_state[SSKey.ESCO_SKILLS_SELECTED_NICE.value] = []
    st.session_state[SSKey.ESCO_SKILLS_MAPPING_REPORT.value] = None
    st.session_state[SSKey.ESCO_OCCUPATION_TITLE_VARIANTS.value] = {}
    st.session_state[SSKey.ESCO_MIGRATION_LOG.value] = []
    st.session_state[SSKey.ESCO_MIGRATION_PENDING.value] = None
    st.session_state[SSKey.COMPANY_NACE_CODE.value] = ""
    st.session_state[SSKey.ROLE_TASKS_JOBSPEC_SUGGESTED.value] = []
    st.session_state[SSKey.ROLE_TASKS_ESCO_SUGGESTED.value] = []
    st.session_state[SSKey.ROLE_TASKS_LLM_SUGGESTED.value] = []
    st.session_state[SSKey.ROLE_TASKS_SELECTED.value] = []
    st.session_state[SSKey.ROLE_TASKS_SUGGEST_COUNT.value] = 5
    st.session_state[SSKey.SKILLS_JOBSPEC_SUGGESTED.value] = []
    st.session_state[SSKey.SKILLS_LLM_SUGGESTED.value] = []
    st.session_state[SSKey.SKILLS_SELECTED.value] = []
    st.session_state[SSKey.SKILLS_SUGGEST_COUNT.value] = 5
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


def get_esco_occupation_selected() -> Dict[str, Any] | None:
    """Return a validated ESCO occupation payload or None for legacy sessions."""

    raw = st.session_state.get(SSKey.ESCO_OCCUPATION_SELECTED.value)
    if raw is None:
        return None
    try:
        return EscoConceptRef.model_validate(raw).model_dump()
    except Exception:
        return None


def get_esco_occupation_payload() -> Dict[str, Any] | None:
    """Return selected ESCO occupation detail payload if available."""

    raw = st.session_state.get(SSKey.ESCO_OCCUPATION_PAYLOAD.value)
    return raw if isinstance(raw, dict) else None


def get_esco_occupation_candidates() -> list[Dict[str, Any]]:
    """Return validated ESCO candidate suggestions; tolerate legacy payloads."""

    raw = st.session_state.get(SSKey.ESCO_OCCUPATION_CANDIDATES.value, [])
    if not isinstance(raw, list):
        return []
    items: list[Dict[str, Any]] = []
    for item in raw:
        try:
            items.append(EscoSuggestionItem.model_validate(item).model_dump())
        except Exception:
            continue
    return items


def get_esco_skills_mapping_report() -> Dict[str, Any] | None:
    """Return validated ESCO mapping report or None for missing/legacy sessions."""

    raw = st.session_state.get(SSKey.ESCO_SKILLS_MAPPING_REPORT.value)
    if raw is None:
        return None
    try:
        return EscoMappingReport.model_validate(raw).model_dump()
    except Exception:
        return None
