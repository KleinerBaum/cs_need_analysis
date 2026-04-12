# wizard_pages/07_interview.py
from __future__ import annotations

import streamlit as st

from constants import SSKey
from question_dependencies import should_show_question
from question_progress import build_answered_lookup
from schemas import JobAdExtract, QuestionPlan
from state import get_answer_meta, get_answers
from ui_layout import render_step_shell
from ui_components import (
    has_meaningful_value,
    render_error_banner,
    render_question_step,
    render_step_review_card,
)
from wizard_pages.base import WizardContext, WizardPage, nav_buttons


def render(ctx: WizardContext) -> None:
    render_error_banner()

    job_dict = st.session_state.get(SSKey.JOB_EXTRACT.value)
    plan_dict = st.session_state.get(SSKey.QUESTION_PLAN.value)

    if not job_dict or not plan_dict:
        st.warning("Bitte zuerst im Start-Schritt eine Analyse durchführen.")
        st.button("Zur Startseite", on_click=lambda: ctx.goto("landing"))
        nav_buttons(ctx, disable_next=True)
        return

    job = JobAdExtract.model_validate(job_dict)
    plan = QuestionPlan.model_validate(plan_dict)

    step = next((s for s in plan.steps if s.step_key == "interview"), None)

    def _render_extracted_slot() -> None:
        shown = False
        if job.recruitment_steps:
            for s in job.recruitment_steps:
                if not has_meaningful_value(s.name):
                    continue
                details = f"– {s.details}" if has_meaningful_value(s.details) else ""
                st.write(f"- **{s.name}** {details}")
                shown = True
        if not shown:
            st.info(
                "Keine verlässlichen Werte erkannt. Details siehe Gaps/Assumptions."
            )

    def _render_main_slot() -> None:
        if step is None or not step.questions:
            st.info(
                "Für diesen Abschnitt wurden keine spezifischen Fragen erzeugt. Du kannst trotzdem weitergehen."
            )
            return

        render_question_step(step)

    def _render_review_slot() -> None:
        if step is None or not step.questions:
            return
        answers = get_answers()
        answer_meta = get_answer_meta()
        visible_questions = [
            question
            for question in step.questions
            if should_show_question(question, answers, answer_meta, step.step_key)
        ]
        if not visible_questions:
            return
        render_step_review_card(
            step=step,
            visible_questions=visible_questions,
            answers=answers,
            answer_meta=answer_meta,
            answered_lookup=build_answered_lookup(
                visible_questions, answers, answer_meta
            ),
        )

    render_step_shell(
        title="Interviewprozess",
        subtitle=(
            "Ziel: Einen klaren, fairen Prozess definieren (Stages, Stakeholder, "
            "Assessments, Timeline) und gleichzeitig das Candidate Experience sicherstellen."
        ),
        outcome_text=(
            "Ein klarer, fairer Interviewablauf mit Verantwortlichkeiten und Timeline "
            "für eine verlässliche Candidate Experience."
        ),
        step=step,
        extracted_from_jobspec_slot=_render_extracted_slot,
        extracted_from_jobspec_label="Aus Jobspec extrahiert (Recruitment Steps)",
        main_content_slot=_render_main_slot,
        review_slot=_render_review_slot,
        footer_slot=lambda: nav_buttons(ctx),
    )


PAGE = WizardPage(
    key="interview",
    title_de="Interviewprozess",
    icon="🗓️",
    render=render,
    requires_jobspec=True,
)
