"""Small reusable UI design-system fragments for Streamlit pages."""

from __future__ import annotations

import json
from collections.abc import Sequence
from html import escape
from pathlib import Path

import streamlit as st

from safe_html import render_static_html
from step_header_overview import StepHeaderOverview

ROOT_DIR = Path(__file__).resolve().parents[1]
DESIGN_SYSTEM_CSS_PATH = ROOT_DIR / "styles" / "design_system.css"
APP_SHELL_CSS_PATH = ROOT_DIR / "styles" / "app_shell.css"
_APP_SHELL_LIGHT_BACKGROUND_PLACEHOLDER = "__CS_STEP_BACKGROUND_LIGHT_URL__"
_APP_SHELL_DARK_BACKGROUND_PLACEHOLDER = "__CS_STEP_BACKGROUND_DARK_URL__"

_PILL_TONE_CLASS_MAP = {
    "neutral": "cs-pill--neutral",
    "primary": "cs-pill--primary",
    "warning": "cs-pill--warning",
    "success": "cs-pill--success",
}

_OVERVIEW_TONE_CLASS_MAP = {
    "neutral": "cs-step-overview--neutral",
    "primary": "cs-step-overview--primary",
    "warning": "cs-step-overview--warning",
    "success": "cs-step-overview--success",
}


def _render_html_block(html: str) -> None:
    render_html = getattr(st, "html", None)
    if callable(render_html):
        render_html(html)
        return
    render_static_html(html, streamlit_module=st)


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
    return (
        '<ul class="cs-meta-list" aria-label="Schrittstatus">'
        + "".join(entries)
        + "</ul>"
    )


def _render_step_header_overview(overview: StepHeaderOverview | None) -> str:
    if overview is None or not overview.groups:
        return ""

    group_entries: list[str] = []
    for group in overview.groups:
        item_entries: list[str] = []
        for item in group.items:
            tone_class = _OVERVIEW_TONE_CLASS_MAP.get(
                item.tone,
                _OVERVIEW_TONE_CLASS_MAP["neutral"],
            )
            value_html = (
                f'<span class="cs-step-overview-value">{escape(item.value)}</span>'
                if item.value
                else ""
            )
            chip_entries = [
                f'<span class="cs-step-overview-chip {tone_class}">{escape(label)}</span>'
                for label in item.items
            ]
            if item.count is not None and item.count > len(item.items):
                chip_entries.append(
                    '<span class="cs-step-overview-chip cs-step-overview--neutral">'
                    f"+{item.count - len(item.items)}</span>"
                )
            chips_html = (
                '<span class="cs-step-overview-chips">'
                + "".join(chip_entries)
                + "</span>"
                if chip_entries
                else ""
            )
            count_html = (
                f'<span class="cs-step-overview-count">{item.count}</span>'
                if item.count is not None and not chip_entries
                else ""
            )
            item_entries.append(
                """
                <li class="cs-step-overview-item {tone_class}">
                    <span class="cs-step-overview-label">{label}</span>
                    {value_html}{chips_html}{count_html}
                </li>
                """.format(
                    tone_class=tone_class,
                    label=escape(item.label),
                    value_html=value_html,
                    chips_html=chips_html,
                    count_html=count_html,
                )
            )
        if not item_entries:
            continue
        tone_class = _OVERVIEW_TONE_CLASS_MAP.get(
            group.tone,
            _OVERVIEW_TONE_CLASS_MAP["neutral"],
        )
        group_entries.append(
            """
            <section class="cs-step-overview-group {tone_class}">
                <h3 class="cs-step-overview-title">{title}</h3>
                <ul class="cs-step-overview-list">{items}</ul>
            </section>
            """.format(
                tone_class=tone_class,
                title=escape(group.title),
                items="".join(item_entries),
            )
        )
    if not group_entries:
        return ""
    return (
        '<div class="cs-step-overview" aria-label="Extrahierte und verbundene Daten">'
        + "".join(group_entries)
        + "</div>"
    )


def _path_mtime_ns(path: Path) -> int:
    return path.stat().st_mtime_ns


@st.cache_data(show_spinner=False)
def _load_text_asset(path: str, mtime_ns: int) -> str:
    del mtime_ns
    return Path(path).read_text(encoding="utf-8")


