from __future__ import annotations

import math
from contextlib import nullcontext
from time import perf_counter
from typing import Any, Final

import streamlit as st

from constants import (
    AnswerType,
    DEFAULT_ESCO_DATA_SOURCE_MODE,
    ESCO_API_MODES,
    ESCO_DATA_SOURCE_MODES,
    ESCO_RELEASE_LANE_PREVIEW,
    ESCO_RELEASE_LANE_SELECTED_VERSION,
    ESCO_RELEASE_LANE_STABLE,
    FactKey,
    FactResolutionStatus,
    FactSourceType,
    SSKey,
)
from job_extract_evidence import (
    format_field_evidence_confidence,
    format_field_evidence_snippet,
    job_extract_field_evidence_by_name,
)
from job_extract_review_helpers import (
    JOB_EXTRACT_TAB_FIELDS,
    JOB_EXTRACT_HYPOTHESIS_GROUP_LABELS,
    build_job_extract_hypothesis_groups,
    has_meaningful_value,
)
from llm_client import (
    OpenAICallError,
    TASK_EXTRACT_JOB_AD,
    TASK_GENERATE_QUESTION_PLAN,
    extract_job_ad,
    generate_question_plan,
    resolve_model_for_task,
)
from intake_facts import (
    write_intake_fact_by_legacy_field,
    write_job_extract_intake_facts,
)
from i18n import sync_language_state, sync_streamlit_language_widget
from occupation_context import build_occupation_question_context, classify_occupation_context
from parsing import extract_text_from_uploaded_file, redact_pii
from question_progress import (
    is_answered,
    resolve_question_job_extract_value,
    value_hash,
)
from question_plan_compiler import compile_question_plan
from schemas import JobAdExtract, Question, QuestionPlan
from settings_openai import load_openai_settings
from state import (
    clear_error,
    get_esco_occupation_selected,
    get_esco_semantic_context,
    has_confirmed_esco_anchor,
    get_model_override,
    handle_unexpected_exception,
    set_error,
    set_answer,
)
from ui_components import (
    render_error_banner,
    render_intake_process_animation,
    render_job_extract_overview,
    render_openai_error,
)
from usage_utils import usage_has_cache_hit
from usage_events import record_enrichment_timed
from wizard_pages.base import (
    WizardContext,
    _get_esco_config,
    _set_esco_config,
    render_ui_mode_selector,
)
from wizard_pages.esco_occupation_ui import render_esco_occupation_confirmation


SOURCE_TEXT_INPUT_KEY: Final[str] = "cs.source_text_input"
SOURCE_UPLOAD_SIG_KEY: Final[str] = "cs.source_upload_signature"
SOURCE_UPLOAD_TEXT_KEY: Final[str] = "cs.source_uploaded_text"
SOURCE_ACTIVE_KEY: Final[str] = "cs.source_active"
HYPOTHESIS_ACTION_ACCEPT: Final[str] = "accept"
HYPOTHESIS_ACTION_EDIT: Final[str] = "edit"
HYPOTHESIS_ACTION_SKIP: Final[str] = "skip"
_START_ROUTING_LABELS: Final[dict[str, dict[str, str]]] = {
    FactKey.INTAKE_SEARCH_CONFIDENTIALITY.value: {
        "open": "Offen kommunizierbar",
        "limited": "Intern begrenzt",
        "high": "Vertraulich / neutralisieren",
    },
    FactKey.INTAKE_HIRING_REASON.value: {
        "unknown": "Noch unklar",
        "replacement": "Ersatz / Backfill",
        "growth": "Wachstum",
        "new_role": "Neue Rolle / Neuaufbau",
        "internal_move": "Interne Nachfolge",
        "confidential": "Vertrauliche Suche",
    },
    FactKey.INTAKE_URGENCY.value: {
        "unknown": "Noch unklar",
        "low": "Planbar",
        "medium": "Relevant",
        "high": "Dringend",
        "critical": "Kritisch / sofort",
    },
    FactKey.INTAKE_ROLE_DEFINITION_MATURITY.value: {
        "unknown": "Noch unklar",
        "high": "Intern kalibriert",
        "medium": "Teilweise kalibriert",
        "low": "Noch unscharf",
    },
}


def _model_dump_json_compatible(model: Any) -> dict[str, Any]:
    model_dump = getattr(model, "model_dump")
    try:
        return model_dump(mode="json")
    except TypeError:
        return model_dump()


