# wizard_pages/02_company.py
from __future__ import annotations

import streamlit as st

from constants import SSKey
from schemas import JobAdExtract, QuestionPlan
from ui_components import (
    has_meaningful_value,
    render_error_banner,
    render_question_step,
)
from wizard_pages.base import WizardContext, WizardPage, nav_buttons


def _format_company_header(job: JobAdExtract) -> str:
    company_name = (job.company_name or "").strip()
    job_title = (job.job_title or "").strip()

    if company_name and job_title:
        return f"Unternehmen · {company_name} ({job_title})"
    if company_name:
        return f"Unternehmen · {company_name}"
    if job_title:
        return f"Unternehmen · Kontext für {job_title}"
    return "Unternehmen"


def _format_company_subheader(job: JobAdExtract) -> str | None:
    location_city = (job.location_city or "").strip()
    remote_policy = (job.remote_policy or "").strip()

    parts = [part for part in [location_city, remote_policy] if part]
    if not parts:
        return None
    return " · ".join(parts)


def _normalize_nace_lookup(raw_lookup: object) -> dict[str, str]:
    if not isinstance(raw_lookup, dict):
        return {}
    normalized: dict[str, str] = {}
    for raw_code, raw_uri in raw_lookup.items():
        code = str(raw_code or "").strip()
        uri = str(raw_uri or "").strip()
        if code and uri:
            normalized[code] = uri
    return normalized


def _render_optional_nace_section() -> None:
    nace_lookup = _normalize_nace_lookup(
        st.session_state.get(SSKey.EURES_NACE_TO_ESCO.value, {})
    )
    has_lookup = bool(nace_lookup)
    configured_source = str(
        st.session_state.get(SSKey.EURES_NACE_SOURCE.value, "") or ""
    ).strip()
    if not has_lookup and not configured_source:
        return

    st.markdown("### NACE (optional)")
    if configured_source:
        st.caption(f"Mapping-Quelle: {configured_source}")

    if not has_lookup:
        st.info(
            "NACE-Mapping ist konfiguriert, aber aktuell nicht im Session-State geladen."
        )
        return

    options = sorted(nace_lookup.keys(), key=str.casefold)
    current_code = str(st.session_state.get(SSKey.COMPANY_NACE_CODE.value, "") or "")
    default_index = options.index(current_code) + 1 if current_code in options else 0

    selected_code = st.selectbox(
        "NACE-Code für diese Vakanz",
        options=[""] + options,
        index=default_index,
        format_func=lambda value: "— nicht gesetzt —" if not value else value,
        key=f"{SSKey.COMPANY_NACE_CODE.value}.widget",
        help=(
            "Optionaler Branchen-Code. Falls gesetzt, wird die gemappte ESCO-URI im "
            "Summary-Readiness-Block berücksichtigt."
        ),
    )
    st.session_state[SSKey.COMPANY_NACE_CODE.value] = selected_code
    if selected_code:
        st.caption(f"Gemappte ESCO-URI: `{nace_lookup.get(selected_code, '')}`")


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

    st.header(_format_company_header(job))
    subheader = _format_company_subheader(job)
    if subheader:
        st.caption(subheader)
    render_error_banner()

    st.write(
        "Hier sammelst du kontextuelle Informationen zum Unternehmen/Business-Bereich, "
        "die Kandidat:innen verstehen müssen (Mission, Markt, Value Prop, Brand, Rahmenbedingungen)."
    )

    with st.expander("Aus Jobspec extrahiert (Company & Location)", expanded=True):
        extracted_rows = [
            ("Unternehmen", job.company_name),
            ("Marke/Brand", job.brand_name),
            ("Ort", job.location_city),
            ("Remote Policy", job.remote_policy),
        ]
        shown = False
        for label, value in extracted_rows:
            if has_meaningful_value(value):
                st.write(f"**{label}:** {str(value).strip()}")
                shown = True
        if not shown:
            st.info(
                "Keine verlässlichen Werte erkannt. Details siehe Gaps/Assumptions."
            )

    _render_optional_nace_section()

    step = next((s for s in plan.steps if s.step_key == "company"), None)
    if step is None or not step.questions:
        st.info(
            "Für diesen Abschnitt wurden keine spezifischen Fragen erzeugt. Du kannst trotzdem weitergehen."
        )
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
