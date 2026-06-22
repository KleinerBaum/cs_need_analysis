# ui_requirement_board.py
"""Compact requirement comparison and adoption UI helpers."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import streamlit as st

from job_extract_review_helpers import has_meaningful_value
from safe_html import render_static_html


def _render_requirement_board_responsive_css() -> None:
    render_static_html(
        """
        <style>
        @media (max-width: 760px) {
            div[data-testid="stHorizontalBlock"]:has(.cs-requirement-board-source) {
                flex-direction: column;
                gap: 0.75rem;
            }
            div[data-testid="stHorizontalBlock"]:has(.cs-requirement-board-source) > div {
                width: 100% !important;
                flex: 1 1 100% !important;
            }
        }
        </style>
        """,
        streamlit_module=st,
    )

def _normalize_requirement_label(value: str) -> str:
    return " ".join(value.strip().casefold().split())


def _truncate_requirement_label(value: str, *, limit: int = 88) -> str:
    text = " ".join(value.split())
    if len(text) <= limit:
        return text
    return f"{text[: max(limit - 1, 1)].rstrip()}…"


def _build_requirement_table_rows(
    *,
    source_key: str,
    entries: list[dict[str, Any]],
    selected_set: set[str],
    buffer_set: set[str],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for entry in entries:
        label = str(entry.get("label") or "").strip()
        if not label:
            continue
        normalized = _normalize_requirement_label(label)
        importance = str(entry.get("importance") or "").strip()
        note_parts = [
            importance,
            str(entry.get("rationale") or "").strip(),
            str(entry.get("evidence") or "").strip(),
        ]
        notes = " | ".join(part for part in note_parts if part)
        rows.append(
            {
                "select": normalized in selected_set or normalized in buffer_set,
                "label": _truncate_requirement_label(label),
                "source": source_key,
                "notes": _truncate_requirement_label(notes, limit=120) if notes else "",
                "_full_label": label,
                "_normalized_label": normalized,
                "_importance": importance,
            }
        )
    return rows


def _is_high_importance(importance: str) -> bool:
    normalized = _normalize_requirement_label(importance)
    if not normalized:
        return False
    high_markers = {
        "hoch",
        "high",
        "sehr hoch",
        "very high",
        "critical",
        "kritisch",
    }
    return normalized in high_markers


def _render_requirement_selection_table(
    *,
    title: str,
    source_key: str,
    entries: list[dict[str, Any]],
    selected_set: set[str],
    selection_state_key: str,
    key_prefix: str,
) -> list[str]:
    table_rows = _build_requirement_table_rows(
        source_key=source_key,
        entries=entries,
        selected_set=selected_set,
        buffer_set={
            _normalize_requirement_label(str(label))
            for label in st.session_state.get(selection_state_key, [])
            if has_meaningful_value(label)
        },
    )
    if not table_rows:
        return []

    st.caption(title)
    filter_key_prefix = f"{key_prefix}.filters.{source_key.casefold()}"
    default_only_new_key = f"{filter_key_prefix}.default_only_new"
    if default_only_new_key not in st.session_state:
        st.session_state[default_only_new_key] = True
    search_term = st.text_input(
        "Suche",
        value="",
        key=f"{filter_key_prefix}.search",
        placeholder="Begriff eingeben…",
        help="Filtert Vorschläge direkt nach Bezeichnung und Hinweisen.",
    ).strip()
    only_new = st.toggle(
        "Nur neue Vorschläge",
        key=f"{filter_key_prefix}.only_new",
        value=bool(st.session_state.get(default_only_new_key, True)),
    )
    st.session_state[default_only_new_key] = False

    filtered_rows: list[dict[str, Any]] = []
    normalized_search = _normalize_requirement_label(search_term)
    for row in table_rows:
        if only_new and bool(row.get("select")):
            continue
        if normalized_search:
            haystack = _normalize_requirement_label(
                f"{row.get('_full_label', '')} {row.get('notes', '')}"
            )
            if normalized_search not in haystack:
                continue
        filtered_rows.append(row)

    if not filtered_rows:
        st.caption("Keine Treffer für die aktuellen Filter.")
        return []

    editor_key = f"{key_prefix}.editor.{source_key.casefold()}"
    edited_rows = st.data_editor(
        filtered_rows,
        key=editor_key,
        width="stretch",
        height=320,
        hide_index=True,
        num_rows="fixed",
        column_order=["select", "label", "notes"],
        column_config={
            "select": st.column_config.CheckboxColumn("Auswahl"),
            "label": st.column_config.TextColumn("Bezeichnung", disabled=True),
            "notes": st.column_config.TextColumn("Hinweise", disabled=True),
        },
    )
    selected_labels: list[str] = []
    for row in edited_rows:
        if not bool(row.get("select")):
            continue
        label = str(row.get("_full_label") or "").strip()
        if label:
            selected_labels.append(label)

    selected_index = next(
        (index for index, row in enumerate(edited_rows) if bool(row.get("select"))), -1
    )
    if selected_index >= 0:
        selected_row = edited_rows[selected_index]
        selected_label = str(selected_row.get("_full_label") or "").strip()
        notes = str(selected_row.get("notes") or "").strip()
        with st.expander("Vorschau", expanded=False):
            st.write(selected_label or "Keine Details verfügbar.")
            if notes:
                st.caption(notes)
    return selected_labels


def render_compare_adopt_intro(
    *,
    adopt_target: str,
    canonical_target: str,
    source_labels: Sequence[str] = ("Jobspec", "ESCO", "AI"),
    include_inferred_confirmed_note: bool = False,
    render_explanatory_copy: bool = False,
) -> None:
    return None


def render_compact_requirement_board(
    *,
    title_jobspec: str,
    jobspec_items: list[dict[str, Any]],
    title_esco: str,
    esco_items: list[dict[str, Any]],
    title_llm: str,
    llm_items: list[dict[str, Any]],
    selected_labels: list[str],
    selection_state_key: str,
    key_prefix: str,
    empty_messages: dict[str, str] | None = None,
) -> list[str]:
    selected_set = {
        _normalize_requirement_label(str(item))
        for item in selected_labels
        if has_meaningful_value(item)
    }
    board_items_all = [
        (title_jobspec, jobspec_items, "Jobspec"),
        (title_esco, esco_items, "ESCO"),
        (title_llm, llm_items, "AI"),
    ]
    board_items = [item for item in board_items_all if item[1]]
    if not board_items:
        st.caption("Keine Vorschläge.")
        st.session_state[selection_state_key] = []
        return []

    bulk_labels: list[str] = []
    if len(board_items) > 1:
        _render_requirement_board_responsive_css()
    columns = st.columns(len(board_items), gap="large")
    for column, (title, entries, source_badge) in zip(columns, board_items):
        with column:
            render_static_html(
                '<span class="cs-requirement-board-source" aria-hidden="true"></span>',
                streamlit_module=st,
            )
            if entries:
                bulk_labels.extend(
                    _render_requirement_selection_table(
                        title=title,
                        source_key=source_badge,
                        entries=entries,
                        selected_set=selected_set,
                        selection_state_key=selection_state_key,
                        key_prefix=key_prefix,
                    )
                )
            else:
                st.caption((empty_messages or {}).get(source_badge, "Keine Vorschläge."))

    deduped_labels: list[str] = []
    seen: set[str] = set()
    for label in bulk_labels:
        normalized = _normalize_requirement_label(label)
        if not normalized or normalized in seen:
            continue
        deduped_labels.append(label)
        seen.add(normalized)
    st.session_state[selection_state_key] = deduped_labels
    return deduped_labels
