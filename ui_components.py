# ui_components.py
"""Reusable Streamlit UI components."""

from __future__ import annotations

from datetime import date
from typing import Any, Dict, Optional

import streamlit as st

from constants import AnswerType, SSKey, WIDGET_KEY_PREFIX
from llm_client import OpenAICallError
from schemas import JobAdExtract, Question, QuestionStep, VacancyBrief
from state import get_answers, set_answer, set_error


def render_error_banner() -> None:
    err = st.session_state.get(SSKey.LAST_ERROR.value)
    if err:
        st.error(err)
    debug_err = st.session_state.get("cs.last_error_debug")
    if debug_err and bool(st.session_state.get("OPENAI_DEBUG_ERRORS", False)):
        with st.expander("Debug (non-sensitive)", expanded=False):
            st.code(str(debug_err))


def render_openai_error(error: OpenAICallError) -> None:
    """Persist concise user message and optional non-sensitive debug details."""

    set_error(error.ui_message)
    st.session_state["cs.last_error_debug"] = None
    if bool(st.session_state.get("OPENAI_DEBUG_ERRORS", False)):
        details: list[str] = []
        if error.error_code:
            details.append(f"code={error.error_code}")
        if error.debug_detail:
            details.append(error.debug_detail)
        if details:
            st.session_state["cs.last_error_debug"] = " | ".join(details)


def render_job_extract_overview(job: JobAdExtract) -> None:
    with st.expander(
        "Aus dem Jobspec extrahiert (strukturierte Übersicht)", expanded=False
    ):
        st.json(job.model_dump(), expanded=False)

    with st.expander("Gaps (fehlende/unklare Punkte)", expanded=False):
        if job.gaps:
            st.write("\n".join([f"- {g}" for g in job.gaps]))
        else:
            st.info("Keine expliziten Gaps erkannt.")

    with st.expander("Assumptions (Annahmen)", expanded=False):
        if job.assumptions:
            st.write("\n".join([f"- {a}" for a in job.assumptions]))
        else:
            st.info("Keine Annahmen dokumentiert.")


def render_question_step(step: QuestionStep) -> None:
    answers = get_answers()

    if step.description_de:
        st.caption(step.description_de)

    for q in step.questions:
        _render_question(q, answers)


def _render_question(q: Question, answers: Dict[str, Any]) -> None:
    key = WIDGET_KEY_PREFIX + q.id
    current_value = answers.get(q.id, q.default)

    # Helper text for required fields
    label = q.label + (" *" if q.required else "")

    # Render appropriate widget
    if q.answer_type == AnswerType.SHORT_TEXT:
        value = st.text_input(label, value=current_value or "", help=q.help, key=key)
    elif q.answer_type == AnswerType.LONG_TEXT:
        value = st.text_area(
            label, value=current_value or "", help=q.help, key=key, height=120
        )
    elif q.answer_type == AnswerType.SINGLE_SELECT:
        options = q.options or []
        # Streamlit selectbox needs an index; allow None by adding sentinel
        if current_value and current_value not in options:
            options = [current_value] + options
        value = st.selectbox(
            label,
            options=options,
            index=(options.index(current_value) if current_value in options else 0)
            if options
            else 0,
            help=q.help,
            key=key,
        )
    elif q.answer_type == AnswerType.MULTI_SELECT:
        options = q.options or []
        if current_value is None:
            current_value = []
        # Ensure values are in options
        cur_list = [v for v in (current_value or []) if isinstance(v, str)]
        for v in cur_list:
            if v not in options:
                options = [v] + options
        value = st.multiselect(
            label, options=options, default=cur_list, help=q.help, key=key
        )
    elif q.answer_type == AnswerType.NUMBER:
        try:
            num = (
                float(current_value)
                if current_value is not None and current_value != ""
                else None
            )
        except Exception:
            num = None
        value = st.number_input(
            label, value=num if num is not None else 0.0, help=q.help, key=key
        )
    elif q.answer_type == AnswerType.BOOLEAN:
        value = st.checkbox(
            label,
            value=bool(current_value) if current_value is not None else False,
            help=q.help,
            key=key,
        )
    elif q.answer_type == AnswerType.DATE:
        # Accept ISO string, date, or None
        d: Optional[date] = None
        if isinstance(current_value, date):
            d = current_value
        elif isinstance(current_value, str) and current_value:
            try:
                d = date.fromisoformat(current_value)
            except Exception:
                d = None
        value = st.date_input(label, value=d, help=q.help, key=key)
        # Convert to iso string for JSON friendliness
        value = value.isoformat() if value else None
    else:
        value = st.text_input(
            label, value=str(current_value or ""), help=q.help, key=key
        )

    # Persist answer
    set_answer(q.id, value)

    if st.session_state.get(SSKey.DEBUG.value) and q.rationale:
        st.caption(f"Rationale: {q.rationale}")


def render_brief(brief: VacancyBrief) -> None:
    st.subheader("Recruiting Brief")
    st.markdown(f"**One-liner:** {brief.one_liner}")
    st.markdown("**Hiring Context**")
    st.write(brief.hiring_context)
    st.markdown("**Role Summary**")
    st.write(brief.role_summary)

    st.markdown("**Top Responsibilities**")
    for x in brief.top_responsibilities:
        st.write(f"- {x}")

    st.markdown("**Must-have**")
    for x in brief.must_have:
        st.write(f"- {x}")

    st.markdown("**Nice-to-have**")
    for x in brief.nice_to_have:
        st.write(f"- {x}")

    st.markdown("**Dealbreakers**")
    for x in brief.dealbreakers:
        st.write(f"- {x}")

    st.markdown("**Interview Plan**")
    for x in brief.interview_plan:
        st.write(f"- {x}")

    st.markdown("**Evaluation Rubric**")
    for x in brief.evaluation_rubric:
        st.write(f"- {x}")

    st.markdown("**Risks / Open Questions**")
    for x in brief.risks_open_questions:
        st.write(f"- {x}")

    st.subheader("Job Ad Draft (DE)")
    st.write(brief.job_ad_draft)

    with st.expander("Structured data (JSON)", expanded=False):
        st.json(brief.structured_data, expanded=False)
