# wizard_pages/04_role_tasks.py
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
    st.header("Rolle & Aufgaben")
    render_error_banner()

    job_dict = st.session_state.get(SSKey.JOB_EXTRACT.value)
    plan_dict = st.session_state.get(SSKey.QUESTION_PLAN.value)

    if not job_dict or not plan_dict:
        st.warning(
            "Bitte zuerst im Start-Schritt eine Analyse durchführen."
        )
        st.button("Zur Startseite", on_click=lambda: ctx.goto("landing"))
        nav_buttons(ctx, disable_next=True)
        return

    job = JobAdExtract.model_validate(job_dict)
    plan = QuestionPlan.model_validate(plan_dict)

    st.write(
        "Jetzt schärfen wir Scope, Verantwortlichkeiten, Deliverables, Erfolgskriterien und Stakeholder. "
        "Das ist der Kern für Briefing, Interviewleitfaden und Erwartungsmanagement."
    )

    with st.expander(
        "Aus Jobspec extrahiert (Responsibilities & Metrics)", expanded=True
    ):
        responsibilities = [r for r in job.responsibilities if has_meaningful_value(r)]
        success_metrics = [r for r in job.success_metrics if has_meaningful_value(r)]
        if responsibilities:
            st.write("**Responsibilities (Auszug):**")
            for r in responsibilities[:10]:
                st.write(f"- {r}")

        if success_metrics:
            st.write("**Success Metrics (Auszug):**")
            for r in success_metrics[:10]:
                st.write(f"- {r}")
        if not responsibilities and not success_metrics:
            st.info(
                "Keine verlässlichen Werte erkannt. Details siehe Gaps/Assumptions."
            )

    step = next((s for s in plan.steps if s.step_key == "role_tasks"), None)
    if step is None or not step.questions:
        st.info(
            "Für diesen Abschnitt wurden keine spezifischen Fragen erzeugt. Du kannst trotzdem weitergehen."
        )
        nav_buttons(ctx)
        return

    render_question_step(step)
    nav_buttons(ctx)


PAGE = WizardPage(
    key="role_tasks",
    title_de="Rolle & Aufgaben",
    icon="🧭",
    render=render,
    requires_jobspec=True,
)
