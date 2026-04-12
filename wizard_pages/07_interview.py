# wizard_pages/07_interview.py
from __future__ import annotations

import streamlit as st

from constants import SSKey
from schemas import JobAdExtract, QuestionPlan, QuestionStep, RecruitmentStep
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
from wizard_pages.base import WizardContext, WizardPage, nav_buttons


def _has_extract_for_keywords(
    *,
    recruitment_steps: list[RecruitmentStep],
    keywords: tuple[str, ...],
) -> bool:
    for step in recruitment_steps:
        source_text = f"{step.name or ''} {step.details or ''}".strip().casefold()
        if source_text and any(keyword in source_text for keyword in keywords):
            return True
    return False


def _render_interview_consistency_checklist(
    *,
    job: JobAdExtract,
    step: QuestionStep | None,
) -> None:
    review_payload = build_step_review_payload(step)
    visible_questions = review_payload["visible_questions"]
    answered_lookup = review_payload["answered_lookup"]
    step_status = review_payload["step_status"]

    checks = [
        (
            "Interview-Stages sind klar beschrieben.",
            bool(job.recruitment_steps)
            or has_answered_question_with_keywords(
                questions=visible_questions,
                answered_lookup=answered_lookup,
                keywords=("stage", "prozess", "schritt", "ablauf", "interview"),
            ),
        ),
        (
            "Verantwortlichkeiten je Stage sind abgestimmt.",
            _has_extract_for_keywords(
                recruitment_steps=job.recruitment_steps,
                keywords=(
                    "hr",
                    "fach",
                    "interviewer",
                    "stakeholder",
                    "panel",
                    "hiring manager",
                ),
            )
            or has_answered_question_with_keywords(
                questions=visible_questions,
                answered_lookup=answered_lookup,
                keywords=(
                    "verantwort",
                    "stakeholder",
                    "interviewer",
                    "panel",
                    "decision",
                ),
            ),
        ),
        (
            "Timeline und Candidate-Updates sind definiert.",
            _has_extract_for_keywords(
                recruitment_steps=job.recruitment_steps,
                keywords=(
                    "timeline",
                    "tage",
                    "week",
                    "deadline",
                    "feedback",
                    "rückmeldung",
                ),
            )
            or has_answered_question_with_keywords(
                questions=visible_questions,
                answered_lookup=answered_lookup,
                keywords=("timeline", "dauer", "feedback", "rückmeldung", "sla"),
            ),
        ),
        (
            "Essenzielle Prozessfragen sind beantwortet.",
            step_status["essentials_total"] == 0
            or step_status["essentials_answered"] == step_status["essentials_total"],
        ),
    ]

    render_recruiting_consistency_checklist(
        title="Recruiting-Konsistenzcheck",
        checks=checks,
        caption="Kurzcheck: Ist der Interviewprozess intern belastbar und für Kandidat:innen klar erklärbar?",
    )


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
        render_standard_step_review(step)
        _render_interview_consistency_checklist(job=job, step=step)

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
