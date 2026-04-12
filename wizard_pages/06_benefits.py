# wizard_pages/06_benefits.py
from __future__ import annotations

import streamlit as st

from constants import SSKey
from schemas import JobAdExtract, QuestionPlan, QuestionStep
from state import get_answers
from ui_layout import render_step_shell
from ui_components import (
    build_step_review_payload,
    has_answered_question_with_keywords,
    has_meaningful_value,
    render_error_banner,
    render_question_step,
    render_recruiting_consistency_checklist,
    render_standard_step_review,
)
from wizard_pages.base import WizardContext, WizardPage, guard_job_and_plan, nav_buttons
from wizard_pages.salary_forecast_panel import render_salary_forecast_panel


def _render_benefits_consistency_checklist(
    *,
    job: JobAdExtract,
    step: QuestionStep | None,
) -> None:
    review_payload = build_step_review_payload(step)
    visible_questions = review_payload["visible_questions"]
    answered_lookup = review_payload["answered_lookup"]
    step_status = review_payload["step_status"]

    salary_extracted = bool(
        job.salary_range and (job.salary_range.min or job.salary_range.max)
    )
    benefits_extracted = any(has_meaningful_value(item) for item in job.benefits)
    remote_extracted = has_meaningful_value(job.remote_policy)

    checks = [
        (
            "Vergütungsrahmen ist intern abgestimmt und kommunizierbar.",
            salary_extracted
            or has_answered_question_with_keywords(
                questions=visible_questions,
                answered_lookup=answered_lookup,
                keywords=("gehalt", "salary", "vergütung", "compensation"),
            ),
        ),
        (
            "Arbeitsmodell (Remote/Hybrid/Onsite) ist abgestimmt.",
            remote_extracted
            or has_answered_question_with_keywords(
                questions=visible_questions,
                answered_lookup=answered_lookup,
                keywords=("remote", "hybrid", "onsite", "homeoffice", "arbeitsmodell"),
            ),
        ),
        (
            "Benefits sind priorisiert und einheitlich benennbar.",
            benefits_extracted
            or has_answered_question_with_keywords(
                questions=visible_questions,
                answered_lookup=answered_lookup,
                keywords=("benefit", "perk", "zusatz", "budget"),
            ),
        ),
        (
            "Essenzielle Rückfragen für dieses Paket sind beantwortet.",
            step_status["essentials_total"] == 0
            or step_status["essentials_answered"] == step_status["essentials_total"],
        ),
    ]

    render_recruiting_consistency_checklist(
        title="Recruiting-Konsistenzcheck",
        checks=checks,
        caption="Kurzcheck: Ist das Offer-Paket intern abgestimmt und extern klar kommunizierbar?",
    )


def render(ctx: WizardContext) -> None:
    render_error_banner()

    preflight = guard_job_and_plan(ctx)
    if preflight is None:
        return

    job, plan = preflight

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
        render_standard_step_review(step)
        _render_benefits_consistency_checklist(job=job, step=step)

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
