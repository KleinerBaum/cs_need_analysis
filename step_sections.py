"""Central registry for ordered wizard step sections and fact ownership."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any, Literal, TypedDict

from constants import (
    INTAKE_FACTS,
    FactKey,
    FactResolutionStatus,
    STEP_KEY_COMPANY,
    STEP_KEY_BENEFITS,
    STEP_KEY_INTERVIEW,
    STEP_KEY_ROLE_TASKS,
    STEP_KEY_SKILLS,
    STEP_SECTION_EXTRACTED_FROM_JOBSPEC,
    STEP_SECTION_LABELS_DE,
    STEP_SECTION_OPEN_QUESTIONS,
    STEP_SECTION_REVIEW,
    STEP_SECTION_SALARY_FORECAST,
    STEP_SECTION_SLOT_NAMES,
    STEP_SECTION_SOURCE_COMPARISON,
)
from intake_facts import latest_fact_confidence
from schemas import Question, QuestionStep

StepSectionRenderer = Callable[[], None]
SectionCompletionRule = Literal["none", "any_fact", "all_facts"]


@dataclass(frozen=True)
class StepSectionDef:
    step_key: str
    section_id: str
    slot_name: str
    title_de: str
    shell_heading_de: str | None = None
    fact_keys: tuple[FactKey, ...] = ()
    completion_rule: SectionCompletionRule = "none"
    render_priority: int = 0
    open_question_fallback: bool = True
    duplicate_exempt_question_ids: frozenset[str] = frozenset()


class SectionStatusPayload(TypedDict):
    step_key: str
    section_id: str
    title_de: str
    answered: int
    total: int
    completion_state: str
    missing_fact_keys: list[str]
    missing_labels: list[str]


_VALID_FACT_KEYS = frozenset(fact.fact_key for fact in INTAKE_FACTS)
_FACT_LABELS = {fact.fact_key: fact.label for fact in INTAKE_FACTS}
_FACT_JOB_EXTRACT_FIELDS: dict[FactKey, str] = {
    FactKey.COMPANY_COMPANY_NAME: "company_name",
    FactKey.COMPANY_COMPANY_WEBSITE: "company_website",
    FactKey.COMPANY_BRAND_NAME: "brand_name",
    FactKey.COMPANY_LOCATION_CITY: "location_city",
    FactKey.COMPANY_LOCATION_COUNTRY: "location_country",
    FactKey.COMPANY_PLACE_OF_WORK: "place_of_work",
    FactKey.COMPANY_REMOTE_POLICY: "remote_policy",
    FactKey.ROLE_JOB_TITLE: "job_title",
    FactKey.ROLE_EMPLOYMENT_TYPE: "employment_type",
    FactKey.ROLE_CONTRACT_TYPE: "contract_type",
    FactKey.ROLE_RESPONSIBILITIES: "responsibilities",
    FactKey.ROLE_SUCCESS_METRICS: "success_metrics",
    FactKey.SKILLS_MUST_HAVE_SKILLS: "must_have_skills",
    FactKey.SKILLS_NICE_TO_HAVE_SKILLS: "nice_to_have_skills",
    FactKey.SKILLS_LANGUAGES: "languages",
    FactKey.BENEFITS_SALARY_RANGE: "salary_range",
    FactKey.BENEFITS_BENEFITS: "benefits",
    FactKey.INTERVIEW_RECRUITMENT_STEPS: "recruitment_steps",
    FactKey.INTERVIEW_CONTACTS: "contacts",
}
_JOB_EXTRACT_FIELD_FACTS = {
    field_name: fact_key for fact_key, field_name in _FACT_JOB_EXTRACT_FIELDS.items()
}

_COMPANY_CONTEXT_FACT_KEYS: tuple[FactKey, ...] = (
    FactKey.COMPANY_EMPLOYER_PITCH,
    FactKey.COMPANY_BUSINESS_UNIT,
    FactKey.COMPANY_ROLE_RELEVANT_POSITIONING,
    FactKey.COMPANY_HIRING_REASON,
    FactKey.COMPANY_GROWTH_CONTEXT,
    FactKey.COMPANY_ROLE_BUSINESS_IMPACT,
    FactKey.COMPANY_COMPANY_NAME,
    FactKey.COMPANY_BRAND_NAME,
    FactKey.COMPANY_COMPANY_WEBSITE,
    FactKey.COMPANY_LOCATION_CITY,
    FactKey.COMPANY_LOCATION_COUNTRY,
    FactKey.COMPANY_PLACE_OF_WORK,
    FactKey.COMPANY_REMOTE_POLICY,
    FactKey.COMPANY_WORK_ARRANGEMENT,
    FactKey.COMPANY_OFFICE_DAYS_PER_WEEK,
    FactKey.COMPANY_ALLOWED_REGIONS_TIMEZONES,
    FactKey.COMPANY_LANGUAGE_INTERNAL,
    FactKey.COMPANY_LANGUAGE_EXTERNAL,
    FactKey.COMPANY_NON_NEGOTIABLES,
    FactKey.COMPANY_COMPLIANCE_CONTEXT,
    FactKey.COMPANY_TARIFF_CONTEXT,
)
_TEAM_CONTEXT_FACT_KEYS: tuple[FactKey, ...] = (
    FactKey.COMPANY_DEPARTMENT_NAME,
    FactKey.COMPANY_REPORTS_TO,
    FactKey.COMPANY_DIRECT_REPORTS_COUNT,
    FactKey.TEAM_NAME,
    FactKey.TEAM_LEADERSHIP_SCOPE,
    FactKey.TEAM_SIZE_DIRECT,
    FactKey.TEAM_STAKEHOLDERS_PRIMARY,
    FactKey.TEAM_SUCCESS_CONTEXT_90D,
)
_COMPANY_STRUCTURED_FACT_KEYS: tuple[FactKey, ...] = (
    *_COMPANY_CONTEXT_FACT_KEYS,
    *_TEAM_CONTEXT_FACT_KEYS,
)
_WORK_CONTEXT_FACT_KEYS: tuple[FactKey, ...] = (
    FactKey.COMPANY_LOCATION_CITY,
    FactKey.COMPANY_LOCATION_COUNTRY,
    FactKey.COMPANY_PLACE_OF_WORK,
    FactKey.COMPANY_REMOTE_POLICY,
    FactKey.COMPANY_WORK_ARRANGEMENT,
    FactKey.COMPANY_OFFICE_DAYS_PER_WEEK,
    FactKey.COMPANY_ALLOWED_REGIONS_TIMEZONES,
    FactKey.COMPANY_LANGUAGE_INTERNAL,
    FactKey.COMPANY_LANGUAGE_EXTERNAL,
    FactKey.COMPANY_NON_NEGOTIABLES,
    FactKey.COMPANY_COMPLIANCE_CONTEXT,
    FactKey.COMPANY_TARIFF_CONTEXT,
)
_ROLE_TASKS_FACT_KEYS: tuple[FactKey, ...] = (
    FactKey.ROLE_JOB_TITLE,
    FactKey.ROLE_EMPLOYMENT_TYPE,
    FactKey.ROLE_CONTRACT_TYPE,
    FactKey.ROLE_SENIORITY_LEVEL,
    FactKey.ROLE_JOB_REF_NUMBER,
    FactKey.ROLE_ROLE_OVERVIEW,
    FactKey.ROLE_RESPONSIBILITIES,
    FactKey.ROLE_RESPONSIBILITIES_PRIORITIZED,
    FactKey.ROLE_DELIVERABLES,
    FactKey.ROLE_SUCCESS_METRICS,
    FactKey.ROLE_SUCCESS_METRICS_TIMELINE,
    FactKey.ROLE_BUSINESS_OUTCOME_PRIMARY,
    FactKey.ROLE_DAY1_RESPONSIBILITIES,
    FactKey.ROLE_EXPANSION_SCOPE,
    FactKey.ROLE_DECISION_SCOPE,
    FactKey.ROLE_YEAR1_SUCCESS_SIGNALS,
    FactKey.ROLE_TECH_STACK,
    FactKey.ROLE_DOMAIN_EXPERTISE,
    FactKey.ROLE_TRAVEL_REQUIRED,
    FactKey.ROLE_TRAVEL_PROFILE,
    FactKey.ROLE_ON_CALL,
    FactKey.ROLE_ONBOARDING_NOTES,
    FactKey.ROLE_GAPS,
    FactKey.ROLE_ASSUMPTIONS,
)
_SKILLS_FACT_KEYS: tuple[FactKey, ...] = (
    FactKey.SKILLS_ITEMS,
    FactKey.SKILLS_MUST_HAVE_SKILLS,
    FactKey.SKILLS_NICE_TO_HAVE_SKILLS,
    FactKey.SKILLS_SOFT_SKILLS,
    FactKey.SKILLS_EDUCATION,
    FactKey.SKILLS_CERTIFICATIONS,
    FactKey.SKILLS_LANGUAGES,
    FactKey.SKILLS_READINESS_TIMING,
    FactKey.SKILLS_FREE_TEXT_REASON,
    FactKey.SKILLS_KNOCKOUT_CRITERIA,
    FactKey.SKILLS_TRAINABLE_SKILLS,
)
_BENEFITS_FACT_KEYS: tuple[FactKey, ...] = (
    FactKey.BENEFITS_SALARY_RANGE,
    FactKey.BENEFITS_VARIABLE_PAY,
    FactKey.BENEFITS_BENEFITS,
    FactKey.BENEFITS_SHIFT_COMPENSATION,
    FactKey.BENEFITS_COLLECTIVE_AGREEMENT_CONTEXT,
    FactKey.BENEFITS_OFFER_COMPONENTS,
    FactKey.LEGAL_WORK_AUTHORIZATION_SUPPORT,
    FactKey.TIMELINE_START_FLEXIBILITY,
)
_INTERVIEW_FACT_KEYS: tuple[FactKey, ...] = (
    FactKey.INTERVIEW_START_DATE,
    FactKey.INTERVIEW_APPLICATION_DEADLINE,
    FactKey.INTERVIEW_RECRUITMENT_STEPS,
    FactKey.INTERVIEW_CONTACTS,
    FactKey.INTERVIEW_ASSESSMENT_EVIDENCE,
    FactKey.INTERVIEW_STAGE_OWNERS,
    FactKey.INTERVIEW_COMMUNICATION_SLA,
    FactKey.INTERVIEW_SCORECARD_TEMPLATE,
    FactKey.INTERVIEW_CORE_QUESTIONS,
    FactKey.INTERVIEW_COMPLIANCE_NOTES,
)

_COMPANY_DISTINCT_FOLLOW_UP_QUESTION_IDS = frozenset(
    {
        "ctx_confidential_external_narrative",
    }
)


def _section(
    step_key: str,
    section_id: str,
    *,
    shell_heading_de: str | None = None,
    fact_keys: tuple[FactKey, ...] = (),
    completion_rule: SectionCompletionRule = "none",
    render_priority: int = 0,
    open_question_fallback: bool = True,
    duplicate_exempt_question_ids: frozenset[str] = frozenset(),
) -> StepSectionDef:
    return StepSectionDef(
        step_key=step_key,
        section_id=section_id,
        slot_name=STEP_SECTION_SLOT_NAMES[section_id],
        title_de=STEP_SECTION_LABELS_DE[section_id],
        shell_heading_de=shell_heading_de,
        fact_keys=fact_keys,
        completion_rule=completion_rule,
        render_priority=render_priority,
        open_question_fallback=open_question_fallback,
        duplicate_exempt_question_ids=duplicate_exempt_question_ids,
    )


_COMPANY_STEP_SECTIONS: tuple[StepSectionDef, ...] = (
    _section(
        STEP_KEY_COMPANY,
        STEP_SECTION_OPEN_QUESTIONS,
        shell_heading_de="Kontext bearbeiten",
        fact_keys=_COMPANY_STRUCTURED_FACT_KEYS,
        completion_rule="any_fact",
        render_priority=10,
        open_question_fallback=False,
        duplicate_exempt_question_ids=_COMPANY_DISTINCT_FOLLOW_UP_QUESTION_IDS,
    ),
    _section(
        STEP_KEY_COMPANY,
        STEP_SECTION_EXTRACTED_FROM_JOBSPEC,
        shell_heading_de="",
        fact_keys=(
            FactKey.COMPANY_COMPANY_NAME,
            FactKey.COMPANY_BRAND_NAME,
            FactKey.COMPANY_COMPANY_WEBSITE,
            FactKey.COMPANY_LOCATION_CITY,
            FactKey.COMPANY_LOCATION_COUNTRY,
            FactKey.COMPANY_DEPARTMENT_NAME,
            FactKey.COMPANY_REPORTS_TO,
            FactKey.COMPANY_DIRECT_REPORTS_COUNT,
        ),
        completion_rule="any_fact",
        render_priority=20,
    ),
    _section(STEP_KEY_COMPANY, STEP_SECTION_SOURCE_COMPARISON, render_priority=30),
    _section(STEP_KEY_COMPANY, STEP_SECTION_REVIEW, render_priority=40),
)

_INTERVIEW_STEP_SECTIONS: tuple[StepSectionDef, ...] = (
    _section(
        STEP_KEY_INTERVIEW,
        STEP_SECTION_SOURCE_COMPARISON,
        shell_heading_de="Interviewprozess planen",
        fact_keys=_INTERVIEW_FACT_KEYS,
        completion_rule="any_fact",
        render_priority=10,
        open_question_fallback=False,
    ),
    _section(
        STEP_KEY_INTERVIEW,
        STEP_SECTION_EXTRACTED_FROM_JOBSPEC,
        shell_heading_de="Identifizierte Interview-Werte",
        fact_keys=(FactKey.INTERVIEW_RECRUITMENT_STEPS, FactKey.INTERVIEW_CONTACTS),
        completion_rule="any_fact",
        render_priority=20,
    ),
    _section(STEP_KEY_INTERVIEW, STEP_SECTION_OPEN_QUESTIONS, render_priority=30),
    _section(STEP_KEY_INTERVIEW, STEP_SECTION_REVIEW, render_priority=40),
)

_ROLE_TASKS_STEP_SECTIONS: tuple[StepSectionDef, ...] = (
    _section(
        STEP_KEY_ROLE_TASKS,
        STEP_SECTION_SOURCE_COMPARISON,
        fact_keys=(*_ROLE_TASKS_FACT_KEYS, *_WORK_CONTEXT_FACT_KEYS),
        completion_rule="any_fact",
        render_priority=10,
        open_question_fallback=False,
    ),
    _section(
        STEP_KEY_ROLE_TASKS,
        STEP_SECTION_EXTRACTED_FROM_JOBSPEC,
        fact_keys=(
            FactKey.ROLE_JOB_TITLE,
            FactKey.ROLE_RESPONSIBILITIES,
            FactKey.ROLE_DELIVERABLES,
            FactKey.ROLE_SUCCESS_METRICS,
        ),
        completion_rule="any_fact",
        render_priority=20,
    ),
    _section(STEP_KEY_ROLE_TASKS, STEP_SECTION_SALARY_FORECAST, render_priority=30),
    _section(STEP_KEY_ROLE_TASKS, STEP_SECTION_OPEN_QUESTIONS, render_priority=40),
    _section(STEP_KEY_ROLE_TASKS, STEP_SECTION_REVIEW, render_priority=50),
)

_SKILLS_STEP_SECTIONS: tuple[StepSectionDef, ...] = (
    _section(
        STEP_KEY_SKILLS,
        STEP_SECTION_SOURCE_COMPARISON,
        shell_heading_de="Skill-Liste bauen",
        fact_keys=_SKILLS_FACT_KEYS,
        completion_rule="any_fact",
        render_priority=10,
        open_question_fallback=False,
    ),
    _section(
        STEP_KEY_SKILLS,
        STEP_SECTION_EXTRACTED_FROM_JOBSPEC,
        fact_keys=(
            FactKey.SKILLS_MUST_HAVE_SKILLS,
            FactKey.SKILLS_NICE_TO_HAVE_SKILLS,
            FactKey.SKILLS_LANGUAGES,
            FactKey.SKILLS_CERTIFICATIONS,
        ),
        completion_rule="any_fact",
        render_priority=20,
    ),
    _section(STEP_KEY_SKILLS, STEP_SECTION_SALARY_FORECAST, render_priority=30),
    _section(STEP_KEY_SKILLS, STEP_SECTION_OPEN_QUESTIONS, render_priority=40),
    _section(STEP_KEY_SKILLS, STEP_SECTION_REVIEW, render_priority=50),
)

_BENEFITS_STEP_SECTIONS: tuple[StepSectionDef, ...] = (
    _section(
        STEP_KEY_BENEFITS,
        STEP_SECTION_SOURCE_COMPARISON,
        shell_heading_de="Angebot bearbeiten",
        fact_keys=_BENEFITS_FACT_KEYS,
        completion_rule="any_fact",
        render_priority=10,
        open_question_fallback=False,
    ),
    _section(
        STEP_KEY_BENEFITS,
        STEP_SECTION_EXTRACTED_FROM_JOBSPEC,
        fact_keys=(FactKey.BENEFITS_SALARY_RANGE, FactKey.BENEFITS_BENEFITS),
        completion_rule="any_fact",
        render_priority=20,
    ),
    _section(STEP_KEY_BENEFITS, STEP_SECTION_SALARY_FORECAST, render_priority=30),
    _section(STEP_KEY_BENEFITS, STEP_SECTION_OPEN_QUESTIONS, render_priority=40),
    _section(STEP_KEY_BENEFITS, STEP_SECTION_REVIEW, render_priority=50),
)

_STEP_SECTION_REGISTRY: dict[str, tuple[StepSectionDef, ...]] = {
    STEP_KEY_COMPANY: _COMPANY_STEP_SECTIONS,
    STEP_KEY_ROLE_TASKS: _ROLE_TASKS_STEP_SECTIONS,
    STEP_KEY_SKILLS: _SKILLS_STEP_SECTIONS,
    STEP_KEY_BENEFITS: _BENEFITS_STEP_SECTIONS,
    STEP_KEY_INTERVIEW: _INTERVIEW_STEP_SECTIONS,
}


def get_step_sections(step_key: str) -> tuple[StepSectionDef, ...]:
    """Return the ordered section definitions for a wizard step."""
    return _STEP_SECTION_REGISTRY.get(step_key, ())


def get_section_fact_keys(step_key: str, section_id: str) -> tuple[FactKey, ...]:
    """Return FactKeys owned by one registered step section."""
    for section in get_step_sections(step_key):
        if section.section_id == section_id:
            return section.fact_keys
    return ()


def get_step_fact_keys(step_key: str) -> tuple[FactKey, ...]:
    """Return all registered FactKeys for a step, preserving first-seen order."""
    fact_keys: list[FactKey] = []
    for section in get_step_sections(step_key):
        for fact_key in section.fact_keys:
            if fact_key not in fact_keys:
                fact_keys.append(fact_key)
    return tuple(fact_keys)


def get_step_structured_fact_keys(step_key: str) -> frozenset[FactKey]:
    """Return FactKeys owned by structured sections rather than open questions."""
    fact_keys: set[FactKey] = set()
    for section in get_step_sections(step_key):
        if section.open_question_fallback:
            continue
        fact_keys.update(section.fact_keys)
    return frozenset(fact_keys)


def get_step_duplicate_exempt_question_ids(step_key: str) -> frozenset[str]:
    """Return question IDs that should stay visible despite FactKey ownership."""
    question_ids: set[str] = set()
    for section in get_step_sections(step_key):
        question_ids.update(section.duplicate_exempt_question_ids)
    return frozenset(question_ids)


def question_candidate_fact_keys(question: Question | Any) -> tuple[FactKey, ...]:
    """Resolve all canonical FactKey candidates for a question."""
    candidates: list[FactKey] = []
    for raw_key in (
        getattr(question, "fact_key", None),
        getattr(question, "target_path", None),
        _normalize_path_tail(getattr(question, "target_path", None)),
        getattr(question, "id", None),
        _normalize_path_tail(getattr(question, "id", None)),
    ):
        fact_key = _coerce_fact_key(raw_key)
        if fact_key is None:
            fact_key = _JOB_EXTRACT_FIELD_FACTS.get(str(raw_key or "").strip())
        if fact_key is None or fact_key in candidates:
            continue
        candidates.append(fact_key)
    return tuple(candidates)


def question_canonical_fact_key(question: Question | Any) -> FactKey | None:
    """Return the primary canonical FactKey for a question, if any."""
    candidates = question_candidate_fact_keys(question)
    return candidates[0] if candidates else None


def has_meaningful_fact_value(value: Any) -> bool:
    """Return whether a fact payload carries user-meaningful content."""
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, Mapping):
        return any(has_meaningful_fact_value(item) for item in value.values())
    if isinstance(value, (list, tuple, set)):
        return any(has_meaningful_fact_value(item) for item in value)
    return True


def fact_evidence_allows_coverage(
    fact_key: FactKey,
    *,
    intake_fact_evidence: Mapping[str, Any] | None = None,
    confidence_threshold: float | None = None,
) -> bool:
    """Return whether evidence is strong enough to hide a matching open question."""
    if isinstance(intake_fact_evidence, Mapping):
        evidence_raw = intake_fact_evidence.get(fact_key.value)
        evidence = evidence_raw if isinstance(evidence_raw, Mapping) else {}
        if evidence.get("resolution_status") == FactResolutionStatus.CONFLICTED.value:
            return False
    threshold = _normalize_confidence_threshold(confidence_threshold)
    if threshold is None or not isinstance(intake_fact_evidence, Mapping):
        return True
    confidence = latest_fact_confidence(fact_key, intake_fact_evidence)
    if confidence is None:
        return True
    return confidence >= threshold


def is_fact_covered(
    fact_key: FactKey,
    *,
    intake_facts: Mapping[str, Any] | None = None,
    intake_fact_evidence: Mapping[str, Any] | None = None,
    confidence_threshold: float | None = None,
) -> bool:
    """Return whether a canonical fact has sufficient value/evidence coverage."""
    if not isinstance(intake_facts, Mapping):
        return False
    if not has_meaningful_fact_value(intake_facts.get(fact_key.value)):
        return False
    return fact_evidence_allows_coverage(
        fact_key,
        intake_fact_evidence=intake_fact_evidence,
        confidence_threshold=confidence_threshold,
    )


def should_show_open_question(
    question: Question,
    *,
    step_key: str,
    intake_facts: Mapping[str, Any] | None = None,
    intake_fact_evidence: Mapping[str, Any] | None = None,
    confidence_threshold: float | None = None,
) -> bool:
    """Return whether an open question should be rendered for a step."""
    question_id = str(getattr(question, "id", "") or "").strip()
    if question_id in get_step_duplicate_exempt_question_ids(step_key):
        return True
    fact_keys = question_candidate_fact_keys(question)
    if not fact_keys:
        return True
    structured_fact_keys = get_step_structured_fact_keys(step_key)
    if any(fact_key in structured_fact_keys for fact_key in fact_keys):
        return False
    return not any(
        is_fact_covered(
            fact_key,
            intake_facts=intake_facts,
            intake_fact_evidence=intake_fact_evidence,
            confidence_threshold=confidence_threshold,
        )
        for fact_key in fact_keys
    )


def filter_open_questions_for_step(
    step: QuestionStep | None,
    *,
    step_key: str | None = None,
    intake_facts: Mapping[str, Any] | None = None,
    intake_fact_evidence: Mapping[str, Any] | None = None,
    confidence_threshold: float | None = None,
) -> QuestionStep | None:
    """Return a QuestionStep with semantic duplicates removed for open-question UI."""
    if step is None:
        return None
    questions = list(getattr(step, "questions", []) or [])
    if not questions:
        return None
    resolved_step_key = step_key or step.step_key
    filtered_questions = [
        question
        for question in questions
        if should_show_open_question(
            question,
            step_key=resolved_step_key,
            intake_facts=intake_facts,
            intake_fact_evidence=intake_fact_evidence,
            confidence_threshold=confidence_threshold,
        )
    ]
    if not filtered_questions:
        return None
    if len(filtered_questions) == len(questions):
        return step
    return QuestionStep(
        step_key=step.step_key,
        title_de=step.title_de,
        description_de=step.description_de,
        questions=filtered_questions,
    )


def build_section_status_payloads(
    *,
    step_key: str,
    intake_facts: Mapping[str, Any] | None = None,
    intake_fact_evidence: Mapping[str, Any] | None = None,
    confidence_threshold: float | None = None,
) -> list[SectionStatusPayload]:
    """Build fact-based completion payloads for registered sections."""
    payloads: list[SectionStatusPayload] = []
    for section in get_step_sections(step_key):
        fact_keys = tuple(dict.fromkeys(section.fact_keys))
        if section.completion_rule == "none" or not fact_keys:
            continue
        covered_keys = [
            fact_key
            for fact_key in fact_keys
            if is_fact_covered(
                fact_key,
                intake_facts=intake_facts,
                intake_fact_evidence=intake_fact_evidence,
                confidence_threshold=confidence_threshold,
            )
        ]
        missing_keys = [fact_key for fact_key in fact_keys if fact_key not in covered_keys]
        completion_state = "not_started"
        if fact_keys:
            if section.completion_rule == "any_fact":
                completion_state = "complete" if covered_keys else "not_started"
            elif len(covered_keys) == len(fact_keys):
                completion_state = "complete"
            elif covered_keys:
                completion_state = "partial"
        payloads.append(
            {
                "step_key": step_key,
                "section_id": section.section_id,
                "title_de": section.title_de,
                "answered": len(covered_keys),
                "total": len(fact_keys),
                "completion_state": completion_state,
                "missing_fact_keys": [fact_key.value for fact_key in missing_keys],
                "missing_labels": [
                    _FACT_LABELS.get(fact_key, fact_key.value)
                    for fact_key in missing_keys
                ],
            }
        )
    return payloads


def section_status_summary(
    section_statuses: list[SectionStatusPayload],
) -> tuple[int, int]:
    """Return complete/total section counts for display surfaces."""
    relevant_statuses = [
        status for status in section_statuses if int(status.get("total", 0)) > 0
    ]
    complete = sum(
        1
        for status in relevant_statuses
        if status.get("completion_state") == "complete"
    )
    return complete, len(relevant_statuses)


def build_step_shell_section_kwargs(
    *,
    step_key: str,
    renderers: Mapping[str, StepSectionRenderer],
) -> dict[str, Any]:
    """Build ordered ``render_step_shell`` kwargs from registered sections."""
    shell_kwargs: dict[str, Any] = {}
    sections = get_step_sections(step_key)
    if sections:
        shell_kwargs["section_order"] = [section.slot_name for section in sections]
    for section in sections:
        renderer = renderers.get(section.section_id)
        if renderer is None:
            continue
        shell_kwargs[section.slot_name] = renderer
        if section.section_id == STEP_SECTION_EXTRACTED_FROM_JOBSPEC:
            shell_kwargs["extracted_from_jobspec_label"] = (
                section.shell_heading_de
                if section.shell_heading_de is not None
                else section.title_de
            )
    return shell_kwargs


def _coerce_fact_key(raw_key: Any) -> FactKey | None:
    if not isinstance(raw_key, str):
        return None
    try:
        fact_key = FactKey(raw_key.strip())
    except ValueError:
        return None
    return fact_key if fact_key in _VALID_FACT_KEYS else None


def _normalize_path_tail(value: str | None) -> str:
    if not isinstance(value, str):
        return ""
    return value.strip().split(".")[-1].strip()


def _normalize_confidence_threshold(raw_threshold: float | None) -> float | None:
    if raw_threshold is None:
        return None
    try:
        return max(0.0, min(1.0, float(raw_threshold)))
    except (TypeError, ValueError):
        return None
