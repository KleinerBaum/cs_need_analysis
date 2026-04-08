# ui_components.py
"""Reusable Streamlit UI components."""

from __future__ import annotations

import re
from datetime import date
from collections.abc import Sequence
from typing import Any, Dict, Optional

import streamlit as st

from constants import AnswerType, SSKey, WIDGET_KEY_PREFIX
from llm_client import OpenAICallError
from schemas import (
    Contact,
    JobAdExtract,
    MoneyRange,
    Question,
    QuestionPlan,
    QuestionStep,
    RecruitmentStep,
    VacancyBrief,
)
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


def render_job_extract_overview(
    job: JobAdExtract, plan: QuestionPlan | None = None
) -> None:
    with st.expander(
        "Aus dem Jobspec extrahiert (strukturierte Übersicht)", expanded=True
    ):
        _render_editable_job_extract(job)

    with st.expander("Gaps (fehlende/unklare Punkte)", expanded=True):
        if job.gaps:
            st.write("\n".join([f"- {g}" for g in job.gaps]))
        else:
            st.info("Keine expliziten Gaps erkannt.")

    _render_question_limits_editor(plan)

    with st.expander("Assumptions (Annahmen)", expanded=True):
        if job.assumptions:
            st.write("\n".join([f"- {a}" for a in job.assumptions]))
        else:
            st.info("Keine Annahmen dokumentiert.")


def _render_editable_job_extract(job: JobAdExtract) -> None:
    st.caption(
        "Extrahierte Werte können hier direkt angepasst werden. Änderungen werden sofort gespeichert."
    )
    values = _sanitize_display_value(job.model_dump())

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
            width="stretch",
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
            width="stretch",
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
            values[field] = (
                st.text_area(
                    field.replace("_", " ").title(),
                    value=(values.get(field) or ""),
                    key=f"cs.job_extract.text.{field}",
                    height=130,
                )
                or None
            )
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


def _suggested_question_limit(step: QuestionStep) -> int:
    required_count = sum(1 for question in step.questions if question.required)
    return required_count if required_count > 0 else len(step.questions)


def _render_question_limits_editor(plan: QuestionPlan | None) -> None:
    if plan is None or not plan.steps:
        return

    st.markdown("#### Fragen pro Step")
    st.caption(
        "Lege fest, wie viele Fragen pro Step angezeigt werden. "
        "Standardwert: erforderliche Fragen pro Step (falls keine markiert sind: alle)."
    )

    limits_raw = st.session_state.get(SSKey.QUESTION_LIMITS.value, {})
    limits: dict[str, int] = {}
    if isinstance(limits_raw, dict):
        for key, value in limits_raw.items():
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
            help=f"Maximal {len(step.questions)} verfügbare Fragen in diesem Step.",
        )
        limits[step.step_key] = int(selected)

    st.session_state[SSKey.QUESTION_LIMITS.value] = limits


def _normalize_optional_string(value: Any) -> str | None:
    if not has_meaningful_value(value):
        return None
    text = str(value).strip()
    return text or None


def has_meaningful_value(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, float):
        return not value != value

    text = str(value).strip()
    if not text:
        return False
    lowered = text.lower()
    return lowered not in {"nan", "none", "null", "n/a", "na", "-", "—"}


def _sanitize_display_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: _sanitize_display_value(v) for k, v in value.items()}
    if isinstance(value, list):
        return [
            v
            for item in value
            for v in [_sanitize_display_value(item)]
            if v is not None
        ]
    return value if has_meaningful_value(value) else None


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
        width="stretch",
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


