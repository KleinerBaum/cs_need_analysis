# wizard_pages/06_benefits.py
from __future__ import annotations

import streamlit as st

from constants import SSKey
from schemas import JobAdExtract, QuestionPlan
from state import get_answers
from ui_layout import render_step_shell
from ui_components import (
    build_step_review_payload,
    has_meaningful_value,
    render_error_banner,
    render_question_step,
    render_step_review_card,
)
from wizard_pages.base import WizardContext, WizardPage, nav_buttons
from wizard_pages.salary_forecast_panel import render_salary_forecast_panel


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

    step = next((s for s in plan.steps if s.step_key == "benefits"), None)

    def _render_extracted_slot() -> None:
        shown = False
        if job.salary_range:
            min_salary = job.salary_range.min
            max_salary = job.salary_range.max
            if has_meaningful_value(min_salary) or has_meaningful_value(max_salary):
                st.write(
                    f"**Salary:** {min_salary} – {max_salary} {job.salary_range.currency or ''} ({job.salary_range.period or ''})"
                )
                shown = True
            if has_meaningful_value(job.salary_range.notes):
                st.write(f"**Notes:** {job.salary_range.notes}")
                shown = True

        benefits = [b for b in job.benefits if has_meaningful_value(b)]
        if benefits:
            st.write("**Benefits (Auszug):**")
            for b in benefits[:12]:
                st.write(f"- {b}")
            shown = True

        if has_meaningful_value(job.remote_policy):
            st.write(f"**Remote Policy:** {job.remote_policy}")
            shown = True
        if not shown:
            st.info(
                "Keine verlässlichen Werte erkannt. Details siehe Gaps/Assumptions."
            )

    def _render_main_slot() -> None:
        with st.expander("Salary Forecast", expanded=True):
            render_salary_forecast_panel(job, get_answers())

        if step is None or not step.questions:
            st.info(
                "Für diesen Abschnitt wurden keine spezifischen Fragen erzeugt. Du kannst trotzdem weitergehen."
            )
            return

        render_question_step(step)

    def _render_review_slot() -> None:
        if step is None or not step.questions:
            return
        review_payload = build_step_review_payload(step)
        render_step_review_card(
            step=step,
            visible_questions=review_payload["visible_questions"],
            answers=review_payload["answers"],
            answer_meta=review_payload["answer_meta"],
            answered_lookup=review_payload["answered_lookup"],
            step_status=review_payload["step_status"],
        )

    render_step_shell(
        title="Benefits & Rahmenbedingungen",
        subtitle=(
            "Hier geht es um das Gesamtpaket: Gehaltsband (falls möglich), "
            "Remote/Hybrid, Arbeitszeit, Benefits, Relocation, Learning Budget "
            "– inklusive der Dinge, die man im Recruiting unbedingt konsistent kommunizieren muss."
        ),
        outcome_text=(
            "Ein konsistentes Offer-Narrativ zu Compensation, Arbeitsmodell und Benefits, "
            "das intern und extern einheitlich kommuniziert werden kann."
        ),
        step=step,
        extracted_from_jobspec_slot=_render_extracted_slot,
        extracted_from_jobspec_label="Aus Jobspec extrahiert (Benefits/Comp)",
        main_content_slot=_render_main_slot,
        review_slot=_render_review_slot,
        footer_slot=lambda: nav_buttons(ctx),
    )


PAGE = WizardPage(
    key="benefits",
    title_de="Benefits & Rahmenbedingungen",
    icon="🎁",
    render=render,
    requires_jobspec=True,
)
