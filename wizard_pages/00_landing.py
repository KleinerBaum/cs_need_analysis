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
            .landing-compare-grid {
                display: grid;
                grid-template-columns: repeat(2, minmax(0, 1fr));
                gap: 0.8rem;
                align-items: stretch;
                margin-top: 1rem;
            }
            .landing-compare-panel {
                border: 1px solid var(--cs-border);
                background: var(--cs-surface);
                border-radius: 8px;
                padding: 0.85rem 0.9rem;
            }
            .landing-compare-panel h4,
            .landing-context-panel h4,
            .landing-context-card h4,
            .landing-process-diagram h4 {
                margin: 0 0 0.5rem 0;
                font-size: 1rem;
                color: var(--cs-text);
            }
            .landing-compare-panel p {
                color: var(--cs-text-muted);
                line-height: 1.45;
                margin: 0 0 0.65rem 0;
            }
            .landing-compare-panel ul {
                margin: 0;
                padding-left: 1.05rem;
            }
            .landing-compare-panel li {
                margin-bottom: 0.42rem;
                line-height: 1.38;
            }
            .landing-compare-panel--classic {
                border-color: #F59E0B;
                background: var(--cs-warning-soft);
            }
            .landing-compare-panel--ai {
                border-color: #0F766E;
                background: var(--cs-success-soft);
            }
            .landing-context-panel {
                margin-top: 0.85rem;
                border: 1px solid var(--cs-border);
                background: var(--cs-surface);
                border-radius: 8px;
                padding: 0.9rem;
            }
            .landing-context-grid {
                display: grid;
                grid-template-columns: repeat(3, minmax(0, 1fr));
                gap: 0.75rem;
                align-items: stretch;
            }
            .landing-context-card {
                border: 1px solid var(--cs-border);
                border-radius: 8px;
                background: var(--cs-surface-muted);
                padding: 0.9rem;
                min-height: 100%;
            }
            .landing-context-card--source {
                border-color: #F59E0B;
                background: var(--cs-warning-soft);
            }
            .landing-context-card--ai {
                border-color: #0F766E;
                background: var(--cs-success-soft);
            }
            .landing-context-card--output {
                border-color: #2563EB;
                background: var(--cs-primary-soft);
            }
            .landing-context-card strong {
                display: block;
                color: var(--cs-text);
                margin-bottom: 0.45rem;
            }
            .landing-context-card ul {
                margin: 0;
                padding-left: 1.05rem;
            }
            .landing-context-card li {
                margin-bottom: 0.32rem;
                line-height: 1.34;
                color: var(--cs-text-muted);
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
            .landing-compare-panel,
            .landing-context-panel,
            .landing-context-card,
            .landing-process-step,
            .landing-signal,
            .landing-resource-links a {
                overflow-wrap: anywhere;
            }
            @media (max-width: 900px) {
                .landing-signal-row,
                .landing-compare-grid,
                .landing-context-grid,
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
    st.markdown(
        f'<section id="{LANDING_SECTION_IDS["importance"]}" class="landing-section landing-card">',
        unsafe_allow_html=True,
    )
    st.subheader(str(START_PAGE_COPY["importance_title"]))
    st.markdown(
        """
        Klassischer Intake sammelt oft nur das, was in der Jobspec sofort sichtbar ist.
        Dieser Wizard nutzt AI, ESCO und Retrieval-Augmented Generation, um den Bedarf
        schrittweise zu vervollständigen und später besser verwertbar zu machen.
        """.strip()
    )
    st.markdown("</section>", unsafe_allow_html=True)

    st.markdown(
        f'<section id="{LANDING_SECTION_IDS["value_cards"]}" class="landing-section">',
        unsafe_allow_html=True,
    )
    st.subheader("Klassische Bedarfsanalyse vs. AI-unterstützter Intake")
    st.markdown(
        """
        <div class="landing-compare-grid">
            <div class="landing-compare-panel landing-compare-panel--classic">
                <h4>Klassisch: sichtbar, aber lückenhaft</h4>
                <p>Die Jobspec zeigt den Startpunkt, aber selten den vollständigen Recruiting-Bedarf.</p>
            </div>
            <div class="landing-compare-panel landing-compare-panel--ai">
                <h4>AI-unterstützt: Kontext wird sichtbar</h4>
                <p>Die App ergänzt den Rollenanker, priorisiert offene Fragen und macht Folgeartefakte belastbarer.</p>
            </div>
        </div>
        <div class="landing-context-panel">
            <h4>Vom sichtbaren Text zur belastbaren Entscheidungsgrundlage</h4>
            <div class="landing-context-grid">
                <div class="landing-context-card landing-context-card--source">
                    <strong>Sichtbar in der Jobspec</strong>
                    <ul>
                        <li>Rollenbezeichnung, Aufgaben und Anforderungen</li>
                        <li>Rahmendaten wie Einsatzort, Vertrag und Angebot</li>
                        <li>erste Must-haves und Nice-to-haves</li>
                    </ul>
                </div>
                <div class="landing-context-card landing-context-card--ai">
                    <strong>Durch AI/ESCO klärbar</strong>
                    <ul>
                        <li>fachliche Rolle hinter uneindeutigen Titeln</li>
                        <li>relevante Skills durch Abgleich mit dem Berufskontext</li>
                        <li>fehlende Anforderungen, Widersprüche und offene Entscheidungen</li>
                    </ul>
                </div>
                <div class="landing-context-card landing-context-card--output">
                    <strong>Ergebnis für Recruiting</strong>
                    <ul>
                        <li>gemeinsamer Rollenanker für Hiring-Team und Recruiting</li>
                        <li>priorisierte Rückfragen statt langer Pflichtformulare</li>
                        <li>saubere Basis für Summary, Interview und Folgeartefakte</li>
                    </ul>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
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