def _get_step_group_rules(step_key: str) -> list[tuple[str, tuple[str, ...]]]:
    """Return ordered grouping rules per step for question rendering."""
    rules: dict[str, list[tuple[str, tuple[str, ...]]]] = {
        "company": [
            (
                "Unternehmenskontext & Business",
                (
                    "unterneh",
                    "company",
                    "markt",
                    "business",
                    "produkt",
                    "mission",
                    "strategie",
                ),
            ),
            (
                "Setup, Zusammenarbeit & Rahmen",
                (
                    "team",
                    "stakeholder",
                    "schnittstelle",
                    "zusammenarbeit",
                    "remote",
                    "standort",
                    "rahmen",
                ),
            ),
        ],
        "team": [
            (
                "Teamstruktur & Verantwortungen",
                (
                    "team",
                    "lead",
                    "reports",
                    "verantwort",
                    "rolle",
                    "hierarchie",
                    "organ",
                ),
            ),
            (
                "Arbeitsweise & Zusammenarbeit",
                (
                    "arbeits",
                    "hybrid",
                    "remote",
                    "schnittstelle",
                    "kommunikation",
                    "prozesse",
                    "kultur",
                ),
            ),
        ],
        "role_tasks": [
            (
                "Scope, Aufgaben & Deliverables",
                (
                    "aufgabe",
                    "scope",
                    "deliver",
                    "projekt",
                    "verantwort",
                    "ergebnis",
                ),
            ),
            (
                "Erfolgskriterien & Stakeholder",
                (
                    "erfolg",
                    "kpi",
                    "ziel",
                    "stakeholder",
                    "entscheidung",
                    "prior",
                ),
            ),
        ],
        "skills": [
            (
                "Must-have & Fachkompetenz",
                (
                    "must",
                    "pflicht",
                    "skill",
                    "tech",
                    "tool",
                    "erfahrung",
                    "expertise",
                ),
            ),
            (
                "Nice-to-have & Entwicklungsfelder",
                (
                    "nice",
                    "optional",
                    "plus",
                    "lernen",
                    "potenzial",
                    "entwicklung",
                    "soft",
                ),
            ),
        ],
        "benefits": [
            (
                "Kompensation & Vertragsrahmen",
                (
                    "gehalt",
                    "salary",
                    "bonus",
                    "vertrag",
                    "arbeitszeit",
                    "stunden",
                    "kondition",
                ),
            ),
            (
                "Benefits, Flexibilität & Entwicklung",
                (
                    "benefit",
                    "remote",
                    "hybrid",
                    "urlaub",
                    "learning",
                    "relocation",
                    "flex",
                ),
            ),
        ],
        "interview": [
            (
                "Interne Ansprechpartner & Prozesssteuerung",
                (
                    "ansprech",
                    "hiring manager",
                    "recruit",
                    "intern",
                    "entscheidung",
                    "freigabe",
                    "prozess",
                ),
            ),
            (
                "Kandidaten-Inputs & Deliverables",
                (
                    "cv",
                    "lebenslauf",
                    "portfolio",
                    "gehalt",
                    "case",
                    "unterlage",
                    "deliver",
                ),
            ),
            (
                "Bewerbungsschritte, Timeline & Kommunikation",
                (
                    "schritt",
                    "interview",
                    "timeline",
                    "stufe",
                    "feedback",
                    "termin",
                    "kommunikation",
                ),
            ),
        ],
    }
    return rules.get(step_key, [])


def _matches_keywords(question: Question, keywords: Sequence[str]) -> bool:
    haystack = " ".join(
        [
            (question.id or ""),
            (question.label or ""),
            (question.help or ""),
            (question.rationale or ""),
        ]
    ).lower()
    return any(keyword.lower() in haystack for keyword in keywords)


def _group_questions(
    step: QuestionStep, questions: list[Question]
) -> list[tuple[str, list[Question]]]:
    grouped: list[tuple[str, list[Question]]] = []
    remaining = questions[:]
    for group_title, keywords in _get_step_group_rules(step.step_key):
        matched = [q for q in remaining if _matches_keywords(q, keywords)]
        if matched:
            grouped.append((group_title, matched))
            remaining = [q for q in remaining if q not in matched]
    if remaining:
        grouped.append(("Weitere Fragen", remaining))
    return grouped


def _render_questions_two_columns(
    questions: list[Question], answers: Dict[str, Any]
) -> None:
    col_left, col_right = st.columns(2, gap="large")
    for index, question in enumerate(questions):
        target_col = col_left if index % 2 == 0 else col_right
        with target_col:
            _render_question(question, answers)


def render_question_step(step: QuestionStep) -> None:
    answers = get_answers()

    if step.description_de:
        st.caption(step.description_de)

    limits_raw = st.session_state.get(SSKey.QUESTION_LIMITS.value, {})
    step_limit: int | None = None
    if isinstance(limits_raw, dict):
        raw_limit = limits_raw.get(step.step_key)
        if isinstance(raw_limit, (int, float, str)):
            try:
                step_limit = int(raw_limit)
            except ValueError:
                step_limit = None

    questions = step.questions
    if step_limit is not None and step_limit > 0:
        questions = step.questions[:step_limit]

    grouped_questions = _group_questions(step, questions)
    for group_title, group_questions in grouped_questions:
        st.markdown(f"#### {group_title}")
        _render_questions_two_columns(group_questions, answers)


