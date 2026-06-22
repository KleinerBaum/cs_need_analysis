# ui_source_pills.py
"""Source pill selection helpers."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import TypedDict

import streamlit as st

from constants import FactResolutionStatus, FactSourceType
from ui_badges import render_provenance_badge
from ui_inputs import inject_pills_grid_css

def render_multi_select_pills(
    label: str,
    *,
    options: Sequence[str],
    default: Sequence[str] | None = None,
    key: str,
) -> list[str]:
    normalized_options = [str(option).strip() for option in options if str(option).strip()]
    normalized_default = (
        [str(item).strip() for item in default if str(item).strip()]
        if default is not None
        else []
    )
    if hasattr(st, "pills"):
        inject_pills_grid_css()
        return (
            st.pills(
                label,
                options=normalized_options,
                default=normalized_default,
                selection_mode="multi",
                key=key,
            )
            or []
        )
    return st.multiselect(
        label, options=normalized_options, default=normalized_default, key=key
    )


class SourcePillColumn(TypedDict):
    title: str
    source_key: str
    options: Sequence[str]
    state_key: str


class SourcePillColumnFooter(TypedDict, total=False):
    footer: Callable[[], None]
    show_provenance: bool


class SourcePillColumnWithFooter(SourcePillColumn, SourcePillColumnFooter):
    pass


class SourcePillSelectionResult(TypedDict):
    selected_labels: list[str]
    selected_by_source: dict[str, list[str]]
    source_counts: dict[str, int]


def normalize_source_pill_label(value: str) -> str:
    return " ".join(str(value or "").strip().casefold().split())


def dedupe_source_pill_labels(values: Sequence[str]) -> list[str]:
    deduped: list[str] = []
    seen: set[str] = set()
    for value in values:
        label = str(value or "").strip()
        normalized = normalize_source_pill_label(label)
        if not normalized or normalized in seen:
            continue
        deduped.append(label)
        seen.add(normalized)
    return deduped


def _source_pill_provenance_caption(source_key: str) -> str:
    normalized = normalize_source_pill_label(source_key)
    if "jobspec" in normalized:
        return "Provenienz: Jobspec"
    if "esco" in normalized or "kontext" in normalized:
        return "Provenienz: ESCO"
    if normalized == "ai" or "ai" in normalized:
        return "Provenienz: AI-Vorschlag"
    if "manual" in normalized or "antwort" in normalized or "eingabe" in normalized:
        return "Provenienz: Eingabe"
    return ""


def _source_pill_provenance_source(source_key: str) -> FactSourceType | None:
    normalized = normalize_source_pill_label(source_key)
    if "jobspec" in normalized:
        return FactSourceType.JOBSPEC
    if "esco" in normalized or "kontext" in normalized:
        return FactSourceType.ESCO
    if normalized == "ai" or "ai" in normalized:
        return FactSourceType.LLM
    if "manual" in normalized or "antwort" in normalized or "eingabe" in normalized:
        return FactSourceType.MANUAL
    return None


def render_source_pill_selection(
    *,
    columns: Sequence[SourcePillColumnWithFooter],
    selected_labels: Sequence[str],
    selected_state_key: str,
    key_prefix: str,
    empty_caption: str = "Keine Vorschläge.",
    show_provenance: bool = True,
) -> SourcePillSelectionResult:
    """Render source columns as multi-select pills and persist canonical selection."""

    canonical_selected = dedupe_source_pill_labels(selected_labels)
    selected_normalized = {
        normalize_source_pill_label(label) for label in canonical_selected
    }
    selected_by_source: dict[str, list[str]] = {}
    source_counts: dict[str, int] = {}
    merged_selected: list[str] = []
    merged_seen: set[str] = set()

    rendered_columns = st.columns(len(columns), gap="large")
    for index, (column, source_column) in enumerate(zip(rendered_columns, columns)):
        title = str(source_column["title"]).strip()
        source_key = str(source_column["source_key"]).strip()
        state_key = str(source_column["state_key"]).strip()
        options = dedupe_source_pill_labels(source_column["options"])
        option_lookup = {normalize_source_pill_label(option): option for option in options}
        default = [
            option_lookup[normalized]
            for normalized in selected_normalized
            if normalized in option_lookup
        ]
        with column:
            st.markdown(f"#### {title}")
            column_show_provenance = bool(
                source_column.get("show_provenance", show_provenance)
            )
            provenance_caption = (
                _source_pill_provenance_caption(source_key)
                if column_show_provenance
                else ""
            )
            provenance_source = (
                _source_pill_provenance_source(source_key)
                if column_show_provenance
                else None
            )
            if provenance_source is not None:
                render_provenance_badge(
                    source_type=provenance_source.value,
                    resolution_status=(
                        FactResolutionStatus.CONFIRMED.value
                        if provenance_source == FactSourceType.MANUAL
                        else FactResolutionStatus.INFERRED.value
                    ),
                    confirmed=provenance_source == FactSourceType.MANUAL,
                    streamlit_module=st,
                )
            elif provenance_caption:
                st.caption(provenance_caption)
            if options:
                picked = render_multi_select_pills(
                    " ",
                    options=options,
                    default=default,
                    key=state_key,
                )
            else:
                st.session_state[state_key] = []
                st.caption(empty_caption)
                picked = []
            footer = source_column.get("footer")
            if footer is not None:
                footer()

        cleaned_picked = dedupe_source_pill_labels(picked)
        selected_by_source[source_key] = cleaned_picked
        for label in cleaned_picked:
            normalized = normalize_source_pill_label(label)
            if not normalized or normalized in merged_seen:
                continue
            merged_selected.append(label)
            merged_seen.add(normalized)
            source_counts[source_key] = source_counts.get(source_key, 0) + 1

    for source_column in columns:
        source_key = str(source_column["source_key"]).strip()
        selected_by_source.setdefault(source_key, [])
        source_counts.setdefault(source_key, 0)

    st.session_state[selected_state_key] = merged_selected
    return {
        "selected_labels": merged_selected,
        "selected_by_source": selected_by_source,
        "source_counts": source_counts,
    }
