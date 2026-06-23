"""Landing and intro section rendering helpers."""

from __future__ import annotations

from typing import Any, Callable, Mapping, Sequence

import streamlit as st

from constants import SSKey
from safe_html import escape_html_text, render_static_html


LANDING_STYLE_TOKENS: dict[str, str] = {
    "card_radius": "8px",
    "section_spacing": "0.85rem 0 1rem 0",
    "muted_text_color": "var(--cs-text-muted)",
    "emphasis_border": "3px solid var(--cs-success)",
    "emphasis_background": "var(--cs-success-soft)",
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


def render_landing_css(
    style_tokens: Mapping[str, str],
    *,
    streamlit_module: Any = st,
) -> None:
    card_radius = escape_html_text(style_tokens["card_radius"])
    section_spacing = escape_html_text(style_tokens["section_spacing"])
    muted_text_color = escape_html_text(style_tokens["muted_text_color"])
    emphasis_background = escape_html_text(style_tokens["emphasis_background"])
    emphasis_border = escape_html_text(style_tokens["emphasis_border"])
    render_static_html(
        f"""
        <style>
            .landing-section {{
                margin: {section_spacing};
            }}

            .landing-hero {{
                background: var(--cs-surface);
                border: 1px solid var(--cs-border);
                border-radius: {card_radius};
                padding: 1.15rem 1.1rem;
                box-shadow: var(--cs-shadow-sm);
            }}

            .landing-hero h1 {{
                margin: 0;
                font-size: clamp(1.55rem, 2vw, 2.15rem);
                line-height: 1.18;
                letter-spacing: 0;
                color: var(--cs-text);
            }}

            .landing-hero-copy {{
                max-width: 72ch;
            }}

            .landing-subhead {{
                margin-top: 0.6rem;
                color: var(--cs-text-muted);
                line-height: 1.5;
                font-size: 1rem;
            }}

            .landing-card {{
                background: var(--cs-surface);
                border: 1px solid var(--cs-border);
                border-radius: {card_radius};
                padding: 0.95rem;
                height: 100%;
                box-shadow: var(--cs-shadow-sm);
            }}

            .landing-card h4 {{
                margin: 0 0 0.45rem 0;
                font-size: 1rem;
                color: var(--cs-text);
            }}

            .landing-card p {{
                margin: 0;
                color: var(--cs-text-muted);
                line-height: 1.5;
            }}

            .landing-emphasis {{
                background: {emphasis_background};
                border-left: {emphasis_border};
                border-radius: {card_radius};
                padding: 0.72rem 0.8rem;
                margin-bottom: 0.75rem;
            }}

            .landing-emphasis p {{
                margin: 0;
                color: var(--cs-text);
                line-height: 1.5;
                font-size: 1.02rem;
                font-weight: 650;
            }}

            .landing-emphasis--subtle {{
                background: var(--cs-surface-muted);
                border-left: 3px solid var(--cs-border);
                padding-bottom: 0.65rem;
                margin-bottom: 0.65rem;
            }}

            .landing-problem-panel {{
                background: var(--cs-surface-muted);
                border: 1px solid var(--cs-border);
                border-radius: {card_radius};
                padding: 0.65rem 0.85rem;
                margin-top: 0.65rem;
            }}

            .landing-problem-list {{
                margin: 0.1rem 0 0 0;
                padding-left: 1rem;
                color: var(--cs-text-muted);
            }}

            .landing-problem-list li {{
                margin-bottom: 0.42rem;
                line-height: 1.35;
            }}

            .landing-problem-list strong {{
                color: var(--cs-text);
            }}

            .landing-problem-heading {{
                margin: 0 0 0.5rem 0;
                font-size: 0.9rem;
                letter-spacing: 0.01em;
                color: var(--cs-text);
            }}

            .landing-section-stack {{
                display: grid;
                gap: 0.65rem;
            }}

            .landing-outcome-callout {{
                margin-top: 0.75rem;
                border-radius: {card_radius};
                border: 1px solid var(--cs-success);
                background: var(--cs-success-soft);
                padding: 0.68rem 0.78rem;
            }}

            .landing-outcome-badge {{
                display: inline-flex;
                align-items: center;
                gap: 0.35rem;
                border: 1px solid var(--cs-success);
                border-radius: 999px;
                padding: 0.13rem 0.48rem;
                font-size: 0.76rem;
                font-weight: 650;
                text-transform: uppercase;
                letter-spacing: 0.02em;
                color: var(--cs-text);
                background: var(--cs-surface);
            }}

            .landing-outcome-text {{
                margin: 0.5rem 0 0 0;
                color: var(--cs-text);
                line-height: 1.42;
                font-size: 0.95rem;
            }}

            .landing-flow-step {{
                background: var(--cs-surface);
                border: 1px solid var(--cs-border);
                border-radius: {card_radius};
                padding: 0.68rem;
                min-height: 108px;
            }}

            .landing-list {{
                margin: 0.5rem 0 0 0;
                padding-left: 1.1rem;
            }}

            .landing-list li {{
                margin-bottom: 0.5rem;
                line-height: 1.45;
            }}

            .landing-output-panel {{
                background: var(--cs-surface);
                border: 1px solid var(--cs-border);
                border-radius: {card_radius};
                padding: 0.65rem 0.85rem;
                min-height: 100%;
            }}

            .landing-caption {{
                color: {muted_text_color};
                font-size: 0.9rem;
                margin-top: 0.35rem;
            }}

            .landing-app-title-row {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                gap: 0.8rem;
                margin-bottom: 0.45rem;
                flex-wrap: wrap;
            }}

            .landing-app-title {{
                color: var(--cs-text);
                font-size: 0.84rem;
                letter-spacing: 0.02em;
                text-transform: uppercase;
                font-weight: 650;
            }}

            .landing-app-links {{
                display: inline-flex;
                justify-content: flex-end;
                align-items: center;
                gap: 0.45rem;
                flex-wrap: wrap;
            }}

            .landing-app-link-pill {{
                display: inline-flex;
                align-items: center;
                gap: 0.35rem;
                padding: 0.34rem 0.75rem;
                border-radius: 999px;
                border: 1px solid var(--cs-primary);
                background: var(--cs-primary);
                text-decoration: none !important;
                color: var(--cs-on-primary, #FFFFFF) !important;
                font-size: 0.82rem;
                font-weight: 620;
                transition: transform 130ms ease, box-shadow 130ms ease, border-color 130ms ease;
            }}

            .landing-app-link-pill:hover {{
                transform: translateY(-1px);
                box-shadow: 0 8px 20px color-mix(in srgb, var(--cs-primary) 22%, transparent);
                border-color: color-mix(in srgb, var(--cs-primary) 88%, #000000);
                color: var(--cs-on-primary, #FFFFFF) !important;
            }}

            .landing-app-link-pill:visited,
            .landing-app-link-pill:focus,
            .landing-app-link-pill:active {{
                text-decoration: none !important;
                color: var(--cs-on-primary, #FFFFFF) !important;
            }}

            .landing-security-note {{
                background: var(--cs-warning-soft);
                border: 1px solid var(--cs-warning);
                border-radius: {card_radius};
                padding: 0.8rem 0.95rem;
                color: var(--cs-text);
                font-size: 0.9rem;
            }}

            @media (max-width: 900px) {{
                .landing-hero {{
                    padding: 1rem;
                }}

                .landing-hero-copy {{
                    max-width: 100%;
                }}

                .landing-flow-step {{
                    min-height: 0;
                }}
            }}
        </style>
        """,
        streamlit_module=streamlit_module,
    )


def render_hero_section(
    ctx: Any,
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
    next_step_line: str = "",
    post_cta_microcopy: str = "",
    value_cards: Sequence[tuple[str, str]],
    show_value_cards: bool = True,
    consent_given: bool,
    start_button_key: str,
    on_start: Callable[[], None],
    start_target: str,
    streamlit_module: Any = st,
) -> None:
    safe_section_id = escape_html_text(section_id, quote=True)
    render_static_html(
        f'<section id="{safe_section_id}" class="landing-section landing-hero">',
        streamlit_module=streamlit_module,
    )
    render_static_html('<div class="landing-hero-copy">', streamlit_module=streamlit_module)
    render_static_html(
        f"<h1>{escape_html_text(headline)}</h1>", streamlit_module=streamlit_module
    )
    if subhead:
        render_static_html(
            f'<p class="landing-subhead">{escape_html_text(subhead)}</p>',
            streamlit_module=streamlit_module,
        )
    if primary_cta and streamlit_module.button(
        primary_cta,
        key=start_button_key,
        type="primary",
        width="stretch",
        disabled=not consent_given,
    ):
        on_start()
        ctx.goto(start_target)
        streamlit_module.rerun()
    if secondary_cta_hint:
        render_static_html(
            f'<p class="landing-caption">{escape_html_text(secondary_cta_hint)}</p>',
            streamlit_module=streamlit_module,
        )
    if next_step_line:
        streamlit_module.caption(next_step_line)
    has_more_details = any(
        [
            bool(before_start_title and before_start_bullets),
            bool(reassurance_line),
            bool(extraction_helper_copy),
            bool(post_cta_microcopy),
        ]
    )
    if has_more_details:
        with streamlit_module.expander("Mehr erfahren", expanded=False):
            if before_start_title and before_start_bullets:
                streamlit_module.markdown(f"#### {before_start_title}")
                render_static_html(
                    '<ul class="landing-list">'
                    + "".join(
                        f"<li>{escape_html_text(bullet)}</li>"
                        for bullet in before_start_bullets
                    )
                    + "</ul>",
                    streamlit_module=streamlit_module,
                )
            if reassurance_line:
                streamlit_module.caption(reassurance_line)
            if extraction_helper_copy:
                streamlit_module.info(extraction_helper_copy, icon="ℹ️")
            if post_cta_microcopy:
                streamlit_module.caption(post_cta_microcopy)
    render_static_html("</div>", streamlit_module=streamlit_module)
    render_static_html("</section>", streamlit_module=streamlit_module)

    if show_value_cards and value_cards:
        render_static_html(
            f'<section id="{LANDING_SECTION_IDS["value_cards"]}" class="landing-section">',
            streamlit_module=streamlit_module,
        )
        streamlit_module.markdown("### Wertbeitrag auf einen Blick")
        render_value_cards(value_cards=value_cards, streamlit_module=streamlit_module)
        render_static_html("</section>", streamlit_module=streamlit_module)


def render_value_cards(
    *,
    value_cards: Sequence[tuple[str, str]],
    streamlit_module: Any = st,
) -> None:
    # Keep predictable 2-column rhythm to avoid narrow, uneven cards.
    for row_start in range(0, len(value_cards), 2):
        row_cols = streamlit_module.columns(2, gap="small")
        for col, (title, body) in zip(row_cols, value_cards[row_start : row_start + 2]):
            with col:
                render_static_html(
                    (
                        '<div class="landing-card">'
                        f"<h4>{escape_html_text(title)}</h4>"
                        f"<p>{escape_html_text(body)}</p>"
                        "</div>"
                    ),
                    streamlit_module=streamlit_module,
                )


def render_importance_section(
    *,
    section_id: str,
    title: str,
    intro: str,
    risk_points: Sequence[tuple[str, str]],
    leverage_points: Sequence[tuple[str, str]],
    closer: str,
    streamlit_module: Any = st,
) -> None:
    safe_section_id = escape_html_text(section_id, quote=True)
    render_static_html(
        f'<section id="{safe_section_id}" class="landing-section">',
        streamlit_module=streamlit_module,
    )
    streamlit_module.subheader(title)
    render_static_html(
        f'<div class="landing-emphasis"><p>{escape_html_text(intro)}</p></div>',
        streamlit_module=streamlit_module,
    )
    risk_items = "".join(
        f"<li><strong>{escape_html_text(point_title)}:</strong> {escape_html_text(body)}</li>"
        for point_title, body in risk_points
    )
    leverage_items = "".join(
        f"<li><strong>{escape_html_text(point_title)}:</strong> {escape_html_text(body)}</li>"
        for point_title, body in leverage_points
    )
    if risk_items or leverage_items:
        render_static_html(
            '<div class="landing-section-stack">', streamlit_module=streamlit_module
        )
    if risk_items:
        render_static_html(
            (
                '<div class="landing-problem-panel">'
                '<h4 class="landing-problem-heading">Ohne sauberen Intake</h4>'
                f'<ul class="landing-problem-list">{risk_items}</ul>'
                "</div>"
            ),
            streamlit_module=streamlit_module,
        )

    if leverage_items:
        render_static_html(
            (
                '<div class="landing-problem-panel">'
                '<h4 class="landing-problem-heading">Mit präzisem Intake</h4>'
                f'<ul class="landing-problem-list">{leverage_items}</ul>'
                "</div>"
            ),
            streamlit_module=streamlit_module,
        )
    if risk_items or leverage_items:
        render_static_html("</div>", streamlit_module=streamlit_module)

    render_static_html(
        (
            '<div class="landing-outcome-callout">'
            '<span class="landing-outcome-badge">🏁 Ergebnis</span>'
            f'<p class="landing-outcome-text">{escape_html_text(closer)}</p>'
            "</div>"
        ),
        streamlit_module=streamlit_module,
    )
    render_static_html("</section>", streamlit_module=streamlit_module)


def render_flow_steps(
    *,
    section_id: str,
    title: str,
    steps: Sequence[tuple[str, str]],
    streamlit_module: Any = st,
) -> None:
    safe_section_id = escape_html_text(section_id, quote=True)
    render_static_html(
        f'<section id="{safe_section_id}" class="landing-section">',
        streamlit_module=streamlit_module,
    )
    streamlit_module.subheader(title)
    for row_start in range(0, len(steps), 2):
        flow_cols = streamlit_module.columns(2, gap="small")
        for col, (step_title, body) in zip(flow_cols, steps[row_start : row_start + 2]):
            with col:
                render_static_html(
                    (
                        '<div class="landing-flow-step">'
                        f"<h4>{escape_html_text(step_title)}</h4>"
                        f"<p>{escape_html_text(body)}</p>"
                        "</div>"
                    ),
                    streamlit_module=streamlit_module,
                )
    render_static_html("</section>", streamlit_module=streamlit_module)


def render_output_section(
    *,
    section_id: str,
    title: str,
    bullets: Sequence[str],
    streamlit_module: Any = st,
) -> None:
    safe_section_id = escape_html_text(section_id, quote=True)
    render_static_html(
        f'<section id="{safe_section_id}" class="landing-section">',
        streamlit_module=streamlit_module,
    )
    streamlit_module.subheader(title)
    render_static_html(
        '<div class="landing-output-panel"><ul class="landing-list">'
        + "".join(f"<li>{escape_html_text(bullet)}</li>" for bullet in bullets)
        + "</ul></div>",
        streamlit_module=streamlit_module,
    )
    render_static_html("</section>", streamlit_module=streamlit_module)


def render_security_note(
    *,
    section_id: str,
    title: str,
    body: str,
    streamlit_module: Any = st,
) -> None:
    safe_section_id = escape_html_text(section_id, quote=True)
    render_static_html(
        f'<section id="{safe_section_id}" class="landing-section">',
        streamlit_module=streamlit_module,
    )
    streamlit_module.subheader(title)
    render_static_html(
        f'<div class="landing-security-note">{escape_html_text(body)}</div>',
        streamlit_module=streamlit_module,
    )
    render_static_html("</section>", streamlit_module=streamlit_module)