def _load_design_system_css(path: Path = DESIGN_SYSTEM_CSS_PATH) -> str:
    return _load_text_asset(str(path), _path_mtime_ns(path))


def _load_app_shell_css(path: Path = APP_SHELL_CSS_PATH) -> str:
    return _load_text_asset(str(path), _path_mtime_ns(path))


def _css_url_value(url: str) -> str:
    css_url = str(url).replace("<", "\\3C ").replace(">", "\\3E ")
    return json.dumps(css_url, ensure_ascii=True)


def build_app_shell_css(light_background_url: str, dark_background_url: str) -> str:
    css = _load_app_shell_css()
    replacements = {
        _APP_SHELL_LIGHT_BACKGROUND_PLACEHOLDER: _css_url_value(light_background_url),
        _APP_SHELL_DARK_BACKGROUND_PLACEHOLDER: _css_url_value(dark_background_url),
    }
    for placeholder, value in replacements.items():
        if placeholder not in css:
            raise ValueError(f"Missing app-shell CSS placeholder: {placeholder}")
        css = css.replace(placeholder, value)
    if any(placeholder in css for placeholder in replacements):
        raise ValueError("Unresolved app-shell CSS placeholder")
    return css


def render_ui_styles() -> None:
    _render_html_block(f"<style>{_load_design_system_css()}</style>")


def render_app_shell_styles(light_background_url: str, dark_background_url: str) -> None:
    css = build_app_shell_css(
        light_background_url=light_background_url,
        dark_background_url=dark_background_url,
    )
    _render_html_block(f"<style>{css}</style>")


def render_pill(label: str, *, tone: str = "neutral") -> None:
    tone_class = _PILL_TONE_CLASS_MAP.get(tone, _PILL_TONE_CLASS_MAP["neutral"])
    _render_html_block(f'<span class="cs-pill {tone_class}">{escape(label)}</span>')


def render_step_header(
    title: str,
    subtitle: str,
    outcome: str | None = None,
    meta_items: Sequence[tuple[str, str, str]] = (),
    overview: StepHeaderOverview | None = None,
) -> None:
    step_header_html = _build_step_header_html(
        title=title,
        subtitle=subtitle,
        outcome=outcome,
        meta_items=meta_items,
        overview=overview,
    )
    _render_html_block(step_header_html)


def build_step_section_heading_html(label: str) -> str:
    safe_label = str(label or "").strip()
    if not safe_label:
        return ""
    return f'<div class="cs-step-section-heading">{escape(safe_label)}</div>'


