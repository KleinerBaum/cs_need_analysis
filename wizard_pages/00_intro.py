from __future__ import annotations

import streamlit as st

from components.iceberg_need_analysis import (
    COMPONENT_HEIGHT,
    build_iceberg_need_analysis_html,
)
from content.start_page import START_PAGE_COPY
from constants import SSKey, STEP_KEY_INTRO, STEP_KEY_LANDING
from i18n import LANGUAGE_WIDGET_KEY_PAGE, render_language_toggle, t
from safe_html import escape_html_text, render_static_html
from wizard_pages.base import (
    LANDING_SECTION_IDS,
    LANDING_STYLE_TOKENS,
    WizardContext,
    WizardPage,
    render_landing_css,
)


INTRO_COPY = {
    "headline": "Recruiting-Briefing vor Workflow",
    "subheadline": (
        "Erst klären, welche Entscheidung ansteht. Danach den Wizard gezielt nutzen."
    ),
    "body": (
        (
            "Die App beginnt vor der Stellenanzeige: Aus Jobspec, Upload oder Rohtext "
            "entsteht zuerst ein prüfbarer Briefing-Stand für Search, Matching, "
            "Interview und Angebot."
        ),
        (
            "Erkannte Fakten, offene Lücken, ESCO-Referenzberufe und Folgefragen "
            "bleiben nachvollziehbar getrennt. Sie prüfen Werte, bevor daraus "
            "Recruiting-Unterlagen entstehen."
        ),
    ),
    "closing": "Starten Sie mit einer Quelle und erhalten Sie zuerst ein Recruiting-Briefing, nicht ein Formular.",
    "cta": "Briefing-Cockpit öffnen",
    "skip_title": "Briefing bereits vorbereitet",
    "skip_body": (
        "Die Einleitung ist jetzt optional. Öffnen Sie direkt den Start, prüfen Sie "
        "die erkannte Briefing-Basis und bestätigen Sie den Referenzberuf."
    ),
    "iceberg_title": "Warum Recruiting-Briefing?",
    "iceberg_caption": (
        "Das Eisberg-Modell zeigt, welche sichtbaren und verdeckten Informationen "
        "ein gutes Recruiting-Briefing zusammenführt."
    ),
}


def _has_prepared_briefing() -> bool:
    return isinstance(st.session_state.get(SSKey.JOB_EXTRACT.value), dict)


