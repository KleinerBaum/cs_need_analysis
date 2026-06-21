# ui_badges.py
"""Badge-style UI helpers."""

from __future__ import annotations

from collections.abc import Sequence

import streamlit as st

from safe_html import render_static_html

ESCO_EXPLAINABILITY_LABELS: tuple[str, ...] = (
    "exact label match",
    "synonym/hidden-term match",
    "derived from occupation relation",
    "manually selected by user",
)
ESCO_CONFIDENCE_BUCKETS: tuple[str, ...] = ("high", "medium", "low")

def _normalize_esco_explainability_label(label: str) -> str:
    normalized = " ".join(str(label or "").strip().casefold().split())
    legacy_to_canonical = {
        "matched from jobspec title": "exact label match",
        "matched from synonyms/hidden terms": "synonym/hidden-term match",
        "manual override": "manually selected by user",
        "manual selection": "manually selected by user",
        "label_exact": "exact label match",
    }
    return legacy_to_canonical.get(normalized, normalized)


def _normalize_esco_confidence(confidence: str) -> str:
    normalized = str(confidence or "").strip().lower()
    return normalized if normalized in ESCO_CONFIDENCE_BUCKETS else "low"


def render_esco_explainability(
    *,
    labels: Sequence[str],
    confidence: str,
    reason: str | None = None,
    caption_prefix: str = "ESCO Explainability",
) -> None:
    normalized_labels: list[str] = []
    seen: set[str] = set()
    for label in labels:
        canonical = _normalize_esco_explainability_label(label)
        if canonical in ESCO_EXPLAINABILITY_LABELS and canonical not in seen:
            normalized_labels.append(canonical)
            seen.add(canonical)
    normalized_confidence = _normalize_esco_confidence(confidence)
    if not normalized_labels and not reason:
        return
    st.caption(f"Sicherheit: {normalized_confidence.title()}")
    if reason:
        st.caption(f"{caption_prefix}: {reason}")
    if normalized_labels:
        badges = [label.title() for label in normalized_labels]

        def _render_badges(entries: Sequence[str]) -> None:
            badge_html = " ".join(
                (
                    "<span style='display:inline-block;padding:0.15rem 0.45rem;"
                    "border-radius:0.6rem;border:1px solid #D9E2EC;font-size:0.78rem;'>"
                    f"{badge}</span>"
                )
                for badge in entries
            )
            if badge_html:
                render_static_html(badge_html, streamlit_module=st)

        with st.expander("Technische Details", expanded=False):
            _render_badges(badges)
