# ui_components.py
"""Reusable Streamlit UI components."""

from __future__ import annotations

from datetime import date
from typing import Any, Dict, Optional

import streamlit as st

from constants import AnswerType, SSKey, WIDGET_KEY_PREFIX
from llm_client import OpenAICallError
from schemas import Contact, JobAdExtract, MoneyRange, Question, QuestionStep, RecruitmentStep, VacancyBrief
from state import get_answers, set_answer, set_error


def render_error_banner() -> None:
    err = st.session_state.get(SSKey.LAST_ERROR.value)
    if err:
        st.error(err)
    debug_err = st.session_state.get("cs.last_error_debug")
    if debug_err and bool(st.session_state.get("OPENAI_DEBUG_ERRORS", False)):
        with st.expander("Debug (non-sensitive)", expanded=False):
            st.code(str(debug_err))


def render_openai_error(error: OpenAICallError) -> None:
    """Persist concise user message and optional non-sensitive debug details."""

    set_error(error.ui_message)
    st.session_state["cs.last_error_debug"] = None
    if bool(st.session_state.get("OPENAI_DEBUG_ERRORS", False)):
        details: list[str] = []
        if error.error_code:
            details.append(f"code={error.error_code}")
        if error.debug_detail:
            details.append(error.debug_detail)
        if details:
            st.session_state["cs.last_error_debug"] = " | ".join(details)


def render_job_extract_overview(job: JobAdExtract) -> None:
    with st.expander(
        "Aus dem Jobspec extrahiert (strukturierte Übersicht)", expanded=False
    ):
        _render_editable_job_extract(job)

    with st.expander("Gaps (fehlende/unklare Punkte)", expanded=False):
        if job.gaps:
            st.write("\n".join([f"- {g}" for g in job.gaps]))
        else:
            st.info("Keine expliziten Gaps erkannt.")

    with st.expander("Assumptions (Annahmen)", expanded=False):
        if job.assumptions:
            st.write("\n".join([f"- {a}" for a in job.assumptions]))
        else:
            st.info("Keine Annahmen dokumentiert.")


def _render_editable_job_extract(job: JobAdExtract) -> None:
    st.caption(
        "Extrahierte Werte können hier direkt angepasst werden. Änderungen werden sofort gespeichert."
    )
    values = job.model_dump()

    core_fields = [
        "job_title",
        "company_name",
        "brand_name",
        "language_guess",
        "employment_type",
        "contract_type",
        "seniority_level",
        "start_date",
        "application_deadline",
        "job_ref_number",
        "department_name",
        "reports_to",
    ]
    location_fields = [
        "location_city",
        "location_country",
        "place_of_work",
        "remote_policy",
        "travel_required",
        "on_call",
        "direct_reports_count",
    ]
    text_fields = ["role_overview", "onboarding_notes"]
    list_fields = [
        ("responsibilities", "Responsibilities"),
        ("deliverables", "Deliverables"),
        ("success_metrics", "Success Metrics"),
        ("must_have_skills", "Must-have Skills"),
        ("nice_to_have_skills", "Nice-to-have Skills"),
        ("soft_skills", "Soft Skills"),
        ("education", "Education"),
        ("certifications", "Certifications"),
        ("languages", "Languages"),
        ("tech_stack", "Tech Stack"),
        ("domain_expertise", "Domain Expertise"),
        ("benefits", "Benefits"),
    ]

    tab_core, tab_location, tab_role, tab_skills, tab_process = st.tabs(
        ["Basis", "Standort", "Rolle", "Skills & Benefits", "Prozess"]
    )

    with tab_core:
        core_rows = [
            {"field": field, "value": values.get(field)}
            for field in core_fields
            if field in values
        ]
        core_edit = st.data_editor(
            core_rows,
            key="cs.job_extract.core",
            use_container_width=True,
            hide_index=True,
            num_rows="fixed",
            column_config={
                "field": st.column_config.TextColumn("Feld", disabled=True),
                "value": st.column_config.TextColumn("Wert"),
            },
        )
        for row in core_edit:
            field = str(row.get("field", "")).strip()
            if field:
                values[field] = _normalize_optional_string(row.get("value"))

    with tab_location:
        location_rows = [
            {"field": field, "value": values.get(field)}
            for field in location_fields
            if field in values
        ]
        location_edit = st.data_editor(
            location_rows,
            key="cs.job_extract.location",
            use_container_width=True,
            hide_index=True,
            num_rows="fixed",
            column_config={
                "field": st.column_config.TextColumn("Feld", disabled=True),
                "value": st.column_config.TextColumn("Wert"),
            },
        )
        for row in location_edit:
            field = str(row.get("field", "")).strip()
            if not field:
                continue
            if field == "direct_reports_count":
                values[field] = _parse_optional_int(row.get("value"))
            else:
                values[field] = _normalize_optional_string(row.get("value"))

    with tab_role:
        for field in text_fields:
            values[field] = st.text_area(
                field.replace("_", " ").title(),
                value=(values.get(field) or ""),
                key=f"cs.job_extract.text.{field}",
                height=130,
            ) or None
        for list_field, label in list_fields[:3]:
            values[list_field] = _render_list_editor(
                label=label,
                key=f"cs.job_extract.list.{list_field}",
                entries=values.get(list_field, []),
            )

    with tab_skills:
        for list_field, label in list_fields[3:]:
            values[list_field] = _render_list_editor(
                label=label,
                key=f"cs.job_extract.list.{list_field}",
                entries=values.get(list_field, []),
            )
        values["salary_range"] = _render_salary_editor(values.get("salary_range"))

    with tab_process:
        values["recruitment_steps"] = _render_recruitment_steps_editor(
            values.get("recruitment_steps", [])
        )
        values["contacts"] = _render_contacts_editor(values.get("contacts", []))

    try:
        validated = JobAdExtract.model_validate(values)
    except Exception:
        st.warning(
            "Einige Eingaben sind ungültig und wurden nicht übernommen. Bitte Felder prüfen."
        )
        return
    st.session_state[SSKey.JOB_EXTRACT.value] = validated.model_dump()


