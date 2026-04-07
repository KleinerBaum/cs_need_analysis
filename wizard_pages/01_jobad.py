# wizard_pages/01_jobad.py
from __future__ import annotations

import streamlit as st
from typing import Final

from constants import SSKey
from llm_client import (
    OpenAICallError,
    TASK_EXTRACT_JOB_AD,
    TASK_GENERATE_QUESTION_PLAN,
    extract_job_ad,
    generate_question_plan,
    resolve_model_for_task,
)
from settings_openai import load_openai_settings
from parsing import extract_text_from_uploaded_file, redact_pii
from schemas import JobAdExtract, QuestionPlan
from state import clear_error, get_model_override, set_error
from ui_components import (
    render_error_banner,
    render_job_extract_overview,
    render_openai_error,
)
from wizard_pages.base import WizardContext, WizardPage, nav_buttons


SAMPLE_SENIOR_DS = """Job Title: Senior Data Scientist
Employment Type: Full-time
Contract Type: Permanent
Seniority Level: Senior
Company Name: Acme Analytics GmbH
City: Düsseldorf
Tech Stack: Python, TensorFlow, PyTorch, AWS, SQL, Docker
Responsibilities:
- Model development
- Deploy ML models to production
- Mentor junior data scientists
Benefits: Hybrid work, learning budget, team events
Recruitment Steps: phone screen, technical interview, final interview
"""

SAMPLE_PRODUKTENTWICKLER = """Produktentwickler*in (w/m/d) innovative Mobilitätskonzepte
- Leitung, Begleitung und Management von Digital-Projekten zur Einführung neuer Geschäftsmodelle, Produkte & Services
- Erstellung von Business Cases, Monitoring des Projektbudgets, Steuerung von Markttests
Anforderungen:
- Abgeschlossenes Studium (BWL / Business Development / Innovationsmanagement / Verkehrswesen / Mobilität / W-Ing.)
- mind. 4 Jahre Berufserfahrung
- Projektmanagement & -Leitung
- ÖPNV-Kenntnisse von Vorteil
Benefits: unbefristeter Vertrag, mobiles Arbeiten, 30 Tage Urlaub, Deutschlandticket Job
"""

SOURCE_TEXT_INPUT_KEY: Final[str] = "cs.source_text_input"
SOURCE_UPLOAD_SIG_KEY: Final[str] = "cs.source_upload_signature"
SOURCE_UPLOAD_TEXT_KEY: Final[str] = "cs.source_uploaded_text"
SOURCE_SAMPLE_SELECT_KEY: Final[str] = "cs.source_sample_select"
SOURCE_ACTIVE_KEY: Final[str] = "cs.source_active"


def _sample_text_for_selection(selection: str) -> str:
    if selection == "Senior Data Scientist (EN, strukturiert)":
        return SAMPLE_SENIOR_DS
    if selection == "Produktentwickler*in (DE, Bullet)":
        return SAMPLE_PRODUKTENTWICKLER
    return ""


def _set_active_source(source: str, text: str) -> None:
    st.session_state[SSKey.SOURCE_TEXT.value] = text
    st.session_state[SOURCE_ACTIVE_KEY] = source


def _on_manual_text_change() -> None:
    manual_text = str(st.session_state.get(SOURCE_TEXT_INPUT_KEY, ""))
    _set_active_source("text", manual_text)


def _on_sample_change() -> None:
    selection = str(st.session_state.get(SOURCE_SAMPLE_SELECT_KEY, "—"))
    sample_text = _sample_text_for_selection(selection)
    if sample_text:
        _set_active_source("sample", sample_text)


def _on_upload_change() -> None:
    upload = st.session_state.get("cs.source_upload_file")
    if upload is None:
        return

    try:
        uploaded_text, source_meta = extract_text_from_uploaded_file(upload)
    except Exception as exc:  # pragma: no cover - streamlit callback runtime
        set_error(
            f"Datei konnte nicht gelesen werden (DE) / Could not read file (EN): {type(exc).__name__}"
        )
        return

    st.session_state[SOURCE_UPLOAD_TEXT_KEY] = uploaded_text
    st.session_state[SSKey.SOURCE_FILE_META.value] = source_meta
    st.session_state[SOURCE_UPLOAD_SIG_KEY] = (
        source_meta.get("name", ""),
        source_meta.get("size", 0),
    )
    _set_active_source("upload", uploaded_text)


