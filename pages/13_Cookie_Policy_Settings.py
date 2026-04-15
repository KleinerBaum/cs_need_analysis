# pages/05_Cookie_Policy_Settings.py
from __future__ import annotations

import streamlit as st

from site_ui import PROFILE, inject_site_styles, render_callout, render_cards, render_cta, render_hero, render_meta_line


st.set_page_config(page_title="Cookie Policy Settings", page_icon="🍪", layout="wide")
inject_site_styles()

render_hero(
    title="Cookie Policy & Einstellungen",
    lead=(
        "Wir verwenden Cookies und vergleichbare Technologien nur im jeweils erforderlichen Umfang. "
        "Auf dieser Seite informieren wir darüber, welche Kategorien es gibt und wie Sie Ihre Einstellungen verwalten können."
    ),
    eyebrow="Cookies & Präferenzen",
)
render_meta_line(f"Stand: {PROFILE.last_updated}")

render_callout(
    "Wichtiger Hinweis",
    (
        "Diese Seite sollte vor Veröffentlichung an die tatsächlich eingesetzten Technologien, "
        "Consent-Mechanismen und Anbieter angepasst werden."
    ),
    tone="warning",
)

st.markdown("## Ihre Wahlmöglichkeiten")
st.markdown(
    """
Sie können Ihre Einstellungen jederzeit anpassen. Nicht unbedingt erforderliche Technologien werden nur eingesetzt, wenn hierfür eine wirksame Einwilligung vorliegt.

Technisch notwendige Technologien können eingesetzt werden, soweit sie für die sichere und funktionsfähige Bereitstellung der Website oder App erforderlich sind.
"""
)

render_cards(
    [
        {
            "title": "Technisch notwendig",
            "body": (
                "Erforderlich für den sicheren Betrieb, grundlegende Funktionen, Navigation, "
                "Sitzungssteuerung oder sicherheitsrelevante Schutzmechanismen."
            ),
        },
        {
            "title": "Präferenzen",
            "body": (
                "Dienen dazu, gewählte Einstellungen, Komfortoptionen oder nutzerseitige Präferenzen zu speichern "
                "und die Nutzung konsistenter zu gestalten."
            ),
        },
        {
            "title": "Statistik",
            "body": (
                "Helfen zu verstehen, wie Inhalte und Funktionen genutzt werden, "
                "um Nutzerführung, Verständlichkeit und Produktqualität zu verbessern."
            ),
        },
        {
            "title": "Externe Inhalte / Dienste",
            "body": (
                "Werden relevant, wenn Inhalte oder Funktionen von Drittanbietern eingebunden werden, "
                "etwa Medien, Karten, Analyse- oder Kommunikationsdienste."
            ),
        },
    ],
    columns=2,
)

st.markdown("## Verwaltung Ihrer Einwilligung")
st.markdown(
    """
Ihre Auswahl kann jederzeit geändert oder widerrufen werden.  
Der Widerruf berührt nicht die Rechtmäßigkeit bereits erfolgter Verarbeitungen, wirkt aber für die Zukunft.

Soweit ein Consent-Management-System eingesetzt wird, können Einstellungen dort direkt angepasst werden.
"""
)

st.markdown("## Transparenz")
st.markdown(
    """
Welche Technologien konkret aktiv sind, hängt von der tatsächlichen Konfiguration dieser Website ab.  
Detaillierte Informationen zu Anbietern, Zwecken, Rechtsgrundlagen und Speicherfristen sollten in einem produktiven Setup technologiescharf dokumentiert sein.
"""
)

st.markdown("## Beispielhafte Angaben, die ergänzt werden sollten")
st.markdown(
    """
- Name des eingesetzten Consent-Tools,
- konkrete technisch notwendige Cookies / Speichermechanismen,
- Statistik- oder Analysetools,
- externe Medien- oder Kommunikationsdienste,
- jeweilige Speicherfristen,
- jeweilige Anbieter und Empfänger.
"""
)

render_cta(
    "Fragen zu Cookie-Einstellungen",
    f"Bei Rückfragen zu eingesetzten Technologien oder Präferenzen erreichen Sie uns unter **{PROFILE.privacy_email}**.",
)
