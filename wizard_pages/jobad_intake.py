from __future__ import annotations

import math
from typing import Any, Final

import streamlit as st

from constants import SSKey
from llm_client import (
    OpenAICallError,
    TASK_EXTRACT_JOB_AD,
    TASK_GENERATE_QUESTION_PLAN,
    extract_job_ad,
    generate_question_plan,
    resolve_model_for_task,
)
from parsing import extract_text_from_uploaded_file, redact_pii
from schemas import JobAdExtract, QuestionPlan
from settings_openai import load_openai_settings
from state import (
    clear_error,
    get_esco_occupation_selected,
    get_model_override,
    handle_unexpected_exception,
    set_error,
)
from ui_components import render_error_banner, render_openai_error
from usage_utils import usage_has_cache_hit
from wizard_pages.base import WizardContext, render_ui_mode_selector
from wizard_pages.esco_occupation_ui import render_esco_occupation_confirmation


SOURCE_TEXT_INPUT_KEY: Final[str] = "cs.source_text_input"
SOURCE_UPLOAD_SIG_KEY: Final[str] = "cs.source_upload_signature"
SOURCE_UPLOAD_TEXT_KEY: Final[str] = "cs.source_uploaded_text"
SOURCE_ACTIVE_KEY: Final[str] = "cs.source_active"
EXTRACT_FIELD_LABELS: Final[dict[str, str]] = {
    "job_title": "Stellenbezeichnung",
    "company_name": "Unternehmen",
    "brand_name": "Marke",
    "language_guess": "Sprache",
    "employment_type": "Beschäftigungsart",
    "contract_type": "Vertragsart",
    "seniority_level": "Karrierestufe",
    "start_date": "Eintrittsdatum",
    "application_deadline": "Bewerbungsfrist",
    "job_ref_number": "Referenznummer",
    "department_name": "Abteilung",
    "reports_to": "Berichtet an",
}


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


def _render_upload_preview(uploaded_text: str) -> None:
    lines = uploaded_text.splitlines()
    first_lines = "\n".join(lines[:3]).strip() or "—"
    st.text_area(
        "Preview (Textauszug)",
        value=first_lines,
        height=112,
        key="cs.source_upload_preview_first",
        disabled=True,
    )

    if len(lines) > 3:
        remaining = "\n".join(lines[3:]).strip()
        with st.expander("Weitere Zeilen anzeigen", expanded=False):
            st.text_area(
                "Restlicher Text",
                value=remaining,
                height=min(260, _preview_height_for_text(remaining)),
                key="cs.source_upload_preview_rest",
                disabled=True,
            )


def _render_identified_information_block(ctx: WizardContext) -> None:
    job_dict = st.session_state.get(SSKey.JOB_EXTRACT.value)
    plan_dict = st.session_state.get(SSKey.QUESTION_PLAN.value)
    if not isinstance(job_dict, dict) or not isinstance(plan_dict, dict):
        return

    job = JobAdExtract.model_validate(job_dict)
    plan = QuestionPlan.model_validate(plan_dict)

    st.markdown("### Identifizierte Informationen")

    values = job.model_dump()
    rows = [
        {
            "anzeige_feld": label,
            "machine_field": field,
            "inhalt": values.get(field),
        }
        for field, label in EXTRACT_FIELD_LABELS.items()
        if values.get(field) not in (None, "", [])
    ]
    st.caption(
        "Extrahierte Werte können hier direkt angepasst werden. Änderungen werden sofort gespeichert."
    )
    edited = st.data_editor(
        rows,
        width="stretch",
        hide_index=True,
        num_rows="fixed",
        key="cs.jobspec.ident_info.table",
        column_config={
            "anzeige_feld": st.column_config.TextColumn("Information", disabled=True),
            "machine_field": None,
            "inhalt": st.column_config.TextColumn("Aktueller Wert"),
        },
    )
    updated_values = dict(values)
    for row in edited:
        machine_field = str(row.get("machine_field", "")).strip()
        if not machine_field:
            continue
        value = row.get("inhalt")
        normalized = str(value).strip() if value is not None else ""
        updated_values[machine_field] = normalized or None
    st.session_state[SSKey.JOB_EXTRACT.value] = JobAdExtract.model_validate(
        updated_values
    ).model_dump()

    gap_col, assumptions_col = st.columns(2, gap="medium")
    with gap_col:
        st.markdown("#### Fehlende oder unklare Punkte")
        if job.gaps:
            for gap in job.gaps:
                st.write(f"- {gap}")
        else:
            st.write("- Keine expliziten Gaps erkannt.")
    with assumptions_col:
        st.markdown("#### Annahmen")
        if job.assumptions:
            for assumption in job.assumptions:
                st.write(f"- {assumption}")
        else:
            st.write("- Keine Annahmen dokumentiert.")

    plan_question_count = sum(len(step.questions) for step in plan.steps)
    selected_occupation = get_esco_occupation_selected() or {}
    selected_occupation_uri = str(
        st.session_state.get(SSKey.ESCO_SELECTED_OCCUPATION_URI.value, "")
    ).strip()
    if not selected_occupation_uri:
        selected_occupation_uri = str(selected_occupation.get("uri") or "").strip()
    has_confirmed_anchor = bool(selected_occupation_uri)
    selected_occupation_title = str(selected_occupation.get("title") or "").strip()

    nav_col_back, nav_col_plan, nav_col_next = st.columns([1, 3, 1], gap="small")
    with nav_col_back:
        if st.button("← Zurück", key="cs.jobspec.ident_info.back"):
            ctx.prev()
            st.rerun()
    with nav_col_plan:
        st.info(
            f'QuestionPlan geladen: "{plan_question_count}" Fragen in {len(plan.steps)} Steps.'
        )
    with nav_col_next:
        if has_confirmed_anchor:
            title = selected_occupation_title or "ESCO-Beruf"
            st.success(f"ESCO-Anker bestätigt: {title}")
        else:
            st.caption("Bitte in Phase C einen semantischen ESCO-Anker bestätigen.")

        if (
            st.button(
                "Weiter →",
                key="cs.jobspec.ident_info.next",
                disabled=not has_confirmed_anchor,
            )
            and has_confirmed_anchor
        ):
            ctx.next()
            st.rerun()


