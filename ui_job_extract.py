# ui_job_extract.py
"""Jobspec extraction overview and editor UI helpers."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Literal

import streamlit as st

from constants import SSKey, UI_DETAILS_DEFAULT_BY_MODE_TEXT
from job_extract_evidence import (
    add_field_evidence_columns,
    field_evidence_caption_text,
    format_field_evidence_confidence,
    job_extract_field_evidence_by_name,
)
from job_extract_review_helpers import (
    JOB_EXTRACT_DISPLAY_LABELS,
    JOB_EXTRACT_LEGACY_REVIEW_TAB_FIELDS,
    JOB_EXTRACT_REVIEW_EMPTY_FIELDS,
    format_recruitment_steps_value as _format_recruitment_steps_value,
    format_salary_range_value as _format_salary_range_value,
    group_extract_notes_by_legacy_review_tab as _group_extract_notes_by_legacy_review_tab,
    has_meaningful_value,
    normalize_display_text as _normalize_display_text,
    normalize_optional_string as _normalize_optional_string,
    parse_optional_int as _parse_optional_int,
    sanitize_display_value as _sanitize_display_value,
)
from schemas import (
    Contact,
    JobAdExtract,
    MoneyRange,
    QuestionPlan,
    QuestionStep,
    RecruitmentStep,
)

def _render_note_block(title: str, notes: Sequence[str], *, tone: str) -> None:
    cleaned = [str(note).strip() for note in notes if str(note).strip()]
    if not cleaned:
        return
    if tone == "warning":
        st.warning(f"**{title}**\n\n" + "\n".join(f"- {note}" for note in cleaned))
    else:
        st.info(f"**{title}**\n\n" + "\n".join(f"- {note}" for note in cleaned))


def _field_evidence_column_config() -> dict[str, Any]:
    return {
        "confidence": st.column_config.TextColumn("Sicherheit", disabled=True),
        "evidence": st.column_config.TextColumn("Fundstelle", disabled=True),
    }


def _render_field_evidence_caption(field_name: str, evidence_by_field: Mapping[str, Any]) -> None:
    caption = field_evidence_caption_text(field_name, evidence_by_field)
    if caption:
        st.caption(caption)
def render_job_extract_overview(
    job: JobAdExtract,
    plan: QuestionPlan | None = None,
    show_question_limits: bool = True,
    show_heading: bool = True,
    mode: Literal["full", "compact"] = "full",
    show_notes: bool = True,
    show_editor: bool = True,
) -> None:
    del plan, show_question_limits
    if mode == "compact":
        _render_compact_job_extract_overview(job, show_heading=show_heading)
        if show_editor:
            _render_editable_job_extract(job, show_notes=show_notes)
        return

    if show_heading:
        st.markdown("### Identifizierte Informationen")
    if show_editor:
        _render_editable_job_extract(job, show_notes=show_notes)


def _join_compact_location(job: JobAdExtract) -> str:
    location_parts = [
        value
        for value in [
            str(job.location_city or "").strip(),
            str(job.location_country or "").strip(),
        ]
        if value
    ]
    return str(job.place_of_work or "").strip() or ", ".join(location_parts)


def _compact_value_rows(
    fields: Sequence[tuple[str, str, Any]],
    evidence_by_field: Mapping[str, Any],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for field, label, value in fields:
        if not has_meaningful_value(value):
            continue
        evidence = evidence_by_field.get(field)
        rows.append(
            {
                "Angabe": label,
                "Inhalt": str(value),
                "Sicherheit": format_field_evidence_confidence(evidence),
            }
        )
    return rows


def _render_compact_value_section(
    title: str,
    fields: Sequence[tuple[str, str, Any]],
    evidence_by_field: Mapping[str, Any],
) -> bool:
    rows = _compact_value_rows(fields, evidence_by_field)
    if not rows:
        return False
    st.markdown(f"**{title}**")
    st.dataframe(
        rows,
        hide_index=True,
        width="stretch",
        column_config={
            "Angabe": st.column_config.TextColumn("Angabe"),
            "Inhalt": st.column_config.TextColumn("Inhalt"),
            "Sicherheit": st.column_config.TextColumn("Sicherheit"),
        },
    )
    return True


def _render_compact_list_section(
    title: str,
    entries: Any,
    *,
    evidence_field: str,
    evidence_by_field: Mapping[str, Any],
    key: str,
) -> bool:
    source = entries if isinstance(entries, list) else []
    cleaned = [str(item).strip() for item in source if has_meaningful_value(item)]
    if not cleaned:
        return False

    st.markdown(f"**{title}**")
    preview = cleaned[:5]
    st.table([{"#": index + 1, "Eintrag": value} for index, value in enumerate(preview)])
    remaining = len(cleaned) - len(preview)
    if remaining > 0:
        with st.expander(f"Alle {len(cleaned)} Einträge anzeigen", expanded=False):
            st.dataframe(
                [{"#": index + 1, "Eintrag": value} for index, value in enumerate(cleaned)],
                key=key,
                hide_index=True,
                width="stretch",
            )
    del evidence_by_field, evidence_field, title
    return True


def _render_compact_job_extract_overview(
    job: JobAdExtract,
    *,
    show_heading: bool,
) -> None:
    if show_heading:
        st.markdown("### Analyseergebnis")
    st.caption(
        "Die wichtigsten Angaben sind nach Themen gruppiert. Die Prüfung fokussiert "
        "auf Sicherheit, offene Punkte und direkte Korrektur."
    )
    evidence_by_field = job_extract_field_evidence_by_name(job)
    rendered_any = False

    rendered_any = (
        _render_compact_value_section(
            "Kernprofil",
            (
                ("job_title", "Rolle", _normalize_display_text(job.job_title)),
                ("company_name", "Unternehmen", _normalize_display_text(job.company_name)),
                ("brand_name", "Marke", _normalize_display_text(job.brand_name)),
                ("place_of_work", "Ort", _join_compact_location(job)),
                (
                    "employment_type",
                    "Beschäftigungsart",
                    _normalize_display_text(job.employment_type),
                ),
                (
                    "contract_type",
                    "Vertragsart",
                    _normalize_display_text(job.contract_type),
                ),
                (
                    "seniority_level",
                    "Seniorität",
                    _normalize_display_text(job.seniority_level),
                ),
            ),
            evidence_by_field,
        )
        or rendered_any
    )
    rendered_any = (
        _render_compact_value_section(
            "Rahmenbedingungen",
            (
                (
                    "remote_policy",
                    "Remote-Regelung",
                    _normalize_display_text(job.remote_policy),
                ),
                ("start_date", "Startdatum", _normalize_display_text(job.start_date)),
                ("salary_range", "Gehaltsrahmen", _format_salary_range_value(job.salary_range)),
                (
                    "travel_required",
                    "Reisebereitschaft",
                    _normalize_display_text(job.travel_required),
                ),
                ("on_call", "Rufbereitschaft", _normalize_display_text(job.on_call)),
                (
                    "recruitment_steps",
                    "Recruiting-Prozess",
                    _format_recruitment_steps_value(job.recruitment_steps),
                ),
            ),
            evidence_by_field,
        )
        or rendered_any
    )

    list_sections = (
        ("Rolle & Aufgaben", job.responsibilities, "responsibilities"),
        ("Lieferergebnisse", job.deliverables, "deliverables"),
        ("Erfolgskriterien", job.success_metrics, "success_metrics"),
        ("Must-have Skills", job.must_have_skills, "must_have_skills"),
        ("Nice-to-have Skills", job.nice_to_have_skills, "nice_to_have_skills"),
        ("Benefits", job.benefits, "benefits"),
    )
    for title, entries, field in list_sections:
        rendered_any = (
            _render_compact_list_section(
                title,
                entries,
                evidence_field=field,
                evidence_by_field=evidence_by_field,
                key=f"cs.job_extract.preview.{field}",
            )
            or rendered_any
        )

    if not rendered_any:
        st.info("Keine verlässlichen Werte erkannt. Details siehe Gaps/Assumptions.")


def _render_compact_extract_lists(job: JobAdExtract) -> None:
    st.caption(
        "Kompaktansicht für lange Listen. Gezeigt werden zunächst die Top 5 Einträge."
    )
    _render_compact_list_table(
        label="Responsibilities",
        entries=job.responsibilities,
        key="cs.job_extract.preview.responsibilities",
    )
    _render_compact_list_table(
        label="Must-have Skills",
        entries=job.must_have_skills,
        key="cs.job_extract.preview.must_have_skills",
    )
    _render_compact_list_table(
        label="Nice-to-have Skills",
        entries=job.nice_to_have_skills,
        key="cs.job_extract.preview.nice_to_have_skills",
    )


def _render_compact_list_table(*, label: str, entries: Any, key: str) -> None:
    source = entries if isinstance(entries, list) else []
    cleaned = [str(item).strip() for item in source if has_meaningful_value(item)]
    if not cleaned:
        return

    st.markdown(f"**{label}**")
    top_five = cleaned[:5]
    st.table(
        [{"#": index + 1, "Eintrag": value} for index, value in enumerate(top_five)]
    )
    remaining = len(cleaned) - len(top_five)
    if remaining <= 0:
        return
    with st.expander(f"Alle {len(cleaned)} Einträge anzeigen", expanded=False):
        st.dataframe(
            [{"#": index + 1, "Eintrag": value} for index, value in enumerate(cleaned)],
            key=key,
            hide_index=True,
            width="stretch",
        )


def _render_editable_job_extract(job: JobAdExtract, *, show_notes: bool = True) -> None:
    st.caption(
        "Extrahierte Werte können hier direkt angepasst werden. Änderungen werden sofort gespeichert."
    )
    values = _sanitize_display_value(job.model_dump())
    evidence_by_field = job_extract_field_evidence_by_name(job)

    tab_core, tab_location, tab_role, tab_skills, tab_process = st.tabs(
        ["Basis", "Standort", "Rolle", "Skills & Benefits", "Prozess"]
    )
    gap_notes_by_tab = _group_extract_notes_by_legacy_review_tab(job.gaps)
    assumption_notes_by_tab = _group_extract_notes_by_legacy_review_tab(job.assumptions)

    with tab_core:
        if show_notes:
            _render_note_block(
                "Fehlende oder unklare Angaben",
                gap_notes_by_tab["Basis"],
                tone="warning",
            )
            _render_note_block(
                "Annahmen",
                assumption_notes_by_tab["Basis"],
                tone="info",
            )
        core_fields = JOB_EXTRACT_LEGACY_REVIEW_TAB_FIELDS["Basis"]
        core_rows = [
            {
                "field": field,
                "label": JOB_EXTRACT_DISPLAY_LABELS.get(field, field),
                "value": values.get(field) or "",
            }
            for field in core_fields
            if field in values and has_meaningful_value(values.get(field))
        ]
        core_rows = add_field_evidence_columns(core_rows, evidence_by_field)
        if core_rows:
            core_edit = st.data_editor(
                core_rows,
                key="cs.job_extract.core",
                width="stretch",
                hide_index=True,
                num_rows="fixed",
                column_order=["label", "value", "confidence", "evidence"],
                column_config={
                    "label": st.column_config.TextColumn("Angabe", disabled=True),
                    "value": st.column_config.TextColumn("Inhalt"),
                    **_field_evidence_column_config(),
                },
            )
            for row in core_edit:
                field = str(row.get("field", "")).strip()
                if field:
                    values[field] = _normalize_optional_string(row.get("value"))
        else:
            st.info("Keine extrahierten Basiswerte mit Inhalt vorhanden.")

    with tab_location:
        if show_notes:
            _render_note_block(
                "Fehlende oder unklare Angaben",
                gap_notes_by_tab["Standort"],
                tone="warning",
            )
            _render_note_block(
                "Annahmen",
                assumption_notes_by_tab["Standort"],
                tone="info",
            )
        location_fields = JOB_EXTRACT_LEGACY_REVIEW_TAB_FIELDS["Standort"]
        location_rows = [
            {
                "field": field,
                "label": JOB_EXTRACT_DISPLAY_LABELS.get(field, field),
                "value": values.get(field) or "",
            }
            for field in location_fields
            if field in values and has_meaningful_value(values.get(field))
        ]
        location_rows = add_field_evidence_columns(location_rows, evidence_by_field)
        if location_rows:
            location_edit = st.data_editor(
                location_rows,
                key="cs.job_extract.location",
                width="stretch",
                hide_index=True,
                num_rows="fixed",
                column_order=["label", "value", "confidence", "evidence"],
                column_config={
                    "label": st.column_config.TextColumn("Angabe", disabled=True),
                    "value": st.column_config.TextColumn("Inhalt"),
                    **_field_evidence_column_config(),
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
        else:
            st.info("Keine extrahierten Standort-/Org-Werte mit Inhalt vorhanden.")

    with tab_role:
        if show_notes:
            _render_note_block(
                "Fehlende oder unklare Angaben",
                gap_notes_by_tab["Rolle"],
                tone="warning",
            )
            _render_note_block("Annahmen", assumption_notes_by_tab["Rolle"], tone="info")
        text_fields = JOB_EXTRACT_LEGACY_REVIEW_TAB_FIELDS["Rolle"]
        for field in text_fields:
            if (
                has_meaningful_value(values.get(field))
                or field in JOB_EXTRACT_REVIEW_EMPTY_FIELDS
            ):
                _render_field_evidence_caption(field, evidence_by_field)
                values[field] = (
                    st.text_area(
                        JOB_EXTRACT_DISPLAY_LABELS.get(field, field),
                        value=(values.get(field) or ""),
                        key=f"cs.job_extract.text.{field}",
                        height=130,
                    )
                    or None
                )
        for list_field, label in [
            ("responsibilities", "Responsibilities"),
            ("deliverables", "Deliverables"),
            ("success_metrics", "Success Metrics"),
        ]:
            _render_field_evidence_caption(list_field, evidence_by_field)
            values[list_field] = _render_list_editor(
                label=label,
                key=f"cs.job_extract.list.{list_field}",
                entries=values.get(list_field, []),
            )

    with tab_skills:
        if show_notes:
            _render_note_block(
                "Fehlende oder unklare Angaben",
                gap_notes_by_tab["Skills & Benefits"],
                tone="warning",
            )
            _render_note_block(
                "Annahmen",
                assumption_notes_by_tab["Skills & Benefits"],
                tone="info",
            )
        for list_field, label in [
            ("must_have_skills", "Must-have Skills"),
            ("nice_to_have_skills", "Nice-to-have Skills"),
            ("soft_skills", "Soft Skills"),
            ("education", "Education"),
            ("certifications", "Certifications"),
            ("languages", "Languages"),
            ("tech_stack", "Tech Stack"),
            ("domain_expertise", "Domain Expertise"),
            ("benefits", "Benefits"),
        ]:
            _render_field_evidence_caption(list_field, evidence_by_field)
            values[list_field] = _render_list_editor(
                label=label,
                key=f"cs.job_extract.list.{list_field}",
                entries=values.get(list_field, []),
            )
        _render_field_evidence_caption("salary_range", evidence_by_field)
        values["salary_range"] = _render_salary_editor(values.get("salary_range"))

    with tab_process:
        if show_notes:
            _render_note_block(
                "Fehlende oder unklare Angaben",
                gap_notes_by_tab["Prozess"],
                tone="warning",
            )
            _render_note_block("Annahmen", assumption_notes_by_tab["Prozess"], tone="info")
        _render_field_evidence_caption("recruitment_steps", evidence_by_field)
        values["recruitment_steps"] = _render_recruitment_steps_editor(
            values.get("recruitment_steps", [])
        )
        _render_field_evidence_caption("contacts", evidence_by_field)
        values["contacts"] = _render_contacts_editor(values.get("contacts", []))

    try:
        validated = JobAdExtract.model_validate(values)
    except Exception:
        st.warning(
            "Einige Eingaben sind ungültig und wurden nicht übernommen. Bitte Felder prüfen."
        )
        return
    st.session_state[SSKey.JOB_EXTRACT.value] = validated.model_dump()


def _suggested_question_limit(step: QuestionStep) -> int:
    required_count = sum(1 for question in step.questions if question.required)
    return required_count if required_count > 0 else len(step.questions)


def _render_question_limits_editor(
    plan: QuestionPlan | None, compact: bool = False
) -> None:
    if plan is None or not plan.steps:
        return

    heading = "##### Fragen pro Step" if compact else "#### Fragen pro Step"
    st.markdown(heading)
    st.caption(
        "Wird automatisch aus Informationsgrad + Ansichtsmodus berechnet "
        f"({UI_DETAILS_DEFAULT_BY_MODE_TEXT})"
    )

    limits_raw = st.session_state.get(SSKey.QUESTION_LIMITS.value, {})
    limits: dict[str, int] = {}
    if isinstance(limits_raw, dict):
        for key, value in limits_raw.items():
            if isinstance(value, dict):
                value = value.get("limit")
            try:
                limits[str(key)] = int(value)
            except (TypeError, ValueError):
                continue

    for step in plan.steps:
        if not step.questions:
            continue
        fallback = max(1, _suggested_question_limit(step))
        current = limits.get(step.step_key, fallback)
        current = max(1, min(current, len(step.questions)))
        selected = st.number_input(
            f"{step.title_de} ({step.step_key})",
            min_value=1,
            max_value=len(step.questions),
            value=current,
            step=1,
            key=f"cs.question_limit.{step.step_key}",
            disabled=True,
            help=f"Maximal {len(step.questions)} verfügbare Fragen in diesem Step.",
        )
        limits[step.step_key] = int(selected)

    st.session_state[SSKey.QUESTION_LIMITS.value] = limits


def _render_list_editor(*, label: str, key: str, entries: Any) -> list[str]:
    source = entries if isinstance(entries, list) else []
    rows = [{"value": str(item)} for item in source if has_meaningful_value(item)]
    edited_rows = st.data_editor(
        rows,
        key=key,
        width="stretch",
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
    salary_labels = {
        "min": "Mindestgehalt",
        "max": "Maximalgehalt",
        "currency": "Währung",
        "period": "Zeitraum",
        "notes": "Hinweis",
    }
    salary_rows = [
        {"field": field, "label": salary_labels.get(field, field), "value": salary.get(field)}
        for field in ("min", "max", "currency", "period", "notes")
        if has_meaningful_value(salary.get(field))
    ]
    if not salary_rows:
        return None
    edited = st.data_editor(
        salary_rows,
        key="cs.job_extract.salary",
        width="stretch",
        hide_index=True,
        num_rows="fixed",
        column_order=["label", "value"],
        column_config={
            "label": st.column_config.TextColumn("Gehaltsangabe", disabled=True),
            "value": st.column_config.TextColumn("Inhalt"),
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
        if not has_meaningful_value(step.name):
            continue
        rows.append({"name": step.name, "details": step.details})
    edited = st.data_editor(
        rows,
        key="cs.job_extract.recruitment_steps",
        width="stretch",
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
        if not any(
            has_meaningful_value(value) for value in contact.model_dump().values()
        ):
            continue
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
        width="stretch",
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
