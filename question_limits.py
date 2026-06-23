"""Adaptive question-limit helpers for progressive intake depth."""

from __future__ import annotations

import inspect
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from math import ceil
from typing import Any, cast

import streamlit as st

from constants import (
    QUESTION_LIMIT_SCOPE_META_KEY,
    SSKey,
    UI_MODE_PRIORITY_TIERS,
    UI_MODE_QUESTION_LIMIT_RATIOS,
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
class StepQuestionScope:
    selected_questions: list[Question]
    visible_questions: list[Question]
    hidden_questions_count: int
    dependency_hidden_questions_count: int
    adaptive_hidden_questions_count: int


@dataclass(frozen=True)
class StepQuestionLimitRule:
    limit: int | None = None
    priority_tiers: tuple[str, ...] | None = None


def _normalize_ui_mode(ui_mode: str) -> str:
    normalized = str(ui_mode).strip().lower()
    if normalized not in UI_MODE_PRIORITY_TIERS:
        return "standard"
    return normalized


def _mode_question_limit_ratio(ui_mode: str) -> float:
    raw_ratio = UI_MODE_QUESTION_LIMIT_RATIOS.get(ui_mode)
    try:
        ratio = float(raw_ratio)
    except (TypeError, ValueError):
        ratio = UI_MODE_QUESTION_LIMIT_RATIOS["standard"]
    return max(0.0, min(1.0, ratio))


def _limit_for_ratio(total: int, ratio: float) -> int:
    if total <= 0:
        return 0
    if ratio >= 1.0:
        return total
    return min(total, max(1, ceil(total * ratio)))


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


def _question_priority_tier(question: Question) -> str:
    priority = str(question.priority or "standard").strip().lower()
    if priority not in {"core", "standard", "detail"}:
        return "standard"
    return priority


def _normalize_priority_tiers(raw_tiers: Any) -> tuple[str, ...] | None:
    if raw_tiers is None:
        return None
    if isinstance(raw_tiers, str):
        candidates = [raw_tiers]
    elif isinstance(raw_tiers, (list, tuple, set)):
        candidates = list(raw_tiers)
    else:
        return None
    tiers = tuple(
        tier
        for tier in (
            str(candidate).strip().lower()
            for candidate in candidates
        )
        if tier in {"core", "standard", "detail"}
    )
    return tiers or None


def _filter_questions_by_priority_tiers(
    questions: list[Question],
    priority_tiers: tuple[str, ...] | None,
) -> list[Question]:
    if not priority_tiers:
        return questions
    allowed = set(priority_tiers)
    matched = [
        question for question in questions if _question_priority_tier(question) in allowed
    ]
    if matched:
        return matched
    if allowed == {"core"} and all(question.priority is None for question in questions):
        return questions
    return matched


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

    dependency_visible_questions = _resolve_visible_questions_for_limit(
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
        dependency_visible_questions,
        limit=limit,
        answers=answers,
        answer_meta=answer_meta,
        job_extract=job_extract,
        intake_facts=intake_facts,
        intake_fact_evidence=intake_fact_evidence,
        confidence_threshold=confidence_threshold,
    )


def _read_step_limit_rule(
    question_limits: Mapping[str, Any] | None,
    step_key: str,
) -> StepQuestionLimitRule:
    if not isinstance(question_limits, Mapping):
        return StepQuestionLimitRule()
    raw_rule = question_limits.get(step_key)
    if isinstance(raw_rule, Mapping):
        limit = _coerce_limit(raw_rule.get("limit"), allow_zero=True)
        tiers = _normalize_priority_tiers(raw_rule.get("priority_tiers"))
        return StepQuestionLimitRule(
            limit=limit,
            priority_tiers=tiers,
        )
    limit = _coerce_limit(raw_rule)
    return StepQuestionLimitRule(limit=limit)


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

    dependency_visible_questions = _resolve_visible_questions_for_limit(
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
    step_rule = _read_step_limit_rule(question_limits, step_key)
    priority_visible_questions = _filter_questions_by_priority_tiers(
        dependency_visible_questions,
        step_rule.priority_tiers,
    )
    if (
        step_rule.limit is None
        and step_rule.priority_tiers is None
    ):
        selected_questions = questions
        selected_visible_questions = dependency_visible_questions
    elif step_rule.limit is not None and step_rule.limit <= 0:
        selected_visible_questions = []
        selected_questions = []
    else:
        selected_visible_questions = _select_visible_questions_for_adaptive_limit(
            priority_visible_questions,
            limit=step_rule.limit,
            answers=answers,
            answer_meta=answer_meta,
            job_extract=job_extract,
            intake_facts=intake_facts,
            intake_fact_evidence=intake_fact_evidence,
            confidence_threshold=confidence_threshold,
        )
        selected_questions = selected_visible_questions

    dependency_hidden_count = max(len(questions) - len(dependency_visible_questions), 0)
    adaptive_hidden_count = max(
        len(dependency_visible_questions) - len(selected_visible_questions),
        0,
    )
    return StepQuestionScope(
        selected_questions=selected_questions,
        visible_questions=selected_visible_questions,
        hidden_questions_count=dependency_hidden_count + adaptive_hidden_count,
        dependency_hidden_questions_count=dependency_hidden_count,
        adaptive_hidden_questions_count=adaptive_hidden_count,
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
            dependency_hidden_questions_count=0,
            adaptive_hidden_questions_count=0,
        )
    step = next((entry for entry in plan.steps if entry.step_key == step_key), None)
    if step is None:
        return StepQuestionScope(
            selected_questions=[],
            visible_questions=[],
            hidden_questions_count=0,
            dependency_hidden_questions_count=0,
            adaptive_hidden_questions_count=0,
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


def resolve_next_best_question(
    questions: list[Question],
    *,
    answered_lookup: Mapping[str, bool] | None = None,
    answers: Mapping[str, Any] | None = None,
    answer_meta: AnswerMetaMap | None = None,
    job_extract: JobAdExtract | None = None,
    intake_facts: Mapping[str, Any] | None = None,
    intake_fact_evidence: Mapping[str, Any] | None = None,
    confidence_threshold: float | None = None,
) -> Question | None:
    """Return the highest-ranked unanswered question from an already visible scope."""

    if not questions:
        return None

    answers_dict = dict(answers or {})
    answer_meta_dict = answer_meta or {}
    scored_questions: list[tuple[int, int, Question]] = []
    for index, question in enumerate(questions):
        if answered_lookup is not None and question.id in answered_lookup:
            covered = bool(answered_lookup[question.id])
        else:
            covered = _question_is_covered(
                question,
                answers=answers_dict,
                answer_meta=answer_meta_dict,
                job_extract=job_extract,
                intake_facts=intake_facts,
                intake_fact_evidence=intake_fact_evidence,
                confidence_threshold=confidence_threshold,
            )
        if covered:
            continue
        scored_questions.append(
            (_question_limit_score(question, covered=False), index, question)
        )

    if not scored_questions:
        return None
    return sorted(scored_questions, key=lambda item: (-item[0], item[1]))[0][2]


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
) -> dict[str, Any]:
    normalized_ui_mode = _normalize_ui_mode(ui_mode)
    priority_tiers = UI_MODE_PRIORITY_TIERS[normalized_ui_mode]
    question_limit_ratio = _mode_question_limit_ratio(normalized_ui_mode)
    limits: dict[str, Any] = {
        QUESTION_LIMIT_SCOPE_META_KEY: {
            "ui_mode": normalized_ui_mode,
            "priority_tiers": list(priority_tiers),
            "question_limit_ratio": question_limit_ratio,
        }
    }

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
        scoped_questions = _filter_questions_by_priority_tiers(
            visible_questions,
            priority_tiers,
        )
        total = len(scoped_questions)
        limit = _limit_for_ratio(total, question_limit_ratio)
        limits[step.step_key] = {
            "limit": limit,
            "priority_tiers": list(priority_tiers),
            "ui_mode": normalized_ui_mode,
            "question_limit_ratio": question_limit_ratio,
        }

    return limits


def _coerce_limit(raw_limit: Any, *, allow_zero: bool = False) -> int | None:
    if not isinstance(raw_limit, (int, float, str)):
        return None
    try:
        limit = int(raw_limit)
    except (TypeError, ValueError):
        return None
    if limit <= 0 and not allow_zero:
        return None
    return limit


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
