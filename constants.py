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


APP_NAME: Final[str] = "Cognitive Staffing"
APP_TAGLINE: Final[str] = "AI-gestützte Kompetenz- und Matching-Workflows"
APP_TITLE: Final[str] = f"{APP_NAME} – Vacancy Intake Wizard"
DEFAULT_LANGUAGE: Final[str] = "de"
DEFAULT_ESCO_SELECTED_VERSION: Final[str] = "v1.2.0"
ESCO_RELEASE_LANE_STABLE: Final[str] = "stable"
ESCO_RELEASE_LANE_PREVIEW: Final[str] = "preview"
DEFAULT_ESCO_RELEASE_LANE: Final[str] = ESCO_RELEASE_LANE_STABLE
ESCO_RELEASE_LANES: Final[tuple[str, str]] = (
    ESCO_RELEASE_LANE_STABLE,
    ESCO_RELEASE_LANE_PREVIEW,
)
ESCO_RELEASE_LANE_SELECTED_VERSION: Final[dict[str, str]] = {
    ESCO_RELEASE_LANE_STABLE: "v1.2.0",
    ESCO_RELEASE_LANE_PREVIEW: "v1.2.1",
}
DEFAULT_ESCO_INDEX_STORAGE_PATH: Final[str] = "data/esco_index"
DEFAULT_ESCO_DATA_SOURCE_MODE: Final[str] = "live_api"
ESCO_DATA_SOURCE_MODES: Final[tuple[str, str, str]] = ("live_api", "offline_index", "hybrid")
ESCO_API_MODES: Final[tuple[str, str]] = ("hosted", "local")
ESCO_ANCHOR_STATE_DEGRADED: Final[str] = "degraded_unconfirmed"
ESCO_ANCHOR_STATE_ANCHORED: Final[str] = "anchored"
ESCO_ANCHOR_STATE_ANCHORED_WITH_CONTEXT: Final[str] = "anchored_with_context"
ESCO_ANCHOR_STATES: Final[tuple[str, str, str]] = (
    ESCO_ANCHOR_STATE_DEGRADED,
    ESCO_ANCHOR_STATE_ANCHORED,
    ESCO_ANCHOR_STATE_ANCHORED_WITH_CONTEXT,
)
ESCO_SEMANTIC_EXPORT_MODE_DEGRADED: Final[str] = "degraded"
ESCO_SEMANTIC_EXPORT_MODE_ANCHORED: Final[str] = "anchored"
ESCO_SEMANTIC_EXPORT_MODES: Final[tuple[str, str]] = (
    ESCO_SEMANTIC_EXPORT_MODE_DEGRADED,
    ESCO_SEMANTIC_EXPORT_MODE_ANCHORED,
)
ESCO_SECONDARY_ANCHOR_MAX: Final[int] = 2
OCCUPATION_QUESTION_MODULE_BASE: Final[str] = "BASE_RECRUITING"
OCCUPATION_QUESTION_MODULE_ISCO1_PREFIX: Final[str] = "ISCO1"
OCCUPATION_QUESTION_MODULE_ISCO3_PREFIX: Final[str] = "ISCO3"
OCCUPATION_QUESTION_MODULE_ISCO4_PREFIX: Final[str] = "ISCO4"
OCCUPATION_QUESTION_MODULE_ESCO_PREFIX: Final[str] = "ESCO_OCCUPATION"
OCCUPATION_QUESTION_MODULE_SKILL_GROUP_PREFIX: Final[str] = "SKILL_GROUP"
OCCUPATION_QUESTION_MODULE_NACE_PREFIX: Final[str] = "NACE"
OCCUPATION_QUESTION_MODULE_REGULATED: Final[str] = "REGULATED_PROFESSION"
ESCO_QUESTION_SKILL_GROUP_DOMAIN_KNOWLEDGE: Final[str] = "domain_knowledge"
ESCO_QUESTION_SKILL_GROUP_TOOLS_METHODS: Final[str] = "tools_methods"
ESCO_QUESTION_SKILL_GROUP_REGULATION_SAFETY: Final[str] = "regulation_safety"
ESCO_QUESTION_SKILL_GROUP_CUSTOMER_CLIENT_INTERACTION: Final[str] = (
    "customer_client_interaction"
)
ESCO_QUESTION_SKILL_GROUP_DOCUMENTATION_REPORTING: Final[str] = (
    "documentation_reporting"
)
ESCO_QUESTION_SKILL_GROUP_LEADERSHIP_COORDINATION: Final[str] = (
    "leadership_coordination"
)
ESCO_QUESTION_SKILL_GROUP_PHYSICAL_MANUAL_CONTEXT: Final[str] = (
    "physical_manual_context"
)
ESCO_QUESTION_SKILL_GROUP_DIGITAL_DATA_AI: Final[str] = "digital_data_ai"
ESCO_QUESTION_SKILL_GROUP_LANGUAGE_COMMUNICATION: Final[str] = (
    "language_communication"
)
ESCO_QUESTION_SKILL_GROUP_TRANSVERSAL_FIT: Final[str] = "transversal_fit"
ESCO_QUESTION_SKILL_GROUP_IDS: Final[tuple[str, ...]] = (
    ESCO_QUESTION_SKILL_GROUP_DOMAIN_KNOWLEDGE,
    ESCO_QUESTION_SKILL_GROUP_TOOLS_METHODS,
    ESCO_QUESTION_SKILL_GROUP_REGULATION_SAFETY,
    ESCO_QUESTION_SKILL_GROUP_CUSTOMER_CLIENT_INTERACTION,
    ESCO_QUESTION_SKILL_GROUP_DOCUMENTATION_REPORTING,
    ESCO_QUESTION_SKILL_GROUP_LEADERSHIP_COORDINATION,
    ESCO_QUESTION_SKILL_GROUP_PHYSICAL_MANUAL_CONTEXT,
    ESCO_QUESTION_SKILL_GROUP_DIGITAL_DATA_AI,
    ESCO_QUESTION_SKILL_GROUP_LANGUAGE_COMMUNICATION,
    ESCO_QUESTION_SKILL_GROUP_TRANSVERSAL_FIT,
)
QUESTION_GROUP_DISPLAY_LABELS_DE: Final[dict[str, str]] = {
    "must_nice_trainable": "Skill-Priorisierung",
    "data_hygiene": "Datenqualität",
    "tech_stack": "Tech Stack",
    "licenses": "Nachweise & Lizenzen",
    "compensation_contract": "Vergütung & Vertrag",
    "legal_contract": "Rechtliches",
    "offer_components": "Angebot",
    "timeline": "Timing",
    "assessment": "Assessment",
    "stage_evaluation": "Bewertung",
    "candidate_communication": "Kommunikation",
    "process_compliance": "Prozess & Compliance",
    ESCO_QUESTION_SKILL_GROUP_DOMAIN_KNOWLEDGE: "Fachwissen",
    ESCO_QUESTION_SKILL_GROUP_TOOLS_METHODS: "Tools & Methoden",
    ESCO_QUESTION_SKILL_GROUP_REGULATION_SAFETY: "Regulierung & Sicherheit",
    ESCO_QUESTION_SKILL_GROUP_CUSTOMER_CLIENT_INTERACTION: "Kundenkontakt",
    ESCO_QUESTION_SKILL_GROUP_DOCUMENTATION_REPORTING: "Dokumentation & Reporting",
    ESCO_QUESTION_SKILL_GROUP_LEADERSHIP_COORDINATION: "Führung & Koordination",
    ESCO_QUESTION_SKILL_GROUP_PHYSICAL_MANUAL_CONTEXT: "Arbeitsumgebung",
    ESCO_QUESTION_SKILL_GROUP_DIGITAL_DATA_AI: "Digital, Data & AI",
    ESCO_QUESTION_SKILL_GROUP_LANGUAGE_COMMUNICATION: "Sprache & Kommunikation",
    ESCO_QUESTION_SKILL_GROUP_TRANSVERSAL_FIT: "Arbeitsweise",
}
ESCO_CONCEPT_QUESTION_CAP_BY_UI_MODE: Final[dict[str, int]] = {
    "quick": 3,
    "standard": 6,
    "expert": 10,
}
UI_MODE_VALUES: Final[tuple[str, str, str]] = ("quick", "standard", "expert")
UI_MODE_DEFAULT: Final[str] = "expert"
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
UI_PREFERENCE_UI_LANGUAGE: Final[str] = "ui_language"

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
# Deprecated routed step key: Team is intentionally excluded from canonical wizard
# routing/sidebar navigation, but this key remains as a compatibility contract for
# historical question plans/answers and summary/progress logic that may still carry
# `step_key == "team"` data.
STEP_KEY_TEAM: Final[str] = "team"
STEP_KEY_ROLE_TASKS: Final[str] = "role_tasks"
STEP_KEY_SKILLS: Final[str] = "skills"
STEP_KEY_BENEFITS: Final[str] = "benefits"
STEP_KEY_INTERVIEW: Final[str] = "interview"
STEP_KEY_SUMMARY: Final[str] = "summary"

