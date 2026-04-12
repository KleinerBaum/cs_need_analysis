"""Reusable page layout shells for wizard steps."""

from __future__ import annotations

from collections.abc import Callable

import streamlit as st

from question_dependencies import should_show_question
from schemas import QuestionStep
from step_status import build_step_status_payload
from state import get_answer_meta, get_answers


def _render_step_status(step: QuestionStep | None) -> None:
    answers = get_answers()
    answer_meta = get_answer_meta()
    status = build_step_status_payload(
        step=step,
        answers=answers,
        answer_meta=answer_meta,
        should_show_question=should_show_question,
        step_key=step.step_key if step is not None else None,
    )
    st.caption(f"Status · {status['answered']}/{status['total']} beantwortet")


def render_step_shell(
    *,
    title: str,
    subtitle: str,
    outcome_text: str | None = None,
    outcome_slot: Callable[[], None] | None = None,
    step: QuestionStep | None = None,
    extracted_from_jobspec_slot: Callable[[], None] | None = None,
    extracted_from_jobspec_label: str = "Aus Jobspec extrahiert",
    main_content_slot: Callable[[], None],
    review_slot: Callable[[], None] | None = None,
    footer_slot: Callable[[], None] | None = None,
) -> None:
    header_col, status_col = st.columns([4, 2])
    with header_col:
        st.header(title)
        st.caption(subtitle)
        if outcome_text:
            st.markdown(f"**Outcome:** {outcome_text}")
        if outcome_slot is not None:
            outcome_slot()
    with status_col:
        _render_step_status(step)

    if extracted_from_jobspec_slot is not None:
        with st.expander(extracted_from_jobspec_label, expanded=True):
            extracted_from_jobspec_slot()

    main_content_slot()
    if review_slot is not None:
        review_slot()

    if footer_slot is not None:
        st.divider()
        footer_slot()