def _render_intro_overrides() -> None:
    render_static_html(
        """
        <style>
            .intro-page {
                max-width: 980px;
                margin: 0 auto;
            }
            .intro-page .landing-hero {
                padding: clamp(1rem, 2.4vw, 1.45rem);
            }
            .intro-body {
                display: grid;
                gap: 0.78rem;
                margin: 1rem 0 1.05rem 0;
                color: var(--cs-text);
                font-size: 0.98rem;
                line-height: 1.56;
            }
            .intro-body p {
                margin: 0;
            }
            .intro-closing {
                border-left: 4px solid var(--cs-success);
                background: var(--cs-success-soft);
                border-radius: 8px;
                padding: 0.72rem 0.85rem;
                margin: 0.25rem 0 0.8rem 0;
                color: var(--cs-text);
                font-weight: 700;
            }
            .intro-start-action {
                margin: 0 0 0.95rem 0;
            }
            .intro-process-diagram {
                border: 1px solid color-mix(in srgb, var(--cs-success) 42%, var(--cs-border));
                background: var(--cs-surface);
                border-radius: 8px;
                padding: clamp(0.82rem, 1.8vw, 1rem);
                box-shadow: var(--cs-shadow-sm);
                margin: 0.95rem 0 1rem 0;
            }
            .intro-process-track {
                display: grid;
                grid-template-columns: repeat(3, minmax(0, 1fr));
                gap: 0.7rem;
                max-width: 100%;
            }
            .intro-process-step {
                position: relative;
                border: 1px solid var(--cs-border);
                background: var(--cs-surface-muted);
                border-radius: 8px;
                padding: 0.62rem 0.65rem;
                min-height: 98px;
                overflow-wrap: anywhere;
            }
            .intro-process-step::after {
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
            .intro-process-step:last-child::after {
                display: none;
            }
            .intro-process-step span {
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
                margin-bottom: 0.4rem;
            }
            .intro-process-step strong {
                display: block;
                font-size: 0.92rem;
                line-height: 1.25;
                color: var(--cs-text);
            }
            .intro-process-step p {
                margin: 0.25rem 0 0 0;
                color: var(--cs-text-muted);
                font-size: 0.82rem;
                line-height: 1.34;
            }
            .intro-process-diagram h3 {
                margin: 0 0 0.35rem 0;
                color: var(--cs-text);
                font-size: 1.08rem;
            }
            .intro-process-heading {
                margin: 0 0 0.6rem 0;
                color: var(--cs-text-muted);
                line-height: 1.45;
            }
            .intro-process-result {
                margin-top: 0.65rem;
                border-left: 3px solid var(--cs-success);
                padding: 0.52rem 0.65rem;
                background: var(--cs-success-soft);
                border-radius: 8px;
                color: var(--cs-text);
                font-weight: 650;
            }
            .intro-process-resources {
                display: flex;
                flex-wrap: wrap;
                align-items: center;
                gap: 0.5rem;
                margin-top: 0.65rem;
            }
            .intro-process-resources span {
                color: var(--cs-text-muted);
                font-size: 0.86rem;
                font-weight: 700;
            }
            .intro-resource-links {
                display: flex;
                flex-wrap: wrap;
                gap: 0.45rem;
            }
            .intro-resource-links a {
                color: #FFFFFF !important;
                text-decoration: none !important;
                border: 1px solid var(--cs-success);
                background: var(--cs-success);
                border-radius: 8px;
                padding: 0.32rem 0.58rem;
                font-size: 0.8rem;
                font-weight: 650;
                overflow-wrap: anywhere;
            }
            .intro-resource-links a:hover,
            .intro-resource-links a:focus-visible {
                border-color: color-mix(in srgb, var(--cs-success) 88%, #000000);
                background: color-mix(in srgb, var(--cs-success) 88%, #000000);
                outline: 3px solid var(--cs-focus-ring);
                outline-offset: 2px;
            }
            .intro-trust-note {
                margin-top: 0.75rem;
                border: 1px solid var(--cs-border);
                background: var(--cs-surface-muted);
                border-radius: 8px;
                padding: 0.68rem 0.78rem;
                color: var(--cs-text);
                line-height: 1.45;
            }
            .intro-trust-note strong {
                display: block;
                margin-bottom: 0.22rem;
                color: var(--cs-text);
            }
            .intro-iceberg {
                border: 1px solid color-mix(in srgb, var(--cs-success) 34%, var(--cs-border));
                background: var(--cs-surface);
                border-radius: 8px;
                box-shadow: var(--cs-shadow-sm);
                padding: clamp(0.7rem, 1.6vw, 0.95rem);
                margin: 0.95rem 0 1rem 0;
            }
            .intro-iceberg h3 {
                margin: 0 0 0.25rem 0;
                color: var(--cs-text);
                font-size: 1.08rem;
            }
            .intro-iceberg p {
                margin: 0 0 0.75rem 0;
                color: var(--cs-text-muted);
                line-height: 1.45;
            }
            @media (max-width: 900px) {
                .intro-process-track {
                    grid-template-columns: minmax(0, 1fr);
                }
                .intro-process-step {
                    min-height: 0;
                }
                .intro-process-step::after {
                    display: none;
                }
            }
        </style>
        """,
        streamlit_module=st,
    )


