"""Wizard base utilities (page model + navigation helpers)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, List, Mapping, Sequence

import streamlit as st

from constants import SSKey, STEPS


@dataclass(frozen=True)
class WizardPage:
    key: str
    title_de: str
    icon: str
    render: Callable[["WizardContext"], None]
    requires_jobspec: bool = False

    @property
    def label(self) -> str:
        return f"{self.icon} {self.title_de}" if self.icon else self.title_de


@dataclass
class WizardContext:
    pages: List[WizardPage]

    def get_current_page_key(self) -> str:
        return st.session_state.get(SSKey.CURRENT_STEP.value, STEPS[0].key)

    def goto(self, key: str) -> None:
        st.session_state[SSKey.CURRENT_STEP.value] = key

    def next(self) -> None:
        cur = self.get_current_page_key()
        keys = [p.key for p in self.pages]
        if cur in keys:
            i = keys.index(cur)
            if i < len(keys) - 1:
                self.goto(keys[i + 1])

    def prev(self) -> None:
        cur = self.get_current_page_key()
        keys = [p.key for p in self.pages]
        if cur in keys:
            i = keys.index(cur)
            if i > 0:
                self.goto(keys[i - 1])


def sidebar_navigation(ctx: WizardContext) -> WizardPage:
    pages = ctx.pages
    cur_key = ctx.get_current_page_key()
    options = [p.key for p in pages]
    format_map = {p.key: p.label for p in pages}

    def _format(k: str) -> str:
        return format_map.get(k, k)

    selected = st.sidebar.radio(
        "Wizard",
        options=options,
        index=options.index(cur_key) if cur_key in options else 0,
        format_func=_format,
    )
    if selected != cur_key:
        st.session_state[SSKey.CURRENT_STEP.value] = selected
        st.rerun()

    current_page = next(p for p in pages if p.key == selected)
    return current_page


def nav_buttons(
    ctx: WizardContext, *, disable_next: bool = False, disable_prev: bool = False
) -> None:
    c1, c2, c3 = st.columns([1, 1, 3])
    with c1:
        back_clicked = st.button("← Zurück", disabled=disable_prev)
    with c2:
        next_clicked = st.button("Weiter →", disabled=disable_next)
    with c3:
        st.caption("Fortschritt wird automatisch in dieser Session gespeichert.")
    # rerun only in normal render flow; callbacks may be within disallowed rerun contexts
    if back_clicked:
        ctx.prev()
        st.rerun()
    if next_clicked:
        ctx.next()
        st.rerun()


LANDING_STYLE_TOKENS: dict[str, str] = {
    "card_radius": "14px",
    "section_spacing": "2.1rem 0 2.4rem 0",
    "muted_text_color": "rgba(218, 231, 255, 0.92)",
    "emphasis_border": "4px solid rgba(126, 173, 255, 0.9)",
    "emphasis_background": "linear-gradient(135deg, rgba(21, 55, 106, 0.5), rgba(16, 37, 71, 0.35))",
}


LANDING_SECTION_IDS: dict[str, str] = {
    "hero": "LANDING_HERO",
    "value_cards": "LANDING_VALUE_CARDS",
    "importance": "LANDING_IMPORTANCE",
    "flow": "LANDING_FLOW",
    "output": "LANDING_OUTPUT",
    "security": "LANDING_SECURITY",
}


LANDING_CTA_KEYS: dict[str, str] = {
    "start": "landing.start_intake",
    "consent": SSKey.CONTENT_SHARING_CONSENT.value,
    "debug": SSKey.DEBUG.value,
}


def render_landing_css(style_tokens: Mapping[str, str]) -> None:
    st.markdown(
        f"""
        <style>
            .landing-section {{
                margin: {style_tokens["section_spacing"]};
            }}

            .landing-hero {{
                background: linear-gradient(145deg, rgba(10, 27, 52, 0.9), rgba(8, 20, 40, 0.85));
                border: 1px solid rgba(146, 185, 255, 0.3);
                border-radius: 18px;
                padding: 1.5rem 1.4rem;
                box-shadow: 0 10px 30px rgba(0, 0, 0, 0.25);
            }}

            .landing-hero h1 {{
                margin: 0;
                font-size: clamp(1.6rem, 2.3vw, 2.45rem);
                line-height: 1.2;
            }}

            .landing-subhead {{
                margin-top: 0.9rem;
                color: rgba(245, 247, 251, 0.94);
                line-height: 1.6;
                font-size: 1.05rem;
            }}

            .landing-card {{
                background: rgba(11, 25, 49, 0.72);
                border: 1px solid rgba(255, 255, 255, 0.14);
                border-radius: {style_tokens["card_radius"]};
                padding: 1rem;
                height: 100%;
            }}

            .landing-card h4 {{
                margin: 0 0 0.45rem 0;
                font-size: 1rem;
            }}

            .landing-card p {{
                margin: 0;
                color: rgba(245, 247, 251, 0.92);
                line-height: 1.5;
            }}

            .landing-emphasis {{
                background: {style_tokens["emphasis_background"]};
                border-left: {style_tokens["emphasis_border"]};
                border-radius: {style_tokens["card_radius"]};
                padding: 1rem 1rem 0.25rem 1rem;
                margin-bottom: 1rem;
            }}

            .landing-flow-step {{
                background: rgba(8, 18, 39, 0.62);
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 12px;
                padding: 0.95rem;
                min-height: 160px;
            }}

            .landing-list {{
                margin: 0.5rem 0 0 0;
                padding-left: 1.1rem;
            }}

            .landing-list li {{
                margin-bottom: 0.5rem;
                line-height: 1.45;
            }}

            .landing-caption {{
                color: {style_tokens["muted_text_color"]};
                font-size: 0.9rem;
                margin-top: 0.35rem;
            }}

            @media (max-width: 900px) {{
                .landing-hero {{
                    padding: 1.2rem;
                }}
            }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_hero_section(
    ctx: WizardContext,
    *,
    section_id: str,
    headline: str,
    subhead: str,
    primary_cta: str,
    secondary_cta_hint: str,
    before_start_title: str = "",
    before_start_bullets: Sequence[str] = (),
    reassurance_line: str = "",
    extraction_helper_copy: str = "",
    post_cta_microcopy: str = "",
    value_cards: Sequence[tuple[str, str]],
    consent_given: bool,
    start_button_key: str,
    on_start: Callable[[], None],
    start_target: str,
) -> None:
    st.markdown(
        f'<section id="{section_id}" class="landing-section landing-hero">',
        unsafe_allow_html=True,
    )
    hero_left, hero_right = st.columns([1.6, 1], gap="large")
    with hero_left:
        st.markdown(f"<h1>{headline}</h1>", unsafe_allow_html=True)
        st.markdown(f'<p class="landing-subhead">{subhead}</p>', unsafe_allow_html=True)
        if before_start_title and before_start_bullets:
            st.markdown(f"#### {before_start_title}")
            st.markdown(
                '<ul class="landing-list">'
                + "".join(f"<li>{bullet}</li>" for bullet in before_start_bullets)
                + "</ul>",
                unsafe_allow_html=True,
            )
        if reassurance_line:
            st.caption(reassurance_line)
        if st.button(
            primary_cta,
            key=start_button_key,
            type="primary",
            use_container_width=True,
            disabled=not consent_given,
        ):
            on_start()
            ctx.goto(start_target)
        if extraction_helper_copy:
            st.info(extraction_helper_copy, icon="ℹ️")
        if post_cta_microcopy:
            st.caption(post_cta_microcopy)
        st.markdown(
            f'<p class="landing-caption">{secondary_cta_hint}</p>',
            unsafe_allow_html=True,
        )
    with hero_right:
        st.markdown("### Wertbeitrag auf einen Blick")
        render_value_cards(value_cards=value_cards)

    st.markdown("</section>", unsafe_allow_html=True)


def render_value_cards(*, value_cards: Sequence[tuple[str, str]]) -> None:
    card_cols_top = st.columns(2, gap="small")
    card_cols_bottom = st.columns(2, gap="small")
    for index, (title, body) in enumerate(value_cards):
        target_col = card_cols_top[index] if index < 2 else card_cols_bottom[index - 2]
        with target_col:
            st.markdown(
                f'<div class="landing-card"><h4>{title}</h4><p>{body}</p></div>',
                unsafe_allow_html=True,
            )


def render_importance_section(
    *,
    section_id: str,
    title: str,
    intro: str,
    points: Sequence[tuple[str, str]],
    closer: str,
) -> None:
    st.markdown(
        f'<section id="{section_id}" class="landing-section">',
        unsafe_allow_html=True,
    )
    st.subheader(title)
    st.markdown(
        f'<div class="landing-emphasis"><p>{intro}</p></div>',
        unsafe_allow_html=True,
    )
    importance_cols = st.columns(3, gap="medium")
    for col, (point_title, body) in zip(importance_cols, points):
        with col:
            st.markdown(
                f'<div class="landing-card"><h4>{point_title}</h4><p>{body}</p></div>',
                unsafe_allow_html=True,
            )
    st.write(closer)
    st.markdown("</section>", unsafe_allow_html=True)


def render_flow_steps(
    *, section_id: str, title: str, steps: Sequence[tuple[str, str]]
) -> None:
    st.markdown(
        f'<section id="{section_id}" class="landing-section">',
        unsafe_allow_html=True,
    )
    st.subheader(title)
    flow_cols = st.columns(4, gap="small")
    for col, (step_title, body) in zip(flow_cols, steps):
        with col:
            st.markdown(
                f'<div class="landing-flow-step"><h4>{step_title}</h4><p>{body}</p></div>',
                unsafe_allow_html=True,
            )
    st.markdown("</section>", unsafe_allow_html=True)


def render_output_section(
    *, section_id: str, title: str, bullets: Sequence[str]
) -> None:
    st.markdown(
        f'<section id="{section_id}" class="landing-section">',
        unsafe_allow_html=True,
    )
    st.subheader(title)
    st.markdown('<div class="landing-card">', unsafe_allow_html=True)
    st.markdown(
        '<ul class="landing-list">'
        + "".join(f"<li>{bullet}</li>" for bullet in bullets)
        + "</ul>",
        unsafe_allow_html=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("</section>", unsafe_allow_html=True)


def render_security_note(*, section_id: str, title: str, body: str) -> None:
    st.markdown(
        f'<section id="{section_id}" class="landing-section">',
        unsafe_allow_html=True,
    )
    st.subheader(title)
    st.caption(body)
    st.markdown("</section>", unsafe_allow_html=True)
