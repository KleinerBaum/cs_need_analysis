# wizard_pages/00_landing.py
from __future__ import annotations

import streamlit as st

from constants import APP_TITLE, SSKey
from state import reset_vacancy
from wizard_pages.base import WizardContext, WizardPage, nav_buttons

# LANDING_HERO
HERO_HEADLINE = "Recruiting beginnt nicht mit Sourcing. Es beginnt mit einem sauberen Vacancy Intake."
HERO_SUBHEAD = (
    "Cognitive Staffing verwandelt Jobspecs und Stellenanzeigen in einen strukturierten, "
    "KI-gestützten Intake. So schaffen Sie von Anfang an Klarheit zu Rolle, Anforderungen, "
    "Rahmenbedingungen und Auswahlprozess – und reduzieren teure Folgefehler."
)
PRIMARY_CTA = "Jobspec hochladen und Intake starten"
SECONDARY_CTA_HINT = (
    "Geeignet für strukturierte Jobspecs und klassische Stellenanzeigen"
)

# LANDING_VALUE_CARDS
VALUE_CARDS: tuple[tuple[str, str], ...] = (
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
)

# LANDING_IMPORTANCE
SECTION_IMPORTANCE_TITLE = "Warum dieser erste Schritt entscheidend ist"
SECTION_IMPORTANCE_INTRO = (
    "Ein unpräziser Vacancy Intake wirkt sich auf den gesamten Recruiting-Prozess aus. "
    "Was hier unscharf bleibt, führt später zu teuren und demotivierenden Folgefehlern."
)
IMPORTANCE_POINTS: tuple[tuple[str, str], ...] = (
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
)
IMPORTANCE_CLOSER = (
    "Ein sauberer Intake senkt das Risiko von Fehlbesetzungen, spart Abstimmungszeit und "
    "erhöht die Qualität jeder nachfolgenden Recruiting-Entscheidung."
)

# LANDING_FLOW
FLOW_TITLE = "So funktioniert der Ablauf"
FLOW_STEPS: tuple[tuple[str, str], ...] = (
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
)

# LANDING_OUTPUT
OUTPUT_TITLE = "Was Sie am Ende erhalten"
OUTPUT_BULLETS: tuple[str, ...] = (
    "Ein klar strukturiertes Anforderungsprofil",
    "Sauber getrennte Must-haves und Nice-to-haves",
    "Konkrete Informationen für Interviewdesign und Kandidatenansprache",
    "Eine deutlich bessere Basis für Recruiting-Qualität und Prozessgeschwindigkeit",
)

# LANDING_SECURITY
SECURITY_TITLE = "Datenschutz und Kontrolle"
SECURITY_BODY = (
    "Vor der Verarbeitung können sensible personenbezogene Angaben optional reduziert werden. "
    "Ziel ist eine datensparsame, nachvollziehbare Nutzung im Vacancy Intake."
)

CONSENT_TITLE = "Einwilligung / Consent"
CONSENT_COPY = (
    "Bitte bestätigen Sie vor dem Start die Hinweise zu OpenAI Content Sharing. "
    "Please confirm the OpenAI content sharing notice before starting."
)


