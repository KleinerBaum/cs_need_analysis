"""Shared step status payload builder for wizard UI surfaces."""

from __future__ import annotations

import inspect
from collections.abc import Callable, Mapping
from typing import Any, Literal, TypedDict

from question_progress import (
    AnswerMetaMap,
    build_answers_with_job_extract_coverage,
    build_answered_lookup,
    compute_question_progress,
)
from schemas import JobAdExtract, Question, QuestionStep

CompletionState = Literal["not_started", "partial", "complete"]
QuestionVisibilityPredicate = Callable[
    [Question, dict[str, Any], AnswerMetaMap, str],
    bool,
]


class StepStatusPayload(TypedDict):
    answered: int
    total: int
    completion_state: CompletionState
    essentials_answered: int
    essentials_total: int
    missing_essentials: list[str]
    missing_essential_ids: list[str]


def _is_essential_question(question: Question) -> bool:
    return question.priority == "core" or question.required


def _should_show_question_accepts_intake_facts(
    should_show_question: QuestionVisibilityPredicate,
) -> bool:
    try:
        signature = inspect.signature(should_show_question)
    except (TypeError, ValueError):
        return False
    return (
        "intake_facts" in signature.parameters
        or any(
            parameter.kind is inspect.Parameter.VAR_KEYWORD
            for parameter in signature.parameters.values()
        )
    )


def _call_should_show_question(
    should_show_question: QuestionVisibilityPredicate,
    accepts_intake_facts: bool,
    question: Question,
    answers: dict[str, Any],
    answer_meta: AnswerMetaMap,
    step_key: str,
    intake_facts: Mapping[str, Any] | None,
) -> bool:
    if accepts_intake_facts:
        return should_show_question(
            question,
            answers,
            answer_meta,
            step_key,
            intake_facts=intake_facts,
        )
    return should_show_question(question, answers, answer_meta, step_key)


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
        }

    effective_answers = build_answers_with_job_extract_coverage(
        step.questions,
        answers_dict,
        answer_meta,
        job_extract=job_extract,
        intake_facts=intake_facts,
    )
    accepts_intake_facts = _should_show_question_accepts_intake_facts(
        should_show_question
    )
    visible_questions = [
        question
        for question in step.questions
        if _call_should_show_question(
            should_show_question,
            accepts_intake_facts,
            question,
            effective_answers,
            answer_meta,
            resolved_step_key,
            intake_facts,
        )
    ]
    answered_lookup = build_answered_lookup(
        visible_questions,
        answers_dict,
        answer_meta,
        job_extract=job_extract,
        intake_facts=intake_facts,
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

    return {
        "answered": progress["answered"],
        "total": progress["total"],
        "completion_state": completion_state,
        "essentials_answered": essentials_progress["answered"],
        "essentials_total": essentials_progress["total"],
        "missing_essentials": missing_essentials,
        "missing_essential_ids": missing_essential_ids,
    }
