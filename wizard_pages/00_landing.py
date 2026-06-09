from __future__ import annotations

import base64
from pathlib import Path

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
                border: 1px solid #0F766E;
                background: #0F766E;
                border-radius: 999px;
                padding: 0.38rem 0.78rem;
                font-size: 0.86rem;
                font-weight: 650;
            }
            .landing-resource-links a:hover,
            .landing-resource-links a:focus-visible {
                border-color: #0B5F58;
                background: #0B5F58;
                outline: none;
            }
            .landing-signal-row {
                display: grid;
                grid-template-columns: repeat(3, minmax(0, 1fr));
                gap: 0.75rem;
                margin-top: 1.1rem;
            }
            .landing-signal {
                border: 1px solid var(--cs-border);
                background: var(--cs-surface);
                border-radius: 8px;
                padding: 0.85rem 0.9rem;
                box-shadow: 0 8px 22px rgba(22, 50, 79, 0.06);
            }
            .landing-signal strong {
                display: block;
                color: var(--cs-text);
                font-size: 0.94rem;
            }
            .landing-signal span {
                display: block;
                color: var(--cs-text-muted);
                font-size: 0.82rem;
                line-height: 1.35;
                margin-top: 0.18rem;
            }
            .landing-iceberg-card {
                border: 1px solid var(--cs-border);
                background: var(--cs-surface);
                border-radius: 8px;
                box-shadow: 0 8px 22px rgba(22, 50, 79, 0.06);
                overflow: hidden;
                padding: clamp(0.55rem, 1.5vw, 1rem);
            }
            .landing-iceberg-card img {
                display: block;
                width: 100%;
                height: auto;
                border-radius: 6px;
            }
            [data-theme="dark"] .landing-iceberg-card {
                border-color: #1E3A63;
                background: #152640;
                box-shadow: 0 8px 22px rgba(0, 0, 0, 0.28);
            }
            .landing-process-diagram {
                border: 1px solid #0F766E;
                background: var(--cs-success-soft);
                border-radius: 8px;
                padding: 0.95rem;
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
                background: var(--cs-surface);
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
                border-top: 2px solid #0F766E;
                border-right: 2px solid #0F766E;
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
                background: #0F766E;
                font-weight: 800;
                font-size: 0.84rem;
                margin-bottom: 0.5rem;
            }
            .landing-process-step strong {
                display: block;
                font-size: 0.92rem;
                line-height: 1.25;
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
                border-left: 3px solid #0F766E;
                padding: 0.55rem 0.7rem;
                background: var(--cs-surface);
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
            .landing-iceberg-card,
            .landing-process-step,
            .landing-signal,
            .landing-resource-links a {
                overflow-wrap: anywhere;
            }
            @media (max-width: 900px) {
                .landing-signal-row,
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


def _image_uri(filename: str) -> str:
    image_path = Path(__file__).resolve().parents[1] / "images" / filename
    image_bytes = image_path.read_bytes()
    encoded_image = base64.b64encode(image_bytes).decode("utf-8")
    return f"data:image/png;base64,{encoded_image}"


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

    st.title(str(START_PAGE_COPY["hero_headline"]))
    hero_subheadline = str(START_PAGE_COPY["hero_subheadline"])
    if hero_subheadline:
        st.subheader(hero_subheadline)
    hero_supporting = str(START_PAGE_COPY["hero_supporting_paragraph"])
    if hero_supporting:
        st.markdown(hero_supporting)
    st.markdown(
        """
        <div class="landing-signal-row">
            <div class="landing-signal">
                <strong>Weniger Rückfragen</strong>
                <span>Der Wizard fragt gezielt nach, statt ein starres Formular abzuarbeiten.</span>
            </div>
            <div class="landing-signal">
                <strong>Klarer Rollenanker</strong>
                <span>Jobtitel werden mit ESCO abgeglichen, damit alle Folgeschritte denselben Berufskontext nutzen.</span>
            </div>
            <div class="landing-signal">
                <strong>Direkt nutzbare Outputs</strong>
                <span>Aus dem Intake entstehen strukturierte Informationen für Recruiting, Hiring-Team und Summary.</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
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
            <h4>Nach dem Klick auf "Jetzt analysieren"</h4>
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
    iceberg_uri = _image_uri("Eisberg.png")
    st.markdown(
        f"""
        <section id="{LANDING_SECTION_IDS["importance"]}" class="landing-section">
            <div class="landing-iceberg-card">
                <img src="{iceberg_uri}" alt="{START_PAGE_COPY["importance_title"]}">
            </div>
        </section>
        """,
        unsafe_allow_html=True,
    )


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
