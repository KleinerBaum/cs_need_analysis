"""Helpers for question-level UX progress state."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from typing import Any, Literal, TypedDict

from constants import AnswerType, FactKey
from schemas import JobAdExtract, Question
from step_sections import (
    fact_evidence_allows_coverage,
    has_meaningful_fact_value,
    question_candidate_fact_keys,
)

WizardUIMode = Literal["quick", "standard", "expert"]

SINGLE_SELECT_PLACEHOLDERS = frozenset({"", "— Bitte wählen —"})
_JOB_EXTRACT_FIELDS = frozenset(JobAdExtract.model_fields)
_LOW_CONFIDENCE_FACT = object()

_JOB_EXTRACT_ALIAS_RULES: tuple[tuple[tuple[str, ...], tuple[str, ...]], ...] = (
    (
        ("company_name",),
        (
            "company_name",
            "company name",
            "employer name",
            "arbeitgebername",
            "firmenname",
            "name der firma",
            "unternehmensname",
            "wie heisst das unternehmen",
            "wie heist das unternehmen",
            "wie heißt das unternehmen",
        ),
    ),
    (
        ("company_website",),
        (
            "company_website",
            "company website",
            "homepage",
            "website",
            "karriereseite",
            "career site",
            "url",
        ),
    ),
    (
        ("brand_name",),
        (
            "brand_name",
            "brand name",
            "marke",
            "arbeitgebermarke",
        ),
    ),
    (
        ("location_city",),
        (
            "location_city",
            "location city",
            "stadt",
            "standort der firma",
            "ort der firma",
            "in welcher stadt",
        ),
    ),
    (
        ("location_country",),
        (
            "location_country",
            "location country",
            "country",
            "land",
            "in welchem land",
        ),
    ),
    (
        ("place_of_work", "location_city"),
        (
            "place_of_work",
            "place of work",
            "arbeitsort",
            "einsatzort",
        ),
    ),
    (
        ("remote_policy",),
        (
            "remote_policy",
            "remote policy",
            "remote-regelung",
            "remote regelung",
            "hybrid",
            "mobiles arbeiten",
        ),
    ),
    (
        ("employment_type", "contract_type"),
        (
            "employment_type",
            "employment type",
            "beschaeftigungsart",
            "beschäftigungsart",
            "anstellungsart",
            "arbeitsvertrag",
            "art des arbeitsvertrags",
            "vertragsart",
            "contract_type",
            "contract type",
        ),
    ),
)


class AnswerMeta(TypedDict, total=False):
    touched: bool
    confirmed: bool
    last_value_hash: str


AnswerMetaMap = dict[str, AnswerMeta]


class QuestionProgress(TypedDict):
    total: int
    answered: int
    required_unanswered: int


class StepScopeProgressLabels(TypedDict):
    visible_label: str
    overall_label: str
    has_different_denominator: bool


def build_step_scope_progress_labels(
    *,
    visible_answered: int,
    visible_total: int,
    overall_answered: int,
    overall_total: int,
) -> StepScopeProgressLabels:
    """Build explicit UX labels for visible vs. overall step progress scopes."""

    has_different_denominator = visible_total != overall_total
    return {
        "visible_label": (
            f"Sichtbar im aktuellen Umfang: {visible_answered}/{visible_total}"
        ),
        "overall_label": (
            "Gesamt im Step (inkl. derzeit ausgeblendeter Details): "
            f"{overall_answered}/{overall_total}"
        ),
        "has_different_denominator": has_different_denominator,
    }


def build_answered_lookup(
    questions: list[Question],
    answers: dict[str, Any],
    answer_meta: AnswerMetaMap,
    *,
    job_extract: JobAdExtract | None = None,
    intake_facts: Mapping[str, Any] | None = None,
    intake_fact_evidence: Mapping[str, Any] | None = None,
    confidence_threshold: float | None = None,
) -> dict[str, bool]:
    """Return a per-question answered lookup for reuse across render sections."""

    return {
        question.id: is_answered(
            question,
            answers.get(question.id),
            answer_meta.get(question.id),
        )
        or is_question_covered_by_job_extract(
            question,
            job_extract,
            intake_facts=intake_facts,
            intake_fact_evidence=intake_fact_evidence,
            confidence_threshold=confidence_threshold,
        )
        for question in questions
    }


def value_hash(value: Any) -> str:
    """Return a deterministic hash for arbitrary JSON-like values."""

    payload = json.dumps(value, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def is_answered(question: Question, value: Any, meta: AnswerMeta | None) -> bool:
    """Type-aware answered evaluation with meta-aware handling for defaults."""

    metadata = meta or {}
    touched = bool(metadata.get("touched", False))
    confirmed = bool(metadata.get("confirmed", False))

    if question.answer_type in (AnswerType.SHORT_TEXT, AnswerType.LONG_TEXT):
        return isinstance(value, str) and bool(value.strip())

    if question.answer_type == AnswerType.MULTI_SELECT:
        return isinstance(value, list) and len(value) > 0

    if question.answer_type == AnswerType.SINGLE_SELECT:
        if value is None:
            return False
        normalized = str(value).strip()
        return normalized not in SINGLE_SELECT_PLACEHOLDERS

    if question.answer_type in (AnswerType.BOOLEAN, AnswerType.NUMBER):
        return touched or confirmed

    if question.answer_type == AnswerType.DATE:
        if value is None:
            return False
        return bool(str(value).strip())

    return value is not None


def build_answers_with_job_extract_coverage(
    questions: list[Question],
    answers: dict[str, Any],
    answer_meta: AnswerMetaMap,
    *,
    job_extract: JobAdExtract | None = None,
    intake_facts: Mapping[str, Any] | None = None,
    intake_fact_evidence: Mapping[str, Any] | None = None,
    confidence_threshold: float | None = None,
) -> dict[str, Any]:
    """Return answers plus inferred extract values for dependency evaluation only."""

    if job_extract is None and not intake_facts:
        return dict(answers)

    effective_answers = dict(answers)
    for question in questions:
        if is_answered(
            question,
            effective_answers.get(question.id),
            answer_meta.get(question.id),
        ):
            continue
        extracted_value = resolve_question_job_extract_value(
            question,
            job_extract,
            intake_facts=intake_facts,
            intake_fact_evidence=intake_fact_evidence,
            confidence_threshold=confidence_threshold,
        )
        if _has_meaningful_extract_value(extracted_value):
            effective_answers[question.id] = extracted_value
    return effective_answers


def is_question_covered_by_job_extract(
    question: Question,
    job_extract: JobAdExtract | None,
    *,
    intake_facts: Mapping[str, Any] | None = None,
    intake_fact_evidence: Mapping[str, Any] | None = None,
    confidence_threshold: float | None = None,
) -> bool:
    return _has_meaningful_extract_value(
        resolve_question_job_extract_value(
            question,
            job_extract,
            intake_facts=intake_facts,
            intake_fact_evidence=intake_fact_evidence,
            confidence_threshold=confidence_threshold,
        )
    )


def resolve_question_job_extract_value(
    question: Question,
    job_extract: JobAdExtract | None,
    *,
    intake_facts: Mapping[str, Any] | None = None,
    intake_fact_evidence: Mapping[str, Any] | None = None,
    confidence_threshold: float | None = None,
) -> Any:
    """Resolve a question to a canonical JobAdExtract value when possible."""

    fact_value = _resolve_question_intake_fact_value(
        question,
        intake_facts,
        intake_fact_evidence=intake_fact_evidence,
        confidence_threshold=confidence_threshold,
    )
    if fact_value is _LOW_CONFIDENCE_FACT:
        return None
    if _has_meaningful_extract_value(fact_value):
        return fact_value

    if job_extract is None:
        return None

    target_path = question.target_path or ""
    target_value = extract_job_extract_value_by_path(job_extract, target_path)
    if _has_meaningful_extract_value(target_value):
        return target_value

    for raw_key in (question.id, target_path):
        tail = _normalize_path_tail(raw_key)
        if tail in _JOB_EXTRACT_FIELDS:
            field_value = extract_job_extract_value_by_path(job_extract, tail)
            if _has_meaningful_extract_value(field_value):
                return field_value

    search_text = _question_search_text(question)
    for candidate_fields, aliases in _JOB_EXTRACT_ALIAS_RULES:
        if not any(alias in search_text for alias in aliases):
            continue
        for field in candidate_fields:
            field_value = extract_job_extract_value_by_path(job_extract, field)
            if _has_meaningful_extract_value(field_value):
                return field_value
    return None


def _resolve_question_intake_fact_value(
    question: Question,
    intake_facts: Mapping[str, Any] | None,
    *,
    intake_fact_evidence: Mapping[str, Any] | None = None,
    confidence_threshold: float | None = None,
) -> Any:
    if not isinstance(intake_facts, Mapping):
        return None

    for fact_key in _candidate_question_fact_keys(question):
        value = intake_facts.get(fact_key.value)
        if _has_meaningful_extract_value(value):
            if not _fact_evidence_allows_coverage(
                fact_key,
                intake_fact_evidence=intake_fact_evidence,
                confidence_threshold=confidence_threshold,
            ):
                return _LOW_CONFIDENCE_FACT
            return value
    return None


def _fact_evidence_allows_coverage(
    fact_key: FactKey,
    *,
    intake_fact_evidence: Mapping[str, Any] | None,
    confidence_threshold: float | None,
) -> bool:
    return fact_evidence_allows_coverage(
        fact_key,
        intake_fact_evidence=intake_fact_evidence,
        confidence_threshold=confidence_threshold,
    )


def _candidate_question_fact_keys(question: Question) -> tuple[FactKey, ...]:
    return question_candidate_fact_keys(question)


def extract_job_extract_value_by_path(
    job_extract: JobAdExtract | None,
    target_path: str,
) -> Any:
    """Read a value from JobAdExtract for canonical field paths only."""

    if job_extract is None or not isinstance(target_path, str):
        return None

    segments = [segment for segment in target_path.strip().split(".") if segment]
    if not segments:
        return None
    if segments[0] in {"job", "job_extract"}:
        segments = segments[1:]
    if not segments or segments[0] == "answers":
        return None
    if segments[0] not in _JOB_EXTRACT_FIELDS:
        return None

    current: Any = job_extract.model_dump(mode="json")
    for segment in segments:
        if not isinstance(current, dict) or segment not in current:
            return None
        current = current.get(segment)
    return current


def _has_meaningful_extract_value(value: Any) -> bool:
    return has_meaningful_fact_value(value)


def _normalize_path_tail(value: str | None) -> str:
    if not isinstance(value, str):
        return ""
    return value.strip().split(".")[-1].strip()


def _question_search_text(question: Question) -> str:
    raw = " ".join(
        str(part or "")
        for part in (
            question.id,
            question.label,
            question.help,
            question.rationale,
            question.target_path,
            question.group_key,
        )
    ).casefold()
    normalized = (
        raw.replace("ä", "ae")
        .replace("ö", "oe")
        .replace("ü", "ue")
        .replace("ß", "ss")
    )
    return re.sub(r"[^a-z0-9_]+", " ", normalized)


def compute_question_progress(
    questions: list[Question],
    answers: dict[str, Any],
    answer_meta: AnswerMetaMap,
    answered_lookup: dict[str, bool] | None = None,
    *,
    job_extract: JobAdExtract | None = None,
    intake_facts: Mapping[str, Any] | None = None,
    intake_fact_evidence: Mapping[str, Any] | None = None,
    confidence_threshold: float | None = None,
) -> QuestionProgress:
    """Compute answered/total and open required counts for a question list."""

    total = len(questions)
    answered = 0
    required_unanswered = 0

    for question in questions:
        question_answered = (
            answered_lookup[question.id]
            if answered_lookup is not None and question.id in answered_lookup
            else is_answered(
                question,
                answers.get(question.id),
                answer_meta.get(question.id),
            )
            or is_question_covered_by_job_extract(
                question,
                job_extract,
                intake_facts=intake_facts,
                intake_fact_evidence=intake_fact_evidence,
                confidence_threshold=confidence_threshold,
            )
        )
        if question_answered:
            answered += 1
        elif question.required:
            required_unanswered += 1

    return {
        "total": total,
        "answered": answered,
        "required_unanswered": required_unanswered,
    }
