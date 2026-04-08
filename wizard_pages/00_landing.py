# wizard_pages/00_landing.py
from __future__ import annotations

import streamlit as st
from typing import cast

from constants import APP_TITLE, SSKey
from state import reset_vacancy
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
    "hero_subhead": (
        "Cognitive Staffing verwandelt Jobspecs und Stellenanzeigen in einen strukturierten, "
        "KI-gestützten Intake. So schaffen Sie von Anfang an Klarheit zu Rolle, Anforderungen, "
        "Rahmenbedingungen und Auswahlprozess – und reduzieren teure Folgefehler."
    ),
    "primary_cta": "Jetzt Jobspec hochladen und Guided Intake starten",
    "secondary_cta_hint": "Geeignet für strukturierte Jobspecs und klassische Stellenanzeigen",
    "before_start_title": "Vor dem Start",
    "before_start_bullets": (
        "Unterstützt Jobspecs, Rollenprofile und klassische Stellenanzeigen",
        "Der Intake dauert nur wenige Minuten und passt sich dem Inhalt dynamisch an",
        "Sie erhalten ein strukturiertes Recruiting Briefing als Ergebnis",
    ),
    "cta_reassurance": (
        "Sie müssen nicht sofort alle Informationen vorliegen haben – "
        "fehlende Punkte werden im Verlauf gezielt ergänzt."
    ),
    "cta_helper": (
        "Das Tool extrahiert zuerst vorhandene Informationen und stellt "
        "danach nur relevante Rückfragen."
    ),
    "cta_microcopy": (
        "Besonders hilfreich bei unklaren Anforderungen, neuen Rollen oder "
        "mehreren Stakeholdern."
    ),
    "value_cards": (
        (
            "Mehr Klarheit von Beginn an",
            "Extrahiert vorhandene Informationen und deckt fehlende Punkte gezielt auf.",
        ),
        (
            "Bessere Interviews",
            "Schärft Must-haves, Aufgabenbild, Stakeholder und Erfolgskriterien.",
        ),
        (
            "Weniger Abstimmungsschleifen",
            "Reduziert Rückfragen zwischen Fachbereich, HR und Recruiting.",
        ),
        (
            "Sauberer Output",
            "Erstellt ein strukturiertes Recruiting Briefing als belastbare Grundlage.",
        ),
    ),
    "importance_title": "Warum dieser erste Schritt entscheidend ist",
    "importance_intro": (
        "Ein unpräziser Vacancy Intake wirkt sich auf den gesamten Recruiting-Prozess aus. "
        "Was hier unscharf bleibt, führt später zu teuren und demotivierenden Folgefehlern."
    ),
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
    "importance_closer": (
        "Ein sauberer Intake senkt das Risiko von Fehlbesetzungen, spart Abstimmungszeit und "
        "erhöht die Qualität jeder nachfolgenden Recruiting-Entscheidung."
    ),
    "flow_title": "So funktioniert der Ablauf",
    "flow_steps": (
        (
            "1. Jobspec hochladen",
            "Laden Sie eine Stellenanzeige, ein Rollenprofil oder eine Jobspec hoch.",
        ),
        (
            "2. Inhalte extrahieren",
            "Die App erkennt Rolle, Aufgaben, Skills, Benefits, Prozessdaten und Informationslücken.",
        ),
        (
            "3. Dynamische Rückfragen",
            "Je nach Jobprofil erhalten Sie gezielte Fragen zu Company, Team, Rolle, Skills und Hiring-Prozess.",
        ),
        (
            "4. Strukturiertes Briefing",
            "Am Ende steht ein konsistenter Recruiting Brief als Grundlage für HR, Fachbereich und Interviews.",
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
    "consent_title": "Einwilligung / Consent",
    "consent_copy": (
        "Bitte bestätigen Sie vor dem Start die Hinweise zu OpenAI Content Sharing. "
        "Please confirm the OpenAI content sharing notice before starting."
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
        post_cta_microcopy=str(LANDING_COPY["cta_microcopy"]),
        value_cards=cast(tuple[tuple[str, str], ...], LANDING_COPY["value_cards"]),
        consent_given=consent_given,
        start_button_key=LANDING_CTA_KEYS["start"],
        on_start=reset_vacancy,
        start_target="jobad",
    )

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

    st.subheader(str(LANDING_COPY["consent_title"]))
    st.info(str(LANDING_COPY["consent_copy"]))
    with st.expander("Details anzeigen / Show details", expanded=False):
        st.markdown(
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
        )

    st.checkbox(
        "Ich habe die Hinweise gelesen und bestätige die erforderliche Information/Einwilligung der Endnutzenden. "
        "I have read this notice and confirm required end-user notice/consent.",
        key=LANDING_CTA_KEYS["consent"],
    )

    if not bool(st.session_state.get(SSKey.CONTENT_SHARING_CONSENT.value)):
        st.warning(
            "Start ist gesperrt, bis die Einwilligung bestätigt wurde. "
            "Start is blocked until consent is confirmed."
        )

    st.checkbox("Debug anzeigen / Show debug", key=LANDING_CTA_KEYS["debug"])

    nav_buttons(ctx, disable_prev=True)


PAGE = WizardPage(
    key="landing",
    title_de="Start",
    icon="🏁",
    render=render,
    requires_jobspec=False,
)
