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
        .cs-process-progress {
            display: flex;
            justify-content: center;
            margin: 0.15rem auto 0.85rem;
        }
        .cs-process-progress-list {
            display: flex;
            align-items: flex-start;
            justify-content: center;
            flex-wrap: wrap;
            gap: 0.45rem;
            margin: 0;
            padding: 0;
            list-style: none;
            max-width: min(100%, 980px);
        }
        .cs-process-progress-item {
            display: grid;
            grid-template-columns: auto minmax(0, 1fr);
            align-items: center;
            gap: 0.35rem;
            min-height: 2rem;
            padding: 0.28rem 0.55rem;
            border: 1px solid #D9E2EC;
            border-radius: 999px;
            background: #ffffff;
            color: #334155;
            font-size: 0.82rem;
            line-height: 1.2;
        }
        .cs-process-progress-item::before {
            content: "";
            width: 0.55rem;
            height: 0.55rem;
            border-radius: 999px;
            border: 1px solid #D9E2EC;
            background: #ffffff;
        }
        .cs-process-progress-item[data-status="complete"]::before {
            border-color: #0F766E;
            background: #0F766E;
        }
        .cs-process-progress-item[data-status="partial"]::before {
            border-color: #F59E0B;
            background: #F59E0B;
        }
        .cs-process-progress-item[data-current="true"] {
            border-color: #0F766E;
            background: #ECFDF5;
            color: #16324F;
            font-weight: 700;
        }
        .cs-process-progress-item[data-current="true"]::before {
            border-color: #0F766E;
            background: #0F766E;
        }
        .cs-process-progress-label {
            overflow-wrap: anywhere;
        }
        .cs-process-progress-count {
            color: inherit;
            font-weight: 600;
            white-space: nowrap;
        }
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
            .cs-process-progress {
                justify-content: flex-start;
            }
            .cs-process-progress-list {
                justify-content: flex-start;
            }
            .cs-process-progress-item {
                border-radius: 8px;
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


def render_process_progress(
    items: Sequence[dict[str, object]],
    *,
    aria_label: str = "Fortschritt des Informationsgewinnungsprozesses",
) -> None:
    progress_html = _build_process_progress_html(items, aria_label=aria_label)
    if progress_html:
        _render_html_block(progress_html)


def _build_process_progress_html(
    items: Sequence[dict[str, object]], *, aria_label: str
) -> str:
    entries: list[str] = []
    for item in items:
        label = str(item.get("label") or "").strip()
        if not label:
            continue
        status = str(item.get("status") or "not_started").strip()
        if status not in {"complete", "partial", "not_started"}:
            status = "not_started"
        count = str(item.get("count") or "").strip()
        current = "true" if bool(item.get("current")) else "false"
        title = str(item.get("title") or label).strip()
        count_html = (
            f'<span class="cs-process-progress-count">{escape(count)}</span>'
            if count
            else ""
        )
        entries.append(
            """
            <li class="cs-process-progress-item" data-status="{status}" data-current="{current}" title="{title}">
                <span class="cs-process-progress-label">{label}</span>{count_html}
            </li>
            """.format(
                status=escape(status),
                current=current,
                title=escape(title),
                label=escape(label),
                count_html=count_html,
            )
        )
    if not entries:
        return ""
    return """
        <nav class="cs-process-progress" aria-label="{aria_label}">
            <ol class="cs-process-progress-list">{entries}</ol>
        </nav>
        """.format(
            aria_label=escape(aria_label),
            entries="".join(entries),
        )


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
