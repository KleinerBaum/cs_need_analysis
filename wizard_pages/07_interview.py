# wizard_pages/07_interview.py
from __future__ import annotations

import inspect
from datetime import date, datetime, time
from typing import Any

import streamlit as st

from constants import SSKey
from schemas import JobAdExtract, QuestionStep, RecruitmentStep
from ui_layout import render_step_shell, responsive_three_columns, responsive_two_columns
from ui_components import (
    build_step_review_payload,
    has_answered_question_with_keywords,
    has_meaningful_value,
    render_error_banner,
    render_question_step,
    render_recruiting_consistency_checklist,
    ReviewRenderContext,
    resolve_standard_review_mode,
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
        "Bewerbungseingang bestätigen",
        "Interviewtag abstimmen",
        "Interview-Feedback bündeln",
        "Entscheidung intern freigeben",
        "Kandidat:in über Ergebnis informieren",
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


def _render_internal_process_container(
    job: JobAdExtract,
    *,
    show_info_loop: bool,
    show_internal_roles: bool,
) -> None:
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

    known_domain = ""
    for contact in existing_contacts:
        if not isinstance(contact, dict):
            continue
        email_raw = str(contact.get("email") or "").strip()
        if "@" not in email_raw:
            continue
        domain = email_raw[email_raw.index("@") :].strip()
        if domain and domain != "@":
            known_domain = domain
            break

    role_labels = ("Money", "Authority", "Need")
    existing_by_role = {
        str(contact.get("role") or "").strip().casefold(): contact
        for contact in existing_contacts
        if isinstance(contact, dict)
    }
    fallback_by_index = [
        contact for contact in existing_contacts if isinstance(contact, dict)
    ]
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

    with st.container(border=True):
        updated_contacts: list[dict[str, Any]] = []
        interview_participants: list[str] = []
        earliest_start = earliest_default
        latest_start = latest_default
        selected_pills = [
            str(item)
            for item in internal_flow.get("info_loop_items", [])
            if isinstance(item, str) and str(item).strip()
        ]

        if show_internal_roles:
            st.caption(
                "Interne Rollen helfen bei Prozessklarheit, sind aber nicht zwingend Teil der externen Kommunikation."
            )
            header_col1, header_col2, header_col3 = responsive_three_columns(gap="large")
            with header_col1:
                earliest_start = st.date_input(
                    "Frühestmöglicher Startzeitpunkt",
                    value=earliest_default,
                    key="interview.internal.earliest_start_date",
                )
            with header_col2:
                latest_start = st.date_input(
                    "Spätester Startzeitpunkt",
                    value=latest_default,
                    key="interview.internal.latest_start_date",
                )
            with header_col3:
                st.caption(
                    "MAN-Rollen strukturiert erfassen. Bei kleinen Teams kann eine Person mehrere Rollen übernehmen."
                )

        if show_internal_roles:
            if merged_names:
                st.caption("Erkannte Ansprechpartner (Jobspec): " + ", ".join(merged_names))
            cols = responsive_three_columns(gap="large")
            money_seed: dict[str, Any] = {}
            for idx, role in enumerate(role_labels):
                existing_contact: dict[str, Any] = existing_by_role.get(
                    role.casefold(), {}
                )
                if not existing_contact and idx < len(fallback_by_index):
                    existing_contact = fallback_by_index[idx]
                with cols[idx]:
                    st.write(f"**{role}**")
                    if role != "Money":
                        if st.checkbox(
                            "Daten aus Money übernehmen",
                            key=f"interview.internal.copy_from_money.{idx}",
                        ):
                            existing_contact = money_seed
                    name = st.text_input(
                        "Ansprechpartner",
                        value=str(existing_contact.get("name") or ""),
                        key=f"interview.internal.name.{idx}",
                    )
                    phone = st.text_input(
                        "Telefonnummer",
                        value=str(existing_contact.get("phone") or ""),
                        key=f"interview.internal.phone.{idx}",
                    )
                    email_default = str(existing_contact.get("email") or "")
                    if not email_default and known_domain:
                        email_default = known_domain
                    email = st.text_input(
                        "E-Mail-Adresse",
                        value=email_default,
                        key=f"interview.internal.email.{idx}",
                    )
                    takes_part = st.checkbox(
                        "Nimmt an Interviews teil",
                        value=bool(existing_contact.get("participates_in_interview", True)),
                        key=f"interview.internal.participates.{idx}",
                    )
                    interview_iso = ""
                    if takes_part:
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
                        interview_iso = interview_dt.isoformat()
                    if takes_part and name.strip():
                        interview_participants.append(name.strip())

                    contact_payload = {
                        "role": role,
                        "name": name.strip(),
                        "phone": phone.strip(),
                        "email": email.strip(),
                        "participates_in_interview": takes_part,
                        "interview_datetime": interview_iso,
                    }
                    updated_contacts.append(contact_payload)
                    if role == "Money":
                        money_seed = contact_payload
        if show_info_loop:
            st.write("**Interner Recruiting-Infoloop (Pills)**")
            info_loop_catalog = [
            (
                "Bewerbungseingang bestätigen",
                "Schnelle Eingangsbestätigung an Kandidat:in.",
            ),
            (
                "Interviewtag abstimmen",
                "Termin mit allen Interview-Teilnehmenden koordinieren.",
            ),
            (
                "Interview-Feedback bündeln",
                "Feedback gesammelt und konsistent dokumentieren.",
            ),
            (
                "Entscheidung intern freigeben",
                "Freigabe durch zuständige Entscheidungsträger.",
            ),
            (
                "Kandidat:in über Ergebnis informieren",
                "Zeitnahes Update zur Candidate Experience.",
            ),
        ]
            if interview_participants:
                info_loop_catalog.insert(
                    2,
                    (
                        "Interviewtag",
                        "Konkreter Interviewtag für teilnehmende Ansprechpartner.",
                    ),
                )

            extracted_options = _extract_internal_process_pills(job.recruitment_steps)
            for option in extracted_options:
                if option not in {label for label, _ in info_loop_catalog}:
                    info_loop_catalog.append((option, "Aus Jobspec/Interviewdetails erkannt."))

            option_labels = [label for label, _ in info_loop_catalog]
            option_display_map = {
                label: f"{label} — {description}" for label, description in info_loop_catalog
            }
            selected_option = st.selectbox(
                "Wer wird wann informiert?",
                options=option_labels,
                key="interview.internal.info_loop_selectbox",
                format_func=lambda item: option_display_map.get(item, item),
            )
            add_col, clear_col = responsive_two_columns(gap="small")
            with add_col:
                if st.button("Auswahl zum Infoloop hinzufügen", key="interview.internal.info_loop_add"):
                    if selected_option not in selected_pills:
                        selected_pills.append(selected_option)
            with clear_col:
                if st.button("Infoloop leeren", key="interview.internal.info_loop_clear"):
                    selected_pills = []

            if selected_pills:
                if hasattr(st, "pills"):
                    st.pills(
                        "Aktive Recruiting-Pills",
                        options=selected_pills,
                        default=selected_pills,
                        selection_mode="single",
                        key="interview.internal.info_loop_selected_view",
                    )
                else:
                    st.caption(", ".join(selected_pills))

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


def _render_candidate_communication_container(job: JobAdExtract) -> None:
    _render_internal_process_container(
        job,
        show_info_loop=True,
        show_internal_roles=False,
    )


def _render_internal_roles_container(job: JobAdExtract) -> None:
    if hasattr(st, "markdown"):
        st.markdown("#### Interne Rollen und Ansprechpartner")
    is_expert_mode = (
        str(st.session_state.get(SSKey.UI_MODE.value, "standard")).strip().lower()
        == "expert"
    )
    if is_expert_mode:
        _render_internal_process_container(
            job,
            show_info_loop=False,
            show_internal_roles=True,
        )
        return
    with st.expander("Interne Rollen und Ansprechpartner", expanded=False):
        _render_internal_process_container(
            job,
            show_info_loop=False,
            show_internal_roles=True,
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

    def _render_main_slot() -> None:
        if hasattr(st, "markdown"):
            st.markdown("#### Interviewprozess definieren")
        if hasattr(st, "caption"):
            st.caption("Definieren Sie zuerst den Prozess, den Kandidat:innen erleben. Interne Rollen und Benachrichtigungen können danach ergänzt werden.")

        if step is None or not step.questions:
            st.info(
                "Für diesen Abschnitt wurden keine spezifischen Fragen erzeugt. Du kannst trotzdem weitergehen."
            )
            return

        render_question_step(step)

    def _render_review_slot() -> None:
        render_standard_step_review(
            step,
            render_mode=resolve_standard_review_mode(context=ReviewRenderContext.STEP_FORM),
        )
        if not hasattr(st, "container"):
            return

        if hasattr(st, "markdown"):
            st.markdown("#### Candidate Communication")
        _render_candidate_communication_container(job)

        _render_internal_roles_container(job)

        _render_interview_consistency_checklist(job=job, step=step)

    shell_kwargs: dict[str, Any] = {
        "title": "Interviewprozess",
        "subtitle": (
            "Ziel: Einen klaren, fairen Prozess definieren (Stages, Stakeholder, "
            "Assessments, Timeline) und gleichzeitig das Candidate Experience sicherstellen."
        ),
        "outcome_slot": lambda: st.markdown(
            "**Vorteile:** Bilden Sie zu Beginn die internen Prozesse sauber ab und "
            "profitieren so von schnellen Prozessen bei minimalem Aufwand für alle "
            "im Prozess involvierten Parteien."
        ),
        "step": step,
        "extracted_from_jobspec_slot": _render_extracted_slot,
        "extracted_from_jobspec_label": "Details",
        "extracted_from_jobspec_use_expander": False,
        "open_questions_slot": _render_main_slot,
        "review_slot": _render_review_slot,
        "footer_slot": lambda: nav_buttons(ctx),
    }
    if "status_position" in inspect.signature(render_step_shell).parameters:
        shell_kwargs["status_position"] = "before_footer"
    render_step_shell(**shell_kwargs)


PAGE = WizardPage(
    key="interview",
    title_de="Interviewprozess",
    icon="🗓️",
    render=render,
    requires_jobspec=True,
)
