from __future__ import annotations

import streamlit as st
from content.start_page import START_PAGE_COPY
from constants import APP_TITLE
from wizard_pages.jobad_intake import render_jobad_intake
from wizard_pages.base import (
    LANDING_SECTION_IDS,
    LANDING_STYLE_TOKENS,
    WizardContext,
    WizardPage,
    render_esco_language_toggle,
    render_landing_css,
)
from ui_components import render_intake_process_animation


def _render_landing_responsive_overrides() -> None:
    st.markdown(
        """
        <style>
            .landing-flow-grid {
                display: grid;
                grid-template-columns: repeat(3, minmax(0, 1fr));
                gap: 0.85rem;
                max-width: 100%;
            }
            .landing-flow-grid p,
            .landing-flow-grid strong {
                overflow-wrap: anywhere;
            }
            @media (max-width: 900px) {
                .landing-flow-grid {
                    grid-template-columns: minmax(0, 1fr);
                }
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _render_landing_hero() -> None:
    st.markdown(
        f'<section id="{LANDING_SECTION_IDS["hero"]}" class="landing-section landing-hero">',
        unsafe_allow_html=True,
    )
    st.markdown('<div class="landing-app-title-row">', unsafe_allow_html=True)
    st.markdown(
        f'<span class="landing-app-title">{APP_TITLE}</span>',
        unsafe_allow_html=True,
    )
    render_esco_language_toggle()
    st.markdown("</div>", unsafe_allow_html=True)

    _, logo_col, _ = st.columns((1, 2, 1))
    with logo_col:
        _, centered_logo_col, _ = st.columns((1, 1, 1))
        with centered_logo_col:
            st.image("images/white_logo_color1_background.png", width=320)

    st.title(str(START_PAGE_COPY["hero_headline"]))
    hero_subheadline = str(START_PAGE_COPY["hero_subheadline"])
    if hero_subheadline:
        st.subheader(hero_subheadline)
    hero_supporting = str(START_PAGE_COPY["hero_supporting_paragraph"])
    if hero_supporting:
        st.markdown(hero_supporting)
    st.markdown("</section>", unsafe_allow_html=True)


def _render_landing_flow_cards() -> None:
    st.markdown(
        f'<section id="{LANDING_SECTION_IDS["flow"]}" class="landing-section">',
        unsafe_allow_html=True,
    )
    st.subheader(str(START_PAGE_COPY["flow_title"]))
    st.caption("Die wichtigen Hintergrundschritte bleiben sichtbar, ohne den Start zu überladen.")
    render_intake_process_animation(state="idle")
    st.markdown("</section>", unsafe_allow_html=True)


def _render_landing_explainer_sections() -> None:
    st.markdown(
        f'<section id="{LANDING_SECTION_IDS["importance"]}" class="landing-section landing-card">',
        unsafe_allow_html=True,
    )
    st.subheader(str(START_PAGE_COPY["importance_title"]))
    st.markdown(
        "Wir reduzieren Mehrdeutigkeit am Anfang des Prozesses, damit die Analyse "
        "später präziser, nachvollziehbarer und für Recruiting besser nutzbar wird."
    )

    left_col, right_col = st.columns(2, gap="large")
    with left_col:
        st.markdown("#### Was ist ESCO?")
        st.markdown(
            "ESCO ist die europäische Klassifikation für Berufe und Skills. "
            "Die App nutzt sie, um unterschiedliche Jobtitel konsistent zu verankern."
        )
        st.markdown("#### Welche Artefakte entstehen?")
        st.markdown(
            "- Präzise Formulierungen für Aufgaben, Must-haves und Nice-to-haves.\n"
            "- Erwartungsmanagement durch belastbarere Zusammenfassungen und Prognosen.\n"
            "- Verwertbare Outputs für Recruiting, Hiring-Team und interne Abstimmung."
        )
    with right_col:
        st.markdown("#### Wie nutzt die App RAG?")
        st.markdown(
            "- Berufserkennung: ähnliche Jobtitel werden auf einen eindeutigen ESCO-Beruf zusammengeführt.\n"
            "- Skill-Vorschläge: bestätigte ESCO-Berufe liefern passende Essential- und Optional-Skills.\n"
            "- Kontextnutzung: relevante ESCO-Beschreibungen fließen als Faktenbasis in die Generierung ein.\n"
            "- Anforderungsnormalisierung: freie Stichworte können ergänzt oder als unternehmensspezifisch belassen werden."
        )
        st.caption(
            "Dieser Dienst stützt sich auf die ESCO-Klassifikation der Europäischen Kommission."
        )
    st.markdown("</section>", unsafe_allow_html=True)

    st.markdown(
        f'<section id="{LANDING_SECTION_IDS["value_cards"]}" class="landing-section">',
        unsafe_allow_html=True,
    )
    st.subheader("Klassische Bedarfsanalyse")
    st.markdown(
        "Die Herausforderung ist selten ein Mangel an Informationen, sondern ihre "
        "Struktur: Ohne sauberen Intake werden Anforderungen schnell unscharf, "
        "unvollständig oder missverständlich."
    )
    _, image_col, _ = st.columns((1, 3, 1))
    with image_col:
        st.image("images/iceberg v1.png", width="stretch")
    st.markdown("</section>", unsafe_allow_html=True)


def render(ctx: WizardContext) -> None:
    render_landing_css(LANDING_STYLE_TOKENS)
    _render_landing_responsive_overrides()
    _render_landing_hero()
    _render_landing_explainer_sections()
    _render_landing_flow_cards()

    st.markdown('<section class="landing-section landing-card landing-intake-card">', unsafe_allow_html=True)
    render_jobad_intake(ctx, title=str(START_PAGE_COPY["primary_cta"]))
    st.markdown("</section>", unsafe_allow_html=True)


PAGE = WizardPage(
    key="landing",
    title_de="Start",
    icon="🏁",
    render=render,
    requires_jobspec=False,
)