QUESTION_IMPACT_TARGET_BRIEF: Final[str] = "brief"
QUESTION_IMPACT_TARGET_SALARY: Final[str] = "salary"
QUESTION_IMPACT_TARGET_SKILLS: Final[str] = "skills"
QUESTION_IMPACT_TARGET_INTERVIEW: Final[str] = "interview"
QUESTION_IMPACT_TARGET_EXPORT: Final[str] = "export"
QUESTION_IMPACT_TARGETS: Final[tuple[str, str, str, str, str]] = (
    QUESTION_IMPACT_TARGET_BRIEF,
    QUESTION_IMPACT_TARGET_SALARY,
    QUESTION_IMPACT_TARGET_SKILLS,
    QUESTION_IMPACT_TARGET_INTERVIEW,
    QUESTION_IMPACT_TARGET_EXPORT,
)

# Plan/System steps that are intentionally excluded from intake completion/facts views.
NON_INTAKE_STEP_KEYS: Final[tuple[str, ...]] = (
    STEP_KEY_LANDING,
    STEP_KEY_SUMMARY,
)

JOBSPEC_NOTE_ROUTE_STEP_KEYS: Final[tuple[str, ...]] = (
    STEP_KEY_BENEFITS,
    STEP_KEY_COMPANY,
    STEP_KEY_ROLE_TASKS,
    STEP_KEY_SKILLS,
    STEP_KEY_INTERVIEW,
)
JOBSPEC_NOTE_ROUTE_KEYWORDS: Final[dict[str, tuple[str, ...]]] = {
    STEP_KEY_BENEFITS: (
        "salary",
        "gehalt",
        "gehalts",
        "vergütung",
        "compensation",
        "benefit",
        "benefits",
        "perk",
        "bonus",
        "budget",
        "urlaub",
        "arbeitszeit",
        "rahmenbedingung",
    ),
    STEP_KEY_COMPANY: (
        "company",
        "company_name",
        "unternehmen",
        "firma",
        "brand",
        "website",
        "homepage",
        "location",
        "standort",
        "arbeitsstandort",
        "place_of_work",
        "ort",
        "remote",
        "hybrid",
        "travel",
        "reise",
        "on call",
        "on_call",
        "rufbereitschaft",
        "department",
        "abteilung",
        "reports_to",
        "team",
    ),
    STEP_KEY_ROLE_TASKS: (
        "role",
        "rolle",
        "scope",
        "responsibility",
        "responsibilities",
        "verantwort",
        "aufgabe",
        "deliverable",
        "liefer",
        "success",
        "erfolg",
        "ziel",
        "seniority",
        "seniorität",
        "onboarding",
    ),
    STEP_KEY_SKILLS: (
        "skill",
        "skills",
        "fähigkeit",
        "kenntnis",
        "anforderung",
        "must",
        "nice",
        "education",
        "ausbildung",
        "certificate",
        "certification",
        "zertifikat",
        "language",
        "sprache",
        "tech",
        "technologie",
        "domain",
        "branche",
        "expertise",
    ),
    STEP_KEY_INTERVIEW: (
        "process",
        "prozess",
        "recruit",
        "bewerbung",
        "interview",
        "contact",
        "kontakt",
        "step",
        "schritt",
        "start",
        "deadline",
        "frist",
        "questionplan",
        "question_plan",
        "question plan",
    ),
}
JOBSPEC_ASSUMPTION_ANSWER_ID_PREFIX: Final[str] = "jobspec_assumption."


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
    INTAKE_FACTS = "cs.intake_facts"
    INTAKE_FACT_EVIDENCE = "cs.intake_fact_evidence"
    QUESTION_PLAN_BASE = "cs.question_plan_base"
    QUESTION_PLAN = "cs.question_plan"
    QUESTION_LIMITS = "cs.question_limits"
    OCCUPATION_PROFILE = "cs.occupation.profile"
    OCCUPATION_QUESTION_CONTEXT = "cs.occupation.question_context"
    OCCUPATION_CLASSIFICATION_TRACE = "cs.occupation.classification_trace"
    OCCUPATION_PACK_KEYS = "cs.occupation.pack_keys"
    QUESTION_FLOW_PROVENANCE = "cs.question_flow_provenance"
    QUESTION_FLOW_FINGERPRINT = "cs.question_flow_fingerprint"
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
    USAGE_EVENTS = "cs.usage_events"
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
    SUMMARY_ARTIFACT_OPTIONS = "cs.summary.artifact_options"
    SUMMARY_ARTIFACT_CHANGE_REQUESTS = "cs.summary.artifact_change_requests"
    SUMMARY_ARTIFACT_FINGERPRINTS = "cs.summary.artifact_fingerprints"
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
    SALARY_FORECAST_INPUT_FINGERPRINT = "cs.salary.forecast.input_fingerprint"
    SALARY_FORECAST_INPUT_SELECTIONS = "cs.salary.forecast.input_selections"
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
    ESCO_RELEASE_LANE = "cs.esco_release_lane"
    ESCO_ANCHOR_STATE = "cs.esco_anchor_state"
    ESCO_PRIMARY_ANCHOR = "cs.esco_primary_anchor"
    ESCO_SECONDARY_ANCHORS = "cs.esco_secondary_anchors"
    ESCO_SEMANTIC_EXPORT_MODE = "cs.esco_semantic_export_mode"
    ESCO_CAPABILITY_SNAPSHOT = "cs.esco_capability_snapshot"
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
    ESCO_SKILLS_REMOVED = "cs.esco_skills_removed"
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
    COMPANY_WEBSITE_FACT_REVIEW = "cs.company_website_fact_review"
    COMPANY_WEBSITE_LAST_ERROR = "cs.company_website_last_error"
    COMPANY_WEBSITE_MANUAL_URL = "cs.company_website_manual_url"
    ROLE_TASKS_JOBSPEC_SUGGESTED = "cs.role_tasks.jobspec_suggested"
    ROLE_TASKS_ESCO_SUGGESTED = "cs.role_tasks.esco_suggested"
    ROLE_TASKS_LLM_SUGGESTED = "cs.role_tasks.llm_suggested"
    ROLE_TASKS_SELECTED = "cs.role_tasks.selected"
    ROLE_TASKS_SUGGEST_COUNT = "cs.role_tasks.suggest_count"
    ROLE_TASKS_JOBSPEC_PILLS = "cs.role_tasks.jobspec_pills"
    ROLE_TASKS_ESCO_PILLS = "cs.role_tasks.esco_pills"
    ROLE_TASKS_AI_PILLS = "cs.role_tasks.ai_pills"
    ROLE_TASKS_SELECTED_BULK_BUFFER = "cs.role_tasks.selected_bulk_buffer"
    INTERVIEW_INTERNAL_FLOW = "cs.interview.internal_flow"
    SKILLS_JOBSPEC_SUGGESTED = "cs.skills.jobspec_suggested"
    SKILLS_LLM_SUGGESTED = "cs.skills.llm_suggested"
    SKILLS_AI_INITIAL_GENERATED = "cs.skills.ai_initial_generated"
    SKILLS_SELECTED = "cs.skills.selected"
    SKILLS_SELECTED_STATUS = "cs.skills.selected_status"
    SKILLS_SUGGEST_COUNT = "cs.skills.suggest_count"
    SKILLS_JOBSPEC_PILLS = "cs.skills.jobspec_pills"
    SKILLS_ESCO_PILLS = "cs.skills.esco_pills"
    SKILLS_AI_PILLS = "cs.skills.ai_pills"
    SKILLS_SELECTED_BULK_BUFFER = "cs.skills.selected_bulk_buffer"
    SKILLS_ESCO_LOAD_CLICKED = "cs.skills.esco_load_clicked"
    SKILLS_ESCO_SEARCH = "cs.skills.esco_search"
    SKILLS_ESCO_SORT = "cs.skills.esco_sort"
    SKILLS_AI_GENERATE_CLICKED = "cs.skills.ai_generate_clicked"
    BENEFITS_JOBSPEC_SUGGESTED = "cs.benefits.jobspec_suggested"
    BENEFITS_LLM_SUGGESTED = "cs.benefits.llm_suggested"
    BENEFITS_SELECTED = "cs.benefits.selected"
    BENEFITS_SELECTED_BULK_BUFFER = "cs.benefits.selected_bulk_buffer"
    BENEFITS_JOBSPEC_PILLS = "cs.benefits.jobspec_pills"
    BENEFITS_CONTEXT_PILLS = "cs.benefits.context_pills"
    BENEFITS_AI_PILLS = "cs.benefits.ai_pills"
    BENEFITS_SUGGEST_COUNT = "cs.benefits.suggest_count"
    BENEFITS_AI_GENERATE_CLICKED = "cs.benefits.ai_generate_clicked"
    BENEFITS_AI_INITIAL_GENERATED = "cs.benefits.ai_initial_generated"
    BENEFITS_REGION_CONTEXT = "cs.benefits.region_context"


