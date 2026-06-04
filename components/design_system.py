"""Small reusable UI design-system fragments for Streamlit pages."""

from __future__ import annotations

from collections.abc import Sequence
from html import escape

import streamlit as st

_PILL_TONE_CLASS_MAP = {
    "neutral": "cs-pill--neutral",
    "primary": "cs-pill--primary",
    "warning": "cs-pill--warning",
    "success": "cs-pill--success",
}


def _render_html_block(html: str) -> None:
    render_html = getattr(st, "html", None)
    if callable(render_html):
        render_html(html)
        return
    st.markdown(html, unsafe_allow_html=True)


def _render_meta_items(meta_items: Sequence[tuple[str, str, str]]) -> str:
    entries: list[str] = []
    for icon, label, value in meta_items:
        entries.append(
            """
            <li class="cs-meta-item">
                <span class="cs-meta-icon">{icon}</span>
                <span class="cs-meta-label">{label}</span>
                <span class="cs-meta-value">{value}</span>
            </li>
            """.format(
                icon=escape(icon),
                label=escape(label),
                value=escape(value),
            )
        )
    if not entries:
        return ""
    return '<ul class="cs-meta-list">' + "".join(entries) + "</ul>"


def render_ui_styles() -> None:
    _render_html_block(
        """
        <style>
        .cs-step-title, .cs-output-title {
            margin: 0;
            font-size: 1.2rem;
            line-height: 1.4;
        }
        .cs-step-subtitle, .cs-output-context {
            margin: 0.25rem 0 0;
            color: #4b5563;
        }
        .cs-meta-list {
            margin: 0.75rem 0 0;
            padding: 0;
            list-style: none;
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 0.5rem;
        }
        .cs-meta-item {
            display: flex;
            gap: 0.4rem;
            align-items: baseline;
            font-size: 0.9rem;
        }
        .cs-meta-icon { opacity: 0.75; }
        .cs-meta-label { color: #4b5563; }
        .cs-meta-value { font-weight: 600; }
        .cs-step-topline, .cs-output-topline {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            gap: 0.75rem;
            flex-wrap: wrap;
        }
        .cs-step-topline > * {
            min-width: 0;
        }
        .cs-step-meta {
            display: flex;
            align-items: center;
            justify-content: flex-end;
            flex-wrap: wrap;
            gap: 0.4rem;
        }
        .cs-next-best-action .cs-next-title {
            margin: 0;
            font-size: 1rem;
        }
        .cs-next-best-action .cs-next-reason {
            margin: 0.4rem 0 0;
        }
        .cs-next-best-action .cs-next-cta {
            margin-top: 0.65rem;
            font-weight: 600;
        }
        @media (max-width: 960px) {
            .cs-grid-2, .cs-grid-3 {
                grid-template-columns: minmax(0, 1fr);
            }
            .cs-step-topline, .cs-output-topline {
                display: grid;
                grid-template-columns: minmax(0, 1fr);
                justify-items: start;
            }
            .cs-step-meta {
                justify-content: flex-start;
            }
            .cs-step-title, .cs-output-title {
                overflow-wrap: break-word;
                word-break: normal;
                hyphens: auto;
            }
        }
        </style>
        """,
    )


def render_pill(label: str, *, tone: str = "neutral") -> None:
    tone_class = _PILL_TONE_CLASS_MAP.get(tone, _PILL_TONE_CLASS_MAP["neutral"])
    _render_html_block(f'<span class="cs-pill {tone_class}">{escape(label)}</span>')


def render_step_header(
    title: str,
    subtitle: str,
    outcome: str | None = None,
    meta_items: Sequence[tuple[str, str, str]] = (),
) -> None:
    step_header_html = _build_step_header_html(
        title=title,
        subtitle=subtitle,
        outcome=outcome,
        meta_items=meta_items,
    )
    _render_html_block(step_header_html)


def _build_step_header_html(
    *,
    title: str,
    subtitle: str,
    outcome: str | None,
    meta_items: Sequence[tuple[str, str, str]],
) -> str:
    outcome_html = (
        f'<span class="cs-pill cs-pill--primary">{escape(outcome)}</span>' if outcome else ""
    )
    return f"""
        <section class="cs-step-header">
            <div class="cs-step-topline">
                <h2 class="cs-step-title">{escape(title)}</h2>
                <div class="cs-step-meta">{outcome_html}</div>
            </div>
            <p class="cs-step-subtitle">{escape(subtitle)}</p>
            {_render_meta_items(meta_items)}
        </section>
        """


def render_output_header(
    title: str,
    context: str,
    meta_items: Sequence[tuple[str, str, str]] = (),
) -> None:
    _render_html_block(
        f"""
        <section class="cs-output-header">
            <div class="cs-output-topline">
                <h3 class="cs-output-title">{escape(title)}</h3>
            </div>
            <p class="cs-output-context">{escape(context)}</p>
            {_render_meta_items(meta_items)}
        </section>
        """
    )


def render_card_start(class_name: str = "cs-card") -> None:
    safe_class = escape(class_name)
    _render_html_block(f'<section class="{safe_class}">')


def render_next_best_action(title: str, reason: str, cta_label: str | None = None) -> None:
    cta_html = (
        f'<div class="cs-next-cta">{escape(cta_label)}</div>' if cta_label else ""
    )
    _render_html_block(
        f"""
        <section class="cs-next-best-action">
            <h4 class="cs-next-title">{escape(title)}</h4>
            <p class="cs-next-reason">{escape(reason)}</p>
            {cta_html}
        </section>
        """
    )


def render_critical_gaps(gaps: Sequence[str], *, title: str = "Kritische Lücken") -> None:
    visible_gaps = [gap.strip() for gap in gaps if gap and gap.strip()]
    if not visible_gaps:
        return
    gap_items = "".join(f"<li>{escape(gap)}</li>" for gap in visible_gaps)
    _render_html_block(
        f"""
        <section class="cs-critical-gaps">
            <h4>{escape(title)}</h4>
            <ul>{gap_items}</ul>
        </section>
        """
    )
