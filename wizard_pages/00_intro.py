from __future__ import annotations

import streamlit as st

from components.iceberg_need_analysis import (
    COMPONENT_HEIGHT,
    build_iceberg_need_analysis_html,
)
from constants import STEP_KEY_INTRO, STEP_KEY_LANDING
from i18n import t
from wizard_pages.base import (
    LANDING_STYLE_TOKENS,
    WizardContext,
    WizardPage,
    render_landing_css,
)


INTRO_COPY = {
    "headline": "Vakanzanforderungen präzise erfassen",
    "subheadline": (
        "Bevor Recruiting beginnt, muss klar sein, welche Person wirklich gesucht wird."
    ),
    "body": (
        (
            "Aus langjähriger Erfahrung in der Personalvermittlung zeigt sich immer wieder: "
            "Essentielle Informationen zu einer Vakanz ändern sich oft erst im laufenden "
            "Bewerbungsprozess, werden zu spät sichtbar oder fehlen vollständig. Das kann "
            "Abstimmungsschleifen, Fehlbesetzungen und hohe Folgekosten verursachen."
        ),
        (
            "Gerade in großen Unternehmen werden regelmäßig ähnliche Qualitäten gesucht "
            "und auf Basis derselben Stellenanzeige ausgeschrieben. Die individuellen "
            "Charakteristika einer konkreten Vakanz bleiben dabei häufig zu unscharf."
        ),
        (
            "Diese App fokussiert ausschließlich den ersten Schritt jedes Recruiting-Prozesses: "
            "Der fachliche Vorgesetzte definiert, welchen Mitarbeiter er sucht. Diverse "
            "Funktionen helfen dabei, mit möglichst wenig Aufwand ein umfassendes Bild der "
            "Stelle zu erstellen. Dafür nutzt die App die europäische Berufs- und "
            "Skill-Taxonomie ESCO sowie die OpenAI-API, um den Informationsgewinnungsprozess "
            "dynamisch an die individuellen Bedürfnisse Ihrer Vakanz anzupassen."
        ),
    ),
    "closing": "Bereit, die Anforderungen Ihrer Vakanz richtig kennenzulernen? Probieren Sie es aus.",
    "cta": "Zum Start",
    "iceberg_title": "Warum Need Analysis?",
    "iceberg_caption": (
        "Das Eisberg-Modell zeigt, welche sichtbaren und verdeckten Informationen "
        "eine gute Vakanzerfassung zusammenführt."
    ),
}


def _render_intro_overrides() -> None:
    st.markdown(
        """
        <style>
            .intro-page {
                max-width: 940px;
                margin: 0 auto;
            }
            .intro-page .landing-hero {
                padding: clamp(1.2rem, 3vw, 2rem);
            }
            .intro-body {
                display: grid;
                gap: 0.95rem;
                margin: 1.25rem 0 1.4rem 0;
                color: var(--cs-text);
                font-size: 1rem;
                line-height: 1.62;
            }
            .intro-body p {
                margin: 0;
            }
            .intro-closing {
                border-left: 4px solid var(--cs-success);
                background: var(--cs-success-soft);
                border-radius: 8px;
                padding: 0.8rem 0.95rem;
                margin: 0.3rem 0 1.1rem 0;
                color: var(--cs-text);
                font-weight: 700;
            }
            .intro-iceberg {
                border: 1px solid color-mix(in srgb, var(--cs-success) 34%, var(--cs-border));
                background: var(--cs-surface);
                border-radius: 8px;
                box-shadow: var(--cs-shadow-sm);
                padding: clamp(0.85rem, 2vw, 1.1rem);
                margin: 1.2rem 0 1.25rem 0;
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
        unsafe_allow_html=True,
    )


def _render_intro_iceberg() -> None:
    st.markdown(
        (
            '<section class="intro-iceberg">'
            f'<h3>{t(INTRO_COPY["iceberg_title"])}</h3>'
            f'<p>{t(INTRO_COPY["iceberg_caption"])}</p>'
        ),
        unsafe_allow_html=True,
    )
    st.iframe(
        build_iceberg_need_analysis_html(),
        height=COMPONENT_HEIGHT,
    )
    st.markdown("</section>", unsafe_allow_html=True)


def render(ctx: WizardContext) -> None:
    render_landing_css(LANDING_STYLE_TOKENS)
    _render_intro_overrides()

    st.markdown('<div class="intro-page">', unsafe_allow_html=True)
    st.markdown(
        '<section class="landing-section landing-hero">',
        unsafe_allow_html=True,
    )
    st.title(str(t(INTRO_COPY["headline"])))
    st.subheader(str(t(INTRO_COPY["subheadline"])))

    st.markdown('<div class="intro-body">', unsafe_allow_html=True)
    for paragraph in INTRO_COPY["body"]:
        st.markdown(f"<p>{t(paragraph)}</p>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown(
        f'<div class="intro-closing">{t(INTRO_COPY["closing"])}</div>',
        unsafe_allow_html=True,
    )
    _render_intro_iceberg()
    if st.button(str(t(INTRO_COPY["cta"])), type="primary"):
        ctx.goto(STEP_KEY_LANDING)
        st.rerun()
    st.markdown("</section>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)


PAGE = WizardPage(
    key=STEP_KEY_INTRO,
    title_de="Einleitung",
    icon="ℹ️",
    render=render,
    requires_jobspec=False,
)
