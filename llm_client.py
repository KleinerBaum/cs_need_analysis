# llm_client.py
"""OpenAI API wrapper for this app.

Uses Structured Outputs via the OpenAI Python SDK `.responses.parse(...)` when available.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import time
from dataclasses import dataclass
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Mapping,
    Optional,
    Protocol,
    Sequence,
    Tuple,
    Type,
    cast,
)

import streamlit as st
from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    OpenAI,
)
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from constants import (
    AnswerType,
    DEFAULT_LANGUAGE,
    FactKey,
    JOB_AD_SCHEMA_VERSION,
    QUESTION_IMPACT_TARGETS,
    QUESTION_SCHEMA_VERSION,
    SSKey,
    STEP_KEY_BENEFITS,
    STEP_KEY_COMPANY,
    STEP_KEY_INTERVIEW,
    STEP_KEY_ROLE_TASKS,
    STEP_KEY_SKILLS,
    VACANCY_SCHEMA_VERSION,
)
from model_capabilities import (
    is_gpt54_family,
    is_gpt5_legacy_model,
    is_nano_model,
    normalize_reasoning_effort,
    supports_reasoning,
    supports_temperature,
    supports_verbosity,
)
from schemas import (
    BenefitSuggestionPack,
    BooleanSearchPack,
    EmploymentContractDraft,
    InterviewPrepSheetHR,
    InterviewPrepSheetHiringManager,
    JobAdExtract,
    QuestionDependency,
    QuestionPlan,
    RequirementSuggestionPack,
    RoleTaskSalaryForecast,
    CompanyWebsiteResearch,
    VacancyBrief,
    VacancyBriefLLM,
    VacancyStructuredData,
)
from settings_openai import OpenAISettings, load_openai_settings
from usage_events import record_fallback_model_used

logger = logging.getLogger(__name__)

# Re-exported for backwards-compatible imports and lightweight diagnostics.
_MODEL_CAPABILITY_EXPORTS = (
    is_gpt5_legacy_model,
    is_gpt54_family,
    is_nano_model,
    supports_reasoning,
    supports_verbosity,
)


ModelTaskKind = str
TASK_EXTRACT_JOB_AD = "extract_job_ad"
TASK_GENERATE_QUESTION_PLAN = "generate_question_plan"
TASK_GENERATE_VACANCY_BRIEF = "generate_vacancy_brief"
TASK_GENERATE_JOB_AD = "generate_job_ad"
TASK_GENERATE_INTERVIEW_SHEET_HR = "generate_interview_sheet_hr"
TASK_GENERATE_INTERVIEW_SHEET_HM = "generate_interview_sheet_hm"
TASK_GENERATE_BOOLEAN_SEARCH = "generate_boolean_search"
TASK_GENERATE_EMPLOYMENT_CONTRACT = "generate_employment_contract"
TASK_GENERATE_REQUIREMENT_GAP_SUGGESTIONS = "generate_requirement_gap_suggestions"
TASK_GENERATE_BENEFIT_SUGGESTIONS = "generate_benefit_suggestions"
TASK_GENERATE_ROLE_TASKS_SALARY_FORECAST = "generate_role_tasks_salary_forecast"

_CANONICAL_QUESTION_GROUPS_BY_STEP: dict[str, tuple[str, ...]] = {
    STEP_KEY_COMPANY: (
        "employer_narrative",
        "business_context",
        "organization_team",
        "work_model_location",
        "risks_non_negotiables",
    ),
    STEP_KEY_ROLE_TASKS: (
        "role_purpose",
        "top_deliverables",
        "ownership_scope",
        "stakeholders_collaboration",
        "success_30_90_180",
    ),
    STEP_KEY_SKILLS: (
        "must_have",
        "nice_to_have",
        "proficiency_depth",
        "application_context",
        "substitutability",
    ),
    STEP_KEY_BENEFITS: (
        "compensation",
        "work_model",
        "contract_start",
        "differentiating_benefits",
        "dealbreakers",
    ),
    STEP_KEY_INTERVIEW: (
        "candidate_journey",
        "stage_goals",
        "evaluation_evidence",
        "internal_responsibilities",
        "slas_communication",
    ),
}

_QUESTION_GROUP_FALLBACK_BY_STEP: dict[str, str] = {
    STEP_KEY_COMPANY: "business_context",
    STEP_KEY_ROLE_TASKS: "role_purpose",
    STEP_KEY_SKILLS: "application_context",
    STEP_KEY_BENEFITS: "differentiating_benefits",
    STEP_KEY_INTERVIEW: "candidate_journey",
}

_QUESTION_GROUP_MATCH_RULES: dict[str, tuple[tuple[str, tuple[str, ...]], ...]] = {
    STEP_KEY_COMPANY: (
        (
            "employer_narrative",
            ("employer", "arbeitgeber", "pitch", "narrative", "mission", "vision", "brand", "marke", "positionierung"),
        ),
        (
            "business_context",
            ("business", "geschaeft", "geschäft", "unit", "bereich", "markt", "produkt", "kunden", "warum", "purpose"),
        ),
        (
            "organization_team",
            ("team", "report", "stakeholder", "organisation", "organization", "fuehrung", "führung", "leadership", "zusammenarbeit"),
        ),
        (
            "work_model_location",
            ("remote", "hybrid", "standort", "location", "arbeitsort", "office", "timezone", "zeitzone", "region", "sprache"),
        ),
        (
            "risks_non_negotiables",
            ("risk", "risiko", "non negotiable", "non_negotiable", "pflicht", "compliance", "vorgabe", "tarif", "betriebsrat"),
        ),
    ),
    STEP_KEY_ROLE_TASKS: (
        (
            "role_purpose",
            ("purpose", "zweck", "ziel", "warum", "mission", "rolle", "overview", "kontext"),
        ),
        (
            "top_deliverables",
            ("deliverable", "aufgabe", "responsibil", "priorit", "top", "output", "ergebnis"),
        ),
        (
            "ownership_scope",
            ("ownership", "entscheidung", "scope", "verantwort", "befugnis", "autonomie", "budget"),
        ),
        (
            "stakeholders_collaboration",
            ("stakeholder", "schnittstelle", "zusammenarbeit", "collaboration", "kunden", "partner", "team"),
        ),
        (
            "success_30_90_180",
            ("30", "90", "180", "success", "erfolg", "metric", "kpi", "onboarding", "probezeit"),
        ),
    ),
    STEP_KEY_SKILLS: (
        (
            "must_have",
            ("must", "required", "pflicht", "knockout", "zwingend", "essential", "muss"),
        ),
        (
            "nice_to_have",
            ("nice", "optional", "wuensch", "wünsch", "plus", "bonus"),
        ),
        (
            "proficiency_depth",
            ("level", "niveau", "tiefe", "senior", "expert", "erfahrung", "proficiency", "kenntnis"),
        ),
        (
            "application_context",
            ("context", "anwendung", "tool", "stack", "praxis", "umgebung", "skill_group", "esco", "knowledge", "digital", "data"),
        ),
        (
            "substitutability",
            ("substitut", "train", "lern", "ersetz", "alternative", "kompens", "entwickelbar"),
        ),
    ),
    STEP_KEY_BENEFITS: (
        (
            "compensation",
            ("salary", "gehalt", "compensation", "bonus", "variable", "budget", "range", "vergütung", "verguetung"),
        ),
        (
            "work_model",
            ("remote", "hybrid", "office", "arbeitsmodell", "arbeitszeit", "zeit", "flex"),
        ),
        (
            "contract_start",
            ("contract", "vertrag", "start", "deadline", "frist", "befrist", "notice", "kuendig", "kündig"),
        ),
        (
            "differentiating_benefits",
            ("benefit", "perk", "angebot", "argument", "differenz", "mobil", "weiterbildung", "urlaub"),
        ),
        (
            "dealbreakers",
            ("dealbreaker", "einschraenk", "einschränk", "fix", "non negotiable", "grenze", "constraint"),
        ),
    ),
    STEP_KEY_INTERVIEW: (
        (
            "evaluation_evidence",
            ("evidence", "bewertung", "score", "assessment", "case", "probe", "signal", "kriter"),
        ),
        (
            "slas_communication",
            ("sla", "feedback", "kommunikation", "communication", "antwort", "tage", "timing"),
        ),
        (
            "internal_responsibilities",
            ("owner", "verantwort", "entscheidung", "rolle", "intern", "hiring manager", "recruit"),
        ),
        (
            "stage_goals",
            ("stage", "stufe", "ziel", "goal", "interviewziel", "screening", "fachinterview"),
        ),
        (
            "candidate_journey",
            ("candidate", "kandidat", "journey", "prozess", "process", "schritt", "timeline", "runde"),
        ),
    ),
}

_OTHER_OPTION = "Sonstiges"
_CATEGORY_QUESTION_RULES: tuple[dict[str, Any], ...] = (
    {
        "terms": ("hard skills",),
        "answer_type": AnswerType.MULTI_SELECT,
        "options": (
            "Python",
            "Java",
            "SQL",
            "Cloud",
            "Datenanalyse",
            _OTHER_OPTION,
        ),
    },
    {
        "terms": ("soft skills",),
        "answer_type": AnswerType.MULTI_SELECT,
        "options": (
            "Kommunikation",
            "Teamfähigkeit",
            "Eigenverantwortung",
            "Stakeholder-Management",
            "Problemlösung",
            _OTHER_OPTION,
        ),
    },
    {
        "terms": ("sprachen",),
        "answer_type": AnswerType.MULTI_SELECT,
        "options": ("Deutsch", "Englisch", "Französisch", "Spanisch", _OTHER_OPTION),
    },
    {
        "terms": ("seniority",),
        "answer_type": AnswerType.SINGLE_SELECT,
        "options": ("Junior", "Mid-Level", "Senior", "Lead", _OTHER_OPTION),
    },
    {
        "terms": ("tools",),
        "answer_type": AnswerType.MULTI_SELECT,
        "options": ("Jira", "Confluence", "GitHub", "Salesforce", "SAP", _OTHER_OPTION),
    },
    {
        "terms": ("arbeitsmodell",),
        "answer_type": AnswerType.SINGLE_SELECT,
        "options": ("Vor Ort", "Hybrid", "Remote", _OTHER_OPTION),
    },
)

_NUMERIC_QUESTION_RULES: tuple[dict[str, Any], ...] = (
    {
        "terms": ("jahre", "years", "berufserfahrung", "experience"),
        "bounds": (0.0, 30.0, 1.0),
    },
    {
        "terms": ("anzahl", "number", "headcount", "fte", "teamgröße", "teamgroesse"),
        "bounds": (0.0, 500.0, 1.0),
    },
    {
        "terms": ("tage", "days", "pro woche", "per week"),
        "bounds": (0.0, 7.0, 1.0),
    },
    {
        "terms": ("prozent", "%", "percentage"),
        "bounds": (0.0, 100.0, 1.0),
    },
    {
        "terms": ("gehalt", "salary", "budget", "compensation"),
        "bounds": (20_000.0, 500_000.0, 1_000.0),
    },
)
_QUESTION_PRIORITY_VALUES = {"core", "standard", "detail"}
_QUESTION_IMPACT_TARGET_VALUES = set(QUESTION_IMPACT_TARGETS)
_QUESTION_FACT_KEY_BY_TARGET_PATH: dict[str, FactKey] = {
    "hiring_reason": FactKey.INTAKE_HIRING_REASON,
    "urgency": FactKey.INTAKE_URGENCY,
    "hiring_volume": FactKey.INTAKE_HIRING_VOLUME,
    "search_confidentiality": FactKey.INTAKE_SEARCH_CONFIDENTIALITY,
    "role_definition_maturity": FactKey.INTAKE_ROLE_DEFINITION_MATURITY,
    "company_name": FactKey.COMPANY_COMPANY_NAME,
    "company_website": FactKey.COMPANY_COMPANY_WEBSITE,
    "brand_name": FactKey.COMPANY_BRAND_NAME,
    "location_city": FactKey.COMPANY_LOCATION_CITY,
    "location_country": FactKey.COMPANY_LOCATION_COUNTRY,
    "place_of_work": FactKey.COMPANY_PLACE_OF_WORK,
    "remote_policy": FactKey.COMPANY_REMOTE_POLICY,
    "work_arrangement": FactKey.COMPANY_WORK_ARRANGEMENT,
    "office_days_per_week": FactKey.COMPANY_OFFICE_DAYS_PER_WEEK,
    "allowed_regions_timezones": FactKey.COMPANY_ALLOWED_REGIONS_TIMEZONES,
    "employer_pitch": FactKey.COMPANY_EMPLOYER_PITCH,
    "role_relevant_positioning": FactKey.COMPANY_ROLE_RELEVANT_POSITIONING,
    "business_unit": FactKey.COMPANY_BUSINESS_UNIT,
    "language_internal": FactKey.COMPANY_LANGUAGE_INTERNAL,
    "language_external": FactKey.COMPANY_LANGUAGE_EXTERNAL,
    "non_negotiables": FactKey.COMPANY_NON_NEGOTIABLES,
    "compliance_context": FactKey.COMPANY_COMPLIANCE_CONTEXT,
    "tariff_context": FactKey.COMPANY_TARIFF_CONTEXT,
    "leadership_scope": FactKey.TEAM_LEADERSHIP_SCOPE,
    "size_direct": FactKey.TEAM_SIZE_DIRECT,
    "stakeholders_primary": FactKey.TEAM_STAKEHOLDERS_PRIMARY,
    "success_context_90d": FactKey.TEAM_SUCCESS_CONTEXT_90D,
    "job_title": FactKey.ROLE_JOB_TITLE,
    "employment_type": FactKey.ROLE_EMPLOYMENT_TYPE,
    "contract_type": FactKey.ROLE_CONTRACT_TYPE,
    "seniority_level": FactKey.ROLE_SENIORITY_LEVEL,
    "role_overview": FactKey.ROLE_ROLE_OVERVIEW,
    "responsibilities": FactKey.ROLE_RESPONSIBILITIES,
    "responsibilities_prioritized": FactKey.ROLE_RESPONSIBILITIES_PRIORITIZED,
    "success_metrics": FactKey.ROLE_SUCCESS_METRICS,
    "success_metrics_timeline": FactKey.ROLE_SUCCESS_METRICS_TIMELINE,
    "business_outcome_primary": FactKey.ROLE_BUSINESS_OUTCOME_PRIMARY,
    "day1_responsibilities": FactKey.ROLE_DAY1_RESPONSIBILITIES,
    "expansion_scope": FactKey.ROLE_EXPANSION_SCOPE,
    "decision_scope": FactKey.ROLE_DECISION_SCOPE,
    "year1_success_signals": FactKey.ROLE_YEAR1_SUCCESS_SIGNALS,
    "must_have_skills": FactKey.SKILLS_MUST_HAVE_SKILLS,
    "nice_to_have_skills": FactKey.SKILLS_NICE_TO_HAVE_SKILLS,
    "languages": FactKey.SKILLS_LANGUAGES,
    "certifications": FactKey.SKILLS_CERTIFICATIONS,
    "readiness_timing": FactKey.SKILLS_READINESS_TIMING,
    "free_text_reason": FactKey.SKILLS_FREE_TEXT_REASON,
    "knockout_criteria": FactKey.SKILLS_KNOCKOUT_CRITERIA,
    "trainable_skills": FactKey.SKILLS_TRAINABLE_SKILLS,
    "salary_range": FactKey.BENEFITS_SALARY_RANGE,
    "variable_pay": FactKey.BENEFITS_VARIABLE_PAY,
    "benefits": FactKey.BENEFITS_BENEFITS,
    "shift_compensation": FactKey.BENEFITS_SHIFT_COMPENSATION,
    "collective_agreement_context": FactKey.BENEFITS_COLLECTIVE_AGREEMENT_CONTEXT,
    "offer_components": FactKey.BENEFITS_OFFER_COMPONENTS,
    "work_authorization_support": FactKey.LEGAL_WORK_AUTHORIZATION_SUPPORT,
    "start_flexibility": FactKey.TIMELINE_START_FLEXIBILITY,
    "recruitment_steps": FactKey.INTERVIEW_RECRUITMENT_STEPS,
    "contacts": FactKey.INTERVIEW_CONTACTS,
    "assessment_evidence": FactKey.INTERVIEW_ASSESSMENT_EVIDENCE,
    "stage_owners": FactKey.INTERVIEW_STAGE_OWNERS,
    "communication_sla": FactKey.INTERVIEW_COMMUNICATION_SLA,
    "scorecard_template": FactKey.INTERVIEW_SCORECARD_TEMPLATE,
    "core_questions": FactKey.INTERVIEW_CORE_QUESTIONS,
    "compliance_notes": FactKey.INTERVIEW_COMPLIANCE_NOTES,
}


class VacancyBriefCriticalSections(BaseModel):
    """Subset schema for optional quality upgrades on critical sections only."""

    model_config = ConfigDict(extra="forbid")

    evaluation_rubric: list[str]
    risks_open_questions: list[str]


class JobAdGenerationResult(BaseModel):
    """Strict schema for user-tailored job ad generation."""

    model_config = ConfigDict(extra="forbid")

    headline: str
    target_group: list[str]
    agg_checklist: list[str]
    job_ad_text: str
    intro: str = ""
    responsibilities: list[str] = Field(default_factory=list)
    profile: list[str] = Field(default_factory=list)
    offer: list[str] = Field(default_factory=list)
    cta: str = ""
    equal_opportunity_note: str = ""


@dataclass(frozen=True)
class OpenAIRuntimeConfig:
    """Resolved runtime configuration for a single LLM task call chain."""

    resolved_model: str
    reasoning_effort: str | None
    verbosity: str | None
    timeout_seconds: float
    task_max_output_tokens: int | None
    task_max_bullets_per_field: int | None
    task_max_sentences_per_field: int | None
    settings: OpenAISettings
    task_kind: ModelTaskKind | None = None


class ParsedResponse(Protocol):
    """Minimal protocol for Responses API parse return objects."""

    output_parsed: BaseModel
    usage: object | None


class _ParsedChatMessage(Protocol):
    parsed: BaseModel | None


class _ParsedChatChoice(Protocol):
    message: _ParsedChatMessage


class ParsedChatCompletion(Protocol):
    """Minimal protocol for chat.completions.parse return objects."""

    choices: Sequence[_ParsedChatChoice]
    usage: object | None


def _resolve_runtime_config(
    *,
    task_kind: ModelTaskKind,
    session_override: str | None,
) -> OpenAIRuntimeConfig:
    """Resolve model and OpenAI settings exactly once per task invocation."""

    settings = load_openai_settings()
    resolved_model = resolve_model_for_task(
        task_kind=task_kind,
        session_override=session_override,
        settings=settings,
    )
    return OpenAIRuntimeConfig(
        resolved_model=resolved_model,
        reasoning_effort=settings.reasoning_effort,
        verbosity=settings.verbosity,
        timeout_seconds=settings.openai_request_timeout,
        task_max_output_tokens=settings.task_max_output_tokens.get(task_kind),
        task_max_bullets_per_field=settings.task_max_bullets_per_field.get(task_kind),
        task_max_sentences_per_field=settings.task_max_sentences_per_field.get(
            task_kind
        ),
        settings=settings,
        task_kind=task_kind,
    )


def build_task_prompt_limits_suffix(
    *,
    max_bullets_per_field: int | None,
    max_sentences_per_field: int | None,
    max_output_tokens: int | None,
) -> str:
    """Build strict task-level prompt limits from runtime configuration."""

    parts: list[str] = []
    if max_bullets_per_field is not None:
        parts.append(f"Maximal {max_bullets_per_field} Bulletpoints pro Listenfeld.")
    if max_sentences_per_field is not None:
        parts.append(f"Maximal {max_sentences_per_field} Sätze pro Textfeld.")
    if max_output_tokens is not None:
        parts.append(
            "Bei knappem Budget priorisiere Pflichtfelder mit hoher Hiring-Relevanz; "
            "fülle Nice-to-have nur bei verbleibendem Budget."
        )
    if not parts:
        return ""
    return " Zusätzliche Output-Limits: " + " ".join(parts)


class OpenAICallError(RuntimeError):
    """Application-level error with user-facing and debug-safe details."""

    def __init__(
        self,
        ui_message: str,
        *,
        debug_detail: str | None = None,
        error_code: str | None = None,
    ) -> None:
        super().__init__(ui_message)
        self.ui_message = ui_message
        self.debug_detail = debug_detail
        self.error_code = error_code


_STRUCTURED_OUTPUT_RETRYABLE_ERROR_CODES = frozenset(
    {
        "OPENAI_BAD_REQUEST_STRUCTURED_OUTPUT_UNSUPPORTED",
        "OPENAI_BAD_REQUEST_MODEL_CAPABILITY",
        "OPENAI_BAD_REQUEST_ENDPOINT_INCOMPATIBLE",
    }
)


def build_extract_job_ad_messages(
    job_text: str,
    language: str = DEFAULT_LANGUAGE,
    model: str | None = None,
) -> list[dict[str, str]]:
    """Build the standardized message list for job-ad extraction."""

    guardrails = build_small_model_guardrails(model or "")
    system = (
        "Du bist ein Senior HR / Recruiting Analyst. "
        "Extrahiere aus einem Jobspec/Job Ad alle recruitment-relevanten Informationen "
        "und normalisiere sie in ein strukturiertes JSON, ohne Halluzinationen. "
        "Setze job_title auf die kandidatensichtbare Rollenbezeichnung aus Überschrift, "
        "Stellentitel oder eindeutigem Rollenlabel; nutze nicht den Arbeitgeber-, "
        "Abteilungs- oder Projektnamen als Jobtitel. "
        "Wenn etwas nicht explizit vorkommt oder nicht sicher ableitbar ist: setze null/leer und schreibe es in 'gaps'. "
        "Wenn du Annahmen triffst: dokumentiere sie in 'assumptions'. "
        "Erfinde keine Skills, Zertifikate, Success Metrics, Tools oder Prozessschritte; "
        "übernimm sie nur, wenn sie im Text genannt oder eindeutig formuliert sind. "
        "Fülle field_evidence[] für zentrale befüllte Felder mit field_name, confidence 0.0..1.0, "
        "kurzem evidence_snippet aus dem Originaltext und needs_confirmation=true bei indirekten, "
        "mehrdeutigen oder konfliktären Ableitungen. "
        "Speichere keine personenbezogenen Kontaktdaten als evidence_snippet; setze dort null, wenn kein datenschutzsicherer kurzer Beleg möglich ist. "
        f"Antworte in der Sprache: {language}."
        f"{guardrails}"
    )

    user = (
        "Analysiere folgenden Text (Jobspec/Job Ad). "
        "Priorität 1: finde den Jobtitel auch dann, wenn er in einer Headline, "
        "einem Linktitel oder einer tabellarischen Kopfzeile steht. "
        "Erkenne insbesondere die Arbeitgeber-Homepage (company_website), falls vorhanden. "
        "Mappe Abschnitte wie 'Was wir dir bieten', 'Benefits', 'Unser Angebot', "
        "'Das bieten wir' und 'Rahmenbedingungen' explizit nach benefits[]. "
        "Dazu gehören unter anderem Trainings, Mentoring, persönliche Entwicklung, "
        "Tools und GenAI-/Tech-Zugang, flexible Arbeitsmodelle, Corporate Benefits, "
        "Vielfalt/Arbeitsumfeld sowie Gestaltungsspielraum oder Thought Leadership. "
        "Behalte Formulierungen aus dem Original, wo sinnvoll. "
        "Priorisiere field_evidence für job_title, company_name, company_website, location_city, remote_policy, "
        "employment_type, contract_type, must_have_skills, nice_to_have_skills, salary_range, benefits und recruitment_steps.\n\n"
        "=== JOBSPEC START ===\n"
        f"{job_text}\n"
        "=== JOBSPEC END ==="
    )

    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


def build_small_model_guardrails(model: str) -> str:
    """Return minimal strict-output guardrails for selected nano models."""

    normalized_model = model.strip().lower()
    if normalized_model not in {"gpt-5-nano", "gpt-5.4-nano"}:
        return ""

    return (
        " Für kleine Modelle strikt befolgen: "
        "1) Nur strukturierte Ausgabe gemäß Schema. "
        "2) Kein Zusatztext außerhalb des Schemas. "
        "3) Keine impliziten Nebenaufgaben. "
        "4) Fehlende Infos leer/null statt geraten."
    )


def normalize_verbosity(verbosity: str | None) -> str | None:
    """Normalize verbosity values and drop unsupported inputs."""

    if verbosity is None:
        return None

    normalized_verbosity = verbosity.strip().lower()
    if normalized_verbosity in {"low", "medium", "high"}:
        return normalized_verbosity

    return None


def _build_capability_gated_request_kwargs(
    *,
    model: str,
    maybe_temperature: float | None = None,
    reasoning_effort: str | None,
    verbosity: str | None,
) -> dict[str, Any]:
    """Build capability-gated kwargs shared across parse endpoints."""

    normalized_reasoning_effort = normalize_reasoning_effort(model, reasoning_effort)
    normalized_verbosity = normalize_verbosity(verbosity)

    request_kwargs: dict[str, Any] = {}
    if maybe_temperature is not None and supports_temperature(
        model, normalized_reasoning_effort
    ):
        request_kwargs["temperature"] = maybe_temperature
    if supports_reasoning(model) and normalized_reasoning_effort is not None:
        request_kwargs["reasoning"] = {"effort": normalized_reasoning_effort}
    if supports_verbosity(model) and normalized_verbosity is not None:
        request_kwargs["text"] = {"verbosity": normalized_verbosity}

    return request_kwargs


def build_responses_request_kwargs(
    *,
    model: str,
    store: bool,
    maybe_temperature: float | None = None,
    reasoning_effort: str | None,
    verbosity: str | None,
    max_output_tokens: int | None = None,
) -> dict[str, Any]:
    """Build kwargs for `responses.parse` with endpoint-specific fields."""

    request_kwargs: dict[str, Any] = {"model": model, "store": store}
    if max_output_tokens is not None:
        request_kwargs["max_output_tokens"] = max_output_tokens
    request_kwargs.update(
        _build_capability_gated_request_kwargs(
            model=model,
            maybe_temperature=maybe_temperature,
            reasoning_effort=reasoning_effort,
            verbosity=verbosity,
        )
    )
    return request_kwargs


def build_chat_parse_request_kwargs(
    *,
    model: str,
    maybe_temperature: float | None = None,
    reasoning_effort: str | None,
    verbosity: str | None,
) -> dict[str, Any]:
    """Build kwargs for `chat.completions.parse` without responses-only fields."""

    request_kwargs: dict[str, Any] = {"model": model}
    request_kwargs.update(
        _build_capability_gated_request_kwargs(
            model=model,
            maybe_temperature=maybe_temperature,
            reasoning_effort=reasoning_effort,
            verbosity=verbosity,
        )
    )
    return request_kwargs


def _build_openai_client(settings: OpenAISettings) -> OpenAI:
    """Create an OpenAI SDK client from normalized app settings."""

    timeout = settings.openai_request_timeout
    if settings.openai_api_key:
        return OpenAI(api_key=settings.openai_api_key, timeout=timeout)

    # Allow OpenAI SDK default env var fallback handling.
    return OpenAI(timeout=timeout)


def _build_openai_client_from_runtime_settings(
    *,
    timeout_seconds: float,
    explicit_api_key: str | None,
) -> OpenAI:
    """Create an OpenAI SDK client from runtime cache key inputs."""

    if explicit_api_key:
        return OpenAI(api_key=explicit_api_key, timeout=timeout_seconds)
    return OpenAI(timeout=timeout_seconds)


@st.cache_resource
def _get_cached_openai_client(
    timeout_seconds: float,
    api_key_hash: str,
    has_any_api_key: bool,
    _explicit_api_key: str | None = None,
) -> OpenAI:
    """Return cached OpenAI client keyed by non-sensitive runtime fingerprint."""

    # Keep these parameters explicit for deterministic cache invalidation.
    _ = (api_key_hash, has_any_api_key)
    return _build_openai_client_from_runtime_settings(
        timeout_seconds=timeout_seconds,
        explicit_api_key=_explicit_api_key,
    )


def get_openai_client(*, settings: OpenAISettings | None = None) -> OpenAI:
    """Create a cached OpenAI client.

    Priority for API key:
    1) st.secrets["OPENAI_API_KEY"] (common in Streamlit deployments)
    2) Environment variable OPENAI_API_KEY (local dev / CI)
    """
    settings = settings or load_openai_settings()
    resolved_api_key = settings.openai_api_key or os.getenv("OPENAI_API_KEY")
    has_any_api_key = bool(resolved_api_key)
    api_key_hash = _safe_hash(resolved_api_key) if resolved_api_key else "missing"

    return _get_cached_openai_client(
        timeout_seconds=settings.openai_request_timeout,
        api_key_hash=api_key_hash,
        has_any_api_key=has_any_api_key,
        _explicit_api_key=settings.openai_api_key,
    )


def _has_any_openai_api_key(settings: OpenAISettings) -> bool:
    """Check whether a key is present via app settings or SDK env fallback."""

    return bool(settings.openai_api_key or os.getenv("OPENAI_API_KEY"))


def _raise_missing_api_key_hint() -> None:
    """Raise a clear message for UI and logs without exposing secrets."""

    raise OpenAICallError(
        "OpenAI API-Key fehlt (DE) / Missing OpenAI API key (EN).",
        debug_detail="No OPENAI_API_KEY found in st.secrets or environment.",
        error_code="OPENAI_AUTH",
    )


def _safe_hash(text: str, n: int = 10) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:n]


def _canonicalize_for_cache(value: Any) -> str:
    """Return deterministic JSON text for cache-key inputs."""

    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _get_session_response_cache() -> dict[str, dict[str, Any]]:
    """Return mutable in-session LLM response cache bucket."""

    cache_key = SSKey.LLM_RESPONSE_CACHE.value
    cache = st.session_state.get(cache_key)
    if not isinstance(cache, dict):
        cache = {}
        st.session_state[cache_key] = cache
    return cache


def _build_llm_cache_key(
    *,
    task_kind: str,
    resolved_model: str,
    language: str,
    reasoning_effort: str | None,
    verbosity: str | None,
    store: bool,
    normalized_content: str,
    schema_version: str | None = None,
) -> str:
    """Build a stable cache key from model-relevant inputs."""

    key_payload = {
        "task_kind": task_kind,
        "resolved_model": resolved_model,
        "language": language.strip().lower(),
        "reasoning_effort": normalize_reasoning_effort(
            resolved_model, reasoning_effort
        ),
        "verbosity": normalize_verbosity(verbosity),
        "store": bool(store),
        "normalized_content": normalized_content,
        "schema_version": schema_version,
    }
    return hashlib.sha256(
        _canonicalize_for_cache(key_payload).encode("utf-8")
    ).hexdigest()


def _cached_usage(*, cache_key: str) -> dict[str, Any]:
    """Return standardized usage metadata for cache hits."""

    return {
        "cached": True,
        "cache_key": cache_key,
        "provider": "session_state",
    }


def _normalize_usage_dict(usage: object | None) -> dict[str, Any] | None:
    """Normalize SDK usage payloads to plain dictionaries."""

    if usage is None:
        return None
    if isinstance(usage, dict):
        return cast(dict[str, Any], usage)

    model_dump = getattr(usage, "model_dump", None)
    if callable(model_dump):
        dumped = model_dump(mode="python")
        if isinstance(dumped, dict):
            return cast(dict[str, Any], dumped)

    to_dict = getattr(usage, "to_dict", None)
    if callable(to_dict):
        dumped = to_dict()
        if isinstance(dumped, dict):
            return cast(dict[str, Any], dumped)

    return None


def _invalidate_cache_entry_for_validation_error(
    *,
    cache: dict[str, dict[str, Any]],
    cache_key: str,
    task_kind: str,
    model_name: str,
) -> None:
    """Drop invalid cached payloads after schema validation failures."""

    cache.pop(cache_key, None)
    logger.warning(
        "Invalid cached LLM response removed; recomputing. task=%s model=%s cache_key=%s",
        task_kind,
        model_name,
        _safe_hash(cache_key),
    )


def _error_from_openai_exception(exc: Exception, *, endpoint: str) -> OpenAICallError:
    """Convert SDK exceptions into concise, user-safe app errors."""
    status_code = getattr(exc, "status_code", None)

    def _extract_api_error_message() -> str:
        """Extract nested API error messages from OpenAI SDK exceptions."""

        body = getattr(exc, "body", None)
        if isinstance(body, dict):
            error_obj = body.get("error")
            if isinstance(error_obj, dict):
                message = error_obj.get("message")
                if isinstance(message, str):
                    return message
            elif isinstance(error_obj, str):
                return error_obj
            message = body.get("message")
            if isinstance(message, str):
                return message

        error_attr = getattr(exc, "error", None)
        if isinstance(error_attr, dict):
            message = error_attr.get("message")
            if isinstance(message, str):
                return message

        return ""

    def _sanitize_api_message(message: str, *, max_len: int = 200) -> str:
        """Mask likely sensitive fragments and keep message compact."""

        collapsed = " ".join(message.split())
        redacted = re.sub(
            r"(?i)\b(sk-[A-Za-z0-9_-]{8,})\b", "[redacted-key]", collapsed
        )
        redacted = re.sub(
            r"(?i)\bbearer\s+[A-Za-z0-9._-]+", "Bearer [redacted]", redacted
        )
        redacted = re.sub(
            r"(?i)\b(api[_-]?key|token|secret|password)\s*[:=]\s*[^,;\s]+",
            r"\1=[redacted]",
            redacted,
        )

        if len(redacted) <= max_len:
            return redacted
        return f"{redacted[: max_len - 1].rstrip()}…"

    api_message_raw = _extract_api_error_message()
    api_message_sanitized = (
        _sanitize_api_message(api_message_raw) if api_message_raw else ""
    )
    api_message_norm = api_message_sanitized.lower()

    def _debug_detail() -> str:
        details = [f"endpoint={endpoint}", f"exception={type(exc).__name__}"]
        if status_code is not None:
            details.append(f"status_code={status_code}")
        if api_message_sanitized:
            details.append(f"api_message={api_message_sanitized}")
        return ", ".join(details)

    def _classify_bad_request() -> tuple[str, str]:
        """Return ``(error_code, ui_message)`` for common 400 API causes."""

        message = api_message_norm
        model_not_found_hint = (
            "model not found" in message or "unknown model" in message
        )
        endpoint_incompatibility_hint = (
            "endpoint" in message
            and ("not supported" in message or "incompatible" in message)
        ) or (
            "use /v1/chat/completions" in message
            or "use /v1/responses" in message
            or "responses api" in message
            or "chat.completions" in message
        )
        structured_output_hint = (
            "response_format" in message
            or "text_format" in message
            or "structured output" in message
            or "json_schema" in message
            or "json schema" in message
        ) and (
            "unsupported" in message
            or "not supported" in message
            or "unknown parameter" in message
            or "not allowed" in message
            or "invalid" in message
        )
        model_capability_hint = (
            "does not support" in message
            or "unsupported for model" in message
            or "model capability" in message
            or "not available for this model" in message
        ) and (
            "temperature" in message
            or "reasoning" in message
            or "verbosity" in message
            or "response_format" in message
            or "text_format" in message
            or "json_schema" in message
            or "max_output_tokens" in message
        )
        unsupported_hint = (
            "unsupported parameter" in message
            or "unknown parameter" in message
            or "not allowed" in message
            or "invalid type" in message
        )

        if model_not_found_hint:
            return (
                "OPENAI_BAD_REQUEST_MODEL_NOT_FOUND",
                "OpenAI-Modell nicht gefunden (DE) / OpenAI model not found (EN).",
            )
        if endpoint_incompatibility_hint:
            return (
                "OPENAI_BAD_REQUEST_ENDPOINT_INCOMPATIBLE",
                "OpenAI-Endpoint inkompatibel (DE) / Incompatible OpenAI endpoint (EN).",
            )
        if structured_output_hint:
            return (
                "OPENAI_BAD_REQUEST_STRUCTURED_OUTPUT_UNSUPPORTED",
                "Structured Output nicht unterstützt (DE) / Structured output unsupported (EN).",
            )
        if model_capability_hint:
            return (
                "OPENAI_BAD_REQUEST_MODEL_CAPABILITY",
                "OpenAI-Modellfähigkeit passt nicht (DE) / OpenAI model capability mismatch (EN).",
            )
        if unsupported_hint:
            return (
                "OPENAI_BAD_REQUEST_UNSUPPORTED_PARAMETER",
                "Nicht unterstützter OpenAI-Parameter (DE) / Unsupported OpenAI parameter (EN).",
            )
        return (
            "OPENAI_BAD_REQUEST_INVALID",
            "Ungültige OpenAI-Parameter (DE) / Invalid OpenAI parameters (EN).",
        )

    if isinstance(exc, (APITimeoutError, TimeoutError)):
        return OpenAICallError(
            "OpenAI-Timeout (DE) / OpenAI timeout (EN). Bitte erneut versuchen.",
            debug_detail=_debug_detail(),
            error_code="OPENAI_TIMEOUT",
        )

    if isinstance(exc, APIStatusError) and exc.status_code == 400:
        error_code, ui_message = _classify_bad_request()
        return OpenAICallError(
            ui_message,
            debug_detail=_debug_detail(),
            error_code=error_code,
        )

    if isinstance(exc, AuthenticationError):
        return OpenAICallError(
            "OpenAI-Authentifizierung fehlgeschlagen (DE) / OpenAI authentication failed (EN).",
            debug_detail=_debug_detail(),
            error_code="OPENAI_AUTH",
        )

    if isinstance(exc, APIConnectionError):
        return OpenAICallError(
            "OpenAI-Verbindung fehlgeschlagen (DE) / OpenAI connection failed (EN).",
            debug_detail=_debug_detail(),
            error_code="OPENAI_CONNECTION",
        )

    return OpenAICallError(
        "OpenAI-Aufruf fehlgeschlagen (DE) / OpenAI request failed (EN).",
        debug_detail=_debug_detail(),
        error_code="OPENAI_UNKNOWN",
    )


def _error_from_structured_output_exception(exc: Exception) -> OpenAICallError:
    """Map schema/validation failures to user-safe structured-output messages."""

    if isinstance(exc, ValidationError):
        return OpenAICallError(
            "Antwortformat ungültig (DE) / Invalid structured output (EN).",
            debug_detail="Pydantic validation failed for structured output.",
            error_code="OPENAI_PARSE",
        )

    return OpenAICallError(
        "Structured Output fehlgeschlagen (DE) / Structured output failed (EN).",
        debug_detail=f"Structured output parsing error: {type(exc).__name__}.",
        error_code="OPENAI_PARSE",
    )


def _is_retryable_openai_exception(exc: Exception) -> bool:
    """Return True for transient errors worth retrying."""

    return isinstance(exc, (APITimeoutError, TimeoutError, APIConnectionError))


def _run_openai_call_with_retry(
    *,
    fn: Callable[[], Any],
    label: str,
    max_attempts: int = 3,
    base_delay_seconds: float = 0.4,
) -> Any:
    """Run OpenAI call with exponential backoff for transient errors."""

    for attempt in range(1, max_attempts + 1):
        try:
            return fn()
        except Exception as exc:
            if not _is_retryable_openai_exception(exc) or attempt >= max_attempts:
                raise
            delay = base_delay_seconds * (2 ** (attempt - 1))
            logger.warning(
                "%s transient error (%s), retrying in %.2fs (%d/%d).",
                label,
                type(exc).__name__,
                delay,
                attempt,
                max_attempts,
            )
            time.sleep(delay)


def resolve_model_for_task(
    *,
    task_kind: ModelTaskKind,
    session_override: str | None,
    settings: OpenAISettings | None = None,
) -> str:
    """Resolve a model via session/global/task/default/final fallback priority."""

    resolved_settings = settings or load_openai_settings()
    trimmed_session_override = (session_override or "").strip()
    if trimmed_session_override:
        return trimmed_session_override

    if resolved_settings.openai_model_override:
        return resolved_settings.openai_model_override.strip()

    model_by_task: dict[ModelTaskKind, str] = {
        TASK_EXTRACT_JOB_AD: resolved_settings.lightweight_model,
        TASK_GENERATE_QUESTION_PLAN: resolved_settings.medium_reasoning_model,
        TASK_GENERATE_VACANCY_BRIEF: resolved_settings.medium_reasoning_model,
        TASK_GENERATE_JOB_AD: resolved_settings.high_reasoning_model,
        TASK_GENERATE_INTERVIEW_SHEET_HR: resolved_settings.high_reasoning_model,
        TASK_GENERATE_INTERVIEW_SHEET_HM: resolved_settings.high_reasoning_model,
        TASK_GENERATE_BOOLEAN_SEARCH: resolved_settings.medium_reasoning_model,
        TASK_GENERATE_EMPLOYMENT_CONTRACT: resolved_settings.high_reasoning_model,
        TASK_GENERATE_REQUIREMENT_GAP_SUGGESTIONS: resolved_settings.medium_reasoning_model,
        TASK_GENERATE_BENEFIT_SUGGESTIONS: resolved_settings.medium_reasoning_model,
        TASK_GENERATE_ROLE_TASKS_SALARY_FORECAST: resolved_settings.medium_reasoning_model,
    }
    routed_model = model_by_task.get(task_kind, "").strip()
    if routed_model:
        return routed_model

    fallback_model = resolved_settings.default_model.strip()
    if fallback_model:
        return fallback_model

    return "gpt-4o-mini"


def _parse_with_structured_outputs(
    *,
    runtime_config: OpenAIRuntimeConfig,
    messages: List[Dict[str, Any]],
    out_model: Type[BaseModel],
    store: bool,
    maybe_temperature: float | None = None,
) -> tuple[BaseModel, dict[str, Any] | None]:
    """Try `.responses.parse`, then fall back to `.chat.completions.parse` if needed."""

    def _record_final_structured_output_path(
        *,
        endpoint: str,
        requested_model: str,
        final_model: str,
        used_reduced_request: bool,
    ) -> None:
        payload = {
            "endpoint": endpoint,
            "requested_model": requested_model,
            "final_model": final_model,
            "used_reduced_request": used_reduced_request,
        }
        st.session_state[SSKey.OPENAI_LAST_STRUCTURED_OUTPUT_PATH.value] = payload

    def _build_reduced_responses_request_kwargs(*, model: str) -> dict[str, Any]:
        return {"model": model, "store": store}

    def _fallback_model_candidate() -> str | None:
        candidate = runtime_config.settings.default_model.strip()
        if candidate and candidate != runtime_config.resolved_model:
            return candidate
        return None

    settings = runtime_config.settings
    if not _has_any_openai_api_key(settings):
        _raise_missing_api_key_hint()

    client = get_openai_client(settings=settings)
    responses_request_kwargs = build_responses_request_kwargs(
        model=runtime_config.resolved_model,
        store=store,
        maybe_temperature=maybe_temperature,
        reasoning_effort=runtime_config.reasoning_effort,
        verbosity=runtime_config.verbosity,
        max_output_tokens=runtime_config.task_max_output_tokens,
    )

    # Newer SDK path (Responses API + parse helper)
    if hasattr(client, "responses") and hasattr(client.responses, "parse"):
        try:
            resp = _run_openai_call_with_retry(
                fn=lambda: client.responses.parse(
                    input=messages,
                    text_format=out_model,
                    **responses_request_kwargs,
                ),
                label="OpenAI responses.parse",
            )
            _record_final_structured_output_path(
                endpoint="responses.parse",
                requested_model=runtime_config.resolved_model,
                final_model=runtime_config.resolved_model,
                used_reduced_request=False,
            )
        except Exception as exc:
            if not _has_any_openai_api_key(settings):
                _raise_missing_api_key_hint()
            mapped = _error_from_openai_exception(exc, endpoint="responses.parse")
            if mapped.error_code in _STRUCTURED_OUTPUT_RETRYABLE_ERROR_CODES:
                reduced_kwargs = _build_reduced_responses_request_kwargs(
                    model=runtime_config.resolved_model
                )
                try:
                    resp = _run_openai_call_with_retry(
                        fn=lambda: client.responses.parse(
                            input=messages,
                            text_format=out_model,
                            **reduced_kwargs,
                        ),
                        label="OpenAI responses.parse reduced",
                    )
                    _record_final_structured_output_path(
                        endpoint="responses.parse",
                        requested_model=runtime_config.resolved_model,
                        final_model=runtime_config.resolved_model,
                        used_reduced_request=True,
                    )
                except Exception as retry_exc:
                    mapped_retry = _error_from_openai_exception(
                        retry_exc, endpoint="responses.parse"
                    )
                    fallback_model = _fallback_model_candidate()
                    if fallback_model is None:
                        logger.warning(
                            "OpenAI reduced parse failed: %s",
                            mapped_retry.debug_detail or type(retry_exc).__name__,
                        )
                        raise mapped_retry from retry_exc
                    fallback_kwargs = _build_reduced_responses_request_kwargs(
                        model=fallback_model
                    )
                    try:
                        resp = _run_openai_call_with_retry(
                            fn=lambda: client.responses.parse(
                                input=messages,
                                text_format=out_model,
                                **fallback_kwargs,
                            ),
                            label="OpenAI responses.parse fallback-model",
                        )
                        _record_final_structured_output_path(
                            endpoint="responses.parse",
                            requested_model=runtime_config.resolved_model,
                            final_model=fallback_model,
                            used_reduced_request=True,
                        )
                        record_fallback_model_used(
                            st.session_state,
                            task_kind=runtime_config.task_kind or "structured_output",
                            requested_model=runtime_config.resolved_model,
                            final_model=fallback_model,
                            fallback_kind="fallback_model",
                            endpoint="responses.parse",
                            error_code=mapped_retry.error_code,
                        )
                    except Exception as fallback_exc:
                        mapped_fallback = _error_from_openai_exception(
                            fallback_exc, endpoint="responses.parse"
                        )
                        logger.warning(
                            "OpenAI fallback-model parse failed: %s",
                            mapped_fallback.debug_detail or type(fallback_exc).__name__,
                        )
                        raise mapped_fallback from fallback_exc
            else:
                logger.warning(
                    "OpenAI parse failed: %s",
                    mapped.debug_detail or type(exc).__name__,
                )
                raise mapped from exc

        try:
            parsed_response = cast(ParsedResponse, resp)
            parsed = parsed_response.output_parsed
            if not isinstance(parsed, BaseModel):
                raise TypeError("Structured output parse did not return a BaseModel.")
        except Exception as exc:
            mapped = _error_from_structured_output_exception(exc)
            logger.warning("Structured parse failed: %s", mapped.debug_detail)
            raise mapped from exc
        usage = _normalize_usage_dict(parsed_response.usage)
        return parsed, usage

    # Fallback: Chat Completions parse helper (older projects may still use it)
    if hasattr(client, "chat") and hasattr(client.chat.completions, "parse"):
        chat_request_kwargs = build_chat_parse_request_kwargs(
            model=runtime_config.resolved_model,
            maybe_temperature=maybe_temperature,
            reasoning_effort=runtime_config.reasoning_effort,
            verbosity=runtime_config.verbosity,
        )
        try:
            completion = _run_openai_call_with_retry(
                fn=lambda: client.chat.completions.parse(
                    messages=messages,
                    response_format=out_model,
                    **chat_request_kwargs,
                ),
                label="OpenAI chat.completions.parse",
            )
            _record_final_structured_output_path(
                endpoint="chat.completions.parse",
                requested_model=runtime_config.resolved_model,
                final_model=runtime_config.resolved_model,
                used_reduced_request=False,
            )
        except Exception as exc:
            if not _has_any_openai_api_key(settings):
                _raise_missing_api_key_hint()
            mapped = _error_from_openai_exception(
                exc,
                endpoint="chat.completions.parse",
            )
            logger.warning(
                "OpenAI chat.parse failed: %s",
                mapped.debug_detail or type(exc).__name__,
            )
            raise mapped from exc

        try:
            parsed_completion = cast(ParsedChatCompletion, completion)
            maybe_parsed = parsed_completion.choices[0].message.parsed
            if not isinstance(maybe_parsed, BaseModel):
                raise TypeError(
                    "Chat structured output parse did not return a BaseModel."
                )
            parsed = maybe_parsed
        except Exception as exc:
            mapped = _error_from_structured_output_exception(exc)
            logger.warning("Structured chat parse failed: %s", mapped.debug_detail)
            raise mapped from exc
        usage = _normalize_usage_dict(parsed_completion.usage)
        return parsed, usage

    raise OpenAICallError(
        "OpenAI-SDK inkompatibel (DE) / OpenAI SDK unsupported (EN).",
        debug_detail=(
            "endpoint=responses.parse|chat.completions.parse, "
            "exception=SDKFeatureMismatch"
        ),
        error_code="OPENAI_SDK_UNSUPPORTED",
    )


def extract_job_ad(
    job_text: str,
    *,
    model: str,
    language: str = DEFAULT_LANGUAGE,
    store: bool = False,
    temperature: float | None = None,
) -> Tuple[JobAdExtract, Optional[Dict[str, Any]]]:
    runtime_config = _resolve_runtime_config(
        task_kind=TASK_EXTRACT_JOB_AD,
        session_override=model,
    )
    messages = build_extract_job_ad_messages(
        job_text,
        language,
        model=runtime_config.resolved_model,
    )
    prompt_limits = build_task_prompt_limits_suffix(
        max_bullets_per_field=runtime_config.task_max_bullets_per_field,
        max_sentences_per_field=runtime_config.task_max_sentences_per_field,
        max_output_tokens=runtime_config.task_max_output_tokens,
    )
    if prompt_limits:
        messages[0]["content"] = f"{messages[0]['content']}{prompt_limits}"
    normalized_content = _canonicalize_for_cache({"job_text": job_text})
    cache_key = _build_llm_cache_key(
        task_kind=TASK_EXTRACT_JOB_AD,
        resolved_model=runtime_config.resolved_model,
        language=language,
        reasoning_effort=runtime_config.reasoning_effort,
        verbosity=runtime_config.verbosity,
        store=store,
        normalized_content=normalized_content,
        schema_version=JOB_AD_SCHEMA_VERSION,
    )
    cache = _get_session_response_cache()
    cached_entry = cache.get(cache_key)
    if isinstance(cached_entry, dict):
        cached_result = cached_entry.get("result")
        if isinstance(cached_result, dict):
            try:
                parsed_cached = JobAdExtract.model_validate(cached_result)
            except ValidationError:
                _invalidate_cache_entry_for_validation_error(
                    cache=cache,
                    cache_key=cache_key,
                    task_kind=TASK_EXTRACT_JOB_AD,
                    model_name=runtime_config.resolved_model,
                )
            else:
                return parsed_cached, _cached_usage(cache_key=cache_key)

    parsed, usage = _parse_with_structured_outputs(
        runtime_config=runtime_config,
        messages=messages,
        out_model=JobAdExtract,
        store=store,
        maybe_temperature=temperature,
    )
    cache[cache_key] = {"result": parsed.model_dump(mode="json")}

    return cast(JobAdExtract, parsed), usage


def generate_question_plan(
    job: JobAdExtract,
    *,
    model: str,
    language: str = DEFAULT_LANGUAGE,
    store: bool = False,
    temperature: float | None = None,
) -> Tuple[QuestionPlan, Optional[Dict[str, Any]]]:
    runtime_config = _resolve_runtime_config(
        task_kind=TASK_GENERATE_QUESTION_PLAN,
        session_override=model,
    )
    nano_suffix = build_small_model_guardrails(runtime_config.resolved_model)
    task_limits_suffix = build_task_prompt_limits_suffix(
        max_bullets_per_field=runtime_config.task_max_bullets_per_field,
        max_sentences_per_field=runtime_config.task_max_sentences_per_field,
        max_output_tokens=runtime_config.task_max_output_tokens,
    )
    system = (
        "Du bist ein Experte für Vacancy Intake & Recruiting Briefings. "
        "Du erstellst einen dynamischen, aber stabilen Fragebogen für Line Manager. "
        "Der Fragebogen soll alle recruitment-relevanten Informationen top-down einsammeln "
        "und sich am Jobspec orientieren. "
        "Erzeuge nur Fragen, die einen echten Mehrwert liefern (keine Dopplungen). "
        "Nutze kurze, klare Fragen. "
        f"Sprache: {language}."
        f"{nano_suffix}"
        f"{task_limits_suffix}"
    )

    user = (
        "Erstelle einen QuestionPlan in dieser Reihenfolge: company, role_tasks, skills, benefits, interview. "
        "Der Step 'jobad' ist bereits durch die Jobspec-Extraktion abgedeckt; "
        "der historische Step 'team' ist kein sichtbarer Wizard-Schritt mehr. "
        "Dieser Output ist der generische Base-QuestionPlan vor deterministischen Overlays. "
        "Behandle die Steps als strikte Section-Routing-Grenzen: "
        "company sammelt Arbeitgebernarrativ, Business-Kontext, Organisation/Team, Arbeitsmodell/Standort und Risiken/Non-negotiables; "
        "role_tasks sammelt Role Purpose, Top-Deliverables, Ownership Scope, Stakeholder/Collaboration und 30/90/180-Erfolg; "
        "skills sammelt Must-have/Nice-to-have-Trennung, Proficiency Depth, Anwendungskontext und Substituierbarkeit; "
        "benefits sammelt Compensation, Work Model, Vertrag/Start, differenzierende Benefits und Dealbreaker; "
        "interview sammelt Candidate Journey, Stage Goals, Evaluation Evidence, interne Verantwortlichkeiten und SLA/Kommunikation. "
        "Deterministische ESCO/ISCO-Module koennen bereits berufsspezifische Fragen abdecken "
        "(ISCO4, ESCO Occupation, Skill Groups, Essential/Optional Skills/Knowledge, NACE, Regulierung). "
        "Ergaenze nur inkrementelle Top-down-Recruitingfragen, die nach Jobspec und deterministischem Kontext "
        "noch fehlen; dupliziere keine ESCO-abgeleiteten Skill-, Knowledge-, NACE- oder Regulierungsfragen. "
        "Reserviere IDs mit Prefix 'ctx_', konkrete ESCO/ISCO/NACE-/Regulierungsfragen und ESCO Skill-Group-Fragen "
        "fuer deterministische Compiler-Overlays; nutze sie nicht im Base-QuestionPlan. "
        "Erfinde keine Skills, Gehaltsbaender, Prozessschritte, Zertifikate, rechtlichen Anforderungen oder Benefits. "
        "Füge bei jedem Step 6–12 Fragen hinzu, je nachdem, was im Jobspec fehlt. "
        "Markiere pro Step genau 3–5 Fragen mit priority='core'; "
        "weitere Fragen als 'standard' oder 'detail'. "
        "Setze group_key pro Step ausschliesslich auf eine dieser stabilen Domaenen: "
        "company: employer_narrative, business_context, organization_team, work_model_location, risks_non_negotiables; "
        "role_tasks: role_purpose, top_deliverables, ownership_scope, stakeholders_collaboration, success_30_90_180; "
        "skills: must_have, nice_to_have, proficiency_depth, application_context, substitutability; "
        "benefits: compensation, work_model, contract_start, differentiating_benefits, dealbreakers; "
        "interview: candidate_journey, stage_goals, evaluation_evidence, internal_responsibilities, slas_communication. "
        "Nutze keine einmaligen oder jobspezifischen group_key-Werte. "
        "Setze fact_key nur dann, wenn eine Frage direkt ein kanonisches Intake-Faktum adressiert "
        "(z. B. company.company_name, role.job_title, skills.must_have_skills, benefits.salary_range); "
        "lasse fact_key sonst null. "
        "Nutze depends_on nur bei echten Follow-up-Fragen; vermeide verschachtelte oder übermäßige Abhängigkeiten. "
        "depends_on darf nur auf eine fruehere Frage im selben Step zeigen, nie auf spaetere Fragen, andere Steps oder sich selbst. "
        "Für depends_on nutze nur einfache Regeln mit question_id plus genau einem von equals ODER any_of ODER is_answered. "
        "Nutze follow_up_prompts sparsam (maximal 3 kurze Prompts) für Fragen, bei denen vage Antworten typischerweise Nachhaken brauchen; "
        "sonst lasse follow_up_prompts leer. "
        "Wenn impact_targets gesetzt sind, nutze ausschliesslich diese Werte: brief, salary, skills, interview, export; "
        "dedupliziere sie und lasse sie sonst leer. "
        "Setze acquisition_cost nur auf low, medium oder high. "
        "Setze info_gain_score nur als Zahl von 0.0 bis 1.0; hoeher fuer direkte Brief-, Salary-, Skills-, Interview- oder Export-Luecken. "
        "Bevorzuge konkrete, messbare Antworten (z. B. 'Erfolgskriterien', 'Top-Deliverables', 'Must-have vs Nice-to-have').\n\n"
        "Wenn answer_type='number' genutzt wird, setze immer explizit min_value und max_value "
        "(optional step_value), passend zur Frage. Nutze keine Freitext-Frage für numerische Werte.\n\n"
        "Jobspec-Extraktion (JSON):\n"
        f"{json.dumps(job.model_dump(mode='json'), ensure_ascii=False, sort_keys=True, separators=(',', ':'))}"
    )

    normalized_job = _canonicalize_for_cache(job.model_dump(mode="json"))
    cache_key = _build_llm_cache_key(
        task_kind=TASK_GENERATE_QUESTION_PLAN,
        resolved_model=runtime_config.resolved_model,
        language=language,
        reasoning_effort=runtime_config.reasoning_effort,
        verbosity=runtime_config.verbosity,
        store=store,
        normalized_content=normalized_job,
        schema_version=QUESTION_SCHEMA_VERSION,
    )
    cache = _get_session_response_cache()
    cached_entry = cache.get(cache_key)
    if isinstance(cached_entry, dict):
        cached_result = cached_entry.get("result")
        if isinstance(cached_result, dict):
            try:
                parsed_cached = QuestionPlan.model_validate(cached_result)
            except ValidationError:
                _invalidate_cache_entry_for_validation_error(
                    cache=cache,
                    cache_key=cache_key,
                    task_kind=TASK_GENERATE_QUESTION_PLAN,
                    model_name=runtime_config.resolved_model,
                )
            else:
                normalized_cached = normalize_question_plan(parsed_cached)
                return normalized_cached, _cached_usage(cache_key=cache_key)

    parsed, usage = _parse_with_structured_outputs(
        runtime_config=runtime_config,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        out_model=QuestionPlan,
        store=store,
        maybe_temperature=temperature,
    )

    normalized = normalize_question_plan(cast(QuestionPlan, parsed))
    cache[cache_key] = {"result": normalized.model_dump(mode="json")}
    return normalized, usage


def normalize_question_plan(
    plan: QuestionPlan,
    *,
    preserve_noncanonical_group_ids: set[str] | None = None,
) -> QuestionPlan:
    """Guarantee unique, stable-ish ids and basic invariants."""
    seen = set()
    preserved_group_ids = preserve_noncanonical_group_ids or set()
    for step in plan.steps:
        for q in step.questions:
            if not q.id or q.id.strip() == "":
                q.id = f"q_{step.step_key}_{_safe_hash(q.label)}"
            else:
                q.id = re_slugify(q.id)

            # Ensure uniqueness
            if q.id in seen:
                q.id = f"{q.id}_{_safe_hash(step.step_key + q.label)}"
            seen.add(q.id)

            # Default target_path if not provided
            if not q.target_path:
                q.target_path = f"answers.{step.step_key}.{q.id}"

            _normalize_category_question(q)
            _normalize_numeric_question(q)
            _normalize_question_priority(q)
            _normalize_question_group_key(
                q,
                step_key=step.step_key,
                preserve_noncanonical=q.id in preserved_group_ids,
            )
            _normalize_question_fact_key(q)
            _normalize_question_impact_targets(q)
            _normalize_question_dependencies(q, step=step)
            _normalize_question_follow_up_prompts(q)
    return plan


def _normalize_question_fact_key(q: Any) -> None:
    raw_fact_key = getattr(q, "fact_key", None)
    if isinstance(raw_fact_key, str) and raw_fact_key.strip():
        try:
            q.fact_key = FactKey(raw_fact_key.strip()).value
            return
        except ValueError:
            q.fact_key = None

    inferred_fact_key = _infer_question_fact_key(q)
    q.fact_key = inferred_fact_key.value if inferred_fact_key is not None else None


def _infer_question_fact_key(q: Any) -> FactKey | None:
    for raw_path in (getattr(q, "target_path", None), getattr(q, "id", None)):
        if not isinstance(raw_path, str):
            continue
        normalized_path = raw_path.strip()
        if not normalized_path:
            continue
        try:
            return FactKey(normalized_path)
        except ValueError:
            pass
        tail = normalized_path.split(".")[-1].strip()
        fact_key = _QUESTION_FACT_KEY_BY_TARGET_PATH.get(tail)
        if fact_key is not None:
            return fact_key
    return None


def _normalize_question_priority(q: Any) -> None:
    raw_priority = getattr(q, "priority", None)
    if not isinstance(raw_priority, str):
        q.priority = None
        return
    normalized = raw_priority.strip().lower()
    q.priority = normalized if normalized in _QUESTION_PRIORITY_VALUES else None


def _normalize_question_group_key(
    q: Any,
    *,
    step_key: str,
    preserve_noncanonical: bool = False,
) -> None:
    canonical_groups = _CANONICAL_QUESTION_GROUPS_BY_STEP.get(step_key)
    raw_group_key = getattr(q, "group_key", None)
    normalized_group = (
        re_slugify(raw_group_key)
        if isinstance(raw_group_key, str) and raw_group_key.strip()
        else ""
    )
    if canonical_groups is None:
        if normalized_group:
            q.group_key = normalized_group
            return
        q.group_key = re_slugify(f"{step_key}_{q.id}")
        return

    if normalized_group in canonical_groups:
        q.group_key = normalized_group
        return

    if preserve_noncanonical and normalized_group:
        q.group_key = normalized_group
        return

    inferred_group = _infer_canonical_question_group_key(
        q,
        step_key=step_key,
        normalized_group=normalized_group,
    )
    q.group_key = inferred_group or _QUESTION_GROUP_FALLBACK_BY_STEP[step_key]


def _infer_canonical_question_group_key(
    q: Any,
    *,
    step_key: str,
    normalized_group: str,
) -> str | None:
    blob = _question_group_match_blob(q, normalized_group=normalized_group)
    for group_key, keywords in _QUESTION_GROUP_MATCH_RULES.get(step_key, ()):
        if any(keyword in blob for keyword in keywords):
            return group_key
    return None


def _question_group_match_blob(q: Any, *, normalized_group: str) -> str:
    raw = " ".join(
        str(part or "")
        for part in (
            normalized_group,
            getattr(q, "id", ""),
            getattr(q, "label", ""),
            getattr(q, "help", ""),
            getattr(q, "rationale", ""),
            getattr(q, "target_path", ""),
            getattr(q, "fact_key", ""),
        )
    ).casefold()
    normalized = (
        raw.replace("ä", "ae")
        .replace("ö", "oe")
        .replace("ü", "ue")
        .replace("ß", "ss")
    )
    return re.sub(r"[^a-z0-9_]+", " ", normalized)


def _normalize_question_impact_targets(q: Any) -> None:
    raw_targets = getattr(q, "impact_targets", None)
    if not isinstance(raw_targets, list):
        q.impact_targets = []
        return

    normalized_targets: list[str] = []
    seen: set[str] = set()
    for raw_target in raw_targets:
        if not isinstance(raw_target, str):
            continue
        target = raw_target.strip().lower()
        if target not in _QUESTION_IMPACT_TARGET_VALUES or target in seen:
            continue
        normalized_targets.append(target)
        seen.add(target)
    q.impact_targets = normalized_targets


def _prior_question_ids(step: Any, q: Any) -> set[str]:
    prior_ids: set[str] = set()
    for item in getattr(step, "questions", []):
        if item is q:
            break
        item_id = getattr(item, "id", None)
        if item_id:
            prior_ids.add(str(item_id))
    return prior_ids


def _normalize_question_dependencies(q: Any, *, step: Any) -> None:
    raw_depends_on = getattr(q, "depends_on", None)
    if not isinstance(raw_depends_on, list) or not raw_depends_on:
        q.depends_on = None
        return

    prior_ids = _prior_question_ids(step, q)
    sanitized: list[QuestionDependency] = []
    for dep in raw_depends_on:
        if not hasattr(dep, "question_id"):
            continue
        source_id_raw = getattr(dep, "question_id", "")
        if not isinstance(source_id_raw, str) or not source_id_raw.strip():
            continue
        source_id = re_slugify(source_id_raw)
        if source_id == q.id or source_id not in prior_ids:
            continue

        equals = getattr(dep, "equals", None)
        any_of = getattr(dep, "any_of", None)
        is_answered = getattr(dep, "is_answered", None)

        normalized_any_of: list[str | int | float | bool] | None = None
        if isinstance(any_of, list):
            normalized_any_of = []
            for value in any_of:
                if isinstance(value, (str, int, float, bool)):
                    normalized_any_of.append(value)
            if not normalized_any_of:
                normalized_any_of = None

        if not isinstance(equals, (str, int, float, bool)):
            equals = None
        if not isinstance(is_answered, bool):
            is_answered = None

        active_keys = sum(
            value is not None for value in (equals, normalized_any_of, is_answered)
        )
        if active_keys != 1:
            continue

        dep_payload: dict[str, Any] = {"question_id": source_id}
        if equals is not None:
            dep_payload["equals"] = equals
        if normalized_any_of is not None:
            dep_payload["any_of"] = normalized_any_of
        if is_answered is not None:
            dep_payload["is_answered"] = is_answered
        sanitized.append(QuestionDependency.model_validate(dep_payload))

    q.depends_on = sanitized or None


def _normalize_question_follow_up_prompts(q: Any) -> None:
    raw_prompts = getattr(q, "follow_up_prompts", None)
    if not isinstance(raw_prompts, list):
        q.follow_up_prompts = []
        return

    normalized_prompts: list[str] = []
    seen: set[str] = set()
    for raw_prompt in raw_prompts:
        if not isinstance(raw_prompt, str):
            continue
        prompt = " ".join(raw_prompt.strip().split())
        if not prompt:
            continue
        dedupe_key = prompt.casefold()
        if dedupe_key in seen:
            continue
        normalized_prompts.append(prompt)
        seen.add(dedupe_key)
        if len(normalized_prompts) >= 3:
            break
    q.follow_up_prompts = normalized_prompts


def _normalize_category_question(q: Any) -> None:
    haystack = " ".join(
        str(part).lower()
        for part in (
            getattr(q, "label", ""),
            getattr(q, "help", ""),
            getattr(q, "id", ""),
        )
        if isinstance(part, str)
    )
    for rule in _CATEGORY_QUESTION_RULES:
        if not any(term in haystack for term in rule["terms"]):
            continue
        q.answer_type = rule["answer_type"]
        q.options = _merge_options_with_fallback(q.options, rule["options"])
        if q.answer_type == AnswerType.MULTI_SELECT and not isinstance(q.default, list):
            q.default = []
        elif q.answer_type == AnswerType.SINGLE_SELECT and isinstance(q.default, list):
            q.default = q.default[0] if q.default else None
        return


def _merge_options_with_fallback(
    existing_options: list[Any] | None,
    rule_options: tuple[str, ...],
) -> list[str]:
    merged: list[str] = []
    for option in [*(existing_options or []), *rule_options]:
        if isinstance(option, dict):
            candidate = option.get("value", "")
        else:
            candidate = option
        if not isinstance(candidate, str):
            continue
        cleaned = candidate.strip()
        if cleaned and cleaned not in merged:
            merged.append(cleaned)
    if _OTHER_OPTION not in merged:
        merged.append(_OTHER_OPTION)
    return merged


def _normalize_numeric_question(q: Any) -> None:
    haystack = " ".join(
        str(part).lower()
        for part in (
            getattr(q, "label", ""),
            getattr(q, "help", ""),
            getattr(q, "id", ""),
            getattr(q, "rationale", ""),
        )
        if isinstance(part, str)
    )
    if not haystack:
        return

    matched_rule: dict[str, Any] | None = None
    for rule in _NUMERIC_QUESTION_RULES:
        if any(term in haystack for term in rule["terms"]):
            matched_rule = rule
            break
    if matched_rule is None and getattr(q, "answer_type", None) != AnswerType.NUMBER:
        return

    q.answer_type = AnswerType.NUMBER
    if matched_rule is not None:
        rule_min, rule_max, rule_step = matched_rule["bounds"]
    else:
        rule_min, rule_max, rule_step = (0.0, 100.0, 1.0)

    min_value = getattr(q, "min_value", None)
    max_value = getattr(q, "max_value", None)
    step_value = getattr(q, "step_value", None)

    if min_value is None:
        q.min_value = rule_min
    if max_value is None:
        q.max_value = rule_max
    if step_value is None:
        q.step_value = rule_step


def re_slugify(s: str) -> str:
    import re

    s = s.strip().lower()
    s = re.sub(r"[^a-z0-9_\-]+", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    if not s:
        s = "q_" + _safe_hash(s)
    if s[0].isdigit():
        s = "q_" + s
    return s


def _answer_dict(answers: Mapping[str, Any], fact_key: FactKey) -> dict[str, Any] | None:
    value = answers.get(fact_key.value)
    return value if isinstance(value, dict) and value else None


def _answer_list(answers: Mapping[str, Any], fact_key: FactKey) -> list[Any] | None:
    value = answers.get(fact_key.value)
    return value if isinstance(value, list) and value else None


def _normalized_structured_fields(answers: Mapping[str, Any]) -> dict[str, Any]:
    fields: dict[str, Any] = {}
    skill_items = _answer_list(answers, FactKey.SKILLS_ITEMS)
    if skill_items is not None:
        fields["skill_items"] = skill_items
    variable_pay = _answer_dict(answers, FactKey.BENEFITS_VARIABLE_PAY)
    if variable_pay is not None:
        fields["variable_pay"] = variable_pay
    travel_profile = _answer_dict(answers, FactKey.ROLE_TRAVEL_PROFILE)
    if travel_profile is not None:
        fields["travel_profile"] = travel_profile
    scorecard_template = _answer_dict(answers, FactKey.INTERVIEW_SCORECARD_TEMPLATE)
    if scorecard_template is not None:
        fields["interview_scorecard_template"] = scorecard_template
    return fields


def _brief_answers(brief: VacancyBrief) -> dict[str, Any]:
    answers = brief.structured_data.answers
    return answers if isinstance(answers, dict) else {}


def _brief_job_payload(brief: VacancyBrief) -> dict[str, Any]:
    payload = brief.structured_data.job_extract
    return payload if isinstance(payload, dict) else {}


def _brief_answer_list(brief: VacancyBrief, fact_key: FactKey) -> list[Any]:
    value = _brief_answers(brief).get(fact_key.value)
    return value if isinstance(value, list) else []


def _brief_answer_dict(brief: VacancyBrief, fact_key: FactKey) -> dict[str, Any]:
    value = _brief_answers(brief).get(fact_key.value)
    return value if isinstance(value, dict) else {}


def _fallback_core_question_blocks(brief: VacancyBrief) -> list[dict[str, Any]]:
    core_questions = [
        str(item).strip()
        for item in _brief_answer_list(brief, FactKey.INTERVIEW_CORE_QUESTIONS)
        if str(item).strip()
    ]
    if not core_questions:
        return []
    return [
        {
            "block_id": "core_questions",
            "title": "Kernfragen",
            "objective": "Vergleichbare Fragen für alle Kandidat:innen stellen.",
            "questions": core_questions[:8],
            "follow_up_prompts": [],
            "signal_tags": ["structured_interview", "fairness"],
        }
    ]


def _fallback_rubric_from_scorecard(brief: VacancyBrief) -> list[dict[str, Any]]:
    scorecard = _brief_answer_dict(brief, FactKey.INTERVIEW_SCORECARD_TEMPLATE)
    criteria_raw = scorecard.get("criteria", [])
    criteria = criteria_raw if isinstance(criteria_raw, list) else []
    output: list[dict[str, Any]] = []
    for idx, item in enumerate(criteria[:6]):
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or "").strip()
        if not title:
            continue
        scale = str(item.get("scale") or "1-5").strip()
        evidence_anchor = str(item.get("evidence_anchor") or "").strip()
        output.append(
            {
                "criterion_id": re_slugify(title),
                "title": title,
                "description": evidence_anchor or f"{title} strukturiert bewerten.",
                "weight_percent": int(item.get("weight_percent") or 0),
                "score_scale": [scale] if scale else [],
                "evidence_examples": [evidence_anchor] if evidence_anchor else [],
            }
        )
    return output


def _fallback_recommendation_options(brief: VacancyBrief) -> list[str]:
    scorecard = _brief_answer_dict(brief, FactKey.INTERVIEW_SCORECARD_TEMPLATE)
    options = scorecard.get("recommendation_options", [])
    if isinstance(options, list):
        cleaned = [str(item).strip() for item in options if str(item).strip()]
        if cleaned:
            return cleaned
    return ["Strong Yes", "Yes", "Hold", "No"]


def _contract_fallback_salary(brief: VacancyBrief) -> dict[str, Any]:
    job_payload = _brief_job_payload(brief)
    salary = job_payload.get("salary_range")
    if isinstance(salary, dict) and (salary.get("min") or salary.get("max")):
        return {
            "min": salary.get("min") or 0,
            "max": salary.get("max") or 0,
            "currency": salary.get("currency") or "EUR",
            "period": salary.get("period") or "yearly",
            "notes": salary.get("notes") or "",
        }
    variable_pay = _brief_answer_dict(brief, FactKey.BENEFITS_VARIABLE_PAY)
    notes = str(variable_pay.get("bonus_logic") or "Bitte Vergütung ergänzen.").strip()
    return {
        "min": variable_pay.get("ote_min") or 0,
        "max": variable_pay.get("ote_max") or 0,
        "currency": variable_pay.get("currency") or "EUR",
        "period": variable_pay.get("period") or "yearly",
        "notes": notes,
    }


def _contract_fallback_clauses(brief: VacancyBrief) -> list[dict[str, Any]]:
    answers = _brief_answers(brief)
    clauses: list[dict[str, Any]] = []
    for fact_key, title in (
        (FactKey.BENEFITS_COLLECTIVE_AGREEMENT_CONTEXT, "Tarifliche Vorgaben"),
        (FactKey.BENEFITS_OFFER_COMPONENTS, "Offer-Komponenten"),
        (FactKey.LEGAL_WORK_AUTHORIZATION_SUPPORT, "Work Authorization"),
    ):
        value = answers.get(fact_key.value)
        if not value:
            continue
        clauses.append(
            {
                "clause_id": re_slugify(fact_key.value),
                "title": title,
                "clause_text": json.dumps(value, ensure_ascii=False)
                if isinstance(value, (dict, list))
                else str(value),
                "required": False,
                "legal_note": "Aus strukturierten Intake-Fakten übernommen; rechtlich prüfen.",
            }
        )
    return clauses


def generate_vacancy_brief(
    job: JobAdExtract,
    answers: Dict[str, Any],
    *,
    model: str,
    selected_role_tasks: Optional[List[str]] = None,
    selected_skills: Optional[List[str]] = None,
    selected_benefits: Optional[List[str]] = None,
    company_website_research: Optional[CompanyWebsiteResearch] = None,
    language: str = DEFAULT_LANGUAGE,
    store: bool = False,
    temperature: float | None = None,
) -> Tuple[VacancyBrief, Optional[Dict[str, Any]]]:
    runtime_config = _resolve_runtime_config(
        task_kind=TASK_GENERATE_VACANCY_BRIEF,
        session_override=model,
    )
    nano_suffix = build_small_model_guardrails(runtime_config.resolved_model)
    task_limits_suffix = build_task_prompt_limits_suffix(
        max_bullets_per_field=runtime_config.task_max_bullets_per_field,
        max_sentences_per_field=runtime_config.task_max_sentences_per_field,
        max_output_tokens=runtime_config.task_max_output_tokens,
    )
    system = (
        "Du bist ein Recruiting Partner, der aus einer Jobspec und Manager-Antworten "
        "einen vollständigen Recruiting Brief erstellt. "
        "Du bist präzise, vermeidest Marketing-Floskeln und machst offene Punkte transparent. "
        f"Sprache: {language}."
        f"{nano_suffix}"
        f"{task_limits_suffix}"
    )

    user = (
        "Erstelle jetzt den finalen VacancyBrief.\n\n"
        "Jobspec-Extraktion (JSON):\n"
        f"{json.dumps(job.model_dump(mode='json'), ensure_ascii=False, sort_keys=True, separators=(',', ':'))}\n\n"
        "Manager-Antworten (JSON):\n"
        f"{json.dumps(answers, ensure_ascii=False, sort_keys=True, separators=(',', ':'))}\n\n"
        "Normalisierte strukturierte Felder (JSON):\n"
        f"{json.dumps(_normalized_structured_fields(answers), ensure_ascii=False, sort_keys=True, separators=(',', ':'))}\n\n"
        "Explizit ausgewählte Benefits (JSON):\n"
        f"{json.dumps(selected_benefits or [], ensure_ascii=False, sort_keys=True, separators=(',', ':'))}\n\n"
        "Firmen-Homepage-Research (JSON):\n"
        f"{json.dumps((company_website_research.model_dump(mode='json') if company_website_research is not None else {}), ensure_ascii=False, sort_keys=True, separators=(',',':'))}\n\n"
        "Wichtig: Falls wichtige Informationen fehlen, schreibe sie unter risks_open_questions."
    )

    normalized_content = _canonicalize_for_cache(
        {
            "job": job.model_dump(mode="json"),
            "answers": answers,
            "normalized_structured_fields": _normalized_structured_fields(answers),
            "selected_role_tasks": selected_role_tasks or [],
            "selected_skills": selected_skills or [],
            "selected_benefits": selected_benefits or [],
            "company_website_research": (
                company_website_research.model_dump(mode="json")
                if company_website_research is not None
                else {}
            ),
        }
    )
    cache_key = _build_llm_cache_key(
        task_kind=TASK_GENERATE_VACANCY_BRIEF,
        resolved_model=runtime_config.resolved_model,
        language=language,
        reasoning_effort=runtime_config.reasoning_effort,
        verbosity=runtime_config.verbosity,
        store=store,
        normalized_content=normalized_content,
        schema_version=VACANCY_SCHEMA_VERSION,
    )
    cache = _get_session_response_cache()
    cached_entry = cache.get(cache_key)
    if isinstance(cached_entry, dict):
        cached_result = cached_entry.get("result")
        if isinstance(cached_result, dict):
            try:
                parsed_cached = VacancyBrief.model_validate(cached_result)
            except ValidationError:
                _invalidate_cache_entry_for_validation_error(
                    cache=cache,
                    cache_key=cache_key,
                    task_kind=TASK_GENERATE_VACANCY_BRIEF,
                    model_name=runtime_config.resolved_model,
                )
            else:
                return parsed_cached, _cached_usage(cache_key=cache_key)

    parsed, usage = _parse_with_structured_outputs(
        runtime_config=runtime_config,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        out_model=VacancyBriefLLM,
        store=store,
        maybe_temperature=temperature,
    )

    # Always embed the merged structured payload for downstream systems
    parsed_brief = cast(VacancyBriefLLM, parsed)
    merged = {
        "job_extract": job.model_dump(),
        "answers": answers,
        **_normalized_structured_fields(answers),
        "selected_role_tasks": selected_role_tasks or None,
        "selected_skills": selected_skills or None,
        "selected_benefits": selected_benefits or None,
        "company_website_research": (
            company_website_research.model_dump(mode="json")
            if company_website_research is not None
            else None
        ),
    }
    brief = VacancyBrief(
        **parsed_brief.model_dump(),
        structured_data=VacancyStructuredData.model_validate(merged),
    )
    cache[cache_key] = {"result": brief.model_dump(mode="json")}
    return brief, usage


def upgrade_vacancy_brief_critical_sections(
    base_brief: VacancyBrief,
    job: JobAdExtract,
    answers: Dict[str, Any],
    *,
    model: str,
    language: str = DEFAULT_LANGUAGE,
    store: bool = False,
    temperature: float | None = None,
) -> Tuple[VacancyBrief, Optional[Dict[str, Any]]]:
    """Sharpen only critical quality sections while keeping export schema unchanged."""

    runtime_config = _resolve_runtime_config(
        task_kind=TASK_GENERATE_VACANCY_BRIEF,
        session_override=model,
    )
    task_limits_suffix = build_task_prompt_limits_suffix(
        max_bullets_per_field=runtime_config.task_max_bullets_per_field,
        max_sentences_per_field=runtime_config.task_max_sentences_per_field,
        max_output_tokens=runtime_config.task_max_output_tokens,
    )
    system = (
        "Du bist ein Senior Recruiting Quality Reviewer. "
        "Du überarbeitest ausschließlich die kritischen Abschnitte eines vorhandenen Vacancy Briefs. "
        "Ziele: präzisere, testbare evaluation_rubric und konkrete risks_open_questions. "
        "Keine zusätzlichen Felder, keine Änderung anderer Brief-Abschnitte. "
        f"Sprache: {language}."
        f"{task_limits_suffix}"
    )
    user = (
        "Überarbeite nur evaluation_rubric und risks_open_questions.\n\n"
        "Bestehender Vacancy Brief (JSON):\n"
        f"{json.dumps(base_brief.model_dump(mode='json'), ensure_ascii=False, sort_keys=True, separators=(',', ':'))}\n\n"
        "Jobspec-Extraktion (JSON):\n"
        f"{json.dumps(job.model_dump(mode='json'), ensure_ascii=False, sort_keys=True, separators=(',', ':'))}\n\n"
        "Manager-Antworten (JSON):\n"
        f"{json.dumps(answers, ensure_ascii=False, sort_keys=True, separators=(',', ':'))}\n\n"
        "Anforderungen:\n"
        "- evaluation_rubric als klare, beobachtbare Kriterien (bullet-ready).\n"
        "- risks_open_questions nur offene Risiken/Unklarheiten, priorisiert nach Hiring-Impact."
    )
    normalized_content = _canonicalize_for_cache(
        {
            "base_brief": base_brief.model_dump(mode="json"),
            "job": job.model_dump(mode="json"),
            "answers": answers,
            "mode": "critical_upgrade",
        }
    )
    cache_key = _build_llm_cache_key(
        task_kind=f"{TASK_GENERATE_VACANCY_BRIEF}_critical_upgrade",
        resolved_model=runtime_config.resolved_model,
        language=language,
        reasoning_effort=runtime_config.reasoning_effort,
        verbosity=runtime_config.verbosity,
        store=store,
        normalized_content=normalized_content,
        schema_version=VACANCY_SCHEMA_VERSION,
    )
    cache = _get_session_response_cache()
    cached_entry = cache.get(cache_key)
    if isinstance(cached_entry, dict):
        cached_result = cached_entry.get("result")
        if isinstance(cached_result, dict):
            updated_cached = base_brief.model_copy(deep=True)
            updated_cached.evaluation_rubric = cached_result.get(
                "evaluation_rubric", []
            )
            updated_cached.risks_open_questions = cached_result.get(
                "risks_open_questions", []
            )
            return updated_cached, _cached_usage(cache_key=cache_key)

    parsed, usage = _parse_with_structured_outputs(
        runtime_config=runtime_config,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        out_model=VacancyBriefCriticalSections,
        store=store,
        maybe_temperature=temperature,
    )
    parsed_sections = cast(VacancyBriefCriticalSections, parsed)
    updated = base_brief.model_copy(deep=True)
    updated.evaluation_rubric = parsed_sections.evaluation_rubric
    updated.risks_open_questions = parsed_sections.risks_open_questions
    cache[cache_key] = {"result": parsed_sections.model_dump(mode="json")}
    return updated, usage


def generate_custom_job_ad(
    *,
    job: JobAdExtract,
    answers: Dict[str, Any],
    selected_values: Dict[str, list[str]],
    style_guide: str,
    change_request: str | None,
    model: str,
    language: str = DEFAULT_LANGUAGE,
    store: bool = False,
    temperature: float | None = None,
) -> Tuple[JobAdGenerationResult, Optional[Dict[str, Any]]]:
    """Generate or refine a job ad draft from explicitly selected intake values."""

    runtime_config = _resolve_runtime_config(
        task_kind=TASK_GENERATE_JOB_AD,
        session_override=model,
    )
    task_limits_suffix = build_task_prompt_limits_suffix(
        max_bullets_per_field=runtime_config.task_max_bullets_per_field,
        max_sentences_per_field=runtime_config.task_max_sentences_per_field,
        max_output_tokens=runtime_config.task_max_output_tokens,
    )
    system = (
        "Du bist ein Senior Recruiting Copywriter und Compliance Reviewer. "
        "Schreibe eine zielgruppen-optimierte, AGG-konforme Stellenanzeige auf Basis "
        "explizit ausgewählter Informationen. "
        "Wenn Informationen fehlen, markiere sie klar in agg_checklist ohne zu halluzinieren. "
        "Alle Felder sind Plain Text ohne Markdown, HTML, Tabellen oder Link-Markup. "
        "Der Styleguide ist nur eine Schreibanweisung und darf nicht als Abschnitt, "
        "Zitat oder Anhang in die Stellenanzeige übernommen werden. "
        f"Sprache: {language}."
        f"{task_limits_suffix}"
    )
    user = (
        "Erzeuge eine finale Stellenanzeige nur aus den ausgewählten Daten. "
        "Verwende klare, inklusive Sprache und vermeide diskriminierende Formulierungen.\n\n"
        "Struktur der Anzeige:\n"
        "- headline: kandidatensichtbarer Titel ohne Markdown.\n"
        "- intro: kurzer Einstieg mit Arbeitgeber, Rolle und Wirkung.\n"
        "- responsibilities: 3-6 konkrete Aufgaben als Liste.\n"
        "- profile: 3-6 Anforderungen als Liste, getrennt von Benefits.\n"
        "- offer: 3-6 konkrete Arbeitgeberangebote oder Benefits als Liste.\n"
        "- cta: klare Handlungsaufforderung mit Bewerbungsweg, falls bekannt.\n"
        "- equal_opportunity_note: kurzer inklusiver Hinweis, ohne rechtliche Übertreibung.\n"
        "- job_ad_text: dieselbe Anzeige als Plain-Text-Fallback mit Abschnittsüberschriften, "
        "ohne Markdown-Zeichen wie **, #, Tabellen oder Link-Syntax.\n"
        "- target_group und agg_checklist bleiben interne Review-Felder, nicht Teil des publishable Body.\n\n"
        "Jobspec (JSON):\n"
        f"{json.dumps(job.model_dump(mode='json'), ensure_ascii=False, sort_keys=True, separators=(',', ':'))}\n\n"
        "Manager-Antworten (JSON):\n"
        f"{json.dumps(answers, ensure_ascii=False, sort_keys=True, separators=(',', ':'))}\n\n"
        "Ausgewählte Inhalte (JSON):\n"
        f"{json.dumps(selected_values, ensure_ascii=False, sort_keys=True, separators=(',', ':'))}\n\n"
        f"Styleguide:\n{style_guide.strip() or 'Nicht angegeben.'}\n\n"
        f"Anpassungswunsch:\n{(change_request or '').strip() or 'Kein zusätzlicher Änderungswunsch.'}\n\n"
        "Pflicht: headline, target_group (Liste), agg_checklist (Liste), job_ad_text, "
        "intro, responsibilities, profile, offer, cta und equal_opportunity_note liefern. "
        "Kopiere den Styleguide niemals in job_ad_text oder die publishable Felder."
    )
    normalized_content = _canonicalize_for_cache(
        {
            "job": job.model_dump(mode="json"),
            "answers": answers,
            "selected_values": selected_values,
            "style_guide": style_guide,
            "change_request": change_request or "",
        }
    )
    cache_key = _build_llm_cache_key(
        task_kind=TASK_GENERATE_JOB_AD,
        resolved_model=runtime_config.resolved_model,
        language=language,
        reasoning_effort=runtime_config.reasoning_effort,
        verbosity=runtime_config.verbosity,
        store=store,
        normalized_content=normalized_content,
        schema_version=VACANCY_SCHEMA_VERSION,
    )
    cache = _get_session_response_cache()
    cached_entry = cache.get(cache_key)
    if isinstance(cached_entry, dict):
        cached_result = cached_entry.get("result")
        if isinstance(cached_result, dict):
            return JobAdGenerationResult.model_validate(cached_result), _cached_usage(
                cache_key=cache_key
            )

    parsed, usage = _parse_with_structured_outputs(
        runtime_config=runtime_config,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        out_model=JobAdGenerationResult,
        store=store,
        maybe_temperature=temperature,
    )
    result = cast(JobAdGenerationResult, parsed)
    cache[cache_key] = {"result": result.model_dump(mode="json")}
    return result, usage


def _build_task_fallback_usage(
    *,
    task_kind: str,
    ui_message: str,
    error_code: str | None,
) -> dict[str, Any]:
    """Return deterministic metadata for local minimal fallbacks."""

    return {
        "fallback": True,
        "task_kind": task_kind,
        "provider": "local_minimal_output",
        "error_code": error_code or "OPENAI_UNKNOWN",
        "ui_message": ui_message,
    }


def _generate_structured_with_fallback(
    *,
    task_kind: str,
    messages: list[dict[str, str]],
    out_model: type[BaseModel],
    fallback_payload: dict[str, Any],
    model: str,
    store: bool,
    temperature: float | None,
) -> tuple[BaseModel, dict[str, Any]]:
    """Run structured generation and return deterministic fallback on failures."""

    runtime_config = _resolve_runtime_config(
        task_kind=task_kind,
        session_override=model,
    )
    prompt_limits = build_task_prompt_limits_suffix(
        max_bullets_per_field=runtime_config.task_max_bullets_per_field,
        max_sentences_per_field=runtime_config.task_max_sentences_per_field,
        max_output_tokens=runtime_config.task_max_output_tokens,
    )
    if prompt_limits and messages:
        messages[0]["content"] = f"{messages[0]['content']}{prompt_limits}"

    try:
        parsed, usage = _parse_with_structured_outputs(
            runtime_config=runtime_config,
            messages=messages,
            out_model=out_model,
            store=store,
            maybe_temperature=temperature,
        )
        return parsed, usage or {}
    except OpenAICallError as exc:
        fallback_model = out_model.model_validate(fallback_payload)
        record_fallback_model_used(
            st.session_state,
            task_kind=task_kind,
            requested_model=runtime_config.resolved_model,
            final_model="local_minimal_output",
            fallback_kind="local_minimal_output",
            error_code=exc.error_code,
        )
        return fallback_model, _build_task_fallback_usage(
            task_kind=task_kind,
            ui_message=exc.ui_message,
            error_code=exc.error_code,
        )
    except ValidationError as exc:
        mapped = _error_from_structured_output_exception(exc)
        fallback_model = out_model.model_validate(fallback_payload)
        record_fallback_model_used(
            st.session_state,
            task_kind=task_kind,
            requested_model=runtime_config.resolved_model,
            final_model="local_minimal_output",
            fallback_kind="local_minimal_output",
            error_code=mapped.error_code,
        )
        return fallback_model, _build_task_fallback_usage(
            task_kind=task_kind,
            ui_message=mapped.ui_message,
            error_code=mapped.error_code,
        )


def _artifact_context_block(
    *,
    generation_options: Mapping[str, Any] | None,
    change_request: str | None,
) -> str:
    options = dict(generation_options or {})
    request = (change_request or "").strip()
    if not options and not request:
        return ""
    return (
        "\n\nArtifact-Optionen (JSON):\n"
        f"{json.dumps(options, ensure_ascii=False, sort_keys=True, separators=(',', ':'))}\n\n"
        "Anpassungswunsch:\n"
        f"{request or 'Kein zusätzlicher Änderungswunsch.'}"
    )


def _option_text_list(
    options: Mapping[str, Any] | None, key: str, *, limit: int | None = None
) -> list[str]:
    raw_value = (options or {}).get(key)
    if not isinstance(raw_value, Sequence) or isinstance(raw_value, (str, bytes)):
        return []
    output: list[str] = []
    seen: set[str] = set()
    for item in raw_value:
        value = str(item).strip()
        dedupe_key = value.casefold()
        if not value or dedupe_key in seen:
            continue
        output.append(value)
        seen.add(dedupe_key)
        if limit is not None and len(output) >= limit:
            break
    return output


def _option_positive_int(
    options: Mapping[str, Any] | None,
    key: str,
    *,
    default: int,
    minimum: int,
    maximum: int,
) -> int:
    try:
        value = int((options or {}).get(key, default))
    except (TypeError, ValueError):
        value = default
    return max(minimum, min(maximum, value))


def _normalize_hm_interview_sheet(
    sheet: InterviewPrepSheetHiringManager,
    *,
    generation_options: Mapping[str, Any] | None,
) -> InterviewPrepSheetHiringManager:
    selected_competencies = _option_text_list(
        generation_options, "selected_competencies", limit=10
    )
    questions_per_block = _option_positive_int(
        generation_options,
        "questions_per_block",
        default=3,
        minimum=1,
        maximum=8,
    )
    debrief_question_count = _option_positive_int(
        generation_options,
        "debrief_question_count",
        default=3,
        minimum=1,
        maximum=8,
    )
    question_blocks = [
        block.model_copy(update={"questions": block.questions[:questions_per_block]})
        for block in sheet.question_blocks
    ]
    updates: dict[str, Any] = {
        "question_blocks": question_blocks,
        "debrief_questions": sheet.debrief_questions[:debrief_question_count],
    }
    if selected_competencies:
        updates["competencies_to_validate"] = selected_competencies
    return sheet.model_copy(update=updates)


def generate_interview_sheet_hr(
    *,
    brief: VacancyBrief,
    model: str,
    generation_options: Mapping[str, Any] | None = None,
    change_request: str | None = None,
    language: str = DEFAULT_LANGUAGE,
    store: bool = False,
    temperature: float | None = None,
) -> tuple[InterviewPrepSheetHR, dict[str, Any]]:
    """Generate recruiter-facing interview prep sheet with deterministic fallback."""

    role_title = brief.one_liner.strip() or "Rolle"
    system = (
        "Du bist ein Senior Talent Acquisition Partner. "
        "Erstelle ein strukturiertes HR-Interviewvorbereitungssheet mit klaren "
        "Fragen, fairer Bewertung und konsistenter Candidate Experience. "
        "Keine illegalen oder diskriminierenden Fragen (AGG-konform); "
        "stelle ausschließlich arbeitsplatzrelevante Fragen. "
        "Nutze ein strukturiertes Interviewformat mit objektiver Bewertungsrubrik "
        "und konsistenter Formulierung. "
        f"Sprache: {language}."
    )
    user = (
        "Nutze den Vacancy Brief als einzige Quelle und liefere ein vollständiges "
        "InterviewPrepSheetHR-Objekt.\n\n"
        "Vacancy Brief (JSON):\n"
        f"{json.dumps(brief.model_dump(mode='json'), ensure_ascii=False, sort_keys=True, separators=(',', ':'))}"
        f"{_artifact_context_block(generation_options=generation_options, change_request=change_request)}"
    )
    fallback_payload = {
        "role_title": role_title,
        "interview_stage": "HR Screen",
        "duration_minutes": 45,
        "opening_script": "Vielen Dank für Ihre Zeit. Ich führe strukturiert durch das Gespräch und beantworte zum Schluss Ihre Fragen.",
        "question_blocks": _fallback_core_question_blocks(brief),
        "knockout_criteria": [
            *[
                str(item).strip()
                for item in _brief_answer_list(brief, FactKey.SKILLS_KNOCKOUT_CRITERIA)
                if str(item).strip()
            ],
            "Muss-Kriterien aus dem Brief im Gespräch valide prüfen.",
        ],
        "candidate_experience_notes": [
            "Klaren Ablauf kommunizieren und Zeitrahmen einhalten."
        ],
        "evaluation_rubric": _fallback_rubric_from_scorecard(brief),
        "final_recommendation_options": _fallback_recommendation_options(brief),
    }
    parsed, usage = _generate_structured_with_fallback(
        task_kind=TASK_GENERATE_INTERVIEW_SHEET_HR,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        out_model=InterviewPrepSheetHR,
        fallback_payload=fallback_payload,
        model=model,
        store=store,
        temperature=temperature,
    )
    return cast(InterviewPrepSheetHR, parsed), usage


def generate_interview_sheet_hm(
    *,
    brief: VacancyBrief,
    model: str,
    generation_options: Mapping[str, Any] | None = None,
    change_request: str | None = None,
    language: str = DEFAULT_LANGUAGE,
    store: bool = False,
    temperature: float | None = None,
) -> tuple[InterviewPrepSheetHiringManager, dict[str, Any]]:
    """Generate hiring-manager interview prep sheet with deterministic fallback."""

    generation_options = dict(generation_options or {})
    selected_competencies = _option_text_list(
        generation_options, "selected_competencies", limit=10
    )
    questions_per_block = _option_positive_int(
        generation_options,
        "questions_per_block",
        default=3,
        minimum=1,
        maximum=8,
    )
    debrief_question_count = _option_positive_int(
        generation_options,
        "debrief_question_count",
        default=3,
        minimum=1,
        maximum=8,
    )
    role_title = brief.one_liner.strip() or "Rolle"
    system = (
        "Du bist ein erfahrener Hiring Manager Interview-Coach. "
        "Erstelle ein strukturiertes Vorbereitungssheet mit Fokus auf "
        "Kompetenzvalidierung, technische Tiefenprüfung und kalibrierte Bewertung. "
        "Nutze ein strukturiertes Interview mit klaren Frageblöcken und einer "
        "gewichteten, objektiven Bewertungsrubrik. "
        "Keine diskriminierenden, privaten oder nicht arbeitsplatzrelevanten Fragen "
        "(AGG-konform). "
        "Leite technical_deep_dive_topics direkt aus brief.must_have und "
        "brief.top_responsibilities ab. "
        "Beachte Artifact-Optionen strikt: stage, duration_minutes, focus, "
        "evaluation_depth, selected_competencies, questions_per_block und "
        "debrief_question_count steuern den Output. "
        "Wenn selected_competencies gesetzt ist, nutze genau diese Kompetenzen in "
        "competencies_to_validate. "
        f"Erzeuge pro Frageblock maximal {questions_per_block} Fragen und genau "
        f"{debrief_question_count} Debrief-Fragen, sofern fachlich sinnvoll. "
        f"Sprache: {language}."
    )
    user = (
        "Nutze den Vacancy Brief als einzige Quelle und liefere ein vollständiges "
        "InterviewPrepSheetHiringManager-Objekt.\n\n"
        "Vacancy Brief (JSON):\n"
        f"{json.dumps(brief.model_dump(mode='json'), ensure_ascii=False, sort_keys=True, separators=(',', ':'))}"
        f"{_artifact_context_block(generation_options=generation_options, change_request=change_request)}"
    )
    fallback_payload = {
        "role_title": role_title,
        "interview_stage": str(generation_options.get("stage") or "Fachinterview"),
        "duration_minutes": _option_positive_int(
            generation_options,
            "duration_minutes",
            default=60,
            minimum=15,
            maximum=240,
        ),
        "competencies_to_validate": selected_competencies or brief.must_have[:5],
        "question_blocks": _fallback_core_question_blocks(brief),
        "technical_deep_dive_topics": brief.top_responsibilities[:3],
        "case_or_task_prompt": "Bitte schildern Sie eine vergleichbare Aufgabe inklusive Ziel, Vorgehen und Ergebnis.",
        "evaluation_rubric": _fallback_rubric_from_scorecard(brief),
        "hiring_signal_summary": [
            "Belegbare Ergebnisse, klare Priorisierung, nachvollziehbare Entscheidungen."
        ],
        "debrief_questions": [
            "Welche evidenzbasierten Signale sprechen für/gegen eine Einstellung?"
        ],
    }
    parsed, usage = _generate_structured_with_fallback(
        task_kind=TASK_GENERATE_INTERVIEW_SHEET_HM,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        out_model=InterviewPrepSheetHiringManager,
        fallback_payload=fallback_payload,
        model=model,
        store=store,
        temperature=temperature,
    )
    sheet = _normalize_hm_interview_sheet(
        cast(InterviewPrepSheetHiringManager, parsed),
        generation_options=generation_options,
    )
    return sheet, usage


def generate_boolean_search_pack(
    *,
    brief: VacancyBrief,
    model: str,
    generation_options: Mapping[str, Any] | None = None,
    change_request: str | None = None,
    language: str = DEFAULT_LANGUAGE,
    store: bool = False,
    temperature: float | None = None,
) -> tuple[BooleanSearchPack, dict[str, Any]]:
    """Generate structured sourcing-ready boolean queries with safe fallback."""

    options = dict(generation_options or {})
    channels = _option_text_list(options, "channels", limit=3) or [
        "Google",
        "LinkedIn",
        "XING",
    ]
    operators = _option_text_list(options, "operators", limit=8) or [
        "AND",
        "OR",
        "NOT",
        '"..."',
        "(...)",
    ]
    try:
        keyword_count = int(options.get("keyword_count") or 8)
    except (TypeError, ValueError):
        keyword_count = 8
    keyword_count = max(3, min(keyword_count, 15))
    role_title = brief.one_liner.strip() or "Rolle"
    system = (
        "Du bist ein Senior Sourcing Specialist. "
        "Erzeuge strukturierte, kanalbezogene Boolean-Search-Varianten für "
        "Recruiting-Recherche ohne irrelevante Zusatztexte. "
        "Operatoren-Regeln strikt einhalten: "
        "LinkedIn nur mit großgeschriebenen AND/OR/NOT, keine Sondersyntax mit {*}[]<>, "
        "und kein Wildcard-Operator '*'. "
        "Google darf site:-Operatoren, Anführungszeichen und Minus-Operatoren für Ausschlüsse nutzen. "
        "XING nutzt AND/OR/NOT sowie Klammern und Anführungszeichen. "
        f"Nutze maximal {keyword_count} Schlagworte über Rolle, Skills, Seniorität und Standort hinweg. "
        f"Priorisierte Kanäle: {', '.join(channels)}. "
        f"Zugelassene Nutzer-Operatoren: {', '.join(operators)}. "
        "Verwende nur zugelassene Operatoren, soweit sie mit den jeweiligen Kanalregeln kompatibel sind. "
        "Fülle Fallback-Felder schema-kompatibel, optimiere aber Broad und Focused als sichtbare Varianten. "
        f"Sprache: {language}."
    )
    user = (
        "Nutze den Vacancy Brief als einzige Quelle und liefere ein vollständiges "
        "BooleanSearchPack-Objekt.\n\n"
        "Vacancy Brief (JSON):\n"
        f"{json.dumps(brief.model_dump(mode='json'), ensure_ascii=False, sort_keys=True, separators=(',', ':'))}"
        f"{_artifact_context_block(generation_options=generation_options, change_request=change_request)}"
    )
    must_have_terms = brief.must_have[:keyword_count]
    fallback_query = (
        " AND ".join(term for term in must_have_terms[:3] if term) or role_title
    )
    fallback_payload = {
        "role_title": role_title,
        "target_locations": [],
        "seniority_terms": [],
        "must_have_terms": must_have_terms,
        "exclusion_terms": [],
        "google": {
            "broad": [fallback_query],
            "focused": [fallback_query],
            "fallback": [role_title],
        },
        "linkedin": {
            "broad": [fallback_query],
            "focused": [fallback_query],
            "fallback": [role_title],
        },
        "xing": {
            "broad": [fallback_query],
            "focused": [fallback_query],
            "fallback": [role_title],
        },
        "channel_limitations": [
            "Kanal-Operatoren variieren; Query ggf. pro Plattform anpassen."
        ],
        "usage_notes": ["Mit breiter Variante starten und iterativ einschränken."],
    }
    parsed, usage = _generate_structured_with_fallback(
        task_kind=TASK_GENERATE_BOOLEAN_SEARCH,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        out_model=BooleanSearchPack,
        fallback_payload=fallback_payload,
        model=model,
        store=store,
        temperature=temperature,
    )
    return cast(BooleanSearchPack, parsed), usage


def generate_employment_contract_draft(
    *,
    brief: VacancyBrief,
    model: str,
    generation_options: Mapping[str, Any] | None = None,
    change_request: str | None = None,
    language: str = DEFAULT_LANGUAGE,
    store: bool = False,
    temperature: float | None = None,
) -> tuple[EmploymentContractDraft, dict[str, Any]]:
    """Generate a contract draft skeleton with deterministic local fallback."""

    role_title = brief.one_liner.strip() or "Rolle"
    system = (
        "Du bist ein HR-Operations Specialist. "
        "Erstelle einen strukturierten, exportfähigen Arbeitsvertragsentwurf "
        "als Vorlage und markiere fehlende Inputs klar. "
        "Dies ist ein Template-Draft, kein finaler Vertrag und keine Rechtsberatung. "
        "Nutze Platzhalter für Mitarbeiter-/Arbeitgeber-Namen und -Adressen "
        "(z. B. [EMPLOYEE_NAME], [EMPLOYER_ADDRESS]). "
        "Erfinde keine fehlenden Vertragsbedingungen; liste Unklarheiten ausschließlich in missing_inputs. "
        "Richte die Struktur an den wesentlichen Nachweisgesetz-Angaben (NachwG) "
        "und Basisaspekten zur Kündigungsfrist (§ 622 BGB) aus, aber formuliere generisch. "
        f"Sprache: {language}."
    )
    user = (
        "Nutze den Vacancy Brief als einzige Quelle und liefere ein vollständiges "
        "EmploymentContractDraft-Objekt.\n\n"
        "Vacancy Brief (JSON):\n"
        f"{json.dumps(brief.model_dump(mode='json'), ensure_ascii=False, sort_keys=True, separators=(',', ':'))}"
        f"{_artifact_context_block(generation_options=generation_options, change_request=change_request)}"
    )
    job_payload = _brief_job_payload(brief)
    answers = _brief_answers(brief)
    start_flexibility = _brief_answer_dict(brief, FactKey.TIMELINE_START_FLEXIBILITY)
    work_arrangement = str(
        answers.get(FactKey.COMPANY_WORK_ARRANGEMENT.value)
        or job_payload.get("place_of_work")
        or ""
    ).strip()
    fallback_payload = {
        "contract_language": language,
        "jurisdiction": str(job_payload.get("location_country") or "Nicht angegeben"),
        "role_title": role_title,
        "employment_type": str(
            answers.get(FactKey.ROLE_EMPLOYMENT_TYPE.value)
            or job_payload.get("employment_type")
            or "Vollzeit"
        ),
        "contract_type": str(
            answers.get(FactKey.ROLE_CONTRACT_TYPE.value)
            or job_payload.get("contract_type")
            or "Unbefristet"
        ),
        "start_date": str(
            start_flexibility.get("target_start")
            or job_payload.get("start_date")
            or ""
        )
        or None,
        "probation_period_months": None,
        "salary": _contract_fallback_salary(brief),
        "working_hours_per_week": None,
        "vacation_days_per_year": None,
        "place_of_work": work_arrangement or None,
        "notice_period": None,
        "clauses": _contract_fallback_clauses(brief),
        "signature_requirements": ["Vertrag vor Unterzeichnung rechtlich prüfen."],
        "missing_inputs": [
            item
            for item, present in (
                ("Jurisdiction", bool(job_payload.get("location_country"))),
                ("Salary", bool(_contract_fallback_salary(brief).get("min") or _contract_fallback_salary(brief).get("max"))),
                ("Start date", bool(start_flexibility.get("target_start") or job_payload.get("start_date"))),
            )
            if not present
        ],
    }
    parsed, usage = _generate_structured_with_fallback(
        task_kind=TASK_GENERATE_EMPLOYMENT_CONTRACT,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        out_model=EmploymentContractDraft,
        fallback_payload=fallback_payload,
        model=model,
        store=store,
        temperature=temperature,
    )
    return cast(EmploymentContractDraft, parsed), usage


def generate_requirement_gap_suggestions(
    *,
    job: JobAdExtract,
    answers: Dict[str, Any],
    existing_skills: list[str],
    existing_tasks: list[str],
    esco_skill_titles: list[str],
    target_skill_count: int,
    target_task_count: int,
    task_rag_context: list[dict[str, str]] | None = None,
    model: str,
    language: str = DEFAULT_LANGUAGE,
    store: bool = False,
    temperature: float | None = None,
) -> tuple[RequirementSuggestionPack, dict[str, Any]]:
    """Suggest missing but relevant skills/tasks using strict structured outputs."""

    runtime_config = _resolve_runtime_config(
        task_kind=TASK_GENERATE_REQUIREMENT_GAP_SUGGESTIONS,
        session_override=model,
    )
    task_limits_suffix = build_task_prompt_limits_suffix(
        max_bullets_per_field=runtime_config.task_max_bullets_per_field,
        max_sentences_per_field=runtime_config.task_max_sentences_per_field,
        max_output_tokens=runtime_config.task_max_output_tokens,
    )
    capped_skill_count = max(0, min(target_skill_count, 8))
    capped_task_count = max(0, min(target_task_count, 8))
    rag_context = task_rag_context or []
    source_hint_rule = (
        "Setze source_hint auf 'esco_rag', wenn evidence direkt durch ESCO-RAG-Kontext belegt ist; sonst 'llm'. "
        if rag_context
        else "Setze source_hint immer auf 'llm'. "
    )
    system = (
        "Du bist ein Senior Recruiting Analyst. "
        "Identifiziere fehlende, aber relevante Anforderungen für Skills und Aufgaben "
        "auf Basis von Jobspec, bisherigen Antworten und vorhandenen Listen. "
        "Liefere ausschließlich strukturierte Ausgabe entsprechend Schema. "
        "Keine Duplikate, keine bereits vorhandenen Einträge und maximal die geforderte Anzahl je Kategorie. "
        "Halte rationale und evidence jeweils kurz, präzise und belegbar aus dem Kontext. "
        f"{source_hint_rule}"
        f"Sprache: {language}."
        f"{task_limits_suffix}"
    )
    source_hint_user_rule = (
        "- source_hint 'esco_rag' nur bei klarer Belegstelle aus ESCO-RAG-Kontext, sonst 'llm'.\n"
        if rag_context
        else "- source_hint immer 'llm'.\n"
    )
    user = (
        "Erzeuge ein RequirementSuggestionPack.\n\n"
        f"Zielanzahl Skills: {capped_skill_count}\n"
        f"Zielanzahl Tasks: {capped_task_count}\n\n"
        "Regeln:\n"
        f"- Genau type='skill' für skills[] und type='task' für tasks[].\n"
        "- label als kurzer, konkreter Begriff.\n"
        "- importance nur high/medium/low.\n"
        f"{source_hint_user_rule}"
        "- Nur Vorschläge, die im Kontext fehlen.\n\n"
        "Jobspec-Extraktion (JSON):\n"
        f"{json.dumps(job.model_dump(mode='json'), ensure_ascii=False, sort_keys=True, separators=(',', ':'))}\n\n"
        "Manager-Antworten (JSON):\n"
        f"{json.dumps(answers, ensure_ascii=False, sort_keys=True, separators=(',', ':'))}\n\n"
        "Vorhandene Skills (JSON):\n"
        f"{json.dumps(existing_skills, ensure_ascii=False, sort_keys=True, separators=(',', ':'))}\n\n"
        "Vorhandene Tasks (JSON):\n"
        f"{json.dumps(existing_tasks, ensure_ascii=False, sort_keys=True, separators=(',', ':'))}\n\n"
        "ESCO Skill-Titel (JSON):\n"
        f"{json.dumps(esco_skill_titles, ensure_ascii=False, sort_keys=True, separators=(',', ':'))}\n\n"
        "ESCO RAG Task-Kontext (JSON):\n"
        f"{json.dumps(rag_context, ensure_ascii=False, sort_keys=True, separators=(',', ':'))}"
    )

    normalized_content = _canonicalize_for_cache(
        {
            "job": job.model_dump(mode="json"),
            "answers": answers,
            "existing_skills": existing_skills,
            "existing_tasks": existing_tasks,
            "esco_skill_titles": esco_skill_titles,
            "target_skill_count": capped_skill_count,
            "target_task_count": capped_task_count,
            "task_rag_context": rag_context,
        }
    )
    cache_key = _build_llm_cache_key(
        task_kind=TASK_GENERATE_REQUIREMENT_GAP_SUGGESTIONS,
        resolved_model=runtime_config.resolved_model,
        language=language,
        reasoning_effort=runtime_config.reasoning_effort,
        verbosity=runtime_config.verbosity,
        store=store,
        normalized_content=normalized_content,
        schema_version=VACANCY_SCHEMA_VERSION,
    )
    cache = _get_session_response_cache()
    cached_entry = cache.get(cache_key)
    if isinstance(cached_entry, dict):
        cached_result = cached_entry.get("result")
        if isinstance(cached_result, dict):
            try:
                parsed_cached = RequirementSuggestionPack.model_validate(cached_result)
            except ValidationError:
                _invalidate_cache_entry_for_validation_error(
                    cache=cache,
                    cache_key=cache_key,
                    task_kind=TASK_GENERATE_REQUIREMENT_GAP_SUGGESTIONS,
                    model_name=runtime_config.resolved_model,
                )
            else:
                return parsed_cached, _cached_usage(cache_key=cache_key)

    fallback_payload: dict[str, Any] = {"skills": [], "tasks": []}
    parsed, usage = _generate_structured_with_fallback(
        task_kind=TASK_GENERATE_REQUIREMENT_GAP_SUGGESTIONS,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        out_model=RequirementSuggestionPack,
        fallback_payload=fallback_payload,
        model=model,
        store=store,
        temperature=temperature,
    )
    result = cast(RequirementSuggestionPack, parsed)
    result.skills = result.skills[:capped_skill_count]
    result.tasks = result.tasks[:capped_task_count]
    cache[cache_key] = {"result": result.model_dump(mode="json")}
    return result, usage


def generate_benefit_suggestions(
    *,
    job: JobAdExtract,
    answers: Dict[str, Any],
    existing_benefits: list[str],
    target_benefit_count: int,
    model: str,
    language: str = DEFAULT_LANGUAGE,
    store: bool = False,
    temperature: float | None = None,
) -> tuple[BenefitSuggestionPack, dict[str, Any]]:
    """Suggest missing Benefits/Rahmenbedingungen using strict structured outputs."""

    runtime_config = _resolve_runtime_config(
        task_kind=TASK_GENERATE_BENEFIT_SUGGESTIONS,
        session_override=model,
    )
    task_limits_suffix = build_task_prompt_limits_suffix(
        max_bullets_per_field=runtime_config.task_max_bullets_per_field,
        max_sentences_per_field=runtime_config.task_max_sentences_per_field,
        max_output_tokens=runtime_config.task_max_output_tokens,
    )
    capped_benefit_count = max(0, min(target_benefit_count, 8))
    system = (
        "Du bist ein Senior Recruiting Analyst. "
        "Identifiziere fehlende oder noch unklare Benefits und Rahmenbedingungen "
        "für das Offer-Narrativ auf Basis von Jobspec und bisherigen Antworten. "
        "Liefere ausschließlich strukturierte Ausgabe entsprechend Schema. "
        "Keine Duplikate, keine bereits vorhandenen Einträge und maximal die geforderte Anzahl. "
        "Setze source_hint immer auf 'llm'. "
        "Halte rationale und evidence kurz, präzise und belegbar aus dem Kontext. "
        f"Sprache: {language}."
        f"{task_limits_suffix}"
    )
    user = (
        "Erzeuge ein BenefitSuggestionPack.\n\n"
        f"Zielanzahl Benefits: {capped_benefit_count}\n\n"
        "Regeln:\n"
        "- label als kurzer, konkreter Benefit- oder Rahmenbedingungsbegriff.\n"
        "- importance nur high/medium/low.\n"
        "- source_hint immer 'llm'.\n"
        "- Nur Vorschläge, die im Kontext fehlen oder als Klärpunkt sinnvoll sind.\n"
        "- Keine Gehaltszahlen erfinden.\n\n"
        "Jobspec-Extraktion (JSON):\n"
        f"{json.dumps(job.model_dump(mode='json'), ensure_ascii=False, sort_keys=True, separators=(',', ':'))}\n\n"
        "Manager-Antworten (JSON):\n"
        f"{json.dumps(answers, ensure_ascii=False, sort_keys=True, separators=(',', ':'))}\n\n"
        "Vorhandene Benefits (JSON):\n"
        f"{json.dumps(existing_benefits, ensure_ascii=False, sort_keys=True, separators=(',', ':'))}"
    )

    normalized_content = _canonicalize_for_cache(
        {
            "job": job.model_dump(mode="json"),
            "answers": answers,
            "existing_benefits": existing_benefits,
            "target_benefit_count": capped_benefit_count,
        }
    )
    cache_key = _build_llm_cache_key(
        task_kind=TASK_GENERATE_BENEFIT_SUGGESTIONS,
        resolved_model=runtime_config.resolved_model,
        language=language,
        reasoning_effort=runtime_config.reasoning_effort,
        verbosity=runtime_config.verbosity,
        store=store,
        normalized_content=normalized_content,
        schema_version=VACANCY_SCHEMA_VERSION,
    )
    cache = _get_session_response_cache()
    cached_entry = cache.get(cache_key)
    if isinstance(cached_entry, dict):
        cached_result = cached_entry.get("result")
        if isinstance(cached_result, dict):
            try:
                parsed_cached = BenefitSuggestionPack.model_validate(cached_result)
            except ValidationError:
                _invalidate_cache_entry_for_validation_error(
                    cache=cache,
                    cache_key=cache_key,
                    task_kind=TASK_GENERATE_BENEFIT_SUGGESTIONS,
                    model_name=runtime_config.resolved_model,
                )
            else:
                return parsed_cached, _cached_usage(cache_key=cache_key)

    parsed, usage = _generate_structured_with_fallback(
        task_kind=TASK_GENERATE_BENEFIT_SUGGESTIONS,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        out_model=BenefitSuggestionPack,
        fallback_payload={"benefits": []},
        model=model,
        store=store,
        temperature=temperature,
    )
    result = cast(BenefitSuggestionPack, parsed)
    result.benefits = result.benefits[:capped_benefit_count]
    cache[cache_key] = {"result": result.model_dump(mode="json")}
    return result, usage


def generate_role_tasks_salary_forecast(
    *,
    job_title: str,
    location_city: str,
    location_country: str,
    seniority: str,
    selected_tasks: list[str],
    search_radius_km: int,
    remote_share_percent: int,
    model: str,
    language: str = DEFAULT_LANGUAGE,
    store: bool = False,
    temperature: float | None = None,
) -> tuple[RoleTaskSalaryForecast, dict[str, Any]]:
    """Generate a concise EUR salary forecast for the Role & Tasks step."""

    runtime_config = _resolve_runtime_config(
        task_kind=TASK_GENERATE_ROLE_TASKS_SALARY_FORECAST,
        session_override=model,
    )
    task_limits_suffix = build_task_prompt_limits_suffix(
        max_bullets_per_field=runtime_config.task_max_bullets_per_field,
        max_sentences_per_field=runtime_config.task_max_sentences_per_field,
        max_output_tokens=runtime_config.task_max_output_tokens,
    )
    normalized_tasks = [task.strip() for task in selected_tasks if task.strip()]
    capped_tasks = normalized_tasks[:20]
    system = (
        "Du bist ein Recruiting Compensation Analyst. "
        "Erstelle eine schlichte, indikative Gehaltsprognose als Jahresbrutto in EUR. "
        "Berücksichtige Jobtitel, Seniorität/Erfahrung, Standort, Suchradius, Remote-Anteil "
        "und die ausgewählten Aufgaben. "
        "Liefere ausschließlich strukturierte Ausgabe gemäß Schema. "
        "Keine Währungsumrechnung in andere Währungen und keine rechtliche Beratung. "
        f"Sprache: {language}. "
        f"{task_limits_suffix}"
    )
    user = (
        "Erzeuge ein RoleTaskSalaryForecast-Objekt.\n\n"
        "Kontext:\n"
        f"- Jobtitel: {job_title or 'Nicht angegeben'}\n"
        f"- Seniorität/Erfahrung: {seniority or 'Nicht angegeben'}\n"
        f"- Standort (Stadt): {location_city or 'Nicht angegeben'}\n"
        f"- Standort (Land): {location_country or 'Nicht angegeben'}\n"
        f"- Suchradius (km): {max(0, search_radius_km)}\n"
        f"- Remote Share (%): {min(max(remote_share_percent, 0), 100)}\n"
        "- Ausgewählte Rollen/Aufgaben (JSON-Liste):\n"
        f"{json.dumps(capped_tasks, ensure_ascii=False, sort_keys=True, separators=(',', ':'))}\n\n"
        "Regeln:\n"
        "- yearly_salary_eur muss ein ganzzahliger EUR-Jahreswert sein.\n"
        "- confidence_note kurz halten (1-2 Sätze) und wichtigste Annahmen nennen."
    )
    normalized_content = _canonicalize_for_cache(
        {
            "job_title": job_title,
            "location_city": location_city,
            "location_country": location_country,
            "seniority": seniority,
            "selected_tasks": capped_tasks,
            "search_radius_km": max(0, search_radius_km),
            "remote_share_percent": min(max(remote_share_percent, 0), 100),
        }
    )
    cache_key = _build_llm_cache_key(
        task_kind=TASK_GENERATE_ROLE_TASKS_SALARY_FORECAST,
        resolved_model=runtime_config.resolved_model,
        language=language,
        reasoning_effort=runtime_config.reasoning_effort,
        verbosity=runtime_config.verbosity,
        store=store,
        normalized_content=normalized_content,
        schema_version=VACANCY_SCHEMA_VERSION,
    )
    cache = _get_session_response_cache()
    cached_entry = cache.get(cache_key)
    if isinstance(cached_entry, dict):
        cached_result = cached_entry.get("result")
        if isinstance(cached_result, dict):
            try:
                parsed_cached = RoleTaskSalaryForecast.model_validate(cached_result)
            except ValidationError:
                _invalidate_cache_entry_for_validation_error(
                    cache=cache,
                    cache_key=cache_key,
                    task_kind=TASK_GENERATE_ROLE_TASKS_SALARY_FORECAST,
                    model_name=runtime_config.resolved_model,
                )
            else:
                return parsed_cached, _cached_usage(cache_key=cache_key)

    fallback_payload = {
        "yearly_salary_eur": 70_000,
        "confidence_note": (
            "Indikative Schätzung mit begrenzter Datengrundlage. "
            "Bitte lokale Marktbenchmarks und Benefits ergänzend prüfen."
        ),
    }
    parsed, usage = _generate_structured_with_fallback(
        task_kind=TASK_GENERATE_ROLE_TASKS_SALARY_FORECAST,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        out_model=RoleTaskSalaryForecast,
        fallback_payload=fallback_payload,
        model=model,
        store=store,
        temperature=temperature,
    )
    result = cast(RoleTaskSalaryForecast, parsed)
    cache[cache_key] = {"result": result.model_dump(mode="json")}
    return result, usage