def _render_landing_css() -> None:
    st.markdown(
        """
        <style>
            .landing-section {
                margin: 2.1rem 0 2.4rem 0;
            }

            .landing-hero {
                background: linear-gradient(145deg, rgba(10, 27, 52, 0.9), rgba(8, 20, 40, 0.85));
                border: 1px solid rgba(146, 185, 255, 0.3);
                border-radius: 18px;
                padding: 1.5rem 1.4rem;
                box-shadow: 0 10px 30px rgba(0, 0, 0, 0.25);
            }

            .landing-hero h1 {
                margin: 0;
                font-size: clamp(1.6rem, 2.3vw, 2.45rem);
                line-height: 1.2;
            }

            .landing-subhead {
                margin-top: 0.9rem;
                color: rgba(245, 247, 251, 0.94);
                line-height: 1.6;
                font-size: 1.05rem;
            }

            .landing-card {
                background: rgba(11, 25, 49, 0.72);
                border: 1px solid rgba(255, 255, 255, 0.14);
                border-radius: 14px;
                padding: 1rem;
                height: 100%;
            }

            .landing-card h4 {
                margin: 0 0 0.45rem 0;
                font-size: 1rem;
            }

            .landing-card p {
                margin: 0;
                color: rgba(245, 247, 251, 0.92);
                line-height: 1.5;
            }

            .landing-emphasis {
                background: linear-gradient(135deg, rgba(21, 55, 106, 0.5), rgba(16, 37, 71, 0.35));
                border-left: 4px solid rgba(126, 173, 255, 0.9);
                border-radius: 14px;
                padding: 1rem 1rem 0.25rem 1rem;
                margin-bottom: 1rem;
            }

            .landing-flow-step {
                background: rgba(8, 18, 39, 0.62);
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 12px;
                padding: 0.95rem;
                min-height: 160px;
            }

            .landing-list {
                margin: 0.5rem 0 0 0;
                padding-left: 1.1rem;
            }

            .landing-list li {
                margin-bottom: 0.5rem;
                line-height: 1.45;
            }

            .landing-caption {
                color: rgba(218, 231, 255, 0.92);
                font-size: 0.9rem;
                margin-top: 0.35rem;
            }

            @media (max-width: 900px) {
                .landing-hero {
                    padding: 1.2rem;
                }
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render(ctx: WizardContext) -> None:
    _render_landing_css()

    st.title(APP_TITLE)

    # LANDING_HERO
    st.markdown(
        '<section class="landing-section landing-hero">', unsafe_allow_html=True
    )
    hero_left, hero_right = st.columns([1.6, 1], gap="large")
    with hero_left:
        st.markdown(f"<h1>{HERO_HEADLINE}</h1>", unsafe_allow_html=True)
        st.markdown(
            f'<p class="landing-subhead">{HERO_SUBHEAD}</p>',
            unsafe_allow_html=True,
        )

        consent_given = bool(st.session_state.get(SSKey.CONTENT_SHARING_CONSENT.value))
        if st.button(
            PRIMARY_CTA,
            type="primary",
            use_container_width=True,
            disabled=not consent_given,
        ):
            reset_vacancy()
            ctx.goto("jobad")

        st.markdown(
            f'<p class="landing-caption">{SECONDARY_CTA_HINT}</p>',
            unsafe_allow_html=True,
        )
    with hero_right:
        st.markdown("### Wertbeitrag auf einen Blick")
        card_cols_top = st.columns(2, gap="small")
        card_cols_bottom = st.columns(2, gap="small")
        for index, (title, body) in enumerate(VALUE_CARDS):
            target_col = (
                card_cols_top[index] if index < 2 else card_cols_bottom[index - 2]
            )
            with target_col:
                st.markdown(
                    f'<div class="landing-card"><h4>{title}</h4><p>{body}</p></div>',
                    unsafe_allow_html=True,
                )

    st.markdown("</section>", unsafe_allow_html=True)

    # LANDING_IMPORTANCE
    st.markdown('<section class="landing-section">', unsafe_allow_html=True)
    st.subheader(SECTION_IMPORTANCE_TITLE)
    st.markdown(
        f'<div class="landing-emphasis"><p>{SECTION_IMPORTANCE_INTRO}</p></div>',
        unsafe_allow_html=True,
    )
    importance_cols = st.columns(3, gap="medium")
    for col, (title, body) in zip(importance_cols, IMPORTANCE_POINTS):
        with col:
            st.markdown(
                f'<div class="landing-card"><h4>{title}</h4><p>{body}</p></div>',
                unsafe_allow_html=True,
            )
    st.write(IMPORTANCE_CLOSER)
    st.markdown("</section>", unsafe_allow_html=True)

    # LANDING_FLOW
    st.markdown('<section class="landing-section">', unsafe_allow_html=True)
    st.subheader(FLOW_TITLE)
    flow_cols = st.columns(4, gap="small")
    for col, (title, body) in zip(flow_cols, FLOW_STEPS):
        with col:
            st.markdown(
                f'<div class="landing-flow-step"><h4>{title}</h4><p>{body}</p></div>',
                unsafe_allow_html=True,
            )
    st.markdown("</section>", unsafe_allow_html=True)

    # LANDING_OUTPUT
    st.markdown('<section class="landing-section">', unsafe_allow_html=True)
    st.subheader(OUTPUT_TITLE)
    st.markdown('<div class="landing-card">', unsafe_allow_html=True)
    st.markdown(
        '<ul class="landing-list">'
        + "".join([f"<li>{bullet}</li>" for bullet in OUTPUT_BULLETS])
        + "</ul>",
        unsafe_allow_html=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("</section>", unsafe_allow_html=True)

    # LANDING_SECURITY
    st.markdown('<section class="landing-section">', unsafe_allow_html=True)
    st.subheader(SECURITY_TITLE)
    st.caption(SECURITY_BODY)
    st.markdown("</section>", unsafe_allow_html=True)

    st.subheader(CONSENT_TITLE)
    st.info(CONSENT_COPY)
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
        key=SSKey.CONTENT_SHARING_CONSENT.value,
    )

    if not bool(st.session_state.get(SSKey.CONTENT_SHARING_CONSENT.value)):
        st.warning(
            "Start ist gesperrt, bis die Einwilligung bestätigt wurde. "
            "Start is blocked until consent is confirmed."
        )

    st.checkbox("Debug anzeigen / Show debug", key=SSKey.DEBUG.value)

    nav_buttons(ctx, disable_prev=True)


PAGE = WizardPage(
    key="landing",
    title_de="Start",
    icon="🏁",
    render=render,
    requires_jobspec=False,
)
