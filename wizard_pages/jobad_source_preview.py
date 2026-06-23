"""Source text preview helpers for the Start intake flow."""

from __future__ import annotations

import html
import math
from typing import Any

import streamlit as st

from document_preview import (
    docx_preview_html,
    text_preview_html,
    uploaded_document_preview_html,
)
from safe_html import render_static_html


def preview_height_for_text(text: str) -> int:
    """Return a dynamic textarea height so the preview does not need scrolling."""
    chars_per_line = 95
    line_height_px = 28
    padding_px = 28
    total_lines = sum(
        max(1, math.ceil(len(line) / chars_per_line))
        for line in text.splitlines() or [""]
    )
    return (total_lines * line_height_px) + padding_px


def manual_input_height_for_text(text: str) -> int:
    """Return a compact default height for short text and grow moderately for longer text."""
    min_height_px = 180
    max_height_px = 300
    return max(min_height_px, min(preview_height_for_text(text), max_height_px))


def looks_like_noisy_source_line(text: str) -> bool:
    cleaned = text.strip()
    if not cleaned:
        return True
    lowered = cleaned.lower()
    noise_markers = (
        "<div",
        "</div",
        "class=",
        "cookie",
        "skip to main content",
        "click here to update your cookie settings",
        "mehr lesen",
        "speichern",
    )
    return any(marker in lowered for marker in noise_markers)


def clean_source_preview_lines(text: str, *, limit: int = 6) -> list[str]:
    lines: list[str] = []
    for raw_line in text.splitlines():
        line = " ".join(str(raw_line or "").strip().split())
        if looks_like_noisy_source_line(line):
            continue
        lines.append(line[:220])
        if len(lines) >= limit:
            break
    return lines


def render_uploaded_source_summary(
    text: str,
    *,
    streamlit_module: Any = st,
) -> None:
    char_count = len(text.strip())
    formatted_char_count = f"{char_count:,}".replace(",", ".")
    lines = clean_source_preview_lines(text)
    if not lines:
        streamlit_module.caption(
            f"Extrahierter Text ist bereit ({formatted_char_count} Zeichen). "
            "Die vollständige Quelle bleibt einklappbar."
        )
        return
    streamlit_module.caption(
        f"Extrahierter Text ist bereit ({formatted_char_count} Zeichen). "
        "Kompakte Vorschau:"
    )
    render_static_html(
        "<br>".join(f"• {html.escape(line)}" for line in lines),
        streamlit_module=streamlit_module,
    )


def render_uploaded_document_preview(
    upload: object | None,
    fallback_text: str,
    *,
    streamlit_module: Any = st,
) -> bool:
    preview_html = uploaded_document_preview_html(upload, fallback_text)
    if preview_html is None:
        return False
    render_static_html(preview_html, streamlit_module=streamlit_module)
    return True