# ---- Wizard Steps (canonical routed/visible wizard navigation only) ----
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

# ---- Wizard Step Sections ----
STEP_SECTION_EXTRACTED_FROM_JOBSPEC: Final[str] = "extracted_from_jobspec"
STEP_SECTION_SOURCE_COMPARISON: Final[str] = "source_comparison"
STEP_SECTION_SALARY_FORECAST: Final[str] = "salary_forecast"
STEP_SECTION_OPEN_QUESTIONS: Final[str] = "open_questions"
STEP_SECTION_REVIEW: Final[str] = "review"
STEP_SECTION_IDS: Final[tuple[str, ...]] = (
    STEP_SECTION_EXTRACTED_FROM_JOBSPEC,
    STEP_SECTION_SOURCE_COMPARISON,
    STEP_SECTION_SALARY_FORECAST,
    STEP_SECTION_OPEN_QUESTIONS,
    STEP_SECTION_REVIEW,
)
STEP_SECTION_LABELS_DE: Final[dict[str, str]] = {
    STEP_SECTION_EXTRACTED_FROM_JOBSPEC: "Aus Jobspec extrahiert",
    STEP_SECTION_SOURCE_COMPARISON: "Quellenabgleich",
    STEP_SECTION_SALARY_FORECAST: "Gehaltsprognose",
    STEP_SECTION_OPEN_QUESTIONS: "Offene Fragen",
    STEP_SECTION_REVIEW: "Review",
}
STEP_SECTION_SLOT_NAMES: Final[dict[str, str]] = {
    STEP_SECTION_EXTRACTED_FROM_JOBSPEC: "extracted_from_jobspec_slot",
    STEP_SECTION_SOURCE_COMPARISON: "source_comparison_slot",
    STEP_SECTION_SALARY_FORECAST: "salary_forecast_slot",
    STEP_SECTION_OPEN_QUESTIONS: "open_questions_slot",
    STEP_SECTION_REVIEW: "review_slot",
}


# ---- Question types ----
class AnswerType(str, Enum):
    SHORT_TEXT = "short_text"
    LONG_TEXT = "long_text"
    SINGLE_SELECT = "single_select"
    MULTI_SELECT = "multi_select"
    NUMBER = "number"
    BOOLEAN = "boolean"
    DATE = "date"


