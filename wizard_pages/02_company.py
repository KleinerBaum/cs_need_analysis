# wizard_pages/02_company.py
from __future__ import annotations

import streamlit as st

from constants import SSKey
from schemas import JobAdExtract, QuestionPlan
from ui_components import render_error_banner, render_question_step
from wizard_pages.base import WizardContext, WizardPage, nav_buttons


def render(ctx: WizardContext) -> None:
    st.header("Unternehmen")
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
        "Hier sammelst du kontextuelle Informationen zum Unternehmen/Business-Bereich, "
        "die Kandidat:innen verstehen müssen (Mission, Markt, Value Prop, Brand, Rahmenbedingungen)."
    )

    with st.expander("Aus Jobspec extrahiert (Company & Location)", expanded=False):
        st.write(f"**Unternehmen:** {job.company_name or '—'}")
        st.write(f"**Marke/Brand:** {job.brand_name or '—'}")
        st.write(f"**Ort:** {job.location_city or '—'}")
        st.write(f"**Remote Policy:** {job.remote_policy or '—'}")

    step = next((s for s in plan.steps if s.step_key == "company"), None)
    if step is None or not step.questions:
        st.info("Für diesen Abschnitt wurden keine spezifischen Fragen erzeugt. Du kannst trotzdem weitergehen.")
        nav_buttons(ctx)
        return

    render_question_step(step)
    nav_buttons(ctx)


PAGE = WizardPage(
    key="company",
    title_de="Unternehmen",
    icon="🏢",
    render=render,
    requires_jobspec=True,
)
