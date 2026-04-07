# wizard_pages/05_skills.py
from __future__ import annotations

import streamlit as st

from constants import SSKey
from schemas import JobAdExtract, QuestionPlan
from ui_components import render_error_banner, render_question_step
from wizard_pages.base import WizardContext, WizardPage, nav_buttons


def render(ctx: WizardContext) -> None:
    st.header("Skills & Anforderungen")
    render_error_banner()

    job_dict = st.session_state.get(SSKey.JOB_EXTRACT.value)
    plan_dict = st.session_state.get(SSKey.QUESTION_PLAN.value)

    if not job_dict or not plan_dict:
        st.warning("Bitte zuerst im Schritt 'Jobspec / Jobad' eine Analyse durchführen.")
        st.button("Zur Jobspec-Seite", on_click=lambda: ctx.goto("jobad"))
        nav_buttons(ctx, disable_next=True)
        return

    job = JobAdExtract.model_validate(job_dict)
    plan = QuestionPlan.model_validate(plan_dict)

    st.write(
        "Ziel: Must-have vs Nice-to-have klar trennen, Level definieren, "
        "und daraus eine Interview- & Assessment-Logik ableiten."
    )

    with st.expander("Aus Jobspec extrahiert (Skills)", expanded=False):
        st.write("**Must-have (Auszug):**")
        if job.must_have_skills:
            for x in job.must_have_skills[:12]:
                st.write(f"- {x}")
        else:
            st.write("—")

        st.write("**Nice-to-have (Auszug):**")
        if job.nice_to_have_skills:
            for x in job.nice_to_have_skills[:12]:
                st.write(f"- {x}")
        else:
            st.write("—")

        if job.tech_stack:
            st.write("**Tech Stack (Auszug):**")
            for x in job.tech_stack[:15]:
                st.write(f"- {x}")

    step = next((s for s in plan.steps if s.step_key == "skills"), None)
    if step is None or not step.questions:
        st.info("Für diesen Abschnitt wurden keine spezifischen Fragen erzeugt. Du kannst trotzdem weitergehen.")
        nav_buttons(ctx)
        return

    render_question_step(step)
    nav_buttons(ctx)


PAGE = WizardPage(
    key="skills",
    title_de="Skills & Anforderungen",
    icon="🧠",
    render=render,
    requires_jobspec=True,
)
