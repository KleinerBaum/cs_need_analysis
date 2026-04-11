# wizard_pages/00_landing.py
from __future__ import annotations

import streamlit as st
from typing import cast

from constants import APP_TITLE
from wizard_pages.jobad_intake import render_jobad_intake
from wizard_pages.base import (
    LANDING_SECTION_IDS,
    LANDING_STYLE_TOKENS,
    WizardContext,
    WizardPage,
    render_importance_section,
    render_landing_css,
    render_output_section,
)

LANDING_COPY: dict[str, object] = {
    "hero_headline": "Präzise Anforderungen. Schnellere Besetzungen. Bessere Einstellungen.",
    "hero_subheadline": "",
    "hero_supporting_paragraph": (
        "Was am Anfang fehlt, fehlt später überall. Fehlende Informationen kosten passende "
        "Bewerbungen, erzeugen Rückfragen und erhöhen das Risiko teurer Fehlbesetzungen. "
        "Ein sauberer Intake schafft die Grundlage für bessere Anzeigen, schnellere Prozesse "
        "und belastbare Entscheidungen."
    ),
    "primary_cta": "Vacancy Intake starten",
    "secondary_cta_hint": "",
    "next_step_line": "",
    "before_start_title": "",
    "before_start_bullets": (),
    "cta_reassurance": "",
    "cta_helper": "",
    "cta_microcopy": "",
    "value_cards": (),
    "importance_title": "Warum dieser erste Schritt entscheidend ist",
    "importance_intro": "Die Qualität des Intakes bestimmt Präzision, Tempo und Entscheidungssicherheit im gesamten Recruitingprozess.",
    "importance_points": (
        (
            "Unscharfer Intake",
            "Verursacht kostspielige Folgeschleifen: Re-Briefings, Neupriorisierungen und wiederholte Suchläufe binden Zeit, Budget und Managementaufmerksamkeit.",
        ),
        (
            "Unklare Anforderungsarchitektur",
            "Verzerrt das Zielprofil, schwächt die Shortlist-Qualität und erhöht den Sourcing-Aufwand durch vermeidbare Streuverluste.",
        ),
        (
            "Unspezifische Must-haves",
            "Führen zu uneinheitlichen Interviewmaßstäben und unterminieren die Vergleichbarkeit von Kandidatinnen und Kandidaten in der Auswahlentscheidung.",
        ),
        (
            "Unvollständige Prozessparameter",
            "Erzeugen Rückfragen, Entscheidungslatenzen und operative Reibung zwischen Hiring Manager, Recruiting und Fachbereich.",
        ),
        (
            "Präziser Intake",
            "Spart Zeit, erhöht die Konsistenz entlang der Prozesskette und verbessert die Qualität jeder nachgelagerten Entscheidung.",
        ),
    ),
    "importance_closer": "Ein sauber definierter Start reduziert Risiko, beschleunigt Umsetzung und erhöht die Trefferquote im gesamten Hiring-Funnel.",
    "flow_title": "So funktioniert der Ablauf",
    "flow_steps": (
        (
            "1. Upload starten",
            "Laden Sie Stellenanzeige, Rollenprofil oder Jobspec hoch.",
        ),
        (
            "2. Lücken erkennen",
            "Die App extrahiert Kerndaten und markiert fehlende Informationen.",
        ),
        (
            "3. Antworten schärfen",
            "Sie beantworten gezielte Rückfragen zu Rolle, Team, Skills und Prozess.",
        ),
        (
            "4. Briefing erzeugen",
            "Sie erhalten ein konsistentes Recruiting-Briefing für HR und Fachbereich.",
        ),
    ),
    "output_title": "Was Sie am Ende erhalten",
    "output_bullets": (
        "Ein klar strukturiertes Anforderungsprofil",
        "Sauber getrennte Must-haves und Nice-to-haves",
        "Konkrete Informationen für Interviewdesign und Kandidatenansprache",
        "Eine deutlich bessere Basis für Recruiting-Qualität und Prozessgeschwindigkeit",
    ),
    "security_title": "Datenschutz und Kontrolle",
    "security_body": (
        "Vor der Verarbeitung können sensible personenbezogene Angaben optional reduziert werden. "
        "Ziel ist eine datensparsame, nachvollziehbare Nutzung im Vacancy Intake."
    ),
    "consent_warning": (
        "Start ist gesperrt, bis die Einwilligung bestätigt wurde. "
        "Start is blocked until consent is confirmed."
    ),
    "consent_details_inline": (
        "Wenn für eure Organisation Designated Content freigegeben ist, können diese Inhalte "
        "von OpenAI zu Entwicklungszwecken genutzt werden (inkl. Training, Evaluierung, Tests). "
        "Ihr müsst Endnutzende informieren und – falls erforderlich – Einwilligungen einholen."
    ),
}


def render(ctx: WizardContext) -> None:
    render_landing_css(LANDING_STYLE_TOKENS)
    st.caption(APP_TITLE)
    st.title(str(LANDING_COPY["hero_headline"]))
    hero_subheadline = str(LANDING_COPY["hero_subheadline"])
    if hero_subheadline:
        st.subheader(hero_subheadline)
    st.markdown(str(LANDING_COPY["hero_supporting_paragraph"]))

    output_col, importance_col = st.columns(2, gap="medium")
    with output_col:
        render_output_section(
            section_id=LANDING_SECTION_IDS["output"],
            title=str(LANDING_COPY["output_title"]),
            bullets=cast(tuple[str, ...], LANDING_COPY["output_bullets"]),
        )
    with importance_col:
        render_importance_section(
            section_id=LANDING_SECTION_IDS["importance"],
            title=str(LANDING_COPY["importance_title"]),
            intro=str(LANDING_COPY["importance_intro"]),
            points=cast(tuple[tuple[str, str], ...], LANDING_COPY["importance_points"]),
            closer=str(LANDING_COPY["importance_closer"]),
        )

    st.divider()
    render_jobad_intake(title=str(LANDING_COPY["primary_cta"]))


PAGE = WizardPage(
    key="landing",
    title_de="Start",
    icon="🏁",
    render=render,
    requires_jobspec=False,
)