# ---- Canonical intake fact contract ----
class FactKey(str, Enum):
    INTAKE_HIRING_REASON = "intake.hiring_reason"
    INTAKE_URGENCY = "intake.urgency"
    INTAKE_HIRING_VOLUME = "intake.hiring_volume"
    INTAKE_SEARCH_CONFIDENTIALITY = "intake.search_confidentiality"
    INTAKE_ROLE_DEFINITION_MATURITY = "intake.role_definition_maturity"
    COMPANY_LANGUAGE_GUESS = "company.language_guess"
    COMPANY_COMPANY_NAME = "company.company_name"
    COMPANY_BRAND_NAME = "company.brand_name"
    COMPANY_COMPANY_WEBSITE = "company.company_website"
    COMPANY_LOCATION_CITY = "company.location_city"
    COMPANY_LOCATION_COUNTRY = "company.location_country"
    COMPANY_PLACE_OF_WORK = "company.place_of_work"
    COMPANY_REMOTE_POLICY = "company.remote_policy"
    COMPANY_WORK_ARRANGEMENT = "company.work_arrangement"
    COMPANY_OFFICE_DAYS_PER_WEEK = "company.office_days_per_week"
    COMPANY_ALLOWED_REGIONS_TIMEZONES = "company.allowed_regions_timezones"
    COMPANY_EMPLOYER_PITCH = "company.employer_pitch"
    COMPANY_ROLE_RELEVANT_POSITIONING = "company.role_relevant_positioning"
    COMPANY_BUSINESS_UNIT = "company.business_unit"
    COMPANY_HIRING_REASON = "company.hiring_reason"
    COMPANY_GROWTH_CONTEXT = "company.growth_context"
    COMPANY_ROLE_BUSINESS_IMPACT = "company.role_business_impact"
    COMPANY_LANGUAGE_INTERNAL = "company.language_internal"
    COMPANY_LANGUAGE_EXTERNAL = "company.language_external"
    COMPANY_NON_NEGOTIABLES = "company.non_negotiables"
    COMPANY_COMPLIANCE_CONTEXT = "company.compliance_context"
    COMPANY_TARIFF_CONTEXT = "company.tariff_context"
    COMPANY_DEPARTMENT_NAME = "company.department_name"
    COMPANY_REPORTS_TO = "company.reports_to"
    COMPANY_DIRECT_REPORTS_COUNT = "company.direct_reports_count"
    TEAM_NAME = "team.name"
    TEAM_LEADERSHIP_SCOPE = "team.leadership_scope"
    TEAM_SIZE_DIRECT = "team.size_direct"
    TEAM_STAKEHOLDERS_PRIMARY = "team.stakeholders_primary"
    TEAM_SUCCESS_CONTEXT_90D = "team.success_context_90d"
    ROLE_JOB_TITLE = "role.job_title"
    ROLE_EMPLOYMENT_TYPE = "role.employment_type"
    ROLE_CONTRACT_TYPE = "role.contract_type"
    ROLE_SENIORITY_LEVEL = "role.seniority_level"
    ROLE_JOB_REF_NUMBER = "role.job_ref_number"
    ROLE_ROLE_OVERVIEW = "role.role_overview"
    ROLE_RESPONSIBILITIES = "role.responsibilities"
    ROLE_RESPONSIBILITIES_PRIORITIZED = "role.responsibilities_prioritized"
    ROLE_DELIVERABLES = "role.deliverables"
    ROLE_SUCCESS_METRICS = "role.success_metrics"
    ROLE_SUCCESS_METRICS_TIMELINE = "role.success_metrics_timeline"
    ROLE_BUSINESS_OUTCOME_PRIMARY = "role.business_outcome_primary"
    ROLE_DAY1_RESPONSIBILITIES = "role.day1_responsibilities"
    ROLE_EXPANSION_SCOPE = "role.expansion_scope"
    ROLE_DECISION_SCOPE = "role.decision_scope"
    ROLE_YEAR1_SUCCESS_SIGNALS = "role.year1_success_signals"
    ROLE_TECH_STACK = "role.tech_stack"
    ROLE_DOMAIN_EXPERTISE = "role.domain_expertise"
    ROLE_TRAVEL_REQUIRED = "role.travel_required"
    ROLE_TRAVEL_PROFILE = "role.travel_profile"
    ROLE_ON_CALL = "role.on_call"
    ROLE_ONBOARDING_NOTES = "role.onboarding_notes"
    ROLE_GAPS = "role.gaps"
    ROLE_ASSUMPTIONS = "role.assumptions"
    SKILLS_ITEMS = "skills.items"
    SKILLS_MUST_HAVE_SKILLS = "skills.must_have_skills"
    SKILLS_NICE_TO_HAVE_SKILLS = "skills.nice_to_have_skills"
    SKILLS_SOFT_SKILLS = "skills.soft_skills"
    SKILLS_EDUCATION = "skills.education"
    SKILLS_CERTIFICATIONS = "skills.certifications"
    SKILLS_LANGUAGES = "skills.languages"
    SKILLS_READINESS_TIMING = "skills.readiness_timing"
    SKILLS_FREE_TEXT_REASON = "skills.free_text_reason"
    SKILLS_KNOCKOUT_CRITERIA = "skills.knockout_criteria"
    SKILLS_TRAINABLE_SKILLS = "skills.trainable_skills"
    BENEFITS_SALARY_RANGE = "benefits.salary_range"
    BENEFITS_VARIABLE_PAY = "benefits.variable_pay"
    BENEFITS_BENEFITS = "benefits.benefits"
    BENEFITS_SHIFT_COMPENSATION = "benefits.shift_compensation"
    BENEFITS_COLLECTIVE_AGREEMENT_CONTEXT = "benefits.collective_agreement_context"
    BENEFITS_OFFER_COMPONENTS = "benefits.offer_components"
    LEGAL_WORK_AUTHORIZATION_SUPPORT = "legal.work_authorization_support"
    TIMELINE_START_FLEXIBILITY = "timeline.start_flexibility"
    INTERVIEW_START_DATE = "interview.start_date"
    INTERVIEW_APPLICATION_DEADLINE = "interview.application_deadline"
    INTERVIEW_RECRUITMENT_STEPS = "interview.recruitment_steps"
    INTERVIEW_CONTACTS = "interview.contacts"
    INTERVIEW_ASSESSMENT_EVIDENCE = "interview.assessment_evidence"
    INTERVIEW_STAGE_OWNERS = "interview.stage_owners"
    INTERVIEW_COMMUNICATION_SLA = "interview.communication_sla"
    INTERVIEW_SCORECARD_TEMPLATE = "interview.scorecard_template"
    INTERVIEW_CORE_QUESTIONS = "interview.core_questions"
    INTERVIEW_COMPLIANCE_NOTES = "interview.compliance_notes"


class FactValueType(str, Enum):
    STRING = "string"
    STRING_LIST = "string_list"
    BOOLEAN = "boolean"
    INTEGER = "integer"
    DATE_STRING = "date_string"
    MONEY_RANGE = "money_range"
    OBJECT = "object"
    OBJECT_LIST = "object_list"


class FactPersistenceIntent(str, Enum):
    LEGACY_COMPATIBLE = "legacy_compatible"


class FactSalaryImpact(str, Enum):
    NONE = "none"
    QUALITY_INDIRECT = "quality_indirect"
    P50_DIRECT = "p50_direct"


class FactRequirementStage(str, Enum):
    BEFORE_SUMMARY = "before_summary"
    BEFORE_ARTIFACT = "before_artifact"
    OPTIONAL = "optional"


FACT_SALARY_IMPACT_DISPLAY_LABELS: Final[dict[FactSalaryImpact, str]] = {
    FactSalaryImpact.P50_DIRECT: "Salary-Treiber",
    FactSalaryImpact.QUALITY_INDIRECT: "Qualität/Unsicherheit",
    FactSalaryImpact.NONE: "Kein Salary-Einfluss",
}
FACT_REQUIREMENT_STAGE_DISPLAY_LABELS: Final[dict[FactRequirementStage, str]] = {
    FactRequirementStage.BEFORE_SUMMARY: "Pflicht vor Summary",
    FactRequirementStage.BEFORE_ARTIFACT: "Pflicht vor Artefakt",
    FactRequirementStage.OPTIONAL: "Optional",
}


