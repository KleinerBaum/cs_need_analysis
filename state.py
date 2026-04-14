# state.py
"""Session state management.

Streamlit re-runs the script on each interaction; st.session_state is the backbone
of a wizard workflow.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Dict, cast

import streamlit as st

from constants import (
    DEFAULT_ESCO_SELECTED_VERSION,
    DEFAULT_LANGUAGE,
    SSKey,
    UI_PREFERENCE_ANSWER_MODE,
    UI_PREFERENCE_CONFIDENCE_THRESHOLD,
    UI_PREFERENCE_DETAILS_EXPANDED_DEFAULT,
    UI_PREFERENCE_ESCO_MATCHING_STRICTNESS,
    UI_PREFERENCE_INFORMATION_DEPTH,
    UI_PREFERENCE_PII_REDUCTION,
    UI_PREFERENCE_REGIONAL_FOCUS,
    UI_PREFERENCE_SHOW_SOURCES_DEFAULT,
    UI_PREFERENCE_STEP_COMPACT,
    STALE_REDESIGN_SESSION_KEY_PREFIXES,
    STEPS,
    SUMMARY_SESSION_KEY_LEGACY_ALIASES,
)
from eures_mapping import load_national_code_lookup_from_file
from question_progress import AnswerMeta, AnswerMetaMap, value_hash
from schemas import EscoConceptRef, EscoMappingReport, EscoSuggestionItem
from settings_openai import load_openai_settings

DEFAULT_ESCO_API_BASE_URL = "https://ec.europa.eu/esco/api/"


def _apply_summary_legacy_key_aliases() -> None:
    """Populate canonical summary keys from compatible legacy aliases when possible."""

    for canonical_key, legacy_keys in SUMMARY_SESSION_KEY_LEGACY_ALIASES.items():
        canonical_name = canonical_key.value
        if canonical_name in st.session_state:
            continue
        for legacy_key in legacy_keys:
            if legacy_key not in st.session_state:
                continue
            st.session_state[canonical_name] = st.session_state[legacy_key]
            break


def _clear_stale_redesign_state() -> None:
    """Drop stale redesign-only session keys while preserving canonical state."""

    canonical_keys = {key.value for key in SSKey}
    for session_key in list(st.session_state.keys()):
        if session_key in canonical_keys:
            continue
        if any(
            session_key.startswith(prefix)
            for prefix in STALE_REDESIGN_SESSION_KEY_PREFIXES
        ):
            st.session_state.pop(session_key, None)
            continue
        for legacy_keys in SUMMARY_SESSION_KEY_LEGACY_ALIASES.values():
            if session_key in legacy_keys:
                st.session_state.pop(session_key, None)
                break


@dataclass(frozen=True)
class EscoCoverageSnapshot:
    selected_occupation_uri: str
    confirmed_essential_skills: list[Dict[str, str]]
    confirmed_optional_skills: list[Dict[str, str]]
    unmapped_requirement_terms: list[str]
    essential_total: int
    essential_covered: int
    optional_total: int
    optional_covered: int

    @property
    def essential_coverage_percent(self) -> int:
        if self.essential_total <= 0:
            return 0
        return round((self.essential_covered / self.essential_total) * 100)

    @property
    def optional_coverage_percent(self) -> int:
        if self.optional_total <= 0:
            return 0
        return round((self.optional_covered / self.optional_total) * 100)


def get_model_override() -> str | None:
    """Return a cleaned model override from the UI, if provided."""

    model_override = st.session_state.get(SSKey.MODEL.value)
    if isinstance(model_override, str):
        cleaned_override = model_override.strip()
        if cleaned_override:
            return cleaned_override
    return None


def _default_ui_preferences() -> dict[str, Any]:
    return {
        UI_PREFERENCE_ANSWER_MODE: "balanced",
        UI_PREFERENCE_INFORMATION_DEPTH: "standard",
        UI_PREFERENCE_ESCO_MATCHING_STRICTNESS: "ausgewogen",
        UI_PREFERENCE_REGIONAL_FOCUS: "DACH",
        UI_PREFERENCE_SHOW_SOURCES_DEFAULT: True,
        UI_PREFERENCE_CONFIDENCE_THRESHOLD: 0.6,
        UI_PREFERENCE_PII_REDUCTION: True,
        UI_PREFERENCE_DETAILS_EXPANDED_DEFAULT: False,
        UI_PREFERENCE_STEP_COMPACT: {},
    }


def normalize_ui_preferences(raw_preferences: Any) -> dict[str, Any]:
    defaults = _default_ui_preferences()
    normalized = dict(defaults)
    if isinstance(raw_preferences, dict):
        normalized.update(raw_preferences)
    if not isinstance(normalized.get(UI_PREFERENCE_STEP_COMPACT), dict):
        normalized[UI_PREFERENCE_STEP_COMPACT] = {}
    confidence = normalized.get(UI_PREFERENCE_CONFIDENCE_THRESHOLD)
    try:
        normalized[UI_PREFERENCE_CONFIDENCE_THRESHOLD] = min(
            0.95, max(0.05, float(confidence))
        )
    except (TypeError, ValueError):
        normalized[UI_PREFERENCE_CONFIDENCE_THRESHOLD] = defaults[
            UI_PREFERENCE_CONFIDENCE_THRESHOLD
        ]
    for key in (
        UI_PREFERENCE_SHOW_SOURCES_DEFAULT,
        UI_PREFERENCE_PII_REDUCTION,
        UI_PREFERENCE_DETAILS_EXPANDED_DEFAULT,
    ):
        normalized[key] = bool(normalized.get(key, defaults[key]))
    return normalized


def get_active_model() -> str:
    """Return UI override model or OpenAI settings fallback model."""

    return get_model_override() or load_openai_settings().openai_model


def init_session_state() -> None:
    _apply_summary_legacy_key_aliases()
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
        SSKey.UI_PREFERENCES.value: _default_ui_preferences(),
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
            "selected_version": os.getenv(
                "ESCO_SELECTED_VERSION", DEFAULT_ESCO_SELECTED_VERSION
            ).strip()
            or DEFAULT_ESCO_SELECTED_VERSION,
            "language": configured_language,
            "view_obsolete": False,
            "api_mode": os.getenv("ESCO_API_MODE", "hosted").strip().lower()
            or "hosted",
        },
        SSKey.ESCO_OCCUPATION_SELECTED.value: None,
        SSKey.ESCO_SELECTED_OCCUPATION_URI.value: "",
        SSKey.ESCO_OCCUPATION_PAYLOAD.value: None,
        SSKey.ESCO_OCCUPATION_CANDIDATES.value: [],
        SSKey.ESCO_MATCH_REASON.value: None,
        SSKey.ESCO_MATCH_CONFIDENCE.value: None,
        SSKey.ESCO_MATCH_PROVENANCE.value: [],
        SSKey.ESCO_SKILLS_SELECTED_MUST.value: [],
        SSKey.ESCO_SKILLS_SELECTED_NICE.value: [],
        SSKey.ESCO_CONFIRMED_ESSENTIAL_SKILLS.value: [],
        SSKey.ESCO_CONFIRMED_OPTIONAL_SKILLS.value: [],
        SSKey.ESCO_UNMAPPED_REQUIREMENT_TERMS.value: [],
        SSKey.ESCO_UNMAPPED_ROLE_TERMS.value: [],
        SSKey.ESCO_UNMAPPED_TERM_ACTIONS.value: {},
        SSKey.ESCO_SKILLS_MAPPING_REPORT.value: None,
        SSKey.ESCO_OCCUPATION_TITLE_VARIANTS.value: {},
        SSKey.ESCO_MIGRATION_LOG.value: [],
        SSKey.ESCO_MIGRATION_PENDING.value: None,
        SSKey.EURES_NACE_TO_ESCO.value: eures_nace_lookup,
        SSKey.EURES_NACE_SOURCE.value: configured_eures_nace_source,
        SSKey.COMPANY_NACE_CODE.value: "",
        SSKey.COMPANY_WEBSITE_RESEARCH.value: {},
        SSKey.COMPANY_WEBSITE_LAST_ERROR.value: None,
        SSKey.ROLE_TASKS_JOBSPEC_SUGGESTED.value: [],
        SSKey.ROLE_TASKS_ESCO_SUGGESTED.value: [],
        SSKey.ROLE_TASKS_LLM_SUGGESTED.value: [],
        SSKey.ROLE_TASKS_SELECTED.value: [],
        SSKey.ROLE_TASKS_SUGGEST_COUNT.value: 5,
        SSKey.SKILLS_JOBSPEC_SUGGESTED.value: [],
        SSKey.SKILLS_LLM_SUGGESTED.value: [],
        SSKey.SKILLS_SELECTED.value: [],
        SSKey.SKILLS_SUGGEST_COUNT.value: 5,
        SSKey.SALARY_SCENARIO_SKILLS_ADD.value: [],
        SSKey.SALARY_SCENARIO_SKILLS_REMOVE.value: [],
        SSKey.SALARY_SCENARIO_LOCATION_OVERRIDE.value: "",
        SSKey.SALARY_SCENARIO_LOCATION_CITY_OVERRIDE.value: "",
        SSKey.SALARY_SCENARIO_LOCATION_COUNTRY_OVERRIDE.value: "",
        SSKey.SALARY_SCENARIO_RADIUS_KM.value: 50,
        SSKey.SALARY_SCENARIO_REMOTE_SHARE_PERCENT.value: 0,
        SSKey.SALARY_SCENARIO_SENIORITY_OVERRIDE.value: "",
        SSKey.SALARY_SCENARIO_LAB_ROWS.value: [],
        SSKey.SALARY_SCENARIO_SELECTED_ROW_ID.value: "",
        SSKey.SALARY_SCENARIO_PENDING_SKILLS_ADD.value: None,
        SSKey.SALARY_SCENARIO_PENDING_SKILLS_REMOVE.value: None,
        SSKey.SALARY_SCENARIO_PENDING_LOCATION_CITY_OVERRIDE.value: None,
        SSKey.SALARY_SCENARIO_PENDING_RADIUS_KM.value: None,
        SSKey.SALARY_SCENARIO_PENDING_REMOTE_SHARE_PERCENT.value: None,
        SSKey.SALARY_SCENARIO_PENDING_SENIORITY_OVERRIDE.value: None,
        SSKey.SALARY_SCENARIO_APPLY_PENDING_UPDATE.value: False,
        SSKey.SALARY_SCENARIO_PENDING_SELECTED_ROW_ID.value: None,
        SSKey.SALARY_FORECAST_SELECTED_SCENARIO.value: "base",
        SSKey.SALARY_FORECAST_LAST_RESULT.value: {},
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v
    st.session_state[SSKey.UI_PREFERENCES.value] = normalize_ui_preferences(
        st.session_state.get(SSKey.UI_PREFERENCES.value)
    )


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
        st.session_state[SSKey.UI_PREFERENCES.value] = _default_ui_preferences()
    else:
        st.session_state[SSKey.UI_PREFERENCES.value] = normalize_ui_preferences(
            st.session_state.get(SSKey.UI_PREFERENCES.value)
        )
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
    st.session_state[SSKey.ESCO_SELECTED_OCCUPATION_URI.value] = ""
    st.session_state[SSKey.ESCO_OCCUPATION_PAYLOAD.value] = None
    st.session_state[SSKey.ESCO_OCCUPATION_CANDIDATES.value] = []
    st.session_state[SSKey.ESCO_MATCH_REASON.value] = None
    st.session_state[SSKey.ESCO_MATCH_CONFIDENCE.value] = None
    st.session_state[SSKey.ESCO_MATCH_PROVENANCE.value] = []
    st.session_state[SSKey.ESCO_SKILLS_SELECTED_MUST.value] = []
    st.session_state[SSKey.ESCO_SKILLS_SELECTED_NICE.value] = []
    st.session_state[SSKey.ESCO_CONFIRMED_ESSENTIAL_SKILLS.value] = []
    st.session_state[SSKey.ESCO_CONFIRMED_OPTIONAL_SKILLS.value] = []
    st.session_state[SSKey.ESCO_UNMAPPED_REQUIREMENT_TERMS.value] = []
    st.session_state[SSKey.ESCO_UNMAPPED_ROLE_TERMS.value] = []
    st.session_state[SSKey.ESCO_UNMAPPED_TERM_ACTIONS.value] = {}
    st.session_state[SSKey.ESCO_SKILLS_MAPPING_REPORT.value] = None
    st.session_state[SSKey.ESCO_OCCUPATION_TITLE_VARIANTS.value] = {}
    st.session_state[SSKey.ESCO_MIGRATION_LOG.value] = []
    st.session_state[SSKey.ESCO_MIGRATION_PENDING.value] = None
    st.session_state[SSKey.COMPANY_NACE_CODE.value] = ""
    st.session_state[SSKey.COMPANY_WEBSITE_RESEARCH.value] = {}
    st.session_state[SSKey.COMPANY_WEBSITE_LAST_ERROR.value] = None
    st.session_state[SSKey.ROLE_TASKS_JOBSPEC_SUGGESTED.value] = []
    st.session_state[SSKey.ROLE_TASKS_ESCO_SUGGESTED.value] = []
    st.session_state[SSKey.ROLE_TASKS_LLM_SUGGESTED.value] = []
    st.session_state[SSKey.ROLE_TASKS_SELECTED.value] = []
    st.session_state[SSKey.ROLE_TASKS_SUGGEST_COUNT.value] = 5
    st.session_state[SSKey.SKILLS_JOBSPEC_SUGGESTED.value] = []
    st.session_state[SSKey.SKILLS_LLM_SUGGESTED.value] = []
    st.session_state[SSKey.SKILLS_SELECTED.value] = []
    st.session_state[SSKey.SKILLS_SUGGEST_COUNT.value] = 5
    st.session_state[SSKey.SALARY_SCENARIO_SKILLS_ADD.value] = []
    st.session_state[SSKey.SALARY_SCENARIO_SKILLS_REMOVE.value] = []
    st.session_state[SSKey.SALARY_SCENARIO_LOCATION_OVERRIDE.value] = ""
    st.session_state[SSKey.SALARY_SCENARIO_LOCATION_CITY_OVERRIDE.value] = ""
    st.session_state[SSKey.SALARY_SCENARIO_LOCATION_COUNTRY_OVERRIDE.value] = ""
    st.session_state[SSKey.SALARY_SCENARIO_RADIUS_KM.value] = 50
    st.session_state[SSKey.SALARY_SCENARIO_REMOTE_SHARE_PERCENT.value] = 0
    st.session_state[SSKey.SALARY_SCENARIO_SENIORITY_OVERRIDE.value] = ""
    st.session_state[SSKey.SALARY_SCENARIO_LAB_ROWS.value] = []
    st.session_state[SSKey.SALARY_SCENARIO_SELECTED_ROW_ID.value] = ""
    st.session_state[SSKey.SALARY_SCENARIO_PENDING_SKILLS_ADD.value] = None
    st.session_state[SSKey.SALARY_SCENARIO_PENDING_SKILLS_REMOVE.value] = None
    st.session_state[SSKey.SALARY_SCENARIO_PENDING_LOCATION_CITY_OVERRIDE.value] = None
    st.session_state[SSKey.SALARY_SCENARIO_PENDING_RADIUS_KM.value] = None
    st.session_state[SSKey.SALARY_SCENARIO_PENDING_REMOTE_SHARE_PERCENT.value] = None
    st.session_state[SSKey.SALARY_SCENARIO_PENDING_SENIORITY_OVERRIDE.value] = None
    st.session_state[SSKey.SALARY_SCENARIO_APPLY_PENDING_UPDATE.value] = False
    st.session_state[SSKey.SALARY_SCENARIO_PENDING_SELECTED_ROW_ID.value] = None
    st.session_state[SSKey.SALARY_FORECAST_SELECTED_SCENARIO.value] = "base"
    _clear_stale_redesign_state()
    st.session_state[SSKey.SALARY_FORECAST_LAST_RESULT.value] = {}
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
        validated = EscoConceptRef.model_validate(raw).model_dump()
        st.session_state[SSKey.ESCO_SELECTED_OCCUPATION_URI.value] = str(
            validated.get("uri") or ""
        ).strip()
        return validated
    except Exception:
        return None


def has_confirmed_esco_anchor() -> bool:
    """Return True when an ESCO occupation anchor URI is confirmed in session state."""

    selected = get_esco_occupation_selected() or {}
    selected_uri = str(
        st.session_state.get(SSKey.ESCO_SELECTED_OCCUPATION_URI.value)
        or selected.get("uri")
        or ""
    ).strip()
    st.session_state[SSKey.ESCO_SELECTED_OCCUPATION_URI.value] = selected_uri
    return bool(selected_uri)


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


def _normalize_requirement_term(value: Any) -> str:
    return " ".join(str(value or "").strip().casefold().split())


def _dedupe_requirement_terms(values: list[str]) -> list[str]:
    deduped: list[str] = []
    seen: set[str] = set()
    for value in values:
        cleaned = str(value or "").strip()
        normalized = _normalize_requirement_term(cleaned)
        if not normalized or normalized in seen:
            continue
        deduped.append(cleaned)
        seen.add(normalized)
    return deduped


def _validated_esco_skill_bucket(raw: Any) -> list[Dict[str, str]]:
    if not isinstance(raw, list):
        return []
    validated: list[Dict[str, str]] = []
    seen_uris: set[str] = set()
    for item in raw:
        if not isinstance(item, dict):
            continue
        uri = str(item.get("uri") or "").strip()
        title = str(item.get("title") or "").strip()
        if not uri and not title:
            continue
        dedupe_key = uri or _normalize_requirement_term(title)
        if not dedupe_key or dedupe_key in seen_uris:
            continue
        validated.append(
            {
                "uri": uri,
                "title": title,
                "type": str(item.get("type") or "skill").strip() or "skill",
            }
        )
        seen_uris.add(dedupe_key)
    return validated


def sync_esco_shared_state() -> EscoCoverageSnapshot:
    selected = get_esco_occupation_selected() or {}
    selected_occupation_uri = str(
        st.session_state.get(SSKey.ESCO_SELECTED_OCCUPATION_URI.value)
        or selected.get("uri")
        or ""
    ).strip()
    st.session_state[SSKey.ESCO_SELECTED_OCCUPATION_URI.value] = selected_occupation_uri

    essential_skills = _validated_esco_skill_bucket(
        st.session_state.get(SSKey.ESCO_SKILLS_SELECTED_MUST.value, [])
    )
    optional_skills = _validated_esco_skill_bucket(
        st.session_state.get(SSKey.ESCO_SKILLS_SELECTED_NICE.value, [])
    )
    st.session_state[SSKey.ESCO_CONFIRMED_ESSENTIAL_SKILLS.value] = essential_skills
    st.session_state[SSKey.ESCO_CONFIRMED_OPTIONAL_SKILLS.value] = optional_skills

    unmapped_raw = st.session_state.get(SSKey.ESCO_UNMAPPED_REQUIREMENT_TERMS.value, [])
    unmapped_terms = (
        _dedupe_requirement_terms([str(item) for item in unmapped_raw])
        if isinstance(unmapped_raw, list)
        else []
    )
    st.session_state[SSKey.ESCO_UNMAPPED_REQUIREMENT_TERMS.value] = unmapped_terms

    job_extract = st.session_state.get(SSKey.JOB_EXTRACT.value, {})
    essential_terms = []
    optional_terms = []
    if isinstance(job_extract, dict):
        essential_terms = _dedupe_requirement_terms(
            [str(item) for item in (job_extract.get("must_have_skills") or [])]
        )
        optional_terms = _dedupe_requirement_terms(
            [str(item) for item in (job_extract.get("nice_to_have_skills") or [])]
        )

    essential_titles = {
        _normalize_requirement_term(item.get("title") or "")
        for item in essential_skills
    }
    optional_titles = {
        _normalize_requirement_term(item.get("title") or "") for item in optional_skills
    }

    essential_covered = sum(
        1
        for term in essential_terms
        if _normalize_requirement_term(term) in essential_titles
    )
    optional_covered = sum(
        1
        for term in optional_terms
        if _normalize_requirement_term(term) in optional_titles
    )

    return EscoCoverageSnapshot(
        selected_occupation_uri=selected_occupation_uri,
        confirmed_essential_skills=essential_skills,
        confirmed_optional_skills=optional_skills,
        unmapped_requirement_terms=unmapped_terms,
        essential_total=len(essential_terms),
        essential_covered=essential_covered,
        optional_total=len(optional_terms),
        optional_covered=optional_covered,
    )
