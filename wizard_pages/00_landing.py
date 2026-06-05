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
                color: #ecfdf5 !important;
                text-decoration: none !important;
                border: 1px solid rgba(94, 234, 212, 0.42);
                background: rgba(20, 83, 75, 0.42);
                border-radius: 999px;
                padding: 0.38rem 0.78rem;
                font-size: 0.86rem;
                font-weight: 650;
            }
            .landing-resource-links a:hover,
            .landing-resource-links a:focus-visible {
                border-color: rgba(94, 234, 212, 0.78);
                background: rgba(20, 184, 166, 0.26);
                outline: none;
            }
            .landing-signal-row {
                display: grid;
                grid-template-columns: repeat(3, minmax(0, 1fr));
                gap: 0.65rem;
                margin-top: 1.1rem;
            }
            .landing-signal {
                border: 1px solid rgba(229, 231, 235, 0.16);
                background: rgba(255, 255, 255, 0.045);
                border-radius: 8px;
                padding: 0.72rem 0.78rem;
            }
            .landing-signal strong {
                display: block;
                font-size: 0.9rem;
            }
            .landing-signal span {
                display: block;
                color: rgba(229, 231, 235, 0.76);
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
                border: 1px solid rgba(229, 231, 235, 0.16);
                background: rgba(255, 255, 255, 0.04);
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
                color: rgba(229, 231, 235, 0.78);
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
                border-color: rgba(251, 191, 36, 0.34);
                background: linear-gradient(180deg, rgba(120, 53, 15, 0.22), rgba(255, 255, 255, 0.03));
            }
            .landing-compare-panel--ai {
                border-color: rgba(94, 234, 212, 0.36);
                background: linear-gradient(180deg, rgba(20, 83, 75, 0.28), rgba(255, 255, 255, 0.03));
            }
            .landing-iceberg-panel {
                margin-top: 0.85rem;
                border: 1px solid rgba(229, 231, 235, 0.16);
                background: linear-gradient(180deg, rgba(7, 18, 35, 0.94), rgba(8, 47, 73, 0.58));
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
                border: 1px solid rgba(125, 211, 252, 0.24);
                border-radius: 8px;
                background: rgba(2, 6, 23, 0.88);
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
                    linear-gradient(90deg, rgba(2, 6, 23, 0.26), transparent 34%, rgba(2, 6, 23, 0.18)),
                    linear-gradient(180deg, rgba(2, 6, 23, 0.1), rgba(2, 6, 23, 0.18));
                pointer-events: none;
            }
            .landing-iceberg-label {
                position: absolute;
                z-index: 1;
                left: 0.85rem;
                top: 0.8rem;
                max-width: min(360px, 70%);
                color: #f8fafc;
                font-size: clamp(1rem, 1.5vw, 1.34rem);
                font-weight: 800;
                line-height: 1.18;
                text-shadow: 0 2px 14px rgba(2, 6, 23, 0.72);
            }
            .landing-waterline-badge {
                position: absolute;
                z-index: 1;
                top: 38%;
                right: 0.85rem;
                color: rgba(186, 230, 253, 0.92);
                background: rgba(8, 47, 73, 0.95);
                border: 1px solid rgba(125, 211, 252, 0.42);
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
                border: 1px solid rgba(229, 231, 235, 0.16);
                border-radius: 8px;
                background: rgba(15, 23, 42, 0.72);
            }
            .landing-iceberg-detail[open] {
                border-color: rgba(94, 234, 212, 0.34);
                background: rgba(15, 23, 42, 0.84);
            }
            .landing-iceberg-detail summary {
                cursor: pointer;
                padding: 0.75rem 0.82rem;
                font-weight: 800;
                list-style-position: inside;
            }
            .landing-iceberg-detail summary:focus-visible {
                outline: 2px solid rgba(94, 234, 212, 0.72);
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
                border: 1px solid rgba(94, 234, 212, 0.28);
                background: linear-gradient(180deg, rgba(6, 78, 59, 0.22), rgba(15, 23, 42, 0.62));
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
                border: 1px solid rgba(229, 231, 235, 0.16);
                background: rgba(15, 23, 42, 0.72);
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
                border-top: 2px solid rgba(94, 234, 212, 0.8);
                border-right: 2px solid rgba(94, 234, 212, 0.8);
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
                color: #022c22;
                background: #5eead4;
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
                color: rgba(229, 231, 235, 0.76);
                font-size: 0.82rem;
                line-height: 1.34;
            }
            .landing-process-result {
                margin-top: 0.8rem;
                border-left: 3px solid rgba(94, 234, 212, 0.9);
                padding: 0.55rem 0.7rem;
                background: rgba(20, 83, 45, 0.26);
                border-radius: 8px;
                color: rgba(236, 253, 245, 0.96);
                font-weight: 650;
            }
            .landing-compare-panel,
            .landing-iceberg-panel,
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
                    min-height: 240px;
                }
                .landing-waterline-badge {
                    top: 40%;
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
                <p>Am Anfang werden meist nur die offensichtlichen Angaben erfasst.</p>
                <ul>
                    <li>Jobtitel, Aufgaben, Qualifikationen</li>
                    <li>Standort, Vertragsart, Benefits</li>
                    <li>erste Must-haves und Nice-to-haves</li>
                    <li>Risiko: unklare Begriffe bleiben unbemerkt</li>
                </ul>
            </div>
            <div class="landing-compare-panel landing-compare-panel--ai">
                <h4>AI-unterstützt: Kontext wird sichtbar</h4>
                <p>Die App erkennt, welche Informationen für genau diese Vakanz noch fehlen.</p>
                <ul>
                    <li>eindeutiger ESCO-Beruf und passende Skill-Familien</li>
                    <li>Team-, Prozess- und Erwartungskontext</li>
                    <li>fehlende Anforderungen, Widersprüche und offene Entscheidungen</li>
                    <li>strukturierte Basis für Summary, Interview, Hiring-Team und Export</li>
                </ul>
            </div>
        </div>
        <div class="landing-iceberg-panel">
            <h4>Der eigentliche Bedarf liegt oft unter der Oberfläche</h4>
            <div class="landing-iceberg">
                <div class="landing-iceberg-visual">
                    <img src="{iceberg_image_uri}" alt="Naturalistische Eisbergdarstellung: sichtbare Anforderungen über der Wasserlinie, verborgene Bedarfstreiber darunter.">
                    <div class="landing-iceberg-label">Der eigentliche Bedarf liegt oft unter der Oberfläche</div>
                    <div class="landing-waterline-badge">sichtbar in der Jobspec</div>
                </div>
                <div class="landing-iceberg-lists">
                    <details class="landing-iceberg-detail" open>
                        <summary>Oben: schnell erfassbar</summary>
                        <ul>
                            <li>Titel, Aufgaben, Qualifikationen</li>
                            <li>Standort, Vertragsart, Benefits</li>
                            <li>erste Skills und Verantwortungen</li>
                        </ul>
                    </details>
                    <details class="landing-iceberg-detail" open>
                        <summary>Unten: durch die App klärbar</summary>
                        <ul>
                            <li>fachliche Rolle hinter uneindeutigen Titeln</li>
                            <li>relevante Skills, Skill-Gruppen und offene Lücken</li>
                            <li>Teamumfeld, Führung, Prozess und Interview-Fokus</li>
                            <li>konkrete Folgeartefakte für bessere Recruiting-Aktivitäten</li>
                        </ul>
                    </details>
                    <div class="landing-resource-links">
                        <a href="https://employment-social-affairs.ec.europa.eu/policies-and-activities/skills-and-qualifications/skills-jobs/european-skillscompetences-qualifications-and-occupations-esco_en" target="_blank" rel="noopener noreferrer">Was ist ESCO?</a>
                        <a href="https://developers.openai.com/api/docs/guides/retrieval" target="_blank" rel="noopener noreferrer">Was bedeutet RAG?</a>
                        <a href="https://developers.openai.com/api/docs" target="_blank" rel="noopener noreferrer">OpenAI API Docs</a>
                    </div>
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
