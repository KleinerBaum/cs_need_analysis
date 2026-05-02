from __future__ import annotations

import math
from contextlib import nullcontext
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
    has_confirmed_esco_anchor,
    get_model_override,
    handle_unexpected_exception,
    set_error,
)
from ui_components import (
    render_error_banner,
    render_job_extract_overview,
    render_openai_error,
)
from usage_utils import usage_has_cache_hit
from wizard_pages.base import (
    WizardContext,
    render_ui_mode_selector,
)
from wizard_pages.esco_occupation_ui import render_esco_occupation_confirmation


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


def _manual_input_height_for_text(text: str) -> int:
    """Return a compact default height for short text and grow moderately for longer text."""
    min_height_px = 200
    max_height_px = 380
    return max(min_height_px, min(_preview_height_for_text(text), max_height_px))


def _render_identified_information_block(ctx: WizardContext) -> None:
    job_dict = st.session_state.get(SSKey.JOB_EXTRACT.value)
    plan_dict = st.session_state.get(SSKey.QUESTION_PLAN.value)
    if not isinstance(job_dict, dict) or not isinstance(plan_dict, dict):
        return

    job = JobAdExtract.model_validate(job_dict)
    plan = QuestionPlan.model_validate(plan_dict)

    plan_question_count = sum(len(step.questions) for step in plan.steps)
    selected_occupation = get_esco_occupation_selected() or {}
    has_confirmed_anchor = has_confirmed_esco_anchor()
    selected_occupation_title = str(selected_occupation.get("title") or "").strip()

    st.success("Analyse abgeschlossen")
    st.caption(
        "Extrahierte Werte und dynamische Rückfragen wurden vorbereitet. "
        "Prüfen Sie die Angaben und bestätigen Sie anschließend den ESCO-Anker."
    )

    with st.expander("Technische Details zur Analyse", expanded=False):
        st.caption(f"Generierte Rückfragen gesamt: {plan_question_count}")
        st.caption(f"Generierte Step-Blöcke: {len(plan.steps)}")
        cache_info = st.session_state.get(SSKey.JOBAD_CACHE_HIT.value)
        if isinstance(cache_info, dict) and cache_info:
            extract_cached = bool(cache_info.get("extract_job_ad"))
            plan_cached = bool(cache_info.get("generate_question_plan"))
            st.caption(
                "Cache-Status: "
                f"Extraktion={'Ja' if extract_cached else 'Nein'}, "
                f"Frageplan={'Ja' if plan_cached else 'Nein'}"
            )
        else:
            st.caption("Cache-Status: keine Daten verfügbar")
    render_job_extract_overview(
        job, plan=plan, show_question_limits=False, show_heading=False
    )

    nav_col_back, nav_col_anchor = st.columns([1, 2], gap="small")
    with nav_col_back:
        if st.button("← Zurück", key="cs.jobspec.ident_info.back"):
            ctx.prev()
            st.rerun()
    with nav_col_anchor:
        if has_confirmed_anchor:
            title = selected_occupation_title or "ESCO-Beruf"
            st.success(f"ESCO-Anker bestätigt: {title}")
        else:
            st.caption(
                "Optional: In Phase C können Sie einen semantischen ESCO-Anker bestätigen."
            )


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


def _has_completed_intake_analysis() -> bool:
    job_dict = st.session_state.get(SSKey.JOB_EXTRACT.value)
    plan_dict = st.session_state.get(SSKey.QUESTION_PLAN.value)
    return isinstance(job_dict, dict) and isinstance(plan_dict, dict)


def _render_phase_a_source_and_privacy_controls() -> bool:
    do_extract = False

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
    st.markdown("### Jobspec erfassen")

    upload_col, text_col = st.columns([1, 1.4], gap="large")
    with upload_col:
        st.file_uploader(
            "Jobspec hochladen (PDF oder DOCX)",
            type=["pdf", "docx", "txt"],
            accept_multiple_files=False,
            key="cs.source_upload_file",
            on_change=_on_upload_change,
        )
        st.caption(
            "Verarbeitet werden PDF, DOCX und TXT mit auslesbarem Text. "
            "Scan-PDFs ohne OCR können leer bleiben."
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
        render_ui_mode_selector(show_label=False)
    with text_col:
        manual_text = str(st.session_state.get(SOURCE_TEXT_INPUT_KEY, ""))
        st.text_area(
            "Text einfügen",
            key=SOURCE_TEXT_INPUT_KEY,
            height=min(420, max(280, _manual_input_height_for_text(manual_text))),
            on_change=_on_manual_text_change,
            placeholder="Füge hier die Stellenanzeige oder Jobspec ein …",
        )

    uploaded_text = str(st.session_state.get(SOURCE_UPLOAD_TEXT_KEY, ""))
    upload_meta = st.session_state.get(SSKey.SOURCE_FILE_META.value, {})
    upload = st.session_state.get("cs.source_upload_file")
    last_error = str(st.session_state.get(SSKey.LAST_ERROR.value, "") or "")

    st.markdown("---")
    status_col, chars_col, action_col = st.columns([2, 1, 1], gap="small")
    with status_col:
        file_name = str(upload_meta.get("name") or getattr(upload, "name", "") or "")
        if upload is not None:
            st.info(f"Datei ausgewählt: {file_name or 'Unbekannt'}")

        if uploaded_text:
            st.success("Text extrahiert.")
        elif upload is not None and last_error:
            st.error(f"Extraktion fehlgeschlagen: {last_error}")
        else:
            st.caption("Optional: Datei hochladen oder Text direkt einfügen.")
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
        company_name = str(job_dict.get("employer_name") or "").strip()

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
        expander_ctx = (
            st.expander("Jobspec-Quelle bearbeiten", expanded=False)
            if hasattr(st, "expander")
            else nullcontext()
        )
        with expander_ctx:
            container_ctx = (
                st.container(border=True) if hasattr(st, "container") else nullcontext()
            )
            with container_ctx:
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
            st.markdown("### ESCO-Anker bestätigen")
        _render_phase_c_esco_anchor(ctx)

def _render_phase_b_extraction_review(ctx: WizardContext) -> None:
    _render_identified_information_block(ctx)


def _render_phase_c_esco_anchor(ctx: WizardContext) -> None:
    job_dict = st.session_state.get(SSKey.JOB_EXTRACT.value)
    plan_dict = st.session_state.get(SSKey.QUESTION_PLAN.value)
    if not isinstance(job_dict, dict) or not isinstance(plan_dict, dict):
        return
    job = JobAdExtract.model_validate(job_dict)
    render_esco_occupation_confirmation(
        job,
        show_start_context_panels=True,
    )

    _, _, next_col = st.columns([1, 1, 1], gap="small")
    with next_col:
        if st.button("Weiter →", key="cs.start.next_step", width="stretch"):
            ctx.next()
            st.rerun()


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

    do_extract = _render_source_input_section(ctx)

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
            set_error("Bitte zuerst ein Jobspec hochladen oder Text einfügen.")
            st.rerun()

        redact = bool(st.session_state.get(SSKey.SOURCE_REDACT_PII.value, False))        
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
