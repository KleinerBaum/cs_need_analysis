from __future__ import annotations

from pathlib import Path

import streamlit as st
from components.iceberg_need_analysis import (
    COMPONENT_HEIGHT,
    build_iceberg_need_analysis_html,
)
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


ROOT_DIR = Path(__file__).resolve().parents[1]
LANDING_LOGO_LIGHT_PATH = (
    ROOT_DIR / "images" / "animation_pulse_SingleColorHex1_7kigl22lw.gif"
)
LANDING_LOGO_DARK_PATH = ROOT_DIR / "images" / "animation_pulse_Default_7kigl22lw.gif"


def _theme_base() -> str:
    try:
        theme_base = st.get_option("theme.base")
    except Exception:
        theme_base = None
    return str(theme_base or "light").lower()


def _landing_logo_path() -> Path:
    if _theme_base() == "light":
        return LANDING_LOGO_LIGHT_PATH
    return LANDING_LOGO_DARK_PATH


def _render_landing_responsive_overrides() -> None:
    st.markdown(
        """
        <style>
            .landing-resource-links {
                display: flex;
                flex-wrap: wrap;
                gap: 0.55rem;
                margin-top: 0.85rem;
            }
            .landing-resource-links a {
                color: #FFFFFF !important;
                text-decoration: none !important;
                border: 1px solid var(--cs-success);
                background: var(--cs-success);
                border-radius: 999px;
                padding: 0.38rem 0.78rem;
                font-size: 0.86rem;
                font-weight: 650;
            }
            .landing-resource-links a:hover,
            .landing-resource-links a:focus-visible {
                border-color: color-mix(in srgb, var(--cs-success) 88%, #000000);
                background: color-mix(in srgb, var(--cs-success) 88%, #000000);
                outline: none;
            }
            .landing-start-logo {
                display: flex;
                align-items: center;
                margin-bottom: 0.55rem;
            }
            .landing-start-logo [data-testid="stImage"] {
                width: 150px;
                max-width: min(150px, 48vw);
            }
            .landing-start-logo img {
                width: 100%;
                height: auto;
            }
            .landing-process-diagram {
                border: 1px solid color-mix(in srgb, var(--cs-success) 42%, var(--cs-border));
                background: var(--cs-surface);
                border-radius: 8px;
                padding: 0.95rem;
                box-shadow: var(--cs-shadow-sm);
            }
            .landing-intake-card {
                padding: 1.05rem 1rem;
            }
            .landing-process-track {
                display: grid;
                grid-template-columns: repeat(4, minmax(0, 1fr));
                gap: 0.7rem;
                max-width: 100%;
            }
            .landing-process-step {
                position: relative;
                border: 1px solid var(--cs-border);
                background: var(--cs-surface-muted);
                border-radius: 8px;
                padding: 0.74rem 0.75rem;
                min-height: 112px;
            }
            .landing-process-step::after {
                content: "";
                position: absolute;
                top: 50%;
                right: -0.52rem;
                width: 0.34rem;
                height: 0.34rem;
                border-top: 2px solid var(--cs-success);
                border-right: 2px solid var(--cs-success);
                transform: translateY(-50%) rotate(45deg);
            }
            .landing-process-step:last-child::after {
                display: none;
            }
            .landing-process-step span {
                display: inline-flex;
                align-items: center;
                justify-content: center;
                width: 1.55rem;
                height: 1.55rem;
                border-radius: 999px;
                color: #FFFFFF;
                background: var(--cs-success);
                font-weight: 800;
                font-size: 0.84rem;
                margin-bottom: 0.5rem;
            }
            .landing-process-step strong {
                display: block;
                font-size: 0.92rem;
                line-height: 1.25;
                color: var(--cs-text);
            }
            .landing-process-diagram h4 {
                margin: 0 0 0.5rem 0;
                font-size: 1rem;
                color: var(--cs-text);
            }
            .landing-process-step p {
                margin: 0.25rem 0 0 0;
                color: var(--cs-text-muted);
                font-size: 0.82rem;
                line-height: 1.34;
            }
            .landing-process-result {
                margin-top: 0.8rem;
                border-left: 3px solid var(--cs-success);
                padding: 0.55rem 0.7rem;
                background: var(--cs-success-soft);
                border-radius: 8px;
                color: var(--cs-text);
                font-weight: 650;
            }
            .landing-process-resources {
                display: flex;
                flex-wrap: wrap;
                align-items: center;
                gap: 0.55rem;
                margin-top: 0.8rem;
            }
            .landing-process-resources span {
                color: var(--cs-text-muted);
                font-size: 0.86rem;
                font-weight: 700;
            }
            .landing-process-step,
            .landing-resource-links a {
                overflow-wrap: anywhere;
            }
            @media (max-width: 900px) {
                .landing-process-track {
                    grid-template-columns: minmax(0, 1fr);
                }
                .landing-process-step {
                    min-height: 0;
                }
                .landing-process-step::after {
                    display: none;
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
    st.markdown('<div class="landing-start-logo">', unsafe_allow_html=True)
    st.image(str(_landing_logo_path()), width=220)
    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown('<div class="landing-app-title-row">', unsafe_allow_html=True)
    st.markdown(
        f'<span class="landing-app-title">{APP_TITLE}</span>',
        unsafe_allow_html=True,
    )
    render_esco_language_toggle()
    st.markdown("</div>", unsafe_allow_html=True)

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
    st.markdown(
        """
        <div class="landing-process-diagram">
            <h4>Nach dem Klick auf "Analyse starten"</h4>
            <div class="landing-process-track">
                <div class="landing-process-step">
                    <span>1</span>
                    <strong>Text verstehen</strong>
                    <p>Upload oder Freitext wird gelesen und in ein sauberes Rollenprofil überführt.</p>
                </div>
                <div class="landing-process-step">
                    <span>2</span>
                    <strong>Beruf verankern</strong>
                    <p>Die App sucht den passenden ESCO-Beruf als gemeinsame Referenz.</p>
                </div>
                <div class="landing-process-step">
                    <span>3</span>
                    <strong>Fragen priorisieren</strong>
                    <p>Nur fehlende oder unsichere Punkte werden für den Wizard vorbereitet.</p>
                </div>
                <div class="landing-process-step">
                    <span>4</span>
                    <strong>Weiterverarbeiten</strong>
                    <p>Aufgaben, Skills, Benefits, Interview- und Summary-Artefakte bauen darauf auf.</p>
                </div>
            </div>
            <div class="landing-process-result">
                Ergebnis: weniger manuelle Sortierarbeit und eine bessere Grundlage für alle Recruiting-Aktivitäten.
            </div>
            <div class="landing-process-resources">
                <span>Mehr Kontext:</span>
                <div class="landing-resource-links">
                    <a href="https://employment-social-affairs.ec.europa.eu/policies-and-activities/skills-and-qualifications/skills-jobs/european-skillscompetences-qualifications-and-occupations-esco_en" target="_blank" rel="noopener noreferrer">Was ist ESCO?</a>
                    <a href="https://developers.openai.com/api/docs/guides/retrieval" target="_blank" rel="noopener noreferrer">Was bedeutet RAG?</a>
                    <a href="https://developers.openai.com/api/docs" target="_blank" rel="noopener noreferrer">OpenAI API Docs</a>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("</section>", unsafe_allow_html=True)


def _render_landing_explainer_sections() -> None:
    with st.expander("Warum Need Analysis?", expanded=False):
        st.caption(
            "Kurzer Kontext, warum die App nicht nur sichtbare Anforderungen, "
            "sondern auch Lücken und implizite Bedarfstreiber strukturiert."
        )
        st.iframe(
            build_iceberg_need_analysis_html(),
            height=COMPONENT_HEIGHT,
        )


def render(ctx: WizardContext) -> None:
    render_landing_css(LANDING_STYLE_TOKENS)
    _render_landing_responsive_overrides()
    _render_landing_hero()

    st.markdown('<section class="landing-section landing-card landing-intake-card">', unsafe_allow_html=True)
    render_jobad_intake(ctx, title=str(START_PAGE_COPY["primary_cta"]))
    st.markdown("</section>", unsafe_allow_html=True)
    _render_landing_explainer_sections()


PAGE = WizardPage(
    key="landing",
    title_de="Start",
    icon="🏁",
    render=render,
    requires_jobspec=False,
)
