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
DEFAULT_ESCO_SELECTED_VERSION: Final[str] = "v1.2.0"
DEFAULT_ESCO_INDEX_STORAGE_PATH: Final[str] = "data/esco_index"
DEFAULT_ESCO_DATA_SOURCE_MODE: Final[str] = "live_api"
ESCO_DATA_SOURCE_MODES: Final[tuple[str, str, str]] = ("live_api", "offline_index", "hybrid")
UI_MODE_VALUES: Final[tuple[str, str, str]] = ("quick", "standard", "expert")
UI_MODE_DISPLAY_LABELS: Final[dict[str, str]] = {
    "quick": "schnell",
    "standard": "ausführlich",
    "expert": "vollumfänglich",
}
UI_DETAILS_DEFAULT_BY_MODE_TEXT: Final[str] = (
    f"{UI_MODE_DISPLAY_LABELS['quick'].capitalize()}/"
    f"{UI_MODE_DISPLAY_LABELS['standard'].capitalize()}: "
    "Detailgruppen standardmäßig kompakt. "
    f"{UI_MODE_DISPLAY_LABELS['expert'].capitalize()}: "
    "Detailgruppen standardmäßig geöffnet."
)
UI_MODE_HELP_TEXT: Final[str] = UI_DETAILS_DEFAULT_BY_MODE_TEXT
UI_GLOBAL_DETAILS_TOGGLE_LABEL: Final[str] = "Details standardmäßig öffnen"
UI_GLOBAL_DETAILS_TOGGLE_HELP: Final[str] = (
    "Globale Voreinstellung für Detailgruppen in allen Wizard-Schritten. "
    f"{UI_DETAILS_DEFAULT_BY_MODE_TEXT}"
)
UI_STEP_COMPACT_TOGGLE_LABEL: Final[str] = "Details kompakt anzeigen"
UI_STEP_COMPACT_TOGGLE_HELP: Final[str] = (
    "Schritt-spezifische Anzeige: Aktiv hält Detailgruppen standardmäßig geschlossen. "
    "Deaktiviert öffnet Detailgruppen standardmäßig."
)
UI_PREFERENCE_ANSWER_MODE: Final[str] = "answer_mode"
UI_PREFERENCE_INFORMATION_DEPTH: Final[str] = "information_depth"
UI_PREFERENCE_ESCO_MATCHING_STRICTNESS: Final[str] = "esco_matching_strictness"
UI_PREFERENCE_REGIONAL_FOCUS: Final[str] = "regional_focus"
UI_PREFERENCE_SHOW_SOURCES_DEFAULT: Final[str] = "show_sources_default"
UI_PREFERENCE_CONFIDENCE_THRESHOLD: Final[str] = "confidence_threshold"
UI_PREFERENCE_PII_REDUCTION: Final[str] = "pii_reduction"
UI_PREFERENCE_DETAILS_EXPANDED_DEFAULT: Final[str] = "details_expanded_default"
UI_PREFERENCE_STEP_COMPACT: Final[str] = "step_compact"

COMPLETION_STATE_COMPLETE: Final[str] = "complete"
COMPLETION_STATE_PARTIAL: Final[str] = "partial"
COMPLETION_STATE_NOT_STARTED: Final[str] = "not_started"
COMPLETION_STATES: Final[tuple[str, str, str]] = (
    COMPLETION_STATE_COMPLETE,
    COMPLETION_STATE_PARTIAL,
    COMPLETION_STATE_NOT_STARTED,
)
COMPLETION_STATE_BADGE_TEXT: Final[dict[str, str]] = {
    COMPLETION_STATE_COMPLETE: "✅ Vollständig",
    COMPLETION_STATE_PARTIAL: "🟡 Teilweise",
    COMPLETION_STATE_NOT_STARTED: "⬜ Offen",
}
COMPLETION_STATE_PREFIX_TOKENS: Final[dict[str, str]] = {
    COMPLETION_STATE_COMPLETE: "✅",
    COMPLETION_STATE_PARTIAL: "🟡",
    COMPLETION_STATE_NOT_STARTED: "⬜",
}

