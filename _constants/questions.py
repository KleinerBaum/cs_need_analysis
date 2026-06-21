"""Question and jobspec routing constants."""

from __future__ import annotations

from enum import Enum
from typing import Final

from _constants.wizard import (
    STEP_KEY_BENEFITS,
    STEP_KEY_COMPANY,
    STEP_KEY_INTERVIEW,
    STEP_KEY_ROLE_TASKS,
    STEP_KEY_SKILLS,
)


QUESTION_LIMIT_SCOPE_META_KEY: Final[str] = "__scope__"

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

# ---- Question types ----
class AnswerType(str, Enum):
    SHORT_TEXT = "short_text"
    LONG_TEXT = "long_text"
    SINGLE_SELECT = "single_select"
    MULTI_SELECT = "multi_select"
    NUMBER = "number"
    BOOLEAN = "boolean"
    DATE = "date"