def _set_active_source(source: str, text: str) -> None:
    st.session_state[SSKey.SOURCE_TEXT.value] = text
    st.session_state[SOURCE_ACTIVE_KEY] = source


def _usage_has_cache_hit(usage: Any) -> bool:
    if isinstance(usage, dict):
        return bool(usage.get("cached"))
    return bool(getattr(usage, "cached", False))


def _on_manual_text_change() -> None:
    manual_text = str(st.session_state.get(SOURCE_TEXT_INPUT_KEY, ""))
    _set_active_source("text", manual_text)


def _extract_upload_to_state(upload: object, *, step: str) -> str | None:
    try:
        uploaded_text, source_meta = extract_text_from_uploaded_file(upload)
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
    _set_active_source("upload", uploaded_text)
    return uploaded_text


def _on_upload_change() -> None:
    upload = st.session_state.get("cs.source_upload_file")
    if upload is None:
        return

    _extract_upload_to_state(
        upload, step="_on_upload_change.extract_text_from_uploaded_file"
    )


def _render_phase_a_source_and_privacy_controls() -> bool:
    st.markdown("### Phase A · Quelle & Datenschutz")
    st.caption(
        "Quelle bereitstellen, Consent setzen und optional PII-Redaktion aktivieren, "
        "bevor die Analyse gestartet wird."
    )

    do_extract = False

    with st.container(border=True):
        st.markdown(
            """
            <style>
            .st-key-cs_ui_mode [data-baseweb="select"] > div,
            .st-key-cs-ui_mode [data-baseweb="select"] > div {
                background: rgba(255, 255, 255, 0.10) !important;
                color: #eaf2ff !important;
                border: 1px solid rgba(255, 255, 255, 0.25) !important;
            }
            </style>
            """,
            unsafe_allow_html=True,
        )
        upload_col, text_col = st.columns([1, 1.4], gap="large")
        with upload_col:
            st.file_uploader(
                "Jobspec hochladen (PDF oder DOCX)",
                type=["pdf", "docx", "txt"],
                accept_multiple_files=False,
                key="cs.source_upload_file",
                on_change=_on_upload_change,
            )
            st.markdown("**Wie weit möchten Sie ins Detail gehen?**")
            render_ui_mode_selector()
        with text_col:
            manual_text = str(st.session_state.get(SOURCE_TEXT_INPUT_KEY, ""))
            st.text_area(
                "Text einfügen",
                key=SOURCE_TEXT_INPUT_KEY,
                height=max(280, _manual_input_height_for_text(manual_text)),
                on_change=_on_manual_text_change,
                placeholder="Füge hier die Stellenanzeige oder Jobspec ein …",
            )

        st.checkbox(
            "Einwilligung zur inhaltlichen Verarbeitung der Jobspec liegt vor",
            key=SSKey.CONTENT_SHARING_CONSENT.value,
            help="Steuert den dokumentierten Consent-Status dieser Session.",
        )
        st.checkbox(
            "PII vor Analyse automatisch redigieren",
            key=SSKey.SOURCE_REDACT_PII.value,
            help="Bei Aktivierung wird der Quelltext vor dem LLM-Aufruf redigiert.",
        )

        uploaded_text = str(st.session_state.get(SOURCE_UPLOAD_TEXT_KEY, ""))
        upload_meta = st.session_state.get(SSKey.SOURCE_FILE_META.value, {})
        if uploaded_text:
            _render_upload_preview(uploaded_text)

        status_col, chars_col, action_col = st.columns([2, 1, 1], gap="small")
        with status_col:
            if uploaded_text:
                st.success(f"Datei geladen: {upload_meta.get('name', 'Unbekannt')}")
            else:
                st.caption("Noch keine Datei hochgeladen.")
        with chars_col:
            active_source_text = str(st.session_state.get(SSKey.SOURCE_TEXT.value, ""))
            char_count = len(active_source_text.strip()) if active_source_text else 0
            st.metric("Zeichen", f"{char_count:,}".replace(",", "."))
        with action_col:
            do_extract = st.button(
                "Jetzt analysieren",
                width="stretch",
                help="Analysieren und identifizierte Informationen direkt im Start anzeigen",
            )

    return do_extract