def _sync_deterministic_question_flow(job: JobAdExtract, base_plan: QuestionPlan) -> None:
    semantic_context = get_esco_semantic_context()
    answers_raw = st.session_state.get(SSKey.ANSWERS.value, {})
    answers = answers_raw if isinstance(answers_raw, dict) else {}
    primary_anchor = (
        semantic_context.primary_anchor.model_dump(mode="json")
        if semantic_context.primary_anchor is not None
        else None
    )
    capability_snapshot = semantic_context.capability_snapshot
    profile = classify_occupation_context(
        job=job,
        esco_selected=primary_anchor,
        esco_payload=st.session_state.get(SSKey.ESCO_OCCUPATION_PAYLOAD.value),
        esco_version=(
            capability_snapshot.selected_version if capability_snapshot else None
        ),
        answers=answers,
    )
    esco_config_raw = st.session_state.get(SSKey.ESCO_CONFIG.value, {})
    esco_config = esco_config_raw if isinstance(esco_config_raw, dict) else {}
    essential_raw = st.session_state.get(SSKey.ESCO_CONFIRMED_ESSENTIAL_SKILLS.value)
    optional_raw = st.session_state.get(SSKey.ESCO_CONFIRMED_OPTIONAL_SKILLS.value)
    essential_skills = (
        essential_raw
        if isinstance(essential_raw, list)
        else st.session_state.get(SSKey.ESCO_SKILLS_SELECTED_MUST.value, [])
    )
    optional_skills = (
        optional_raw
        if isinstance(optional_raw, list)
        else st.session_state.get(SSKey.ESCO_SKILLS_SELECTED_NICE.value, [])
    )
    matrix_rows_raw = st.session_state.get(SSKey.ESCO_MATRIX_COVERAGE_ROWS.value, [])
    skill_group_share_raw = st.session_state.get(
        SSKey.ESCO_OCCUPATION_SKILL_GROUP_SHARE.value, []
    )
    question_context = build_occupation_question_context(
        esco_selected=primary_anchor,
        esco_payload=st.session_state.get(SSKey.ESCO_OCCUPATION_PAYLOAD.value),
        essential_skills=essential_skills if isinstance(essential_skills, list) else [],
        optional_skills=optional_skills if isinstance(optional_skills, list) else [],
        matrix_coverage_rows=matrix_rows_raw if isinstance(matrix_rows_raw, list) else [],
        skill_group_share=(
            skill_group_share_raw if isinstance(skill_group_share_raw, list) else []
        ),
        capability_snapshot=capability_snapshot,
        esco_version=(
            capability_snapshot.selected_version if capability_snapshot else None
        ),
        source_mode=(
            capability_snapshot.data_source_mode if capability_snapshot else None
        ),
        language=str(esco_config.get("language") or "de"),
        regulated_profession=profile.regulated_profession,
    )
    compiled = compile_question_plan(
        base_plan=base_plan,
        profile=profile,
        question_context=question_context,
        ui_mode=str(st.session_state.get(SSKey.UI_MODE.value, "standard")),
    )
    st.session_state[SSKey.OCCUPATION_PROFILE.value] = profile.model_dump(mode="json")
    st.session_state[SSKey.OCCUPATION_QUESTION_CONTEXT.value] = (
        question_context.model_dump(mode="json")
    )
    st.session_state[SSKey.OCCUPATION_CLASSIFICATION_TRACE.value] = [
        item.model_dump(mode="json") for item in profile.evidence
    ]
    st.session_state[SSKey.OCCUPATION_PACK_KEYS.value] = list(profile.pack_keys)
    st.session_state[SSKey.QUESTION_FLOW_PROVENANCE.value] = (
        compiled.provenance.model_dump(mode="json")
    )
    st.session_state[SSKey.QUESTION_FLOW_FINGERPRINT.value] = (
        compiled.provenance.profile_fingerprint
    )
    st.session_state[SSKey.QUESTION_PLAN.value] = compiled.plan.model_dump(mode="json")


def _has_promotable_value(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, dict):
        return any(_has_promotable_value(item) for item in value.values())
    if isinstance(value, (list, tuple, set)):
        return any(_has_promotable_value(item) for item in value)
    return True


def _dedupe_strings(values: list[Any]) -> list[str]:
    deduped: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = str(value or "").strip()
        key = text.casefold()
        if not text or key in seen:
            continue
        deduped.append(text)
        seen.add(key)
    return deduped


def _coerce_extract_value_for_question(question: Question, value: Any) -> Any:
    if not _has_promotable_value(value):
        return None
    if question.answer_type == AnswerType.MULTI_SELECT:
        if isinstance(value, list):
            return _dedupe_strings(value)
        return [str(value).strip()]
    if question.answer_type in (AnswerType.SHORT_TEXT, AnswerType.LONG_TEXT):
        if isinstance(value, list):
            return "\n".join(_dedupe_strings(value))
        if isinstance(value, dict):
            return None
        return str(value).strip()
    if question.answer_type == AnswerType.SINGLE_SELECT:
        text = str(value).strip()
        option_values = {
            str(getattr(option, "value", option)).strip()
            for option in question.options or []
            if str(getattr(option, "value", option)).strip()
        }
        if option_values and text not in option_values:
            return None
        return text
    if question.answer_type == AnswerType.NUMBER:
        if isinstance(value, (int, float)):
            return value
        try:
            return float(str(value).strip())
        except ValueError:
            return None
    if question.answer_type == AnswerType.BOOLEAN:
        return value if isinstance(value, bool) else None
    if question.answer_type == AnswerType.DATE:
        return str(value).strip()
    return value


def _seed_list_state_from_jobspec(state_key: SSKey, values: list[Any]) -> None:
    current = st.session_state.get(state_key.value, [])
    if isinstance(current, list) and current:
        return
    deduped = _dedupe_strings(values)
    if deduped:
        st.session_state[state_key.value] = deduped


def _promote_reviewed_job_extract(job: JobAdExtract, plan: QuestionPlan) -> None:
    answers_raw = st.session_state.get(SSKey.ANSWERS.value, {})
    answers = dict(answers_raw) if isinstance(answers_raw, dict) else {}
    meta_raw = st.session_state.get(SSKey.ANSWER_META.value, {})
    meta = dict(meta_raw) if isinstance(meta_raw, dict) else {}
    intake_facts_raw = st.session_state.get(SSKey.INTAKE_FACTS.value)
    intake_facts = intake_facts_raw if isinstance(intake_facts_raw, dict) else {}

    for step in plan.steps:
        for question in step.questions:
            question_meta = meta.get(question.id, {})
            if isinstance(question_meta, dict) and question_meta.get("touched"):
                continue
            if is_answered(
                question,
                answers.get(question.id),
                question_meta if isinstance(question_meta, dict) else {},
            ):
                continue
            extracted_value = resolve_question_job_extract_value(
                question,
                job,
                intake_facts=intake_facts,
            )
            answer_value = _coerce_extract_value_for_question(question, extracted_value)
            if not _has_promotable_value(answer_value):
                continue
            answers[question.id] = answer_value
            meta[question.id] = {
                **(question_meta if isinstance(question_meta, dict) else {}),
                "confirmed": True,
                "touched": False,
                "last_value_hash": value_hash(answer_value),
            }

    st.session_state[SSKey.ANSWERS.value] = answers
    st.session_state[SSKey.ANSWER_META.value] = meta
    write_job_extract_intake_facts(st.session_state, job)
    for question_id, answer_value in answers.items():
        answer_meta = meta.get(question_id, {})
        is_manual_answer = isinstance(answer_meta, dict) and bool(
            answer_meta.get("touched")
        )
        write_intake_fact_by_legacy_field(
            st.session_state,
            str(question_id),
            answer_value,
            source_type=(
                FactSourceType.MANUAL if is_manual_answer else FactSourceType.JOBSPEC
            ),
            source_label=(
                "Manual input" if is_manual_answer else "Jobspec extraction"
            ),
            confidence=1.0 if is_manual_answer else 0.75,
        )
    _seed_list_state_from_jobspec(
        SSKey.ROLE_TASKS_SELECTED,
        [*job.responsibilities, *job.deliverables, *job.success_metrics],
    )
    _seed_list_state_from_jobspec(
        SSKey.SKILLS_SELECTED,
        [
            *job.must_have_skills,
            *job.nice_to_have_skills,
            *job.tech_stack,
            *job.domain_expertise,
        ],
    )