def _render_question(q: Question, answers: Dict[str, Any]) -> None:
    key = WIDGET_KEY_PREFIX + q.id
    inferred_default = _infer_default_value(q)
    current_value = answers.get(q.id, inferred_default)
    value: Any = None

    # Helper text for required fields
    label = q.label + (" *" if q.required else "")

    with st.container(border=True):
        if q.answer_type == AnswerType.SHORT_TEXT:
            value = st.text_input(
                label,
                value=str(current_value or ""),
                help=q.help,
                key=key,
                placeholder=q.help or "Kurzantwort eingeben",
            )
        elif q.answer_type == AnswerType.LONG_TEXT:
            value = st.text_area(
                label,
                value=str(current_value or ""),
                help=q.help,
                key=key,
                height=140,
                placeholder=q.help or "Details ergänzen …",
            )
        elif q.answer_type == AnswerType.SINGLE_SELECT:
            options = q.options or []
            if current_value and current_value not in options:
                options = [str(current_value)] + options
            if not q.required:
                options = ["— Bitte wählen —", *options]
            selected_value = str(current_value) if current_value is not None else None
            default_index = (
                options.index(selected_value)
                if selected_value in options
                else (0 if options else None)
            )
            if hasattr(st, "segmented_control") and 2 <= len(options) <= 5:
                value = st.segmented_control(
                    label,
                    options=options,
                    default=options[default_index]
                    if default_index is not None
                    else None,
                    key=key,
                    help=q.help,
                )
            elif len(options) <= 4:
                value = st.radio(
                    label,
                    options=options,
                    index=default_index if default_index is not None else 0,
                    horizontal=True,
                    help=q.help,
                    key=key,
                )
            else:
                value = st.selectbox(
                    label,
                    options=options,
                    index=default_index if default_index is not None else 0,
                    help=q.help,
                    key=key,
                )
            if value == "— Bitte wählen —":
                value = None
        elif q.answer_type == AnswerType.MULTI_SELECT:
            options = q.options or []
            cur_list = [
                v
                for v in (current_value or [])
                if isinstance(v, str) and has_meaningful_value(v)
            ]
            for v in cur_list:
                if v not in options:
                    options = [v] + options
            if hasattr(st, "pills") and options:
                value = (
                    st.pills(
                        label,
                        options=options,
                        default=cur_list,
                        selection_mode="multi",
                        key=key,
                        help=q.help,
                    )
                    or []
                )
            else:
                value = st.multiselect(
                    label, options=options, default=cur_list, help=q.help, key=key
                )
        elif q.answer_type == AnswerType.NUMBER:
            value = _render_number_question(
                key=key, label=label, help_text=q.help, current_value=current_value
            )
        elif q.answer_type == AnswerType.BOOLEAN:
            value = st.toggle(
                label,
                value=bool(current_value) if current_value is not None else False,
                help=q.help,
                key=key,
            )
        elif q.answer_type == AnswerType.DATE:
            d: Optional[date] = None
            if isinstance(current_value, date):
                d = current_value
            elif isinstance(current_value, str) and current_value:
                try:
                    d = date.fromisoformat(current_value)
                except Exception:
                    d = None
            picked_date = st.date_input(label, value=d, help=q.help, key=key)
            value = picked_date.isoformat() if picked_date else None
        else:
            value = st.text_input(
                label, value=str(current_value or ""), help=q.help, key=key
            )

        if q.help:
            st.caption(q.help)

    # Persist answer
    set_answer(q.id, value)

    if st.session_state.get(SSKey.DEBUG.value) and q.rationale:
        st.caption(f"Rationale: {q.rationale}")


def _render_number_question(
    *, key: str, label: str, help_text: str | None, current_value: Any
) -> float | int:
    min_value, max_value = _parse_scale_bounds(f"{label} {help_text or ''}")
    if min_value is not None and max_value is not None and min_value < max_value:
        try:
            current = int(float(current_value))
        except Exception:
            current = min_value
        current = max(min_value, min(current, max_value))
        return st.slider(
            label,
            min_value=min_value,
            max_value=max_value,
            value=current,
            step=1,
            help=help_text,
            key=key,
        )
    try:
        num = (
            float(current_value)
            if current_value is not None and current_value != ""
            else 0
        )
    except Exception:
        num = 0
    return st.number_input(label, value=num, help=help_text, key=key)


def _infer_default_value(q: Question) -> Any:
    if q.default is not None:
        return q.default
    if q.answer_type == AnswerType.SINGLE_SELECT:
        options = q.options or []
        return options[0] if options else None
    if q.answer_type == AnswerType.MULTI_SELECT:
        return []
    if q.answer_type == AnswerType.BOOLEAN:
        return False
    if q.answer_type == AnswerType.NUMBER:
        min_value, max_value = _parse_scale_bounds(f"{q.label} {q.help or ''}")
        if min_value is not None and max_value is not None and min_value < max_value:
            return int((min_value + max_value) / 2)
        return 0
    return None


def _parse_scale_bounds(text: str) -> tuple[int | None, int | None]:
    match = re.search(r"(\d+)\s*[-–]\s*(\d+)", text)
    if not match:
        return None, None
    lower = int(match.group(1))
    upper = int(match.group(2))
    if lower > upper:
        lower, upper = upper, lower
    if upper - lower > 20:
        return None, None
    return lower, upper


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
