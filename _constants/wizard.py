"""Wizard step and navigation constants."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final, List


WIZARD_STEP_QUERY_PARAM: Final[str] = "wizard_step"

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
STEP_KEY_INTRO: Final[str] = "intro"
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

# ---- Canonical Route Groups ----
PRE_WIZARD_STEP_KEYS: Final[tuple[str, ...]] = (STEP_KEY_INTRO,)
OPERATIONAL_WIZARD_STEP_KEYS: Final[tuple[str, ...]] = (
    STEP_KEY_LANDING,
    STEP_KEY_COMPANY,
    STEP_KEY_ROLE_TASKS,
    STEP_KEY_SKILLS,
    STEP_KEY_BENEFITS,
    STEP_KEY_INTERVIEW,
    STEP_KEY_SUMMARY,
)
PROGRESS_STEP_KEYS: Final[tuple[str, ...]] = OPERATIONAL_WIZARD_STEP_KEYS

# Plan/System steps that are intentionally excluded from intake completion/facts views.
NON_INTAKE_STEP_KEYS: Final[tuple[str, ...]] = (
    STEP_KEY_INTRO,
    STEP_KEY_LANDING,
    STEP_KEY_SUMMARY,
)

# ---- Wizard Steps (canonical routable page contract) ----
@dataclass(frozen=True)
class WizardStepDef:
    key: str
    title_de: str
    icon: str


STEPS: Final[List[WizardStepDef]] = [
    WizardStepDef(key=STEP_KEY_INTRO, title_de="Einleitung", icon="ℹ️"),
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
