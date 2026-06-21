from __future__ import annotations

import html
from typing import Any

import streamlit as st


def escape_html_text(value: object | None, quote: bool = True) -> str:
    if value is None:
        return ""
    return html.escape(str(value), quote=quote)


def render_static_html(html_markup: str, *, streamlit_module: Any = st) -> None:
    """Render repo-owned HTML/CSS; escape every dynamic value before interpolation."""

    streamlit_module.markdown(str(html_markup), unsafe_allow_html=True)
