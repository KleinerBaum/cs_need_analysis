"""Adaptive question-limit helpers for progressive intake depth."""

from __future__ import annotations

import math
import inspect
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any, cast

import streamlit as st

from constants import (
    SSKey,
    STEP_KEY_BENEFITS,
    STEP_KEY_COMPANY,
    STEP_KEY_INTERVIEW,
    STEP_KEY_ROLE_TASKS,
    STEP_KEY_SKILLS,
    UI_PREFERENCE_CONFIDENCE_THRESHOLD,
)
from question_dependencies import should_show_question
from question_progress import (
    AnswerMetaMap,
    build_answers_with_job_extract_coverage,
    is_answered,
    is_question_covered_by_job_extract,
)
from schemas import JobAdExtract, Question, QuestionPlan

QuestionVisibilityPredicate = Callable[..., bool]


@dataclass(frozen=True)
class ModeLimitProfile:
    missing_fraction: float
    min_questions: int
    context_buffer: int
    full_depth: bool = False


@dataclass(frozen=True)
class StepQuestionScope:
    selected_questions: list[Question]
    visible_questions: list[Question]
    hidden_questions_count: int


_MODE_LIMIT_PROFILES: dict[str, ModeLimitProfile] = {
    "quick": ModeLimitProfile(missing_fraction=0.45, min_questions=1, context_buffer=0),
    "standard": ModeLimitProfile(
        missing_fraction=0.7,
        min_questions=2,
        context_buffer=1,
    ),
    "expert": ModeLimitProfile(
        missing_fraction=1.0,
        min_questions=3,
        context_buffer=2,
        full_depth=True,
    ),
}

_STANDARD_STEP_FLOORS: dict[str, int] = {
    STEP_KEY_COMPANY: 5,
    STEP_KEY_ROLE_TASKS: 6,
    STEP_KEY_SKILLS: 5,
    STEP_KEY_BENEFITS: 4,
    STEP_KEY_INTERVIEW: 5,
}


def _resolve_mode_profile(ui_mode: str) -> ModeLimitProfile:
    normalized = str(ui_mode).strip().lower()
    return _MODE_LIMIT_PROFILES.get(normalized, _MODE_LIMIT_PROFILES["standard"])


def _question_is_covered(
    question: Question,
    *,
    answers: dict[str, Any],
    answer_meta: AnswerMetaMap,
    job_extract: JobAdExtract | None,
    intake_facts: Mapping[str, Any] | None,
    intake_fact_evidence: Mapping[str, Any] | None,
    confidence_threshold: float | None,
) -> bool:
    if is_answered(question, answers.get(question.id), answer_meta.get(question.id)):
        return True
    return is_question_covered_by_job_extract(
        question,
        job_extract,
        intake_facts=intake_facts,
        intake_fact_evidence=intake_fact_evidence,
        confidence_threshold=confidence_threshold,
    )


def _visibility_predicate_accepts_intake_facts(
    visibility_predicate: QuestionVisibilityPredicate,
) -> bool:
    try:
        signature = inspect.signature(visibility_predicate)
    except (TypeError, ValueError):
        return False
    return (
        "intake_facts" in signature.parameters
        or any(
            parameter.kind is inspect.Parameter.VAR_KEYWORD
            for parameter in signature.parameters.values()
        )
    )


def _call_visibility_predicate(
    visibility_predicate: QuestionVisibilityPredicate,
    accepts_intake_facts: bool,
    question: Question,
    answers: dict[str, Any],
    answer_meta: AnswerMetaMap,
    step_key: str,
    intake_facts: Mapping[str, Any] | None,
) -> bool:
    if accepts_intake_facts:
        return visibility_predicate(
            question,
            answers,
            answer_meta,
            step_key,
            intake_facts=intake_facts,
        )
    return visibility_predicate(question, answers, answer_meta, step_key)