def _preview_height_for_text(text: str) -> int:
    """Return a dynamic textarea height so the preview does not need scrolling."""
    chars_per_line = 95
    line_height_px = 28
    padding_px = 28
    total_lines = sum(
        max(1, math.ceil(len(line) / chars_per_line))
        for line in text.splitlines() or [""]
    )
    return (total_lines * line_height_px) + padding_px


def _manual_input_height_for_text(text: str) -> int:
    """Return a compact default height for short text and grow moderately for longer text."""
    min_height_px = 200
    max_height_px = 380
    return max(min_height_px, min(_preview_height_for_text(text), max_height_px))


def _coerce_hypothesis_edit_value(original_value: Any, edited_text: str) -> Any:
    cleaned = str(edited_text or "").strip()
    if isinstance(original_value, list):
        return _dedupe_strings(
            [
                line.strip(" -•\t")
                for line in cleaned.replace(";", "\n").splitlines()
                if line.strip(" -•\t")
            ]
        )
    if isinstance(original_value, int):
        try:
            return int(float(cleaned))
        except ValueError:
            return original_value
    if isinstance(original_value, float):
        try:
            return float(cleaned)
        except ValueError:
            return original_value
    if isinstance(original_value, bool):
        return cleaned.lower() in {"1", "true", "yes", "ja", "y"}
    return cleaned or None


def _empty_hypothesis_value(original_value: Any) -> Any:
    if isinstance(original_value, list):
        return []
    return None


def _apply_job_extract_hypothesis_updates(
    job: JobAdExtract,
    submitted_rows: list[dict[str, Any]],
) -> JobAdExtract:
    values = job.model_dump(mode="json")
    for row in submitted_rows:
        field_name = str(row.get("field_name") or "").strip()
        if not field_name or field_name not in values:
            continue
        action = str(row.get("action") or HYPOTHESIS_ACTION_ACCEPT)
        original_value = values.get(field_name)
        if action == HYPOTHESIS_ACTION_SKIP:
            values[field_name] = _empty_hypothesis_value(original_value)
            resolution_status = FactResolutionStatus.MISSING
            fact_value = None
        elif action == HYPOTHESIS_ACTION_EDIT:
            values[field_name] = _coerce_hypothesis_edit_value(
                original_value,
                str(row.get("edited_value") or ""),
            )
            resolution_status = FactResolutionStatus.CONFIRMED
            fact_value = values[field_name]
        else:
            resolution_status = (
                FactResolutionStatus.INFERRED
                if row.get("group_key") == "ready_to_accept"
                else FactResolutionStatus.ASSUMED
            )
            fact_value = values[field_name]
        write_intake_fact_by_legacy_field(
            st.session_state,
            field_name,
            fact_value,
            source_type=FactSourceType.JOBSPEC,
            source_label="Jobspec hypothesis review",
            confidence=row.get("confidence") if row.get("confidence") is not None else 0.75,
            evidence_snippet=str(row.get("evidence_snippet") or "").strip() or None,
            confirmed=action == HYPOTHESIS_ACTION_EDIT,
            resolution_status=resolution_status,
        )
    return JobAdExtract.model_validate(values)


def _build_hypothesis_rows_by_tab(
    groups: dict[str, list[dict[str, Any]]],
) -> dict[str, list[dict[str, Any]]]:
    rows_by_field = {
        str(row.get("field_name") or ""): row
        for rows in groups.values()
        for row in rows
    }
    return {
        tab_name: [
            rows_by_field[field_name]
            for field_name in field_names
            if field_name in rows_by_field
            and has_meaningful_value(rows_by_field[field_name].get("value"))
        ]
        for tab_name, field_names in JOB_EXTRACT_TAB_FIELDS.items()
    }


def _build_hypothesis_editor_rows(
    rows: list[dict[str, Any]],
    evidence_by_field: dict[str, Any],
) -> list[dict[str, Any]]:
    editor_rows: list[dict[str, Any]] = []
    for row in rows:
        field_name = str(row.get("field_name") or "")
        editor_rows.append(
            {
                "field_name": field_name,
                "Feld": row.get("label") or field_name,
                "Wert": row.get("display_value") or "",
                "Status": JOB_EXTRACT_HYPOTHESIS_GROUP_LABELS.get(
                    str(row.get("group_key") or ""),
                    str(row.get("group_key") or ""),
                ),
                "Sicherheit": format_field_evidence_confidence(
                    evidence_by_field.get(field_name)
                ),
                "Textstelle": format_field_evidence_snippet(
                    evidence_by_field.get(field_name)
                ),
            }
        )
    return editor_rows


