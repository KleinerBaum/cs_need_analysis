"""Canonical step payload builder for wizard question UI surfaces."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypedDict, cast

from question_dependencies import should_show_question
from question_limits import (
    QuestionVisibilityPredicate,
    StepQuestionScope,
    build_step_question_scope,
)
from question_progress import (
    AnswerMetaMap,
    QuestionProgress,
    StepScopeProgressLabels,
    build_answered_lookup,
    build_step_scope_progress_labels,
    compute_question_progress,
)
from schemas import JobAdExtract, Question, QuestionStep
from state_store import StateStore
from step_status import StepStatusPayload, build_step_status_payload


class StepReviewPayload(TypedDict):
    visible_questions: list[Question]
    answers: dict[str, Any]
    answer_meta: AnswerMetaMap
    answered_lookup: dict[str, bool]
    step_status: StepStatusPayload
    job_extract: JobAdExtract | None
    intake_facts: dict[str, Any]
    intake_fact_evidence: dict[str, Any]
    confidence_threshold: float | None


class StepPayload(TypedDict):
    question_scope: StepQuestionScope
    selected_questions: list[Question]
    visible_questions: list[Question]
    hidden_questions_count: int
    dependency_hidden_questions_count: int
    adaptive_hidden_questions_count: int
    answers: dict[str, Any]
    answer_meta: AnswerMetaMap
    answered_lookup: dict[str, bool]
    selected_answered_lookup: dict[str, bool]
    visible_progress: QuestionProgress
    selected_progress: QuestionProgress
    scope_progress_labels: StepScopeProgressLabels
    step_status: StepStatusPayload
    review_payload: StepReviewPayload
    job_extract: JobAdExtract | None
    intake_facts: dict[str, Any]
    intake_fact_evidence: dict[str, Any]
    confidence_threshold: float | None


def load_job_extract_from_state(
    session_state: Mapping[str, Any] | None = None,
) -> JobAdExtract | None:
    return StateStore(session_state).job_extract()


def load_intake_facts_from_state(
    session_state: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    return StateStore(session_state).intake_facts()


def load_intake_fact_evidence_from_state(
    session_state: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    return StateStore(session_state).intake_fact_evidence()


def read_question_limits_from_state(
    session_state: Mapping[str, Any] | None = None,
) -> Mapping[str, Any] | None:
    return StateStore(session_state).question_limits()


def read_confidence_threshold_from_state(
    session_state: Mapping[str, Any] | None = None,
) -> float | None:
    return StateStore(session_state).confidence_threshold()


def build_step_payload(
    *,
    step: QuestionStep | None,
    answers: Mapping[str, Any],
    answer_meta: Mapping[str, Any],
    question_limits: Mapping[str, Any] | None,
    questions: list[Question] | None = None,
    job_extract: JobAdExtract | None = None,
    intake_facts: Mapping[str, Any] | None = None,
    intake_fact_evidence: Mapping[str, Any] | None = None,
    confidence_threshold: float | None = None,
    visibility_predicate: QuestionVisibilityPredicate = should_show_question,
    missing_essentials_max: int = 5,
) -> StepPayload:
    answers_dict = dict(answers)
    answer_meta_dict = cast(AnswerMetaMap, dict(answer_meta))
    intake_facts_dict = dict(intake_facts or {})
    intake_fact_evidence_dict = dict(intake_fact_evidence or {})
    if questions is not None:
        source_questions = list(questions)
    elif step is not None:
        source_questions = list(step.questions)
    else:
        source_questions = []

    if step is None:
        question_scope = StepQuestionScope(
            selected_questions=[],
            visible_questions=[],
            hidden_questions_count=0,
            dependency_hidden_questions_count=0,
            adaptive_hidden_questions_count=0,
        )
    else:
        question_scope = build_step_question_scope(
            source_questions,
            step_key=step.step_key,
            question_limits=question_limits,
            answers=answers_dict,
            answer_meta=answer_meta_dict,
            job_extract=job_extract,
            intake_facts=intake_facts_dict,
            intake_fact_evidence=intake_fact_evidence_dict,
            confidence_threshold=confidence_threshold,
            visibility_predicate=visibility_predicate,
        )

    selected_questions = question_scope.selected_questions
    visible_questions = question_scope.visible_questions
    answered_lookup = build_answered_lookup(
        visible_questions,
        answers_dict,
        answer_meta_dict,
        job_extract=job_extract,
        intake_facts=intake_facts_dict,
        intake_fact_evidence=intake_fact_evidence_dict,
        confidence_threshold=confidence_threshold,
    )
    selected_answered_lookup = build_answered_lookup(
        selected_questions,
        answers_dict,
        answer_meta_dict,
        job_extract=job_extract,
        intake_facts=intake_facts_dict,
        intake_fact_evidence=intake_fact_evidence_dict,
        confidence_threshold=confidence_threshold,
    )
    visible_progress = compute_question_progress(
        visible_questions,
        answers_dict,
        answer_meta_dict,
        answered_lookup=answered_lookup,
    )
    selected_progress = compute_question_progress(
        selected_questions,
        answers_dict,
        answer_meta_dict,
        answered_lookup=selected_answered_lookup,
    )
    scope_progress_labels = build_step_scope_progress_labels(
        visible_answered=visible_progress["answered"],
        visible_total=visible_progress["total"],
        overall_answered=selected_progress["answered"],
        overall_total=selected_progress["total"],
    )

    status_step = None
    if step is not None:
        status_step = QuestionStep(
            step_key=step.step_key,
            title_de=step.title_de,
            description_de=step.description_de,
            questions=selected_questions,
        )
    step_status = build_step_status_payload(
        step=status_step,
        answers=answers_dict,
        answer_meta=answer_meta_dict,
        should_show_question=visibility_predicate,
        step_key=step.step_key if step is not None else None,
        missing_essentials_max=missing_essentials_max,
        job_extract=job_extract,
        intake_facts=intake_facts_dict,
        intake_fact_evidence=intake_fact_evidence_dict,
        confidence_threshold=confidence_threshold,
        visible_questions=visible_questions,
        answered_lookup=answered_lookup,
    )
    review_payload: StepReviewPayload = {
        "visible_questions": visible_questions,
        "answers": answers_dict,
        "answer_meta": answer_meta_dict,
        "answered_lookup": answered_lookup,
        "step_status": step_status,
        "job_extract": job_extract,
        "intake_facts": intake_facts_dict,
        "intake_fact_evidence": intake_fact_evidence_dict,
        "confidence_threshold": confidence_threshold,
    }

    return {
        "question_scope": question_scope,
        "selected_questions": selected_questions,
        "visible_questions": visible_questions,
        "hidden_questions_count": question_scope.hidden_questions_count,
        "dependency_hidden_questions_count": (
            question_scope.dependency_hidden_questions_count
        ),
        "adaptive_hidden_questions_count": (
            question_scope.adaptive_hidden_questions_count
        ),
        "answers": answers_dict,
        "answer_meta": answer_meta_dict,
        "answered_lookup": answered_lookup,
        "selected_answered_lookup": selected_answered_lookup,
        "visible_progress": visible_progress,
        "selected_progress": selected_progress,
        "scope_progress_labels": scope_progress_labels,
        "step_status": step_status,
        "review_payload": review_payload,
        "job_extract": job_extract,
        "intake_facts": intake_facts_dict,
        "intake_fact_evidence": intake_fact_evidence_dict,
        "confidence_threshold": confidence_threshold,
    }


def build_step_payload_from_state(
    step: QuestionStep | None,
    *,
    questions: list[Question] | None = None,
    session_state: Mapping[str, Any] | None = None,
    answers: Mapping[str, Any] | None = None,
    answer_meta: Mapping[str, Any] | None = None,
    visibility_predicate: QuestionVisibilityPredicate = should_show_question,
) -> StepPayload:
    store = StateStore(session_state)
    return build_step_payload(
        step=step,
        questions=questions,
        answers=store.answers() if answers is None else answers,
        answer_meta=store.answer_meta() if answer_meta is None else answer_meta,
        question_limits=store.question_limits(),
        job_extract=store.job_extract(),
        intake_facts=store.intake_facts(),
        intake_fact_evidence=store.intake_fact_evidence(),
        confidence_threshold=store.confidence_threshold(),
        visibility_predicate=visibility_predicate,
    )
