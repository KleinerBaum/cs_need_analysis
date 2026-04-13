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
    render_esco_language_toggle,
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
    "importance_intro": "Der Recruiting-Prozess wird nicht erst in der Jobanzeige gut — sondern im allerersten Intake-Schritt.",
    # Risiken ohne sauberen Intake
    "importance_risk_points": (
        (
            "Unklare Anforderungen",
            "a) Rollen werden zu breit formuliert. Must-haves und Nice-to-haves verschwimmen. Das führt zu unpräzisem Sourcing und Diskussionen über die falschen Profile. b) Job Ads, Interviewleitfäden und Suchstrings werden mehrfach neu gebaut, weil die Grundlagen nicht früh genug strukturiert wurden.",
        ),
    ),
    # Hebel mit präzisem Intake
    "importance_leverage_points": (
        (
            "Schneller in die Umsetzung",
            "a) Der Wizard leitet aus der Rolle nur die Fragen ab, die für den konkreten Fall relevant sind — nicht für jede Stelle denselben Standardbogen. b) Aufgaben, Skills, Benefits und Gehalt werden gegeneinander plausibilisiert. Dadurch sinkt das Risiko eines unrealistischen Wunschprofils.",
        ),
    ),
    # Outcome
    "importance_closer": "Die App macht aus einem unscharfen Startpunkt einen strukturierten, überprüfbaren und weiterverwendbaren Recruiting-Datensatz.",
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
    title_col, language_col, links_col = st.columns((1.45, 0.7, 1.45), gap="small")
    with title_col:
        st.markdown(
            f'<span class="landing-app-title">{APP_TITLE}</span>',
            unsafe_allow_html=True,
        )
    with language_col:
        render_esco_language_toggle()
    with links_col:
        st.markdown(
            """
            <span class="landing-app-links">
                <a class="landing-app-link-pill" href="?info=esco">Über ESCO</a>
                <a class="landing-app-link-pill" href="?info=about">Was passiert da und ist das sicher?</a>
            </span>
            """,
            unsafe_allow_html=True,
        )
    _, logo_col, _ = st.columns((1, 2, 1))
    with logo_col:
        _, centered_logo_col, _ = st.columns((1, 1, 1))
        with centered_logo_col:
            st.image("images/white_logo_color1_background.png", width=256)
    st.title(str(LANDING_COPY["hero_headline"]))
    hero_subheadline = str(LANDING_COPY["hero_subheadline"])
    if hero_subheadline:
        st.subheader(hero_subheadline)
    st.markdown(str(LANDING_COPY["hero_supporting_paragraph"]))

    content_col, image_col = st.columns((1.35, 1), gap="large")
    with content_col:
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
        render_output_section(
            section_id=LANDING_SECTION_IDS["output"],
            title=str(LANDING_COPY["output_title"]),
            bullets=cast(tuple[str, ...], LANDING_COPY["output_bullets"]),
        )
    with image_col:
        st.image("images/iceberg v1.png", width="stretch")

    st.divider()
    render_jobad_intake(ctx, title=str(LANDING_COPY["primary_cta"]))


PAGE = WizardPage(
    key="landing",
    title_de="Start",
    icon="🏁",
    render=render,
    requires_jobspec=False,
)
