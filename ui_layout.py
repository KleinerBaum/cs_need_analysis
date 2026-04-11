"""Reusable page layout shells for wizard steps."""

from __future__ import annotations

from collections.abc import Callable

import streamlit as st

from question_dependencies import should_show_question
from question_progress import compute_question_progress
from schemas import QuestionStep
from state import get_answer_meta, get_answers


def _render_step_status(step: QuestionStep | None) -> None:
    if step is None:
        st.caption("Status · keine Fragen")
        return

    answers = get_answers()
    answer_meta = get_answer_meta()
    visible_questions = [
        question
        for question in step.questions
        if should_show_question(question, answers, answer_meta, step.step_key)
    ]
    progress = compute_question_progress(visible_questions, answers, answer_meta)
    st.caption(f"Status · {progress['answered']}/{progress['total']} beantwortet")


def render_step_shell(
    *,
    title: str,
    subtitle: str,
    step: QuestionStep | None = None,
    extracted_from_jobspec_slot: Callable[[], None] | None = None,
    extracted_from_jobspec_label: str = "Aus Jobspec extrahiert",
    main_content_slot: Callable[[], None],
    footer_slot: Callable[[], None] | None = None,
) -> None:
    header_col, status_col = st.columns([4, 2])
    with header_col:
        st.header(title)
        st.caption(subtitle)
    with status_col:
        _render_step_status(step)

    if extracted_from_jobspec_slot is not None:
        with st.expander(extracted_from_jobspec_label, expanded=True):
            extracted_from_jobspec_slot()

    main_content_slot()

    if footer_slot is not None:
        st.divider()
        footer_slot()
