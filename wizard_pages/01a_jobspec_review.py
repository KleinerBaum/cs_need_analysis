"""Legacy jobspec review page.

This module is intentionally kept as a non-routable legacy implementation. The active
wizard no longer exposes a separate "Identifizierte Informationen" step; extraction
review and ESCO confirmation are integrated into Start phases B/C.

Some helper behavior in this module is still referenced by focused tests.
"""

from __future__ import annotations

from typing import cast

import streamlit as st

from constants import SSKey
from esco_client import EscoClient
from schemas import JobAdExtract, QuestionPlan
from ui_components import (
    _render_question_limits_editor,
    render_error_banner,
    render_job_extract_overview,
)
from wizard_pages.base import (
    WizardContext,
    WizardPage,
    get_current_ui_mode,
    nav_buttons,
)

from wizard_pages import esco_occupation_ui
from wizard_pages.esco_occupation_ui import render_esco_occupation_confirmation


def _infer_esco_match_explainability(
    *,
    query_text: str,
    selected: dict[str, object],
    options: list[dict[str, object]],
    applied_meta: dict[str, object],
) -> dict[str, object]:
    return cast(
        dict[str, object],
        esco_occupation_ui._infer_esco_match_explainability(
            query_text=query_text,
            selected=selected,
            options=options,
            applied_meta=applied_meta,
        ),
    )


def _load_occupation_title_variants(
    *, occupation_uri: str, languages: list[str]
) -> tuple[dict[str, list[str]], list[str]]:
    return esco_occupation_ui._load_occupation_title_variants(
        occupation_uri=occupation_uri,
        languages=languages,
        client_factory=EscoClient,
    )


def _render_extraction_quality_summary(job: JobAdExtract) -> None:
    expected_fields = [
        "job_title",
        "company_name",
        "role_overview",
        "responsibilities",
        "must_have_skills",
        "location_city",
        "employment_type",
    ]
    populated = 0
    for field_name in expected_fields:
        value = getattr(job, field_name, None)
        if isinstance(value, list):
            if any(str(item).strip() for item in value if item):
                populated += 1
            continue
        if value and str(value).strip():
            populated += 1

    quality_ratio = populated / len(expected_fields)
    if quality_ratio >= 0.75:
        quality_label = "hoch"
    elif quality_ratio >= 0.45:
        quality_label = "mittel"
    else:
        quality_label = "niedrig"

    st.caption(
        "Extraktionsqualität: "
        f"{quality_label} ({populated}/{len(expected_fields)} Kernfelder gefüllt)."
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

    st.header("Identifizierte Informationen")
    st.caption(
        "Hier prüfst und ergänzt du die extrahierten Inhalte, Gaps und Assumptions, "
        "bevor du in den Schritt 'Unternehmen' wechselst."
    )
    render_error_banner()

    st.markdown(f"**Jobtitel:** {job.job_title or '—'}")
    _render_extraction_quality_summary(job)
    render_esco_occupation_confirmation(job)
    unmapped_roles_raw = st.session_state.get(SSKey.ESCO_UNMAPPED_ROLE_TERMS.value, [])
    unmapped_roles = (
        [str(item).strip() for item in unmapped_roles_raw if str(item).strip()]
        if isinstance(unmapped_roles_raw, list)
        else []
    )
    if unmapped_roles:
        st.info(
            "Falls ESCO gerade nicht verfügbar ist, kannst du mit den vorhandenen "
            "Jobspec-Informationen manuell fortfahren und später erneut versuchen."
        )

    with st.sidebar:
        if get_current_ui_mode() == "standard":
            with st.expander("Advanced", expanded=False):
                with st.expander("Fragen pro Step", expanded=False):
                    _render_question_limits_editor(plan, compact=True)
        else:
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
    title_de="Identifizierte Informationen",
    icon="🧾",
    render=render,
    requires_jobspec=True,
)
