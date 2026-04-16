# wizard_pages/07_interview.py
from __future__ import annotations

from datetime import date, datetime, time
from typing import Any

import streamlit as st

from constants import SSKey
from schemas import JobAdExtract, QuestionStep, RecruitmentStep
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


def _normalize_values(values: list[str]) -> list[str]:
    deduped: list[str] = []
    seen: set[str] = set()
    for value in values:
        compact = " ".join(str(value or "").split()).strip()
        normalized = compact.casefold()
        if not compact or normalized in seen:
            continue
        deduped.append(compact)
        seen.add(normalized)
    return deduped


def _read_internal_flow_state() -> dict[str, Any]:
    raw = st.session_state.get(SSKey.INTERVIEW_INTERNAL_FLOW.value, {})
    if not isinstance(raw, dict):
        return {
            "contacts": [],
            "info_loop_items": [],
            "earliest_start_date": None,
            "latest_start_date": None,
        }
    return {
        "contacts": raw.get("contacts", []),
        "info_loop_items": raw.get("info_loop_items", []),
        "earliest_start_date": raw.get("earliest_start_date"),
        "latest_start_date": raw.get("latest_start_date"),
    }


def _extract_contact_names(recruitment_steps: list[RecruitmentStep]) -> list[str]:
    names = [
        str(step.name or "").strip()
        for step in recruitment_steps
        if has_meaningful_value(step.name)
    ]
    return _normalize_values(names)


def _extract_internal_process_pills(
    recruitment_steps: list[RecruitmentStep],
) -> list[str]:
    default_pills = [
        "Teilnahme Interviewrunde festlegen",
        "Betriebsrat-Freigabe einholen",
        "Hiring Manager im Feedbackloop",
        "HR informiert Fachbereich",
        "Entscheidungsgremium dokumentiert",
        "Kandidat:innen-Update terminieren",
    ]
    extracted = [
        str(step.details or "").strip()
        for step in recruitment_steps
        if has_meaningful_value(step.details)
    ]
    return _normalize_values([*default_pills, *extracted])


def _render_interview_datetime_input(*, key: str, default: datetime) -> datetime:
    if hasattr(st, "datetime_input"):
        return st.datetime_input("Interviewtag", value=default, key=key)
    picked_day = st.date_input("Interviewtag", value=default.date(), key=f"{key}.date")
    picked_time = st.time_input("Uhrzeit", value=default.time(), key=f"{key}.time")
    return datetime.combine(picked_day, picked_time)


def _render_internal_process_container(job: JobAdExtract) -> None:
    st.markdown("### Interne Ablaufe")
    internal_flow = _read_internal_flow_state()
    existing_contacts_raw = internal_flow.get("contacts", [])
    existing_contacts = (
        existing_contacts_raw if isinstance(existing_contacts_raw, list) else []
    )

    extracted_names = _extract_contact_names(job.recruitment_steps)
    existing_names = [
        str(item.get("name") or "").strip()
        for item in existing_contacts
        if isinstance(item, dict) and has_meaningful_value(item.get("name"))
    ]
    merged_names = _normalize_values([*extracted_names, *existing_names])

    with st.container(border=True):
        col1, col2, col3 = st.columns((1, 1, 1), gap="large")
        with col1:
            st.write("**Ansprechpartner**")
            contacts_text = st.text_area(
                "Namen (eine Zeile pro Person)",
                value="\n".join(merged_names),
                key="interview.internal.contacts_text",
                height=220,
            )
            contact_names = _normalize_values(contacts_text.splitlines())
            for name in contact_names:
                st.write(f"- {name}")

        updated_contacts: list[dict[str, str]] = []
        with col2:
            st.write("**Kontakt & Interviewtage**")
            earliest_default = date.today()
            earliest_raw = str(internal_flow.get("earliest_start_date") or "").strip()
            if earliest_raw:
                try:
                    earliest_default = date.fromisoformat(earliest_raw)
                except ValueError:
                    earliest_default = date.today()
            latest_default = earliest_default
            latest_raw = str(internal_flow.get("latest_start_date") or "").strip()
            if latest_raw:
                try:
                    latest_default = date.fromisoformat(latest_raw)
                except ValueError:
                    latest_default = earliest_default
            earliest_start = st.date_input(
                "Frühestmöglicher Startzeitpunkt",
                value=earliest_default,
                key="interview.internal.earliest_start_date",
            )
            latest_start = st.date_input(
                "Spätester Startzeitpunkt",
                value=latest_default,
                key="interview.internal.latest_start_date",
            )
            for idx, name in enumerate(contact_names):
                st.markdown(f"**{name}**")
                existing_contact: dict[str, Any] = next(
                    (
                        contact
                        for contact in existing_contacts
                        if str(contact.get("name") or "").strip().casefold()
                        == name.casefold()
                    ),
                    {},
                )
                phone = st.text_input(
                    "Telefonnummer",
                    value=str(existing_contact.get("phone") or ""),
                    key=f"interview.internal.phone.{idx}",
                )
                email = st.text_input(
                    "E-Mail-Adresse",
                    value=str(existing_contact.get("email") or ""),
                    key=f"interview.internal.email.{idx}",
                )
                interview_default = datetime.now().replace(
                    hour=time(9, 0).hour,
                    minute=0,
                    second=0,
                    microsecond=0,
                )
                existing_datetime = str(
                    existing_contact.get("interview_datetime") or ""
                )
                if has_meaningful_value(existing_datetime):
                    try:
                        interview_default = datetime.fromisoformat(existing_datetime)
                    except ValueError:
                        interview_default = interview_default
                interview_dt = _render_interview_datetime_input(
                    key=f"interview.internal.datetime.{idx}",
                    default=interview_default,
                )
                updated_contacts.append(
                    {
                        "name": name,
                        "phone": phone.strip(),
                        "email": email.strip(),
                        "interview_datetime": interview_dt.isoformat(),
                    }
                )

        with col3:
            st.write("**Interner Recruiting-Infoloop (Pills)**")
            pill_options = _extract_internal_process_pills(job.recruitment_steps)
            default_pills = internal_flow.get("info_loop_items", [])
            if hasattr(st, "pills"):
                selected_pills = (
                    st.pills(
                        "Wer wird wann informiert?",
                        options=pill_options,
                        default=[
                            str(item)
                            for item in default_pills
                            if str(item) in pill_options
                        ],
                        selection_mode="multi",
                        key="interview.internal.info_loop_pills",
                    )
                    or []
                )
            else:
                selected_pills = st.multiselect(
                    "Wer wird wann informiert?",
                    options=pill_options,
                    default=[
                        str(item) for item in default_pills if str(item) in pill_options
                    ],
                    key="interview.internal.info_loop_multiselect",
                )
            for item in selected_pills:
                st.write(f"- {item}")

    st.session_state[SSKey.INTERVIEW_INTERNAL_FLOW.value] = {
        "contacts": updated_contacts,
        "info_loop_items": selected_pills,
        "earliest_start_date": earliest_start.isoformat(),
        "latest_start_date": latest_start.isoformat(),
    }


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
        _render_internal_process_container(job)

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
        extracted_from_jobspec_label="Details",
        extracted_from_jobspec_use_expander=False,
        open_questions_slot=_render_main_slot,
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
