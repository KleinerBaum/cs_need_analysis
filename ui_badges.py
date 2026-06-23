# ui_badges.py
"""Badge-style UI helpers."""

from __future__ import annotations

from collections.abc import Sequence
from contextlib import nullcontext
from dataclasses import dataclass
from html import escape
from typing import Any, Mapping

import streamlit as st

from constants import FactResolutionStatus, FactSourceType
from job_extract_evidence import (
    canonical_source_label,
    format_field_evidence_snippet,
    format_provenance_label,
)
from safe_html import render_static_html

ESCO_EXPLAINABILITY_LABELS: tuple[str, ...] = (
    "exact label match",
    "synonym/hidden-term match",
    "derived from occupation relation",
    "manually selected by user",
)
ESCO_CONFIDENCE_BUCKETS: tuple[str, ...] = ("high", "medium", "low")


@dataclass(frozen=True)
class ProvenanceBadge:
    label: str
    tone: str = "neutral"


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


def _coerce_confidence(value: Any) -> float | None:
    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return None


def _resolved_evidence_value(
    evidence: Mapping[str, Any],
    key: str,
    fallback: Any = None,
) -> Any:
    if key in evidence:
        return evidence.get(key)
    return fallback


def trust_source_label(source_type: str = "", source_label: str = "") -> str:
    """Return the canonical short source label for trust UI."""

    return canonical_source_label(source_type=source_type, source_label=source_label)


def trust_status_label(
    evidence: Any = None,
    *,
    source_type: str = "",
    source_label: str = "",
    resolution_status: str = "",
    confirmed: bool | None = None,
    confidence: Any = None,
    needs_confirmation: bool = False,
    confidence_threshold: float | None = None,
) -> str:
    """Return compact trust text without exposing raw evidence."""

    return format_provenance_label(
        evidence,
        source_type=source_type,
        source_label=source_label,
        resolution_status=resolution_status,
        confirmed=confirmed,
        confidence=confidence,
        needs_confirmation=needs_confirmation,
        confidence_threshold=confidence_threshold,
    )


def _provenance_badge_tone(
    *,
    label: str,
    evidence: Mapping[str, Any],
    source_type: str,
    resolution_status: str,
    confirmed: bool | None,
    needs_confirmation: bool,
    confidence: Any,
    confidence_threshold: float | None,
) -> str:
    normalized_label = label.casefold()
    resolved_status = str(
        _resolved_evidence_value(evidence, "resolution_status", resolution_status) or ""
    ).strip()
    resolved_source_type = str(
        _resolved_evidence_value(evidence, "source_type", source_type) or ""
    ).strip()
    resolved_confirmed = (
        bool(evidence.get("confirmed")) if "confirmed" in evidence else confirmed
    )
    resolved_needs_confirmation = bool(
        _resolved_evidence_value(evidence, "needs_confirmation", needs_confirmation)
    )
    resolved_confidence = _coerce_confidence(
        _resolved_evidence_value(evidence, "confidence", confidence)
    )
    threshold = _coerce_confidence(confidence_threshold)
    is_low_confidence = (
        threshold is not None
        and resolved_confidence is not None
        and resolved_confidence < threshold
    )
    if (
        resolved_status
        in {FactResolutionStatus.CONFLICTED.value, FactResolutionStatus.MISSING.value}
        or resolved_needs_confirmation
        or is_low_confidence
        or any(
            token in normalized_label
            for token in ("konflikt", "fehlt", "ergänzen", "offen", "prüfen")
        )
    ):
        return "warning"
    if (
        resolved_source_type == FactSourceType.MANUAL.value
        or resolved_confirmed is True
        or resolved_status == FactResolutionStatus.CONFIRMED.value
        or any(token in normalized_label for token in ("bestätigt", "eingabe"))
    ):
        return "success"
    if resolved_source_type in {
        FactSourceType.JOBSPEC.value,
        FactSourceType.HOMEPAGE.value,
        FactSourceType.ESCO.value,
        FactSourceType.LLM.value,
    }:
        return "primary"
    return "neutral"


