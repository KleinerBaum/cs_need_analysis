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
    return '<ul class="cs-meta-list" aria-label="Schrittstatus">' + "".join(entries) + "</ul>"


def render_ui_styles() -> None:
    _render_html_block(
        """
        <style>
        :root,
        :root[data-theme="light"],
        html[data-theme="light"],
        body[data-theme="light"],
        [data-theme="light"] {
            color-scheme: light;
            --cs-font-sans: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
            --cs-font-mono: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
            --cs-primary-navy: #0B1724;
            --cs-primary-blue: #1D4ED8;
            --cs-guidance-teal: #0F766E;
            --cs-bg: var(--background-color, #F4F7FA);
            --cs-surface: var(--secondary-background-color, #FFFFFF);
            --cs-surface-raised: #FCFDFF;
            --cs-surface-muted: color-mix(
                in srgb,
                var(--secondary-background-color, #FFFFFF) 86%,
                var(--background-color, #F4F7FA)
            );
            --cs-border: var(--border-color, #CAD6E2);
            --cs-border-soft: color-mix(in srgb, var(--border-color, #CAD6E2) 66%, transparent);
            --cs-text: var(--text-color, #142033);
            --cs-text-muted: #475569;
            --cs-text-subtle: #64748B;
            --cs-sidebar-bg: #0B1724;
            --cs-sidebar-surface: #142033;
            --cs-sidebar-surface-muted: #1E2C42;
            --cs-sidebar-border: #2D3A4F;
            --cs-sidebar-text: #F8FAFC;
            --cs-sidebar-text-muted: #CBD5E1;
            --cs-sidebar-surface-text: #F8FAFC;
            --cs-sidebar-surface-text-muted: #CBD5E1;
            --cs-primary: var(--primary-color, var(--cs-primary-blue));
            --cs-on-primary: #FFFFFF;
            --cs-primary-soft: #E8F0FF;
            --cs-success: var(--cs-guidance-teal);
            --cs-success-soft: #E6F6F3;
            --cs-warning: #B45309;
            --cs-warning-soft: #FFF4DA;
            --cs-danger: #B91C1C;
            --cs-danger-soft: #FDECEC;
            --cs-focus-ring: color-mix(in srgb, var(--cs-primary) 38%, transparent);
            --cs-shadow-sm: 0 1px 2px rgba(15, 23, 42, 0.05);
            --cs-shadow-md: 0 14px 30px rgba(15, 23, 42, 0.07);
            --cs-radius-sm: 8px;
            --cs-radius-md: 10px;
            --cs-radius-lg: 12px;
        }
        :root[data-theme="dark"],
        html[data-theme="dark"],
        body[data-theme="dark"],
        [data-theme="dark"] {
            color-scheme: dark;
            --cs-primary-navy: #0B1220;
            --cs-primary-blue: #60A5FA;
            --cs-guidance-teal: #2DD4BF;
            --cs-bg: #0B111B;
            --cs-surface: #111827;
            --cs-surface-raised: #172033;
            --cs-surface-muted: #1E293B;
            --cs-border: #334155;
            --cs-border-soft: #475569;
            --cs-text: #F1F5F9;
            --cs-text-muted: #CBD5E1;
            --cs-text-subtle: #94A3B8;
            --cs-sidebar-bg: #07111F;
            --cs-sidebar-surface: #142033;
            --cs-sidebar-surface-muted: #1E2C42;
            --cs-sidebar-border: #2D3A4F;
            --cs-sidebar-text: #F8FAFC;
            --cs-sidebar-text-muted: #CBD5E1;
            --cs-sidebar-surface-text: #F8FAFC;
            --cs-sidebar-surface-text-muted: #CBD5E1;
            --cs-primary: #60A5FA;
            --cs-on-primary: #07111F;
            --cs-primary-soft: color-mix(in srgb, var(--cs-primary) 20%, var(--cs-surface));
            --cs-success: #2DD4BF;
            --cs-success-soft: color-mix(in srgb, var(--cs-success) 18%, var(--cs-surface));
            --cs-warning: #FBBF24;
            --cs-warning-soft: color-mix(in srgb, var(--cs-warning) 18%, var(--cs-surface));
            --cs-danger: #F87171;
            --cs-danger-soft: color-mix(in srgb, var(--cs-danger) 18%, var(--cs-surface));
            --cs-focus-ring: color-mix(in srgb, var(--cs-primary) 45%, transparent);
            --cs-shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.24);
            --cs-shadow-md: 0 14px 32px rgba(0, 0, 0, 0.28);
        }
        html,
        body,
        .stApp,
        .stMain,
        .stMainBlockContainer,
        .block-container,
        [data-testid="stAppViewContainer"] {
            background: var(--cs-bg);
            color: var(--cs-text-muted);
            font-family: var(--cs-font-sans);
            letter-spacing: 0;
        }
        h1,
        h2,
        h3,
        h4,
        h5,
        h6,
        label,
        p,
        li,
        [data-testid="stMarkdownContainer"],
        [data-testid="stWidgetLabel"],
        [data-testid="stDataFrame"],
        [data-testid="stTable"] {
            color: var(--cs-text);
            font-family: var(--cs-font-sans);
            letter-spacing: 0;
        }
        [data-testid="stCaptionContainer"],
        small {
            color: var(--cs-text-muted) !important;
        }
        [data-theme="dark"] h1,
        [data-theme="dark"] h2,
        [data-theme="dark"] h3,
        [data-theme="dark"] h4,
        [data-theme="dark"] h5,
        [data-theme="dark"] h6,
        [data-theme="dark"] label,
        [data-theme="dark"] p,
        [data-theme="dark"] li,
        [data-theme="dark"] [data-testid="stMarkdownContainer"],
        [data-theme="dark"] [data-testid="stWidgetLabel"],
        [data-theme="dark"] [data-testid="stDataFrame"],
        [data-theme="dark"] [data-testid="stTable"] {
            color: var(--cs-text) !important;
        }
        [data-theme="dark"] [data-testid="stCaptionContainer"],
        [data-theme="dark"] small {
            color: var(--cs-text-muted) !important;
        }
        [data-testid="stSidebar"] {
            background: var(--cs-sidebar-bg) !important;
            border-color: var(--cs-sidebar-border) !important;
            color: var(--cs-sidebar-text);
        }
        [data-testid="stSidebarContent"] {
            background: var(--cs-sidebar-bg) !important;
            color: var(--cs-sidebar-text);
        }
        [data-testid="stSidebar"] h1,
        [data-testid="stSidebar"] h2,
        [data-testid="stSidebar"] h3,
        [data-testid="stSidebar"] h4,
        [data-testid="stSidebar"] h5,
        [data-testid="stSidebar"] h6,
        [data-testid="stSidebar"] p,
        [data-testid="stSidebar"] span,
        [data-testid="stSidebar"] li,
        [data-testid="stSidebar"] label,
        [data-testid="stSidebar"] [data-testid="stMarkdownContainer"],
        [data-testid="stSidebar"] [data-testid="stWidgetLabel"],
        [data-testid="stSidebar"] .cs-sidebar-title {
            color: var(--cs-sidebar-text) !important;
        }
        [data-testid="stSidebar"] [data-testid="stCaptionContainer"],
        [data-testid="stSidebar"] small,
        [data-testid="stSidebar"] .caption {
            color: var(--cs-sidebar-text-muted) !important;
        }
        [data-testid="stSidebar"] [data-testid="stExpander"] {
            background: var(--cs-sidebar-surface) !important;
            border: 1px solid var(--cs-sidebar-border) !important;
            border-radius: var(--cs-radius-md);
            color: var(--cs-sidebar-surface-text);
        }
        [data-testid="stSidebar"] [data-testid="stExpander"] summary,
        [data-testid="stSidebar"] [data-testid="stExpander"] summary p,
        [data-testid="stSidebar"] [data-testid="stExpander"] [data-testid="stMarkdownContainer"],
        [data-testid="stSidebar"] [data-testid="stExpander"] [data-testid="stWidgetLabel"] {
            color: var(--cs-sidebar-surface-text) !important;
        }
        [data-testid="stSidebar"] [data-testid="stExpander"] [data-testid="stCaptionContainer"] {
            color: var(--cs-sidebar-surface-text-muted) !important;
        }
        [data-testid="stSidebar"] [data-testid="stProgress"] > div > div {
            background: var(--cs-sidebar-surface-muted) !important;
        }
        [data-testid="stSidebar"] [data-testid="stProgress"] [role="progressbar"] > div {
            background: var(--cs-primary) !important;
        }
        [data-testid="stSidebar"] [data-testid="stProgress"] [data-testid="stMarkdownContainer"] {
            color: var(--cs-sidebar-text-muted) !important;
        }
        [data-testid="stSidebar"] a,
        [data-testid="stSidebar"] [data-testid="stPageLink"] a {
            color: var(--cs-sidebar-text) !important;
            text-decoration-color: color-mix(in srgb, var(--cs-sidebar-text) 48%, transparent);
        }
        [data-testid="stSidebar"] [data-testid="stPageLink"] a:hover {
            color: #FFFFFF !important;
            background: rgba(255, 255, 255, 0.08);
        }
        [data-testid="stSidebar"] [data-testid="stRadio"] label,
        [data-testid="stSidebar"] [data-testid="stCheckbox"] label,
        [data-testid="stSidebar"] [data-testid="stToggle"] label {
            color: var(--cs-sidebar-text) !important;
        }
        [data-testid="stSidebar"] [data-testid="stRadio"] [role="radiogroup"] label,
        [data-testid="stSidebar"] [data-testid="stCheckbox"] label,
        [data-testid="stSidebar"] [data-testid="stToggle"] label {
            border-radius: var(--cs-radius-sm);
        }
        [data-testid="stSidebar"] [data-baseweb="radio"] > div:first-child,
        [data-testid="stSidebar"] [data-testid="stCheckbox"] span,
        [data-testid="stSidebar"] [data-testid="stToggle"] span,
        [data-testid="stSidebar"] [data-testid="stRadio"] svg,
        [data-testid="stSidebar"] [data-testid="stCheckbox"] svg,
        [data-testid="stSidebar"] [data-testid="stToggle"] svg {
            color: inherit !important;
            fill: currentColor !important;
        }
        [data-testid="stSidebar"] input,
        [data-testid="stSidebar"] textarea,
        [data-testid="stSidebar"] [data-baseweb="select"] > div,
        [data-testid="stSidebar"] [data-baseweb="textarea"] textarea,
        [data-testid="stSidebar"] [data-baseweb="input"] > div {
            background: var(--cs-sidebar-surface) !important;
            border-color: var(--cs-sidebar-border) !important;
            color: var(--cs-sidebar-surface-text) !important;
        }
        [data-testid="stSidebar"] [data-baseweb="select"] *,
        [data-testid="stSidebar"] [data-baseweb="input"] *,
        [data-testid="stSidebar"] [data-baseweb="textarea"] * {
            color: var(--cs-sidebar-surface-text) !important;
        }
        [data-testid="stSidebar"] input::placeholder,
        [data-testid="stSidebar"] textarea::placeholder {
            color: var(--cs-sidebar-surface-text-muted) !important;
        }
        [data-testid="stSidebar"] [data-testid="stButton"] button,
        [data-testid="stSidebar"] [data-testid="stFormSubmitButton"] button,
        [data-testid="stSidebar"] [data-testid="stDownloadButton"] button {
            background: var(--cs-sidebar-surface) !important;
            border-color: var(--cs-sidebar-border) !important;
            color: var(--cs-sidebar-surface-text) !important;
            box-shadow: none;
        }
        [data-testid="stSidebar"] [data-testid="stButton"] button:hover,
        [data-testid="stSidebar"] [data-testid="stFormSubmitButton"] button:hover,
        [data-testid="stSidebar"] [data-testid="stDownloadButton"] button:hover {
            border-color: var(--cs-primary) !important;
            color: var(--cs-primary) !important;
        }
        [data-testid="stSidebar"] [data-testid="stButton"] button[kind="primary"],
        [data-testid="stSidebar"] [data-testid="stFormSubmitButton"] button[kind="primary"],
        [data-testid="stSidebar"] [data-testid="stDownloadButton"] button[kind="primary"] {
            background: var(--cs-primary) !important;
            border-color: var(--cs-primary) !important;
            color: var(--cs-on-primary) !important;
        }
        [data-testid="stButton"] button {
            border-radius: var(--cs-radius-sm) !important;
            border-color: var(--cs-border) !important;
            background: var(--cs-surface) !important;
            color: var(--cs-text) !important;
            font-family: var(--cs-font-sans);
            font-weight: 650;
            box-shadow: var(--cs-shadow-sm);
        }
        [data-testid="stButton"] button *,
        [data-testid="stFormSubmitButton"] button *,
        [data-testid="stDownloadButton"] button * {
            color: inherit !important;
            fill: currentColor !important;
        }
        [data-testid="stFormSubmitButton"] button,
        [data-testid="stDownloadButton"] button {
            border-radius: var(--cs-radius-sm) !important;
            border-color: var(--cs-border) !important;
            background: var(--cs-surface) !important;
            color: var(--cs-text) !important;
            font-family: var(--cs-font-sans);
            font-weight: 650;
            box-shadow: var(--cs-shadow-sm);
        }
        [data-testid="stButton"] button:hover,
        [data-testid="stFormSubmitButton"] button:hover,
        [data-testid="stDownloadButton"] button:hover {
            border-color: var(--cs-primary) !important;
            color: var(--cs-primary) !important;
        }
        [data-testid="stButton"] button:focus-visible,
        [data-testid="stFormSubmitButton"] button:focus-visible,
        [data-testid="stDownloadButton"] button:focus-visible,
        [data-testid="stRadio"] label:focus-within,
        [data-testid="stCheckbox"] label:focus-within,
        [data-testid="stToggle"] label:focus-within,
        input:focus,
        textarea:focus,
        [data-baseweb="select"] > div:focus-within {
            outline: 3px solid var(--cs-focus-ring) !important;
            outline-offset: 2px;
            box-shadow: none !important;
        }
        [data-testid="stButton"] button[kind="primary"],
        [data-testid="stFormSubmitButton"] button[kind="primary"],
        [data-testid="stDownloadButton"] button[kind="primary"] {
            background: var(--cs-primary) !important;
            border-color: var(--cs-primary) !important;
            color: var(--cs-on-primary) !important;
        }
        [data-testid="stButton"] button[kind="primary"]:hover,
        [data-testid="stFormSubmitButton"] button[kind="primary"]:hover,
        [data-testid="stDownloadButton"] button[kind="primary"]:hover {
            background: color-mix(in srgb, var(--cs-primary) 88%, #000000) !important;
            border-color: color-mix(in srgb, var(--cs-primary) 88%, #000000) !important;
            color: var(--cs-on-primary) !important;
        }
        input,
        textarea,
        [data-baseweb="select"] > div,
        [data-baseweb="textarea"] textarea,
        [data-baseweb="input"] > div {
            background: var(--cs-surface) !important;
            border-color: var(--cs-border) !important;
            color: var(--cs-text) !important;
            border-radius: var(--cs-radius-sm) !important;
            font-family: var(--cs-font-sans);
        }
        [data-baseweb="select"] *,
        [data-baseweb="input"] *,
        [data-baseweb="textarea"] * {
            color: var(--cs-text) !important;
        }
        input::placeholder,
        textarea::placeholder {
            color: var(--cs-text-subtle) !important;
        }
        [data-testid="stCheckbox"] label,
        [data-testid="stRadio"] label,
        [data-testid="stToggle"] label {
            color: var(--cs-text) !important;
        }
        [data-testid="stCheckbox"] span,
        [data-testid="stRadio"] span,
        [data-testid="stToggle"] span {
            color: inherit !important;
        }
        [data-testid="stFileUploader"] section {
            background: var(--cs-surface) !important;
            border: 1px solid var(--cs-border) !important;
            border-radius: var(--cs-radius-md) !important;
            color: var(--cs-text) !important;
        }
        [data-testid="stFileUploader"] section *,
        [data-testid="stFileUploader"] [data-testid="stMarkdownContainer"] {
            color: var(--cs-text) !important;
        }
        [data-testid="stFileUploaderDropzone"] {
            background: var(--cs-surface-muted) !important;
            border-color: var(--cs-border) !important;
            color: var(--cs-text) !important;
        }
        [data-testid="stSidebar"] [data-testid="stExpander"] h1,
        [data-testid="stSidebar"] [data-testid="stExpander"] h2,
        [data-testid="stSidebar"] [data-testid="stExpander"] h3,
        [data-testid="stSidebar"] [data-testid="stExpander"] h4,
        [data-testid="stSidebar"] [data-testid="stExpander"] h5,
        [data-testid="stSidebar"] [data-testid="stExpander"] h6,
        [data-testid="stSidebar"] [data-testid="stExpander"] p,
        [data-testid="stSidebar"] [data-testid="stExpander"] li,
        [data-testid="stSidebar"] [data-testid="stExpander"] label,
        [data-testid="stSidebar"] [data-testid="stExpander"] span,
        [data-testid="stSidebar"] [data-testid="stExpander"] div,
        [data-testid="stSidebar"] [data-testid="stExpander"] svg,
        [data-testid="stSidebar"] [data-testid="stExpander"] [data-testid="stMarkdownContainer"],
        [data-testid="stSidebar"] [data-testid="stExpander"] [data-testid="stWidgetLabel"],
        [data-testid="stSidebar"] [data-testid="stExpander"] [data-testid="stRadio"] label,
        [data-testid="stSidebar"] [data-testid="stExpander"] [data-testid="stCheckbox"] label,
        [data-testid="stSidebar"] [data-testid="stExpander"] [data-testid="stToggle"] label {
            color: var(--cs-sidebar-surface-text) !important;
        }
        [data-testid="stSidebar"] [data-testid="stExpander"] [data-testid="stCaptionContainer"],
        [data-testid="stSidebar"] [data-testid="stExpander"] small,
        [data-testid="stSidebar"] [data-testid="stExpander"] .caption {
            color: var(--cs-sidebar-surface-text-muted) !important;
        }
        [data-testid="stSidebar"] [data-testid="stExpander"] input,
        [data-testid="stSidebar"] [data-testid="stExpander"] textarea,
        [data-testid="stSidebar"] [data-testid="stExpander"] [data-baseweb="select"] > div,
        [data-testid="stSidebar"] [data-testid="stExpander"] [data-baseweb="textarea"] textarea,
        [data-testid="stSidebar"] [data-testid="stExpander"] [data-baseweb="input"] > div,
        [data-testid="stSidebar"] [data-testid="stVerticalBlockBorderWrapper"] input,
        [data-testid="stSidebar"] [data-testid="stVerticalBlockBorderWrapper"] textarea,
        [data-testid="stSidebar"] [data-testid="stVerticalBlockBorderWrapper"] [data-baseweb="select"] > div,
        [data-testid="stSidebar"] [data-testid="stVerticalBlockBorderWrapper"] [data-baseweb="textarea"] textarea,
        [data-testid="stSidebar"] [data-testid="stVerticalBlockBorderWrapper"] [data-baseweb="input"] > div {
            background: var(--cs-sidebar-surface-muted) !important;
            border-color: var(--cs-sidebar-border) !important;
            color: var(--cs-sidebar-surface-text) !important;
        }
        [data-testid="stSidebar"] [data-testid="stExpander"] [data-baseweb="select"] *,
        [data-testid="stSidebar"] [data-testid="stExpander"] [data-baseweb="input"] *,
        [data-testid="stSidebar"] [data-testid="stExpander"] [data-baseweb="textarea"] *,
        [data-testid="stSidebar"] [data-testid="stVerticalBlockBorderWrapper"] [data-baseweb="select"] *,
        [data-testid="stSidebar"] [data-testid="stVerticalBlockBorderWrapper"] [data-baseweb="input"] *,
        [data-testid="stSidebar"] [data-testid="stVerticalBlockBorderWrapper"] [data-baseweb="textarea"] * {
            color: var(--cs-sidebar-surface-text) !important;
            fill: currentColor !important;
        }
        [data-testid="stSidebar"] [data-testid="stExpander"] input::placeholder,
        [data-testid="stSidebar"] [data-testid="stExpander"] textarea::placeholder,
        [data-testid="stSidebar"] [data-testid="stVerticalBlockBorderWrapper"] input::placeholder,
        [data-testid="stSidebar"] [data-testid="stVerticalBlockBorderWrapper"] textarea::placeholder {
            color: var(--cs-sidebar-surface-text-muted) !important;
        }
        [data-testid="stExpander"] {
            background: var(--cs-surface) !important;
            border: 1px solid var(--cs-border) !important;
            border-radius: var(--cs-radius-md) !important;
            box-shadow: var(--cs-shadow-sm);
        }
        [data-testid="stExpander"] summary,
        [data-testid="stExpander"] summary p {
            color: var(--cs-text) !important;
            font-weight: 650;
        }
        [data-testid="stAlert"] {
            border-radius: var(--cs-radius-md);
            border-color: var(--cs-border);
            background: var(--cs-surface-muted) !important;
            color: var(--cs-text);
        }
        [data-testid="stAlert"] [data-testid="stMarkdownContainer"],
        [data-testid="stAlert"] [data-testid="stMarkdownContainer"] *,
        [data-testid="stAlert"] div,
        [data-testid="stAlert"] span,
        [data-testid="stAlert"] li,
        [data-testid="stAlert"] p {
            color: var(--cs-text) !important;
        }
        [data-testid="stAlert"] svg {
            fill: currentColor !important;
        }
        [data-testid="stTabs"] button {
            color: var(--cs-text-muted) !important;
            font-family: var(--cs-font-sans);
        }
        [data-testid="stTabs"] button[aria-selected="true"] {
            color: var(--cs-text) !important;
            font-weight: 700;
        }
        [data-testid="stTabs"] button[aria-selected="true"] p {
            color: var(--cs-text) !important;
        }
        [data-testid="stTabs"] button p {
            color: inherit !important;
        }
        [data-testid="stProgress"] > div > div {
            background: var(--cs-surface-muted) !important;
        }
        [data-testid="stProgress"] [role="progressbar"] > div {
            background: var(--cs-primary) !important;
        }
        [data-theme="dark"] [data-testid="stButton"] button[kind="primary"],
        [data-theme="dark"] [data-testid="stFormSubmitButton"] button[kind="primary"],
        [data-theme="dark"] [data-testid="stDownloadButton"] button[kind="primary"] {
            background: var(--cs-primary) !important;
            border-color: var(--cs-primary) !important;
            color: var(--cs-on-primary) !important;
        }
        [data-theme="dark"] [data-testid="stButton"] button[kind="primary"]:hover,
        [data-theme="dark"] [data-testid="stFormSubmitButton"] button[kind="primary"]:hover,
        [data-theme="dark"] [data-testid="stDownloadButton"] button[kind="primary"]:hover {
            background: #93C5FD !important;
            border-color: #93C5FD !important;
            color: var(--cs-on-primary) !important;
        }
        [data-theme="dark"] input,
        [data-theme="dark"] textarea,
        [data-theme="dark"] [data-baseweb="select"] > div,
        [data-theme="dark"] [data-baseweb="textarea"] textarea {
            background: var(--cs-surface) !important;
            border-color: var(--cs-border) !important;
            color: var(--cs-text) !important;
        }
        [data-theme="dark"] input::placeholder,
        [data-theme="dark"] textarea::placeholder {
            color: var(--cs-text-subtle) !important;
        }
        [data-theme="dark"] [data-testid="stDataFrame"] tbody tr,
        [data-theme="dark"] [data-testid="stTable"] tbody tr {
            background: var(--cs-surface-muted) !important;
        }
        [data-testid="stSidebar"] input,
        [data-testid="stSidebar"] textarea,
        [data-testid="stSidebar"] [data-baseweb="select"] > div,
        [data-testid="stSidebar"] [data-baseweb="textarea"] textarea,
        [data-testid="stSidebar"] [data-baseweb="input"] > div {
            background: var(--cs-sidebar-surface-muted) !important;
            border-color: var(--cs-sidebar-border) !important;
            color: var(--cs-sidebar-surface-text) !important;
        }
        [data-testid="stSidebar"] [data-baseweb="select"] *,
        [data-testid="stSidebar"] [data-baseweb="input"] *,
        [data-testid="stSidebar"] [data-baseweb="textarea"] * {
            color: var(--cs-sidebar-surface-text) !important;
            fill: currentColor !important;
        }
        [data-testid="stSidebar"] input::placeholder,
        [data-testid="stSidebar"] textarea::placeholder {
            color: var(--cs-sidebar-surface-text-muted) !important;
        }
        [data-testid="stSidebar"] [data-testid="stButton"] button,
        [data-testid="stSidebar"] [data-testid="stFormSubmitButton"] button,
        [data-testid="stSidebar"] [data-testid="stDownloadButton"] button {
            background: var(--cs-sidebar-surface) !important;
            border-color: var(--cs-sidebar-border) !important;
            color: var(--cs-sidebar-surface-text) !important;
            box-shadow: none;
        }
        [data-testid="stDataFrame"],
        [data-testid="stTable"] {
            color: var(--cs-text) !important;
        }
        [data-testid="stDataFrame"] div,
        [data-testid="stTable"] table,
        [data-testid="stTable"] th,
        [data-testid="stTable"] td {
            color: var(--cs-text) !important;
        }
        [data-testid="stTable"] table {
            background: var(--cs-surface) !important;
            border-color: var(--cs-border) !important;
        }
        [data-testid="stTable"] th,
        [data-testid="stDataFrame"] thead tr {
            background: var(--cs-surface-muted) !important;
            color: var(--cs-text-muted) !important;
        }
        [data-testid="stTable"] td,
        [data-testid="stTable"] th {
            border-color: var(--cs-border-soft) !important;
        }
        [data-testid="stTable"] tbody tr {
            background: var(--cs-surface) !important;
        }
        [data-testid="stVerticalBlockBorderWrapper"] {
            background: var(--cs-surface) !important;
            border-color: var(--cs-border) !important;
            border-radius: var(--cs-radius-md) !important;
            box-shadow: var(--cs-shadow-sm);
            color: var(--cs-text);
        }
        [data-testid="stMetric"] {
            background: var(--cs-surface);
            border: 1px solid var(--cs-border);
            border-radius: var(--cs-radius-sm);
            padding: 0.8rem 0.85rem;
            min-height: 100%;
            box-shadow: var(--cs-shadow-sm);
            color: var(--cs-text);
        }
        [data-testid="stMetric"] label,
        [data-testid="stMetric"] [data-testid="stMetricLabel"],
        [data-testid="stMetric"] [data-testid="stMetricDelta"] {
            color: var(--cs-text-muted) !important;
        }
        [data-testid="stMetric"] [data-testid="stMetricValue"] {
            color: var(--cs-text) !important;
        }
        [data-testid="stSidebar"] [data-testid="stMetric"] {
            background: var(--cs-sidebar-surface);
            border: 1px solid var(--cs-sidebar-border);
            color: var(--cs-sidebar-surface-text);
            box-shadow: none;
        }
        [data-testid="stSidebar"] [data-testid="stMetric"] label,
        [data-testid="stSidebar"] [data-testid="stMetric"] [data-testid="stMetricLabel"],
        [data-testid="stSidebar"] [data-testid="stMetric"] [data-testid="stMetricDelta"] {
            color: var(--cs-sidebar-surface-text-muted) !important;
        }
        [data-testid="stSidebar"] [data-testid="stMetric"] [data-testid="stMetricValue"] {
            color: var(--cs-sidebar-surface-text) !important;
        }
        [data-testid="stSidebar"] [data-testid="stMetric"] [data-testid="stMetricDelta"] svg {
            fill: currentColor;
        }
        [data-testid="stSidebar"] [data-testid="stAlert"] {
            background: var(--cs-sidebar-surface) !important;
            border-color: var(--cs-sidebar-border) !important;
            color: var(--cs-sidebar-surface-text) !important;
        }
        [data-testid="stSidebar"] [data-testid="stAlert"] [data-testid="stMarkdownContainer"],
        [data-testid="stSidebar"] [data-testid="stAlert"] p,
        [data-testid="stSidebar"] [data-testid="stAlert"] li,
        [data-testid="stSidebar"] [data-testid="stAlert"] span,
        [data-testid="stSidebar"] [data-testid="stAlert"] div,
        [data-testid="stSidebar"] [data-testid="stAlert"] svg {
            color: var(--cs-sidebar-surface-text) !important;
            fill: currentColor !important;
        }
        [data-testid="stSidebar"] [data-testid="stVerticalBlockBorderWrapper"] {
            background: var(--cs-sidebar-surface) !important;
            border-color: var(--cs-sidebar-border) !important;
            color: var(--cs-sidebar-surface-text) !important;
            box-shadow: none;
        }
        [data-testid="stSidebar"] [data-testid="stVerticalBlockBorderWrapper"] p,
        [data-testid="stSidebar"] [data-testid="stVerticalBlockBorderWrapper"] label,
        [data-testid="stSidebar"] [data-testid="stVerticalBlockBorderWrapper"] span,
        [data-testid="stSidebar"] [data-testid="stVerticalBlockBorderWrapper"] div,
        [data-testid="stSidebar"] [data-testid="stVerticalBlockBorderWrapper"] svg,
        [data-testid="stSidebar"] [data-testid="stVerticalBlockBorderWrapper"] li,
        [data-testid="stSidebar"] [data-testid="stVerticalBlockBorderWrapper"] [data-testid="stMarkdownContainer"],
        [data-testid="stSidebar"] [data-testid="stVerticalBlockBorderWrapper"] [data-testid="stWidgetLabel"],
        [data-testid="stSidebar"] [data-testid="stVerticalBlockBorderWrapper"] [data-testid="stRadio"] label,
        [data-testid="stSidebar"] [data-testid="stVerticalBlockBorderWrapper"] [data-testid="stCheckbox"] label,
        [data-testid="stSidebar"] [data-testid="stVerticalBlockBorderWrapper"] [data-testid="stToggle"] label {
            color: var(--cs-sidebar-surface-text) !important;
            fill: currentColor !important;
        }
        [data-testid="stSidebar"] [data-testid="stVerticalBlockBorderWrapper"] [data-testid="stCaptionContainer"],
        [data-testid="stSidebar"] [data-testid="stVerticalBlockBorderWrapper"] small {
            color: var(--cs-sidebar-surface-text-muted) !important;
        }
        [data-testid="stSidebar"] .cs-pill {
            background: var(--cs-sidebar-surface-muted);
            border-color: var(--cs-sidebar-border);
            color: var(--cs-sidebar-surface-text);
        }
        .cs-card,
        .cs-step-header,
        .cs-output-header,
        .cs-next-best-action,
        .cs-critical-gaps,
        .cs-next-action,
        .cs-critical,
        .cs-boolean-card,
        .cs-code-card,
        .cs-salary-card {
            background: var(--cs-surface);
            border: 1px solid var(--cs-border);
            border-radius: var(--cs-radius-md);
            color: var(--cs-text);
            box-shadow: var(--cs-shadow-sm);
        }
        .cs-card,
        .cs-next-best-action,
        .cs-critical-gaps,
        .cs-next-action,
        .cs-critical,
        .cs-boolean-card,
        .cs-code-card,
        .cs-salary-card {
            padding: 1rem 1.1rem;
        }
        .cs-step-header,
        .cs-output-header {
            padding: 0.95rem 1rem;
            margin-bottom: 0.9rem;
            background: linear-gradient(
                180deg,
                var(--cs-surface),
                color-mix(in srgb, var(--cs-surface) 88%, var(--cs-bg))
            );
        }
        .cs-step-header {
            border-left: 2px solid var(--cs-success);
        }
        .cs-output-header,
        .cs-next-action {
            border-left: 4px solid var(--cs-primary);
        }
        .cs-critical {
            border-left: 4px solid var(--cs-danger);
        }
        .cs-pill {
            display: inline-flex;
            align-items: center;
            gap: 0.35rem;
            padding: 0.22rem 0.58rem;
            border-radius: 999px;
            font-size: 0.78rem;
            font-weight: 650;
            line-height: 1.2;
            border: 1px solid var(--cs-border);
            background: var(--cs-surface-muted);
            color: var(--cs-text-muted);
            max-width: 100%;
            overflow-wrap: anywhere;
        }
        .cs-pill--primary,
        .cs-pill-primary {
            border-color: color-mix(in srgb, var(--cs-primary) 55%, var(--cs-border));
            background: color-mix(in srgb, var(--cs-primary) 15%, var(--cs-surface-muted));
            color: var(--cs-text);
        }
        .cs-pill--warning,
        .cs-pill-warning {
            border-color: color-mix(in srgb, var(--cs-warning) 58%, var(--cs-border));
            background: var(--cs-warning-soft);
            color: var(--cs-text);
        }
        .cs-pill--success,
        .cs-pill-success {
            border-color: color-mix(in srgb, var(--cs-success) 58%, var(--cs-border));
            background: var(--cs-success-soft);
            color: var(--cs-text);
        }
        .cs-pill--neutral {
            border-color: var(--cs-border);
            background: var(--cs-surface-muted);
            color: var(--cs-text-muted);
        }
        .cs-process-progress {
            display: flex;
            justify-content: flex-start;
            margin: 0.1rem auto 0.85rem;
            width: 100%;
            overflow-x: auto;
            padding: 0.12rem 0 0.32rem;
            scrollbar-gutter: stable;
        }
        .cs-process-progress-list {
            display: flex;
            align-items: stretch;
            justify-content: flex-start;
            flex-wrap: nowrap;
            gap: 0.42rem;
            margin: 0;
            padding: 0;
            list-style: none;
            min-width: 100%;
            width: max-content;
        }
        .cs-process-progress-item {
            flex: 1 0 8.35rem;
            min-width: 8.35rem;
            max-width: 10.5rem;
        }
        .cs-process-progress-link {
            display: grid;
            grid-template-columns: auto minmax(0, 1fr);
            align-items: flex-start;
            gap: 0.42rem;
            min-height: 3.35rem;
            height: 100%;
            padding: 0.45rem 0.52rem;
            border: 1px solid var(--cs-border);
            border-radius: 7px;
            background: color-mix(in srgb, var(--cs-surface-raised) 96%, var(--cs-bg) 4%);
            color: var(--cs-text);
            text-decoration: none;
            font-size: 0.74rem;
            line-height: 1.16;
            box-shadow: var(--cs-shadow-sm);
            transition:
                border-color 120ms ease,
                background-color 120ms ease,
                box-shadow 120ms ease,
                transform 120ms ease;
        }
        .cs-process-progress-link:hover {
            border-color: var(--cs-primary);
            background: color-mix(in srgb, var(--cs-surface-raised) 90%, var(--cs-primary) 10%);
            color: var(--cs-text);
            text-decoration: none;
            transform: translateY(-1px);
        }
        .cs-process-progress-link:focus-visible {
            outline: 3px solid var(--cs-focus-ring);
            outline-offset: 2px;
        }
        .cs-process-progress-marker {
            display: grid;
            place-items: center;
            width: 1.38rem;
            height: 1.38rem;
            border-radius: 999px;
            border: 1px solid var(--cs-border);
            background: var(--cs-surface);
            color: var(--cs-text-muted);
            font-size: 0.62rem;
            font-weight: 800;
            line-height: 1;
        }
        .cs-process-progress-item[data-status="complete"] .cs-process-progress-link {
            border-color: color-mix(in srgb, var(--cs-success) 42%, var(--cs-border));
            background: color-mix(in srgb, var(--cs-success-soft) 34%, var(--cs-surface));
        }
        .cs-process-progress-item[data-status="complete"] .cs-process-progress-marker {
            border-color: var(--cs-success);
            background: var(--cs-success-soft);
            color: var(--cs-success);
        }
        .cs-process-progress-item[data-status="partial"] .cs-process-progress-link {
            border-color: color-mix(in srgb, var(--cs-warning) 45%, var(--cs-border));
            background: color-mix(in srgb, var(--cs-warning-soft) 30%, var(--cs-surface));
        }
        .cs-process-progress-item[data-status="partial"] .cs-process-progress-marker {
            border-color: var(--cs-warning);
            background: var(--cs-warning-soft);
            color: var(--cs-warning);
        }
        .cs-process-progress-item[data-current="true"] .cs-process-progress-link {
            border-color: var(--cs-primary);
            background: color-mix(in srgb, var(--cs-primary-soft) 72%, var(--cs-surface-raised));
            color: var(--cs-text);
            box-shadow: 0 0 0 2px var(--cs-focus-ring);
        }
        .cs-process-progress-item[data-current="true"] .cs-process-progress-marker {
            border-color: var(--cs-primary);
            background: var(--cs-primary);
            color: var(--cs-on-primary);
        }
        .cs-process-progress-body {
            display: grid;
            gap: 0.2rem;
            min-width: 0;
        }
        .cs-process-progress-label-row {
            display: flex;
            align-items: center;
            gap: 0.3rem;
            min-width: 0;
        }
        .cs-process-progress-label {
            color: var(--cs-text);
            font-weight: 750;
            overflow-wrap: break-word;
            hyphens: auto;
        }
        .cs-process-progress-icon {
            flex: 0 0 auto;
            line-height: 1;
        }
        .cs-process-progress-meta {
            display: flex;
            align-items: center;
            flex-wrap: wrap;
            gap: 0.28rem 0.45rem;
            color: var(--cs-text-muted);
            font-size: 0.68rem;
            font-weight: 600;
        }
        .cs-process-progress-status {
            color: var(--cs-text-muted);
        }
        .cs-process-progress-item[data-status="complete"] .cs-process-progress-status {
            color: var(--cs-success);
        }
        .cs-process-progress-item[data-status="partial"] .cs-process-progress-status {
            color: var(--cs-warning);
        }
        .cs-process-progress-count {
            color: var(--cs-text-subtle);
            font-weight: 600;
            overflow-wrap: anywhere;
        }
        [data-testid="stSidebar"] .cs-process-progress-link {
            background: var(--cs-sidebar-surface);
            border-color: var(--cs-sidebar-border);
            color: var(--cs-sidebar-surface-text);
            box-shadow: none;
        }
        [data-testid="stSidebar"] .cs-process-progress-marker {
            background: var(--cs-sidebar-surface);
            border-color: var(--cs-sidebar-border);
            color: var(--cs-sidebar-surface-text-muted);
        }
        [data-testid="stSidebar"] .cs-process-progress-item[data-current="true"] .cs-process-progress-link {
            background: var(--cs-sidebar-surface-muted);
            border-color: var(--cs-success);
            color: var(--cs-sidebar-surface-text);
        }
        [data-testid="stSidebar"] .cs-process-progress-item[data-status="complete"] .cs-process-progress-link,
        [data-testid="stSidebar"] .cs-process-progress-item[data-status="partial"] .cs-process-progress-link {
            background: var(--cs-sidebar-surface);
            border-color: var(--cs-sidebar-border);
        }
        [data-testid="stSidebar"] .cs-process-progress-label {
            color: var(--cs-sidebar-surface-text);
        }
        [data-testid="stSidebar"] .cs-process-progress-meta,
        [data-testid="stSidebar"] .cs-process-progress-count {
            color: var(--cs-sidebar-surface-text-muted);
        }
        .cs-step-title, .cs-output-title {
            margin: 0;
            color: var(--cs-text);
            font-size: clamp(1.28rem, 1.8vw, 1.65rem);
            line-height: 1.22;
        }
        .cs-step-subtitle, .cs-output-context {
            margin: 0.45rem 0 0;
            color: var(--cs-text-muted);
            line-height: 1.55;
            max-width: 76rem;
        }
        .cs-meta-list {
            margin: 0.7rem 0 0;
            padding: 0;
            list-style: none;
            display: flex;
            flex-wrap: wrap;
            gap: 0.4rem;
        }
        .cs-meta-item {
            display: inline-grid;
            grid-template-columns: auto auto minmax(0, auto);
            column-gap: 0.4rem;
            row-gap: 0.05rem;
            align-items: center;
            max-width: min(100%, 34rem);
            padding: 0.28rem 0.55rem;
            border: 1px solid var(--cs-border-soft);
            border-radius: 999px;
            background: var(--cs-surface-muted);
            font-size: 0.8rem;
        }
        .cs-meta-icon { opacity: 0.75; }
        .cs-meta-label {
            color: var(--cs-text-subtle);
            font-size: 0.72rem;
            font-weight: 700;
            text-transform: uppercase;
        }
        .cs-meta-value {
            color: var(--cs-text);
            font-weight: 650;
            overflow-wrap: anywhere;
        }
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
            max-width: 44rem;
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
        .cs-step-section-heading {
            margin: 1.1rem 0 0.45rem;
            color: var(--cs-text);
            font-size: 1rem;
            font-weight: 750;
            line-height: 1.3;
        }
        .cs-question-group-title,
        .cs-review-card-title {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 0.75rem;
            flex-wrap: wrap;
            margin-bottom: 0.45rem;
        }
        .cs-question-group-title strong,
        .cs-review-card-title strong {
            color: var(--cs-text);
            font-size: 1rem;
            line-height: 1.3;
        }
        .cs-question-group-meta,
        .cs-review-card-meta {
            display: inline-flex;
            align-items: center;
            gap: 0.35rem;
            color: var(--cs-text-muted);
            background: var(--cs-surface-muted);
            border: 1px solid var(--cs-border-soft);
            border-radius: 999px;
            padding: 0.18rem 0.5rem;
            font-size: 0.78rem;
            font-weight: 650;
        }
        .cs-review-essential-list {
            margin: 0.35rem 0 0;
            padding-left: 1.1rem;
        }
        .cs-review-essential-list li {
            margin-bottom: 0.25rem;
            color: var(--cs-text-muted);
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
                flex-basis: min(72vw, 15rem);
                min-width: min(72vw, 15rem);
                max-width: min(72vw, 15rem);
            }
            .cs-meta-list {
                display: grid;
                grid-template-columns: minmax(0, 1fr);
            }
            .cs-meta-item {
                border-radius: 8px;
                grid-template-columns: auto minmax(0, auto) minmax(0, 1fr);
                align-items: start;
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
                </span>
        """.format(
            marker_title=escape(marker_title),
            marker_label=escape(marker_label),
            icon_html=icon_html,
            label=escape(label),
            status_label=escape(status_label),
            count_html=count_html,
        )
        if href:
            tile_html = (
                '<a class="cs-process-progress-link" href="{href}" title="{title}"{aria_current}>'
                "{tile_body}</a>"
            ).format(
                href=escape(href, quote=True),
                title=escape(title, quote=True),
                aria_current=aria_current,
                tile_body=tile_body,
            )
        else:
            tile_html = (
                '<div class="cs-process-progress-link" title="{title}"{aria_current}>'
                "{tile_body}</div>"
            ).format(
                title=escape(title, quote=True),
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
) -> str:
    outcome_html = (
        f'<span class="cs-pill cs-pill--primary">{escape(outcome)}</span>' if outcome else ""
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
        </section>
        """


def render_output_header(
    title: str,
    context: str,
    meta_items: Sequence[tuple[str, str, str]] = (),
) -> None:
    context_html = (
        f'<p class="cs-output-context">{escape(context)}</p>' if context else ""
    )
    _render_html_block(
        f"""
        <section class="cs-output-header">
            <div class="cs-output-topline">
                <h3 class="cs-output-title">{escape(title)}</h3>
            </div>
            {context_html}
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