class FactSourceType(str, Enum):
    MANUAL = "manual"
    JOBSPEC = "jobspec"
    HOMEPAGE = "homepage"
    ESCO = "esco"
    LLM = "llm"


class FactResolutionStatus(str, Enum):
    CONFIRMED = "confirmed"
    INFERRED = "inferred"
    ASSUMED = "assumed"
    CONFLICTED = "conflicted"
    MISSING = "missing"


class FactSensitivity(str, Enum):
    NORMAL = "normal"
    PERSONAL = "personal"
    RESTRICTED = "restricted"


class UsageEventType(str, Enum):
    STEP_ENTERED = "step_entered"
    STEP_SUBMITTED = "step_submitted"
    FACT_CONFIRMED = "fact_confirmed"
    FACT_CORRECTED = "fact_corrected"
    FACT_REJECTED = "fact_rejected"
    FALLBACK_MODEL_USED = "fallback_model_used"
    HOMEPAGE_FETCH_FAILED = "homepage_fetch_failed"
    ENRICHMENT_TIMED = "enrichment_timed"
    ARTIFACT_GENERATED = "artifact_generated"
    EVALUATION_RUN_COMPLETED = "evaluation_run_completed"


@dataclass(frozen=True)
class IntakeFactDef:
    fact_key: FactKey
    label: str
    step_key: str
    value_type: FactValueType
    persistence_intent: FactPersistenceIntent
    salary_impact: FactSalaryImpact
    requirement_stage: FactRequirementStage
    website_enrichable: bool


_FACT_PERSISTENCE_LEGACY_COMPATIBLE: Final[FactPersistenceIntent] = (
    FactPersistenceIntent.LEGACY_COMPATIBLE
)
SALARY_DRIVER_FACT_KEYS: Final[frozenset[FactKey]] = frozenset(
    {
        FactKey.BENEFITS_SALARY_RANGE,
        FactKey.ROLE_SENIORITY_LEVEL,
        FactKey.COMPANY_REMOTE_POLICY,
        FactKey.COMPANY_LOCATION_CITY,
        FactKey.COMPANY_LOCATION_COUNTRY,
        FactKey.ROLE_JOB_TITLE,
        FactKey.SKILLS_MUST_HAVE_SKILLS,
        FactKey.SKILLS_NICE_TO_HAVE_SKILLS,
        FactKey.SKILLS_CERTIFICATIONS,
        FactKey.SKILLS_LANGUAGES,
        FactKey.INTERVIEW_RECRUITMENT_STEPS,
    }
)
SALARY_QUALITY_DRIVER_FACT_KEYS: Final[frozenset[FactKey]] = frozenset(
    {
        FactKey.INTAKE_HIRING_REASON,
        FactKey.INTAKE_URGENCY,
        FactKey.INTAKE_HIRING_VOLUME,
        FactKey.INTAKE_SEARCH_CONFIDENTIALITY,
        FactKey.INTAKE_ROLE_DEFINITION_MATURITY,
        FactKey.COMPANY_WORK_ARRANGEMENT,
        FactKey.COMPANY_OFFICE_DAYS_PER_WEEK,
        FactKey.COMPANY_ALLOWED_REGIONS_TIMEZONES,
        FactKey.COMPANY_EMPLOYER_PITCH,
        FactKey.COMPANY_ROLE_RELEVANT_POSITIONING,
        FactKey.COMPANY_BUSINESS_UNIT,
        FactKey.COMPANY_HIRING_REASON,
        FactKey.COMPANY_GROWTH_CONTEXT,
        FactKey.COMPANY_ROLE_BUSINESS_IMPACT,
        FactKey.COMPANY_LANGUAGE_INTERNAL,
        FactKey.COMPANY_LANGUAGE_EXTERNAL,
        FactKey.COMPANY_NON_NEGOTIABLES,
        FactKey.COMPANY_COMPLIANCE_CONTEXT,
        FactKey.COMPANY_TARIFF_CONTEXT,
        FactKey.TEAM_NAME,
        FactKey.TEAM_LEADERSHIP_SCOPE,
        FactKey.TEAM_SIZE_DIRECT,
        FactKey.TEAM_STAKEHOLDERS_PRIMARY,
        FactKey.TEAM_SUCCESS_CONTEXT_90D,
        FactKey.ROLE_RESPONSIBILITIES,
        FactKey.ROLE_RESPONSIBILITIES_PRIORITIZED,
        FactKey.ROLE_SUCCESS_METRICS_TIMELINE,
        FactKey.ROLE_BUSINESS_OUTCOME_PRIMARY,
        FactKey.ROLE_DAY1_RESPONSIBILITIES,
        FactKey.ROLE_EXPANSION_SCOPE,
        FactKey.ROLE_DECISION_SCOPE,
        FactKey.ROLE_YEAR1_SUCCESS_SIGNALS,
        FactKey.SKILLS_ITEMS,
        FactKey.SKILLS_READINESS_TIMING,
        FactKey.SKILLS_FREE_TEXT_REASON,
        FactKey.SKILLS_KNOCKOUT_CRITERIA,
        FactKey.SKILLS_TRAINABLE_SKILLS,
        FactKey.TIMELINE_START_FLEXIBILITY,
    }
)
BEFORE_SUMMARY_REQUIRED_FACT_KEYS: Final[frozenset[FactKey]] = (
    SALARY_DRIVER_FACT_KEYS
    | frozenset(
        {
            FactKey.INTAKE_SEARCH_CONFIDENTIALITY,
            FactKey.ROLE_EMPLOYMENT_TYPE,
            FactKey.ROLE_CONTRACT_TYPE,
            FactKey.ROLE_TRAVEL_REQUIRED,
            FactKey.ROLE_ON_CALL,
            FactKey.BENEFITS_VARIABLE_PAY,
            FactKey.COMPANY_COMPLIANCE_CONTEXT,
            FactKey.LEGAL_WORK_AUTHORIZATION_SUPPORT,
            FactKey.INTERVIEW_START_DATE,
            FactKey.INTERVIEW_APPLICATION_DEADLINE,
        }
    )
)
BEFORE_ARTIFACT_REQUIRED_FACT_KEYS: Final[frozenset[FactKey]] = frozenset(
    {
        FactKey.BENEFITS_OFFER_COMPONENTS,
        FactKey.INTERVIEW_ASSESSMENT_EVIDENCE,
        FactKey.INTERVIEW_STAGE_OWNERS,
        FactKey.INTERVIEW_COMMUNICATION_SLA,
        FactKey.INTERVIEW_SCORECARD_TEMPLATE,
        FactKey.INTERVIEW_CORE_QUESTIONS,
        FactKey.INTERVIEW_COMPLIANCE_NOTES,
    }
)
WEBSITE_ENRICHABLE_FACT_KEYS: Final[frozenset[FactKey]] = frozenset(
    {
        FactKey.COMPANY_COMPANY_NAME,
        FactKey.COMPANY_COMPANY_WEBSITE,
        FactKey.COMPANY_LOCATION_CITY,
        FactKey.COMPANY_LOCATION_COUNTRY,
        FactKey.COMPANY_WORK_ARRANGEMENT,
        FactKey.COMPANY_OFFICE_DAYS_PER_WEEK,
        FactKey.COMPANY_ALLOWED_REGIONS_TIMEZONES,
        FactKey.COMPANY_EMPLOYER_PITCH,
        FactKey.COMPANY_ROLE_RELEVANT_POSITIONING,
        FactKey.COMPANY_LANGUAGE_INTERNAL,
        FactKey.COMPANY_COMPLIANCE_CONTEXT,
        FactKey.ROLE_TECH_STACK,
        FactKey.ROLE_DOMAIN_EXPERTISE,
        FactKey.BENEFITS_BENEFITS,
    }
)


