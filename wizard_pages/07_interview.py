# wizard_pages/07_interview.py
from __future__ import annotations

import streamlit as st

from constants import SSKey
from schemas import JobAdExtract, QuestionPlan
from ui_layout import render_step_shell
from ui_components import (
    has_meaningful_value,
    render_error_banner,
    render_question_step,
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

    render_step_shell(
        title="Interviewprozess",
        subtitle=(
            "Ziel: Einen klaren, fairen Prozess definieren (Stages, Stakeholder, "
            "Assessments, Timeline) und gleichzeitig das Candidate Experience sicherstellen."
        ),
        step=step,
        extracted_from_jobspec_slot=_render_extracted_slot,
        extracted_from_jobspec_label="Aus Jobspec extrahiert (Recruitment Steps)",
        main_content_slot=_render_main_slot,
        footer_slot=lambda: nav_buttons(ctx),
    )


PAGE = WizardPage(
    key="interview",
    title_de="Interviewprozess",
    icon="🗓️",
    render=render,
    requires_jobspec=True,
)