def _render_phase_b_extraction_review(ctx: WizardContext) -> None:
    st.markdown("### Phase B · Extraktion prüfen")
    _render_identified_information_block(ctx)


def _render_phase_c_esco_anchor() -> None:
    st.markdown("### Phase C · ESCO Semantic Anchor")
    job_dict = st.session_state.get(SSKey.JOB_EXTRACT.value)
    plan_dict = st.session_state.get(SSKey.QUESTION_PLAN.value)
    if not isinstance(job_dict, dict) or not isinstance(plan_dict, dict):
        st.info(
            "Phase C wird nach erfolgreicher Analyse (Extraktion + QuestionPlan) aktiviert."
        )
        return

    job = JobAdExtract.model_validate(job_dict)
    render_esco_occupation_confirmation(job)


def render_jobad_intake(
    ctx: WizardContext, *, title: str = "Jobspezifikation einlesen"
) -> None:
    st.header(title)
    render_error_banner()

    st.caption(
        "Lade ein Jobspec als PDF/DOCX hoch oder füge den Text direkt ein. Danach klickst du auf **Analysieren**."
    )

    if SOURCE_TEXT_INPUT_KEY not in st.session_state:
        st.session_state[SOURCE_TEXT_INPUT_KEY] = st.session_state.get(
            SSKey.SOURCE_TEXT.value, ""
        )

    do_extract = _render_phase_a_source_and_privacy_controls()

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
                )
                if extracted_upload_text is not None:
                    raw = extracted_upload_text

        if not raw.strip():
            set_error("Bitte zuerst ein Jobspec hochladen oder Text einfügen.")
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
            with st.spinner("Extrahiere Jobspec…"):
                job, usage1 = extract_job_ad(
                    submitted,
                    model=resolved_extract_model,
                    store=store,
                )

            with st.spinner("Erzeuge dynamischen Fragebogen…"):
                plan, usage2 = generate_question_plan(
                    job,
                    model=resolved_plan_model,
                    store=store,
                )

            st.session_state[SSKey.JOB_EXTRACT.value] = job.model_dump()
            st.session_state[SSKey.QUESTION_PLAN.value] = plan.model_dump()

            extract_cached = usage_has_cache_hit(usage1)
            plan_cached = usage_has_cache_hit(usage2)
            st.session_state[SSKey.JOBAD_CACHE_HIT.value] = {
                "extract_job_ad": extract_cached,
                "generate_question_plan": plan_cached,
            }
            st.success("Fertig: Jobspec extrahiert und Fragebogen erzeugt.")
            if extract_cached or plan_cached:
                st.info("Mindestens ein Ergebnis wurde aus dem Cache geladen.")

            with st.expander("API Usage (Debug)", expanded=False):
                st.write(
                    {
                        "resolved_models": {
                            "extract_job_ad": resolved_extract_model,
                            "generate_question_plan": resolved_plan_model,
                        },
                        "extract_usage": usage1,
                        "plan_usage": usage2,
                    }
                )
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

    _render_phase_b_extraction_review(ctx)
    _render_phase_c_esco_anchor()