def _collect_hypothesis_editor_updates(
    rows: list[dict[str, Any]],
    edited_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    rows_by_field = {str(row.get("field_name") or ""): row for row in rows}
    edited_by_field = {
        str(row.get("field_name") or ""): row
        for row in edited_rows
        if str(row.get("field_name") or "").strip()
    }
    submitted_rows: list[dict[str, Any]] = []
    for field_name, row in rows_by_field.items():
        edited_row = edited_by_field.get(field_name)
        if edited_row is None:
            submitted_rows.append({**row, "action": HYPOTHESIS_ACTION_SKIP})
            continue
        edited_value = str(edited_row.get("Wert") or "")
        original_value = str(row.get("display_value") or "")
        if not has_meaningful_value(edited_value):
            action = HYPOTHESIS_ACTION_SKIP
        elif not bool(row.get("editable", True)):
            action = HYPOTHESIS_ACTION_ACCEPT
        elif edited_value.strip() != original_value.strip():
            action = HYPOTHESIS_ACTION_EDIT
        else:
            action = HYPOTHESIS_ACTION_ACCEPT
        submitted_rows.append(
            {
                **row,
                "action": action,
                "edited_value": edited_value,
            }
        )
    return submitted_rows


def _normalize_hypothesis_editor_rows(edited_rows: Any) -> list[dict[str, Any]]:
    if isinstance(edited_rows, list):
        return [row for row in edited_rows if isinstance(row, dict)]
    to_dict = getattr(edited_rows, "to_dict", None)
    if callable(to_dict):
        records = to_dict("records")
        if isinstance(records, list):
            return [row for row in records if isinstance(row, dict)]
    return []


def _render_job_extract_hypothesis_form(job: JobAdExtract) -> None:
    values = job.model_dump(mode="json")
    evidence_by_field = job_extract_field_evidence_by_name(job)
    groups = build_job_extract_hypothesis_groups(values, evidence_by_field)
    if not any(groups.values()):
        return
    rows_by_tab = _build_hypothesis_rows_by_tab(groups)
    if not any(rows_by_tab.values()):
        return

    st.markdown("#### Erkannte Angaben prüfen")
    st.caption(
        "Prüfen Sie die erkannten Angaben vor dem Weiterarbeiten. "
        "Korrigieren Sie Werte direkt in der Tabelle oder löschen Sie eine Zeile, "
        "wenn die Angabe nicht übernommen werden soll."
    )
    form_ctx = (
        st.form("cs.jobspec.hypothesis_review_form")
        if hasattr(st, "form")
        else nullcontext()
    )
    submitted_rows: list[dict[str, Any]] = []
    with form_ctx:
        tab_names = [tab_name for tab_name, rows in rows_by_tab.items() if rows]
        tab_contexts = (
            st.tabs(tab_names)
            if hasattr(st, "tabs")
            else [nullcontext()] * len(tab_names)
        )
        for tab_name, tab_ctx in zip(tab_names, tab_contexts):
            with tab_ctx:
                rows = rows_by_tab[tab_name]
                editor_rows = _build_hypothesis_editor_rows(rows, evidence_by_field)
                edited_rows = st.data_editor(
                    editor_rows,
                    key=f"cs.jobspec.hypothesis.{tab_name}.editor",
                    hide_index=True,
                    num_rows="dynamic",
                    width="stretch",
                    column_order=("Feld", "Wert", "Status", "Sicherheit", "Textstelle"),
                    disabled=["Feld", "Status", "Sicherheit", "Textstelle"],
                    column_config={
                        "Feld": st.column_config.TextColumn("Feld"),
                        "Wert": st.column_config.TextColumn("Wert"),
                        "Status": st.column_config.TextColumn("Status"),
                        "Sicherheit": st.column_config.TextColumn("Sicherheit"),
                        "Textstelle": st.column_config.TextColumn("Textstelle"),
                    },
                )
                submitted_rows.extend(
                    _collect_hypothesis_editor_updates(
                        rows,
                        _normalize_hypothesis_editor_rows(edited_rows),
                    )
                )
        submit = (
            st.form_submit_button("Angaben übernehmen")
            if hasattr(st, "form_submit_button")
            else st.button("Angaben übernehmen", key="cs.jobspec.hypothesis.submit")
        )
    if not submit:
        return
    reviewed_job = _apply_job_extract_hypothesis_updates(job, submitted_rows)
    st.session_state[SSKey.JOB_EXTRACT.value] = _model_dump_json_compatible(
        reviewed_job
    )
    st.success("Angaben übernommen.")
    st.rerun()


def _render_identified_information_block(ctx: WizardContext) -> None:
    job_dict = st.session_state.get(SSKey.JOB_EXTRACT.value)
    plan_dict = st.session_state.get(SSKey.QUESTION_PLAN.value)
    if not isinstance(job_dict, dict) or not isinstance(plan_dict, dict):
        return

    job = JobAdExtract.model_validate(job_dict)
    plan = QuestionPlan.model_validate(plan_dict)

    selected_occupation = get_esco_occupation_selected() or {}
    has_confirmed_anchor = has_confirmed_esco_anchor()
    selected_occupation_title = str(selected_occupation.get("title") or "").strip()

    st.caption(
        "Die wichtigsten Angaben sind vorbereitet. Prüfen Sie kurz die Basisdaten "
        "und bestätigen Sie anschließend den passenden Beruf für den Abgleich."
    )
    render_job_extract_overview(
        job,
        plan=plan,
        show_question_limits=False,
        show_heading=False,
        mode="compact",
        show_notes=False,
        show_editor=False,
    )
    _render_job_extract_hypothesis_form(job)

    nav_col_back, nav_col_anchor = st.columns([1, 2], gap="small")
    with nav_col_back:
        if st.button("← Zurück", key="cs.jobspec.ident_info.back"):
            ctx.prev()
            st.rerun()
    with nav_col_anchor:
        if has_confirmed_anchor:
            title = selected_occupation_title or "Referenzberuf"
            st.success(f"Berufsabgleich bestätigt: {title}")
        else:
            st.caption(
                "Optional: Im nächsten Abschnitt können Sie einen Referenzberuf für den "
                "Berufsabgleich bestätigen."
            )


def _set_active_source(source: str, text: str) -> None:
    st.session_state[SSKey.SOURCE_TEXT.value] = text
    st.session_state[SOURCE_ACTIVE_KEY] = source


def _routing_answer(fact_key: FactKey, default: Any) -> Any:
    answers_raw = st.session_state.get(SSKey.ANSWERS.value, {})
    answers = answers_raw if isinstance(answers_raw, dict) else {}
    value = answers.get(fact_key.value, default)
    return default if value is None else value


def _persist_routing_answer(fact_key: FactKey, value: Any) -> None:
    set_answer(fact_key.value, value, fact_key=fact_key.value)


def _render_routing_select(
    *,
    fact_key: FactKey,
    label: str,
    options: tuple[str, ...],
    default: str,
) -> None:
    labels = _START_ROUTING_LABELS[fact_key.value]
    current = str(_routing_answer(fact_key, default) or default)
    if current not in options:
        current = default
    selected = st.selectbox(
        label,
        options=options,
        index=options.index(current),
        format_func=lambda value: labels.get(value, value),
        key=f"cs.start.routing.{fact_key.value}",
    )
    _persist_routing_answer(fact_key, selected)


def _render_start_routing_controls() -> None:
    if not all(hasattr(st, name) for name in ("selectbox", "number_input", "columns")):
        if hasattr(st, "caption"):
            st.caption("Ein paar Informationen vorab: Standardwerte werden verwendet.")
        return

    with st.container(border=True):
        st.markdown("#### Ein paar Informationen vorab")
        st.caption(
            "Diese Metadaten steuern Folgefragen zu Unternehmen, Rolle, Benefits und Interview."
        )
        top_left, top_right = st.columns([1, 1], gap="small")
        with top_left:
            _render_routing_select(
                fact_key=FactKey.INTAKE_SEARCH_CONFIDENTIALITY,
                label="Wie vertraulich ist die Suche?",
                options=("open", "limited", "high"),
                default="open",
            )
        with top_right:
            _render_routing_select(
                fact_key=FactKey.INTAKE_URGENCY,
                label="Wie dringend ist die Besetzung?",
                options=("unknown", "low", "medium", "high", "critical"),
                default="unknown",
            )

        lower_left, lower_mid, lower_right = st.columns([1, 1, 1], gap="small")
        with lower_left:
            _render_routing_select(
                fact_key=FactKey.INTAKE_HIRING_REASON,
                label="Warum wird besetzt?",
                options=(
                    "unknown",
                    "replacement",
                    "growth",
                    "new_role",
                    "internal_move",
                    "confidential",
                ),
                default="unknown",
            )
        with lower_mid:
            current_volume = _routing_answer(FactKey.INTAKE_HIRING_VOLUME, 1)
            try:
                current_volume_int = int(current_volume)
            except (TypeError, ValueError):
                current_volume_int = 1
            hiring_volume = st.number_input(
                "Wie viele Personen sollen besetzt werden?",
                min_value=1,
                max_value=50,
                value=max(1, min(50, current_volume_int)),
                step=1,
                key=f"cs.start.routing.{FactKey.INTAKE_HIRING_VOLUME.value}",
            )
            _persist_routing_answer(FactKey.INTAKE_HIRING_VOLUME, int(hiring_volume))
        with lower_right:
            _render_routing_select(
                fact_key=FactKey.INTAKE_ROLE_DEFINITION_MATURITY,
                label="Ist die Rolle intern kalibriert?",
                options=("unknown", "high", "medium", "low"),
                default="unknown",
            )


def _usage_has_cache_hit(usage: Any) -> bool:
    if isinstance(usage, dict):
        return bool(usage.get("cached"))
    return bool(getattr(usage, "cached", False))


def _on_manual_text_change() -> None:
    manual_text = str(st.session_state.get(SOURCE_TEXT_INPUT_KEY, ""))
    _set_active_source("text", manual_text)


def _extract_upload_to_state(
    upload: object, *, step: str, update_text_widget: bool = True
) -> str | None:
    try:
        uploaded_text, source_meta = extract_text_from_uploaded_file(upload)
        if not uploaded_text.strip():
            raise ValueError("Datei enthält keinen auslesbaren Inhalt.")
    except ValueError as exc:
        set_error(str(exc) or "Datei enthält keinen auslesbaren Inhalt.")
        return None
    except Exception as exc:
        error_type = type(exc).__name__
        handle_unexpected_exception(
            step=step,
            exc=exc,
            error_type=error_type,
            error_code="JOBAD_FILE_READ_UNEXPECTED",
            user_message="Datei konnte nicht gelesen werden.",
        )
        return None

    st.session_state[SOURCE_UPLOAD_TEXT_KEY] = uploaded_text
    st.session_state[SSKey.SOURCE_FILE_META.value] = source_meta
    st.session_state[SOURCE_UPLOAD_SIG_KEY] = (
        source_meta.get("name", ""),
        source_meta.get("size", 0),
    )
    if uploaded_text.strip():
        st.session_state[SOURCE_TEXT_INPUT_KEY] = uploaded_text
    _set_active_source("upload", uploaded_text)
    return uploaded_text


def _on_upload_change() -> None:
    upload = st.session_state.get("cs.source_upload_file")
    if upload is None:
        return

    _extract_upload_to_state(
        upload, step="_on_upload_change.extract_text_from_uploaded_file"
    )


def _has_completed_landing_analysis() -> bool:
    job_dict = st.session_state.get(SSKey.JOB_EXTRACT.value)
    plan_dict = st.session_state.get(SSKey.QUESTION_PLAN.value)
    return isinstance(job_dict, dict) and isinstance(plan_dict, dict)


def _has_completed_intake_analysis() -> bool:
    return _has_completed_landing_analysis()


def _render_phase_a_source_and_privacy_controls() -> bool:
    do_extract = False

    st.markdown(
        """
        <style>
        .st-key-cs_ui_mode [data-baseweb="select"] > div,
        .st-key-cs-ui_mode [data-baseweb="select"] > div {
            background: var(--cs-surface) !important;
            color: var(--cs-text) !important;
            border: 1px solid var(--cs-border) !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    upload_col, text_col = st.columns([1, 1.4], gap="large")
    with upload_col:
        st.file_uploader(
            "PDF, DOCX oder TXT hochladen",
            type=["pdf", "docx", "txt"],
            accept_multiple_files=False,
            key="cs.source_upload_file",
            on_change=_on_upload_change,
        )
        upload = st.session_state.get("cs.source_upload_file")
        if upload is not None:
            current_sig = (
                str(getattr(upload, "name", "") or ""),
                int(getattr(upload, "size", 0) or 0),
            )
            if st.session_state.get(SOURCE_UPLOAD_SIG_KEY) != current_sig:
                _extract_upload_to_state(
                    upload,
                    step="_render_phase_a_source_and_privacy_controls.sync_upload",
                    update_text_widget=True,
                )
        st.markdown("#### Detailgrad")
        render_ui_mode_selector()
        _render_esco_operating_block()
    with text_col:
        manual_text = str(st.session_state.get(SOURCE_TEXT_INPUT_KEY, ""))
        st.text_area(
            "Stellenanzeige oder Jobspec",
            key=SOURCE_TEXT_INPUT_KEY,
            height=min(420, max(280, _manual_input_height_for_text(manual_text))),
            on_change=_on_manual_text_change,
            placeholder="Füge hier den vollständigen Ausschreibungstext ein …",
        )

    _render_start_routing_controls()

    uploaded_text = str(st.session_state.get(SOURCE_UPLOAD_TEXT_KEY, ""))
    upload_meta = st.session_state.get(SSKey.SOURCE_FILE_META.value, {})
    upload = st.session_state.get("cs.source_upload_file")
    last_error = str(st.session_state.get(SSKey.LAST_ERROR.value, "") or "")

    st.markdown("---")
    status_col, chars_col, action_col = st.columns([1.6, 1, 1], gap="small")
    with status_col:
        file_name = str(upload_meta.get("name") or getattr(upload, "name", "") or "")
        if upload is not None:
            st.info(f"Datei bereit: {file_name or 'Unbekannt'}")

        if upload is not None and not uploaded_text and last_error:
            st.error(f"Extraktion fehlgeschlagen: {last_error}")
    with chars_col:
        active_source_text = str(st.session_state.get(SSKey.SOURCE_TEXT.value, ""))
        char_count = len(active_source_text.strip()) if active_source_text else 0
        st.metric("Zeichen", f"{char_count:,}".replace(",", "."))
        if 0 < char_count < 250:
            st.warning("Die Quelle ist sehr kurz. Die Extraktion kann unvollstaendig sein.")
    with action_col:
        do_extract = st.button(
            "Analyse starten",
            width="stretch",
            help="Es wird immer nur die aktuell aktive Quelle analysiert.",
        )

    return do_extract


def _render_esco_operating_block() -> None:
    if not all(hasattr(st, name) for name in ("radio", "selectbox", "caption")):
        if hasattr(st, "caption"):
            st.caption("Berufsabgleich: Standardsprache DE, Alternative EN")
        return

    config = _get_esco_config()
    ui_mode = str(st.session_state.get(SSKey.UI_MODE.value, "standard")).strip().lower()
    is_expert = ui_mode == "expert"
    language_options = ("de", "en")
    selected_language = str(config.get("language") or "de").strip().lower()
    if selected_language not in language_options:
        selected_language = "de"
    fallback_language = str(config.get("fallback_language") or "en").strip().lower()
    if fallback_language not in language_options or fallback_language == selected_language:
        fallback_language = "en" if selected_language == "de" else "de"

    with st.container(border=True):
        st.markdown("#### Berufsabgleich")
        if is_expert:
            st.caption(
                "Technische ESCO-Einstellungen für Version, API und Datenquelle."
            )
        else:
            st.caption(
                "Mithilfe der ESCO-Taxonomie nutzt diese App einen standardisierten "
                "Berufs- und Skill-Bezug, damit Folgefragen besser zur Rolle passen."
            )
            esco_popover = getattr(st, "popover", None)
            if callable(esco_popover):
                with esco_popover("Was ist die ESCO-Taxonomie?"):
                    st.markdown(
                        "**European Skills/Competences, Qualifications and Occupations (ESCO)**"
                    )
                    st.caption(
                        "Die europäische mehrsprachige Klassifikation von Skills, "
                        "Kompetenzen, Qualifikationen und Berufen der Europäischen Kommission."
                    )
                    st.write(
                        "ESCO funktioniert wie ein Wörterbuch: Es beschreibt, identifiziert "
                        "und klassifiziert 3.039 berufliche Tätigkeiten und 13.939 damit "
                        "verknüpfte Skills, übersetzt in 28 Sprachen."
                    )
            else:
                st.caption(
                    "ESCO beschreibt 3.039 Berufe und 13.939 damit verknüpfte Skills "
                    "in 28 Sprachen."
                )
        lang_col, fallback_col = st.columns([1, 1], gap="small")
        with lang_col:
            selected_language = st.radio(
                "Sprache für Vorschläge",
                options=language_options,
                index=language_options.index(selected_language),
                horizontal=True,
                key=f"{SSKey.ESCO_CONFIG.value}.phase_a.language",
                on_change=sync_streamlit_language_widget,
                args=(f"{SSKey.ESCO_CONFIG.value}.phase_a.language",),
            )
            sync_language_state(selected_language)
        with fallback_col:
            fallback_language = st.selectbox(
                "Alternative Sprache",
                options=[value for value in language_options if value != selected_language],
                index=0,
                key=f"{SSKey.ESCO_CONFIG.value}.phase_a.fallback_language",
            )

        release_lane = str(config.get("release_lane") or ESCO_RELEASE_LANE_STABLE)
        selected_version = str(config.get("selected_version") or "").strip()
        api_mode = str(config.get("api_mode") or "hosted").strip().lower()
        data_source_mode = str(
            config.get("data_source_mode") or DEFAULT_ESCO_DATA_SOURCE_MODE
        ).strip().lower()
        view_obsolete = bool(config.get("view_obsolete", False))
        if is_expert:
            release_lane_options = (ESCO_RELEASE_LANE_STABLE, ESCO_RELEASE_LANE_PREVIEW)
            release_lane = st.selectbox(
                "Semantik-Lane",
                options=release_lane_options,
                index=(
                    release_lane_options.index(release_lane)
                    if release_lane in release_lane_options
                    else 0
                ),
                format_func=lambda lane: (
                    f"Stable ({ESCO_RELEASE_LANE_SELECTED_VERSION[ESCO_RELEASE_LANE_STABLE]})"
                    if lane == ESCO_RELEASE_LANE_STABLE
                    else f"Preview ({ESCO_RELEASE_LANE_SELECTED_VERSION[ESCO_RELEASE_LANE_PREVIEW]})"
                ),
                key=f"{SSKey.ESCO_CONFIG.value}.phase_a.release_lane",
            )
            selected_version = ESCO_RELEASE_LANE_SELECTED_VERSION[release_lane]
            api_mode = st.selectbox(
                "API-Modus",
                options=ESCO_API_MODES,
                index=ESCO_API_MODES.index(api_mode) if api_mode in ESCO_API_MODES else 0,
                key=f"{SSKey.ESCO_CONFIG.value}.phase_a.api_mode",
            )
            data_source_mode = st.selectbox(
                "Runtime-Lane",
                options=ESCO_DATA_SOURCE_MODES,
                index=(
                    ESCO_DATA_SOURCE_MODES.index(data_source_mode)
                    if data_source_mode in ESCO_DATA_SOURCE_MODES
                    else 0
                ),
                key=f"{SSKey.ESCO_CONFIG.value}.phase_a.data_source_mode",
            )
            if hasattr(st, "toggle"):
                view_obsolete = st.toggle(
                    "Obsolete anzeigen",
                    value=view_obsolete,
                    key=f"{SSKey.ESCO_CONFIG.value}.phase_a.view_obsolete",
                )
        else:
            release_lane = ESCO_RELEASE_LANE_STABLE
            selected_version = (
                selected_version
                or ESCO_RELEASE_LANE_SELECTED_VERSION[ESCO_RELEASE_LANE_STABLE]
            )

        _set_esco_config(
            release_lane=release_lane,
            selected_version=selected_version,
            view_obsolete=view_obsolete,
            language=selected_language,
            fallback_language=fallback_language,
            api_mode=api_mode,
            data_source_mode=data_source_mode,
        )
        if is_expert:
            st.caption(
                "Diagnose: "
                f"lane={release_lane} · version={selected_version} · "
                f"api={api_mode} · runtime={data_source_mode} · "
                f"language={selected_language}/{fallback_language}"
            )




def _render_source_summary() -> None:
    active_source = str(st.session_state.get(SOURCE_ACTIVE_KEY, "") or "")
    source_label = "Upload" if active_source == "upload" else "Text"
    source_text = str(st.session_state.get(SSKey.SOURCE_TEXT.value, "") or "")
    char_count = len(source_text.strip())

    job_title = ""
    company_name = ""
    job_dict = st.session_state.get(SSKey.JOB_EXTRACT.value)
    if isinstance(job_dict, dict):
        job_title = str(job_dict.get("job_title") or "").strip()
        company_name = str(job_dict.get("company_name") or "").strip()

    summary_parts = [
        f"Quelle: **{source_label}**",
        f"Zeichen: **{char_count:,}**".replace(",", "."),
    ]
    if job_title:
        summary_parts.append(f"Rolle: **{job_title}**")
    if company_name:
        summary_parts.append(f"Unternehmen: **{company_name}**")
    st.caption(" · ".join(summary_parts))


def _render_source_input_section(ctx: WizardContext) -> bool:
    del ctx
    if _has_completed_intake_analysis():
        _render_source_summary()
        container_ctx = (
            st.container(border=True) if hasattr(st, "container") else nullcontext()
        )
        with container_ctx:
            if hasattr(st, "markdown"):
                st.markdown("#### Quelle bearbeiten")
            return _render_phase_a_source_and_privacy_controls()
    container_ctx = (
        st.container(border=True) if hasattr(st, "container") else nullcontext()
    )
    with container_ctx:
        return _render_phase_a_source_and_privacy_controls()


def _render_extraction_result_section(ctx: WizardContext) -> None:
    if not _has_completed_intake_analysis():
        return
    container_ctx = (
        st.container(border=True) if hasattr(st, "container") else nullcontext()
    )
    with container_ctx:
        if hasattr(st, "markdown"):
            st.markdown("### Analyseergebnis")
        _render_phase_b_extraction_review(ctx)


def _render_esco_anchor_section(ctx: WizardContext) -> None:
    if not _has_completed_intake_analysis():
        return
    container_ctx = (
        st.container(border=True) if hasattr(st, "container") else nullcontext()
    )
    with container_ctx:
        if hasattr(st, "markdown"):
            st.markdown("### Berufsabgleich bestätigen")
        _render_phase_c_esco_anchor(ctx)

def _render_phase_b_extraction_review(ctx: WizardContext) -> None:
    _render_identified_information_block(ctx)


def _render_phase_c_esco_anchor(ctx: WizardContext) -> None:
    job_dict = st.session_state.get(SSKey.JOB_EXTRACT.value)
    plan_dict = st.session_state.get(SSKey.QUESTION_PLAN_BASE.value) or st.session_state.get(
        SSKey.QUESTION_PLAN.value
    )
    if not isinstance(job_dict, dict) or not isinstance(plan_dict, dict):
        return
    job = JobAdExtract.model_validate(job_dict)
    base_plan = QuestionPlan.model_validate(plan_dict)
    render_esco_occupation_confirmation(
        job,
        compact=True,
        show_start_context_panels=True,
        show_detail_panels=False,
    )
    _sync_deterministic_question_flow(job, base_plan)

    _, _, next_col = st.columns([1, 1, 1], gap="small")
    with next_col:
        if st.button("Weiter →", key="cs.start.next_step", width="stretch"):
            active_plan_raw = st.session_state.get(SSKey.QUESTION_PLAN.value, {})
            active_plan = (
                QuestionPlan.model_validate(active_plan_raw)
                if isinstance(active_plan_raw, dict)
                else base_plan
            )
            _promote_reviewed_job_extract(job, active_plan)
            ctx.next()
            st.rerun()


def render_jobad_intake(
    ctx: WizardContext, *, title: str = "Jobspezifikation einlesen"
) -> None:
    st.header(title)
    render_error_banner()

    if SOURCE_TEXT_INPUT_KEY not in st.session_state:
        st.session_state[SOURCE_TEXT_INPUT_KEY] = st.session_state.get(
            SSKey.SOURCE_TEXT.value, ""
        )

    do_extract = _render_source_input_section(ctx)

    if _has_completed_intake_analysis():
        render_intake_process_animation(state="done")

    if do_extract:
        clear_error()
        effective_source_text = str(
            st.session_state.get(SSKey.SOURCE_TEXT.value, "") or ""
        )
        raw = effective_source_text
        if not raw.strip():
            uploaded_text = str(st.session_state.get(SOURCE_UPLOAD_TEXT_KEY, "") or "")
            if uploaded_text.strip():
                _set_active_source("upload", uploaded_text)
                raw = uploaded_text

        if not raw.strip():
            upload = st.session_state.get("cs.source_upload_file")
            if upload is not None:
                extracted_upload_text = _extract_upload_to_state(
                    upload,
                    step="jobad.extract_and_plan.extract_text_from_uploaded_file",
                    update_text_widget=False,
                )
                if extracted_upload_text is not None:
                    raw = extracted_upload_text

        if not raw.strip():
            set_error("Bitte lade eine Datei hoch oder füge Text ein.")
            st.rerun()

        redact = bool(st.session_state.get(SSKey.SOURCE_REDACT_PII.value, True))
        submitted = redact_pii(raw) if redact else raw
        session_override = get_model_override()
        store = bool(st.session_state.get(SSKey.STORE_API_OUTPUT.value, False))
        settings = load_openai_settings()
        resolved_extract_model = resolve_model_for_task(
            task_kind=TASK_EXTRACT_JOB_AD,
            session_override=session_override,
            settings=settings,
        )
        resolved_plan_model = resolve_model_for_task(
            task_kind=TASK_GENERATE_QUESTION_PLAN,
            session_override=session_override,
            settings=settings,
        )

        try:
            with st.spinner("Analysiere Stellenanzeige…"):
                extract_started_at = perf_counter()
                job, usage1 = extract_job_ad(
                    submitted,
                    model=resolved_extract_model,
                    store=store,
                )
                extract_duration_ms = int((perf_counter() - extract_started_at) * 1000)

            with st.spinner("Erzeuge dynamischen Fragebogen…"):
                plan_started_at = perf_counter()
                plan, usage2 = generate_question_plan(
                    job,
                    model=resolved_plan_model,
                    store=store,
                )
                plan_duration_ms = int((perf_counter() - plan_started_at) * 1000)

            st.session_state[SSKey.JOB_EXTRACT.value] = _model_dump_json_compatible(
                job
            )
            write_job_extract_intake_facts(st.session_state, job)
            st.session_state[SSKey.QUESTION_PLAN_BASE.value] = (
                _model_dump_json_compatible(plan)
            )
            if isinstance(job, JobAdExtract) and isinstance(plan, QuestionPlan):
                _sync_deterministic_question_flow(job, plan)
            else:
                st.session_state[SSKey.QUESTION_PLAN.value] = (
                    _model_dump_json_compatible(plan)
                )

            extract_cached = usage_has_cache_hit(usage1)
            plan_cached = usage_has_cache_hit(usage2)
            record_enrichment_timed(
                st.session_state,
                stage="extract_job_ad",
                path="landing_phase_a",
                duration_ms=extract_duration_ms,
                cache_hit=extract_cached,
            )
            record_enrichment_timed(
                st.session_state,
                stage="generate_question_plan",
                path="landing_phase_a",
                duration_ms=plan_duration_ms,
                cache_hit=plan_cached,
                result_count=len(plan.steps),
            )
            st.session_state[SSKey.JOBAD_CACHE_HIT.value] = {
                "extract_job_ad": extract_cached,
                "generate_question_plan": plan_cached,
            }
            st.success("Analyse abgeschlossen: Informationen extrahiert und Fragebogen erzeugt.")
            if extract_cached or plan_cached:
                st.info("Mindestens ein Ergebnis wurde aus dem Cache geladen.")
        except OpenAICallError as e:
            render_openai_error(e)
        except Exception as exc:
            error_type = type(exc).__name__
            handle_unexpected_exception(
                step="jobad.extract_and_plan",
                exc=exc,
                error_type=error_type,
                error_code="JOBAD_ANALYZE_UNEXPECTED",
            )

        st.rerun()

    _render_extraction_result_section(ctx)
    _render_esco_anchor_section(ctx)
