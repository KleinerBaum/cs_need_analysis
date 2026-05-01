# pages/02_Über_Cognitive_Staffing.py
from __future__ import annotations

import streamlit as st

from site_ui import PROFILE, inject_site_styles, render_cards, render_cta, render_hero, render_meta_line


st.set_page_config(page_title="Über Cognitive Staffing", page_icon="🏢", layout="wide")
inject_site_styles()

render_hero(
    title="Über Cognitive Staffing",
    lead=(
        "Der Firmengründer, Gerrit Fabisch, entwickelt digitale Werkzeuge, die Arbeitgebern helfen, "
        "Prozesse klarer zu definieren und durch den Einsatz von KI zu optimieren."
    ),
    eyebrow="Über uns",
)
render_meta_line("Präzision · Steuerbarkeit · Wiederverwendbarkeit")

render_cards(
    [
        {
            "title": "Mein Werdegang",
            "body": (
                "Ich bringe dafür ein Profil mit, das Business-Verständnis, Schnittstellenkompetenz und aktuelle KI-Praxis "
                "zusammenführt. Nach meinem BWL-Studium habe ich über viele Jahre in vertriebs- und recruitingnahen Rollen "
                "gearbeitet – mit Verantwortung für Kundenentwicklung, Verhandlungen, Projektstabilität, KPI-Steuerung und "
                "die Zusammenarbeit mit unterschiedlichen internen und externen Stakeholdern."
            ),
        },
        {
            "title": "Was ich biete",
            "body": (
                "In meiner aktuellen Tätigkeit als Gründer und KI-Recruitment-Berater entwickle ich einen KI-gestützten "
                "Prototypen zur Optimierung von Recruiting-Aktivitäten auf Basis der OpenAI-API, ESCO-API und eines eigenen "
                "Vector Stores. Ergänzt wird dies durch meine Data-Science-Weiterbildung sowie LLM-spezifische Kurse zu "
                "strukturierten Outputs und Reasoning."
            ),
        },
        {
            "title": "Was ich mir wünsche",
            "body": (
                "Ich sehe KI nicht als Selbstzweck, sondern als Hebel für bessere Entscheidungen, effizientere Prozesse und "
                "einen konkreten Mehrwert für Fachbereiche und Kunden. Diese Haltung möchte ich in ein Umfeld einbringen, "
                "das KI bereits strategisch und international verankert."
            ),
        },
    ],
    columns=3,
)

st.markdown("## Warum Cognitive Staffing")
st.markdown(
    """
Unsere Stärke liegt in der Verbindung aus Recruiting-Fachlogik, semantischer Strukturierung und moderner KI-Unterstützung.  
So entstehen Lösungen, die nicht nur innovativ wirken, sondern im Alltag spürbar entlasten.

Wir denken vom Prozess her:  
nicht von einem einzelnen Text, nicht von einem einzelnen Formular, sondern von einem besseren Startpunkt für den gesamten Recruiting-Verlauf.
"""
)

render_cta(
    "Unser Ziel",
    (
        "Nicht nur schnellere Besetzungen. "
        "Unser Ziel ist, Arbeitgeber und Arbeitnehmer langfristig passender, erfolgreicher und nachhaltiger zusammenzubringen."
    ),
)