def build_provenance_badge(
    evidence: Any = None,
    *,
    label: str = "",
    source_type: str = "",
    source_label: str = "",
    resolution_status: str = "",
    confirmed: bool | None = None,
    confidence: Any = None,
    needs_confirmation: bool = False,
    confidence_threshold: float | None = None,
) -> ProvenanceBadge:
    evidence_map = evidence if isinstance(evidence, Mapping) else {}
    resolved_label = str(label or "").strip() or format_provenance_label(
        evidence_map,
        source_type=source_type,
        source_label=source_label,
        resolution_status=resolution_status,
        confirmed=confirmed,
        confidence=confidence,
        needs_confirmation=needs_confirmation,
        confidence_threshold=confidence_threshold,
    )
    if not resolved_label:
        return ProvenanceBadge(label="", tone="neutral")
    return ProvenanceBadge(
        label=resolved_label,
        tone=_provenance_badge_tone(
            label=resolved_label,
            evidence=evidence_map,
            source_type=source_type,
            resolution_status=resolution_status,
            confirmed=confirmed,
            needs_confirmation=needs_confirmation,
            confidence=confidence,
            confidence_threshold=confidence_threshold,
        ),
    )


def render_provenance_badge(
    evidence: Any = None,
    *,
    label: str = "",
    source_type: str = "",
    source_label: str = "",
    resolution_status: str = "",
    confirmed: bool | None = None,
    confidence: Any = None,
    needs_confirmation: bool = False,
    confidence_threshold: float | None = None,
    streamlit_module: Any | None = None,
) -> None:
    badge = build_provenance_badge(
        evidence,
        label=label,
        source_type=source_type,
        source_label=source_label,
        resolution_status=resolution_status,
        confirmed=confirmed,
        confidence=confidence,
        needs_confirmation=needs_confirmation,
        confidence_threshold=confidence_threshold,
    )
    if not badge.label:
        return
    tone_class = {
        "success": "cs-pill--success",
        "primary": "cs-pill--primary",
        "warning": "cs-pill--warning",
        "neutral": "cs-pill--neutral",
    }.get(badge.tone, "cs-pill--neutral")
    render_static_html(
        f'<span class="cs-pill {tone_class}">{escape(badge.label)}</span>',
        streamlit_module=streamlit_module or st,
    )


def render_source_evidence_popover(
    evidence: Any = None,
    *,
    source_type: str = "",
    source_label: str = "",
    evidence_snippet: str = "",
    trigger_label: str = "Quelle & Beleg",
    confidence_threshold: float | None = None,
    streamlit_module: Any | None = None,
) -> None:
    """Render a compact, consistent source/evidence disclosure."""

    st_module = streamlit_module or st
    evidence_map = evidence if isinstance(evidence, Mapping) else {}
    resolved_source_type = str(evidence_map.get("source_type") or source_type).strip()
    raw_source_label = str(evidence_map.get("source_label") or source_label).strip()
    display_source = trust_source_label(resolved_source_type, raw_source_label)
    if not display_source and raw_source_label:
        display_source = raw_source_label

    snippet_source: Mapping[str, Any]
    if evidence_map:
        snippet_source = evidence_map
    else:
        snippet_source = {"evidence_snippet": evidence_snippet}
    snippet = format_field_evidence_snippet(snippet_source)

    badge = build_provenance_badge(
        evidence_map,
        source_type=resolved_source_type,
        source_label=raw_source_label,
        confidence_threshold=confidence_threshold,
    )
    if not any((display_source, snippet, badge.label)):
        return

    popover = getattr(st_module, "popover", None)
    expander = getattr(st_module, "expander", None)
    if callable(popover):
        context = popover(trigger_label)
    elif callable(expander):
        context = expander(trigger_label, expanded=False)
    else:
        context = nullcontext()

    with context:
        if badge.label:
            render_provenance_badge(
                evidence_map,
                label=badge.label,
                source_type=resolved_source_type,
                source_label=raw_source_label,
                confidence_threshold=confidence_threshold,
                streamlit_module=st_module,
            )
        if display_source:
            st_module.caption(f"Quelle: {display_source}")
        if snippet:
            render_static_html(
                (
                    '<div class="cs-source-evidence-snippet">'
                    f"{escape(snippet)}"
                    "</div>"
                ),
                streamlit_module=st_module,
            )


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
