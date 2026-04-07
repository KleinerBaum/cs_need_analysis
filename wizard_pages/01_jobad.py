# wizard_pages/01_jobad.py
from __future__ import annotations

import streamlit as st

from constants import SSKey
from llm_client import extract_job_ad, generate_question_plan
from parsing import extract_text_from_uploaded_file, redact_pii
from schemas import JobAdExtract, QuestionPlan
from state import clear_error, set_error
from ui_components import render_error_banner, render_job_extract_overview
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

    tab1, tab2, tab3 = st.tabs(["Upload", "Text einfügen", "Samples"])

    source_text = ""
    source_meta = {}

    with tab1:
        upload = st.file_uploader(
            "Jobspec hochladen (PDF oder DOCX)",
            type=["pdf", "docx", "txt"],
            accept_multiple_files=False,
        )
        if upload is not None:
            try:
                text, meta = extract_text_from_uploaded_file(upload)
                source_text, source_meta = text, meta
                st.success(f"Datei geladen: {meta.get('name')}")
                st.text_area(
                    "Preview (Textauszug)", value=source_text[:4000], height=220
                )
            except Exception as e:
                set_error(f"Datei konnte nicht gelesen werden: {e}")

    with tab2:
        source_text = st.text_area(
            "Jobspec Text",
            value=st.session_state.get(SSKey.SOURCE_TEXT.value, ""),
            height=320,
        )

    with tab3:
        sample = st.selectbox(
            "Sample auswählen",
            options=[
                "—",
                "Senior Data Scientist (EN, strukturiert)",
                "Produktentwickler*in (DE, Bullet)",
            ],
        )
        if sample == "Senior Data Scientist (EN, strukturiert)":
            source_text = SAMPLE_SENIOR_DS
        elif sample == "Produktentwickler*in (DE, Bullet)":
            source_text = SAMPLE_PRODUKTENTWICKLER
        st.text_area("Sample Text", value=source_text, height=280)

    # Persist source text
    if source_text:
        st.session_state[SSKey.SOURCE_TEXT.value] = source_text
    if source_meta:
        st.session_state[SSKey.SOURCE_FILE_META.value] = source_meta

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
        raw = st.session_state.get(SSKey.SOURCE_TEXT.value, "") or ""
        if not raw.strip():
            set_error("Bitte zuerst ein Jobspec hochladen oder Text einfügen.")
            st.rerun()

        redact = bool(st.session_state.get(SSKey.SOURCE_REDACT_PII.value, True))
        submitted = redact_pii(raw) if redact else raw

        model = str(st.session_state.get(SSKey.MODEL.value, "")).strip()
        if not model:
            set_error(
                "Kein Modell konfiguriert. Bitte LLM-Model im Sidebar-Feld setzen."
            )
            st.rerun()
        store = bool(st.session_state.get(SSKey.STORE_API_OUTPUT.value, False))

        try:
            with st.spinner("Extrahiere Jobspec…"):
                job, usage1 = extract_job_ad(submitted, model=model, store=store)

            with st.spinner("Erzeuge dynamischen Fragebogen…"):
                plan, usage2 = generate_question_plan(job, model=model, store=store)

            st.session_state[SSKey.JOB_EXTRACT.value] = job.model_dump()
            st.session_state[SSKey.QUESTION_PLAN.value] = plan.model_dump()
            st.success("Fertig: Jobspec extrahiert und Fragebogen erzeugt.")

            # Optional: show usage
            with st.expander("API Usage (Debug)", expanded=False):
                st.write({"extract_usage": usage1, "plan_usage": usage2})

        except Exception as e:
            set_error(f"OpenAI-Analyse fehlgeschlagen: {e}")

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
