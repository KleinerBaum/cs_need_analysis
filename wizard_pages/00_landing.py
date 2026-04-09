# wizard_pages/00_landing.py
from __future__ import annotations

import streamlit as st
from typing import cast

from constants import APP_TITLE, SSKey
from state import reset_vacancy
from wizard_pages.jobad_intake import render_jobad_intake
from wizard_pages.base import (
    LANDING_CTA_KEYS,
    LANDING_SECTION_IDS,
    LANDING_STYLE_TOKENS,
    WizardContext,
    WizardPage,
    nav_buttons,
    render_flow_steps,
    render_hero_section,
    render_importance_section,
    render_landing_css,
    render_output_section,
    render_security_note,
)

LANDING_COPY: dict[str, object] = {
    "hero_headline": "Recruiting beginnt nicht mit Sourcing. Es beginnt mit einem sauberen Vacancy Intake.",
    "hero_subhead": (""),
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
    "consent_hint": (
        "Kurz vor dem Start: Bitte Consent bestätigen, damit der Upload freigeschaltet ist."
    ),
    "consent_warning": (
        "Start ist gesperrt, bis die Einwilligung bestätigt wurde. "
        "Start is blocked until consent is confirmed."
    ),
    "consent_checkbox": (
        "Hinweise gelesen und erforderliche Endnutzer-Information/Einwilligung bestätigt. "
        "Read and confirmed required end-user notice/consent."
    ),
    "consent_expander_title": "Consent-Details anzeigen / Show consent details",
    "consent_details": (
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
    ),
}


def render(ctx: WizardContext) -> None:
    render_landing_css(LANDING_STYLE_TOKENS)
    st.title(APP_TITLE)

    consent_given = bool(st.session_state.get(LANDING_CTA_KEYS["consent"]))

    render_hero_section(
        ctx,
        section_id=LANDING_SECTION_IDS["hero"],
        headline=str(LANDING_COPY["hero_headline"]),
        subhead=str(LANDING_COPY["hero_subhead"]),
        primary_cta=str(LANDING_COPY["primary_cta"]),
        secondary_cta_hint=str(LANDING_COPY["secondary_cta_hint"]),
        before_start_title=str(LANDING_COPY["before_start_title"]),
        before_start_bullets=cast(
            tuple[str, ...], LANDING_COPY["before_start_bullets"]
        ),
        reassurance_line=str(LANDING_COPY["cta_reassurance"]),
        extraction_helper_copy=str(LANDING_COPY["cta_helper"]),
        next_step_line=str(LANDING_COPY["next_step_line"]),
        post_cta_microcopy=str(LANDING_COPY["cta_microcopy"]),
        value_cards=cast(tuple[tuple[str, str], ...], LANDING_COPY["value_cards"]),
        show_value_cards=False,
        consent_given=consent_given,
        start_button_key=LANDING_CTA_KEYS["start"],
        on_start=reset_vacancy,
        start_target="landing",
    )

    st.caption(str(LANDING_COPY["consent_hint"]))
    with st.expander(str(LANDING_COPY["consent_expander_title"]), expanded=False):
        st.markdown(str(LANDING_COPY["consent_details"]))

    st.checkbox(
        str(LANDING_COPY["consent_checkbox"]),
        key=LANDING_CTA_KEYS["consent"],
    )

    if not bool(st.session_state.get(SSKey.CONTENT_SHARING_CONSENT.value)):
        st.warning(str(LANDING_COPY["consent_warning"]))

    render_importance_section(
        section_id=LANDING_SECTION_IDS["importance"],
        title=str(LANDING_COPY["importance_title"]),
        intro=str(LANDING_COPY["importance_intro"]),
        points=cast(tuple[tuple[str, str], ...], LANDING_COPY["importance_points"]),
        closer=str(LANDING_COPY["importance_closer"]),
    )

    render_flow_steps(
        section_id=LANDING_SECTION_IDS["flow"],
        title=str(LANDING_COPY["flow_title"]),
        steps=cast(tuple[tuple[str, str], ...], LANDING_COPY["flow_steps"]),
    )

    render_output_section(
        section_id=LANDING_SECTION_IDS["output"],
        title=str(LANDING_COPY["output_title"]),
        bullets=cast(tuple[str, ...], LANDING_COPY["output_bullets"]),
    )

    render_security_note(
        section_id=LANDING_SECTION_IDS["security"],
        title=str(LANDING_COPY["security_title"]),
        body=str(LANDING_COPY["security_body"]),
    )

    st.divider()
    render_jobad_intake()

    st.caption("Debug im Sidebar aktivierbar / Debug can be enabled in the sidebar.")

    nav_buttons(ctx, disable_prev=True)


PAGE = WizardPage(
    key="landing",
    title_de="Start",
    icon="🏁",
    render=render,
    requires_jobspec=False,
)
