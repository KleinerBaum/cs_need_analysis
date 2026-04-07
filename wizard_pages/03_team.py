# wizard_pages/03_team.py
from __future__ import annotations

import streamlit as st

from constants import SSKey
from schemas import JobAdExtract, QuestionPlan
from ui_components import (
    has_meaningful_value,
    render_error_banner,
    render_question_step,
)
from wizard_pages.base import WizardContext, WizardPage, nav_buttons


def render(ctx: WizardContext) -> None:
    st.header("Team")
    render_error_banner()

    job_dict = st.session_state.get(SSKey.JOB_EXTRACT.value)
    plan_dict = st.session_state.get(SSKey.QUESTION_PLAN.value)

    if not job_dict or not plan_dict:
        st.warning(
            "Bitte zuerst im Schritt 'Jobspec / Jobad' eine Analyse durchführen."
        )
        st.button("Zur Jobspec-Seite", on_click=lambda: ctx.goto("jobad"))
        nav_buttons(ctx, disable_next=True)
        return

    job = JobAdExtract.model_validate(job_dict)
    plan = QuestionPlan.model_validate(plan_dict)

    st.write(
        "Hier geht es um Team-Setup, Schnittstellen, Arbeitsmodus (hybrid/remote), aktuelle Herausforderungen "
        "und warum diese Rolle für das Team wichtig ist."
    )

    with st.expander("Aus Jobspec extrahiert (Team/Org)", expanded=True):
        extracted_rows = [
            ("Department", job.department_name),
            ("Reports to", job.reports_to),
            ("Direct reports", job.direct_reports_count),
        ]
        shown = False
        for label, value in extracted_rows:
            if has_meaningful_value(value):
                st.write(f"**{label}:** {value}")
                shown = True
        if not shown:
            st.info(
                "Keine verlässlichen Werte erkannt. Details siehe Gaps/Assumptions."
            )

    step = next((s for s in plan.steps if s.step_key == "team"), None)
    if step is None or not step.questions:
        st.info(
            "Für diesen Abschnitt wurden keine spezifischen Fragen erzeugt. Du kannst trotzdem weitergehen."
        )
        nav_buttons(ctx)
        return

    render_question_step(step)
    nav_buttons(ctx)


PAGE = WizardPage(
    key="team",
    title_de="Team",
    icon="👥",
    render=render,
    requires_jobspec=True,
)
