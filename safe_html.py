from __future__ import annotations

import html
from typing import Any

import streamlit as st


def escape_html_text(value: object | None, quote: bool = True) -> str:
    if value is None:
        return ""
    return html.escape(str(value), quote=quote)


def render_static_html(html_markup: str, *, streamlit_module: Any = st) -> None:
    """Render repo-owned HTML/CSS through Streamlit's audited unsafe boundary.

    Dynamic values must be escaped with ``escape_html_text`` before interpolation.
    """

    render_html = getattr(streamlit_module, "html", None)
    if callable(render_html):
        render_html(str(html_markup))
        return

    # Intentional Streamlit unsafe HTML fallback for older/runtime-limited Streamlit.
    streamlit_module.markdown(str(html_markup), unsafe_allow_html=True)
