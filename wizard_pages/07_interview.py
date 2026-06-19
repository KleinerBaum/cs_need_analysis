# wizard_pages/07_interview.py
from __future__ import annotations

from datetime import date, datetime, time
from typing import Any, Callable

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


def _render_section_form(
    *,
    form_key: str,
    submit_label: str,
    renderer: Callable[[], None],
) -> None:
    if callable(getattr(st, "form", None)) and callable(
        getattr(st, "form_submit_button", None)
    ):
        with st.form(form_key, clear_on_submit=False):
            renderer()
            submitted = st.form_submit_button(submit_label, width="stretch")
        if submitted:
            st.success("Abschnitt gespeichert.")
        return
    renderer()


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
    if hasattr(st, "markdown"):
        st.markdown("#### Interne Rollen und Ansprechpartner")
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
    st.markdown("#### Interviewstufen")
    for idx, stage in enumerate(stage_labels[:5]):
        current = existing_steps.get(stage, {})
        with section_container(border=True):
            name = st.text_input(
                "Stage",
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
                    "Dauer (Minuten)",
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
    st.markdown("#### Stage Owner")
    for idx, stage in enumerate(stage_labels[:5]):
        current = existing.get(stage, {})
        cols = responsive_three_columns(gap="large")
        with cols[0]:
            st.caption(stage)
        with cols[1]:
            owner = st.text_input(
                "Owner",
                value=compact_text(current.get("owner")),
                key=f"fact_input.{FactKey.INTERVIEW_STAGE_OWNERS.value}.{idx}.owner",
            )
        with cols[2]:
            role = st.text_input(
                "Entscheidungsrolle",
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
    st.markdown("#### Candidate Update SLA")
    for idx, event in enumerate(default_events):
        current = existing.get(event, {})
        cols = responsive_three_columns(gap="large")
        with cols[0]:
            event_name = st.text_input(
                "Event",
                value=compact_text(current.get("event") or event),
                key=f"fact_input.{FactKey.INTERVIEW_COMMUNICATION_SLA.value}.{idx}.event",
            )
        with cols[1]:
            owner = st.text_input(
                "Owner",
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
    st.markdown("#### Assessment Evidence")
    for idx in range(3):
        current = existing_items[idx] if idx < len(existing_items) and isinstance(existing_items[idx], dict) else {}
        cols = responsive_three_columns(gap="large")
        with cols[0]:
            item = st.text_input(
                "Nachweis / Arbeitsprobe",
                value=compact_text(current.get("item")),
                key=f"fact_input.{FactKey.INTERVIEW_ASSESSMENT_EVIDENCE.value}.{idx}.item",
            )
        with cols[1]:
            stage = st.selectbox(
                "Stage",
                options=stage_labels or ["Fachinterview"],
                index=0,
                key=f"fact_input.{FactKey.INTERVIEW_ASSESSMENT_EVIDENCE.value}.{idx}.stage",
            )
        with cols[2]:
            signal = st.text_input(
                "Erfolgssignal",
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
    st.markdown("#### Scorecard")
    stage = st.selectbox(
        "Scorecard Stage",
        options=stage_labels or ["Fachinterview"],
        index=0,
        key=f"fact_input.{FactKey.INTERVIEW_SCORECARD_TEMPLATE.value}.stage",
    )
    criteria_rows: list[dict[str, Any]] = []
    for idx in range(4):
        current_criterion = (
            criteria[idx] if idx < len(criteria) and isinstance(criteria[idx], dict) else {}
        )
        cols = st.columns([2, 1, 1], gap="small")
        with cols[0]:
            title = st.text_input(
                "Kriterium",
                value=compact_text(current_criterion.get("title")),
                key=f"fact_input.{FactKey.INTERVIEW_SCORECARD_TEMPLATE.value}.criteria.{idx}.title",
            )
        with cols[1]:
            weight = st.number_input(
                "Gewicht %",
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
            "Evidenzanker",
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
        "Empfehlungsoptionen",
        value=", ".join(
            split_lines(current.get("recommendation_options") or ["Strong Yes", "Yes", "Hold", "No"])
        ),
        key=f"fact_input.{FactKey.INTERVIEW_SCORECARD_TEMPLATE.value}.recommendations",
    )
    notes = st.text_area(
        "Scorecard Notes",
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


def _render_structured_interview_design(job: JobAdExtract) -> None:
    with section_container(border=True):
        st.markdown("### Stage & Evaluation")
        stage_labels = _render_stage_rows(job)
        _render_stage_owner_rows(stage_labels)
        _render_candidate_sla_rows(stage_labels)
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
            "Datenschutz-/Dokumentationspflichten oder Compliance Notes",
            height=90,
        )


def render(ctx: WizardContext) -> None:
    render_error_banner()

    preflight = guard_job_and_plan(ctx)
    if preflight is None:
        return

    job, plan = preflight

    step = next((s for s in plan.steps if s.step_key == STEP_KEY_INTERVIEW), None)

    def _render_extracted_slot() -> None:
        _render_section_form(
            form_key="interview.value_board.form",
            submit_label="Interview-Werte speichern",
            renderer=lambda: _render_interview_value_board(job=job, plan=plan),
        )

    def _render_source_comparison_slot() -> None:
        st.markdown("#### Prozessdesign und interne Steuerung")
        st.caption(
            "Definiere zuerst den sichtbaren Kandidat:innen-Prozess. Danach ergänzt "
            "du interne Rollen, Kommunikation und Zeitfenster."
        )
        _render_section_form(
            form_key="interview.stage_evaluation.form",
            submit_label="Stage & Evaluation speichern",
            renderer=lambda: _render_structured_interview_design(job),
        )

        if hasattr(st, "markdown"):
            st.markdown("#### Candidate Communication")
        _render_candidate_communication_container(job)

        _render_section_form(
            form_key="interview.internal_roles.form",
            submit_label="Interne Rollen speichern",
            renderer=lambda: _render_internal_roles_container(job),
        )

    def _render_open_questions_slot() -> None:
        st.markdown("#### Offene Fragen")
        if step is None or not step.questions:
            st.info(
                "Für diesen Abschnitt wurden keine spezifischen Fragen erzeugt. Du kannst trotzdem weitergehen."
            )
            return
        render_question_step(step)

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
        subtitle=(
            "Definiere zuerst den sichtbaren Kandidat:innen-Prozess. Danach ergänzt du "
            "interne Rollen, Kommunikation und Zeitfenster, damit Candidate Experience "
            "und interne Steuerung zusammenpassen."
        ),
        outcome_text=(
            "Ein klarer, fairer Interviewprozess mit abgestimmten Rollen, "
            "Update-Zeitpunkten und evidenzbasierter Bewertung."
        ),
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
