"""Adaptive question-limit helpers for progressive intake depth."""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, cast

import streamlit as st

from constants import SSKey, UI_PREFERENCE_CONFIDENCE_THRESHOLD
from question_dependencies import should_show_question
from question_progress import (
    AnswerMetaMap,
    build_answers_with_job_extract_coverage,
    is_answered,
    is_question_covered_by_job_extract,
)
from schemas import JobAdExtract, Question, QuestionPlan


@dataclass(frozen=True)
class ModeLimitProfile:
    missing_fraction: float
    min_questions: int
    context_buffer: int


_MODE_LIMIT_PROFILES: dict[str, ModeLimitProfile] = {
    "quick": ModeLimitProfile(missing_fraction=0.45, min_questions=1, context_buffer=0),
    "standard": ModeLimitProfile(
        missing_fraction=0.7,
        min_questions=2,
        context_buffer=1,
    ),
    "expert": ModeLimitProfile(missing_fraction=1.0, min_questions=3, context_buffer=2),
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
        effective_answers = build_answers_with_job_extract_coverage(
            step.questions,
            answers,
            answer_meta,
            job_extract=job_extract,
            intake_facts=intake_facts,
            intake_fact_evidence=intake_fact_evidence,
            confidence_threshold=confidence_threshold,
        )
        visible_questions = [
            question
            for question in step.questions
            if should_show_question(
                question,
                effective_answers,
                answer_meta,
                step.step_key,
                intake_facts=intake_facts,
            )
        ]
        total = len(visible_questions)
        if total == 0:
            continue

        covered = sum(
            1
            for question in visible_questions
            if _question_is_covered(
                question,
                answers=answers,
                answer_meta=answer_meta,
                job_extract=job_extract,
                intake_facts=intake_facts,
                intake_fact_evidence=intake_fact_evidence,
                confidence_threshold=confidence_threshold,
            )
        )
        missing = max(total - covered, 0)
        adaptive_count = math.ceil(missing * profile.missing_fraction)
        limit = max(profile.min_questions, adaptive_count + profile.context_buffer)
        limits[step.step_key] = max(1, min(total, limit))

    return limits


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