def _intake_fact(
    fact_key: FactKey,
    label: str,
    step_key: str,
    value_type: FactValueType,
    *,
    salary_impact: FactSalaryImpact | None = None,
    requirement_stage: FactRequirementStage | None = None,
    website_enrichable: bool | None = None,
) -> IntakeFactDef:
    if salary_impact is None:
        if fact_key in SALARY_DRIVER_FACT_KEYS:
            salary_impact = FactSalaryImpact.P50_DIRECT
        elif fact_key in SALARY_QUALITY_DRIVER_FACT_KEYS:
            salary_impact = FactSalaryImpact.QUALITY_INDIRECT
        else:
            salary_impact = FactSalaryImpact.NONE
    if requirement_stage is None:
        if fact_key in BEFORE_SUMMARY_REQUIRED_FACT_KEYS:
            requirement_stage = FactRequirementStage.BEFORE_SUMMARY
        elif fact_key in BEFORE_ARTIFACT_REQUIRED_FACT_KEYS:
            requirement_stage = FactRequirementStage.BEFORE_ARTIFACT
        else:
            requirement_stage = FactRequirementStage.OPTIONAL
    if website_enrichable is None:
        website_enrichable = fact_key in WEBSITE_ENRICHABLE_FACT_KEYS
    return IntakeFactDef(
        fact_key=fact_key,
        label=label,
        step_key=step_key,
        value_type=value_type,
        persistence_intent=_FACT_PERSISTENCE_LEGACY_COMPATIBLE,
        salary_impact=salary_impact,
        requirement_stage=requirement_stage,
        website_enrichable=website_enrichable,
    )


