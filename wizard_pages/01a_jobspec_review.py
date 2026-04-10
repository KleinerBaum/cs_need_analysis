from __future__ import annotations

import streamlit as st

from constants import SSKey
from schemas import JobAdExtract, QuestionPlan
from ui_components import (
    _render_question_limits_editor,
    render_error_banner,
    render_esco_picker_card,
    render_job_extract_overview,
)
from wizard_pages.base import WizardContext, WizardPage, nav_buttons


def _build_esco_query(job: JobAdExtract) -> str:
    title = (job.job_title or "").strip()
    if not title:
        return ""
    context_parts = [job.seniority_level, job.department_name, job.location_city]
    context = ", ".join(part.strip() for part in context_parts if part and part.strip())
    if not context:
        return title
    return f"{title} ({context})"


def _render_esco_occupation_block(job: JobAdExtract) -> None:
    st.markdown("### ESCO Occupation")
    query_text = _build_esco_query(job)
    if not query_text:
        st.info("Kein Jobtitel vorhanden. ESCO-Zuordnung aktuell nicht möglich.")
        st.session_state[SSKey.ESCO_OCCUPATION_CANDIDATES.value] = []
        st.session_state[SSKey.ESCO_OCCUPATION_SELECTED.value] = None
        return

    st.caption(f"Suche mit: `{query_text}`")
    query_state_key = f"{SSKey.ESCO_OCCUPATION_SELECTED.value}.esco_picker.query"
    if not st.session_state.get(query_state_key):
        st.session_state[query_state_key] = query_text
    render_esco_picker_card(
        concept_type="occupation",
        target_state_key=SSKey.ESCO_OCCUPATION_SELECTED,
        enable_preview=True,
    )
    options_state_key = f"{SSKey.ESCO_OCCUPATION_SELECTED.value}.esco_picker.options"
    options = st.session_state.get(options_state_key, [])
    st.session_state[SSKey.ESCO_OCCUPATION_CANDIDATES.value] = (
        options if isinstance(options, list) else []
    )


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

    st.header("Jobspec-Übersicht")
    st.caption(
        "Hier prüfst und ergänzt du die extrahierten Inhalte, Gaps und Assumptions, "
        "bevor du in den Schritt 'Unternehmen' wechselst."
    )
    render_error_banner()

    st.markdown(f"**Jobtitel:** {job.job_title or '—'}")
    _render_esco_occupation_block(job)

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
