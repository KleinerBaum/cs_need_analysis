# constants.py

"""Canonical constants & keys.

Keep this file as the single source of truth for:
- session_state keys
- wizard step identifiers
- question/answer types
- schema versions
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Final, List


APP_TITLE: Final[str] = "Cognitive Staffing – Vacancy Intake Wizard"
DEFAULT_LANGUAGE: Final[str] = "de"


# ---- Session State Keys ----
class SSKey(str, Enum):
    CURRENT_STEP = "cs.current_step"
    LAST_RENDERED_STEP = "cs.last_rendered_step"
    NAV_SELECTED = "cs.nav_selected"
    NAV_SYNC_PENDING = "cs.nav_sync_pending"
    LANGUAGE = "cs.language"
    MODEL = "cs.model"
    STORE_API_OUTPUT = "cs.store_api_output"

    SOURCE_TEXT = "cs.source_text"
    SOURCE_FILE_META = "cs.source_file_meta"
    SOURCE_REDACT_PII = "cs.source_redact_pii"

    JOB_EXTRACT = "cs.job_extract"
    QUESTION_PLAN = "cs.question_plan"
    QUESTION_LIMITS = "cs.question_limits"
    ANSWERS = "cs.answers"
    ANSWER_META = "cs.answer_meta"
    UI_MODE = "cs.ui_mode"
    UI_PREFERENCES = "cs.ui_preferences"
    OPEN_GROUPS = "cs.open_groups"

    BRIEF = "cs.brief"
    LAST_ERROR = "cs.last_error"
    LAST_ERROR_DEBUG = "cs.last_error_debug"
    OPENAI_DEBUG_ERRORS = "OPENAI_DEBUG_ERRORS"
    DEBUG = "cs.debug"
    CONTENT_SHARING_CONSENT = "cs.content_sharing_consent"
    LLM_RESPONSE_CACHE = "cs.llm_response_cache"
    JOBAD_CACHE_HIT = "cs.jobad_cache_hit"
    SUMMARY_CACHE_HIT = "cs.summary_cache_hit"
    SUMMARY_DIRTY = "cs.summary_dirty"
    SUMMARY_INPUT_FINGERPRINT = "cs.summary_input_fingerprint"
    SUMMARY_LAST_BRIEF_FINGERPRINT = "cs.summary_last_brief_fingerprint"
    SUMMARY_ACTIVE_ARTIFACT = "cs.summary_active_artifact"
    SUMMARY_SHOW_JOB_AD_CONFIG = "cs.summary_show_job_ad_config"
    SUMMARY_LAST_MODE = "cs.summary_last_mode"
    SUMMARY_LAST_MODELS = "cs.summary_last_models"
    SUMMARY_FACTS_SEARCH = "cs.summary_facts_search"
    SUMMARY_FACTS_STATUS_FILTER = "cs.summary_facts_status_filter"
    OPENAI_LAST_STRUCTURED_OUTPUT_PATH = "cs.openai_last_structured_output_path"
    SUMMARY_SELECTIONS = "cs.summary_selections"
    SUMMARY_STYLEGUIDE_BLOCKS = "cs.summary_styleguide_blocks"
    SUMMARY_CHANGE_REQUEST_BLOCKS = "cs.summary_change_request_blocks"
    SUMMARY_STYLEGUIDE_TEXT = "cs.summary.styleguide"
    SUMMARY_CHANGE_REQUEST_TEXT = "cs.summary.change_request"
    JOB_AD_DRAFT_CUSTOM = "cs.job_ad_draft_custom"
    JOB_AD_LAST_USAGE = "cs.job_ad_last_usage"
    SUMMARY_LOGO = "cs.summary_logo"
    SUMMARY_WEIGHT_WIDGET_PREFIX = "cs.summary.weight"
    SUMMARY_SALARY_FORECAST_WIDGET = "cs.summary.salary_forecast"
    SALARY_SCENARIO_SKILLS_ADD = "cs.salary.scenario.skills_add"
    SALARY_SCENARIO_SKILLS_REMOVE = "cs.salary.scenario.skills_remove"
    SALARY_SCENARIO_LOCATION_OVERRIDE = "cs.salary.scenario.location_override"
    SALARY_SCENARIO_LOCATION_CITY_OVERRIDE = "cs.salary.scenario.location_city_override"
    SALARY_SCENARIO_LOCATION_COUNTRY_OVERRIDE = (
        "cs.salary.scenario.location_country_override"
    )
    SALARY_SCENARIO_RADIUS_KM = "cs.salary.scenario.radius_km"
    SALARY_SCENARIO_REMOTE_SHARE_PERCENT = "cs.salary.scenario.remote_share_percent"
    SALARY_SCENARIO_SENIORITY_OVERRIDE = "cs.salary.scenario.seniority_override"
    SALARY_SCENARIO_LAB_ROWS = "cs.salary.scenario.scenario_lab_rows"
    SALARY_SCENARIO_SELECTED_ROW_ID = "cs.salary.scenario.selected_row_id"
    SALARY_FORECAST_LAST_RESULT = "cs.salary.forecast.last_result"
    SALARY_FORECAST_SELECTED_SCENARIO = "cs.salary.forecast.selected_scenario"
    SUMMARY_SELECTION_PICK_WIDGET_PREFIX = "cs.summary.pick"
    SUMMARY_LOGO_UPLOAD_WIDGET = "cs.summary.logo_upload"
    SUMMARY_ACTION_WIDGET_PREFIX = "cs.summary.action"
    SUMMARY_STYLEGUIDE_BLOCK_WIDGET_PREFIX = "cs.summary.styleguide.block"
    SUMMARY_CHANGE_REQUEST_BLOCK_WIDGET_PREFIX = "cs.summary.change_request.block"
    INTERVIEW_PREP_HR = "cs.summary.interview_prep_hr"
    INTERVIEW_PREP_HR_LAST_USAGE = "cs.summary.interview_prep_hr_last_usage"
    INTERVIEW_PREP_HR_CACHE_HIT = "cs.summary.interview_prep_hr_cache_hit"
    INTERVIEW_PREP_HR_LAST_MODE = "cs.summary.interview_prep_hr_last_mode"
    INTERVIEW_PREP_HR_LAST_MODELS = "cs.summary.interview_prep_hr_last_models"
    INTERVIEW_PREP_FACH = "cs.summary.interview_prep_fach"
    INTERVIEW_PREP_FACH_LAST_USAGE = "cs.summary.interview_prep_fach_last_usage"
    INTERVIEW_PREP_FACH_CACHE_HIT = "cs.summary.interview_prep_fach_cache_hit"
    INTERVIEW_PREP_FACH_LAST_MODE = "cs.summary.interview_prep_fach_last_mode"
    INTERVIEW_PREP_FACH_LAST_MODELS = "cs.summary.interview_prep_fach_last_models"
    BOOLEAN_SEARCH_STRING = "cs.summary.boolean_search_string"
    BOOLEAN_SEARCH_LAST_USAGE = "cs.summary.boolean_search_last_usage"
    BOOLEAN_SEARCH_CACHE_HIT = "cs.summary.boolean_search_cache_hit"
    BOOLEAN_SEARCH_LAST_MODE = "cs.summary.boolean_search_last_mode"
    BOOLEAN_SEARCH_LAST_MODELS = "cs.summary.boolean_search_last_models"
    EMPLOYMENT_CONTRACT_DRAFT = "cs.summary.employment_contract"
    EMPLOYMENT_CONTRACT_LAST_USAGE = "cs.summary.employment_contract_last_usage"
    EMPLOYMENT_CONTRACT_CACHE_HIT = "cs.summary.employment_contract_cache_hit"
    EMPLOYMENT_CONTRACT_LAST_MODE = "cs.summary.employment_contract_last_mode"
    EMPLOYMENT_CONTRACT_LAST_MODELS = "cs.summary.employment_contract_last_models"
    ESCO_CONFIG = "cs.esco_config"
    ESCO_OCCUPATION_SELECTED = "cs.esco_occupation_selected"
    ESCO_OCCUPATION_PAYLOAD = "cs.esco_occupation_payload"
    ESCO_OCCUPATION_CANDIDATES = "cs.esco_occupation_candidates"
    ESCO_MATCH_REASON = "cs.esco_match_reason"
    ESCO_MATCH_CONFIDENCE = "cs.esco_match_confidence"
    ESCO_MATCH_PROVENANCE = "cs.esco_match_provenance"
    ESCO_SKILLS_SELECTED_MUST = "cs.esco_skills_selected_must"
    ESCO_SKILLS_SELECTED_NICE = "cs.esco_skills_selected_nice"
    ESCO_SKILLS_MAPPING_REPORT = "cs.esco_skills_mapping_report"
    ESCO_SKILL_DETAIL_CACHE = "cs.esco_skill_detail_cache"
    ESCO_OCCUPATION_TITLE_VARIANTS = "cs.esco_occupation_title_variants"
    ESCO_MIGRATION_LOG = "cs.esco_migration_log"
    ESCO_MIGRATION_PENDING = "cs.esco_migration_pending"
    EURES_NACE_TO_ESCO = "cs.eures_nace_to_esco"
    EURES_NACE_SOURCE = "cs.eures_nace_source"
    COMPANY_NACE_CODE = "cs.company_nace_code"
    ROLE_TASKS_JOBSPEC_SUGGESTED = "cs.role_tasks.jobspec_suggested"
    ROLE_TASKS_ESCO_SUGGESTED = "cs.role_tasks.esco_suggested"
    ROLE_TASKS_LLM_SUGGESTED = "cs.role_tasks.llm_suggested"
    ROLE_TASKS_SELECTED = "cs.role_tasks.selected"
    ROLE_TASKS_SUGGEST_COUNT = "cs.role_tasks.suggest_count"
    SKILLS_JOBSPEC_SUGGESTED = "cs.skills.jobspec_suggested"
    SKILLS_LLM_SUGGESTED = "cs.skills.llm_suggested"
    SKILLS_SELECTED = "cs.skills.selected"
    SKILLS_SUGGEST_COUNT = "cs.skills.suggest_count"


# ---- Wizard Steps (match your screenshot structure) ----
@dataclass(frozen=True)
class WizardStepDef:
    key: str
    title_de: str
    icon: str


STEPS: Final[List[WizardStepDef]] = [
    WizardStepDef(key="landing", title_de="Start", icon="🏁"),
    WizardStepDef(
        key="jobspec_review",
        title_de="Identifizierte Informationen",
        icon="🧾",
    ),
    WizardStepDef(key="company", title_de="Unternehmen", icon="🏢"),
    WizardStepDef(key="team", title_de="Team", icon="👥"),
    WizardStepDef(key="role_tasks", title_de="Rolle & Aufgaben", icon="🧭"),
    WizardStepDef(key="skills", title_de="Skills & Anforderungen", icon="🧠"),
    WizardStepDef(key="benefits", title_de="Benefits & Rahmenbedingungen", icon="🎁"),
    WizardStepDef(key="interview", title_de="Interviewprozess", icon="🗓️"),
    WizardStepDef(key="summary", title_de="Zusammenfassung", icon="✅"),
]


# ---- Question types ----
class AnswerType(str, Enum):
    SHORT_TEXT = "short_text"
    LONG_TEXT = "long_text"
    SINGLE_SELECT = "single_select"
    MULTI_SELECT = "multi_select"
    NUMBER = "number"
    BOOLEAN = "boolean"
    DATE = "date"


QUESTION_SCHEMA_VERSION: Final[str] = "2026-04-09"
VACANCY_SCHEMA_VERSION: Final[str] = "2026-04-07"
JOB_AD_SCHEMA_VERSION: Final[str] = "2026-04-07"
SUMMARY_ARTIFACT_IDS: Final[tuple[str, ...]] = (
    "brief",
    "job_ad",
    "interview_hr",
    "interview_fach",
    "boolean_search",
    "employment_contract",
)
SUMMARY_ARTIFACT_LEGACY_ALIASES: Final[dict[str, str]] = {
    "recruiting_brief": "brief",
    "job_ad_generator": "job_ad",
    "interview_hr_sheet": "interview_hr",
    "interview_fach_sheet": "interview_fach",
}

# Prefix used to generate stable Streamlit widget keys per question
WIDGET_KEY_PREFIX: Final[str] = "cs.q::"
