# wizard_pages/00_landing.py
from __future__ import annotations

import streamlit as st

from constants import APP_TITLE, SSKey
from state import reset_vacancy
from wizard_pages.base import WizardContext, WizardPage, nav_buttons


def render(ctx: WizardContext) -> None:
    st.title(APP_TITLE)
    st.subheader("Ziel")
    st.write(
        "Dieses Tool führt Line Manager strukturiert durch ein Vacancy Intake. "
        "Du lädst zuerst ein Jobspec/Job Ad hoch (PDF/DOCX) oder fügst Text ein. "
        "Danach erzeugt die App automatisch einen dynamischen Fragebogen, der sich am Jobspec orientiert."
    )

    st.subheader("So funktioniert der Ablauf")
    st.write(
        "1) Jobspec hochladen → 2) Extraktion → 3) Dynamische Fragen je Abschnitt → 4) Recruiting Brief & Job-Ad Draft."
    )

    st.subheader("Datenschutz / Sicherheit")
    st.write(
        "Du kannst optional eine PII-Redaktion (E-Mail/Telefon) aktivieren, "
        "bevor Text an das LLM gesendet wird. Außerdem kannst du API-Response-Storage deaktivieren."
    )

    st.subheader("Einwilligung / Consent")
    st.info(
        "Bitte bestätige vor dem Start die Hinweise zu OpenAI Content Sharing. "
        "Please confirm the OpenAI content sharing notice before starting."
    )
    with st.expander("Details anzeigen / Show details", expanded=False):
        st.markdown(
            """
            **DE:** Wenn für eure Organisation *Designated Content* freigegeben ist,
            können diese Inhalte von OpenAI zu Entwicklungszwecken genutzt werden
            (inkl. Training, Evaluierung, Tests). Ihr müsst Endnutzende informieren
            und – falls erforderlich – Einwilligungen einholen.

            **EN:** If your organization enables *Designated Content* sharing, that
            content may be used by OpenAI for development purposes (including model
            training, evaluation, and testing). You must inform end users and collect
            consent where required.

            **Nicht eingeben / Do not submit:** PHI (HIPAA), Daten von Kindern unter 13
            (oder unter lokalem Mindestalter), sowie Informationen, die nicht für
            Entwicklungszwecke genutzt werden dürfen.
            """
        )

    st.checkbox(
        "Ich habe die Hinweise gelesen und bestätige die erforderliche Information/Einwilligung der Endnutzenden. "
        "I have read this notice and confirm required end-user notice/consent.",
        key=SSKey.CONTENT_SHARING_CONSENT.value,
    )

    consent_given = bool(st.session_state.get(SSKey.CONTENT_SHARING_CONSENT.value))
    if not consent_given:
        st.warning(
            "Start ist gesperrt, bis die Einwilligung bestätigt wurde. "
            "Start is blocked until consent is confirmed."
        )

    col1, col2 = st.columns([1, 2])
    with col1:
        if st.button(
            "Neuen Vorgang starten / Start new intake",
            type="primary",
            disabled=not consent_given,
        ):
            reset_vacancy()
            ctx.goto("jobad")

    with col2:
        st.checkbox("Debug anzeigen / Show debug", key=SSKey.DEBUG.value)

    nav_buttons(ctx, disable_prev=True)


PAGE = WizardPage(
    key="landing",
    title_de="Start",
    icon="🏁",
    render=render,
    requires_jobspec=False,
)