# FACT_REGISTRY: canonical intake fact definitions used by runtime write-through.
INTAKE_FACTS: Final[tuple[IntakeFactDef, ...]] = (
    _intake_fact(
        FactKey.INTAKE_HIRING_REASON,
        "Hiring reason",
        STEP_KEY_LANDING,
        FactValueType.STRING,
    ),
    _intake_fact(
        FactKey.INTAKE_URGENCY,
        "Hiring urgency",
        STEP_KEY_LANDING,
        FactValueType.STRING,
    ),
    _intake_fact(
        FactKey.INTAKE_HIRING_VOLUME,
        "Hiring volume",
        STEP_KEY_LANDING,
        FactValueType.INTEGER,
    ),
    _intake_fact(
        FactKey.INTAKE_SEARCH_CONFIDENTIALITY,
        "Search confidentiality",
        STEP_KEY_LANDING,
        FactValueType.STRING,
    ),
    _intake_fact(
        FactKey.INTAKE_ROLE_DEFINITION_MATURITY,
        "Role definition maturity",
        STEP_KEY_LANDING,
        FactValueType.STRING,
    ),
    _intake_fact(
        FactKey.COMPANY_LANGUAGE_GUESS,
        "Detected language",
        STEP_KEY_COMPANY,
        FactValueType.STRING,
    ),
    _intake_fact(
        FactKey.COMPANY_COMPANY_NAME,
        "Company name",
        STEP_KEY_COMPANY,
        FactValueType.STRING,
    ),
    _intake_fact(
        FactKey.COMPANY_BRAND_NAME,
        "Brand name",
        STEP_KEY_COMPANY,
        FactValueType.STRING,
    ),
    _intake_fact(
        FactKey.COMPANY_COMPANY_WEBSITE,
        "Company website",
        STEP_KEY_COMPANY,
        FactValueType.STRING,
    ),
    _intake_fact(
        FactKey.COMPANY_LOCATION_CITY,
        "Location city",
        STEP_KEY_COMPANY,
        FactValueType.STRING,
    ),
    _intake_fact(
        FactKey.COMPANY_LOCATION_COUNTRY,
        "Location country",
        STEP_KEY_COMPANY,
        FactValueType.STRING,
    ),
    _intake_fact(
        FactKey.COMPANY_PLACE_OF_WORK,
        "Place of work",
        STEP_KEY_COMPANY,
        FactValueType.STRING,
    ),
    _intake_fact(
        FactKey.COMPANY_REMOTE_POLICY,
        "Remote policy",
        STEP_KEY_COMPANY,
        FactValueType.STRING,
    ),
    _intake_fact(
        FactKey.COMPANY_WORK_ARRANGEMENT,
        "Work arrangement",
        STEP_KEY_COMPANY,
        FactValueType.STRING,
    ),
    _intake_fact(
        FactKey.COMPANY_OFFICE_DAYS_PER_WEEK,
        "Office days per week",
        STEP_KEY_COMPANY,
        FactValueType.INTEGER,
    ),
    _intake_fact(
        FactKey.COMPANY_ALLOWED_REGIONS_TIMEZONES,
        "Allowed regions and timezones",
        STEP_KEY_COMPANY,
        FactValueType.STRING_LIST,
    ),
    _intake_fact(
        FactKey.COMPANY_EMPLOYER_PITCH,
        "Employer pitch",
        STEP_KEY_COMPANY,
        FactValueType.STRING,
    ),
    _intake_fact(
        FactKey.COMPANY_ROLE_RELEVANT_POSITIONING,
        "Role-relevant positioning",
        STEP_KEY_COMPANY,
        FactValueType.STRING_LIST,
    ),
    _intake_fact(
        FactKey.COMPANY_BUSINESS_UNIT,
        "Business unit",
        STEP_KEY_COMPANY,
        FactValueType.STRING,
    ),
    _intake_fact(
        FactKey.COMPANY_HIRING_REASON,
        "Company hiring reason",
        STEP_KEY_COMPANY,
        FactValueType.STRING,
    ),
    _intake_fact(
        FactKey.COMPANY_GROWTH_CONTEXT,
        "Company growth context",
        STEP_KEY_COMPANY,
        FactValueType.STRING,
    ),
    _intake_fact(
        FactKey.COMPANY_ROLE_BUSINESS_IMPACT,
        "Role business impact",
        STEP_KEY_COMPANY,
        FactValueType.STRING,
    ),
    _intake_fact(
        FactKey.COMPANY_LANGUAGE_INTERNAL,
        "Internal working language",
        STEP_KEY_COMPANY,
        FactValueType.OBJECT,
    ),
    _intake_fact(
        FactKey.COMPANY_LANGUAGE_EXTERNAL,
        "External communication language",
        STEP_KEY_COMPANY,
        FactValueType.OBJECT,
    ),
    _intake_fact(
        FactKey.COMPANY_NON_NEGOTIABLES,
        "Non-negotiables",
        STEP_KEY_COMPANY,
        FactValueType.STRING_LIST,
    ),
    _intake_fact(
        FactKey.COMPANY_COMPLIANCE_CONTEXT,
        "Compliance context",
        STEP_KEY_COMPANY,
        FactValueType.STRING_LIST,
    ),
    _intake_fact(
        FactKey.COMPANY_TARIFF_CONTEXT,
        "Tariff context",
        STEP_KEY_COMPANY,
        FactValueType.STRING,
    ),
    _intake_fact(
        FactKey.COMPANY_DEPARTMENT_NAME,
        "Department name",
        STEP_KEY_COMPANY,
        FactValueType.STRING,
    ),
    _intake_fact(
        FactKey.COMPANY_REPORTS_TO,
        "Reports to",
        STEP_KEY_COMPANY,
        FactValueType.STRING,
    ),
    _intake_fact(
        FactKey.COMPANY_DIRECT_REPORTS_COUNT,
        "Direct reports count",
        STEP_KEY_COMPANY,
        FactValueType.INTEGER,
    ),
    _intake_fact(
        FactKey.TEAM_NAME,
        "Team name",
        STEP_KEY_COMPANY,
        FactValueType.STRING,
    ),
    _intake_fact(
        FactKey.TEAM_LEADERSHIP_SCOPE,
        "Leadership scope",
        STEP_KEY_COMPANY,
        FactValueType.STRING,
    ),
    _intake_fact(
        FactKey.TEAM_SIZE_DIRECT,
        "Direct team size",
        STEP_KEY_COMPANY,
        FactValueType.INTEGER,
    ),
    _intake_fact(
        FactKey.TEAM_STAKEHOLDERS_PRIMARY,
        "Primary stakeholders",
        STEP_KEY_COMPANY,
        FactValueType.STRING_LIST,
    ),
    _intake_fact(
        FactKey.TEAM_SUCCESS_CONTEXT_90D,
        "90-day team success context",
        STEP_KEY_COMPANY,
        FactValueType.STRING,
    ),
    _intake_fact(
        FactKey.ROLE_JOB_TITLE,
        "Job title",
        STEP_KEY_ROLE_TASKS,
        FactValueType.STRING,
    ),
    _intake_fact(
        FactKey.ROLE_EMPLOYMENT_TYPE,
        "Employment type",
        STEP_KEY_ROLE_TASKS,
        FactValueType.STRING,
    ),
    _intake_fact(
        FactKey.ROLE_CONTRACT_TYPE,
        "Contract type",
        STEP_KEY_ROLE_TASKS,
        FactValueType.STRING,
    ),
    _intake_fact(
        FactKey.ROLE_SENIORITY_LEVEL,
        "Seniority level",
        STEP_KEY_ROLE_TASKS,
        FactValueType.STRING,
    ),
    _intake_fact(
        FactKey.ROLE_JOB_REF_NUMBER,
        "Job reference number",
        STEP_KEY_ROLE_TASKS,
        FactValueType.STRING,
    ),
    _intake_fact(
        FactKey.ROLE_ROLE_OVERVIEW,
        "Role overview",
        STEP_KEY_ROLE_TASKS,
        FactValueType.STRING,
    ),
    _intake_fact(
        FactKey.ROLE_RESPONSIBILITIES,
        "Responsibilities",
        STEP_KEY_ROLE_TASKS,
        FactValueType.STRING_LIST,
    ),
    _intake_fact(
        FactKey.ROLE_RESPONSIBILITIES_PRIORITIZED,
        "Prioritized responsibilities",
        STEP_KEY_ROLE_TASKS,
        FactValueType.OBJECT_LIST,
    ),
    _intake_fact(
        FactKey.ROLE_DELIVERABLES,
        "Deliverables",
        STEP_KEY_ROLE_TASKS,
        FactValueType.STRING_LIST,
    ),
    _intake_fact(
        FactKey.ROLE_SUCCESS_METRICS,
        "Success metrics",
        STEP_KEY_ROLE_TASKS,
        FactValueType.STRING_LIST,
    ),
    _intake_fact(
        FactKey.ROLE_SUCCESS_METRICS_TIMELINE,
        "Success metrics timeline",
        STEP_KEY_ROLE_TASKS,
        FactValueType.OBJECT,
    ),
    _intake_fact(
        FactKey.ROLE_BUSINESS_OUTCOME_PRIMARY,
        "Primary business outcome",
        STEP_KEY_ROLE_TASKS,
        FactValueType.STRING,
    ),
    _intake_fact(
        FactKey.ROLE_DAY1_RESPONSIBILITIES,
        "Day-1 responsibilities",
        STEP_KEY_ROLE_TASKS,
        FactValueType.STRING_LIST,
    ),
    _intake_fact(
        FactKey.ROLE_EXPANSION_SCOPE,
        "Expansion scope",
        STEP_KEY_ROLE_TASKS,
        FactValueType.STRING_LIST,
    ),
    _intake_fact(
        FactKey.ROLE_DECISION_SCOPE,
        "Decision scope",
        STEP_KEY_ROLE_TASKS,
        FactValueType.STRING,
    ),
    _intake_fact(
        FactKey.ROLE_YEAR1_SUCCESS_SIGNALS,
        "Year-1 success signals",
        STEP_KEY_ROLE_TASKS,
        FactValueType.STRING,
    ),
    _intake_fact(
        FactKey.ROLE_TECH_STACK,
        "Tech stack",
        STEP_KEY_ROLE_TASKS,
        FactValueType.STRING_LIST,
    ),
    _intake_fact(
        FactKey.ROLE_DOMAIN_EXPERTISE,
        "Domain expertise",
        STEP_KEY_ROLE_TASKS,
        FactValueType.STRING_LIST,
    ),
    _intake_fact(
        FactKey.ROLE_TRAVEL_REQUIRED,
        "Travel required",
        STEP_KEY_ROLE_TASKS,
        FactValueType.BOOLEAN,
    ),
    _intake_fact(
        FactKey.ROLE_TRAVEL_PROFILE,
        "Travel profile",
        STEP_KEY_BENEFITS,
        FactValueType.OBJECT,
    ),
    _intake_fact(
        FactKey.ROLE_ON_CALL,
        "On-call requirement",
        STEP_KEY_ROLE_TASKS,
        FactValueType.BOOLEAN,
    ),
    _intake_fact(
        FactKey.ROLE_ONBOARDING_NOTES,
        "Onboarding notes",
        STEP_KEY_ROLE_TASKS,
        FactValueType.STRING,
    ),
    _intake_fact(
        FactKey.ROLE_GAPS,
        "Extraction gaps",
        STEP_KEY_ROLE_TASKS,
        FactValueType.STRING_LIST,
    ),
    _intake_fact(
        FactKey.ROLE_ASSUMPTIONS,
        "Extraction assumptions",
        STEP_KEY_ROLE_TASKS,
        FactValueType.STRING_LIST,
    ),
    _intake_fact(
        FactKey.SKILLS_ITEMS,
        "Structured skill items",
        STEP_KEY_SKILLS,
        FactValueType.OBJECT_LIST,
    ),
    _intake_fact(
        FactKey.SKILLS_MUST_HAVE_SKILLS,
        "Must-have skills",
        STEP_KEY_SKILLS,
        FactValueType.STRING_LIST,
    ),
    _intake_fact(
        FactKey.SKILLS_NICE_TO_HAVE_SKILLS,
        "Nice-to-have skills",
        STEP_KEY_SKILLS,
        FactValueType.STRING_LIST,
    ),
    _intake_fact(
        FactKey.SKILLS_SOFT_SKILLS,
        "Soft skills",
        STEP_KEY_SKILLS,
        FactValueType.STRING_LIST,
    ),
    _intake_fact(
        FactKey.SKILLS_EDUCATION,
        "Education",
        STEP_KEY_SKILLS,
        FactValueType.STRING_LIST,
    ),
    _intake_fact(
        FactKey.SKILLS_CERTIFICATIONS,
        "Certifications",
        STEP_KEY_SKILLS,
        FactValueType.STRING_LIST,
    ),
    _intake_fact(
        FactKey.SKILLS_LANGUAGES,
        "Languages",
        STEP_KEY_SKILLS,
        FactValueType.STRING_LIST,
    ),
    _intake_fact(
        FactKey.SKILLS_READINESS_TIMING,
        "Skill readiness timing",
        STEP_KEY_SKILLS,
        FactValueType.OBJECT_LIST,
    ),
    _intake_fact(
        FactKey.SKILLS_FREE_TEXT_REASON,
        "Free-text skill retention reason",
        STEP_KEY_SKILLS,
        FactValueType.STRING,
    ),
    _intake_fact(
        FactKey.SKILLS_KNOCKOUT_CRITERIA,
        "Knockout criteria",
        STEP_KEY_SKILLS,
        FactValueType.STRING_LIST,
    ),
    _intake_fact(
        FactKey.SKILLS_TRAINABLE_SKILLS,
        "Trainable skills",
        STEP_KEY_SKILLS,
        FactValueType.STRING_LIST,
    ),
    _intake_fact(
        FactKey.BENEFITS_SALARY_RANGE,
        "Salary range",
        STEP_KEY_BENEFITS,
        FactValueType.MONEY_RANGE,
    ),
    _intake_fact(
        FactKey.BENEFITS_VARIABLE_PAY,
        "Variable pay",
        STEP_KEY_BENEFITS,
        FactValueType.OBJECT,
    ),
    _intake_fact(
        FactKey.BENEFITS_BENEFITS,
        "Benefits",
        STEP_KEY_BENEFITS,
        FactValueType.STRING_LIST,
    ),
    _intake_fact(
        FactKey.BENEFITS_SHIFT_COMPENSATION,
        "Shift compensation",
        STEP_KEY_BENEFITS,
        FactValueType.OBJECT,
    ),
    _intake_fact(
        FactKey.BENEFITS_COLLECTIVE_AGREEMENT_CONTEXT,
        "Collective agreement context",
        STEP_KEY_BENEFITS,
        FactValueType.STRING_LIST,
    ),
    _intake_fact(
        FactKey.BENEFITS_OFFER_COMPONENTS,
        "Offer components",
        STEP_KEY_BENEFITS,
        FactValueType.STRING_LIST,
    ),
    _intake_fact(
        FactKey.LEGAL_WORK_AUTHORIZATION_SUPPORT,
        "Work authorization support",
        STEP_KEY_BENEFITS,
        FactValueType.STRING,
    ),
    _intake_fact(
        FactKey.TIMELINE_START_FLEXIBILITY,
        "Start flexibility",
        STEP_KEY_BENEFITS,
        FactValueType.OBJECT,
    ),
    _intake_fact(
        FactKey.INTERVIEW_START_DATE,
        "Start date",
        STEP_KEY_INTERVIEW,
        FactValueType.DATE_STRING,
    ),
    _intake_fact(
        FactKey.INTERVIEW_APPLICATION_DEADLINE,
        "Application deadline",
        STEP_KEY_INTERVIEW,
        FactValueType.DATE_STRING,
    ),
    _intake_fact(
        FactKey.INTERVIEW_RECRUITMENT_STEPS,
        "Recruitment steps",
        STEP_KEY_INTERVIEW,
        FactValueType.OBJECT_LIST,
    ),
    _intake_fact(
        FactKey.INTERVIEW_CONTACTS,
        "Contacts",
        STEP_KEY_INTERVIEW,
        FactValueType.OBJECT_LIST,
    ),
    _intake_fact(
        FactKey.INTERVIEW_ASSESSMENT_EVIDENCE,
        "Assessment evidence",
        STEP_KEY_INTERVIEW,
        FactValueType.OBJECT_LIST,
    ),
    _intake_fact(
        FactKey.INTERVIEW_STAGE_OWNERS,
        "Stage owners",
        STEP_KEY_INTERVIEW,
        FactValueType.OBJECT_LIST,
    ),
    _intake_fact(
        FactKey.INTERVIEW_COMMUNICATION_SLA,
        "Candidate communication SLA",
        STEP_KEY_INTERVIEW,
        FactValueType.OBJECT_LIST,
    ),
    _intake_fact(
        FactKey.INTERVIEW_SCORECARD_TEMPLATE,
        "Scorecard template",
        STEP_KEY_INTERVIEW,
        FactValueType.OBJECT,
    ),
    _intake_fact(
        FactKey.INTERVIEW_CORE_QUESTIONS,
        "Core interview questions",
        STEP_KEY_INTERVIEW,
        FactValueType.STRING_LIST,
    ),
    _intake_fact(
        FactKey.INTERVIEW_COMPLIANCE_NOTES,
        "Interview compliance notes",
        STEP_KEY_INTERVIEW,
        FactValueType.STRING,
    ),
)


