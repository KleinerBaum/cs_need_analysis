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

    BRIEF = "cs.brief"
    LAST_ERROR = "cs.last_error"
    DEBUG = "cs.debug"
    CONTENT_SHARING_CONSENT = "cs.content_sharing_consent"
    LLM_RESPONSE_CACHE = "cs.llm_response_cache"
    JOBAD_CACHE_HIT = "cs.jobad_cache_hit"
    SUMMARY_CACHE_HIT = "cs.summary_cache_hit"
    SUMMARY_LAST_MODE = "cs.summary_last_mode"
    SUMMARY_LAST_MODELS = "cs.summary_last_models"
    OPENAI_LAST_STRUCTURED_OUTPUT_PATH = "cs.openai_last_structured_output_path"
    SUMMARY_SELECTIONS = "cs.summary_selections"
    JOB_AD_DRAFT_CUSTOM = "cs.job_ad_draft_custom"
    JOB_AD_LAST_USAGE = "cs.job_ad_last_usage"


# ---- Wizard Steps (match your screenshot structure) ----
@dataclass(frozen=True)
class WizardStepDef:
    key: str
    title_de: str
    icon: str


STEPS: Final[List[WizardStepDef]] = [
    WizardStepDef(key="landing", title_de="Start", icon="🏁"),
    WizardStepDef(key="jobad", title_de="Jobspec / Jobad", icon="📄"),
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


QUESTION_SCHEMA_VERSION: Final[str] = "2026-04-07"
VACANCY_SCHEMA_VERSION: Final[str] = "2026-04-07"

# Prefix used to generate stable Streamlit widget keys per question
WIDGET_KEY_PREFIX: Final[str] = "cs.q::"
