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


def _iceberg_image_uri() -> str:
    image_path = Path(__file__).resolve().parents[1] / "images" / "iceberg v1.png"
    image_bytes = image_path.read_bytes()
    return f"data:image/png;base64,{base64.b64encode(image_bytes).decode('utf-8')}"


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
                gap: 0.65rem;
                margin-top: 1.1rem;
            }
            .landing-signal {
                border: 1px solid #D9E2EC;
                background: #F8FAFC;
                border-radius: 8px;
                padding: 0.72rem 0.78rem;
            }
            .landing-signal strong {
                display: block;
                font-size: 0.9rem;
            }
            .landing-signal span {
                display: block;
                color: #334155;
                font-size: 0.82rem;
                line-height: 1.35;
                margin-top: 0.18rem;
            }
            .landing-compare-grid {
                display: grid;
                grid-template-columns: minmax(0, 0.9fr) minmax(0, 1.1fr);
                gap: 0.8rem;
                align-items: stretch;
                margin-top: 1rem;
            }
            .landing-compare-panel {
                border: 1px solid #D9E2EC;
                background: #FFFFFF;
                border-radius: 8px;
                padding: 0.85rem 0.9rem;
            }
            .landing-compare-panel h4,
            .landing-iceberg-panel h4,
            .landing-process-diagram h4 {
                margin: 0 0 0.5rem 0;
                font-size: 1rem;
            }
            .landing-compare-panel p {
                color: #334155;
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
                background: #FEF3C7;
            }
            .landing-compare-panel--ai {
                border-color: #0F766E;
                background: #ECFDF5;
            }
            .landing-iceberg-panel {
                margin-top: 0.85rem;
                border: 1px solid #D9E2EC;
                background: #FFFFFF;
                border-radius: 8px;
                padding: 0.9rem;
            }
            .landing-iceberg {
                position: relative;
                display: grid;
                grid-template-columns: minmax(0, 1.45fr) minmax(260px, 0.85fr);
                gap: 0.9rem;
                align-items: stretch;
            }
            .landing-iceberg-visual {
                position: relative;
                min-height: 320px;
                aspect-ratio: 16 / 9;
                overflow: hidden;
                border: 1px solid #D9E2EC;
                border-radius: 8px;
                background: #16324F;
            }
            .landing-iceberg-visual img {
                width: 100%;
                height: 100%;
                object-fit: cover;
                object-position: center;
                display: block;
            }
            .landing-iceberg-visual::after {
                content: "";
                position: absolute;
                inset: 0;
                background:
                    linear-gradient(90deg, rgba(22, 50, 79, 0.72), rgba(22, 50, 79, 0.18) 46%, rgba(22, 50, 79, 0.54)),
                    linear-gradient(180deg, rgba(22, 50, 79, 0.16), rgba(22, 50, 79, 0.28));
                pointer-events: none;
            }
            .landing-iceberg-overlay {
                position: absolute;
                z-index: 1;
                inset: 0.85rem;
                display: grid;
                grid-template-rows: minmax(0, 0.78fr) minmax(0, 1.22fr);
                gap: 0.75rem;
                pointer-events: none;
            }
            .landing-iceberg-overlay-card {
                max-width: min(330px, 52%);
                color: #FFFFFF;
                text-shadow: 0 2px 14px rgba(22, 50, 79, 0.72);
            }
            .landing-iceberg-overlay-card--classic {
                align-self: start;
            }
            .landing-iceberg-overlay-card--ai {
                align-self: end;
                max-width: min(380px, 58%);
            }
            .landing-iceberg-overlay-card strong {
                display: block;
                font-size: clamp(0.9rem, 1.25vw, 1.06rem);
                line-height: 1.2;
                margin-bottom: 0.32rem;
            }
            .landing-iceberg-overlay-card ul {
                margin: 0;
                padding-left: 1rem;
            }
            .landing-iceberg-overlay-card li {
                font-size: clamp(0.74rem, 1vw, 0.88rem);
                line-height: 1.25;
                margin-bottom: 0.2rem;
            }
            .landing-iceberg-risk {
                color: #FEF3C7;
                font-weight: 700;
            }
            .landing-waterline-badge {
                position: absolute;
                z-index: 1;
                top: 39%;
                right: 0.85rem;
                color: #FFFFFF;
                background: #0F766E;
                border: 1px solid #0F766E;
                padding: 0.16rem 0.48rem;
                border-radius: 999px;
                font-size: 0.72rem;
                font-weight: 650;
            }
            .landing-iceberg-lists {
                position: relative;
                z-index: 1;
                display: grid;
                gap: 0.65rem;
                align-content: start;
            }
            .landing-iceberg-detail {
                border: 1px solid #D9E2EC;
                border-radius: 8px;
                background: #F8FAFC;
            }
            .landing-iceberg-detail[open] {
                border-color: #0F766E;
                background: #ECFDF5;
            }
            .landing-iceberg-detail summary {
                cursor: pointer;
                padding: 0.75rem 0.82rem;
                font-weight: 800;
                list-style-position: inside;
            }
            .landing-iceberg-detail summary:focus-visible {
                outline: 2px solid #0F766E;
                outline-offset: 2px;
            }
            .landing-iceberg-detail ul {
                margin: 0 0 0.78rem 0;
                padding-left: 1.95rem;
                padding-right: 0.82rem;
            }
            .landing-iceberg-detail li {
                margin-bottom: 0.32rem;
                line-height: 1.34;
            }
            .landing-process-diagram {
                border: 1px solid #0F766E;
                background: #ECFDF5;
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
                border: 1px solid #D9E2EC;
                background: #FFFFFF;
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
                color: #334155;
                font-size: 0.82rem;
                line-height: 1.34;
            }
            .landing-process-result {
                margin-top: 0.8rem;
                border-left: 3px solid #0F766E;
                padding: 0.55rem 0.7rem;
                background: #FFFFFF;
                border-radius: 8px;
                color: #16324F;
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
                color: #334155;
                font-size: 0.86rem;
                font-weight: 700;
            }
            .landing-compare-panel,
            .landing-iceberg-panel,
            .landing-iceberg-overlay-card,
            .landing-process-step,
            .landing-signal,
            .landing-resource-links a {
                overflow-wrap: anywhere;
            }
            @media (max-width: 900px) {
                .landing-signal-row,
                .landing-compare-grid,
                .landing-iceberg,
                .landing-process-track {
                    grid-template-columns: minmax(0, 1fr);
                }
                .landing-process-step {
                    min-height: 0;
                }
                .landing-process-step::after {
                    display: none;
                }
                .landing-iceberg-visual {
                    min-height: 440px;
                }
                .landing-iceberg-overlay {
                    grid-template-rows: auto 1fr;
                }
                .landing-iceberg-overlay-card,
                .landing-iceberg-overlay-card--ai {
                    max-width: min(390px, 78%);
                }
                .landing-waterline-badge {
                    top: 43%;
                    right: 0.55rem;
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
    iceberg_image_uri = _iceberg_image_uri()

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
        <div class="landing-iceberg-panel">
            <h4>Was oberhalb und unterhalb der Wasserlinie liegt</h4>
            <div class="landing-iceberg">
                <div class="landing-iceberg-visual">
                    <img src="{iceberg_image_uri}" alt="Naturalistische Eisbergdarstellung: sichtbare Anforderungen über der Wasserlinie, verborgene Bedarfstreiber darunter.">
                    <div class="landing-waterline-badge">sichtbar in der Jobspec</div>
                    <div class="landing-iceberg-overlay">
                        <div class="landing-iceberg-overlay-card landing-iceberg-overlay-card--classic">
                            <strong>Klassisch: sichtbar, aber meist lückenhaft</strong>
                            <ul>
                                <li>Rollenbezeichnung, Aufgaben und Anforderungen</li>
                                <li>Rahmendaten wie Einsatzort, Vertrag und Angebot</li>
                                <li>erste Must-haves und Nice-to-haves</li>
                                <li class="landing-iceberg-risk">Risiko: unklare Begriffe bleiben unbemerkt</li>
                            </ul>
                        </div>
                        <div class="landing-iceberg-overlay-card landing-iceberg-overlay-card--ai">
                            <strong>AI-unterstützt: durch die App klärbar</strong>
                            <ul>
                                <li>fachliche Rolle hinter uneindeutigen Titeln</li>
                                <li>relevante Skills durch Abgleich mit der Marktsituation</li>
                                <li>Team-, Prozess- und Erwartungskontext</li>
                                <li>fehlende Anforderungen, Widersprüche und offene Entscheidungen</li>
                            </ul>
                        </div>
                    </div>
                </div>
                <div class="landing-iceberg-lists">
                    <details class="landing-iceberg-detail" open>
                        <summary>Oben: schnell sichtbar</summary>
                        <ul>
                            <li>Die Jobspec liefert den Ausgangspunkt.</li>
                            <li>Der Kontext bleibt ohne Nachfragen oft unscharf.</li>
                        </ul>
                    </details>
                    <details class="landing-iceberg-detail" open>
                        <summary>Unten: systematisch klärbar</summary>
                        <ul>
                            <li>ESCO, Skills und offene Entscheidungen werden zusammengeführt.</li>
                            <li>Summary, Interview und Hiring-Team erhalten dieselbe Grundlage.</li>
                        </ul>
                    </details>
                </div>
            </div>
        </div>
        """.format(iceberg_image_uri=iceberg_image_uri),
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
