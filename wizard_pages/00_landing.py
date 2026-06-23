from __future__ import annotations

from pathlib import Path

import streamlit as st
from content.start_page import START_PAGE_COPY
from constants import APP_TITLE, SSKey, STEP_KEY_LANDING
from i18n import LANGUAGE_WIDGET_KEY_PAGE, active_language, render_language_toggle, t
from safe_html import escape_html_text, render_static_html
from ux_copy_contract import StepCopy, VacancyCopyContext, build_step_copy
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
    render_static_html(
        """
        <style>
            .landing-resource-links {
                display: flex;
                flex-wrap: wrap;
                gap: 0.45rem;
                margin-top: 0.65rem;
            }
            .landing-resource-links a {
                color: #FFFFFF !important;
                text-decoration: none !important;
                border: 1px solid var(--cs-success);
                background: var(--cs-success);
                border-radius: 8px;
                padding: 0.32rem 0.58rem;
                font-size: 0.8rem;
                font-weight: 650;
            }
            .landing-resource-links a:hover,
            .landing-resource-links a:focus-visible {
                border-color: color-mix(in srgb, var(--cs-success) 88%, #000000);
                background: color-mix(in srgb, var(--cs-success) 88%, #000000);
                outline: 3px solid var(--cs-focus-ring);
                outline-offset: 2px;
            }
            .landing-start-logo {
                display: flex;
                align-items: center;
                margin-bottom: 0.35rem;
            }
            .landing-start-logo [data-testid="stImage"] {
                width: 118px;
                max-width: min(118px, 44vw);
            }
            .landing-start-logo img {
                width: 100%;
                height: auto;
            }
            .landing-process-diagram {
                border: 1px solid color-mix(in srgb, var(--cs-success) 42%, var(--cs-border));
                background: var(--cs-surface);
                border-radius: 8px;
                padding: 0.82rem;
                box-shadow: var(--cs-shadow-sm);
            }
            .landing-intake-card {
                padding: 0.95rem;
            }
            .landing-process-track {
                display: grid;
                grid-template-columns: repeat(3, minmax(0, 1fr));
                gap: 0.7rem;
                max-width: 100%;
            }
            .landing-process-step {
                position: relative;
                border: 1px solid var(--cs-border);
                background: var(--cs-surface-muted);
                border-radius: 8px;
                padding: 0.62rem 0.65rem;
                min-height: 98px;
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
                margin-bottom: 0.4rem;
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
                margin-top: 0.65rem;
                border-left: 3px solid var(--cs-success);
                padding: 0.52rem 0.65rem;
                background: var(--cs-success-soft);
                border-radius: 8px;
                color: var(--cs-text);
                font-weight: 650;
            }
            .landing-process-resources {
                display: flex;
                flex-wrap: wrap;
                align-items: center;
                gap: 0.5rem;
                margin-top: 0.65rem;
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
            .landing-trust-note {
                margin-top: 0.75rem;
                border: 1px solid var(--cs-border);
                background: var(--cs-surface-muted);
                border-radius: 8px;
                padding: 0.68rem 0.78rem;
                color: var(--cs-text);
                line-height: 1.45;
            }
            .landing-trust-note strong {
                display: block;
                margin-bottom: 0.22rem;
                color: var(--cs-text);
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
        streamlit_module=st,
    )


def _landing_role_title() -> str:
    job_dict = st.session_state.get(SSKey.JOB_EXTRACT.value)
    if not isinstance(job_dict, dict):
        return ""
    return str(job_dict.get("job_title") or "").strip()


def _landing_copy_context() -> VacancyCopyContext | None:
    role_title = _landing_role_title()
    if not role_title:
        return None
    return VacancyCopyContext(role_title=role_title)


def _render_landing_hero(copy: StepCopy) -> None:
    with st.container(border=True):
        st.image(str(_landing_logo_path()), width=118)
        title_col, controls_col = st.columns([1.45, 1], gap="small")
        with title_col:
            render_static_html(
                f'<span class="landing-app-title">{escape_html_text(APP_TITLE)}</span>',
                streamlit_module=st,
            )
        with controls_col:
            render_language_toggle(location="main", key=LANGUAGE_WIDGET_KEY_PAGE)
            render_esco_language_toggle()
        st.title(copy.headline)
        if copy.value_line:
            st.subheader(copy.value_line)
        if copy.subheadline:
            st.markdown(copy.subheadline)


def _render_landing_flow_cards() -> None:
    st.subheader(str(t(START_PAGE_COPY["flow_title"])))
    flow_heading = t("Was nach dem Briefing-Start entsteht")
    flow_steps = tuple(START_PAGE_COPY["flow_steps"])
    flow_step_html = "\n".join(
        f"""
                <div class="landing-process-step">
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
            class="landing-process-diagram"
        >
            <h4>{escape_html_text(flow_heading)}</h4>
            <div class="landing-process-track">
                {flow_step_html}
            </div>
            <div class="landing-process-result">
                {escape_html_text(flow_result)}
            </div>
            <div class="landing-process-resources">
                <span>{escape_html_text(flow_context_label)}</span>
                <div class="landing-resource-links">
                    <a href="https://employment-social-affairs.ec.europa.eu/policies-and-activities/skills-and-qualifications/skills-jobs/european-skillscompetences-qualifications-and-occupations-esco_en" target="_blank" rel="noopener noreferrer">{escape_html_text(esco_link_label)}</a>
                    <a href="https://developers.openai.com/api/docs/guides/retrieval" target="_blank" rel="noopener noreferrer">{escape_html_text(rag_link_label)}</a>
                    <a href="https://developers.openai.com/api/docs" target="_blank" rel="noopener noreferrer">OpenAI API Docs</a>
                </div>
            </div>
            <div class="landing-trust-note">
                <strong>{escape_html_text(security_title)}</strong>
                {escape_html_text(security_body)}
            </div>
        </section>
        """,
        streamlit_module=st,
    )


def render(ctx: WizardContext) -> None:
    render_landing_css(LANDING_STYLE_TOKENS)
    _render_landing_responsive_overrides()
    landing_copy = build_step_copy(
        STEP_KEY_LANDING,
        language=active_language(),
        context=_landing_copy_context(),
    )
    _render_landing_hero(landing_copy)

    with st.container(border=True):
        render_jobad_intake(ctx, title=landing_copy.primary_cta)
    _render_landing_flow_cards()


PAGE = WizardPage(
    key="landing",
    title_de="Start",
    icon="🏁",
    render=render,
    requires_jobspec=False,
)