def _render_intro_flow_cards() -> None:
    flow_heading = t("Was nach dem Briefing-Start entsteht")
    flow_steps = tuple(START_PAGE_COPY["flow_steps"])
    flow_step_html = "\n".join(
        f"""
                <div class="intro-process-step">
                    <span>{index}</span>
                    <strong>{escape_html_text(t(str(step_title)))}</strong>
                    <p>{escape_html_text(t(str(step_body)))}</p>
                </div>
        """
        for index, (step_title, step_body) in enumerate(flow_steps, start=1)
    )
    flow_result = t(
        "Eisberg-Prinzip: Sichtbare Jobspec-Daten bleiben mit verdeckten Entscheidungskriterien verbunden, damit Recruiting, Search und Interview dieselbe Briefing-Basis nutzen."
    )
    flow_context_label = t("Technische Vertrauensbasis:")
    esco_link_label = t("Was ist ESCO?")
    rag_link_label = t("Was bedeutet RAG?")
    security_title = t(START_PAGE_COPY["security_title"])
    security_body = t(START_PAGE_COPY["security_body"])
    render_static_html(
        f"""
        <section
            id="{escape_html_text(LANDING_SECTION_IDS["flow"], quote=True)}"
            class="intro-process-diagram"
        >
            <h3>{escape_html_text(t(START_PAGE_COPY["flow_title"]))}</h3>
            <p class="intro-process-heading">{escape_html_text(flow_heading)}</p>
            <div class="intro-process-track">
                {flow_step_html}
            </div>
            <div class="intro-process-result">
                {escape_html_text(flow_result)}
            </div>
            <div class="intro-process-resources">
                <span>{escape_html_text(flow_context_label)}</span>
                <div class="intro-resource-links">
                    <a href="https://employment-social-affairs.ec.europa.eu/policies-and-activities/skills-and-qualifications/skills-jobs/european-skillscompetences-qualifications-and-occupations-esco_en" target="_blank" rel="noopener noreferrer">{escape_html_text(esco_link_label)}</a>
                    <a href="https://developers.openai.com/api/docs/guides/retrieval" target="_blank" rel="noopener noreferrer">{escape_html_text(rag_link_label)}</a>
                    <a href="https://developers.openai.com/api/docs" target="_blank" rel="noopener noreferrer">OpenAI API Docs</a>
                </div>
            </div>
            <div class="intro-trust-note">
                <strong>{escape_html_text(security_title)}</strong>
                {escape_html_text(security_body)}
            </div>
        </section>
        """,
        streamlit_module=st,
    )


def _render_intro_iceberg() -> None:
    with st.container(border=True):
        st.markdown(f"### {t(INTRO_COPY['iceberg_title'])}")
        st.caption(str(t(INTRO_COPY["iceberg_caption"])))
        st.iframe(
            build_iceberg_need_analysis_html(),
            height=COMPONENT_HEIGHT,
        )


def render(ctx: WizardContext) -> None:
    render_landing_css(LANDING_STYLE_TOKENS)
    _render_intro_overrides()

    with st.container(border=True):
        render_language_toggle(location="main", key=LANGUAGE_WIDGET_KEY_PAGE)
        if _has_prepared_briefing():
            st.info(str(t(INTRO_COPY["skip_title"])))
            st.caption(str(t(INTRO_COPY["skip_body"])))
        st.title(str(t(INTRO_COPY["headline"])))
        st.subheader(str(t(INTRO_COPY["subheadline"])))

        for paragraph in INTRO_COPY["body"]:
            st.markdown(str(t(paragraph)))

        render_static_html(
            f'<div class="intro-closing">{escape_html_text(t(INTRO_COPY["closing"]))}</div>',
            streamlit_module=st,
        )
        if st.button(str(t(INTRO_COPY["cta"])), type="primary"):
            ctx.goto(STEP_KEY_LANDING)
            st.rerun()
    _render_intro_flow_cards()
    _render_intro_iceberg()


PAGE = WizardPage(
    key=STEP_KEY_INTRO,
    title_de="Einleitung",
    icon="ℹ️",
    render=render,
    requires_jobspec=False,
)
