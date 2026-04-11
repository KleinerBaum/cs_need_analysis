"""Adaptive question-limit helpers for progressive intake depth."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

import streamlit as st

from constants import SSKey
from question_dependencies import should_show_question
from question_progress import is_answered
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


def _is_meaningful(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, set, dict)):
        return len(value) > 0
    return True


def _extract_value_by_target_path(job_extract: JobAdExtract | None, target_path: str) -> Any:
    if job_extract is None:
        return None

    data: dict[str, Any] = job_extract.model_dump()
    current: Any = data
    for segment in (part for part in target_path.split(".") if part):
        if not isinstance(current, dict):
            return None
        if segment not in current:
            return None
        current = current.get(segment)
    return current


def _question_is_covered(
    question: Question,
    *,
    answers: dict[str, Any],
    answer_meta: dict[str, dict[str, Any]],
    job_extract: JobAdExtract | None,
) -> bool:
    if is_answered(question, answers.get(question.id), answer_meta.get(question.id)):
        return True
    target_path = question.target_path
    if not isinstance(target_path, str) or not target_path.strip():
        return False
    return _is_meaningful(_extract_value_by_target_path(job_extract, target_path.strip()))


def compute_adaptive_question_limits(
    *,
    plan: QuestionPlan,
    ui_mode: str,
    answers: dict[str, Any],
    answer_meta: dict[str, dict[str, Any]],
    job_extract: JobAdExtract | None,
) -> dict[str, int]:
    profile = _resolve_mode_profile(ui_mode)
    limits: dict[str, int] = {}

    for step in plan.steps:
        if not step.questions:
            continue
        visible_questions = [
            question
            for question in step.questions
            if should_show_question(question, answers, answer_meta, step.step_key)
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
    answer_meta = answer_meta_raw if isinstance(answer_meta_raw, dict) else {}
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
    )

