# wizard_pages/07_interview.py
from __future__ import annotations

from datetime import date, datetime, time
from typing import Any

import streamlit as st

from constants import (
    FactKey,
    FactResolutionStatus,
    FactSourceType,
    SSKey,
    STEP_KEY_INTERVIEW,
    STEP_SECTION_EXTRACTED_FROM_JOBSPEC,
    STEP_SECTION_OPEN_QUESTIONS,
    STEP_SECTION_REVIEW,
    STEP_SECTION_SOURCE_COMPARISON,
)
from intake_facts import write_intake_fact_by_legacy_field
from interview_process import (
    build_interview_value_rows,
    default_selected_interview_value_ids,
    normalize_interview_internal_flow,
)
from schemas import JobAdExtract, QuestionStep, RecruitmentStep
from state import get_answers
from step_sections import build_step_shell_section_kwargs
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
from job_extract_evidence import format_provenance_label
from wizard_pages.base import WizardContext, WizardPage, guard_job_and_plan, nav_buttons
from wizard_pages.fact_inputs import (
    compact_text,
    fact_value,
    persist_compact_object,
    persist_fact,
    render_text_area_fact,
    section_container,
    split_lines,
)


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
    return normalize_interview_internal_flow(
        st.session_state.get(SSKey.INTERVIEW_INTERNAL_FLOW.value, {})
    )


def _sync_interview_contact_intake_facts() -> None:
    write_intake_fact_by_legacy_field(
        st.session_state,
        "contacts",
        _read_internal_flow_state().get("contacts"),
    )


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


def _display_value(value: Any) -> str:
    if isinstance(value, bool):
        return "Ja" if value else "Nein"
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, list):
        return ", ".join(compact_text(item) for item in value if compact_text(item))
    return compact_text(value)