# ---- Canonical Wizard Step Keys ----
STEP_KEY_LANDING: Final[str] = "landing"
# Legacy-only key: previously rendered as a standalone step via 01a_jobspec_review.py.
# The integrated flow now handles extraction review and ESCO confirmation directly in
# Start phases B/C, so this key must stay out of active runtime step contracts.
STEP_KEY_JOBSPEC_REVIEW: Final[str] = "jobspec_review"
STEP_KEY_COMPANY: Final[str] = "company"
# Legacy-only key: Team is no longer part of the visible canonical wizard
# navigation, but this step key remains for backward compatibility with
# historical question plans/answers and legacy artifacts.
STEP_KEY_TEAM: Final[str] = "team"
STEP_KEY_ROLE_TASKS: Final[str] = "role_tasks"
STEP_KEY_SKILLS: Final[str] = "skills"
STEP_KEY_BENEFITS: Final[str] = "benefits"
STEP_KEY_INTERVIEW: Final[str] = "interview"
STEP_KEY_SUMMARY: Final[str] = "summary"

# Plan/System steps that are intentionally excluded from intake completion/facts views.
NON_INTAKE_STEP_KEYS: Final[tuple[str, ...]] = (
    STEP_KEY_LANDING,
    STEP_KEY_SUMMARY,
)


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
    SALARY_SCENARIO_PENDING_SKILLS_ADD = "cs.salary.scenario.pending.skills_add"
    SALARY_SCENARIO_PENDING_SKILLS_REMOVE = "cs.salary.scenario.pending.skills_remove"
    SALARY_SCENARIO_PENDING_LOCATION_CITY_OVERRIDE = "cs.salary.scenario.pending.city"
    SALARY_SCENARIO_PENDING_RADIUS_KM = "cs.salary.scenario.pending.radius_km"
    SALARY_SCENARIO_PENDING_REMOTE_SHARE_PERCENT = (
        "cs.salary.scenario.pending.remote_share_percent"
    )
    SALARY_SCENARIO_PENDING_SENIORITY_OVERRIDE = (
        "cs.salary.scenario.pending.seniority_override"
    )
    SALARY_SCENARIO_APPLY_PENDING_UPDATE = "cs.salary.scenario.pending.apply_update"
    SALARY_SCENARIO_PENDING_SELECTED_ROW_ID = "cs.salary.scenario.pending.selected_row"
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
    ESCO_LAST_DATA_SOURCE = "cs.esco_last_data_source"
    ESCO_OCCUPATION_SELECTED = "cs.esco_occupation_selected"
    ESCO_SELECTED_OCCUPATION_URI = "cs.esco_selected_occupation_uri"
    ESCO_OCCUPATION_PAYLOAD = "cs.esco_occupation_payload"
    ESCO_OCCUPATION_RELATED_COUNTS = "cs.esco_occupation_related_counts"
    ESCO_OCCUPATION_SKILL_GROUP_SHARE = "cs.esco_occupation_skill_group_share"
    ESCO_OCCUPATION_CANDIDATES = "cs.esco_occupation_candidates"
    ESCO_MATCH_REASON = "cs.esco_match_reason"
    ESCO_MATCH_CONFIDENCE = "cs.esco_match_confidence"
    ESCO_MATCH_PROVENANCE = "cs.esco_match_provenance"
    ESCO_SKILLS_SELECTED_MUST = "cs.esco_skills_selected_must"
    ESCO_SKILLS_SELECTED_NICE = "cs.esco_skills_selected_nice"
    ESCO_CONFIRMED_ESSENTIAL_SKILLS = "cs.esco_confirmed_essential_skills"
    ESCO_CONFIRMED_OPTIONAL_SKILLS = "cs.esco_confirmed_optional_skills"
    ESCO_UNMAPPED_REQUIREMENT_TERMS = "cs.esco_unmapped_requirement_terms"
    ESCO_UNMAPPED_ROLE_TERMS = "cs.esco_unmapped_role_terms"
    ESCO_UNMAPPED_TERM_ACTIONS = "cs.esco_unmapped_term_actions"
    ESCO_UNRESOLVED_TERM_DECISIONS = "cs.esco_unresolved_term_decisions"
    ESCO_SKILLS_MAPPING_REPORT = "cs.esco_skills_mapping_report"
    ESCO_SKILL_DETAIL_CACHE = "cs.esco_skill_detail_cache"
    ESCO_OCCUPATION_TITLE_VARIANTS = "cs.esco_occupation_title_variants"
    ESCO_NEGATIVE_CACHE = "cs.esco_negative_cache"
    ESCO_MIGRATION_LOG = "cs.esco_migration_log"
    ESCO_MIGRATION_PENDING = "cs.esco_migration_pending"
    ESCO_MATRIX_ENABLED = "cs.esco_matrix_enabled"
    ESCO_MATRIX_METADATA = "cs.esco_matrix_metadata"
    ESCO_MATRIX_LOADED = "cs.esco_matrix_loaded"
    ESCO_MATRIX_COVERAGE_ROWS = "cs.esco_matrix_coverage_rows"
    ESCO_MATRIX_COVERAGE_CONTEXT = "cs.esco_matrix_coverage_context"
    COMPANY_WEBSITE_RESEARCH = "cs.company_website_research"
    COMPANY_WEBSITE_SELECTED_MATCHES = "cs.company_website_selected_matches"
    COMPANY_WEBSITE_LAST_ERROR = "cs.company_website_last_error"
    COMPANY_WEBSITE_MANUAL_URL = "cs.company_website_manual_url"
    ROLE_TASKS_JOBSPEC_SUGGESTED = "cs.role_tasks.jobspec_suggested"
    ROLE_TASKS_ESCO_SUGGESTED = "cs.role_tasks.esco_suggested"
    ROLE_TASKS_LLM_SUGGESTED = "cs.role_tasks.llm_suggested"
    ROLE_TASKS_SELECTED = "cs.role_tasks.selected"
    ROLE_TASKS_SUGGEST_COUNT = "cs.role_tasks.suggest_count"
    INTERVIEW_INTERNAL_FLOW = "cs.interview.internal_flow"
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
    WizardStepDef(key=STEP_KEY_LANDING, title_de="Start", icon="🏁"),
    WizardStepDef(key=STEP_KEY_COMPANY, title_de="Unternehmen", icon="🏢"),
    WizardStepDef(key=STEP_KEY_ROLE_TASKS, title_de="Rolle & Aufgaben", icon="🧭"),
    WizardStepDef(key=STEP_KEY_SKILLS, title_de="Skills & Anforderungen", icon="🧠"),
    WizardStepDef(
        key=STEP_KEY_BENEFITS,
        title_de="Benefits & Rahmenbedingungen",
        icon="🎁",
    ),
    WizardStepDef(key=STEP_KEY_INTERVIEW, title_de="Interviewprozess", icon="🗓️"),
    WizardStepDef(key=STEP_KEY_SUMMARY, title_de="Zusammenfassung", icon="✅"),
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
VACANCY_SCHEMA_VERSION: Final[str] = "2026-04-14"
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
SUMMARY_SESSION_KEY_LEGACY_ALIASES: Final[dict[SSKey, tuple[str, ...]]] = {
    SSKey.SUMMARY_ACTIVE_ARTIFACT: (
        "cs.summary.active_artifact",
        "cs.summary.active_action",
    ),
    SSKey.SUMMARY_SELECTIONS: ("cs.summary.selections",),
    SSKey.SUMMARY_STYLEGUIDE_TEXT: ("cs.summary.style_guide",),
    SSKey.SUMMARY_CHANGE_REQUEST_TEXT: ("cs.summary.change_requests",),
}
STALE_REDESIGN_SESSION_KEY_PREFIXES: Final[tuple[str, ...]] = (
    "cs.redesign.",
    "cs.summary.redesign.",
)

# Prefix used to generate stable Streamlit widget keys per question
WIDGET_KEY_PREFIX: Final[str] = "cs.q::"