def _filter_visible_questions(
    questions: list[Question],
    *,
    step_key: str,
    answers: dict[str, Any],
    answer_meta: AnswerMetaMap,
    job_extract: JobAdExtract | None,
    intake_facts: Mapping[str, Any] | None,
    intake_fact_evidence: Mapping[str, Any] | None,
    confidence_threshold: float | None,
    visibility_predicate: QuestionVisibilityPredicate,
) -> list[Question]:
    effective_answers = build_answers_with_job_extract_coverage(
        questions,
        answers,
        answer_meta,
        job_extract=job_extract,
        intake_facts=intake_facts,
        intake_fact_evidence=intake_fact_evidence,
        confidence_threshold=confidence_threshold,
    )
    accepts_intake_facts = _visibility_predicate_accepts_intake_facts(
        visibility_predicate
    )
    return [
        question
        for question in questions
        if _call_visibility_predicate(
            visibility_predicate,
            accepts_intake_facts,
            question,
            effective_answers,
            answer_meta,
            step_key,
            intake_facts,
        )
    ]


def _select_visible_questions_for_adaptive_limit(
    visible_questions: list[Question],
    *,
    limit: int | None,
    answers: dict[str, Any],
    answer_meta: AnswerMetaMap,
    job_extract: JobAdExtract | None,
    intake_facts: Mapping[str, Any] | None,
    intake_fact_evidence: Mapping[str, Any] | None,
    confidence_threshold: float | None,
) -> list[Question]:
    if limit is None or limit <= 0 or limit >= len(visible_questions):
        return visible_questions

    scored_questions = [
        (
            _question_limit_score(
                question,
                covered=_question_is_covered(
                    question,
                    answers=answers,
                    answer_meta=answer_meta,
                    job_extract=job_extract,
                    intake_facts=intake_facts,
                    intake_fact_evidence=intake_fact_evidence,
                    confidence_threshold=confidence_threshold,
                ),
            ),
            index,
            question,
        )
        for index, question in enumerate(visible_questions)
    ]
    selected_questions = sorted(
        scored_questions,
        key=lambda item: (-item[0], item[1]),
    )[:limit]
    return [question for _, _, question in selected_questions]


def select_questions_for_adaptive_limit(
    questions: list[Question],
    *,
    step_key: str,
    limit: int | None,
    answers: dict[str, Any],
    answer_meta: AnswerMetaMap,
    job_extract: JobAdExtract | None,
    intake_facts: Mapping[str, Any] | None = None,
    intake_fact_evidence: Mapping[str, Any] | None = None,
    confidence_threshold: float | None = None,
) -> list[Question]:
    """Return dependency-visible questions selected by adaptive need."""

    visible_questions = _resolve_visible_questions_for_limit(
        questions,
        step_key=step_key,
        answers=answers,
        answer_meta=answer_meta,
        job_extract=job_extract,
        intake_facts=intake_facts,
        intake_fact_evidence=intake_fact_evidence,
        confidence_threshold=confidence_threshold,
    )
    return _select_visible_questions_for_adaptive_limit(
        visible_questions,
        limit=limit,
        answers=answers,
        answer_meta=answer_meta,
        job_extract=job_extract,
        intake_facts=intake_facts,
        intake_fact_evidence=intake_fact_evidence,
        confidence_threshold=confidence_threshold,
    )


def build_step_question_scope(
    questions: list[Question],
    *,
    step_key: str,
    question_limits: Mapping[str, Any] | None,
    answers: dict[str, Any],
    answer_meta: AnswerMetaMap,
    job_extract: JobAdExtract | None,
    intake_facts: Mapping[str, Any] | None = None,
    intake_fact_evidence: Mapping[str, Any] | None = None,
    confidence_threshold: float | None = None,
    visibility_predicate: QuestionVisibilityPredicate = should_show_question,
) -> StepQuestionScope:
    """Return the adaptive selected scope and its dependency-visible questions."""

    visible_questions = _resolve_visible_questions_for_limit(
        questions,
        step_key=step_key,
        answers=answers,
        answer_meta=answer_meta,
        job_extract=job_extract,
        intake_facts=intake_facts,
        intake_fact_evidence=intake_fact_evidence,
        confidence_threshold=confidence_threshold,
        visibility_predicate=visibility_predicate,
    )
    step_limit = _read_step_limit(question_limits, step_key)
    if step_limit is None or step_limit <= 0:
        selected_questions = questions
        selected_visible_questions = visible_questions
    else:
        selected_visible_questions = _select_visible_questions_for_adaptive_limit(
            visible_questions,
            limit=step_limit,
            answers=answers,
            answer_meta=answer_meta,
            job_extract=job_extract,
            intake_facts=intake_facts,
            intake_fact_evidence=intake_fact_evidence,
            confidence_threshold=confidence_threshold,
        )
        selected_questions = selected_visible_questions

    return StepQuestionScope(
        selected_questions=selected_questions,
        visible_questions=selected_visible_questions,
        hidden_questions_count=len(selected_questions) - len(selected_visible_questions),
    )


