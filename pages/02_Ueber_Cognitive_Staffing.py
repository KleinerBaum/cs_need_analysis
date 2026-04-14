# pages/02_Ueber_Cognitive_Staffing.py
from __future__ import annotations

import streamlit as st

from pages._site_ui import (
    inject_site_styles,
    render_cards,
    render_cta,
    render_hero,
    render_meta_line,
)


st.set_page_config(page_title="Über Cognitive Staffing", page_icon="🏢", layout="wide")
inject_site_styles()

render_hero(
    title="Über Cognitive Staffing",
    lead=(
        "Cognitive Staffing steht für strukturiertes, intelligentes und verantwortungsbewusstes Recruiting. "
        "Wir entwickeln digitale Werkzeuge, die Arbeitgebern helfen, Stellen klarer zu definieren, "
        "Prozesse schlanker zu gestalten und bessere Entscheidungen früher im Recruiting-Verlauf zu treffen."
    ),
    eyebrow="Über uns",
)
render_meta_line("Präzision · Steuerbarkeit · Wiederverwendbarkeit")

render_cards(
    [
        {
            "title": "Unser Ansatz",
            "body": (
                "Viele Recruiting-Probleme beginnen nicht im Sourcing, sondern viel früher: "
                "bei einer unklaren oder unvollständigen Bedarfserfassung. Genau dort setzen wir an."
            ),
        },
        {
            "title": "Unser Verständnis von KI",
            "body": (
                "Wir nutzen KI nicht als Show-Effekt, sondern als Werkzeug innerhalb eines kontrollierten Systems. "
                "Struktur, Nachvollziehbarkeit und fachliche Nutzbarkeit stehen im Vordergrund."
            ),
        },
        {
            "title": "Unser Produktziel",
            "body": (
                "Aus verstreuten Informationen soll ein klarer, belastbarer und weiterverwendbarer Recruiting-Arbeitsstand entstehen."
            ),
        },
    ],
    columns=3,
)

st.markdown("## Woran wir glauben")
st.markdown(
    """
Recruiting wird besser, wenn Anforderungen früh klarer werden.  
Je strukturierter der erste Schritt, desto konsistenter werden Jobanzeige, Suche, Gesprächsführung und Auswahl.

Deshalb bauen wir keine isolierten Einzelgeneratoren, sondern Werkzeuge, die Zusammenhänge sichtbar machen:
zwischen Rolle und Kontext, zwischen Anforderungen und Markt, zwischen Recruiting und interner Abstimmung.
"""
)

st.markdown("## Wofür wir stehen")
render_cards(
    [
        {
            "title": "Präzision statt Bauchgefühl",
            "body": "Wir machen Anforderungen explizit, vergleichbar und belastbar.",
        },
        {
            "title": "Struktur statt Medienbruch",
            "body": "Wir reduzieren Übersetzungsarbeit zwischen Fachbereich, Recruiting und Management.",
        },
        {
            "title": "Technologie mit Augenmaß",
            "body": "Wir setzen moderne KI dort ein, wo sie tatsächlich Qualität und Nutzbarkeit erhöht.",
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
