from __future__ import annotations

import streamlit as st

from schemas import QuestionStep
from ui_components import has_meaningful_value, render_standard_step_review
from ui_layout import render_step_shell
from wizard_pages.base import WizardContext, guard_job_and_plan, nav_buttons
from wizard_pages.team_section import render_team_questions_with_optional_esco_context


def render(ctx: WizardContext) -> None:
    preflight = guard_job_and_plan(ctx)
    if preflight is None:
        return
    job, plan = preflight
    step: QuestionStep | None = next((s for s in plan.steps if s.step_key == "team"), None)

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
        render_team_questions_with_optional_esco_context(
            step=step,
            ctx=ctx,
            show_error_banner=True,
        )

    render_step_shell(
        title="Team",
        subtitle="Teamkontext, Schnittstellen und Zusammenarbeit.",
        outcome_text=(
            "Ein abgestimmtes Bild von Team-Setup, Interfaces und Arbeitsweise, "
            "damit die Rolle im echten Kontext bewertet werden kann."
        ),
        step=step,
        extracted_from_jobspec_slot=_render_extracted_slot,
        extracted_from_jobspec_label="Aus Jobspec extrahiert (Team/Org)",
        main_content_slot=_render_main_slot,
        review_slot=lambda: render_standard_step_review(step),
        footer_slot=lambda: nav_buttons(ctx),
    )

# Team questions are rendered exclusively on this Team step (`step_key == "team"`).
# Intentionally no `PAGE` export so routing can stay controlled by the central wizard config.