QUESTION_SCHEMA_VERSION: Final[str] = "2026-06-19"
VACANCY_SCHEMA_VERSION: Final[str] = "2026-04-14"
JOB_AD_SCHEMA_VERSION: Final[str] = "2026-06-10"
OCCUPATION_CONTEXT_SCHEMA_VERSION: Final[str] = "2026-06-03"
OCCUPATION_QUESTION_CONTEXT_SCHEMA_VERSION: Final[str] = "2026-06-11"
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

# ---- Company website research canonical keys ----
WEBSITE_TOPIC_ABOUT: Final[str] = "about"
WEBSITE_TOPIC_IMPRINT: Final[str] = "imprint"
WEBSITE_TOPIC_VISION_MISSION: Final[str] = "vision_mission"

WEBSITE_RESEARCH_HOMEPAGE_URL: Final[str] = "homepage_url"
WEBSITE_RESEARCH_SECTIONS: Final[str] = "sections"
WEBSITE_RESEARCH_OPEN_QUESTION_MATCHES: Final[str] = "open_question_matches"

WEBSITE_SECTION_SOURCE_URL: Final[str] = "source_url"
WEBSITE_SECTION_SUMMARY: Final[str] = "summary"
WEBSITE_SECTION_FACTS: Final[str] = "facts"
WEBSITE_SECTION_FETCHED_AT: Final[str] = "fetched_at"

STALE_REDESIGN_SESSION_KEY_PREFIXES: Final[tuple[str, ...]] = (
    "cs.redesign.",
    "cs.summary.redesign.",
)

# Prefix used to generate stable Streamlit widget keys per question
WIDGET_KEY_PREFIX: Final[str] = "cs.q::"
