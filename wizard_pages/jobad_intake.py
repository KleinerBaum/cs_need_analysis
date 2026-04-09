from __future__ import annotations

import math
from typing import Final

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
from settings_openai import load_openai_settings
from state import (
    clear_error,
    get_model_override,
    handle_unexpected_exception,
    set_error,
)
from ui_components import render_error_banner, render_openai_error
from wizard_pages.base import set_current_step


SOURCE_TEXT_INPUT_KEY: Final[str] = "cs.source_text_input"
SOURCE_UPLOAD_SIG_KEY: Final[str] = "cs.source_upload_signature"
SOURCE_UPLOAD_TEXT_KEY: Final[str] = "cs.source_uploaded_text"
SOURCE_ACTIVE_KEY: Final[str] = "cs.source_active"


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


def _set_active_source(source: str, text: str) -> None:
    st.session_state[SSKey.SOURCE_TEXT.value] = text
    st.session_state[SOURCE_ACTIVE_KEY] = source


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
            user_message="Datei konnte nicht gelesen werden (DE) / Could not read file (EN).",
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


def render_jobad_intake(*, title: str = "Jobspec / Job Ad einlesen") -> None:
    st.header(title)
    render_error_banner()

    st.caption(
        "Lade ein Jobspec als PDF/DOCX hoch oder füge den Text direkt ein. Danach klickst du auf **Analysieren**."
    )

    with st.sidebar:
        st.subheader("LLM Settings")
        st.text_input(
            "Model",
            key=SSKey.MODEL.value,
            help="z.B. gpt-4o-mini oder ein anderes Modell aus deinem Account.",
        )
        st.checkbox(
            "API Output speichern (store=true)",
            key=SSKey.STORE_API_OUTPUT.value,
            help="Für Datenschutz i.d.R. deaktiviert lassen.",
        )
        st.checkbox(
            "PII redaktionieren (E-Mail/Telefon maskieren)",
            key=SSKey.SOURCE_REDACT_PII.value,
        )
        st.checkbox(
            "Debug-Fehlerdetails anzeigen (nur Metadaten)",
            key=SSKey.OPENAI_DEBUG_ERRORS.value,
            help="Zeigt nur Error-Code, Step und Typ – keine Inhalte oder PII.",
        )

    if SOURCE_TEXT_INPUT_KEY not in st.session_state:
        st.session_state[SOURCE_TEXT_INPUT_KEY] = st.session_state.get(
            SSKey.SOURCE_TEXT.value, ""
        )

    tab1, tab2 = st.tabs(["📤 Upload", "📝 Text einfügen"])
    do_extract = False

    with tab1:
        with st.container(border=True):
            upload_col, analyze_col = st.columns([2, 1], vertical_alignment="bottom")
            with upload_col:
                st.file_uploader(
                    "Jobspec hochladen (PDF oder DOCX)",
                    type=["pdf", "docx", "txt"],
                    accept_multiple_files=False,
                    key="cs.source_upload_file",
                    on_change=_on_upload_change,
                )
            with analyze_col:
                st.caption("Aktive Quelle: **Upload**")
                do_extract = st.button(
                    "Investigiere!",
                    width="stretch",
                    help="Analysieren und direkt zur Jobspec-Übersicht wechseln",
                )
            uploaded_text = str(st.session_state.get(SOURCE_UPLOAD_TEXT_KEY, ""))
            upload_meta = st.session_state.get(SSKey.SOURCE_FILE_META.value, {})
            if uploaded_text:
                col_meta_left, col_meta_right = st.columns([2, 1])
                with col_meta_left:
                    st.success(
                        f"Datei geladen: {upload_meta.get('name', 'Unbekannt')} / File loaded"
                    )
                with col_meta_right:
                    st.metric("Zeichen", f"{len(uploaded_text):,}".replace(",", "."))
                preview_text = uploaded_text[:4000]
                st.text_area(
                    "Preview (Textauszug)",
                    value=preview_text,
                    height=_preview_height_for_text(preview_text),
                    key="cs.source_upload_preview",
                    disabled=True,
                )

    with tab2:
        with st.container(border=True):
            st.text_area(
                "Jobspec Text",
                key=SOURCE_TEXT_INPUT_KEY,
                height=320,
                on_change=_on_manual_text_change,
                placeholder="Füge hier die Stellenanzeige oder Jobspec ein …",
            )

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
            extract_cached = bool((usage1 or {}).get("cached"))
            plan_cached = bool((usage2 or {}).get("cached"))
            st.session_state[SSKey.JOBAD_CACHE_HIT.value] = {
                "extract_job_ad": extract_cached,
                "generate_question_plan": plan_cached,
            }
            st.success("Fertig: Jobspec extrahiert und Fragebogen erzeugt.")
            if extract_cached or plan_cached:
                st.info(
                    "Mindestens ein Ergebnis wurde aus Cache geladen (DE) / At least one result was loaded from cache (EN)."
                )
            set_current_step("jobspec_review")

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
