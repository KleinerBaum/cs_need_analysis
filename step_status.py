"""Shared step status payload builder for wizard UI surfaces."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Literal, TypedDict

from constants import STEP_SECTION_OPEN_QUESTIONS
from question_limits import (
    QuestionVisibilityPredicate,
    select_visible_questions_for_step_scope,
)
from question_progress import (
    AnswerMetaMap,
    build_answered_lookup,
    compute_question_progress,
)
from schemas import JobAdExtract, Question, QuestionStep
from step_sections import question_canonical_fact_key

CompletionState = Literal["not_started", "partial", "complete"]


class MissingEssentialTarget(TypedDict):
    target_step: str
    target_section: str
    target_fact_key: str
    target_question_id: str
    label: str


class StepStatusPayload(TypedDict):
    answered: int
    total: int
    completion_state: CompletionState
    essentials_answered: int
    essentials_total: int
    missing_essentials: list[str]
    missing_essential_ids: list[str]
    missing_essential_targets: list[MissingEssentialTarget]


def _is_essential_question(question: Question) -> bool:
    return question.priority == "core" or question.required


def _missing_essential_target(
    question: Question,
    *,
    step_key: str,
) -> MissingEssentialTarget:
    fact_key = question_canonical_fact_key(question)
    return {
        "target_step": step_key,
        "target_section": STEP_SECTION_OPEN_QUESTIONS,
        "target_fact_key": fact_key.value if fact_key is not None else "",
        "target_question_id": question.id,
        "label": question.label,
    }


def build_step_status_payload(
    *,
    step: QuestionStep | None,
    answers: Mapping[str, Any],
    answer_meta: AnswerMetaMap,
    should_show_question: QuestionVisibilityPredicate,
    step_key: str | None = None,
    missing_essentials_max: int = 5,
    job_extract: JobAdExtract | None = None,
    intake_facts: Mapping[str, Any] | None = None,
    intake_fact_evidence: Mapping[str, Any] | None = None,
    confidence_threshold: float | None = None,
    visible_questions: list[Question] | None = None,
    answered_lookup: dict[str, bool] | None = None,
) -> StepStatusPayload:
    answers_dict = dict(answers)
    resolved_step_key = step_key or (step.step_key if step is not None else "")

    if step is None or not step.questions:
        return {
            "answered": 0,
            "total": 0,
            "completion_state": "not_started",
            "essentials_answered": 0,
            "essentials_total": 0,
            "missing_essentials": [],
            "missing_essential_ids": [],
            "missing_essential_targets": [],
        }

    if visible_questions is None:
        visible_questions = select_visible_questions_for_step_scope(
            step.questions,
            step_key=resolved_step_key,
            question_limits=None,
            answers=answers_dict,
            answer_meta=answer_meta,
            job_extract=job_extract,
            intake_facts=intake_facts,
            intake_fact_evidence=intake_fact_evidence,
            confidence_threshold=confidence_threshold,
            visibility_predicate=should_show_question,
        )
    if answered_lookup is None:
        answered_lookup = build_answered_lookup(
            visible_questions,
            answers_dict,
            answer_meta,
            job_extract=job_extract,
            intake_facts=intake_facts,
            intake_fact_evidence=intake_fact_evidence,
            confidence_threshold=confidence_threshold,
        )
    progress = compute_question_progress(
        visible_questions,
        answers_dict,
        answer_meta,
        answered_lookup=answered_lookup,
    )

    essential_questions = [
        question for question in visible_questions if _is_essential_question(question)
    ]
    essentials_progress = compute_question_progress(
        essential_questions,
        answers_dict,
        answer_meta,
        answered_lookup=answered_lookup,
    )

    completion_state: CompletionState = "not_started"
    if progress["total"] > 0:
        if progress["answered"] == progress["total"]:
            completion_state = "complete"
        elif progress["answered"] > 0:
            completion_state = "partial"

    missing_essential_questions = [
        question
        for question in essential_questions
        if not answered_lookup.get(question.id, False)
    ][:missing_essentials_max]
    missing_essential_ids = [question.id for question in missing_essential_questions]
    missing_essentials = [question.label for question in missing_essential_questions]
    missing_essential_targets = [
        _missing_essential_target(question, step_key=resolved_step_key)
        for question in missing_essential_questions
    ]

    return {
        "answered": progress["answered"],
        "total": progress["total"],
        "completion_state": completion_state,
        "essentials_answered": essentials_progress["answered"],
        "essentials_total": essentials_progress["total"],
        "missing_essentials": missing_essentials,
        "missing_essential_ids": missing_essential_ids,
        "missing_essential_targets": missing_essential_targets,
    }
