"""Reusable page layout shells for wizard steps."""

from __future__ import annotations

from collections.abc import Callable

import streamlit as st

from question_dependencies import should_show_question
from schemas import QuestionStep
from step_status import StepStatusPayload, build_step_status_payload
from state import get_answer_meta, get_answers


def _status_badge_text(completion_state: str) -> str:
    if completion_state == "complete":
        return "✅ Vollständig"
    if completion_state == "partial":
        return "🟡 Teilweise"
    return "⬜ Offen"


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
        answers = get_answers()
        answer_meta = get_answer_meta()
        status = build_step_status_payload(
            step=step,
            answers=answers,
            answer_meta=answer_meta,
            should_show_question=should_show_question,
            step_key=step.step_key if step is not None else None,
        )
        _render_step_status(status)

    if extracted_from_jobspec_slot is not None:
        with st.expander(extracted_from_jobspec_label, expanded=True):
            extracted_from_jobspec_slot()

    main_content_slot()
    if review_slot is not None:
        review_slot()

    if footer_slot is not None:
        st.divider()
        footer_slot()
