# wizard_pages/07_interview.py
from __future__ import annotations

import streamlit as st

from ui_layout import render_step_shell
from ui_components import (
    build_step_review_payload,
    has_meaningful_value,
    render_error_banner,
    render_question_step,
    render_step_review_card,
)
from wizard_pages.base import WizardContext, WizardPage, guard_job_and_plan, nav_buttons


def render(ctx: WizardContext) -> None:
    render_error_banner()

    preflight = guard_job_and_plan(ctx)
    if preflight is None:
        return

    job, plan = preflight

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
        title="Interviewprozess",
        subtitle=(
            "Ziel: Einen klaren, fairen Prozess definieren (Stages, Stakeholder, "
            "Assessments, Timeline) und gleichzeitig das Candidate Experience sicherstellen."
        ),
        outcome_text=(
            "Ein klarer, fairer Interviewablauf mit Verantwortlichkeiten und Timeline "
            "für eine verlässliche Candidate Experience."
        ),
        step=step,
        extracted_from_jobspec_slot=_render_extracted_slot,
        extracted_from_jobspec_label="Aus Jobspec extrahiert (Recruitment Steps)",
        main_content_slot=_render_main_slot,
        review_slot=_render_review_slot,
        footer_slot=lambda: nav_buttons(ctx),
    )


PAGE = WizardPage(
    key="interview",
    title_de="Interviewprozess",
    icon="🗓️",
    render=render,
    requires_jobspec=True,
)