def select_questions_for_step_scope(
    questions: list[Question],
    *,
    step_key: str,
    question_limits: Mapping[str, Any] | None,
    answers: dict[str, Any],
    answer_meta: AnswerMetaMap,
    job_extract: JobAdExtract | None,
    intake_facts: Mapping[str, Any] | None = None,
    intake_fact_evidence: Mapping[str, Any] | None = None,
    confidence_threshold: float | None = None,
) -> list[Question]:
    """Return the step question scope after applying the adaptive limit."""

    return build_step_question_scope(
        questions,
        step_key=step_key,
        question_limits=question_limits,
        answers=answers,
        answer_meta=answer_meta,
        job_extract=job_extract,
        intake_facts=intake_facts,
        intake_fact_evidence=intake_fact_evidence,
        confidence_threshold=confidence_threshold,
    ).selected_questions


def select_visible_questions_for_step_scope(
    questions: list[Question],
    *,
    step_key: str,
    question_limits: Mapping[str, Any] | None,
    answers: dict[str, Any],
    answer_meta: AnswerMetaMap,
    job_extract: JobAdExtract | None,
    intake_facts: Mapping[str, Any] | None = None,
    intake_fact_evidence: Mapping[str, Any] | None = None,
    confidence_threshold: float | None = None,
    visibility_predicate: QuestionVisibilityPredicate = should_show_question,
) -> list[Question]:
    """Return the dependency-visible questions in the adaptive step scope."""

    return build_step_question_scope(
        questions,
        step_key=step_key,
        question_limits=question_limits,
        answers=answers,
        answer_meta=answer_meta,
        job_extract=job_extract,
        intake_facts=intake_facts,
        intake_fact_evidence=intake_fact_evidence,
        confidence_threshold=confidence_threshold,
        visibility_predicate=visibility_predicate,
    ).visible_questions


def build_step_question_scope_from_plan(
    plan: QuestionPlan | None,
    step_key: str,
    *,
    question_limits: Mapping[str, Any] | None,
    answers: dict[str, Any],
    answer_meta: AnswerMetaMap,
    job_extract: JobAdExtract | None,
    intake_facts: Mapping[str, Any] | None = None,
    intake_fact_evidence: Mapping[str, Any] | None = None,
    confidence_threshold: float | None = None,
    visibility_predicate: QuestionVisibilityPredicate = should_show_question,
) -> StepQuestionScope:
    """Return a plan step's adaptive and visible question scope."""

    if plan is None:
        return StepQuestionScope(
            selected_questions=[],
            visible_questions=[],
            hidden_questions_count=0,
        )
    step = next((entry for entry in plan.steps if entry.step_key == step_key), None)
    if step is None:
        return StepQuestionScope(
            selected_questions=[],
            visible_questions=[],
            hidden_questions_count=0,
        )
    return build_step_question_scope(
        step.questions,
        step_key=step_key,
        question_limits=question_limits,
        answers=answers,
        answer_meta=answer_meta,
        job_extract=job_extract,
        intake_facts=intake_facts,
        intake_fact_evidence=intake_fact_evidence,
        confidence_threshold=confidence_threshold,
        visibility_predicate=visibility_predicate,
    )


def select_questions_for_step_scope_from_plan(
    plan: QuestionPlan | None,
    step_key: str,
    *,
    question_limits: Mapping[str, Any] | None,
    answers: dict[str, Any],
    answer_meta: AnswerMetaMap,
    job_extract: JobAdExtract | None,
    intake_facts: Mapping[str, Any] | None = None,
    intake_fact_evidence: Mapping[str, Any] | None = None,
    confidence_threshold: float | None = None,
) -> list[Question]:
    """Return a plan step's canonical adaptive question scope."""

    return build_step_question_scope_from_plan(
        plan,
        step_key=step_key,
        question_limits=question_limits,
        answers=answers,
        answer_meta=answer_meta,
        job_extract=job_extract,
        intake_facts=intake_facts,
        intake_fact_evidence=intake_fact_evidence,
        confidence_threshold=confidence_threshold,
    ).selected_questions