def render_step_section_heading(label: str) -> None:
    heading_html = build_step_section_heading_html(label)
    if heading_html:
        _render_html_block(heading_html)


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
    status_fallback_labels = {
        "complete": "Fertig",
        "partial": "In Arbeit",
        "not_started": "Offen",
    }
    for item in items:
        label = str(item.get("label") or "").strip()
        if not label:
            continue
        status = str(item.get("status") or "not_started").strip()
        if status not in {"complete", "partial", "not_started"}:
            status = "not_started"
        count = str(item.get("count") or "").strip()
        detail = str(item.get("detail") or "").strip()
        secondary_text = count or detail
        current = "true" if bool(item.get("current")) else "false"
        title = str(item.get("title") or label).strip()
        href = str(item.get("href") or "").strip()
        icon = str(item.get("icon") or "").strip()
        status_label = str(
            item.get("status_label") or status_fallback_labels[status]
        ).strip()
        step_index = str(item.get("step_index") or "").strip()
        step_total = str(item.get("step_total") or "").strip()
        if step_index and step_total:
            marker_label = f"{step_index}/{step_total}"
            marker_title = f"Schritt {step_index} von {step_total}"
        else:
            marker_label = step_index or "•"
            marker_title = "Schritt"
        status_detail_parts = [status_label]
        if secondary_text:
            status_detail_parts.append(secondary_text)
        status_detail = ", ".join(status_detail_parts)
        aria_label_text = f"{marker_title}: {label}. Status: {status_detail}."
        if current == "true":
            aria_label_text += " Aktueller Schritt."
        icon_html = (
            f'<span class="cs-process-progress-icon" aria-hidden="true">{escape(icon)}</span>'
            if icon
            else ""
        )
        count_html = (
            f'<span class="cs-process-progress-count">{escape(secondary_text)}</span>'
            if secondary_text
            else ""
        )
        aria_current = ' aria-current="step"' if current == "true" else ""
        tile_body = """
                <span class="cs-process-progress-marker" title="{marker_title}">{marker_label}</span>
                <span class="cs-process-progress-body">
                    <span class="cs-process-progress-label-row">
                        {icon_html}<span class="cs-process-progress-label">{label}</span>
                    </span>
                    <span class="cs-process-progress-meta">
                        <span class="cs-process-progress-status">{status_label}</span>{count_html}
                    </span>
                    <span class="cs-sr-only">{aria_label_text}</span>
                </span>
        """.format(
            marker_title=escape(marker_title),
            marker_label=escape(marker_label),
            icon_html=icon_html,
            label=escape(label),
            status_label=escape(status_label),
            count_html=count_html,
            aria_label_text=escape(aria_label_text),
        )
        if href:
            tile_html = (
                '<a class="cs-process-progress-link" href="{href}" title="{title}" aria-label="{aria_label_text}"{aria_current}>'
                "{tile_body}</a>"
            ).format(
                href=escape(href, quote=True),
                title=escape(title, quote=True),
                aria_label_text=escape(aria_label_text, quote=True),
                aria_current=aria_current,
                tile_body=tile_body,
            )
        else:
            tile_html = (
                '<div class="cs-process-progress-link" role="group" title="{title}" aria-label="{aria_label_text}"{aria_current}>'
                "{tile_body}</div>"
            ).format(
                title=escape(title, quote=True),
                aria_label_text=escape(aria_label_text, quote=True),
                aria_current=aria_current,
                tile_body=tile_body,
            )
        entries.append(
            """
            <li class="cs-process-progress-item" data-status="{status}" data-current="{current}">
                {tile_html}
            </li>
            """.format(
                status=escape(status),
                current=current,
                tile_html=tile_html,
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
    overview: StepHeaderOverview | None = None,
) -> str:
    outcome_html = (
        f'<span class="cs-pill cs-pill--primary">{escape(outcome)}</span>'
        if outcome
        else ""
    )
    subtitle_html = (
        f'<p class="cs-step-subtitle">{escape(subtitle)}</p>' if subtitle else ""
    )
    return f"""
        <section class="cs-step-header">
            <div class="cs-step-topline">
                <h2 class="cs-step-title">{escape(title)}</h2>
                <div class="cs-step-meta">{outcome_html}</div>
            </div>
            {subtitle_html}
            {_render_meta_items(meta_items)}
            {_render_step_header_overview(overview)}
        </section>
        """


def render_output_header(
    title: str,
    context: str,
    meta_items: Sequence[tuple[str, str, str]] = (),
    overview: StepHeaderOverview | None = None,
) -> None:
    context_html = (
        f'<p class="cs-output-context">{escape(context)}</p>' if context else ""
    )
    _render_html_block(f"""
        <section class="cs-output-header">
            <div class="cs-output-topline">
                <h3 class="cs-output-title">{escape(title)}</h3>
            </div>
            {context_html}
            {_render_meta_items(meta_items)}
            {_render_step_header_overview(overview)}
        </section>
        """)


def render_card_start(class_name: str = "cs-card") -> None:
    safe_class = escape(class_name)
    _render_html_block(f'<section class="{safe_class}">')


def render_next_best_action(
    title: str, reason: str, cta_label: str | None = None
) -> None:
    cta_html = (
        f'<div class="cs-next-cta">{escape(cta_label)}</div>' if cta_label else ""
    )
    _render_html_block(f"""
        <section class="cs-next-best-action">
            <h4 class="cs-next-title">{escape(title)}</h4>
            <p class="cs-next-reason">{escape(reason)}</p>
            {cta_html}
        </section>
        """)


def render_critical_gaps(
    gaps: Sequence[str], *, title: str = "Kritische Lücken"
) -> None:
    visible_gaps = [gap.strip() for gap in gaps if gap and gap.strip()]
    if not visible_gaps:
        return
    gap_items = "".join(f"<li>{escape(gap)}</li>" for gap in visible_gaps)
    _render_html_block(f"""
        <section class="cs-critical-gaps">
            <h4>{escape(title)}</h4>
            <ul>{gap_items}</ul>
        </section>
        """)
