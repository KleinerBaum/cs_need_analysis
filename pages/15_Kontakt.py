# pages/06_Kontakt.py
from __future__ import annotations

import streamlit as st

from site_ui import PROFILE, inject_site_styles, render_cards, render_callout, render_cta, render_hero, render_meta_line


def _legal_policy_links() -> tuple[tuple[str, str], ...]:
    return (
        ("pages/03_Impressum.py", "Impressum"),
        ("pages/11_Datenschutzrichtlinie.py", "Datenschutzrichtlinie"),
        ("pages/12_Nutzungsbedingungen.py", "Nutzungsbedingungen"),
        ("pages/13_Cookie_Policy_Settings.py", "Cookie Policy Settings"),
        ("pages/14_Erklaerung_zur_Barrierefreiheit.py", "Erklärung zur Barrierefreiheit"),
    )


st.set_page_config(page_title="Kontakt", page_icon="✉️", layout="wide")
inject_site_styles()

render_hero(
    title="Kontakt",
    lead=(
        "Sie möchten Cognitive Staffing kennenlernen, eine Demo anfragen oder über einen konkreten Einsatzfall sprechen? "
        "Dann freuen wir uns auf Ihre Nachricht."
    ),
    eyebrow="Kontakt & Demo",
)
render_meta_line("Für Unternehmen, HR, Recruiting, IT und Produktverantwortliche")

render_cards(
    [
        {
            "title": "Unternehmen & Entscheider",
            "body": (
                "Sie möchten Ihren Vacancy Intake professionalisieren, Reibung im Recruiting reduzieren "
                "und bessere Entscheidungen früher im Prozess ermöglichen."
            ),
        },
        {
            "title": "HR & Recruiting",
            "body": (
                "Sie interessieren sich für klarere Übergaben, bessere Suchprofile, "
                "stärkere Interviewvorbereitung und wiederverwendbare Recruiting-Artefakte."
            ),
        },
        {
            "title": "IT & Produktverantwortliche",
            "body": (
                "Sie möchten mehr über Architektur, Sicherheit, Integrationsfähigkeit, "
                "On-Prem-Optionen oder lokale LLM-Szenarien erfahren."
            ),
        },
    ],
    columns=3,
)

col_left, col_right = st.columns([1.05, 1.15], gap="large")

with col_left:
    st.markdown("## So erreichen Sie uns")
    st.markdown(
        f"""
**E-Mail**  
{PROFILE.email}

**Telefon**  
{PROFILE.phone}

**Adresse**  
{PROFILE.legal_entity}  
{PROFILE.street}  
{PROFILE.postal_code} {PROFILE.city}  
{PROFILE.country}
"""
    )

    render_callout(
        "Hinweis zum Datenschutz",
        (
            "Bitte senden Sie uns über das Kontaktformular oder per E-Mail keine besonders sensiblen personenbezogenen Daten, "
            "sofern dies nicht erforderlich und abgestimmt ist."
        ),
    )

with col_right:
    st.markdown("## Demo oder Rückruf anfragen")
    with st.form("contact_form", clear_on_submit=False):
        name = st.text_input("Name")
        company = st.text_input("Unternehmen")
        email = st.text_input("E-Mail")
        topic = st.selectbox(
            "Anliegen",
            options=[
                "Demo anfragen",
                "Produktinformationen",
                "Technische Fragen",
                "Partnerschaft / Zusammenarbeit",
                "Sonstiges",
            ],
        )
        message = st.text_area(
            "Nachricht",
            placeholder="Beschreiben Sie kurz Ihren Anwendungsfall oder Ihr Anliegen.",
            height=160,
        )
        submitted = st.form_submit_button("Anfrage vorbereiten")

    if submitted:
        st.success("Vielen Dank. Bitte binden Sie nun den gewünschten Versandweg an, z. B. E-Mail, CRM oder Helpdesk.")
        st.code(
            f"Name: {name}\nUnternehmen: {company}\nE-Mail: {email}\nAnliegen: {topic}\n\nNachricht:\n{message}",
            language="text",
        )

render_cta(
    "Direkter Draht",
    f"Für schnelle Rückfragen erreichen Sie uns direkt unter **{PROFILE.email}**.",
)

st.markdown("## Rechtliches & Richtlinien")
for page_path, label in _legal_policy_links():
    st.page_link(page_path, label=label)