def select_visible_questions_for_step_scope_from_plan(
    plan: QuestionPlan | None,
    step_key: str,
    *,
    question_limits: Mapping[str, Any] | None,
    answers: dict[str, Any],
    answer_meta: AnswerMetaMap,
    job_extract: JobAdExtract | None,
    intake_facts: Mapping[str, Any] | None = None,
    intake_fact_evidence: Mapping[str, Any] | None = None,
    confidence_threshold: float | None = None,
    visibility_predicate: QuestionVisibilityPredicate = should_show_question,
) -> list[Question]:
    """Return a plan step's canonical visible adaptive question scope."""

    return build_step_question_scope_from_plan(
        plan,
        step_key=step_key,
        question_limits=question_limits,
        answers=answers,
        answer_meta=answer_meta,
        job_extract=job_extract,
        intake_facts=intake_facts,
        intake_fact_evidence=intake_fact_evidence,
        confidence_threshold=confidence_threshold,
        visibility_predicate=visibility_predicate,
    ).visible_questions


def compute_adaptive_question_limits(
    *,
    plan: QuestionPlan,
    ui_mode: str,
    answers: dict[str, Any],
    answer_meta: AnswerMetaMap,
    job_extract: JobAdExtract | None,
    intake_facts: Mapping[str, Any] | None = None,
    intake_fact_evidence: Mapping[str, Any] | None = None,
    confidence_threshold: float | None = None,
) -> dict[str, int]:
    profile = _resolve_mode_profile(ui_mode)
    limits: dict[str, int] = {}

    for step in plan.steps:
        if not step.questions:
            continue
        visible_questions = _resolve_visible_questions_for_limit(
            step.questions,
            step_key=step.step_key,
            answers=answers,
            answer_meta=answer_meta,
            job_extract=job_extract,
            intake_facts=intake_facts,
            intake_fact_evidence=intake_fact_evidence,
            confidence_threshold=confidence_threshold,
        )
        total = len(visible_questions)
        if total == 0:
            continue
        if profile.full_depth:
            limits[step.step_key] = total
            continue

        covered_by_question = {
            question.id: _question_is_covered(
                question,
                answers=answers,
                answer_meta=answer_meta,
                job_extract=job_extract,
                intake_facts=intake_facts,
                intake_fact_evidence=intake_fact_evidence,
                confidence_threshold=confidence_threshold,
            )
            for question in visible_questions
        }
        covered = sum(1 for is_covered in covered_by_question.values() if is_covered)
        missing = max(total - covered, 0)
        essential_missing = sum(
            1
            for question in visible_questions
            if not covered_by_question.get(question.id, False)
            and _question_is_adaptive_essential(question)
        )
        adaptive_count = math.ceil(missing * profile.missing_fraction)
        limit = max(
            profile.min_questions,
            _step_min_questions(ui_mode, step.step_key),
            adaptive_count + profile.context_buffer,
            essential_missing,
        )
        limits[step.step_key] = max(1, min(total, limit))

    return limits


def _read_step_limit(
    question_limits: Mapping[str, Any] | None,
    step_key: str,
) -> int | None:
    if not isinstance(question_limits, Mapping):
        return None
    raw_limit = question_limits.get(step_key)
    if not isinstance(raw_limit, (int, float, str)):
        return None
    try:
        return int(raw_limit)
    except (TypeError, ValueError):
        return None


def _step_min_questions(ui_mode: str, step_key: str) -> int:
    if str(ui_mode).strip().lower() != "standard":
        return 0
    return _STANDARD_STEP_FLOORS.get(step_key, 0)