def _normalize_optional_string(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _parse_optional_int(value: Any) -> int | None:
    normalized = _normalize_optional_string(value)
    if normalized is None:
        return None
    try:
        return int(float(normalized))
    except ValueError:
        return None


def _render_list_editor(*, label: str, key: str, entries: Any) -> list[str]:
    source = entries if isinstance(entries, list) else []
    rows = [{"value": str(item)} for item in source if str(item).strip()]
    edited_rows = st.data_editor(
        rows,
        key=key,
        use_container_width=True,
        hide_index=True,
        num_rows="dynamic",
        column_config={"value": st.column_config.TextColumn(label)},
    )
    return [
        value
        for row in edited_rows
        for value in [_normalize_optional_string(row.get("value"))]
        if value
    ]


def _render_salary_editor(salary_data: Any) -> dict[str, Any] | None:
    salary = MoneyRange.model_validate(salary_data or {}).model_dump()
    salary_rows = [
        {"field": "min", "value": salary.get("min")},
        {"field": "max", "value": salary.get("max")},
        {"field": "currency", "value": salary.get("currency")},
        {"field": "period", "value": salary.get("period")},
        {"field": "notes", "value": salary.get("notes")},
    ]
    edited = st.data_editor(
        salary_rows,
        key="cs.job_extract.salary",
        use_container_width=True,
        hide_index=True,
        num_rows="fixed",
        column_config={
            "field": st.column_config.TextColumn("Salary Feld", disabled=True),
            "value": st.column_config.TextColumn("Wert"),
        },
    )
    result: dict[str, Any] = {}
    for row in edited:
        field = str(row.get("field", "")).strip()
        if not field:
            continue
        raw = row.get("value")
        if field in {"min", "max"}:
            normalized = _normalize_optional_string(raw)
            if normalized is None:
                result[field] = None
            else:
                try:
                    result[field] = float(normalized)
                except ValueError:
                    result[field] = None
        else:
            result[field] = _normalize_optional_string(raw)
    if not any(v is not None for v in result.values()):
        return None
    return MoneyRange.model_validate(result).model_dump()


def _render_recruitment_steps_editor(steps_data: Any) -> list[dict[str, Any]]:
    source = steps_data if isinstance(steps_data, list) else []
    rows = []
    for item in source:
        step = RecruitmentStep.model_validate(item)
        rows.append({"name": step.name, "details": step.details})
    edited = st.data_editor(
        rows,
        key="cs.job_extract.recruitment_steps",
        use_container_width=True,
        hide_index=True,
        num_rows="dynamic",
        column_config={
            "name": st.column_config.TextColumn("Schritt"),
            "details": st.column_config.TextColumn("Details"),
        },
    )
    result: list[dict[str, Any]] = []
    for row in edited:
        name = _normalize_optional_string(row.get("name"))
        if not name:
            continue
        result.append(
            RecruitmentStep(
                name=name,
                details=_normalize_optional_string(row.get("details")),
            ).model_dump()
        )
    return result


def _render_contacts_editor(contacts_data: Any) -> list[dict[str, Any]]:
    source = contacts_data if isinstance(contacts_data, list) else []
    rows = []
    for item in source:
        contact = Contact.model_validate(item)
        rows.append(
            {
                "name": contact.name,
                "role": contact.role,
                "email": contact.email,
                "phone": contact.phone,
            }
        )
    edited = st.data_editor(
        rows,
        key="cs.job_extract.contacts",
        use_container_width=True,
        hide_index=True,
        num_rows="dynamic",
        column_config={
            "name": st.column_config.TextColumn("Name"),
            "role": st.column_config.TextColumn("Rolle"),
            "email": st.column_config.TextColumn("E-Mail"),
            "phone": st.column_config.TextColumn("Telefon"),
        },
    )
    result: list[dict[str, Any]] = []
    for row in edited:
        normalized = Contact(
            name=_normalize_optional_string(row.get("name")),
            role=_normalize_optional_string(row.get("role")),
            email=_normalize_optional_string(row.get("email")),
            phone=_normalize_optional_string(row.get("phone")),
        ).model_dump()
        if any(value is not None for value in normalized.values()):
            result.append(normalized)
    return result


def render_question_step(step: QuestionStep) -> None:
    answers = get_answers()

    if step.description_de:
        st.caption(step.description_de)

    for q in step.questions:
        _render_question(q, answers)


def _render_question(q: Question, answers: Dict[str, Any]) -> None:
    key = WIDGET_KEY_PREFIX + q.id
    current_value = answers.get(q.id, q.default)

    # Helper text for required fields
    label = q.label + (" *" if q.required else "")

    # Render appropriate widget
    if q.answer_type == AnswerType.SHORT_TEXT:
        value = st.text_input(label, value=current_value or "", help=q.help, key=key)
    elif q.answer_type == AnswerType.LONG_TEXT:
        value = st.text_area(
            label, value=current_value or "", help=q.help, key=key, height=120
        )
    elif q.answer_type == AnswerType.SINGLE_SELECT:
        options = q.options or []
        # Streamlit selectbox needs an index; allow None by adding sentinel
        if current_value and current_value not in options:
            options = [current_value] + options
        value = st.selectbox(
            label,
            options=options,
            index=(options.index(current_value) if current_value in options else 0)
            if options
            else 0,
            help=q.help,
            key=key,
        )
    elif q.answer_type == AnswerType.MULTI_SELECT:
        options = q.options or []
        if current_value is None:
            current_value = []
        # Ensure values are in options
        cur_list = [v for v in (current_value or []) if isinstance(v, str)]
        for v in cur_list:
            if v not in options:
                options = [v] + options
        value = st.multiselect(
            label, options=options, default=cur_list, help=q.help, key=key
        )
    elif q.answer_type == AnswerType.NUMBER:
        try:
            num = (
                float(current_value)
                if current_value is not None and current_value != ""
                else None
            )
        except Exception:
            num = None
        value = st.number_input(
            label, value=num if num is not None else 0.0, help=q.help, key=key
        )
    elif q.answer_type == AnswerType.BOOLEAN:
        value = st.checkbox(
            label,
            value=bool(current_value) if current_value is not None else False,
            help=q.help,
            key=key,
        )
    elif q.answer_type == AnswerType.DATE:
        # Accept ISO string, date, or None
        d: Optional[date] = None
        if isinstance(current_value, date):
            d = current_value
        elif isinstance(current_value, str) and current_value:
            try:
                d = date.fromisoformat(current_value)
            except Exception:
                d = None
        value = st.date_input(label, value=d, help=q.help, key=key)
        # Convert to iso string for JSON friendliness
        value = value.isoformat() if value else None
    else:
        value = st.text_input(
            label, value=str(current_value or ""), help=q.help, key=key
        )

    # Persist answer
    set_answer(q.id, value)

    if st.session_state.get(SSKey.DEBUG.value) and q.rationale:
        st.caption(f"Rationale: {q.rationale}")


def render_brief(brief: VacancyBrief) -> None:
    st.subheader("Recruiting Brief")
    st.markdown(f"**One-liner:** {brief.one_liner}")
    st.markdown("**Hiring Context**")
    st.write(brief.hiring_context)
    st.markdown("**Role Summary**")
    st.write(brief.role_summary)

    st.markdown("**Top Responsibilities**")
    for x in brief.top_responsibilities:
        st.write(f"- {x}")

    st.markdown("**Must-have**")
    for x in brief.must_have:
        st.write(f"- {x}")

    st.markdown("**Nice-to-have**")
    for x in brief.nice_to_have:
        st.write(f"- {x}")

    st.markdown("**Dealbreakers**")
    for x in brief.dealbreakers:
        st.write(f"- {x}")

    st.markdown("**Interview Plan**")
    for x in brief.interview_plan:
        st.write(f"- {x}")

    st.markdown("**Evaluation Rubric**")
    for x in brief.evaluation_rubric:
        st.write(f"- {x}")

    st.markdown("**Risks / Open Questions**")
    for x in brief.risks_open_questions:
        st.write(f"- {x}")

    st.subheader("Job Ad Draft (DE)")
    st.write(brief.job_ad_draft)

    with st.expander("Structured data (JSON)", expanded=False):
        st.json(brief.structured_data, expanded=False)
