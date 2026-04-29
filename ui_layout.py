"""Reusable page layout shells for wizard steps."""

from __future__ import annotations

from collections.abc import Callable
from typing import Literal

import streamlit as st

from constants import COMPLETION_STATE_BADGE_TEXT, COMPLETION_STATE_NOT_STARTED
from question_dependencies import should_show_question
from schemas import QuestionStep
from step_status import StepStatusPayload, build_step_status_payload
from state import get_answer_meta, get_answers
def _status_badge_text(completion_state: str) -> str:
    return COMPLETION_STATE_BADGE_TEXT.get(
        completion_state, COMPLETION_STATE_BADGE_TEXT[COMPLETION_STATE_NOT_STARTED]
    )


def _truncate_missing_essentials(
    missing_essentials: list[str], max_items: int = 4
) -> str:
    compact_items = [item.strip() for item in missing_essentials if item.strip()]
    shown_items = compact_items[:max_items]
    if not shown_items:
        return ""
    suffix = " …" if len(compact_items) > len(shown_items) else ""
    return ", ".join(shown_items) + suffix


def _render_step_status(status: StepStatusPayload | None) -> None:
    if status is None:
        st.caption("⬜ Offen")
        st.caption("0/0 beantwortet")
        return

    badge_text = _status_badge_text(status["completion_state"])
    st.caption(badge_text)
    st.caption(f"{status['answered']}/{status['total']} beantwortet")
    missing_summary = _truncate_missing_essentials(status["missing_essentials"])
    if missing_summary:
        st.caption(f"Fehlt (essentiell): {missing_summary}")


def render_step_shell(
    *,
    title: str,
    subtitle: str,
    outcome_text: str | None = None,
    outcome_slot: Callable[[], None] | None = None,
    step: QuestionStep | None = None,
    extracted_from_jobspec_slot: Callable[[], None] | None = None,
    extracted_from_jobspec_label: str = "Aus Jobspec extrahiert",
    extracted_from_jobspec_use_expander: bool = True,
    source_comparison_slot: Callable[[], None] | None = None,
    salary_forecast_slot: Callable[[], None] | None = None,
    open_questions_slot: Callable[[], None] | None = None,
    main_content_slot: Callable[[], None] | None = None,
    review_slot: Callable[[], None] | None = None,
    after_review_slot: Callable[[], None] | None = None,
    post_review_slot: Callable[[], None] | None = None,
    footer_slot: Callable[[], None] | None = None,
    status_position: Literal["header", "before_footer"] = "header",
) -> None:
    header_col, status_col = st.columns([4, 2])
    with header_col:
        st.header(title)
        st.caption(subtitle)
        if outcome_text:
            st.markdown(f"**Outcome:** {outcome_text}")
        if outcome_slot is not None:
            outcome_slot()
    answers = get_answers()
    answer_meta = get_answer_meta()
    status = build_step_status_payload(
        step=step,
        answers=answers,
        answer_meta=answer_meta,
        should_show_question=should_show_question,
        step_key=step.step_key if step is not None else None,
    )
    with status_col:
        if status_position == "header":
            _render_step_status(status)

    if extracted_from_jobspec_slot is not None:
        if extracted_from_jobspec_use_expander:
            with st.expander(extracted_from_jobspec_label, expanded=True):
                extracted_from_jobspec_slot()
        else:
            st.markdown(f"### {extracted_from_jobspec_label}")
            extracted_from_jobspec_slot()

    uses_new_slots = any(
        slot is not None
        for slot in (
            source_comparison_slot,
            salary_forecast_slot,
            open_questions_slot,
        )
    )
    if uses_new_slots:
        if source_comparison_slot is not None:
            source_comparison_slot()
        if salary_forecast_slot is not None:
            salary_forecast_slot()
        if open_questions_slot is not None:
            open_questions_slot()
    elif main_content_slot is not None:
        main_content_slot()
    if review_slot is not None:
        review_slot()
    if after_review_slot is not None:
        after_review_slot()
    if post_review_slot is not None:
        post_review_slot()

    if status_position == "before_footer":
        _render_step_status(status)

    if footer_slot is not None:
        st.divider()
        footer_slot()
