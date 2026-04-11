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
from ui_layout import render_step_shell
from wizard_pages.base import WizardContext, WizardPage, nav_buttons


def render(ctx: WizardContext) -> None:
    job_dict = st.session_state.get(SSKey.JOB_EXTRACT.value)
    plan_dict = st.session_state.get(SSKey.QUESTION_PLAN.value)

    if not job_dict or not plan_dict:
        st.warning("Bitte zuerst im Start-Schritt eine Analyse durchführen.")
        st.button("Zur Startseite", on_click=lambda: ctx.goto("landing"))
        nav_buttons(ctx, disable_next=True)
        return

    job = JobAdExtract.model_validate(job_dict)
    plan = QuestionPlan.model_validate(plan_dict)
    step = next((s for s in plan.steps if s.step_key == "team"), None)

    def _render_extracted_slot() -> None:
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

    def _render_main_slot() -> None:
        render_error_banner()
        st.write(
            "Hier geht es um Team-Setup, Schnittstellen, Arbeitsmodus (hybrid/remote), aktuelle Herausforderungen "
            "und warum diese Rolle für das Team wichtig ist."
        )
        if step is None or not step.questions:
            st.info(
                "Für diesen Abschnitt wurden keine spezifischen Fragen erzeugt. Du kannst trotzdem weitergehen."
            )
            return
        render_question_step(step)

    render_step_shell(
        title="Team",
        subtitle="Teamkontext, Schnittstellen und Zusammenarbeit.",
        step=step,
        extracted_from_jobspec_slot=_render_extracted_slot,
        extracted_from_jobspec_label="Aus Jobspec extrahiert (Team/Org)",
        main_content_slot=_render_main_slot,
        footer_slot=lambda: nav_buttons(ctx),
    )


PAGE = WizardPage(
    key="team",
    title_de="Team",
    icon="👥",
    render=render,
    requires_jobspec=True,
)