def _normalize_object_list(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _append_summary_item(items: list[str], value: Any) -> None:
    text = _display_value(value)
    if text:
        items.append(text)


def _format_stage_summary(step: dict[str, Any] | RecruitmentStep) -> str:
    if isinstance(step, RecruitmentStep):
        name = compact_text(step.name)
        goal = compact_text(step.details)
        duration = None
    else:
        name = compact_text(step.get("name"))
        goal = compact_text(step.get("goal") or step.get("details"))
        duration = step.get("duration_minutes")
    parts = [name]
    if goal:
        parts.append(goal)
    try:
        duration_int = int(duration)
    except (TypeError, ValueError):
        duration_int = 0
    if duration_int:
        parts.append(f"{duration_int} Min.")
    return " - ".join(part for part in parts if part)


def _format_sla_summary(item: dict[str, Any]) -> str:
    event = compact_text(item.get("event"))
    owner = compact_text(item.get("owner"))
    try:
        days = int(item.get("days"))
    except (TypeError, ValueError):
        days = 0
    parts = [event]
    if days:
        parts.append(f"Update binnen {days} Tagen")
    if owner:
        parts.append(owner)
    return " - ".join(part for part in parts if part)


def _format_contact_summary(contact: dict[str, Any]) -> str:
    role_labels = {
        "money": "Budget",
        "authority": "Entscheidung",
        "need": "Fachbedarf",
    }
    role = compact_text(contact.get("role"))
    name = compact_text(contact.get("name"))
    role_label = role_labels.get(role.casefold(), role)
    participates = bool(contact.get("participates_in_interview"))
    interview_datetime = compact_text(contact.get("interview_datetime"))
    parts = [part for part in (role_label, name) if part]
    if participates:
        parts.append("Interview")
    if interview_datetime:
        parts.append(interview_datetime)
    return " - ".join(parts)


def _format_owner_summary(item: dict[str, Any]) -> str:
    stage = compact_text(item.get("stage"))
    owner = compact_text(item.get("owner"))
    role = compact_text(item.get("decision_role"))
    return " - ".join(part for part in (stage, owner, role) if part)


def _format_evidence_summary(item: dict[str, Any]) -> str:
    evidence = compact_text(item.get("item"))
    stage = compact_text(item.get("stage"))
    signal = compact_text(item.get("success_signal"))
    return " - ".join(part for part in (evidence, stage, signal) if part)


def _format_scorecard_summary(raw_scorecard: Any) -> list[str]:
    if not isinstance(raw_scorecard, dict):
        return []
    output: list[str] = []
    stage = compact_text(raw_scorecard.get("stage"))
    if stage:
        output.append(f"Bewertung für {stage}")
    criteria = raw_scorecard.get("criteria")
    if isinstance(criteria, list):
        for criterion in criteria[:4]:
            if not isinstance(criterion, dict):
                continue
            title = compact_text(criterion.get("title"))
            anchor = compact_text(criterion.get("evidence_anchor"))
            weight = compact_text(criterion.get("weight_percent"))
            parts = [title]
            if weight and weight != "0":
                parts.append(f"{weight}%")
            if anchor:
                parts.append(anchor)
            _append_summary_item(output, " - ".join(part for part in parts if part))
    notes = compact_text(raw_scorecard.get("notes"))
    if notes:
        output.append(notes)
    return output


def _render_known_summary_group(
    title: str,
    items: list[str],
    *,
    empty_text: str,
) -> None:
    with section_container(border=True):
        st.markdown(f"**{title}**")
        if not items:
            st.caption(empty_text)
            return
        for item in items[:6]:
            st.write(f"- {item}")
        if len(items) > 6:
            st.caption(f"+{len(items) - 6} weitere Angabe(n)")


def _render_export_selection(rows: list[dict[str, str]]) -> None:
    if not rows:
        return

    option_by_label = {
        f"{row['Bereich']} · {row['Feld']}: {row['Wert']}": row["id"]
        for row in rows
    }
    label_by_id = {row_id: label for label, row_id in option_by_label.items()}
    default_ids = default_selected_interview_value_ids(rows)
    internal_flow = _read_internal_flow_state()
    selected_ids = [
        row_id
        for row_id in internal_flow["selected_value_ids"]
        if row_id in label_by_id
    ] or default_ids
    selected_labels = st.multiselect(
        "In Summary und Export übernehmen",
        options=list(option_by_label),
        default=[label_by_id[row_id] for row_id in selected_ids],
        key="interview.internal.selected_value_labels",
    )
    st.session_state[SSKey.INTERVIEW_INTERNAL_FLOW.value] = {
        **internal_flow,
        "selected_value_ids": [option_by_label[label] for label in selected_labels],
    }
    _sync_interview_contact_intake_facts()


def _render_known_interview_overview(
    *,
    job: JobAdExtract,
    plan: Any,
) -> None:
    internal_flow = _read_internal_flow_state()
    rows = build_interview_value_rows(
        job=job,
        answers=get_answers(),
        plan=plan,
        internal_flow=internal_flow,
    )

    process_items: list[str] = []
    fact_steps = _normalize_object_list(
        fact_value(FactKey.INTERVIEW_RECRUITMENT_STEPS, [])
    )
    for step in fact_steps:
        _append_summary_item(process_items, _format_stage_summary(step))
    if not process_items:
        for step in job.recruitment_steps:
            _append_summary_item(process_items, _format_stage_summary(step))
    for row in rows:
        if row.get("Bereich") in {"Interview", "Timing"}:
            _append_summary_item(process_items, f"{row['Feld']}: {row['Wert']}")

    communication_items: list[str] = []
    for item in _normalize_object_list(
        fact_value(FactKey.INTERVIEW_COMMUNICATION_SLA, [])
    ):
        _append_summary_item(communication_items, _format_sla_summary(item))
    for item in internal_flow["info_loop_items"]:
        _append_summary_item(communication_items, item)
    for row in rows:
        if row.get("Bereich") == "Candidate Communication":
            _append_summary_item(communication_items, f"{row['Feld']}: {row['Wert']}")

    role_items: list[str] = []
    for item in _normalize_object_list(fact_value(FactKey.INTERVIEW_STAGE_OWNERS, [])):
        _append_summary_item(role_items, _format_owner_summary(item))
    for contact in internal_flow["contacts"]:
        if isinstance(contact, dict):
            _append_summary_item(role_items, _format_contact_summary(contact))
    for row in rows:
        if row.get("Bereich") == "Interne Rollen":
            _append_summary_item(role_items, f"{row['Feld']}: {row['Wert']}")

    evaluation_items: list[str] = []
    for item in _normalize_object_list(
        fact_value(FactKey.INTERVIEW_ASSESSMENT_EVIDENCE, [])
    ):
        _append_summary_item(evaluation_items, _format_evidence_summary(item))
    evaluation_items.extend(
        _format_scorecard_summary(fact_value(FactKey.INTERVIEW_SCORECARD_TEMPLATE, {}))
    )
    core_questions = split_lines(fact_value(FactKey.INTERVIEW_CORE_QUESTIONS, []))
    if core_questions:
        evaluation_items.append(f"Kernfragen: {', '.join(core_questions[:4])}")
    compliance_notes = compact_text(fact_value(FactKey.INTERVIEW_COMPLIANCE_NOTES, ""))
    if compliance_notes:
        evaluation_items.append(f"Dokumentation: {compliance_notes}")

    st.markdown("### Bereits bekannt")
    st.caption(
        "Diese Angaben wurden aus Jobspec, bisherigen Antworten und diesem Schritt gesammelt."
    )
    col_process, col_comm = responsive_two_columns(gap="large")
    with col_process:
        _render_known_summary_group(
            "Prozess",
            _normalize_values(process_items),
            empty_text="Noch kein Ablauf erfasst.",
        )
    with col_comm:
        _render_known_summary_group(
            "Kommunikation",
            _normalize_values(communication_items),
            empty_text="Noch keine Update-Regel erfasst.",
        )
    col_roles, col_eval = responsive_two_columns(gap="large")
    with col_roles:
        _render_known_summary_group(
            "Zuständigkeiten",
            _normalize_values(role_items),
            empty_text="Noch keine internen Rollen erfasst.",
        )
    with col_eval:
        _render_known_summary_group(
            "Bewertung",
            _normalize_values(evaluation_items),
            empty_text="Noch keine Bewertungskriterien erfasst.",
        )

    if callable(getattr(st, "expander", None)):
        with st.expander("Summary- und Exportauswahl", expanded=False):
            _render_export_selection(rows)
    else:
        _render_export_selection(rows)


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
            st.caption("Lege fest, wer entscheidet, wer informiert und wer am Interview teilnimmt.")
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
                st.caption("Eine Person kann mehrere Rollen übernehmen.")

        if show_internal_roles:
            if merged_names:
                st.caption("Aus der Jobspec erkannt: " + ", ".join(merged_names))
            cols = responsive_three_columns(gap="large")
            money_seed: dict[str, Any] = {}
            role_display_labels = {
                "Money": "Budget",
                "Authority": "Entscheidung",
                "Need": "Fachbedarf",
            }
            for idx, role in enumerate(role_labels):
                existing_contact: dict[str, Any] = existing_by_role.get(
                    role.casefold(), {}
                )
                if not existing_contact and idx < len(fallback_by_index):
                    existing_contact = fallback_by_index[idx]
                with cols[idx]:
                    role_display = role_display_labels.get(role, role)
                    st.write(f"**{role_display}**")
                    if role != "Money":
                        if st.checkbox(
                            "Daten aus Budget übernehmen",
                            key=f"interview.internal.copy_from_money.{idx}",
                        ):
                            existing_contact = money_seed
                    name = st.text_input(
                        "Name",
                        value=str(existing_contact.get("name") or ""),
                        key=f"interview.internal.name.{idx}",
                    )
                    phone = st.text_input(
                        "Telefon",
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
                        "Bei Interviews dabei",
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
            st.write("**Updates an Kandidat:innen**")
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
                    info_loop_catalog.append((option, "Aus Jobspec oder Interviewdetails erkannt."))

            option_labels = [label for label, _ in info_loop_catalog]
            option_display_map = {
                label: f"{label} — {description}" for label, description in info_loop_catalog
            }
            selected_option = st.selectbox(
                "Nächstes Update",
                options=option_labels,
                key="interview.internal.info_loop_selectbox",
                format_func=lambda item: option_display_map.get(item, item),
            )
            add_col, clear_col = responsive_two_columns(gap="small")
            with add_col:
                if st.button("Update hinzufügen", key="interview.internal.info_loop_add"):
                    if selected_option not in selected_pills:
                        selected_pills.append(selected_option)
            with clear_col:
                if st.button("Auswahl zurücksetzen", key="interview.internal.info_loop_clear"):
                    selected_pills = []

            if selected_pills:
                if hasattr(st, "pills"):
                    st.pills(
                        "Geplante Updates",
                        options=selected_pills,
                        default=selected_pills,
                        selection_mode="single",
                        key="interview.internal.info_loop_selected_view",
                    )
                else:
                    st.caption(", ".join(selected_pills))

    st.session_state[SSKey.INTERVIEW_INTERNAL_FLOW.value] = {
        **internal_flow,
        "contacts": updated_contacts if show_internal_roles else existing_contacts,
        "info_loop_items": (
            selected_pills if show_info_loop else internal_flow["info_loop_items"]
        ),
        "earliest_start_date": (
            earliest_start.isoformat()
            if show_internal_roles
            else internal_flow["earliest_start_date"]
        ),
        "latest_start_date": (
            latest_start.isoformat()
            if show_internal_roles
            else internal_flow["latest_start_date"]
        ),
    }
    _sync_interview_contact_intake_facts()


def _render_interview_value_board(
    *,
    job: JobAdExtract,
    plan: Any,
) -> None:
    rows = build_interview_value_rows(
        job=job,
        answers=get_answers(),
        plan=plan,
        internal_flow=_read_internal_flow_state(),
    )
    if not rows:
        st.info("Keine verlässlichen Werte erkannt. Details siehe Gaps/Assumptions.")
        return

    def _row_provenance(row: dict[str, str]) -> str:
        source = str(row.get("Quelle") or "").strip()
        normalized_source = source.casefold()
        if "jobspec" in normalized_source:
            return format_provenance_label(
                source_type=FactSourceType.JOBSPEC.value,
                resolution_status=FactResolutionStatus.INFERRED.value,
            )
        return format_provenance_label(
            source_type=FactSourceType.MANUAL.value,
            resolution_status=FactResolutionStatus.CONFIRMED.value,
            confirmed=True,
        )

    st.dataframe(
        [
            {
                "Bereich": row["Bereich"],
                "Feld": row["Feld"],
                "Wert": row["Wert"],
                "Quelle": row["Quelle"],
                "Status": row["Status"],
                "Provenienz": _row_provenance(row),
            }
            for row in rows
        ],
        width="stretch",
        hide_index=True,
        column_order=["Bereich", "Feld", "Wert", "Quelle", "Status", "Provenienz"],
        column_config={
            "Bereich": st.column_config.TextColumn("Abschnitt"),
            "Feld": st.column_config.TextColumn("Angabe"),
            "Wert": st.column_config.TextColumn("Inhalt"),
            "Quelle": st.column_config.TextColumn("Quelle"),
            "Status": st.column_config.TextColumn("Status"),
            "Provenienz": st.column_config.TextColumn("Provenienz"),
        },
    )

    option_by_label = {
        f"{row['Bereich']} · {row['Feld']} — {row['Wert']}": row["id"]
        for row in rows
    }
    label_by_id = {row_id: label for label, row_id in option_by_label.items()}
    default_ids = default_selected_interview_value_ids(rows)
    internal_flow = _read_internal_flow_state()
    selected_ids = [
        row_id
        for row_id in internal_flow["selected_value_ids"]
        if row_id in label_by_id
    ] or default_ids
    selected_labels = st.multiselect(
        "Für Summary/Export verwenden",
        options=list(option_by_label),
        default=[label_by_id[row_id] for row_id in selected_ids],
        key="interview.internal.selected_value_labels",
    )
    st.session_state[SSKey.INTERVIEW_INTERNAL_FLOW.value] = {
        **internal_flow,
        "selected_value_ids": [option_by_label[label] for label in selected_labels],
    }
    _sync_interview_contact_intake_facts()


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
    _render_internal_process_container(
        job,
        show_info_loop=False,
        show_internal_roles=True,
    )


def _stage_seed_labels(job: JobAdExtract) -> list[str]:
    labels = [
        compact_text(step.name or step.details)
        for step in job.recruitment_steps
        if compact_text(step.name or step.details)
    ]
    return _normalize_values(labels) or ["HR Screen", "Fachinterview", "Finale Entscheidung"]


def _list_by_stage(raw_items: Any, key_name: str = "stage") -> dict[str, dict[str, Any]]:
    items = raw_items if isinstance(raw_items, list) else []
    output: dict[str, dict[str, Any]] = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        stage = compact_text(item.get(key_name))
        if stage:
            output[stage] = item
    return output


def _render_stage_rows(job: JobAdExtract) -> list[str]:
    existing_steps = _list_by_stage(fact_value(FactKey.INTERVIEW_RECRUITMENT_STEPS, []), "name")
    stage_labels = _stage_seed_labels(job)
    rows: list[dict[str, Any]] = []
    st.markdown("#### Ablauf")
    for idx, stage in enumerate(stage_labels[:5]):
        current = existing_steps.get(stage, {})
        with section_container(border=True):
            name = st.text_input(
                "Stufe",
                value=compact_text(current.get("name") or stage),
                key=f"fact_input.{FactKey.INTERVIEW_RECRUITMENT_STEPS.value}.{idx}.name",
            )
            col_goal, col_duration = responsive_two_columns(gap="large")
            with col_goal:
                goal = st.text_input(
                    "Ziel der Stufe",
                    value=compact_text(current.get("goal") or current.get("details")),
                    key=f"fact_input.{FactKey.INTERVIEW_RECRUITMENT_STEPS.value}.{idx}.goal",
                )
            with col_duration:
                duration = st.number_input(
                    "Dauer",
                    min_value=0,
                    max_value=240,
                    value=int(current.get("duration_minutes") or 45),
                    step=15,
                    key=f"fact_input.{FactKey.INTERVIEW_RECRUITMENT_STEPS.value}.{idx}.duration",
                )
            if name:
                rows.append(
                    {
                        "name": compact_text(name),
                        "goal": compact_text(goal),
                        "duration_minutes": int(duration),
                    }
                )
    persist_fact(FactKey.INTERVIEW_RECRUITMENT_STEPS, rows)
    return [row["name"] for row in rows] or stage_labels


def _render_stage_owner_rows(stage_labels: list[str]) -> None:
    existing = _list_by_stage(fact_value(FactKey.INTERVIEW_STAGE_OWNERS, []))
    rows: list[dict[str, str]] = []
    st.markdown("#### Verantwortung")
    for idx, stage in enumerate(stage_labels[:5]):
        current = existing.get(stage, {})
        cols = responsive_three_columns(gap="large")
        with cols[0]:
            st.caption(stage)
        with cols[1]:
            owner = st.text_input(
                "Verantwortlich",
                value=compact_text(current.get("owner")),
                key=f"fact_input.{FactKey.INTERVIEW_STAGE_OWNERS.value}.{idx}.owner",
            )
        with cols[2]:
            role = st.text_input(
                "Rolle im Entscheidungsprozess",
                value=compact_text(current.get("decision_role")),
                placeholder="z. B. Entscheider, Interviewer, Feedback",
                key=f"fact_input.{FactKey.INTERVIEW_STAGE_OWNERS.value}.{idx}.role",
            )
        if owner or role:
            rows.append(
                {
                    "stage": stage,
                    "owner": compact_text(owner),
                    "decision_role": compact_text(role),
                }
            )
    persist_fact(FactKey.INTERVIEW_STAGE_OWNERS, rows)


def _render_candidate_sla_rows(stage_labels: list[str]) -> None:
    existing = _list_by_stage(fact_value(FactKey.INTERVIEW_COMMUNICATION_SLA, []), "event")
    default_events = ["Bewerbungseingang", "Nach Interview", "Finale Entscheidung"]
    rows: list[dict[str, Any]] = []
    st.markdown("#### Rückmeldefristen")
    for idx, event in enumerate(default_events):
        current = existing.get(event, {})
        cols = responsive_three_columns(gap="large")
        with cols[0]:
            event_name = st.text_input(
                "Moment",
                value=compact_text(current.get("event") or event),
                key=f"fact_input.{FactKey.INTERVIEW_COMMUNICATION_SLA.value}.{idx}.event",
            )
        with cols[1]:
            owner = st.text_input(
                "Verantwortlich",
                value=compact_text(current.get("owner")),
                key=f"fact_input.{FactKey.INTERVIEW_COMMUNICATION_SLA.value}.{idx}.owner",
            )
        with cols[2]:
            days = st.number_input(
                "Update binnen Tagen",
                min_value=0,
                max_value=30,
                value=int(current.get("days") or 2),
                step=1,
                key=f"fact_input.{FactKey.INTERVIEW_COMMUNICATION_SLA.value}.{idx}.days",
            )
        if event_name:
            rows.append(
                {
                    "event": compact_text(event_name),
                    "owner": compact_text(owner),
                    "days": int(days),
                    "stage_hint": stage_labels[min(idx, len(stage_labels) - 1)] if stage_labels else "",
                }
            )
    persist_fact(FactKey.INTERVIEW_COMMUNICATION_SLA, rows)


def _render_assessment_evidence(stage_labels: list[str]) -> None:
    existing = fact_value(FactKey.INTERVIEW_ASSESSMENT_EVIDENCE, [])
    existing_items = existing if isinstance(existing, list) else []
    rows: list[dict[str, str]] = []
    st.markdown("#### Arbeitsproben und Nachweise")
    for idx in range(3):
        current = existing_items[idx] if idx < len(existing_items) and isinstance(existing_items[idx], dict) else {}
        cols = responsive_three_columns(gap="large")
        with cols[0]:
            item = st.text_input(
                "Was wird bewertet?",
                value=compact_text(current.get("item")),
                key=f"fact_input.{FactKey.INTERVIEW_ASSESSMENT_EVIDENCE.value}.{idx}.item",
            )
        with cols[1]:
            stage = st.selectbox(
                "Interviewstufe",
                options=stage_labels or ["Fachinterview"],
                index=0,
                key=f"fact_input.{FactKey.INTERVIEW_ASSESSMENT_EVIDENCE.value}.{idx}.stage",
            )
        with cols[2]:
            signal = st.text_input(
                "Woran erkennt man gute Ergebnisse?",
                value=compact_text(current.get("success_signal")),
                key=f"fact_input.{FactKey.INTERVIEW_ASSESSMENT_EVIDENCE.value}.{idx}.signal",
            )
        if item or signal:
            rows.append(
                {
                    "item": compact_text(item),
                    "stage": compact_text(stage),
                    "success_signal": compact_text(signal),
                }
            )
    persist_fact(FactKey.INTERVIEW_ASSESSMENT_EVIDENCE, rows)


def _render_scorecard(stage_labels: list[str]) -> None:
    current_raw = fact_value(FactKey.INTERVIEW_SCORECARD_TEMPLATE, {})
    current = current_raw if isinstance(current_raw, dict) else {}
    criteria_raw = current.get("criteria", [])
    criteria = criteria_raw if isinstance(criteria_raw, list) else []
    st.markdown("#### Bewertung")
    stage = st.selectbox(
        "Interviewstufe für die Bewertung",
        options=stage_labels or ["Fachinterview"],
        index=0,
        key=f"fact_input.{FactKey.INTERVIEW_SCORECARD_TEMPLATE.value}.stage",
    )
    criteria_rows: list[dict[str, Any]] = []
    for idx in range(4):
        current_criterion = (
            criteria[idx] if idx < len(criteria) and isinstance(criteria[idx], dict) else {}
        )
        with section_container(border=True):
            st.markdown(f"**Bewertungspunkt {idx + 1}**")
            cols = st.columns([2, 1, 1], gap="small")
            with cols[0]:
                title = st.text_input(
                    "Was wird bewertet?",
                    value=compact_text(current_criterion.get("title")),
                    key=f"fact_input.{FactKey.INTERVIEW_SCORECARD_TEMPLATE.value}.criteria.{idx}.title",
                )
            with cols[1]:
                weight = st.number_input(
                    "Gewichtung %",
                    min_value=0,
                    max_value=100,
                    value=int(current_criterion.get("weight_percent") or 0),
                    step=5,
                    key=f"fact_input.{FactKey.INTERVIEW_SCORECARD_TEMPLATE.value}.criteria.{idx}.weight",
                )
            with cols[2]:
                scale = st.text_input(
                    "Skala",
                    value=compact_text(current_criterion.get("scale") or "1-5"),
                    key=f"fact_input.{FactKey.INTERVIEW_SCORECARD_TEMPLATE.value}.criteria.{idx}.scale",
                )
            evidence_anchor = st.text_input(
                "Woran erkennt man gute Antworten?",
                value=compact_text(current_criterion.get("evidence_anchor")),
                key=f"fact_input.{FactKey.INTERVIEW_SCORECARD_TEMPLATE.value}.criteria.{idx}.evidence",
            )
        if title:
            criteria_rows.append(
                {
                    "title": compact_text(title),
                    "weight_percent": int(weight),
                    "scale": compact_text(scale),
                    "evidence_anchor": compact_text(evidence_anchor),
                }
            )
    recommendation_text = st.text_input(
        "Empfehlungen",
        value=", ".join(
            split_lines(current.get("recommendation_options") or ["Strong Yes", "Yes", "Hold", "No"])
        ),
        key=f"fact_input.{FactKey.INTERVIEW_SCORECARD_TEMPLATE.value}.recommendations",
    )
    notes = st.text_area(
        "Notizen zur Bewertung",
        value=str(current.get("notes") or ""),
        height=80,
        key=f"fact_input.{FactKey.INTERVIEW_SCORECARD_TEMPLATE.value}.notes",
    )
    persist_compact_object(
        FactKey.INTERVIEW_SCORECARD_TEMPLATE,
        {
            "stage": stage,
            "criteria": criteria_rows,
            "recommendation_options": split_lines(recommendation_text),
            "notes": notes,
        },
    )


def _render_evaluation_inputs(stage_labels: list[str]) -> None:
    _render_assessment_evidence(stage_labels)
    _render_scorecard(stage_labels)
    core_questions = st.text_area(
        "Welche Fragen sind für alle Kandidat:innen identisch?",
        value="\n".join(split_lines(fact_value(FactKey.INTERVIEW_CORE_QUESTIONS, []))),
        height=110,
        key=f"fact_input.{FactKey.INTERVIEW_CORE_QUESTIONS.value}",
    )
    persist_fact(FactKey.INTERVIEW_CORE_QUESTIONS, split_lines(core_questions))
    render_text_area_fact(
        FactKey.INTERVIEW_COMPLIANCE_NOTES,
        "Datenschutz, Dokumentation oder Compliance",
        height=90,
    )


def _render_combined_interview_workspace(job: JobAdExtract) -> None:
    with section_container(border=True):
        st.markdown("### Interviewprozess planen")
        st.caption(
            "Ablauf, Kommunikation, Zuständigkeiten und Bewertung werden hier zusammen gepflegt."
        )
        tab_labels = [
            "Ablauf",
            "Kommunikation",
            "Team & Entscheidungen",
            "Bewertung",
        ]
        if callable(getattr(st, "tabs", None)):
            tab_flow, tab_comm, tab_team, tab_eval = st.tabs(tab_labels)
            with tab_flow:
                stage_labels = _render_stage_rows(job)
            with tab_comm:
                _render_candidate_sla_rows(stage_labels)
                _render_candidate_communication_container(job)
            with tab_team:
                _render_stage_owner_rows(stage_labels)
                _render_internal_roles_container(job)
            with tab_eval:
                _render_evaluation_inputs(stage_labels)
            return

        stage_labels = _render_stage_rows(job)
        _render_candidate_sla_rows(stage_labels)
        _render_candidate_communication_container(job)
        _render_stage_owner_rows(stage_labels)
        _render_internal_roles_container(job)
        _render_evaluation_inputs(stage_labels)


def render(ctx: WizardContext) -> None:
    render_error_banner()

    preflight = guard_job_and_plan(ctx)
    if preflight is None:
        return

    job, plan = preflight

    step = next((s for s in plan.steps if s.step_key == STEP_KEY_INTERVIEW), None)

    def _render_guidance_slot() -> None:
        st.markdown(
            "\n".join(
                (
                    "- Halte den Ablauf so kurz und nachvollziehbar wie möglich.",
                    "- Lege pro Stufe fest, wer entscheidet und wann Kandidat:innen ein Update erhalten.",
                    "- Nutze die Bewertung nur für Signale, die im Interview wirklich beobachtbar sind.",
                )
            )
        )

    def _render_extracted_slot() -> None:
        _render_known_interview_overview(job=job, plan=plan)

    def _render_source_comparison_slot() -> None:
        _render_combined_interview_workspace(job)
        expander = getattr(st, "expander", None)
        if callable(expander):
            with expander("Leitlinien für den Prozess", expanded=False):
                _render_guidance_slot()
        else:
            _render_guidance_slot()

    def _render_open_questions_slot() -> None:
        st.markdown("#### Offene Fragen")
        if step is None or not step.questions:
            st.info(
                "Für diesen Abschnitt wurden keine spezifischen Fragen erzeugt. Du kannst trotzdem weitergehen."
            )
            return
        render_question_step(step, context_mode="compact")

    def _render_review_slot() -> None:
        st.markdown("#### Review")
        render_standard_step_review(
            step,
            render_mode=resolve_standard_review_mode(context=ReviewRenderContext.STEP_FORM),
        )
        _render_interview_consistency_checklist(job=job, step=step)

    section_kwargs = build_step_shell_section_kwargs(
        step_key=STEP_KEY_INTERVIEW,
        renderers={
            STEP_SECTION_EXTRACTED_FROM_JOBSPEC: _render_extracted_slot,
            STEP_SECTION_SOURCE_COMPARISON: _render_source_comparison_slot,
            STEP_SECTION_OPEN_QUESTIONS: _render_open_questions_slot,
            STEP_SECTION_REVIEW: _render_review_slot,
        },
    )

    render_step_shell(
        title="Interviewprozess klar und fair gestalten",
        subtitle="Klarer Ablauf, verbindliche Updates und faire Bewertung.",
        step=step,
        **section_kwargs,
        footer_slot=lambda: nav_buttons(ctx),
    )


PAGE = WizardPage(
    key=STEP_KEY_INTERVIEW,
    title_de="Interviewprozess",
    icon="🗓️",
    render=render,
    requires_jobspec=True,
)
