from __future__ import annotations

import streamlit as st

from components.iceberg_need_analysis import (
    COMPONENT_HEIGHT,
    build_iceberg_need_analysis_html,
)
from constants import SSKey, STEP_KEY_INTRO, STEP_KEY_LANDING
from i18n import LANGUAGE_WIDGET_KEY_PAGE, render_language_toggle, t
from safe_html import escape_html_text, render_static_html
from wizard_pages.base import (
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
        "eine gute Vakanzerfassung zusammenführt."
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
        </style>
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
    _render_intro_iceberg()


PAGE = WizardPage(
    key=STEP_KEY_INTRO,
    title_de="Einleitung",
    icon="ℹ️",
    render=render,
    requires_jobspec=False,
)