def render(ctx: WizardContext) -> None:
    st.header("Jobspec / Job Ad einlesen")

    render_error_banner()

    st.write(
        "Lade ein Jobspec als PDF/DOCX hoch oder füge den Text direkt ein. Danach klickst du auf **Analysieren**."
    )

    # Preferences / settings
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

    if SOURCE_TEXT_INPUT_KEY not in st.session_state:
        st.session_state[SOURCE_TEXT_INPUT_KEY] = st.session_state.get(
            SSKey.SOURCE_TEXT.value, ""
        )

    tab1, tab2, tab3 = st.tabs(["Upload", "Text einfügen", "Samples"])

    with tab1:
        st.file_uploader(
            "Jobspec hochladen (PDF oder DOCX)",
            type=["pdf", "docx", "txt"],
            accept_multiple_files=False,
            key="cs.source_upload_file",
            on_change=_on_upload_change,
        )
        uploaded_text = str(st.session_state.get(SOURCE_UPLOAD_TEXT_KEY, ""))
        upload_meta = st.session_state.get(SSKey.SOURCE_FILE_META.value, {})
        if uploaded_text:
            st.success(
                f"Datei geladen: {upload_meta.get('name', 'Unbekannt')} / File loaded"
            )
            st.text_area(
                "Preview (Textauszug)",
                value=uploaded_text[:4000],
                height=220,
                key="cs.source_upload_preview",
                disabled=True,
            )

    with tab2:
        st.text_area(
            "Jobspec Text",
            key=SOURCE_TEXT_INPUT_KEY,
            height=320,
            on_change=_on_manual_text_change,
        )

    with tab3:
        st.selectbox(
            "Sample auswählen",
            options=[
                "—",
                "Senior Data Scientist (EN, strukturiert)",
                "Produktentwickler*in (DE, Bullet)",
            ],
            key=SOURCE_SAMPLE_SELECT_KEY,
            on_change=_on_sample_change,
        )
        selected_sample = str(st.session_state.get(SOURCE_SAMPLE_SELECT_KEY, "—"))
        sample_text = _sample_text_for_selection(selected_sample)
        st.text_area(
            "Sample Text",
            value=sample_text,
            height=280,
            key="cs.source_sample_preview",
            disabled=True,
        )

    source_labels = {
        "upload": "Upload",
        "text": "Text",
        "sample": "Sample",
    }
    active_source = str(st.session_state.get(SOURCE_ACTIVE_KEY, "text"))
    st.caption(
        f"Aktive Textquelle: {source_labels.get(active_source, 'Unbekannt')} / Active source: {source_labels.get(active_source, 'Unknown')}"
    )

    col1, col2 = st.columns([1, 2])
    with col1:
        do_extract = st.button(
            "Analysieren & Fragebogen erzeugen",
            type="primary",
            use_container_width=True,
        )
    with col2:
        st.caption(
            "Hinweis: Die Analyse ruft die OpenAI API auf. Das kann je nach Länge des Jobspec etwas dauern."
        )

    if do_extract:
        clear_error()
        effective_source_text = str(
            st.session_state.get(SSKey.SOURCE_TEXT.value, "") or ""
        )
        raw = effective_source_text
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
            st.success("Fertig: Jobspec extrahiert und Fragebogen erzeugt.")

            # Optional: show usage
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
        except Exception:
            set_error("Unerwarteter Fehler (DE) / Unexpected error (EN).")

        st.rerun()

    # Show current extraction if available
    job_dict = st.session_state.get(SSKey.JOB_EXTRACT.value)
    plan_dict = st.session_state.get(SSKey.QUESTION_PLAN.value)

    if job_dict:
        job = JobAdExtract.model_validate(job_dict)
        render_job_extract_overview(job)

    if plan_dict:
        plan = QuestionPlan.model_validate(plan_dict)
        st.info(
            f"QuestionPlan geladen: {sum(len(s.questions) for s in plan.steps)} Fragen in {len(plan.steps)} Steps."
        )

    nav_buttons(
        ctx,
        disable_prev=False,
        disable_next=not bool(st.session_state.get(SSKey.JOB_EXTRACT.value)),
    )


PAGE = WizardPage(
    key="jobad",
    title_de="Jobspec / Jobad",
    icon="📄",
    render=render,
    requires_jobspec=False,
)
