# wizard_pages/00_landing.py
from __future__ import annotations

import streamlit as st
from typing import cast

from constants import APP_TITLE
from wizard_pages.jobad_intake import render_jobad_intake
from wizard_pages.base import (
    LANDING_CTA_KEYS,
    LANDING_SECTION_IDS,
    LANDING_STYLE_TOKENS,
    WizardContext,
    WizardPage,
    render_importance_section,
    render_landing_css,
    render_output_section,
)

LANDING_COPY: dict[str, object] = {
    "hero_headline": "Recruiting beginnt nicht mit Sourcing. Es beginnt mit einem sauberen Vacancy Intake.",
    "primary_cta": "",
    "secondary_cta_hint": "",
    "next_step_line": "",
    "before_start_title": "",
    "before_start_bullets": (),
    "cta_reassurance": "",
    "cta_helper": "",
    "cta_microcopy": "",
    "value_cards": (),
    "importance_title": "Warum dieser erste Schritt entscheidend ist",
    "importance_intro": "Unscharfer Intake = teure Folgeschleifen im Recruiting.",
    "importance_points": (
        (
            "Unklare Anforderungen",
            "Führen zu falschen Kandidatenprofilen, schwächeren Shortlists und unnötigem Sourcing-Aufwand.",
        ),
        (
            "Unscharfe Must-haves",
            "Erzeugen inkonsistente Interviews und erschweren belastbare Auswahlentscheidungen.",
        ),
        (
            "Fehlende Rahmenbedingungen",
            "Verursachen Verzögerungen, Rückfragen und vermeidbare Reibung im Prozess.",
        ),
    ),
    "importance_closer": "Guter Intake spart Zeit und verbessert jede Folgeentscheidung.",
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
    "consent_checkbox": (
        "Hinweise gelesen und erforderliche Endnutzer-Information/Einwilligung bestätigt. "
        "Read and confirmed required end-user notice/consent."
    ),
    "consent_details_inline": (
        "DE: Wenn für eure Organisation Designated Content freigegeben ist, können diese "
        "Inhalte von OpenAI zu Entwicklungszwecken genutzt werden (inkl. Training, Evaluierung, "
        "Tests). Ihr müsst Endnutzende informieren und – falls erforderlich – Einwilligungen "
        "einholen.\n\n"
        "EN: If your organization enables Designated Content sharing, that content may be used "
        "by OpenAI for development purposes (including model training, evaluation, and testing). "
        "You must inform end users and collect consent where required."
    ),
}


def render(ctx: WizardContext) -> None:
    render_landing_css(LANDING_STYLE_TOKENS)
    st.title(APP_TITLE)
    st.subheader(str(LANDING_COPY["hero_headline"]))

    consent_text_col, consent_checkbox_col = st.columns((4, 2), gap="medium")
    with consent_text_col:
        st.markdown(str(LANDING_COPY["consent_details_inline"]))
    with consent_checkbox_col:
        st.checkbox(
            str(LANDING_COPY["consent_checkbox"]),
            key=LANDING_CTA_KEYS["consent"],
        )

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
    render_jobad_intake()

    st.caption("Debug im Sidebar aktivierbar / Debug can be enabled in the sidebar.")


PAGE = WizardPage(
    key="landing",
    title_de="Start",
    icon="🏁",
    render=render,
    requires_jobspec=False,
)