def sync_adaptive_question_limits() -> None:
    plan_raw = st.session_state.get(SSKey.QUESTION_PLAN.value)
    if not isinstance(plan_raw, dict):
        return
    try:
        plan = QuestionPlan.model_validate(plan_raw)
    except Exception:
        return

    answers_raw = st.session_state.get(SSKey.ANSWERS.value, {})
    answers = answers_raw if isinstance(answers_raw, dict) else {}
    answer_meta_raw = st.session_state.get(SSKey.ANSWER_META.value, {})
    answer_meta: AnswerMetaMap = (
        cast(AnswerMetaMap, answer_meta_raw)
        if isinstance(answer_meta_raw, dict)
        else {}
    )
    ui_mode_raw = st.session_state.get(SSKey.UI_MODE.value, "standard")
    ui_mode = str(ui_mode_raw).strip().lower()

    job_extract_raw = st.session_state.get(SSKey.JOB_EXTRACT.value)
    job_extract: JobAdExtract | None = None
    if isinstance(job_extract_raw, dict):
        try:
            job_extract = JobAdExtract.model_validate(job_extract_raw)
        except Exception:
            job_extract = None

    st.session_state[SSKey.QUESTION_LIMITS.value] = compute_adaptive_question_limits(
        plan=plan,
        ui_mode=ui_mode,
        answers=answers,
        answer_meta=answer_meta,
        job_extract=job_extract,
        intake_facts=st.session_state.get(SSKey.INTAKE_FACTS.value),
        intake_fact_evidence=st.session_state.get(SSKey.INTAKE_FACT_EVIDENCE.value),
        confidence_threshold=_read_confidence_threshold(),
    )


def _read_confidence_threshold() -> float | None:
    preferences_raw = st.session_state.get(SSKey.UI_PREFERENCES.value, {})
    if not isinstance(preferences_raw, Mapping):
        return None
    try:
        return max(
            0.0,
            min(1.0, float(preferences_raw.get(UI_PREFERENCE_CONFIDENCE_THRESHOLD))),
        )
    except (TypeError, ValueError):
        return None


def _resolve_visible_questions_for_limit(
    questions: list[Question],
    *,
    step_key: str,
    answers: dict[str, Any],
    answer_meta: AnswerMetaMap,
    job_extract: JobAdExtract | None,
    intake_facts: Mapping[str, Any] | None,
    intake_fact_evidence: Mapping[str, Any] | None,
    confidence_threshold: float | None,
    visibility_predicate: QuestionVisibilityPredicate = should_show_question,
) -> list[Question]:
    return _filter_visible_questions(
        questions,
        step_key=step_key,
        answers=answers,
        answer_meta=answer_meta,
        job_extract=job_extract,
        intake_facts=intake_facts,
        intake_fact_evidence=intake_fact_evidence,
        confidence_threshold=confidence_threshold,
        visibility_predicate=visibility_predicate,
    )


def _question_limit_score(question: Question, *, covered: bool) -> int:
    priority_score = {"core": 30, "standard": 20, "detail": 10}.get(
        question.priority or "",
        20,
    )
    score = priority_score
    if not covered:
        score += 100
    else:
        score += 5
    if question.required:
        score += 40
    if question.depends_on:
        score += 15
    if _question_has_follow_up_prompts(question):
        score += 12
    score += _question_information_gain_score(question)
    return score


def _question_information_gain_score(question: Question) -> int:
    score = 0
    try:
        explicit_score = getattr(question, "info_gain_score", None)
        if explicit_score is not None:
            score += int(max(0.0, min(1.0, float(explicit_score))) * 30)
    except (TypeError, ValueError):
        pass

    impact_targets = getattr(question, "impact_targets", [])
    if isinstance(impact_targets, list):
        normalized_targets = {
            str(target).strip().casefold()
            for target in impact_targets
            if str(target).strip()
        }
        score += min(24, len(normalized_targets) * 6)

    acquisition_cost = str(getattr(question, "acquisition_cost", "medium") or "medium")
    score += {"low": 8, "medium": 4, "high": 0}.get(acquisition_cost, 4)
    return score


def _question_is_adaptive_essential(question: Question) -> bool:
    return (
        bool(question.required)
        or question.priority == "core"
        or bool(question.depends_on)
        or _question_has_follow_up_prompts(question)
        or _question_information_gain_score(question) >= 24
    )


def _question_has_follow_up_prompts(question: Question) -> bool:
    prompts = getattr(question, "follow_up_prompts", None)
    return isinstance(prompts, list) and any(
        isinstance(prompt, str) and bool(prompt.strip()) for prompt in prompts
    )
