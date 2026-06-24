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
    LANDING_STYLE_TOKENS,
    WizardContext,
    WizardPage,
    render_esco_language_toggle,
    render_landing_css,
    render_value_cards,
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
            .landing-intake-card {
                padding: 0.95rem;
            }
            .landing-unlocked-list {
                margin: 0.55rem 0 0 0;
                padding-left: 1.15rem;
                color: var(--cs-text);
            }
            .landing-unlocked-list li {
                margin: 0.28rem 0;
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


def _format_role_line(de_template: str, en_template: str, *, role_title: str) -> str:
    template = en_template if active_language() == "en" else de_template
    return template.format(role_title=role_title)


def _render_pre_upload_cockpit() -> None:
    with st.container(border=True):
        st.subheader(str(t(START_PAGE_COPY["cockpit_title"])))
        st.caption(str(t(START_PAGE_COPY["cockpit_caption"])))
        value_cards = [
            (str(t(str(title))), str(t(str(body))))
            for title, body in tuple(START_PAGE_COPY["value_cards"])
        ]
        render_value_cards(value_cards=value_cards)


def _render_unlocked_briefing_panel(role_title: str) -> None:
    items_html = "\n".join(
        f"<li>{escape_html_text(t(str(item)))}</li>"
        for item in tuple(START_PAGE_COPY["unlocked_items"])
    )
    with st.container(border=True):
        st.subheader(
            _format_role_line(
                "Schon freigeschaltet für {role_title}",
                "Already unlocked for {role_title}",
                role_title=role_title,
            )
        )
        st.caption(str(t(START_PAGE_COPY["unlocked_next_action"])))
        render_static_html(
            f'<ul class="landing-unlocked-list">{items_html}</ul>',
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
    role_title = _landing_role_title()
    if role_title:
        _render_unlocked_briefing_panel(role_title)
    else:
        _render_pre_upload_cockpit()

    with st.container(border=True):
        render_jobad_intake(ctx, title=landing_copy.primary_cta)


PAGE = WizardPage(
    key="landing",
    title_de="Start",
    icon="🏁",
    render=render,
    requires_jobspec=False,
)
