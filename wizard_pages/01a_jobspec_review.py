from __future__ import annotations

import streamlit as st

from constants import SSKey
from schemas import JobAdExtract, QuestionPlan
from ui_components import (
    _render_question_limits_editor,
    render_error_banner,
    render_job_extract_overview,
)
from wizard_pages.base import WizardContext, WizardPage, nav_buttons


def render(ctx: WizardContext) -> None:
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

    st.header("Jobspec-Übersicht")
    st.caption(
        "Hier prüfst und ergänzt du die extrahierten Inhalte, Gaps und Assumptions, "
        "bevor du in den Schritt 'Unternehmen' wechselst."
    )
    render_error_banner()

    with st.sidebar:
        with st.expander("Fragen pro Step", expanded=False):
            _render_question_limits_editor(plan, compact=True)

    render_job_extract_overview(job, plan=plan, show_question_limits=False)

    st.info(
        f"QuestionPlan geladen: {sum(len(s.questions) for s in plan.steps)} Fragen in "
        f"{len(plan.steps)} Steps."
    )
    nav_buttons(ctx)


PAGE = WizardPage(
    key="jobspec_review",
    title_de="Jobspec-Übersicht",
    icon="🧾",
    render=render,
    requires_jobspec=True,
)
