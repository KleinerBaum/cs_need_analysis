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

    col1, col2 = st.columns([1, 2])
    with col1:
        if st.button("Neuen Vorgang starten", type="primary"):
            reset_vacancy()
            ctx.goto("jobad")

    with col2:
        st.checkbox("Debug anzeigen", key=SSKey.DEBUG.value)

    nav_buttons(ctx, disable_prev=True)


PAGE = WizardPage(
    key="landing",
    title_de="Start",
    icon="🏁",
    render=render,
    requires_jobspec=False,
)
