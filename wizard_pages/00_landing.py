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
        "Willkommen bei einer hochmodernen, KI-gestützten Recruiting-Anwendung: dem "
        "„Cognitive Staffing – Vacancy Intake Wizard“. Ziel ist es, den Vacancy-Intake-"
        "Prozess in einen intelligenten, unternehmenstauglichen Workspace zu verwandeln. "
        "Mit Präzision und ruhiger Eleganz gestaltet, setzt dieses Konzept einen neuen "
        "Standard in der Recruiting-Technologie."
    ),
    "primary_cta": "Geben Sie uns ein paar Informationen zu Ihrer Vakanz",
    "secondary_cta_hint": "",
    "next_step_line": "",
    "before_start_title": "",
    "before_start_bullets": (),
    "cta_reassurance": "",
    "cta_helper": "",
    "cta_microcopy": "",
    "value_cards": (),
    "importance_title": "Warum dieser erste Schritt entscheidend ist",
    # Leitthese
    "importance_intro": "Die Intake-Qualität steuert, wie präzise, schnell und sicher Sie im weiteren Recruiting entscheiden.",
    # Risiken ohne sauberen Intake
    "importance_risk_points": (
        (
            "Schneller eskaliert Aufwand",
            "Mehr Re-Briefings, mehr Suchschleifen, mehr Verzögerung.",
        ),
        (
            "Klarer wird Vergleichbarkeit zum Risiko",
            "Uneinheitliche Must-haves machen Kandidatinnen und Kandidaten schwer vergleichbar.",
        ),
        (
            "Planbarer sinkt Interviewqualität",
            "Unklare Kriterien führen zu mehr Rückfragen und inkonsistenten Interviewentscheidungen.",
        ),
    ),
    # Hebel mit präzisem Intake
    "importance_leverage_points": (
        (
            "Schneller in die Umsetzung",
            "Weniger Rückfragen, konsistentere Interviews, belastbarere Shortlists.",
        ),
    ),
    # Outcome
    "importance_closer": "Ein sauber definierter Start senkt Risiko, verkürzt Time-to-Hire und erhöht die Trefferquote über den gesamten Funnel.",
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
        "Ein klar strukturiertes Anforderungsprofil auf einen Blick",
        "Messerscharf getrennte Must-haves und Nice-to-haves",
        "Konkrete Leitplanken für Interviewdesign und Kandidatenansprache",
        "Schnellere, fundiertere Entscheidungen im gesamten Hiring-Team",
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
    st.markdown(
        f"""
        <div class="landing-app-title-row">
            <span class="landing-app-title">{APP_TITLE}</span>
            <span class="landing-app-links">
                <a class="landing-app-link-pill" href="?info=esco">Über ESCO</a>
                <a class="landing-app-link-pill" href="?info=about">Was passiert da und ist das sicher?</a>
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )
    _, logo_col, _ = st.columns((1, 2, 1))
    with logo_col:
        st.image("images/color1_logo_transparent_background.png", width=128)
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
            risk_points=cast(
                tuple[tuple[str, str], ...],
                LANDING_COPY["importance_risk_points"],
            ),
            leverage_points=cast(
                tuple[tuple[str, str], ...],
                LANDING_COPY["importance_leverage_points"],
            ),
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
